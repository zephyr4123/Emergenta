"""gateway.py 单元测试。

验证 LLM 网关的调用、重试、JSON 解析和统计功能。
默认使用真实 LLM 调用（从 config.yaml 读取配置）。
"""

import pytest

from civsim.llm.gateway import LLMGateway, LLMResponse


class TestLLMGatewayInit:
    """测试 LLM 网关初始化。"""

    def test_default_stats(self) -> None:
        """验证初始统计数据为零。"""
        gw = LLMGateway()
        assert gw.stats.total_calls == 0
        assert gw.stats.total_prompt_tokens == 0
        assert gw.stats.errors == 0

    def test_register_model(self) -> None:
        """验证模型注册成功。"""
        gw = LLMGateway()
        # 手动创建一个简单配置
        from civsim.config import LLMModelConfig
        model_cfg = LLMModelConfig(
            provider="openai",
            model="test-model",
            max_tokens=100,
            temperature=0.5,
        )
        gw.register_model("test_role", model_cfg)
        assert "test_role" in gw._model_configs

    def test_call_unregistered_role_raises(self) -> None:
        """验证调用未注册角色时报错。"""
        gw = LLMGateway()
        with pytest.raises(KeyError, match="未注册角色"):
            gw.call("nonexistent", [{"role": "user", "content": "hello"}])


class TestLLMResponseDataclass:
    """测试 LLMResponse 数据类。"""

    def test_default_values(self) -> None:
        """验证默认值。"""
        resp = LLMResponse(content="test")
        assert resp.content == "test"
        assert resp.prompt_tokens == 0
        assert resp.completion_tokens == 0
        assert resp.cache_hit is False

    def test_custom_values(self) -> None:
        """验证自定义值。"""
        resp = LLMResponse(
            content="hello",
            prompt_tokens=10,
            completion_tokens=20,
            latency_ms=150.0,
            model="test-model",
        )
        assert resp.prompt_tokens == 10
        assert resp.completion_tokens == 20
        assert resp.latency_ms == 150.0


class TestLLMGatewayStats:
    """测试统计功能。"""

    def test_reset_stats(self) -> None:
        """验证重置统计。"""
        gw = LLMGateway()
        gw.stats.total_calls = 5
        gw.stats.errors = 2
        gw.reset_stats()
        assert gw.stats.total_calls == 0
        assert gw.stats.errors == 0

    def test_avg_latency_no_calls(self) -> None:
        """验证无调用时平均延迟为 0。"""
        gw = LLMGateway()
        assert gw.stats.avg_latency_ms == 0.0


class TestLLMGatewayRealCall:
    """测试真实 LLM 调用（使用 config.yaml 中的配置）。"""

    @pytest.fixture()
    def gateway_with_config(self) -> LLMGateway:
        """使用项目 config.yaml 配置创建网关。"""
        # 从 config.yaml 加载真实配置
        from civsim.config import load_config
        try:
            config = load_config()
        except FileNotFoundError:
            pytest.skip("找不到 config.yaml")

        gw = LLMGateway(max_retries=1, timeout=60)
        llm_cfg = config.llm
        for role in llm_cfg.models:
            model_cfg = llm_cfg.get_model_config(role)
            gw.register_model(role, model_cfg)
        return gw

    def test_real_llm_call(self, gateway_with_config: LLMGateway) -> None:
        """验证真实 LLM 调用成功。"""
        gw = gateway_with_config
        messages = [
            {"role": "user", "content": "回答'是'或'否'：天空是蓝色的吗？"},
        ]
        response = gw.call("governor", messages)
        assert response.content
        assert len(response.content) > 0
        assert gw.stats.total_calls == 1
        assert response.latency_ms > 0

    def test_real_llm_json_call(self, gateway_with_config: LLMGateway) -> None:
        """验证 LLM JSON 调用并解析。"""
        gw = gateway_with_config
        messages = [
            {
                "role": "user",
                "content": (
                    "请严格以 JSON 格式回复，不要包含任何其他文字。\n"
                    '格式: {"answer": "yes"}\n'
                    "问题：天空是蓝色的吗？"
                ),
            },
        ]
        result = gw.call_json("governor", messages)
        assert isinstance(result, dict)
        assert "answer" in result
