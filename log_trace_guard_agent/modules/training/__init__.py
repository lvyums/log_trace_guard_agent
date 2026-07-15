"""模块五：交互式攻防实训模块"""

from modules.training.check_strategy import CheckStrategyFactory
from modules.training.check_strategy import (
    ConclusionCheckStrategy,
    RuleCheckStrategy,
    ScriptCheckStrategy,
    PlanCheckStrategy,
)

# 注册所有校验策略
CheckStrategyFactory.register("conclusion", ConclusionCheckStrategy)
CheckStrategyFactory.register("rule", RuleCheckStrategy)
CheckStrategyFactory.register("script", ScriptCheckStrategy)
CheckStrategyFactory.register("plan", PlanCheckStrategy)