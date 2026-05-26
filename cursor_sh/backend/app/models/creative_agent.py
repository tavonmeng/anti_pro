"""创意 Agent 工作台数据模型。

该模块只保存创意工作台自己的会话、运行、方案和评估结果。
订单信息仅以 source_order_id 形式只读引用，避免 Agent 流程修改订单状态。
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.utils.validators import generate_id


class CreativeSession(Base):
    """创意工作台会话。"""

    __tablename__ = "creative_sessions"

    id = Column(String(50), primary_key=True, index=True, default=lambda: generate_id("crs"))
    title = Column(String(200), nullable=False, default="")
    created_by_id = Column(String(50), nullable=False, index=True)
    created_by_name = Column(String(100), nullable=True)
    visibility = Column(String(20), nullable=False, default="team", index=True)  # team / private

    source_type = Column(String(30), nullable=False, default="manual", index=True)  # manual / order
    source_order_id = Column(String(50), nullable=True, index=True)
    customer_user_id = Column(String(50), nullable=True, index=True)

    brief_json = Column(JSON, default=dict)
    designer_direction = Column(Text, default="")
    seed_ideas = Column(JSON, default=list)
    status = Column(String(30), nullable=False, default="draft", index=True)
    selected_idea_id = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    ideas = relationship("CreativeIdea", back_populates="session", cascade="all, delete-orphan", lazy="selectin")
    runs = relationship("CreativeRun", back_populates="session", cascade="all, delete-orphan", lazy="selectin")
    iterations = relationship("CreativeIteration", back_populates="session", cascade="all, delete-orphan", lazy="selectin")
    agent_steps = relationship("CreativeAgentStep", back_populates="session", cascade="all, delete-orphan", lazy="selectin")
    feedbacks = relationship("CreativeDesignerFeedback", back_populates="session", cascade="all, delete-orphan", lazy="selectin")


class CreativeIdea(Base):
    """Agent 或人工生成的创意版本。"""

    __tablename__ = "creative_ideas"

    id = Column(String(50), primary_key=True, index=True, default=lambda: generate_id("cri"))
    session_id = Column(String(50), ForeignKey("creative_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(String(50), nullable=True, index=True)
    run_id = Column(String(50), nullable=True, index=True)

    version = Column(Integer, nullable=False, default=1)
    title = Column(String(200), nullable=False, default="")
    core_concept = Column(Text, default="")
    spatial_mechanism = Column(Text, default="")
    story_outline = Column(Text, default="")
    production_notes = Column(Text, default="")
    risk_notes = Column(Text, default="")
    tags = Column(JSON, default=list)

    status = Column(String(30), nullable=False, default="proposed", index=True)
    score = Column(Integer, nullable=True, index=True)
    created_by_role = Column(String(30), nullable=False, default="agent")  # agent / user

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    session = relationship("CreativeSession", back_populates="ideas")
    reviews = relationship("CreativeReview", back_populates="idea", cascade="all, delete-orphan", lazy="selectin")


class CreativeReview(Base):
    """创意质检评分结果。"""

    __tablename__ = "creative_reviews"

    id = Column(String(50), primary_key=True, index=True, default=lambda: generate_id("crr"))
    idea_id = Column(String(50), ForeignKey("creative_ideas.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String(50), nullable=True, index=True)

    rubric_version = Column(String(50), nullable=False, default="creative_qc_v1")
    scores_json = Column(JSON, default=dict)
    total_score = Column(Integer, nullable=False, default=0, index=True)
    grade = Column(String(30), nullable=True)
    core_issues = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    risk_flags = Column(JSON, default=list)
    summary = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    idea = relationship("CreativeIdea", back_populates="reviews")


class CreativeRun(Base):
    """一次 Hermes 创意 Agent 运行。"""

    __tablename__ = "creative_runs"

    id = Column(String(50), primary_key=True, index=True, default=lambda: generate_id("crun"))
    session_id = Column(String(50), ForeignKey("creative_sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    run_type = Column(String(30), nullable=False, default="auto_optimize", index=True)
    status = Column(String(30), nullable=False, default="queued", index=True)
    provider = Column(String(30), nullable=False, default="hermes")

    hermes_run_id = Column(String(100), nullable=True, index=True)
    hermes_session_id = Column(String(100), nullable=True, index=True)
    previous_response_id = Column(String(100), nullable=True)

    input_json = Column(JSON, default=dict)
    output_json = Column(JSON, default=dict)
    error = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    session = relationship("CreativeSession", back_populates="runs")
    events = relationship("CreativeRunEvent", back_populates="run", cascade="all, delete-orphan", lazy="selectin")
    iterations = relationship("CreativeIteration", back_populates="run", cascade="all, delete-orphan", lazy="selectin")
    agent_steps = relationship("CreativeAgentStep", back_populates="run", cascade="all, delete-orphan", lazy="selectin")
    feedbacks = relationship("CreativeDesignerFeedback", back_populates="run", cascade="all, delete-orphan", lazy="selectin")


class CreativeRunEvent(Base):
    """Hermes 运行事件快照。

    用于让管理端看到 Agent 的运行轨迹：启动、工具进度、状态刷新、解析入库、错误等。
    """

    __tablename__ = "creative_run_events"

    id = Column(String(50), primary_key=True, index=True, default=lambda: generate_id("cre"))
    run_id = Column(String(50), ForeignKey("creative_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    sequence = Column(Integer, nullable=False, default=1)
    event_type = Column(String(60), nullable=False, index=True)
    message = Column(Text, default="")
    payload_json = Column(JSON, default=dict)
    source = Column(String(30), nullable=False, default="backend")  # backend / hermes

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    run = relationship("CreativeRun", back_populates="events")


class CreativeAgentStep(Base):
    """可展示的 ReAct-style 审计步骤。

    这里保存的是面向用户的推理摘要，不保存模型隐藏思考链。
    """

    __tablename__ = "creative_agent_steps"

    id = Column(String(50), primary_key=True, index=True, default=lambda: generate_id("cas"))
    session_id = Column(String(50), ForeignKey("creative_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String(50), ForeignKey("creative_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_index = Column(Integer, nullable=False, default=1, index=True)
    phase = Column(String(30), nullable=False, default="action", index=True)  # plan / action / observation / reflection / decision
    role = Column(String(60), nullable=False, default="")
    tool_name = Column(String(100), nullable=False, default="")
    input_summary = Column(Text, default="")
    output_summary = Column(Text, default="")
    observation = Column(Text, default="")
    reflection_summary = Column(Text, default="")
    decision = Column(Text, default="")
    next_action = Column(Text, default="")
    score_snapshot = Column(JSON, default=dict)
    dimension_deltas = Column(JSON, default=list)
    payload_json = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("CreativeSession", back_populates="agent_steps")
    run = relationship("CreativeRun", back_populates="agent_steps")


class CreativeIteration(Base):
    """自动优化过程中的一轮迭代记录。"""

    __tablename__ = "creative_iterations"

    id = Column(String(50), primary_key=True, index=True, default=lambda: generate_id("cit"))
    session_id = Column(String(50), ForeignKey("creative_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String(50), ForeignKey("creative_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    round_index = Column(Integer, nullable=False, default=1, index=True)
    action = Column(String(80), nullable=False, default="")
    score_before = Column(Integer, nullable=True)
    score_after = Column(Integer, nullable=True)
    score_delta = Column(Integer, nullable=True)
    focus = Column(Text, default="")
    summary = Column(Text, default="")
    agent_explanation = Column(Text, default="")
    dimension_deltas = Column(JSON, default=list)
    key_improvements = Column(JSON, default=list)
    payload_json = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("CreativeSession", back_populates="iterations")
    run = relationship("CreativeRun", back_populates="iterations")


class CreativeDesignerFeedback(Base):
    """设计师在 Agent 迭代中途或结束后的人工反馈。"""

    __tablename__ = "creative_designer_feedbacks"

    id = Column(String(50), primary_key=True, index=True, default=lambda: generate_id("cdf"))
    session_id = Column(String(50), ForeignKey("creative_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String(50), ForeignKey("creative_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    target_idea_id = Column(String(50), nullable=True, index=True)
    feedback_text = Column(Text, nullable=False)
    priority = Column(String(30), nullable=False, default="normal")  # low / normal / high
    constraints = Column(JSON, default=list)
    liked_parts = Column(JSON, default=list)
    disliked_parts = Column(JSON, default=list)
    requested_changes = Column(JSON, default=list)
    status = Column(String(30), nullable=False, default="submitted", index=True)
    created_by_id = Column(String(50), nullable=False, default="")
    created_by_name = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    session = relationship("CreativeSession", back_populates="feedbacks")
    run = relationship("CreativeRun", back_populates="feedbacks")


class CreativeMemoryEntry(Base):
    """创意团队沉淀的可复用经验。

    scope=team 表示团队共享；scope=personal 表示某个成员自己的偏好或素材笔记。
    """

    __tablename__ = "creative_memory_entries"

    id = Column(String(50), primary_key=True, index=True, default=lambda: generate_id("crm"))
    scope = Column(String(20), nullable=False, default="team", index=True)  # team / personal / project
    owner_id = Column(String(50), nullable=True, index=True)
    kind = Column(String(50), nullable=False, default="principle", index=True)
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=list)
    status = Column(String(30), nullable=False, default="approved", index=True)  # approved / proposed / archived
    created_by_id = Column(String(50), nullable=False, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
