"""全局 pytest fixtures。"""

from pathlib import Path

import pytest

from civsim.config import reset_config


@pytest.fixture(autouse=True)
def _reset_config_singleton():
    """每个测试前重置配置单例，防止测试间状态泄漏。"""
    reset_config()
    yield
    reset_config()


@pytest.fixture()
def project_root() -> Path:
    """返回项目根目录路径。"""
    return Path(__file__).resolve().parent.parent


@pytest.fixture()
def config_path(project_root: Path) -> Path:
    """返回 config.yaml 路径。"""
    return project_root / "config.yaml"
