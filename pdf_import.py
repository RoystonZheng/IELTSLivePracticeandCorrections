"""Extract an editable local practice draft from a text-based IELTS PDF."""

from __future__ import annotations

import re

MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PAGES = 80
MAX_TEXT_CHARS = 180_000
QUESTION = re.compile(r"^\s*(?:Question\s+)?([1-9]\d?)(?:[.):]\s*|\s+)(.+)$", re.I)
BARE_NUMBER = re.compile(r"^\s*([1-9]\d?)\s*$")
RANGE = re.compile(r"^\s*Questions?\s+\d+\s*(?:[-–—]|to)\s*\d+", re.I)
OPTION = re.compile(r"^\s*([A-D])[.)]\s*(.+)$", re.I)
TASK = re.compile(r"^\s*(?:Writing\s+)?Task\s*([12])\s*[:.\-]?\s*(.*)$", re.I)
ANSWER_HEADING = re.compile(r"^\s*(?:answer\s*key|answers|参考答案|答案解析)\s*[:：]?\s*$", re.I)
KEY_LINE = re.compile(r"^\s*([1-9]\d?)[.):]?\s+(.{1,80}?)\s*$")


def parse_pages(pages: list[str], skill: str, title: str) -> dict:
    """Parse likely question starts; all extracted fields remain editable in the UI."""
    if skill not in {"reading", "listening", "writing", "speaking"}:
        raise ValueError("请选择听力、阅读、写作或口语")
    lines: list[tuple[int, str]] = []
    for page_number, page in enumerate(pages, 1):
        lines.extend((page_number, line.strip()) for line in page.splitlines() if line.strip())

    answer_start = next((i for i, (_, line) in enumerate(lines) if ANSWER_HEADING.match(line)), len(lines))
    body_lines, key_lines = lines[:answer_start], lines[answer_start + 1:]
    answer_key: dict[int, str] = {}
    for _, line in key_lines:
        match = KEY_LINE.match(line)
        if match:
            answer_key[int(match[1])] = match[2].strip()

    questions: list[dict] = []
    if skill == "writing":
        for page, line in body_lines:
            match = TASK.match(line)
            if match:
                questions.append({"number": int(match[1]), "page": page, "prompt": match[2].strip(), "options": [], "answer": ""})
            elif questions:
                questions[-1]["prompt"] += "\n" + line
    else:
        in_questions = False
        skip_next = False
        for i, (page, line) in enumerate(body_lines):
            if skip_next:
                skip_next = False
                continue
            if RANGE.match(line):
                in_questions = True
                continue
            match = QUESTION.match(line)
            number = int(match[1]) if match else None
            body = match[2].strip() if match else ""
            bare = BARE_NUMBER.match(line) if not match and in_questions else None
            if bare and i + 1 < len(body_lines):
                number = int(bare[1])
                body = body_lines[i + 1][1]
                skip_next = True
            # Avoid treating dates, page numbers and repeated references as questions.
            if number is not None and (not questions or number > questions[-1]["number"]):
                questions.append({"number": number, "page": page, "prompt": body, "options": [], "answer": ""})
                continue
            if not questions or bare:
                continue
            option = OPTION.match(line)
            if option and len(questions[-1]["options"]) < 4:
                questions[-1]["options"].append(f"{option[1].upper()}. {option[2].strip()}")
            elif not (line.lower().startswith(("page ", "questions ")) or RANGE.match(line)):
                questions[-1]["prompt"] += "\n" + line

    for question in questions:
        question["prompt"] = question["prompt"].strip()
        answer = answer_key.get(question["number"], "")
        if question["options"] and re.match(r"^[A-D](?:[.):]|$)", answer, re.I):
            answer = answer[0].upper()
        question["answer"] = answer
    questions = [q for q in questions if q["prompt"]][:120]

    reference_parts = []
    for page_number, line in body_lines:
        if not reference_parts or reference_parts[-1][0] != page_number:
            reference_parts.append((page_number, []))
        reference_parts[-1][1].append(line)
    reference = "\n\n".join(f"[第 {page} 页]\n" + "\n".join(content)
                           for page, content in reference_parts)[:MAX_TEXT_CHARS]
    warnings = ["自动提取可能漏掉表格、图形、双栏顺序或连线题；保存前请核对每道题。"]
    if not questions:
        warnings.append("没有识别到题号；可在预览中手动添加题目。")
    if not answer_key:
        warnings.append("未找到明确的答案页；可手动填写标准答案。没有答案的题目不会自动评分。")
    return {"title": title, "skill": skill, "pageCount": len(pages), "referenceText": reference,
            "questions": questions, "warnings": warnings}


def parse_pdf(data: bytes, skill: str, filename: str) -> dict:
    if not data.startswith(b"%PDF-") or not 1 <= len(data) <= MAX_PDF_BYTES:
        raise ValueError("请选择不超过 20 MB 的 PDF 文件")
    try:
        import pymupdf
    except ImportError as exc:
        raise RuntimeError("缺少 PyMuPDF；请先运行 python3 -m pip install -r requirements-pdf.txt") from exc
    try:
        with pymupdf.open(stream=data, filetype="pdf") as document:
            if document.needs_pass:
                raise ValueError("暂不支持加密 PDF，请先解锁后再导入")
            if not 1 <= len(document) <= MAX_PAGES:
                raise ValueError("PDF 页数须在 1—80 页之间")
            pages = [page.get_text("text", sort=True) for page in document]
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise ValueError("PDF 无法读取或文件已损坏") from exc
    if sum(len(page.strip()) for page in pages) < 30:
        raise ValueError("未提取到可用文字。这可能是扫描版 PDF，请先进行 OCR 再导入")
    title = re.sub(r"[\x00-\x1f]", "", filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])[:100]
    if title.lower().endswith(".pdf"):
        title = title[:-4]
    return parse_pages(pages, skill, title or "导入的 PDF 试卷")
