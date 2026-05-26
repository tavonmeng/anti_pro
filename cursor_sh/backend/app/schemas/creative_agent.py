"""创意 Agent 工作台 API schema。"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class CreativeSessionCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    visibility: Literal["team", "private"] = "team"
    source_type: Literal["manual", "order"] = "manual"
    source_order_id: Optional[str] = Field(default=None, max_length=50)
    customer_user_id: Optional[str] = Field(default=None, max_length=50)
    brief: dict[str, Any] = Field(default_factory=dict)
    designer_direction: str = ""
    seed_ideas: list[dict[str, Any]] = Field(default_factory=list)


class CreativeSessionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    visibility: Optional[Literal["team", "private"]] = None
    brief: Optional[dict[str, Any]] = None
    designer_direction: Optional[str] = None
    seed_ideas: Optional[list[dict[str, Any]]] = None
    selected_idea_id: Optional[str] = Field(default=None, max_length=50)


class CreativeAutoRunRequest(BaseModel):
    max_rounds: int = Field(default=4, ge=1, le=8)
    target_score: int = Field(default=85, ge=0, le=100)
    idea_count: int = Field(default=3, ge=1, le=5)
    strategy: Literal["balanced", "bold", "safe", "low_cost", "viral"] = "balanced"
    use_parallel_evaluators: bool = True
    use_team_memory: bool = True
    use_personal_memory: bool = True
    save_memory_candidates: bool = True
    wait_for_completion: bool = False
    hard_constraints: list[str] = Field(default_factory=list)
    reference_cases: list[dict[str, Any]] = Field(default_factory=list)
    negative_examples: list[str] = Field(default_factory=list)
    designer_direction: str = ""
    seed_ideas: list[dict[str, Any]] = Field(default_factory=list)


class CreativeIdeaCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    core_concept: str = ""
    spatial_mechanism: str = ""
    story_outline: str = ""
    production_notes: str = ""
    risk_notes: str = ""
    tags: list[str] = Field(default_factory=list)


class CreativeIdeaRunRequest(BaseModel):
    max_rounds: int = Field(default=2, ge=1, le=5)
    target_score: int = Field(default=85, ge=0, le=100)
    use_parallel_evaluators: bool = True
    use_team_memory: bool = True
    use_personal_memory: bool = True
    save_memory_candidates: bool = True
    wait_for_completion: bool = False
    focus: str = ""
    designer_direction: str = ""


class CreativeDesignerFeedbackCreate(BaseModel):
    target_idea_id: Optional[str] = Field(default=None, max_length=50)
    run_id: Optional[str] = Field(default=None, max_length=50)
    feedback_text: str = Field(min_length=1)
    priority: Literal["low", "normal", "high"] = "normal"
    constraints: list[str] = Field(default_factory=list)
    liked_parts: list[str] = Field(default_factory=list)
    disliked_parts: list[str] = Field(default_factory=list)
    requested_changes: list[str] = Field(default_factory=list)


class CreativeContinueRunRequest(BaseModel):
    feedback_id: Optional[str] = Field(default=None, max_length=50)
    target_idea_id: Optional[str] = Field(default=None, max_length=50)
    feedback_text: str = ""
    priority: Literal["low", "normal", "high"] = "normal"
    constraints: list[str] = Field(default_factory=list)
    liked_parts: list[str] = Field(default_factory=list)
    disliked_parts: list[str] = Field(default_factory=list)
    requested_changes: list[str] = Field(default_factory=list)
    max_rounds: int = Field(default=2, ge=1, le=5)
    target_score: int = Field(default=85, ge=0, le=100)
    use_parallel_evaluators: bool = True
    use_team_memory: bool = True
    use_personal_memory: bool = True
    save_memory_candidates: bool = True
    wait_for_completion: bool = False


class CreativeMemoryCreate(BaseModel):
    scope: Literal["team", "personal", "project"] = "team"
    kind: str = Field(default="principle", max_length=50)
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    status: Literal["approved", "proposed"] = "approved"


class CreativeMemoryUpdate(BaseModel):
    kind: Optional[str] = Field(default=None, max_length=50)
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[Literal["approved", "proposed", "archived"]] = None
