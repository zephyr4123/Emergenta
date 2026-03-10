"""LiteLLM 网关封装。

统一多模型调用接口，支持重试、超时控制和 token 消耗统计。
通过 config.yaml 配置路由不同角色到不同模型。
"""

import json
import logging
import time
from dataclasses import dataclass

import litellm

from civsim.config import LLMModelConfig

logger = logging.getLogger(__name__)

# 抑制 litellm 内部大量调试日志
litellm.suppress_debug_info = True


@dataclass
class LLMCallStats:
    """LLM 调用统计数据。

    Attributes:
        total_calls: 总调用次数。
        total_prompt_tokens: 总 prompt token 数。
        total_completion_tokens: 总 completion token 数。
        total_latency_ms: 总延迟（毫秒）。
        errors: 错误次数。
        cache_hits: 缓存命中次数。
    """

    total_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_latency_ms: float = 0.0
    errors: int = 0
    cache_hits: int = 0

    @property
    def avg_latency_ms(self) -> float:
        """平均延迟（毫秒）。"""
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_calls


@dataclass
class LLMResponse:
    """LLM 响应封装。

    Attributes:
        content: 响应文本内容。
        prompt_tokens: 输入 token 数。
        completion_tokens: 输出 token 数。
        latency_ms: 本次调用延迟（毫秒）。
        model: 实际使用的模型名。
        cache_hit: 是否为缓存命中。
    """

    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    model: str = ""
    cache_hit: bool = False


class LLMGateway:
    """LiteLLM 网关。

    封装 LiteLLM 调用，提供统一的模型路由、重试和统计功能。

    Attributes:
        stats: 调用统计数据。
        cost_tracker: 成本追踪器。
        prompt_cache: Prompt 缓存管理器。
    """

    def __init__(self, max_retries: int = 2, timeout: int = 30) -> None:
        self._max_retries = max_retries
        self._timeout = timeout
        self.stats = LLMCallStats()
        self._model_configs: dict[str, LLMModelConfig] = {}
        self.cost_tracker: CostTracker | None = None
        self.prompt_cache: PromptCacheManager | None = None

    def enable_cost_tracking(self) -> None:
        """启用成本追踪。"""
        from civsim.llm.cost_tracker import CostTracker
        self.cost_tracker = CostTracker()

    def enable_prompt_cache(self) -> None:
        """启用 Prompt 缓存。"""
        from civsim.llm.prompt_cache import PromptCacheManager
        self.prompt_cache = PromptCacheManager()

    def register_model(self, role: str, config: LLMModelConfig) -> None:
        """注册角色对应的模型配置。

        Args:
            role: 角色名（governor / leader / leader_opus）。
            config: 合并后的模型配置。
        """
        self._model_configs[role] = config

    def call(
        self,
        role: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """调用 LLM 模型。

        Args:
            role: 角色名，用于路由到对应模型。
            messages: OpenAI 格式的消息列表。
            temperature: 覆盖默认温度（可选）。
            max_tokens: 覆盖默认 max_tokens（可选）。

        Returns:
            LLM 响应对象。

        Raises:
            KeyError: 角色未注册。
            RuntimeError: 调用失败且重试耗尽。
        """
        if role not in self._model_configs:
            msg = f"未注册角色 '{role}' 的模型配置"
            raise KeyError(msg)

        config = self._model_configs[role]
        model_name = f"{config.provider}/{config.model}"
        temp = temperature if temperature is not None else config.temperature
        tokens = max_tokens if max_tokens is not None else config.max_tokens

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                start = time.monotonic()
                response = litellm.completion(
                    model=model_name,
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                    api_key=config.api_key,
                    api_base=config.base_url,
                    timeout=self._timeout,
                )
                elapsed_ms = (time.monotonic() - start) * 1000

                content = response.choices[0].message.content or ""
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0

                # 更新统计
                self.stats.total_calls += 1
                self.stats.total_prompt_tokens += prompt_tokens
                self.stats.total_completion_tokens += completion_tokens
                self.stats.total_latency_ms += elapsed_ms

                # 成本追踪
                if self.cost_tracker is not None:
                    self.cost_tracker.record_call(
                        model=model_name,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                    )

                return LLMResponse(
                    content=content,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=elapsed_ms,
                    model=model_name,
                )

            except Exception as e:
                last_error = e
                self.stats.errors += 1
                logger.warning(
                    "LLM 调用失败 (attempt %d/%d): %s",
                    attempt + 1,
                    self._max_retries + 1,
                    e,
                )
                if attempt < self._max_retries:
                    time.sleep(1.0 * (attempt + 1))

        msg = f"LLM 调用失败，已重试 {self._max_retries} 次: {last_error}"
        raise RuntimeError(msg)

    def call_json(
        self,
        role: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """调用 LLM 并解析 JSON 响应。

        Args:
            role: 角色名。
            messages: 消息列表。
            temperature: 覆盖温度。
            max_tokens: 覆盖 max_tokens。

        Returns:
            解析后的 JSON 字典。

        Raises:
            ValueError: JSON 解析失败。
        """
        response = self.call(role, messages, temperature, max_tokens)
        content = response.content.strip()

        # 尝试从 markdown 代码块中提取 JSON
        if content.startswith("```"):
            lines = content.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```") and not in_block:
                    in_block = True
                    continue
                if line.startswith("```") and in_block:
                    break
                if in_block:
                    json_lines.append(line)
            content = "\n".join(json_lines)

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            msg = f"LLM 返回的内容无法解析为 JSON: {e}\n原始内容: {content[:200]}"
            raise ValueError(msg) from e

    def call_with_cascade(
        self,
        messages: list[dict[str, str]],
        complexity_hint: str = "moderate",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """使用级联策略调用 LLM。

        根据 complexity_hint 自动选择模型：
        - simple → governor (Haiku)
        - moderate → leader (Sonnet)
        - complex → leader_opus (Opus)

        Args:
            messages: 消息列表。
            complexity_hint: 复杂度提示 (simple/moderate/complex)。
            temperature: 覆盖温度。
            max_tokens: 覆盖 max_tokens。

        Returns:
            LLM 响应对象。
        """
        role_map = {
            "simple": "governor",
            "moderate": "leader",
            "complex": "leader_opus",
        }
        role = role_map.get(complexity_hint, "leader")
        # 如果目标角色未注册，降级到已注册的角色
        if role not in self._model_configs:
            for fallback in ["leader", "governor", "leader_opus"]:
                if fallback in self._model_configs:
                    role = fallback
                    break
        return self.call(role, messages, temperature, max_tokens)

    def reset_stats(self) -> None:
        """重置调用统计。"""
        self.stats = LLMCallStats()
