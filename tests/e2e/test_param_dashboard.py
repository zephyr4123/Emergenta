"""参数面板端到端测试。"""

import pytest

from civsim.config import CivSimConfig
from civsim.dashboard.param_registry import (
    get_config_by_path,
    resolve_legacy_param,
    set_config_by_path,
)


class TestSetParameterViaRunner:
    """通过模拟 Runner 的 _handle_set_parameter 测试通用路径。"""

    def test_generic_path_set(self) -> None:
        """通用配置路径可正确设置。"""
        cfg = CivSimConfig()
        set_config_by_path(cfg, "revolution_params.protest_threshold", 0.5)
        assert cfg.revolution_params.protest_threshold == pytest.approx(0.5)

    def test_legacy_name_resolution(self) -> None:
        """旧参数名经翻译后可正确设置。"""
        cfg = CivSimConfig()
        path = resolve_legacy_param("target_temperature")
        set_config_by_path(cfg, path, 0.8)
        assert cfg.adaptive_controller.target_temperature == pytest.approx(0.8)

    def test_capacity_propagation_e2e(self) -> None:
        """人口上限传播端到端验证。"""
        from civsim.dashboard.param_registry import propagate_capacity

        class FakeSettlement:
            def __init__(self, cap: int = 500) -> None:
                self.capacity = cap

        class FakeEngine:
            def __init__(self) -> None:
                self.settlements = {
                    i: FakeSettlement() for i in range(8)
                }

        engine = FakeEngine()
        cfg = CivSimConfig()

        # 写入配置
        set_config_by_path(cfg, "settlement_params.default_capacity", 2000)
        assert cfg.settlement_params.default_capacity == 2000

        # 传播到运行时
        propagate_capacity(engine, 2000)
        for s in engine.settlements.values():
            assert s.capacity == 2000


class TestDashAppCreation:
    """验证 Dash app 创建不报错。"""

    def test_app_has_seven_tabs(self) -> None:
        """App 布局包含 7 个标签页。"""
        from civsim.dashboard.app import create_app
        from civsim.dashboard.shared_state import SharedState

        state = SharedState()
        app = create_app(state)

        # 查找 Tabs 组件
        layout = app.layout
        tabs_component = None
        for child in layout.children:
            if hasattr(child, "id") and getattr(child, "id", None) == "tabs":
                tabs_component = child
                break

        assert tabs_component is not None, "未找到 tabs 组件"
        assert len(tabs_component.children) == 7, (
            f"期望 7 个标签页，实际 {len(tabs_component.children)}"
        )

    def test_param_tab_present(self) -> None:
        """参数配置标签页存在。"""
        from civsim.dashboard.app import create_app
        from civsim.dashboard.shared_state import SharedState

        state = SharedState()
        app = create_app(state)

        layout = app.layout
        tab_ids = []
        for child in layout.children:
            if hasattr(child, "children") and hasattr(child, "id"):
                if getattr(child, "id", None) == "tabs":
                    for tab in child.children:
                        if hasattr(tab, "tab_id"):
                            tab_ids.append(tab.tab_id)

        assert "tab-params" in tab_ids, f"tab-params 不在 {tab_ids} 中"


class TestPromptOverride:
    """验证 Prompt 覆盖机制。"""

    def test_governor_prompt_override(self) -> None:
        """build_governor_system_prompt 支持 override。"""
        from civsim.llm.prompts import build_governor_system_prompt

        custom = "自定义镇长人格"
        result = build_governor_system_prompt(override=custom)
        assert result == custom

    def test_governor_prompt_default(self) -> None:
        """build_governor_system_prompt 无 override 时返回默认。"""
        from civsim.llm.prompts import build_governor_system_prompt

        result = build_governor_system_prompt()
        assert "聚落镇长" in result

    def test_leader_prompt_override(self) -> None:
        """build_leader_system_prompt 支持 override。"""
        from civsim.llm.prompts import build_leader_system_prompt

        custom = "自定义首领人格"
        result = build_leader_system_prompt(override=custom)
        assert result == custom
