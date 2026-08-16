"""Model management: upload GGUF, import into Ollama, delete, configure, estimate.

Route notes:
- Static routes (/local, /upload, /import) are registered before the
  parameterised /{name} routes so they are matched first.
- Ollama model names may contain slashes (namespaces), so the DELETE and
  config endpoints take the name as a query parameter.
"""

import base64
import json
import logging
import re
import shutil
import subprocess
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import ModelConfig, User
from ..services import ollama

logger = logging.getLogger("olmwed.models")
router = APIRouter()

MODELS_DIR = Path(settings.models_dir)
ALLOWED_EXT = {".gguf"}
MAP_FILE = Path("data/model_files.json")

# Empirical KV-cache factor: KV bytes per token ≈ 0.003% of model bytes.
# (llama.cpp-style estimate; exact value depends on the architecture.)
KV_FACTOR = 0.00003


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_filename(filename: str) -> str:
    """Strip any path components from a client-supplied filename."""
    return Path(filename or "model.gguf").name


def _sanitize_model_name(name: str) -> str:
    """Ollama model names allow [a-zA-Z0-9._:-]; replace anything else."""
    name = re.sub(r"[^a-zA-Z0-9._:\-]", "_", name).strip("._:-")
    return name[:255]


def _load_file_map() -> dict:
    """model_name -> local GGUF filename (sidecar mapping)."""
    try:
        return json.loads(MAP_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_file_map(mapping: dict) -> None:
    MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    MAP_FILE.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_model_file(name: str) -> Path | None:
    """Locate the local GGUF file associated with a model name."""
    mapping = _load_file_map()
    fn = mapping.get(name)
    if fn:
        candidate = MODELS_DIR / fn
        if candidate.is_file():
            return candidate
    # Fallback: guess by basename
    for p in MODELS_DIR.glob("*.gguf"):
        if p.stem == name or p.name == name:
            return p
    return None


def _register_with_llamaswap(model_name: str, filename: str) -> str:
    """Register a GGUF with the llama-swap container and restart it.

    Returns a human-readable note for the caller. Never raises — on any
    failure it returns a message explaining what still needs to be done
    manually.
    """
    cfg, note = _read_llamaswap_config()
    if cfg is None:
        return note

    # upsert the model entry (full path fixes shared-lib resolution)
    models = cfg.setdefault("models", {})
    models[model_name] = {
        "cmd": (
            f"/app/llama-server --port ${{PORT}} --host 0.0.0.0 "
            f"--model /models/{filename} --ctx-size 4096 --threads 4"
        ),
        "ttl": 1800,
    }

    note = _write_llamaswap_config(cfg)
    if note:
        return note

    logger.info("已自动注册模型 %s -> %s 并重启 llama-swap", model_name, filename)
    return f"已注册到模型后端（{model_name}）并重启生效"


def _unregister_from_llamaswap(model_name: str) -> str:
    """Remove a model entry from the llama-swap config and restart it.

    Returns a note; never raises. Used by the OpenAI-compatible delete path so
    the model actually disappears from the backend list.
    """
    cfg, note = _read_llamaswap_config()
    if cfg is None:
        return note

    models = cfg.get("models") or {}
    if model_name not in models:
        return "模型不在 llama-swap 配置中（无需移除）"
    del models[model_name]

    note = _write_llamaswap_config(cfg)
    if note:
        return note

    logger.info("已从 llama-swap 移除模型 %s 并重启", model_name)
    return f"已从模型后端移除（{model_name}）并重启生效"


def _update_llamaswap_ctx(model_name: str, num_ctx: int) -> str:
    """Update a model's ``--ctx-size`` in the llama-swap config and restart.

    Returns a note; never raises. This is what makes the context-length
    slider actually take effect on llama.cpp backends (ctx is fixed at
    server start, so we rewrite the command and restart).
    """
    cfg, note = _read_llamaswap_config()
    if cfg is None:
        return note

    models = cfg.get("models") or {}
    entry = models.get(model_name)
    if not entry:
        return "模型不在 llama-swap 配置中，无法更新上下文长度"

    cmd = str(entry.get("cmd", ""))
    new_cmd = re.sub(r"--ctx-size\s+\d+", f"--ctx-size {int(num_ctx)}", cmd)
    if "--ctx-size" not in new_cmd:
        new_cmd = f"{new_cmd} --ctx-size {int(num_ctx)}"
    entry["cmd"] = new_cmd

    note = _write_llamaswap_config(cfg)
    if note:
        return note

    logger.info("已更新模型 %s 的 ctx -> %s 并重启 llama-swap", model_name, num_ctx)
    return f"上下文长度已更新为 {num_ctx}（模型后端已重启生效）"


def _read_llamaswap_config() -> tuple[dict | None, str]:
    """Read llama-swap's config.yaml. Returns (cfg, note); cfg=None on failure."""
    try:
        import yaml  # PyYAML
    except ImportError:
        return None, "服务器缺少 PyYAML，请手动修改 llama-swap 配置"

    docker = shutil.which("docker")
    if not docker:
        return None, "未检测到 docker（webapp 容器内运行），请手动修改 llama-swap 配置"

    try:
        proc = subprocess.run(
            [docker, "exec", "llama-swap", "cat", "/app/config.yaml"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception as exc:
        return None, f"读取 llama-swap 配置失败：{exc}"
    if proc.returncode != 0:
        return None, f"读取 llama-swap 配置失败：{proc.stderr.strip()[:150]}"

    try:
        return (yaml.safe_load(proc.stdout) or {}), ""
    except Exception as exc:
        return None, f"解析 llama-swap 配置失败：{exc}"


def _write_llamaswap_config(cfg: dict) -> str:
    """Write cfg back to llama-swap and restart it. Returns '' on success."""
    try:
        import yaml  # PyYAML
    except ImportError:
        return "服务器缺少 PyYAML，请手动修改 llama-swap 配置"

    docker = shutil.which("docker")
    if not docker:
        return "未检测到 docker（webapp 容器内运行），请手动修改 llama-swap 配置"

    new_yaml = yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, default_flow_style=False)
    encoded = base64.b64encode(new_yaml.encode("utf-8")).decode("ascii")
    try:
        subprocess.run(
            [docker, "exec", "llama-swap", "sh", "-c", f"echo {encoded} | base64 -d > /app/config.yaml"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
    except Exception as exc:
        return f"写入 llama-swap 配置失败：{exc}"

    try:
        subprocess.run([docker, "restart", "llama-swap"], capture_output=True, text=True, timeout=120, check=True)
    except Exception as exc:
        return f"配置已写入，但重启模型后端失败：{exc}"
    return ""


def _system_memory() -> dict | None:
    """Total/available RAM from /proc/meminfo (Linux). None elsewhere."""
    try:
        info = {}
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            parts = line.split(":")
            if len(parts) == 2:
                info[parts[0].strip()] = int(parts[1].strip().split()[0])  # kB
        total = info.get("MemTotal")
        available = info.get("MemAvailable")
        if total is None or available is None:
            return None
        return {"total": total * 1024, "available": available * 1024}
    except (OSError, ValueError, IndexError):
        return None


def _gpu_info() -> list[dict] | None:
    """Best-effort VRAM info via nvidia-smi. None if unavailable."""
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        gpus = []
        for line in out.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 3:
                gpus.append(
                    {"name": parts[0], "total": int(parts[1]) * 1024 * 1024, "free": int(parts[2]) * 1024 * 1024}
                )
        return gpus or None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


# ---------------------------------------------------------------------------
# Local GGUF files
# ---------------------------------------------------------------------------
@router.get("/local", summary="扫描本地 GGUF 文件")
def list_local_models(_: User = Depends(get_current_user)):
    """Scan the shared ./models directory (webapp view: /app/models)."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for p in sorted(MODELS_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in ALLOWED_EXT:
            files.append({"filename": p.name, "size": p.stat().st_size})
    return {"files": files, "dir": str(MODELS_DIR)}


@router.post("/upload", summary="上传 GGUF 文件")
async def upload_model(file: UploadFile = File(...), _: User = Depends(get_current_user)):
    """Save an uploaded .gguf into /app/models (visible to Ollama at /models)."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(file.filename or "model.gguf")
    if not filename.lower().endswith(".gguf"):
        raise HTTPException(status_code=400, detail="仅支持 .gguf 格式的文件")

    dest = MODELS_DIR / filename
    size = 0
    try:
        with open(dest, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                out.write(chunk)
                size += len(chunk)
    except Exception as exc:  # noqa: BLE001 — client disconnect / aborted upload
        dest.unlink(missing_ok=True)
        logger.warning("上传中断（%s），已清理不完整文件 %s", exc.__class__.__name__, filename)
        raise HTTPException(status_code=400, detail="上传中断，已清理不完整文件")
    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="上传的文件为空")

    logger.info("GGUF 已上传: %s (%.1f MB)", filename, size / 1024 / 1024)
    return {"filename": filename, "size": size}


@router.put("/upload/raw", summary="上传 GGUF（raw 流式，规避 multipart 解析问题）")
async def upload_model_raw(request: Request, filename: str, _: User = Depends(get_current_user)):
    """Raw-binary upload: request body is the file bytes, name via query.

    Avoids multipart parsing entirely (python-multipart has known issues with
    large files / special filenames that surface as "There was an error
    parsing the body").
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(filename or "model.gguf")
    if not filename.lower().endswith(".gguf"):
        raise HTTPException(status_code=400, detail="仅支持 .gguf 格式的文件")

    dest = MODELS_DIR / filename
    size = 0
    try:
        with open(dest, "wb") as out:
            async for chunk in request.stream():
                out.write(chunk)
                size += len(chunk)
    except Exception as exc:  # noqa: BLE001 — client disconnect / aborted upload
        dest.unlink(missing_ok=True)
        logger.warning("上传中断（%s），已清理不完整文件 %s", exc.__class__.__name__, filename)
        raise HTTPException(status_code=400, detail="上传中断，已清理不完整文件")
    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="上传的文件为空")

    logger.info("GGUF 已上传(raw): %s (%.1f MB)", filename, size / 1024 / 1024)
    return {"filename": filename, "size": size}


# 分块上传：前端按固定块大小切片，串行上传；后端按偏移量幂等写入
UPLOAD_CHUNK_SIZE = 64 * 1024 * 1024  # 64 MiB（与前端一致）


@router.put("/upload/chunk", summary="分块上传 GGUF（可断点续传）")
async def upload_model_chunk(
    request: Request,
    filename: str,
    index: int = 0,
    _: User = Depends(get_current_user),
):
    """Upload one chunk of a file.

    ``index`` is the 0-based chunk number; the chunk is written at
    ``index * 64MiB`` (seek), so re-uploading a failed chunk is idempotent —
    it simply overwrites the same region. The client drives the order and
    finalizes by uploading all chunks (last chunk may be smaller).
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(filename or "model.gguf")
    if not filename.lower().endswith(".gguf"):
        raise HTTPException(status_code=400, detail="仅支持 .gguf 格式的文件")

    dest = MODELS_DIR / filename
    if not dest.exists():
        dest.touch()
    offset = max(index, 0) * UPLOAD_CHUNK_SIZE

    size = 0
    try:
        with open(dest, "r+b") as out:
            out.seek(offset)
            async for chunk in request.stream():
                out.write(chunk)
                size += len(chunk)
    except Exception as exc:  # noqa: BLE001 — client disconnect / aborted upload
        logger.warning("分块上传中断（%s）: %s #%s", exc.__class__.__name__, filename, index)
        raise HTTPException(status_code=400, detail="分块上传中断")
    if size == 0:
        raise HTTPException(status_code=400, detail="分块数据为空")

    logger.info("GGUF 分块: %s #%s (%d bytes @ %d)", filename, index, size, offset)
    return {"filename": filename, "index": index, "offset": offset, "size": size}


@router.post("/upload/finalize", summary="完成分块上传（校验大小）")
async def finalize_upload(
    payload: dict,
    _: User = Depends(get_current_user),
):
    """Mark a chunked upload complete and verify the resulting file size."""
    filename = _safe_filename(str(payload.get("filename", "")))
    expected = int(payload.get("size", 0) or 0)
    dest = MODELS_DIR / filename
    if not dest.is_file():
        raise HTTPException(status_code=404, detail=f"文件不存在：{filename}")
    actual = dest.stat().st_size
    if expected > 0 and actual != expected:
        # 大小不符：说明有块丢失/重复写坏，清理让用户重传
        dest.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=f"上传不完整（期望 {expected} 字节，实际 {actual} 字节），已清理，请重新上传",
        )
    logger.info("GGUF 分块上传完成: %s (%.1f MB)", filename, actual / 1024 / 1024)
    return {"filename": filename, "size": actual}


@router.post("/import", summary="导入 GGUF 到模型后端")
async def import_model(payload: dict, _: User = Depends(get_current_user)):
    """Create a model from a local GGUF.

    - Ollama: ``/api/create`` with ``FROM /models/<file>``.
    - OpenAI-compatible (llama.cpp / llama-swap): the GGUF was already saved by
      the upload step; we return ``status: saved`` with a hint instead of
      failing — the file is ready to be registered in the backend config.
    """
    filename = _safe_filename(str(payload.get("filename", "")))
    if not filename.lower().endswith(".gguf"):
        raise HTTPException(status_code=400, detail="仅支持 .gguf 格式的文件")

    if not (MODELS_DIR / filename).is_file():
        raise HTTPException(status_code=404, detail=f"本地文件不存在：{filename}")

    raw_name = str(payload.get("name") or "").strip() or filename[:-5]
    model_name = _sanitize_model_name(raw_name)
    if not model_name:
        raise HTTPException(status_code=400, detail="模型名称不合法")

    modelfile = f"FROM /models/{filename}\n"
    try:
        result = await ollama.create_model(model_name, modelfile)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except httpx.HTTPError as exc:
        logger.warning("Ollama create 失败: %s", exc)
        raise HTTPException(status_code=502, detail=f"导入 Ollama 失败（{exc}），请检查 ollama 容器")

    mapping = _load_file_map()
    mapping[model_name] = filename
    _save_file_map(mapping)

    status = result.get("status", "imported")
    note = result.get("note", "")

    # OpenAI-compatible backend: the GGUF is saved; try to register it with
    # llama-swap automatically so the model becomes usable right away.
    if status == "saved":
        note = _register_with_llamaswap(model_name, filename)
        status = "registered"

    return {
        "name": model_name,
        "filename": filename,
        "status": status,
        "note": note,
    }


@router.delete("", summary="删除模型")
async def delete_model(
    name: str,
    delete_file: bool = False,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a model from the backend; optionally remove the local GGUF too.

    On OpenAI-compatible backends (llama-swap) we remove the entry from the
    llama-swap config and restart it, so the model disappears from the list —
    in addition to cleaning up local files / saved config.
    """
    if not name:
        raise HTTPException(status_code=400, detail="缺少模型名称")

    notes: list[str] = []

    # 1. Try the backend's own delete API (works for Ollama; llama-swap 404s)
    try:
        result = await ollama.delete_model(name)
        if result.get("note"):
            notes.append(result["note"])
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"删除模型后端失败（{exc}）")

    # 2. OpenAI-compatible backend: also remove the entry from llama-swap config
    if settings.ollama_api_style.strip().lower() == "openai":
        notes.append(_unregister_from_llamaswap(name))

    # Remove saved config for the model
    db.query(ModelConfig).filter(ModelConfig.model_name == name).delete()
    db.commit()

    # Optional: remove the local GGUF file
    removed = False
    if delete_file:
        mapping = _load_file_map()
        local_file = _find_model_file(name)
        if local_file is not None:
            try:
                local_file.unlink()
                removed = True
            except OSError:
                logger.warning("无法删除本地文件 %s", local_file)
        mapping.pop(name, None)
        _save_file_map(mapping)

    return {
        "name": name,
        "status": "deleted",
        "file_removed": removed,
        "note": "；".join(n for n in notes if n),
    }


@router.post("/{name}/load", summary="加载模型")
async def load_model(name: str, _: User = Depends(get_current_user)):
    """Trigger loading of a model into memory (Ollama / OpenAI-compatible)."""
    try:
        result = await ollama.load_model(name)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"模型加载失败（{exc}）")
    return {"name": name, "status": result.get("status", "loading")}


@router.post("/{name}/unload", summary="卸下模型（释放内存）")
async def unload_model(name: str, _: User = Depends(get_current_user)):
    """Stop the model and unload it from memory (Ollama / llama-swap)."""
    try:
        result = await ollama.unload_model(name)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"模型卸下失败（{exc}）")
    return {"name": name, "status": result.get("status", "unloaded"), "note": result.get("note", "")}


# ---------------------------------------------------------------------------
# Per-model configuration
# ---------------------------------------------------------------------------
class ModelConfigIn(BaseModel):
    num_ctx: int = Field(default=4096, ge=256, le=131072)
    num_gpu: int = Field(default=-1, ge=-1)
    num_thread: int = Field(default=0, ge=0)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    system_prompt: str = ""


@router.get("/{name}/config", summary="读取模型配置")
def get_model_config(name: str, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = db.query(ModelConfig).filter(ModelConfig.model_name == name).first()
    if cfg is None:
        return {
            "model_name": name,
            "num_ctx": 4096,
            "num_gpu": -1,
            "num_thread": 0,
            "temperature": 0.7,
            "system_prompt": "",
        }
    return cfg


@router.put("/{name}/config", summary="保存模型配置")
def save_model_config(
    name: str,
    payload: ModelConfigIn,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cfg = db.query(ModelConfig).filter(ModelConfig.model_name == name).first()
    if cfg is None:
        cfg = ModelConfig(model_name=name)
        db.add(cfg)
    cfg.num_ctx = payload.num_ctx
    cfg.num_gpu = payload.num_gpu
    cfg.num_thread = payload.num_thread
    cfg.temperature = payload.temperature
    cfg.system_prompt = payload.system_prompt
    db.commit()
    db.refresh(cfg)

    # OpenAI-compatible backend: num_ctx only takes effect at server start —
    # rewrite llama-swap's --ctx-size and restart so the slider is honored.
    sync_note = ""
    if settings.ollama_api_style.strip().lower() == "openai":
        sync_note = _update_llamaswap_ctx(name, payload.num_ctx)

    result = {
        "model_name": cfg.model_name,
        "num_ctx": cfg.num_ctx,
        "num_gpu": cfg.num_gpu,
        "num_thread": cfg.num_thread,
        "temperature": cfg.temperature,
        "system_prompt": cfg.system_prompt,
        "sync_note": sync_note,
    }
    return result


# ---------------------------------------------------------------------------
# Memory / VRAM estimation
# ---------------------------------------------------------------------------
@router.get("/{name}/estimate", summary="内存占用预估")
async def estimate_model(
    name: str,
    num_ctx: int = 4096,
    num_gpu: int = -1,
    _: User = Depends(get_current_user),
):
    """Estimate RAM/VRAM usage from GGUF size + context, vs. system resources.

    Heuristic (approximate):
      weights  ≈ GGUF file size
      KV cache ≈ num_ctx × KV_FACTOR × weights
      total    = weights + KV cache
    """
    local_file = _find_model_file(name)
    file_size = local_file.stat().st_size if local_file else None

    if file_size is None:
        # Fall back to the size reported by /api/tags
        try:
            data = await ollama.tags()
            for m in data.get("models", []):
                if (m.get("name") or m.get("model")) == name:
                    file_size = m.get("size")
                    break
        except httpx.HTTPError:
            pass

    if file_size is None:
        return {"estimated": False, "reason": "找不到模型文件，无法估算"}

    kv_cache = num_ctx * file_size * KV_FACTOR
    total = file_size + kv_cache

    system_mem = _system_memory()
    gpus = _gpu_info()

    advice = []
    if num_gpu == 0:
        advice.append("纯 CPU 运行：权重与 KV 缓存均占用系统内存")
        if system_mem and total > system_mem["available"]:
            advice.append("⚠️ 预估内存超出当前可用内存，请降低 num_ctx 或换用更小的模型")
        elif system_mem and total > system_mem["available"] * 0.8:
            advice.append("⚠️ 内存占用偏高，建议降低 num_ctx")
        else:
            advice.append("✅ 系统内存可满足当前配置")
    else:
        if gpus:
            free_vram = max((g["free"] for g in gpus), default=0)
            if total > free_vram:
                advice.append(f"⚠️ 预估显存需求（{_fmt(total)}）超出 GPU 可用显存（{_fmt(free_vram)}），建议降低 num_ctx 或使用 CPU")
            else:
                advice.append(f"✅ GPU 显存充足（{len(gpus)} 张，可用 {_fmt(free_vram)}）")
        else:
            advice.append("未检测到 NVIDIA GPU（nvidia-smi），按 CPU 内存评估")
            if system_mem and total > system_mem["available"]:
                advice.append("⚠️ 预估内存超出当前可用内存")
            elif system_mem:
                advice.append(f"系统可用内存 {_fmt(system_mem['available'])}")

    return {
        "estimated": True,
        "model": name,
        "file_size": file_size,
        "weights_gb": round(file_size / 1024**3, 2),
        "kv_cache_gb": round(kv_cache / 1024**3, 2),
        "total_gb": round(total / 1024**3, 2),
        "num_ctx": num_ctx,
        "system_memory": system_mem,
        "gpus": gpus,
        "advice": advice,
    }


def _fmt(n: int | float) -> str:
    return f"{n / 1024**3:.1f} GB"
