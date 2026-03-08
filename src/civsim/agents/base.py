"""Agent 基类。

为所有 CivSim Agent 提供通用属性和接口。
继承自 Mesa Agent，添加 CivSim 特有的通用字段。
"""

import mesa


class BaseAgent(mesa.Agent):
    """CivSim Agent 基类。

    所有 Agent（平民、镇长、首领）都继承此类。

    Attributes:
        home_settlement_id: 所属聚落 ID。
    """

    def __init__(self, model: mesa.Model, home_settlement_id: int = 0) -> None:
        super().__init__(model)
        self.home_settlement_id = home_settlement_id

    def step(self) -> None:
        """每 tick 执行的行为，子类必须重写。"""
        raise NotImplementedError
