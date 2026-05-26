from app.api import ai_intro_agent as intro_module


def test_order_entry_reply_for_ai_custom_uses_opening_question():
    reply = intro_module._build_order_entry_reply("ai_3d_custom", "意向AI驱动3D OOH内容定制")

    assert "这次大概想做什么样的内容" in reply
    assert "品牌或项目名称" not in reply
    assert "项目基础信息开始" not in reply


def test_order_entry_reply_for_orderable_businesses_do_not_force_first_field():
    for business_type in ["ai_3d_custom", "video_purchase", "digital_art"]:
        reply = intro_module._build_order_entry_reply(business_type)
        assert "品牌或项目名称" not in reply
        assert "请先告诉我" not in reply
        assert "这次" in reply
