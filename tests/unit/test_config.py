"""config.py 单元测试。

验证 Pydantic 配置模型的加载、验证和边界条件。
"""

import tempfile
from pathlib import Path

import pytest

from civsim.config import (
    CivSimConfig,
    ClockConfig,
    find_config_path,
    get_config,
    load_config,
    reset_config,
)


class TestLoadConfig:
    """测试配置文件加载。"""

    def test_load_default_config(self, config_path: Path) -> None:
        """验证能正确加载项目的 config.yaml。"""
        config = load_config(config_path)
        assert config.project.name == "CivSim"
        assert config.project.version == "0.1.0"

    def test_load_config_all_sections(self, config_path: Path) -> None:
        """验证所有配置段都被正确加载。"""
        config = load_config(config_path)
        assert config.world.grid.width == 100
        assert config.world.grid.height == 100
        assert config.clock.ticks_per_day == 4
        assert config.agents.civilian.initial_count == 1000
        assert config.resources.types == ["food", "wood", "ore", "gold"]
        assert config.database.engine == "duckdb"
        assert config.testing.test_grid_size == 20
        assert config.visualization.renderer == "matplotlib"

    def test_load_nonexistent_file_raises(self) -> None:
        """验证加载不存在的文件时抛出 FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")

    def test_load_empty_config(self) -> None:
        """验证空配置文件使用默认值。"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("")
            f.flush()
            config = load_config(f.name)
        assert config.project.name == "CivSim"
        assert config.world.grid.width == 100


class TestConfigValidation:
    """测试配置值的校验约束。"""

    def test_invalid_temperature_raises(self) -> None:
        """验证 temperature 超出范围时报错。"""
        data = {
            "llm": {
                "models": {
                    "governor": {
                        "provider": "anthropic",
                        "model": "test",
                        "temperature": 3.0,
                    }
                }
            }
        }
        with pytest.raises((ValueError, Exception)):
            CivSimConfig(**data)

    def test_invalid_personality_distribution_raises(self) -> None:
        """验证性格分布比例之和不为 1.0 时报错。"""
        data = {
            "agents": {
                "civilian": {
                    "personality_distribution": {
                        "compliant": 0.5,
                        "neutral": 0.3,
                        "rebellious": 0.3,
                    }
                }
            }
        }
        with pytest.raises((ValueError, Exception)):
            CivSimConfig(**data)

    def test_negative_grid_size_raises(self) -> None:
        """验证网格尺寸不能为负数或零。"""
        data = {"world": {"grid": {"width": -1, "height": 100}}}
        with pytest.raises((ValueError, Exception)):
            CivSimConfig(**data)

    def test_valid_custom_config(self) -> None:
        """验证自定义配置值能正确加载。"""
        data = {
            "world": {"grid": {"width": 50, "height": 50}},
            "clock": {"ticks_per_day": 8},
            "agents": {"civilian": {"initial_count": 500}},
        }
        config = CivSimConfig(**data)
        assert config.world.grid.width == 50
        assert config.clock.ticks_per_day == 8
        assert config.agents.civilian.initial_count == 500


class TestClockConfig:
    """测试时间系统计算属性。"""

    def test_ticks_per_season(self) -> None:
        """验证每季度 tick 数计算。"""
        clock = ClockConfig(ticks_per_day=4, days_per_season=30)
        assert clock.ticks_per_season == 120

    def test_ticks_per_year(self) -> None:
        """验证每年 tick 数计算。"""
        clock = ClockConfig(ticks_per_day=4, days_per_season=30, seasons_per_year=4)
        assert clock.ticks_per_year == 480


class TestFindConfigPath:
    """测试配置文件路径查找。"""

    def test_explicit_path(self, config_path: Path) -> None:
        """验证显式指定路径时直接返回。"""
        result = find_config_path(config_path)
        assert result == config_path.resolve()

    def test_explicit_nonexistent_raises(self) -> None:
        """验证显式指定不存在的路径时报错。"""
        with pytest.raises(FileNotFoundError):
            find_config_path("/no/such/file.yaml")


class TestGetConfig:
    """测试全局配置单例。"""

    def test_singleton_returns_same_instance(self, config_path: Path) -> None:
        """验证多次调用返回同一实例。"""
        c1 = get_config(config_path)
        c2 = get_config()
        assert c1 is c2

    def test_reset_clears_singleton(self, config_path: Path) -> None:
        """验证 reset 后重新加载。"""
        c1 = get_config(config_path)
        reset_config()
        c2 = get_config(config_path)
        assert c1 is not c2
        assert c1.project.name == c2.project.name


class TestEnvVarExpansion:
    """测试环境变量展开。"""

    def test_env_var_expansion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """验证 ${VAR} 格式的值被正确展开。"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
        data = {"llm": {"api_keys": {"anthropic": "${ANTHROPIC_API_KEY}"}}}
        config = CivSimConfig(**data)
        assert config.llm.api_keys.anthropic == "test-key-123"

    def test_missing_env_var_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """验证环境变量不存在时返回空字符串。"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        data = {"llm": {"api_keys": {"anthropic": "${ANTHROPIC_API_KEY}"}}}
        config = CivSimConfig(**data)
        assert config.llm.api_keys.anthropic == ""

    def test_literal_value_not_expanded(self) -> None:
        """验证非 ${} 格式的值不被处理。"""
        data = {"llm": {"api_keys": {"anthropic": "sk-plain-key"}}}
        config = CivSimConfig(**data)
        assert config.llm.api_keys.anthropic == "sk-plain-key"
