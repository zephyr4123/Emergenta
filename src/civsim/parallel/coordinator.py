"""并行协调器。

管理 Ray Worker 池，实现 SDCA 完整流程。
Ray 不可用时自动降级为本地串行执行。
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor
from typing import TYPE_CHECKING

from civsim.parallel.snapshots import (
    AgentSnapshot,
    EnvironmentSnapshot,
    StepResult,
    create_agent_snapshots_batch,
    create_environment_snapshot,
)
from civsim.parallel.worker import process_batch

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _is_ray_available() -> bool:
    """检查 Ray 是否可用且已初始化。"""
    try:
        import ray
        return ray.is_initialized()
    except ImportError:
        return False


def _init_ray(num_cpus: int | None = None, object_store_mb: int = 200) -> bool:
    """尝试初始化 Ray。

    Args:
        num_cpus: CPU 核数限制。
        object_store_mb: Object Store 大小（MB）。

    Returns:
        是否初始化成功。
    """
    try:
        import ray
        if not ray.is_initialized():
            ray.init(
                num_cpus=num_cpus,
                object_store_memory=object_store_mb * 1024 * 1024,
                log_to_driver=False,
                ignore_reinit_error=True,
            )
        return True
    except Exception as e:
        logger.warning("Ray 初始化失败: %s，将使用本地执行", e)
        return False


class ParallelCoordinator:
    """并行执行协调器。

    管理 SDCA 流程：Snapshot → Dispatch → Collect → Apply。
    支持 Ray 并行和本地串行两种模式。

    Attributes:
        num_workers: Worker 数量。
        batch_size: 每个 Worker 处理的 Agent 批次大小。
        use_ray: 是否使用 Ray。
    """

    def __init__(
        self,
        num_workers: int = 4,
        batch_size: int = 100,
        enable_ray: bool = False,
        object_store_mb: int = 200,
    ) -> None:
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.use_ray = False
        self._ray_process_batch = None

        if enable_ray:
            self.use_ray = _init_ray(num_cpus=num_workers, object_store_mb=object_store_mb)
            if self.use_ray:
                import ray
                self._ray_process_batch = ray.remote(process_batch)
                logger.info("并行协调器已启用 Ray（%d workers）", num_workers)
            else:
                logger.info("并行协调器降级为本地执行")
        else:
            logger.info("并行协调器使用本地串行执行")

    def execute_parallel_step(
        self,
        engine: object,
        civilians: list[object],
    ) -> list[StepResult]:
        """执行一个 tick 的并行 step。

        SDCA 完整流程：
        1. Snapshot: 创建环境和 Agent 快照
        2. Dispatch: 分批分发给 Worker
        3. Collect: 收集计算结果
        4. 返回结果（Apply 由调用方完成）

        Args:
            engine: CivilizationEngine 实例。
            civilians: Civilian Agent 列表。

        Returns:
            所有平民的 StepResult 列表。
        """
        if not civilians:
            return []

        # 1. Snapshot
        env_snapshot = create_environment_snapshot(engine)
        agent_snapshots = create_agent_snapshots_batch(engine, civilians)

        tick_seed = 0
        if hasattr(engine, "clock"):
            tick_seed = engine.clock.tick

        # 2. Dispatch + 3. Collect
        if self.use_ray:
            return self._execute_ray(agent_snapshots, env_snapshot, tick_seed)
        return self._execute_local(agent_snapshots, env_snapshot, tick_seed)

    def _split_batches(
        self, agents: list[AgentSnapshot],
    ) -> list[list[AgentSnapshot]]:
        """将 Agent 列表分成批次。"""
        batches: list[list[AgentSnapshot]] = []
        for i in range(0, len(agents), self.batch_size):
            batches.append(agents[i:i + self.batch_size])
        return batches

    def _execute_ray(
        self,
        agents: list[AgentSnapshot],
        env: EnvironmentSnapshot,
        tick_seed: int,
    ) -> list[StepResult]:
        """使用 Ray 并行执行。"""
        import ray

        batches = self._split_batches(agents)
        env_ref = ray.put(env)

        futures = []
        for batch in batches:
            future = self._ray_process_batch.remote(batch, env_ref, tick_seed)
            futures.append(future)

        batch_results = ray.get(futures)
        results: list[StepResult] = []
        for batch_result in batch_results:
            results.extend(batch_result)
        return results

    def _execute_local(
        self,
        agents: list[AgentSnapshot],
        env: EnvironmentSnapshot,
        tick_seed: int,
    ) -> list[StepResult]:
        """本地串行执行。"""
        return process_batch(agents, env, tick_seed)

    def shutdown(self) -> None:
        """清理资源。"""
        if self.use_ray:
            try:
                import ray
                if ray.is_initialized():
                    ray.shutdown()
                    logger.info("Ray 已关闭")
            except Exception as e:
                logger.warning("Ray 关闭失败: %s", e)
        self.use_ray = False
