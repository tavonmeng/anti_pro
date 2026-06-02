from app.services.memory_sanitizer import (
    sanitize_agent_notes,
    sanitize_document_memory_data,
    sanitize_screen_resources,
)
from app.services.memory_merge_service import merge_document_knowledge


def test_sanitize_document_memory_data_removes_price_fields_and_source_filename():
    data = {
        "screen_resources": [
            {
                "name": "合肥天幕",
                "play_frequency": "15s/60次/天",
                "list_price": "300000元/周",
                "notes": "投放规则需确认；制作费 5万元；日媒体接触人次 100万人次/天",
                "source": {"filename": "2511合肥天幕资源介绍汇总.pdf", "page": "3"},
            }
        ],
        "important_notes": [
            {"note": "刊例价 300000元/周，播放时间 10:00-23:00"},
        ],
    }

    sanitized = sanitize_document_memory_data(data)
    screen = sanitized["screen_resources"][0]

    assert "list_price" not in screen
    assert "filename" not in screen["source"]
    assert screen["source"]["page"] == "3"
    assert screen["play_frequency"] == "15s/60次/天"
    assert "制作费" not in screen["notes"]
    assert "100万人次/天" in screen["notes"]
    assert "刊例价" not in str(sanitized)
    assert "300000" not in str(sanitized)


def test_sanitize_agent_notes_normalizes_document_title_and_keeps_non_amount_budget_note():
    notes = """
【客户资料导入备注 - 2511合肥天幕资源介绍汇总.pdf】
- 预算待确认
- 报价 30万元，需内部确认
- 资源适合节庆主题
"""

    sanitized = sanitize_agent_notes(notes)

    assert "2511合肥天幕资源介绍汇总.pdf" not in sanitized
    assert "【客户资料导入备注】" in sanitized
    assert "预算待确认" in sanitized
    assert "报价" not in sanitized
    assert "30万" not in sanitized
    assert "资源适合节庆主题" in sanitized


def test_sanitize_screen_resources_drops_empty_price_only_items():
    sanitized = sanitize_screen_resources([
        {"list_price": "20万元/周"},
        {"name": "银泰中心北侧", "daily_traffic": "100万人次/天"},
    ])

    assert sanitized == [{"name": "银泰中心北侧", "daily_traffic": "100万人次/天"}]


def test_merge_document_knowledge_omits_source_filename_and_price_notes():
    class Memory:
        company_info = {}
        screen_resources = []
        agent_notes = ""

    updates = merge_document_knowledge(
        Memory(),
        {
            "screen_resources": [
                {
                    "city": "合肥",
                    "name": "银泰中心北侧",
                    "list_price": "300000元/周",
                    "source": {"filename": "2511合肥天幕资源介绍汇总.pdf", "page": "5"},
                }
            ],
            "important_notes": [
                {"note": "制作费 5万元，资源适合节庆主题"},
            ],
        },
        {"document_id": "doc-1", "filename": "2511合肥天幕资源介绍汇总.pdf"},
    )

    assert "2511合肥天幕资源介绍汇总.pdf" not in updates["agent_notes"]
    assert "客户资料导入备注 -" not in updates["agent_notes"]
    assert "制作费" not in updates["agent_notes"]
    assert "5万" not in updates["agent_notes"]
    assert "list_price" not in updates["screen_resources"][0]
    assert "filename" not in updates["screen_resources"][0]["source"]
    assert updates["screen_resources"][0]["source"]["document_id"] == "doc-1"
