# OLm-Mn-wed

> 基于 [Ollama](https://ollama.com) / llama.cpp 的本地 AI 模型 WebUI —— 简洁、透明（毛玻璃 Glassmorphism）风格，支持**模型管理、流式聊天、知识库 RAG、OpenAI 兼容 API**。

- 前端：Vue 3 + Vite + TailwindCSS（`backdrop-filter` 毛玻璃、深/浅色主题、中英文 i18n）
- 后端：Python FastAPI + SQLite（SQLAlchemy 2.0）
- 推理引擎：**Ollama** 原生 API，或任意 **OpenAI 兼容后端**（llama-swap / llama.cpp server / vLLM 等）
- 容器化：Docker Compose 双容器，支持 `linux/amd64` 与 `linux/arm64`

---

## ✨ 功能特性

| 模块 | 功能 |
| --- | --- |
| 🔐 认证 | 首次启动自动创建 `admin`，随机密码打印到容器日志；支持修改用户名/密码（JWT） |
| 💬 聊天 | 多会话管理、**SSE 流式输出**、Markdown 渲染 + 代码高亮、**重新生成回复**、消息复制 |
| ⚙️ 参数 | 温度、思考模式（Qwen3/DeepSeek）、上下文长度（num_ctx）、num_gpu / num_thread、System Prompt、**人格预设（可保存/选择）** |
| 🧠 模型 | 模型列表（含加载状态）、**加载 / 卸下（释放内存）**、上传 GGUF（**分块上传，大文件可靠**）、自动注册到后端、删除（含后端配置移除）、每模型默认参数、内存/显存预估 |
| 📚 知识库 | 上传 txt / md / pdf → 文本提取 → 分块 → 向量化（Ollama 嵌入模型）→ 聊天 RAG 检索增强 |
| ⚡ API | OpenAI 兼容 `/v1/chat/completions`（流式/非流式）与 `/v1/models`，API Key 鉴权，服务开关，端口可配 |
| ⚙️ 设置 | 深色/浅色/跟随系统、中英文、修改密码/用户名、检查更新（GitHub 对比）、模型后端管理（重启/停止/启动） |

## 🗂 双后端支持

通过环境变量 `OLLAMA_API_STYLE` 切换：

- **`ollama`**（默认）：原生 Ollama REST API（`/api/tags`、`/api/chat`、`/api/create`……）
- **`openai`**：OpenAI 兼容端点（`/v1/models`、`/v1/chat/completions`、`/v1/embeddings`）—— 可对接 llama-swap、llama.cpp server、vLLM 等，支持**自动读写后端配置**（注册/删除/上下文同步）

## 🏗 系统架构

```
┌────────────────────────────────────────────────────────┐
│ 宿主机 (Host)                                           │
│  ./models ──┐                  ./data ──┐              │
│             │ bind mount                  │             │
│  ┌──────────▼──────────┐   ┌─────────────▼─────────┐   │
│  │  webapp 容器          │   │  ollama 容器           │   │
│  │  Vue 构建产物 + FastAPI│   │  ollama/ollama        │   │
│  │  :3000 Web UI         │   │  不对外暴露端口         │   │
│  │  :3001 API (可选)      │   │  OLLAMA_MODELS=/models │   │
│  └──────────▲──────────┘   └─────────────▲─────────┘   │
│             │                              │            │
│         /app/models                    /models         │
│             └──────────────┬───────────────┘            │
│                    同一 ./models 目录                    │
└────────────────────────────────────────────────────────┘
```

## 🚀 快速开始（Docker）

**前置要求**：Docker ≥ 23（自带 BuildKit）、Docker Compose v2。

```bash
# 1. 克隆
git clone https://github.com/Zhu1024Byte/OLm-Mn-wed.git
cd OLm-Mn-wed

# 2.（可选）自定义端口/密钥
cp .env.example .env

# 3. 构建并启动
docker compose up --build -d

# 4. 查看初始 admin 密码
docker compose logs webapp | grep -A 4 "password"

# 5. 打开 http://localhost:3000 登录
```

> 首次启动自动创建 `admin`，随机密码打印在日志并保存于 `./data/admin_credentials.txt`。

## ⚡ 一条命令直接运行（已发布 Docker 镜像，无需 clone / 无需选位置）

镜像发布在 **GitHub Container Registry**：`ghcr.io/zhu1024byte/olm-mn-wed:latest`（amd64 + arm64，由 GitHub Actions 自动构建）。

**方式 1 — 已有 Ollama / llama-swap 后端，只想跑 WebUI（单容器）**：

```bash
docker run -d --name olm-mn-wed -p 3000:3000 -p 3001:3001 \
  -e OLLAMA_BASE_URL=http://<你的后端IP>:11434 \
  -v $(pwd)/models:/app/models -v $(pwd)/data:/app/data \
  ghcr.io/zhu1024byte/olm-mn-wed:latest

docker logs olm-mn-wed 2>&1 | grep -A 4 "password"   # admin 密码
# 打开 http://localhost:3000
```

**方式 2 — 连 Ollama 一起跑（双容器，一条命令）**：

```bash
curl -o docker-compose.yml https://raw.githubusercontent.com/Zhu1024Byte/OLm-Mn-wed/main/docker-compose.prod.yml
docker compose up -d
```

或直接引用远程文件（无需保存）：

```bash
docker compose -f https://raw.githubusercontent.com/Zhu1024Byte/OLm-Mn-wed/main/docker-compose.prod.yml up -d
```

> 模型目录 `./models`、数据目录 `./data` 会自动在当前目录创建并挂载（不想放在当前目录就自己改路径）。

### 从源码构建（可选）

```bash
git clone https://github.com/Zhu1024Byte/OLm-Mn-wed.git
cd OLm-Mn-wed
docker compose up --build -d
```

### 双架构构建（AMD64 + ARM64）

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t olm-mn-wed:latest -f backend/Dockerfile --push .
```

### GPU 加速（可选）

- **NVIDIA**：宿主机安装 [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)，在 compose 的 ollama 服务取消注释 `deploy.resources.reservations.devices`（见 `docker-compose.yml` 注释）。
- **AMD**：ollama 镜像换为 `ollama/ollama:rocm`，添加 `/dev/kfd`、`/dev/dri`。

## 💻 原生部署（无 Docker）

当无法拉取镜像时（如受限网络），可直接用 Python 运行：

```bash
# 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OLLAMA_BASE_URL=http://localhost:11434        # 或指向 llama-swap / vLLM
export OLLAMA_API_STYLE=ollama                        # 或 openai
uvicorn app.main:app --port 3000

# 前端构建产物（dist）放入 backend/static 即可被后端托管
```

## 🔧 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `WEB_PORT` / `API_PORT` | `3000` / `3001` | 宿主机映射端口 |
| `SECRET_KEY` | 空 | JWT 密钥，留空自动生成（`./data/.secret_key`） |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | 模型后端地址 |
| `OLLAMA_API_STYLE` | `ollama` | `ollama` 原生 / `openai` 兼容 |
| `EMBED_MODEL` | `nomic-embed-text` | 知识库嵌入模型 |
| `PROJECT_REPO` | 空 | 检查更新用的项目 GitHub 仓库 |

## 📖 API 文档

启动后访问 `http://localhost:3000/docs`（Swagger UI）。

核心端点：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/auth/login` | 登录（JWT） |
| `POST` | `/api/chat` | **SSE 流式聊天** |
| `GET/POST/PATCH/DELETE` | `/api/conversations[/{id}]` | 会话 CRUD |
| `GET` | `/api/ollama/tags` | 模型列表（含状态） |
| `POST` | `/api/models/upload/chunk` | **分块上传 GGUF** |
| `POST` | `/api/models/import` | 导入/自动注册模型 |
| `POST` | `/api/models/{name}/load` `/unload` | **加载 / 卸下模型** |
| `GET/PUT` | `/api/models/{name}/config` | 每模型默认参数（含后端 ctx 同步） |
| `POST` | `/api/knowledge/upload` | 知识库上传（txt/md/pdf） |
| `GET/POST/PATCH/DELETE` | `/api/personas` | 人格预设 |
| `GET/POST/PATCH/DELETE` | `/api/keys` | API Key 管理 |
| `GET` | `/api/system/status` | 后端健康状态 |

**OpenAI 兼容 API**（`:3001`）：`POST /v1/chat/completions`、`GET /v1/models`（Bearer API Key 鉴权）。

## 🗺 Roadmap

- [x] 登录/认证、会话管理、SSE 流式聊天
- [x] 模型上传（分块）、导入、加载/卸下、删除、参数配置
- [x] 知识库 RAG
- [x] OpenAI 兼容 API + API Key
- [x] 人格预设、i18n、主题
- [ ] MCP 服务器支持（界面占位）
- [ ] 联网搜索插件
- [ ] 多用户注册/角色权限
- [ ] 模型间对话转发/对比

## 🤝 贡献

欢迎提交 Issue 与 PR！开发流程：

```bash
cd frontend && npm install && npm run dev   # 前端热更新（代理到 :8000）
cd backend  && uvicorn app.main:app --reload
```

## ❓ 常见问题：缺少容器 / 容器误删怎么办

项目包含 **2 类容器**，各自作用与恢复方法：

| 容器 | 作用 | 缺少时的表现 | 恢复 |
| --- | --- | --- | --- |
| `webapp`（本项目镜像） | Web 界面 + API（:3000/:3001） | 网页打不开 | `docker compose up -d`（双容器）或 `docker run` 单容器（见上） |
| `ollama` 或 `llama-swap` | 模型推理后端（:11434 或 :8080） | 网页能开，但**模型列表为空/聊天报"无法连接模型后端"** | 见下方 |

### 模型后端（ollama / llama-swap）缺失或启动失败

**现象**：登录正常，但模型页空白、聊天报错。

**检查**（Compose 双容器方式）：
```bash
docker compose ps              # ollama 是否 Up
docker compose logs ollama     # 看报错
```

**恢复**：
```bash
# 双容器：ollama 由 compose 管理，直接拉起
docker compose up -d

# 单容器 + 外部 llama-swap：重新启动 llama-swap
docker run -d --name llama-swap -p 8080:8080 \
  -v $(pwd)/models:/models \
  -v /path/to/llamaswap-config.yaml:/app/config.yaml \
  --restart unless-stopped \
  ghcr.io/mostlygeek/llama-swap:cpu
```

**llama-swap 配置要点**（易错）：
1. `cmd` 中必须用**完整路径** `/app/llama-server`（裸命令 `llama-server` 会因动态库解析失败而 500）
2. 模型路径用容器内视角 `/models/xxx.gguf`
3. 配置挂载或写入容器内 `/app/config.yaml`（容器重建会丢，建议挂载宿主机文件）
4. 镜像自带示例配置可能是坏的，务必用自己写的配置挂载覆盖

### 数据与模型目录（别删！）

- `./data`：SQLite 数据库、账号密码、聊天记录、知识库索引 —— **删了密码和记录全丢**
- `./models`：GGUF 模型文件 —— **删了模型全丢**
- 容器删除**不会**删除这两个挂载目录，但手动清理时注意

### 端口被占 / 登录不上

- `3000` 被其他服务占用 → 改 `.env` 的 `WEB_PORT` 后 `docker compose up -d`
- 登录不上：先确认访问的是**正确的端口**和**正确的实例**（避免多实例并存）；首次密码在 `docker compose logs webapp | grep password` 或 `./data/admin_credentials.txt`

## 📄 License

[MIT](./LICENSE)

---

**仅供学习研究使用。模型版权归各模型原作者所有，请遵守相应许可。**
