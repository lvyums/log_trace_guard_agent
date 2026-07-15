"""模块五：交互式攻防实训模块 — 请求/响应 Pydantic Schema"""

from pydantic import BaseModel, Field
from typing import Optional


# ── 任务下发 ──

class TaskItem(BaseModel):
    """单个任务项"""
    task_id: str = Field(default="", description="任务ID")
    order: int = Field(default=0, description="任务顺序")
    title: str = Field(default="", description="任务标题")
    description: str = Field(default="", description="任务描述")
    input_type: str = Field(default="", description="输入类型")
    input_data: list[str] = Field(default_factory=list, description="输入数据")
    submit_type: str = Field(default="", description="提交类型")
    hint: Optional[str] = Field(default=None, description="提示信息")


class ScenarioInfo(BaseModel):
    """场景信息"""
    scenario_id: str = Field(default="", description="场景ID")
    name: str = Field(default="", description="场景名称")
    category: str = Field(default="", description="场景分类")
    difficulty: str = Field(default="", description="难度")
    order: int = Field(default=0, description="排序")
    description: str = Field(default="", description="场景描述")
    objectives: list[str] = Field(default_factory=list, description="学习目标")


class TaskInfo(BaseModel):
    """任务信息（含场景信息）"""
    scenario: ScenarioInfo = Field(default_factory=ScenarioInfo, description="场景信息")
    tasks: list[TaskItem] = Field(default_factory=list, description="任务列表")
    total_tasks: int = Field(default=0, description="任务总数")
    completed_tasks: int = Field(default=0, description="已完成任务数")


class TaskDispatchReq(BaseModel):
    """任务下发请求"""
    scenario_id: Optional[str] = Field(default=None, max_length=50, description="场景ID（可选，不指定则返回所有场景）")
    category: Optional[str] = Field(default=None, max_length=50, description="分类筛选")


class TaskDispatchResp(BaseModel):
    """任务下发响应"""
    scenarios: list[TaskInfo] = Field(default_factory=list, description="场景列表")
    total: int = Field(default=0, description="总场景数")


# ── 学员提交与校验 ──

class SubmitAnswerReq(BaseModel):
    """学员提交答案请求"""
    scenario_id: str = Field(..., max_length=50, description="场景ID")
    task_id: str = Field(..., max_length=50, description="任务ID")
    submit_type: str = Field(default="conclusion", pattern="^(rule|script|conclusion|plan)$", description="提交类型")
    content: dict = Field(default_factory=dict, description="提交内容，JSON对象格式")
    student_id: Optional[str] = Field(default=None, max_length=100, description="学员标识")


class CheckResult(BaseModel):
    """单条检查结果"""
    field: str = Field(default="", description="检查字段")
    status: str = Field(default="", description="检查状态：correct/partial/incorrect")
    expected: Optional[str] = Field(default=None, description="期望值")
    actual: Optional[str] = Field(default=None, description="实际值")
    detail: Optional[str] = Field(default=None, description="详细说明")


class SubmitAnswerResp(BaseModel):
    """提交答案校验响应"""
    task_id: str = Field(default="", description="任务ID")
    scenario_id: str = Field(default="", description="场景ID")
    score: int = Field(default=0, ge=0, le=100, description="得分 0-100")
    grade: str = Field(default="", description="等级：A(≥90)/B(70-89)/C(<70)")
    status: str = Field(default="", description="校验状态：passed/optimize/retry")
    checks: list[CheckResult] = Field(default_factory=list, description="逐项检查结果")
    analysis: str = Field(default="", description="错误分析与原理讲解")
    suggestion: Optional[str] = Field(default=None, description="优化建议")
    correct_answer: Optional[dict] = Field(default=None, description="标准答案（仅C等级展示）")


# ── 实训报告 ──

class TaskRecord(BaseModel):
    """单条任务记录"""
    task_id: str = Field(default="", description="任务ID")
    title: str = Field(default="", description="任务标题")
    score: int = Field(default=0, description="得分")
    grade: str = Field(default="", description="等级")
    attempts: int = Field(default=1, description="尝试次数")
    status: str = Field(default="", description="状态")


class WeaknessItem(BaseModel):
    """薄弱项"""
    category: str = Field(default="", description="薄弱类型")
    description: str = Field(default="", description="描述")
    score: int = Field(default=0, description="得分")
    suggestion: str = Field(default="", description="提升建议")


class ReportReq(BaseModel):
    """实训报告请求"""
    student_id: Optional[str] = Field(default=None, max_length=100, description="学员标识")
    scenario_id: Optional[str] = Field(default=None, max_length=50, description="场景ID（可选）")


class ReportResp(BaseModel):
    """实训报告响应"""
    student_id: Optional[str] = Field(default=None, description="学员标识")
    scenario_name: Optional[str] = Field(default=None, description="场景名称")
    total_tasks: int = Field(default=0, description="总任务数")
    completed_tasks: int = Field(default=0, description="已完成数")
    average_score: float = Field(default=0.0, description="平均分")
    overall_grade: str = Field(default="", description="综合评级")
    task_records: list[TaskRecord] = Field(default_factory=list, description="任务记录")
    weaknesses: list[WeaknessItem] = Field(default_factory=list, description="薄弱项分析")
    improvement_plan: str = Field(default="", description="能力提升方案")
    summary: str = Field(default="", description="实训总结")