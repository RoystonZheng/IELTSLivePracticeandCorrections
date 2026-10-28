"""Refresh the active IELTS recall index for China-focused practice.

Only source metadata, short topic labels, and links are stored. Third-party
passages, audio, answer keys, writing prompts, and speaking cards remain on
their publishers' sites. The January/May/September boundaries are collection
windows, not an official replacement calendar for Listening, Reading, or Writing papers.
"""
from __future__ import annotations

import argparse
import calendar
import csv
from concurrent.futures import ThreadPoolExecutor
import hashlib
import ipaddress
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html import unescape
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Semaphore, Thread
from urllib.error import HTTPError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
ACTIVE = ROOT / "question-bank" / "current"
TZ = ZoneInfo("Asia/Shanghai")
YAQUAN = "https://www.yaquan.site/ielts/writing"
XHD = "https://cq.xhd.cn/ielts/ysjj/"
TUONIDEFU = "https://tuonidefu.com.cn/blogs"
JOE_SPEAKING = "https://joespeaking.com/zh-CN/ielts-speaking-questions"
ZIP_SPEAKING = "https://www.zipielts.com/library"
MONTH_CODES = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
EMPTY_SEASON_NOTICE = ("本期只展示有来源的公开考后记录。未获得转载授权的题目、答案和音频不会打包到仓库；"
                       "请到来源网站核对原题，或导入自己有权使用的试卷。")


@dataclass(frozen=True)
class Season:
    start: date
    end: date

    @property
    def id(self) -> str:
        return f"{self.start:%Y-%m}_{self.end:%Y-%m}"

    @property
    def months(self) -> list[str]:
        return [f"{self.start.year}-{m:02}" for m in range(self.start.month, self.end.month + 1)]

    @property
    def label(self) -> str:
        return f"{self.start.year} 年 {self.start.month}—{self.end.month} 月"

    def as_dict(self) -> dict:
        return {"id": self.id, "start": self.start.isoformat(), "end": self.end.isoformat(),
                "label": self.label, "months": self.months}


def season_for(day: date) -> Season:
    start_month = 9 if day.month >= 9 else 5 if day.month >= 5 else 1
    end_month = start_month + 3
    return Season(date(day.year, start_month, 1),
                  date(day.year, end_month, calendar.monthrange(day.year, end_month)[1]))


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; IELTSPracticeDesk/2.0; public-source-index)"})
    for attempt in range(2):
        try:
            with urlopen(request, timeout=25) as response:
                return response.read().decode("utf-8", "replace")
        except HTTPError:
            raise
        except OSError:
            if attempt:
                raise
            time.sleep(0.4)


def strip_tags(html: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", html)).strip()


def parse_yaquan(html: str, season: Season, today: date) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    pattern = (r'<a[^>]*href="(/paper/[^"]+)"[^>]*>(.*?)</a>\s*'
               r'<span[^>]*>Task ([12]) · (20\d\d\.\d{1,2}\.\d{1,2})([^<]*)</span>')
    for href, title, task, raw_date, venue in re.findall(pattern, html, re.S):
        try:
            year, month, day = map(int, raw_date.split("."))
            exam_date = date(year, month, day)
        except ValueError:
            continue
        url = urljoin(YAQUAN, href)
        if not season.start <= exam_date <= min(today, season.end) or url in seen:
            continue
        seen.add(url)
        reported_venue = strip_tags(venue)
        items.append({"id": f"W-{exam_date:%Y%m%d}-{len(items)+1:03}",
                      "month": f"{exam_date:%Y-%m}", "date": exam_date.isoformat(),
                      "task": f"Task {task}", "venueReported": reported_venue,
                      "title": strip_tags(title), "url": url,
                      "kind": "third_party_dated_topic", "geography": "site_reported_venue",
                      "reportedAppearances": [{"date": exam_date.isoformat(), "venue": reported_venue or None,
                                               "sourceUrl": url, "verification": "third_party_report_only"}],
                      "sourceId": "yaquan"})
    return sorted(items, key=lambda x: (x["date"], x["task"], x["url"]), reverse=True)


def parse_xhd(html: str, season: Season, today: date) -> list[dict]:
    items = []
    pattern = (r'<a href="(/ielts/ysjj/\d+\.html)"[^>]*>.*?'
               r'<h3[^>]*>(.*?)</h3>\s*<span class="indetail_n_noteTime">(20\d\d-\d\d-\d\d)</span>')
    for href, raw_title, raw_date in re.findall(pattern, html, re.S):
        try:
            published = date.fromisoformat(raw_date)
        except ValueError:
            continue
        title = strip_tags(raw_title)
        if not season.start <= published <= min(today, season.end):
            continue
        mentioned_months = [int(x) for x in re.findall(r"(?<!\d)(\d{1,2})月", title)]
        if mentioned_months and any(m < season.start.month or m > season.end.month for m in mentioned_months):
            continue
        if "口语" in title or not any(word in title for word in ("回忆", "考情", "考了什么")):
            continue
        items.append({"id": f"X-{href.rsplit('/', 1)[-1].split('.')[0]}",
                      "month": f"{published:%Y-%m}", "date": published.isoformat(),
                      "title": title, "url": urljoin(XHD, href),
                      "kind": "candidate_recall_article", "geography": "china_multi_venue_or_unspecified",
                      "sourceId": "xhd"})
    return list({x["url"]: x for x in items}.values())


def parse_tuonidefu(html: str, season: Season, today: date) -> list[dict]:
    items = []
    pattern = (r'<a href="(/blogs/\d+)"[^>]*aria-label="阅读文章：([^"]+)"[^>]*>\s*'
               r'<div[^>]*create_timestamp="(20\d\d-\d\d-\d\d)')
    for href, raw_title, raw_date in re.findall(pattern, html):
        try:
            published = date.fromisoformat(raw_date)
        except ValueError:
            continue
        title = unescape(raw_title).strip()
        if not season.start <= published <= min(today, season.end):
            continue
        if "雅思" not in title or "口语" in title or not any(word in title for word in ("回忆", "考情", "复盘")):
            continue
        mentioned_months = [int(x) for x in re.findall(r"(?<!\d)(\d{1,2})月", title)]
        if mentioned_months and any(m < season.start.month or m > season.end.month for m in mentioned_months):
            continue
        items.append({"id": f"T-{href.rsplit('/', 1)[-1]}", "month": f"{published:%Y-%m}",
                      "date": published.isoformat(), "title": title, "url": urljoin(TUONIDEFU, href),
                      "kind": "weekly_exam_recap", "geography": "china_education_site_location_unspecified",
                      "sourceId": "tuonidefu"})
    return items


class _VisibleText(HTMLParser):
    """Keep short visible text fragments in document order, without page scripts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fragments: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            value = " ".join(unescape(data).split())
            if value:
                self.fragments.append(value)


def visible_fragments(html: str) -> list[str]:
    parser = _VisibleText()
    parser.feed(html)
    return parser.fragments


def weekly_period(title: str, year: int) -> str | None:
    match = re.search(r"(\d{1,2})月(\d{1,2})日?\s*[-‐‑–—至~]\s*(?:(\d{1,2})月)?(\d{1,2})日?", title)
    if not match:
        return None
    start_month, start_day, end_month, end_day = match.groups()
    try:
        first = date(year, int(start_month), int(start_day))
        last = date(year, int(end_month or start_month), int(end_day))
    except ValueError:
        return None
    return f"{first.isoformat()}—{last.isoformat()}" if first <= last else None


def _topic_record(lead: dict, skill: str, section: str | None, title: str,
                  position: int, period: str | None) -> dict:
    key = f"{lead['id']}|{skill}|{section}|{title}|{position}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return {"id": f"{'R' if skill == 'reading' else 'L'}-{lead['id']}-{digest}",
            "month": lead["month"], "date": lead["date"], "title": title,
            "url": lead["url"], "kind": "reported_topic", "section": section,
            "reportedPeriod": period, "reportedAppearances": [],
            "geography": "venue_unverified", "sourceId": f"{lead['sourceId']}-{lead['id']}",
            "sourceTitle": lead["title"]}


def parse_weekly_recap_topics(html: str, lead: dict) -> dict[str, list[dict]]:
    """Extract only numbered hearing/reading topic labels, not papers or answers."""
    fragments = visible_fragments(html)
    disclaimer = next((i for i, value in enumerate(fragments)
                       if "不提供、不传播任何考试原题" in value), -1)
    if disclaimer < 0:
        raise ValueError("weekly recap disclaimer/structure not found")
    start = next((i for i in range(disclaimer + 1, len(fragments)) if fragments[i] == "听力"), -1)
    reading_start = next((i for i in range(start + 1, len(fragments)) if fragments[i] == "阅读"), -1)
    end = next((i for i in range(reading_start + 1, len(fragments)) if fragments[i] == "写作"), -1)
    if min(start, reading_start, end) < 0:
        raise ValueError("weekly recap listening/reading sections not found")
    period = weekly_period(lead["title"], int(lead["date"][:4]))
    result: dict[str, list[dict]] = {"reading": [], "listening": []}
    for skill, part in (("listening", fragments[start + 1:reading_start]),
                        ("reading", fragments[reading_start + 1:end])):
        section = None
        section_count = 0
        named_heading_mode = skill == "reading" and any(re.match(r"第[一二三]篇[：:]", x) for x in part)
        section_detail_mode = skill == "listening" and any(re.match(r"Section\s*[1-4]", x, re.I) for x in part)
        for value in part:
            heading = re.fullmatch(r"(?:Part|P|passage|Section)\s*([1-4])\s*[:：]?\s*(.*)", value, re.I)
            if heading:
                number = int(heading.group(1))
                section = f"{'Part' if skill == 'listening' else 'Passage'} {number}"
                section_count += 1
                heading_topic = heading.group(2).strip()
                if heading_topic and len(heading_topic) <= 80:
                    result[skill].append(_topic_record(lead, skill, section, heading_topic,
                                                       len(result[skill]) + 1, period))
                elif skill == 'listening' and 'Section' in value:
                    item = _topic_record(lead, skill, section,
                                         f'{section} 回忆 {section_count}（话题未标明）',
                                         len(result[skill]) + 1, period)
                    item["kind"] = "reported_section"
                    result[skill].append(item)
                continue
            if section_detail_mode:
                continue
            if skill == "reading":
                named = re.fullmatch(r"第([一二三])篇[：:]\s*(.{2,100})", value)
                if named:
                    section = f"Passage {('一', '二', '三').index(named.group(1)) + 1}"
                    result[skill].append(_topic_record(lead, skill, section, named.group(2),
                                                       len(result[skill]) + 1, period))
                    continue
                if named_heading_mode:
                    continue
            match = re.match(r"^\s*\d{1,2}\s*[.．、)）]?\s+(.+)$", value)
            if not match:
                match = re.match(r"^\s*\d{1,2}\s*[.．、)）]\s*(.+)$", value)
            if not section or not match:
                if skill == "reading" and not section and match:
                    topic = match.group(1).strip(" ：:;；。")
                    if 2 <= len(topic) <= 100 and "____" not in topic:
                        result[skill].append(_topic_record(lead, skill, None, topic,
                                                           len(result[skill]) + 1, period))
                elif skill == "reading" and not match and 3 <= len(value) <= 85 and re.search(r"[A-Za-z]", value) and not re.search(r"(?:Answer|Question|参考答案)", value, re.I):
                    result[skill].append(_topic_record(lead, skill, section, value,
                                                       len(result[skill]) + 1, period))
                continue
            topic = match.group(1).strip(" ：:;；。")
            if not 2 <= len(topic) <= 120:
                continue
            result[skill].append(_topic_record(lead, skill, section, topic,
                                               len(result[skill]) + 1, period))
    if not result["reading"] and not result["listening"]:
        raise ValueError("weekly recap has no numbered topics")
    return result


def parse_xhd_topics(html: str, lead: dict) -> dict[str, list[dict]]:
    fragments = visible_fragments(html)
    listening = next((i for i, v in enumerate(fragments) if v.startswith("雅思听力考情")), -1)
    reading = next((i for i, v in enumerate(fragments) if v.startswith("雅思阅读考情")), -1)
    if min(listening, reading) < 0:
        raise ValueError("XHD skill sections not found")
    result = {"reading": [], "listening": []}
    year = int(lead["date"][:4])
    period_match = re.search(r"(\d{1,2})\.(\d{1,2})\s*[-‐‑–—至~]\s*(\d{1,2})\.(\d{1,2})", lead["title"])
    period = None
    if period_match:
        sm, sd, em, ed = map(int, period_match.groups())
        try:
            period = f"{date(year,sm,sd).isoformat()}—{date(year,em,ed).isoformat()}"
        except ValueError:
            pass
    for value in fragments[listening + 1:reading]:
        match = re.match(r"P(?:art)?\s*([1-4])\s*[（(](20\d\d)\.(\d{1,2})\.(\d{1,2})[）)]\s*(.*)", value, re.I)
        if not match:
            continue
        number, y, m, d, rest = match.groups()
        try:
            day = date(int(y), int(m), int(d))
        except ValueError:
            continue
        venue = re.split(r"题型|难度", rest, 1)[0].strip() or None
        topic = "沼气发电厂" if "沼气发电厂" in rest else "超市布局" if "超市布局" in rest else f"Part {number} 回忆（话题未标明）"
        item = _topic_record(lead, "listening", f"Part {number}", topic, len(result["listening"]) + 1, period)
        if "话题未标明" in topic:
            item["kind"] = "reported_section"
        item["reportedAppearances"] = [{"date": day.isoformat(), "venue": venue,
                                        "sourceUrl": lead["url"], "verification": "third_party_report_only"}]
        result["listening"].append(item)
    section = None
    for value in fragments[reading + 1:]:
        heading = re.match(r"Passage\s*([1-3])文章特点", value, re.I)
        if heading:
            section = f"Passage {heading.group(1)}"
            continue
        if section and value.startswith("话题分布："):
            for group in re.findall(r"[①②③④]([^①②③④]+)", value):
                topics = group.split("：", 1)[-1]
                for raw in re.split(r"[、，。]​?", topics):
                    topic = re.sub(r"(?:出现\s*\d+\s*次|[（(]\d+次[）)])", "", raw).strip(" ：:;；。")
                    if 2 <= len(topic) <= 55:
                        result["reading"].append(_topic_record(lead, "reading", section, topic,
                                                                len(result["reading"]) + 1, period))
        if value.startswith("二、 高频话题文章精讲"):
            break
    if not result["reading"]:
        raise ValueError("XHD reading topics not found")
    return result


def speaking_url(season: Season) -> str:
    return f"{JOE_SPEAKING}/{season.start.year}-{MONTH_CODES[season.start.month-1]}-{MONTH_CODES[season.end.month-1]}"


def parse_joe_speaking(html: str, season: Season) -> list[dict]:
    marker = f"{season.start.year} 年 {season.start.month}-{season.end.month} 月"
    if marker not in html:
        raise ValueError(f"speaking index season marker absent: {marker}")
    url = speaking_url(season)
    items = []
    for article in re.findall(r"<article\b[^>]*>(.*?)</article>", html, re.S):
        heading = re.search(r"<h2[^>]*>(.*?)</h2>", article, re.S)
        if not heading:
            continue
        top = strip_tags(article.split("</div>", 1)[0])
        if "中国大陆" not in top:
            continue
        part = "Part 2 / Part 3" if "Part 2 / Part 3" in top else "Part 1" if "Part 1" in top else None
        number = re.search(r"话题\s*(\d+)", top)
        if not part or not number:
            continue
        title = strip_tags(heading.group(1))
        if not title:
            continue
        items.append({"id": f"S-{season.id}-{'p1' if part == 'Part 1' else 'p23'}-{int(number.group(1)):03}",
                      "month": f"{season.start:%Y-%m}", "date": None,
                      "part": part, "title": title, "url": url,
                      "kind": "third_party_topic_index", "geography": "site_reported_mainland",
                      "sourceId": "joe-speaking"})
    if not items:
        raise ValueError("no mainland speaking topics parsed")
    return items


def parse_zip_speaking(html: str, season: Season) -> list[dict]:
    marker = f"{season.start.year} 年 {season.start.month}–{season.end.month} 月"
    if marker not in html:
        raise ValueError(f"speaking index season marker absent: {marker}")
    items = []
    pattern = r'id="nav-topic-([^"]+)".*?<span class="leading-snug\s*">(.*?)</span>'
    for topic_id, title_html in re.findall(pattern, html, re.S):
        if "overseas" in topic_id or not topic_id.startswith(("p1_", "p23_")):
            continue
        dated = re.search(r"_20\d\d_(?:jan|may|sep)_", topic_id)
        current = f"_{season.start.year}_{MONTH_CODES[season.start.month - 1]}_"
        if dated and dated.group() != current:
            continue
        title = strip_tags(title_html)
        if not title:
            continue
        items.append({"id": f"S-{season.id}-zip-{topic_id}", "month": f"{season.start:%Y-%m}",
                      "date": None, "part": "Part 1" if topic_id.startswith("p1_") else "Part 2 / Part 3",
                      "title": title, "url": ZIP_SPEAKING, "kind": "third_party_topic_index",
                      "geography": "site_reported_mainland", "sourceId": "zip-speaking"})
    if not items:
        raise ValueError("no mainland speaking topics parsed")
    return items


def previous_index() -> dict | None:
    path = APP / "data" / "public-index.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def collect(today: date, fetcher=fetch, previous: dict | None = None) -> dict:
    season = season_for(today)
    same_season = bool(previous and previous.get("season", {}).get("id") == season.id)
    result = {"schemaVersion": 3, "checkedAt": today.isoformat(), "season": season.as_dict(),
              "scope": "中国大陆考生的公开考情线索；仅展示来源允许保存的简短元数据和链接。",
              "reading": [], "listening": [], "writing": [], "speaking": [], "recallLeads": [],
              "sourceStatus": [], "futureMonths": [m for m in season.months if m > f"{today:%Y-%m}"]}

    def run_source(source_id: str, url: str, parser, field: str) -> None:
        try:
            items = parser(fetcher(url))
            old = [x for x in (previous or {}).get(field, []) if x.get("sourceId") == source_id] if same_season else []
            if old and len(items) < max(1, len(old) // 2):
                raise ValueError(f"sudden source shrink: {len(old)} -> {len(items)}")
            result[field].extend(items)
            result["sourceStatus"].append({"id": source_id, "url": url, "status": "ok",
                                            "items": len(items), "checkedAt": today.isoformat()})
        except HTTPError as exc:
            status = "not_published" if exc.code == 404 else "error"
            retain(source_id, url, status, f"HTTP {exc.code}", field)
        except Exception as exc:
            retain(source_id, url, "error", f"{type(exc).__name__}: {exc}", field)

    def retain(source_id: str, url: str, status: str, error: str, field: str) -> None:
        old = [x for x in (previous or {}).get(field, []) if x.get("sourceId") == source_id] if same_season else []
        result[field].extend(old)
        result["sourceStatus"].append({"id": source_id, "url": url, "status": status,
                                        "items": len(old), "retainedFromSameSeason": bool(old),
                                        "error": error[:200], "checkedAt": today.isoformat()})

    run_source("yaquan", YAQUAN, lambda html: parse_yaquan(html, season, today), "writing")
    run_source("xhd", XHD, lambda html: parse_xhd(html, season, today), "recallLeads")
    run_source("tuonidefu", TUONIDEFU, lambda html: parse_tuonidefu(html, season, today), "recallLeads")
    run_source("joe-speaking", speaking_url(season), lambda html: parse_joe_speaking(html, season), "speaking")
    if not result["speaking"]:
        run_source("zip-speaking", ZIP_SPEAKING, lambda html: parse_zip_speaking(html, season), "speaking")
    article_leads = [(lead, parse_weekly_recap_topics) for lead in result["recallLeads"]
                     if lead.get("sourceId") == "tuonidefu"]
    article_leads += [(lead, parse_xhd_topics) for lead in result["recallLeads"]
                      if lead.get("sourceId") == "xhd" and
                      any(term in lead.get("title", "") for term in ("考了什么", "全科", "听力", "阅读", "机考回忆"))]
    with ThreadPoolExecutor(max_workers=5) as pool:
        pages = [(lead, parser, pool.submit(fetcher, lead["url"])) for lead, parser in article_leads]
        for lead, parser, future in pages:
            source_id = f"{lead['sourceId']}-{lead['id']}"
            try:
                parsed = parser(future.result(), lead)
                for field in ("reading", "listening"):
                    old = [x for x in (previous or {}).get(field, []) if x.get("sourceId") == source_id] if same_season else []
                    items = parsed[field]
                    if old and len(items) < max(1, len(old) // 2):
                        raise ValueError(f"sudden topic shrink in {field}: {len(old)} -> {len(items)}")
                for field in ("reading", "listening"):
                    result[field].extend(parsed[field])
                result["sourceStatus"].append({"id": source_id, "url": lead["url"], "status": "ok",
                                                "items": sum(map(len, parsed.values())), "checkedAt": today.isoformat()})
            except Exception as exc:
                retained = []
                if same_season:
                    for field in ("reading", "listening"):
                        old = [x for x in (previous or {}).get(field, []) if x.get("sourceId") == source_id]
                        result[field].extend(old)
                        retained.extend(old)
                result["sourceStatus"].append({"id": source_id, "url": lead["url"], "status": "error",
                                                "items": len(retained), "retainedFromSameSeason": bool(retained),
                                                "error": f"{type(exc).__name__}: {exc}"[:200],
                                                "checkedAt": today.isoformat()})
    for field in ("reading", "listening", "writing", "speaking", "recallLeads"):
        key = "id" if field in ("reading", "listening", "speaking") else "url"
        result[field] = list({x[key]: x for x in result[field]}.values())
        for item in result[field]:
            item.setdefault("reportedAppearances", [])
    result["sources"] = [
        {"id": "yaquan", "url": YAQUAN, "description": "写作日期和考点由第三方网站标注，未独立逐条核验。"},
        {"id": "xhd", "url": XHD, "description": "机构考情文章，可能涉及全国多地；不是完整原卷。"},
        {"id": "tuonidefu", "url": TUONIDEFU, "description": "按周整理的机考反馈文章；考点地点需回原文核对。"},
        {"id": "joe-speaking", "url": speaking_url(season), "description": "第三方当期资料目录；只保存大陆话题标题和 Part，题卡请到原站查看。"},
        {"id": "zip-speaking", "url": ZIP_SPEAKING, "description": "口语目录备用来源；仅在主目录不可用时保存本期资料标题与 Part。"},
        {"id": "official", "url": "https://www.chinaielts.org/prepare/ielts-practice-tests/mocks-academic",
         "description": "雅思官方学术类免费样题；不属于当季考后回忆。"},
    ]
    return result


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def csv_text(items: list[dict], columns: list[str]) -> str:
    from io import StringIO
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(items)
    return output.getvalue()


def sync_season_content(index: dict) -> bool:
    """Drop the old season's practice only when the source-index season changes."""
    path = APP / "data" / "season-content.json"
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        current = {}
    if current.get("seasonId") == index["season"]["id"]:
        return False
    content = {"seasonId": index["season"]["id"], "notice": EMPTY_SEASON_NOTICE,
               "reading": [], "listening": [], "writing": [], "speaking": []}
    atomic_text(path, json.dumps(content, ensure_ascii=False, indent=2) + "\n")
    atomic_text(APP / "season-content.js", "window.IELTS_SEASON_CONTENT = " +
                json.dumps(content, ensure_ascii=False, separators=(",", ":")) + ";\n")
    for audio in (APP / "audio" / "season").glob("*.m4a"):
        audio.unlink()
    return True


def publish(index: dict) -> None:
    season = index["season"]
    for field in ("reading", "listening", "writing", "speaking", "recallLeads"):
        assert all(x["month"] in season["months"] for x in index[field]), field
    assert all(x["url"].startswith("https://") for field in ("reading", "listening", "writing", "recallLeads") for x in index[field])
    ACTIVE.mkdir(parents=True, exist_ok=True)
    for field, columns in {
        "reading": ["id", "month", "date", "section", "reportedPeriod", "title", "url", "kind", "geography", "sourceId", "sourceTitle"],
        "listening": ["id", "month", "date", "section", "reportedPeriod", "title", "url", "kind", "geography", "sourceId", "sourceTitle"],
        "writing": ["id", "month", "date", "task", "venueReported", "title", "url", "kind", "geography", "sourceId"],
        "speaking": ["id", "month", "date", "part", "title", "url", "kind", "geography", "sourceId"],
        "recallLeads": ["id", "month", "date", "title", "url", "kind", "geography", "sourceId"],
    }.items():
        atomic_text(ACTIVE / f"{field}.csv", csv_text(index[field], columns))
    manifest = {"season": season, "checkedAt": index["checkedAt"], "scope": index["scope"],
                "counts": {field: len(index[field]) for field in ("reading", "listening", "writing", "speaking", "recallLeads")},
                "sourceStatus": index["sourceStatus"], "contentPolicy": "Metadata and links only; no third-party full papers/audio/answers."}
    atomic_text(ACTIVE / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    atomic_text(APP / "data" / "public-index.json", json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    bundle = {"publicIndex": index}
    for key, file in (("readingTest", "demo-test.json"), ("listeningTest", "listening-test.json"),
                      ("writingTest", "writing-test.json")):
        bundle[key] = json.loads((APP / "data" / file).read_text(encoding="utf-8"))
    atomic_text(APP / "bank.js", "window.IELTS_BANK = " + json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + ";\n")
    sync_season_content(index)


def update_once(day: date | None = None, fetcher=fetch) -> dict:
    today = day or datetime.now(TZ).date()
    old = previous_index()
    index = collect(today, fetcher, old)
    publish(index)
    counts = {k: len(index[k]) for k in ("reading", "listening", "writing", "speaking", "recallLeads")}
    print(json.dumps({"checkedAt": index["checkedAt"], "season": index["season"]["id"],
                      "counts": counts, "errors": [x for x in index["sourceStatus"] if x["status"] == "error"]},
                     ensure_ascii=False))
    return index


def due_for_daily_refresh(now: datetime, last_run: date) -> bool:
    local = now.astimezone(TZ)
    return local.hour >= 8 and local.date() != last_run


AI_SLOT = Semaphore(1)


def make_handler():
    from ai_bridge import build_case, build_spoken_case, cli_available, run_codex
    from pdf_import import MAX_PDF_BYTES, parse_pdf
    from speech_analysis import MAX_AUDIO_BYTES, SUFFIXES, speech_available, transcribe_audio

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def end_headers(self) -> None:
            if self.path.endswith((".js", ".json")) or self.path.startswith("/api/"):
                self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def send_json(self, status: int, value: dict) -> None:
            data = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def local_request(self) -> bool:
            try:
                return ipaddress.ip_address(self.client_address[0]).is_loopback
            except ValueError:
                return False

        def do_GET(self) -> None:
            if self.path == "/api/capabilities":
                if not self.local_request():
                    self.send_json(403, {"error": "仅允许本机访问"})
                else:
                    self.send_json(200, {"codexCli": cli_available(), "speechToText": speech_available(),
                                         "mode": "local_optional"})
                return
            super().do_GET()

        def do_POST(self) -> None:
            if self.path not in {"/api/feedback", "/api/import-pdf", "/api/speaking-audio"}:
                self.send_json(404, {"error": "接口不存在"})
                return
            origin = urlparse(self.headers.get("Origin", ""))
            try:
                origin_ok = (origin.scheme == "http" and origin.hostname in {"127.0.0.1", "localhost", "::1"}
                             and origin.port == self.server.server_port)
            except ValueError:
                origin_ok = False
            content_type = self.headers.get("Content-Type", "")
            media_type = content_type.split(";", 1)[0].strip().lower()
            if self.path == "/api/import-pdf":
                type_ok = media_type == "application/pdf"
            elif self.path == "/api/speaking-audio":
                type_ok = media_type in SUFFIXES
            else:
                type_ok = media_type == "application/json"
            if not self.local_request() or not origin_ok or not type_ok:
                self.send_json(403, {"error": "仅允许当前本地页面提交"})
                return
            if self.path == "/api/import-pdf":
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= size <= MAX_PDF_BYTES:
                        raise ValueError("PDF 须小于 20 MB")
                    skill = self.headers.get("X-IELTS-Skill", "")
                    filename = unquote(self.headers.get("X-IELTS-Filename", "paper.pdf"))
                    result = parse_pdf(self.rfile.read(size), skill, filename)
                except ValueError as exc:
                    self.send_json(400, {"error": str(exc)[:200]})
                    return
                except RuntimeError as exc:
                    self.send_json(503, {"error": str(exc)[:200]})
                    return
                self.send_json(200, result)
                return
            if self.path == "/api/speaking-audio":
                try:
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= size <= MAX_AUDIO_BYTES:
                        raise ValueError("录音须小于 15 MB")
                    topic_id = self.headers.get("X-IELTS-Topic", "")
                    if len(topic_id) > 100:
                        raise ValueError("口语话题无效")
                    if not AI_SLOT.acquire(blocking=False):
                        self.send_json(429, {"error": "已有一条反馈正在生成，请稍后重试"})
                        return
                    try:
                        evidence = transcribe_audio(self.rfile.read(size), media_type)
                        case = build_spoken_case(topic_id, evidence)
                        result = run_codex(case)
                    finally:
                        AI_SLOT.release()
                except ValueError as exc:
                    self.send_json(400, {"error": str(exc)[:200]})
                    return
                except RuntimeError as exc:
                    self.send_json(503, {"error": str(exc)[:200]})
                    return
                except OSError:
                    self.send_json(503, {"error": "本地语音组件或 Codex CLI 启动失败"})
                    return
                self.send_json(200, {"feedback": result, "transcript": evidence["transcript"],
                                     "timing": case["audioTiming"]})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 1 <= size <= 32000:
                    raise ValueError("请求内容过长或为空")
                payload = json.loads(self.rfile.read(size))
                case = build_case(payload)
            except (ValueError, json.JSONDecodeError, StopIteration) as exc:
                self.send_json(400, {"error": str(exc)[:200]})
                return
            if not AI_SLOT.acquire(blocking=False):
                self.send_json(429, {"error": "已有一条反馈正在生成，请稍后重试"})
                return
            try:
                result = run_codex(case)
                self.send_json(200, {"feedback": result})
            except RuntimeError as exc:
                self.send_json(503, {"error": str(exc)[:200]})
            except OSError:
                self.send_json(503, {"error": "Codex CLI 启动失败"})
            finally:
                AI_SLOT.release()

    return Handler


def serve(host: str, port: int) -> None:
    # Running locally refreshes immediately, then again at/after 08:00 China time each day.
    try:
        update_once()
    except Exception as exc:
        print(f"Startup refresh failed: {exc}", file=sys.stderr)
    stop = Event()
    started = datetime.now(TZ)
    last_run = started.date() if started.hour >= 8 else started.date() - timedelta(days=1)

    def schedule() -> None:
        nonlocal last_run
        while not stop.wait(30):
            now = datetime.now(TZ)
            if due_for_daily_refresh(now, last_run):
                try:
                    update_once(now.date())
                except Exception as exc:
                    print(f"08:00 refresh failed: {exc}", file=sys.stderr)
                last_run = now.date()

    Thread(target=schedule, daemon=True).start()
    server = ThreadingHTTPServer((host, port), make_handler())
    print(f"Open http://{host}:{port}/app/index.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="refresh the current collection season and exit")
    parser.add_argument("--serve", action="store_true", help="refresh now, serve locally, and refresh daily at 08:00 China time")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    if args.serve:
        serve(args.host, args.port)
    else:
        update_once()


if __name__ == "__main__":
    main()
