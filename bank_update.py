"""Refresh the active IELTS recall index for China-focused practice.

Only source metadata, short topic labels, and links are stored. Third-party
passages, audio, answer keys, and writing prompts remain on their publishers'
sites. The January/May/September boundaries are collection windows, not an
official replacement calendar for Listening, Reading, or Writing papers.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from html import unescape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app"
ACTIVE = ROOT / "question-bank" / "current"
TZ = ZoneInfo("Asia/Shanghai")
IELTSA = "https://ieltsactualtests.com"
YAQUAN = "https://www.yaquan.site/ielts/writing"
MENTOR = "https://aiieltsmentor.com/jijing.html"
XHD = "https://cq.xhd.cn/ielts/ysjj/"
TUONIDEFU = "https://tuonidefu.com.cn/blogs"
MONTH_CODES = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")


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
    with urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", "replace")


def strip_tags(html: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", html)).strip()


def parse_ieltsa(html: str, year: int, month: int, skill: str) -> list[dict]:
    code = MONTH_CODES[month - 1]
    path = rf"/{skill}/{year}-{code}-hf-(\d+)"
    nums = sorted({int(n) for n in re.findall(r'href="' + path + r'"', html)})
    return [{"id": f"{skill[0].upper()}-{year}-{month:02}-{n:02}",
             "month": f"{year}-{month:02}", "date": None,
             "title": f"{year}-{month:02} {skill.title()} reconstruction {n}",
             "url": f"{IELTSA}/{skill}/{year}-{code}-hf-{n}",
             "kind": "third_party_reconstruction", "geography": "global_unattributed",
             "sourceId": f"ieltsa-{year}-{month:02}-{skill}"} for n in nums]


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
        items.append({"id": f"W-{exam_date:%Y%m%d}-{len(items)+1:03}",
                      "month": f"{exam_date:%Y-%m}", "date": exam_date.isoformat(),
                      "task": f"Task {task}", "venueReported": strip_tags(venue),
                      "title": strip_tags(title), "url": url,
                      "kind": "third_party_dated_topic", "geography": "site_reported_venue",
                      "sourceId": "yaquan"})
    return sorted(items, key=lambda x: (x["date"], x["task"], x["url"]), reverse=True)


def parse_mentor(html: str, season: Season, today: date) -> list[dict]:
    paths = sorted(set(re.findall(r'href="(/jijing/(20\d\d-\d\d-\d\d-[^"/]+))"', html)))
    items = []
    for path, raw_date in paths:
        try:
            exam_date = date.fromisoformat(raw_date[:10])
        except ValueError:
            continue
        if not season.start <= exam_date <= min(today, season.end):
            continue
        subject = "听力与阅读" if "listening-reading" in path else "写作" if "writing-speaking" in path else "综合"
        items.append({"id": f"M-{path.rsplit('/', 1)[-1]}", "month": f"{exam_date:%Y-%m}",
                      "date": exam_date.isoformat(), "title": f"{exam_date} {subject}考生回忆",
                      "url": urljoin("https://aiieltsmentor.com", path), "kind": "candidate_recall_article",
                      "geography": "mainland_or_asia_mixed_verify_article", "sourceId": "mentor"})
    return items


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


def previous_index() -> dict | None:
    path = APP / "data" / "public-index.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def collect(today: date, fetcher=fetch, previous: dict | None = None) -> dict:
    season = season_for(today)
    same_season = bool(previous and previous.get("season", {}).get("id") == season.id)
    result = {"schemaVersion": 2, "checkedAt": today.isoformat(), "season": season.as_dict(),
              "scope": "中国大陆考生的公开回忆索引；听读重建练习可能来自全球，来源地点逐项标注。",
              "reading": [], "listening": [], "writing": [], "recallLeads": [],
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

    for month_text in season.months:
        if month_text > f"{today:%Y-%m}":
            continue
        year, month = map(int, month_text.split("-"))
        url = f"{IELTSA}/recalls/{month_text}"
        for skill in ("reading", "listening"):
            run_source(f"ieltsa-{month_text}-{skill}", url,
                       lambda html, y=year, m=month, s=skill: parse_ieltsa(html, y, m, s), skill)
    run_source("yaquan", YAQUAN, lambda html: parse_yaquan(html, season, today), "writing")
    run_source("mentor", MENTOR, lambda html: parse_mentor(html, season, today), "recallLeads")
    run_source("xhd", XHD, lambda html: parse_xhd(html, season, today), "recallLeads")
    run_source("tuonidefu", TUONIDEFU, lambda html: parse_tuonidefu(html, season, today), "recallLeads")
    for field in ("reading", "listening", "writing", "recallLeads"):
        result[field] = list({x["url"]: x for x in result[field]}.values())
    result["sources"] = [
        {"id": "ieltsa", "url": f"{IELTSA}/recalls", "description": "按月重建练习；地点不明，不能视为全国考点原卷。"},
        {"id": "yaquan", "url": YAQUAN, "description": "写作日期和考点由第三方网站标注，未独立逐条核验。"},
        {"id": "mentor", "url": MENTOR, "description": "按日期的考生回忆文章；部分含亚太场，需回原文核对地点。"},
        {"id": "xhd", "url": XHD, "description": "机构考情文章，可能涉及全国多地；不是完整原卷。"},
        {"id": "tuonidefu", "url": TUONIDEFU, "description": "按周整理的机考反馈文章；考点地点需回原文核对。"},
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


def publish(index: dict) -> None:
    season = index["season"]
    for field in ("reading", "listening", "writing", "recallLeads"):
        assert all(x["month"] in season["months"] for x in index[field]), field
    assert all(x["url"].startswith("https://") for field in ("reading", "listening", "writing", "recallLeads") for x in index[field])
    ACTIVE.mkdir(parents=True, exist_ok=True)
    for field, columns in {
        "reading": ["id", "month", "date", "title", "url", "kind", "geography", "sourceId"],
        "listening": ["id", "month", "date", "title", "url", "kind", "geography", "sourceId"],
        "writing": ["id", "month", "date", "task", "venueReported", "title", "url", "kind", "geography", "sourceId"],
        "recallLeads": ["id", "month", "date", "title", "url", "kind", "geography", "sourceId"],
    }.items():
        atomic_text(ACTIVE / f"{field}.csv", csv_text(index[field], columns))
    manifest = {"season": season, "checkedAt": index["checkedAt"], "scope": index["scope"],
                "counts": {field: len(index[field]) for field in ("reading", "listening", "writing", "recallLeads")},
                "sourceStatus": index["sourceStatus"], "contentPolicy": "Metadata and links only; no third-party full papers/audio/answers."}
    atomic_text(ACTIVE / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    atomic_text(APP / "data" / "public-index.json", json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    bundle = {"publicIndex": index}
    for key, file in (("readingTest", "demo-test.json"), ("listeningTest", "listening-test.json"),
                      ("writingTest", "writing-test.json")):
        bundle[key] = json.loads((APP / "data" / file).read_text(encoding="utf-8"))
    atomic_text(APP / "bank.js", "window.IELTS_BANK = " + json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + ";\n")


def update_once(day: date | None = None, fetcher=fetch) -> dict:
    today = day or datetime.now(TZ).date()
    old = previous_index()
    index = collect(today, fetcher, old)
    publish(index)
    counts = {k: len(index[k]) for k in ("reading", "listening", "writing", "recallLeads")}
    print(json.dumps({"checkedAt": index["checkedAt"], "season": index["season"]["id"],
                      "counts": counts, "errors": [x for x in index["sourceStatus"] if x["status"] == "error"]},
                     ensure_ascii=False))
    return index


def due_for_daily_refresh(now: datetime, last_run: date) -> bool:
    local = now.astimezone(TZ)
    return local.hour >= 8 and local.date() != last_run


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
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def end_headers(self) -> None:
            if self.path.endswith((".js", ".json")):
                self.send_header("Cache-Control", "no-store")
            super().end_headers()

    server = ThreadingHTTPServer((host, port), Handler)
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
