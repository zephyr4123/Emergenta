"""参数注册表单元测试。"""

import pytest

from civsim.config import CivSimConfig
from civsim.dashboard.param_registry import (
    CATEGORIES,
    LEGACY_PARAM_MAP,
    PARAM_REGISTRY,
    SPECIAL_HANDLERS,
    apply_special_handler,
    get_config_by_path,
    get_param_spec,
    get_params_by_category,
    resolve_legacy_param,
    set_config_by_path,
)


class TestGetSetConfigByPath:
    """测试 get/set_config_by_path 通用读写。"""

    def test_get_simple_path(self) -> None:
        """读取一层嵌套路径。"""
        cfg = CivSimConfig()
        val = get_config_by_path(cfg, "adaptive_controller.target_temperature")
        assert val == pytest.approx(0.45)

    def test_get_deep_path(self) -> None:
        """读取多层嵌套路径。"""
        cfg = CivSimConfig()
        val = get_config_by_path(
            cfg, "resources.regeneration.farmland_per_tick",
        )
        assert val == pytest.approx(0.8)

    def test_set_simple_path(self) -> None:
        """写入一层嵌套路径。"""
        cfg = CivSimConfig()
        set_config_by_path(cfg, "adaptive_controller.target_temperature", 0.7)
        assert cfg.adaptive_controller.target_temperature == pytest.approx(0.7)

    def test_set_deep_path(self) -> None:
        """写入多层嵌套路径。"""
        cfg = CivSimConfig()
        set_config_by_path(
            cfg, "resources.consumption.food_per_civilian_per_tick", 1.5,
        )
        assert cfg.resources.consumption.food_per_civilian_per_tick == pytest.approx(1.5)

    def test_invalid_path_raises(self) -> None:
        """无效路径抛出 AttributeError。"""
        cfg = CivSimConfig()
        with pytest.raises(AttributeError):
            get_config_by_path(cfg, "nonexistent.field")


class TestParamRegistryPaths:
    """验证注册表中所有 path 在默认 CivSimConfig 上可解析。"""

    @pytest.mark.parametrize(
        "spec",
        PARAM_REGISTRY,
        ids=[p.config_path for p in PARAM_REGISTRY],
    )
    def test_path_resolvable(self, spec: object) -> None:
        """每条注册表的 path 都应能在默认配置上读到值。"""
        cfg = CivSimConfig()
        val = get_config_by_path(cfg, spec.config_path)  # type: ignore[attr-defined]
        assert val is not None or spec.input_type == "textarea"  # type: ignore[attr-defined]


class TestParamRegistryMetadata:
    """验证注册表元数据完整性。"""

    def test_all_categories_have_params(self) -> None:
        """每个分类至少有一个参数。"""
        for cat in CATEGORIES:
            params = get_params_by_category(cat)
            assert len(params) > 0, f"分类 '{cat}' 没有参数"

    def test_total_params_count(self) -> None:
        """总参数数量 >= 40。"""
        assert len(PARAM_REGISTRY) >= 40

    def test_get_param_spec(self) -> None:
        """通过 path 查找参数。"""
        spec = get_param_spec("revolution_params.protest_threshold")
        assert spec is not None
        assert spec.category == "政治系统"

    def test_get_param_spec_missing(self) -> None:
        """不存在的 path 返回 None。"""
        assert get_param_spec("nonexistent.path") is None


class TestLegacyParamMap:
    """验证旧参数名映射。"""

    def test_legacy_names(self) -> None:
        """旧参数名正确映射到新路径。"""
        assert resolve_legacy_param("target_temperature") == (
            "adaptive_controller.target_temperature"
        )
        assert resolve_legacy_param("food_regen") == (
            "resources.regeneration.farmland_per_tick"
        )
        assert resolve_legacy_param("food_consumption") == (
            "resources.consumption.food_per_civilian_per_tick"
        )

    def test_new_path_passthrough(self) -> None:
        """新路径直接透传。"""
        path = "revolution_params.protest_threshold"
        assert resolve_legacy_param(path) == path


class TestSpecialHandlers:
    """验证特殊传播处理器。"""

    def test_propagate_capacity(self) -> None:
        """capacity 传播到所有聚落。"""

        class FakeSettlement:
            def __init__(self) -> None:
                self.capacity = 500

        class FakeEngine:
            def __init__(self) -> None:
                self.settlements = {
                    0: FakeSettlement(),
                    1: FakeSettlement(),
                    2: FakeSettlement(),
                }

        engine = FakeEngine()
        apply_special_handler("propagate_capacity", engine, 1000)
        for s in engine.settlements.values():
            assert s.capacity == 1000

    def test_propagate_governor_prompt(self) -> None:
        """governor prompt 传播到所有镇长。"""

        class FakeGov:
            def __init__(self) -> None:
                self.system_prompt_override: str | None = None

        govs = [FakeGov(), FakeGov()]

        class FakeEngine:
            def get_governors(self) -> list:
                return govs

        engine = FakeEngine()
        apply_special_handler("propagate_governor_prompt", engine, "新Prompt")
        for g in govs:
            assert g.system_prompt_override == "新Prompt"

    def test_propagate_leader_prompt(self) -> None:
        """leader prompt 传播到所有首领。"""

        class FakeLeader:
            def __init__(self) -> None:
                self.system_prompt_override: str | None = None

        leaders = [FakeLeader(), FakeLeader()]

        class FakeEngine:
            def __init__(self) -> None:
                self.leaders = leaders

        engine = FakeEngine()
        apply_special_handler("propagate_leader_prompt", engine, "首领Prompt")
        for l in leaders:
            assert l.system_prompt_override == "首领Prompt"

    def test_unknown_handler(self) -> None:
        """未知处理器名称不报错。"""
        apply_special_handler("unknown_handler", object(), 42)

    def test_all_registered_handlers_exist(self) -> None:
        """所有注册表中引用的特殊处理器都已实现。"""
        for spec in PARAM_REGISTRY:
            if spec.special_handler:
                assert spec.special_handler in SPECIAL_HANDLERS, (
                    f"处理器 '{spec.special_handler}' 未实现"
                )


class TestGovernorPromptConfig:
    """验证 GovernorPromptConfig 集成。"""

    def test_config_has_governor_prompt(self) -> None:
        """CivSimConfig 包含 governor_prompt 字段。"""
        cfg = CivSimConfig()
        assert hasattr(cfg, "governor_prompt")
        assert cfg.governor_prompt.system_prompt != ""

    def test_governor_prompt_path_resolvable(self) -> None:
        """governor_prompt.system_prompt 路径可解析。"""
        cfg = CivSimConfig()
        val = get_config_by_path(cfg, "governor_prompt.system_prompt")
        assert isinstance(val, str)
        assert len(val) > 10
