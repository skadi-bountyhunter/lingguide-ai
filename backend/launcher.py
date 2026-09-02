"""Windows 便携版后端启动器。"""
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import sys
from pathlib import Path


def _resource_root() -> Path:
    """资源根由 Electron 显式传入，开发运行时回退到 backend。"""
    value = os.environ.get("LINGGUIDE_RESOURCE_ROOT")
    if value:
        return Path(value).expanduser().resolve()
    return Path(__file__).resolve().parent


def _data_root() -> Path:
    value = os.environ.get("DATA_ROOT") or os.environ.get("LINGGUIDE_DATA_ROOT")
    if value:
        return Path(value).expanduser().resolve()
    return (Path(sys.executable).resolve().parent / "LingGuideData").resolve()


def _atomic_copy(source: Path, target: Path) -> bool:
    """首次启动用临时文件原子落盘，避免中断留下半个数据库。"""
    if target.exists() or not source.is_file():
        return False
    temporary = target.with_suffix(target.suffix + ".tmp")
    shutil.copy2(source, temporary)
    os.replace(temporary, target)
    return True


def initialize_data_root(resource_root: Path, data_root: Path) -> None:
    """准备可写目录并复制公开 seed；无 seed 时由应用创建空库。"""
    for path in (data_root, data_root / "uploads", data_root / "logs"):
        path.mkdir(parents=True, exist_ok=True)
    seed_root = resource_root / "seed"
    _atomic_copy(seed_root / "lingguide.db", data_root / "lingguide.db")
    _atomic_copy(seed_root / "faqs.json", data_root / "faqs.json")
    _atomic_copy(seed_root / "manifest.json", data_root / "manifest.json")


def _reserve_loopback_port() -> tuple[socket.socket, int]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    return sock, int(sock.getsockname()[1])


def _configure_logging(log_path: Path) -> None:
    from loguru import logger

    logger.remove()
    logger.add(
        log_path,
        rotation="5 MB",
        retention=3,
        encoding="utf-8",
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )


def main() -> int:
    resource_root = _resource_root()
    data_root = _data_root()
    initialize_data_root(resource_root, data_root)

    listener, port = _reserve_loopback_port()
    os.environ["RUNTIME_MODE"] = "desktop"
    os.environ.setdefault("RAG_MODE", "lite")
    os.environ["LINGGUIDE_RESOURCE_ROOT"] = str(resource_root)
    os.environ["DATA_ROOT"] = str(data_root)
    os.environ["LINGGUIDE_DESKTOP_ORIGIN"] = f"http://127.0.0.1:{port}"
    _configure_logging(data_root / "logs" / "lingguide.log")

    import uvicorn
    from app.main import app

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_config=None,
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None

    def stop_server(_signum, _frame):
        server.should_exit = True

    signal.signal(signal.SIGINT, stop_server)
    signal.signal(signal.SIGTERM, stop_server)
    ready = {"host": "127.0.0.1", "port": port, "url": f"http://127.0.0.1:{port}"}
    print(f"LINGGUIDE_READY {json.dumps(ready, ensure_ascii=False)}", flush=True)
    server.run(sockets=[listener])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
