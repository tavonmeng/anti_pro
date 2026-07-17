from types import SimpleNamespace

import pytest

from app.services import document_parser_service as parser


def test_parse_legacy_doc_uses_antiword_with_utf8_mapping(monkeypatch, tmp_path):
    doc_path = tmp_path / "legacy.doc"
    doc_path.write_bytes(b"mock-legacy-doc")
    captured = {}

    def _mock_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout="项目名称：旧版 Word Brief\n预算：30-50万".encode("utf-8"),
            stderr=b"",
        )

    monkeypatch.setattr(parser.subprocess, "run", _mock_run)

    sections = parser.parse_document(str(doc_path), "legacy.doc")

    assert captured["args"] == [
        "antiword",
        "-m",
        "UTF-8.txt",
        str(doc_path),
    ]
    assert captured["kwargs"]["check"] is False
    assert captured["kwargs"]["capture_output"] is True
    assert captured["kwargs"]["timeout"] == parser.LEGACY_DOC_PARSE_TIMEOUT_SECONDS
    assert sections == [
        parser.ParsedSection(
            label="Word正文",
            page=None,
            text="项目名称：旧版 Word Brief\n预算：30-50万",
        )
    ]


def test_parse_legacy_doc_reports_missing_antiword(monkeypatch, tmp_path):
    doc_path = tmp_path / "legacy.doc"
    doc_path.write_bytes(b"mock-legacy-doc")

    def _missing_binary(*_args, **_kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(parser.subprocess, "run", _missing_binary)

    with pytest.raises(parser.DocumentParseError, match="antiword"):
        parser.parse_document(str(doc_path), "legacy.doc")


def test_parse_legacy_doc_rejects_empty_output(monkeypatch, tmp_path):
    doc_path = tmp_path / "legacy.doc"
    doc_path.write_bytes(b"mock-legacy-doc")

    monkeypatch.setattr(
        parser.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=b"",
            stderr=b"",
        ),
    )

    with pytest.raises(parser.DocumentParseError, match="没有可提取的文字"):
        parser.parse_document(str(doc_path), "legacy.doc")
