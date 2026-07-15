"""模块四：技术赋能脚本生成模块"""

from modules.script_gen.script_strategy import ScriptStrategyFactory
from modules.script_gen.regex_gen import RegexGenStrategy
from modules.script_gen.es_sql_gen import ESQueryGenStrategy
from modules.script_gen.platform_choose import PlatformChooseStrategy
from modules.script_gen.trace_link import TraceLinkStrategy

# 注册所有策略
ScriptStrategyFactory.register("regex", RegexGenStrategy)
ScriptStrategyFactory.register("es_query", ESQueryGenStrategy)
ScriptStrategyFactory.register("platform", PlatformChooseStrategy)
ScriptStrategyFactory.register("trace", TraceLinkStrategy)