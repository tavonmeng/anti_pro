import pytest

from app.services.ai_interaction import _interaction_messages, decide_interaction, normalize_interaction


def test_interaction_prompt_requires_one_answerable_task_and_finite_options():
    system = _interaction_messages(
        "这次主要面向哪类受众？",
        history=[],
        brief_state={},
    )[0]["content"]

    assert "只包含一个需要用户回答的任务" in system
    assert "不要只按问号数量判断" in system
    assert "选项为 2 至 5 个" in system
    assert "所有选项属于同一个回答维度" in system
    assert "用户只选择选项就能完整回答当前问题" in system
    assert "当前上下文、已提供的业务枚举或已有候选信息" in system
    assert "问题本身的真实答案空间已经封闭" in system
    assert "不能因为 assistant_reply 临时写成‘A 还是 B’" in system
    assert "连续使用选择题会让对话像填表" in system
    assert "options_exhaustive" in system
    assert "不能依赖‘其他’来弥补不完整候选" in system
    assert "五项必须全部为 true" in system
    assert "品牌营销节点还是城市地标焕新" in system
    assert "是否符合预期/是否准确" in system
    assert "field 返回 online_time，type 返回 date" in system
    assert "不要因为问题使用了‘大概什么时候’这种自然措辞而退回 text" in system
    assert "不要凭空创造创意方向" not in system
    assert "没有 Memory 也可以根据上下文生成合理选项" not in system


def test_normalize_choice_always_keeps_custom_answer():
    interaction = normalize_interaction(
        {
            "type": "single_choice",
            "field": "budget",
            "choice_eligibility": {
                "answer_space_closed": True,
                "options_exhaustive": True,
                "selection_fully_answers": True,
                "options_grounded": True,
                "materially_better_than_text": True,
            },
            "options": [
                {"label": "5-10 万", "value": "5-10万"},
                {"label": "10-20 万", "value": "10-20万"},
            ],
        },
        reply="预算范围大概是多少？",
    )

    assert interaction["type"] == "single_choice"
    assert len(interaction["options"]) == 2
    assert interaction["allow_other"] is True
    assert interaction["question_id"].startswith("question:")


def test_normalize_invalid_choice_falls_back_to_text_contract():
    assert normalize_interaction({"type": "single_choice", "options": []}) is None
    assert normalize_interaction({"type": "single_choice", "options": [{"label": "唯一选项"}]}) is None
    assert normalize_interaction(
        {
            "type": "single_choice",
            "choice_eligibility": {
                "answer_space_closed": True,
                "options_exhaustive": False,
                "selection_fully_answers": True,
                "options_grounded": True,
                "materially_better_than_text": True,
            },
            "options": [{"label": "A"}, {"label": "B"}],
        }
    ) is None
    assert normalize_interaction({"type": "unsupported"}) is None


def test_normalize_online_time_uses_date_affordance_even_when_model_returns_text():
    interaction = normalize_interaction(
        {
            "type": "text",
            "field": "online_time",
        },
        reply="您期望的预计上刊时间大概是什么时候？",
    )

    assert interaction["type"] == "date"
    assert interaction["field"] == "online_time"
    assert interaction["placeholder"] == "选择预计上刊日期"


@pytest.mark.asyncio
async def test_decide_interaction_uses_structured_llm_output(monkeypatch):
    async def fake_post(*args, **kwargs):
        return {
            "choices": [{"message": {"content": '{"type":"text","field":"theme_concept"}'}}]
        }

    monkeypatch.setattr("app.services.ai_interaction.post_chat_completion", fake_post)
    result = await decide_interaction(
        reply="请描述一下这次项目的主题。",
        history=[],
        brief_state={},
        model="test-model",
        timeout=8,
    )

    assert result is not None
    assert result["type"] == "text"
    assert result["field"] == "theme_concept"
    assert result["question_id"].startswith("question:")
