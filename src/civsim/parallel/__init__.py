"""并行执行模块。

提供 SDCA（Snapshot → Dispatch → Collect → Apply）模式的分布式执行支持。
当 Ray 不可用时自动降级为本地串行执行。
"""
