"""First-run seeding: create the default ``admin`` user.

The random password is printed to the container log (project requirement)
and mirrored to ``data/admin_credentials.txt`` for convenience.
"""

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from .models import User
from .security import generate_random_password, hash_password

logger = logging.getLogger("olmwed.seed")

ADMIN_CREDENTIALS_FILE = Path("data/admin_credentials.txt")


def seed_admin(db: Session) -> None:
    """Create ``admin`` with a random password when no users exist yet."""
    if db.query(User).count() > 0:
        return

    password = generate_random_password(16)
    db.add(User(username="admin", password_hash=hash_password(password)))
    db.commit()

    # Requirement: print the random password to the container log.
    logger.warning("=" * 62)
    logger.warning("默认管理员账号已创建 / Default admin account created:")
    logger.warning("  username: admin")
    logger.warning(f"  password: {password}")
    logger.warning("首次登录后请在 设置 -> 修改密码 中更换。")
    logger.warning("=" * 62)

    # Mirror to a file so it survives log rotation / scrollback.
    try:
        ADMIN_CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        ADMIN_CREDENTIALS_FILE.write_text(
            f"username: admin\npassword: {password}\n", encoding="utf-8"
        )
    except OSError:
        logger.warning("无法写入管理员凭据文件 %s", ADMIN_CREDENTIALS_FILE)
