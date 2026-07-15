"""模块二：合规审计基线模块"""

from modules.compliance.compliance_rule import ComplianceStrategyFactory
from modules.compliance.compliance_rule import ComplianceQAStrategy
from modules.compliance.baseline_gen import BaselineGenStrategy
from modules.compliance.baseline_gen import ComplianceCheckStrategy

# 注册所有策略
ComplianceStrategyFactory.register("qa", ComplianceQAStrategy)
ComplianceStrategyFactory.register("baseline_gen", BaselineGenStrategy)
ComplianceStrategyFactory.register("check", ComplianceCheckStrategy)