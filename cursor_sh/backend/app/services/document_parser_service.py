"""客户资料解析服务。

MVP 支持可提取文本的 PDF / DOCX / PPTX，不做 OCR。
"""

import os
from dataclasses import dataclass


class DocumentParseError(Exception):
    """文档解析失败。"""


@dataclass
class ParsedSection:
    label: str
    page: int | None
    text: str


MAX_SECTION_CHARS = 3500
MAX_TOTAL_CHARS = 60000


def parse_document(file_path: str, filename: str = "") -> list[ParsedSection]:
    """解析文档文本并保留页码/幻灯片编号。"""
    ext = os.path.splitext(filename or file_path)[1].lower()
    if ext == ".pdf":
        return _parse_pdf(file_path)
    if ext == ".docx":
        return _parse_docx(file_path)
    if ext == ".pptx":
        return _parse_pptx(file_path)
    raise DocumentParseError(f"不支持的文件类型: {ext}")


def build_llm_text(sections: list[ParsedSection]) -> str:
    """构建带来源标记的 LLM 输入文本。"""
    parts = []
    total = 0
    for section in sections:
        text = _clean_text(section.text)
        if not text:
            continue
        if len(text) > MAX_SECTION_CHARS:
            text = text[:MAX_SECTION_CHARS] + "\n...(本页内容已截断)"
        block = f"【来源：{section.label}】\n{text}"
        if total + len(block) > MAX_TOTAL_CHARS:
            break
        parts.append(block)
        total += len(block)
    return "\n\n".join(parts)


def _parse_pdf(file_path: str) -> list[ParsedSection]:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise DocumentParseError("缺少 PDF 解析依赖 pypdf，请安装 requirements.txt") from exc

    try:
        reader = PdfReader(file_path)
        sections = []
        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            sections.append(ParsedSection(label=f"第{idx}页", page=idx, text=text))
        return sections
    except Exception as exc:
        raise DocumentParseError(f"PDF 解析失败: {exc}") from exc


def _parse_docx(file_path: str) -> list[ParsedSection]:
    try:
        from docx import Document
    except Exception as exc:
        raise DocumentParseError("缺少 Word 解析依赖 python-docx，请安装 requirements.txt") from exc

    try:
        doc = Document(file_path)
        lines = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    lines.append(" | ".join(cells))
        return [ParsedSection(label="Word正文", page=None, text="\n".join(lines))]
    except Exception as exc:
        raise DocumentParseError(f"Word 解析失败: {exc}") from exc


def _parse_pptx(file_path: str) -> list[ParsedSection]:
    try:
        from pptx import Presentation
    except Exception as exc:
        raise DocumentParseError("缺少 PPT 解析依赖 python-pptx，请安装 requirements.txt") from exc

    try:
        prs = Presentation(file_path)
        sections = []
        for idx, slide in enumerate(prs.slides, start=1):
            lines = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text and shape.text.strip():
                    lines.append(shape.text.strip())
                if getattr(shape, "has_table", False):
                    for row in shape.table.rows:
                        cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if cells:
                            lines.append(" | ".join(cells))
            sections.append(ParsedSection(label=f"第{idx}页幻灯片", page=idx, text="\n".join(lines)))
        return sections
    except Exception as exc:
        raise DocumentParseError(f"PPT 解析失败: {exc}") from exc


def _clean_text(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines()]
    return "\n".join(line for line in lines if line)
