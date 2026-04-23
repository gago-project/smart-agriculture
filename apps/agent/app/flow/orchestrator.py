"""土壤墒情 Agent 流程编排入口。

本模块提供 `SoilMoistureFlowOrchestrator`：将各业务节点实例与静态路由表 `ROUTES`
绑定到通用 `FlowRunner`，固定入口节点、终止状态集合与兜底节点名称，
从而在「受限有向图」上驱动一次完整的对话/推理流水线。
"""

from __future__ import annotations


from app.flow.runner import FlowRunner, RouteRegistry
from app.flow.routes import ROUTES
from app.flow.nodes import (
    AdviceComposeNode,
    AnswerVerifyNode,
    ConversationBoundaryNode,
    DataFactCheckNode,
    ExecutionGateNode,
    FallbackGuardNode,
    HistoryContextMergeNode,
    InputGuardNode,
    IntentSlotExtractNode,
    RegionResolveNode,
    ResponseGenerateNode,
    SoilDataQueryNode,
    SoilRuleEngineNode,
    TemplateRenderNode,
    TimeResolveNode,
)


class SoilMoistureFlowOrchestrator:
    """土壤墒情场景的流程编排器（对 `FlowRunner` 的薄封装）。

    职责：用方案中约定的入口（`input_guard`）、多种正常/异常结束态（如
    `safe_end`、`clarify_end`、`fallback_end` 等）以及兜底节点 `fallback_guard`，
    构造一个已配置好的 `FlowRunner`。外部只需传入「节点名 → 节点实例」映射
    与可选的调试服务，即可按路由表逐步执行图上的节点逻辑。
    """

    def __init__(self, *, nodes: dict[str, object], debug_service=None):
        """初始化内部 `FlowRunner`。

        Args:
            nodes: 节点注册表，键为节点名称（与 `ROUTES` 中引用一致），值为可调用节点实例。
            debug_service: 可选调试/观测服务，透传给 `FlowRunner`（如记录每步状态）。
        """
        self.runner = FlowRunner(
            nodes=nodes,
            routes=RouteRegistry(ROUTES),
            entrypoint="input_guard",
            terminals={"safe_end", "clarify_end", "boundary_end", "closing_end", "block_end", "verified_end", "fallback_end"},
            fallback_node_name="fallback_guard",
            debug_service=debug_service,
        )

    async def run(self, state):
        """从当前 `FlowState` 出发，沿静态路由执行整条流程直至终止或兜底。

        由 `FlowRunner` 根据 `ROUTES` 与节点返回值决定下一跳；命中任一终止态
        或需走兜底时结束。返回值为更新后的状态（具体结构由 `FlowState` 定义）。
        """
        return await self.runner.run(state)
