"""Reusable opening copy for external AI agents."""

from __future__ import annotations


def build_ai_3d_custom_brief_opening(prefix: str = "好的。") -> str:
    normalized_prefix = (prefix or "").strip()
    if normalized_prefix and not normalized_prefix.endswith(("。", "！", "？", "\n")):
        normalized_prefix += "。"
    leading = f"{normalized_prefix}\n\n" if normalized_prefix else ""
    return (
        f"{leading}"
        "**裸眼3D视频**和普通平面视频不太一样，它要同时考虑"
        "**屏幕结构、观看动线、现场空间，以及出屏/入屏视觉机制**；"
        "这些条件会直接影响创意是否成立、制作难度和最终播放效果。\n\n"
        "所以前期我会先用轻量对话把 Brief 梳理清楚，不需要您一次准备完整资料。"
        "我们会结合项目背景、投放场景和大概目标，围绕三个维度慢慢收拢："
        "**基础信息、创意方向以及技术与交付**。\n\n"
        "您可以先简单说说，这次大概想做什么样的内容？"
    )
