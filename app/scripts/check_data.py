"""Verify the active season index, local practice content, and browser bundle."""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
sys.path.insert(0, str(ROOT))
from bank_update import season_for

index = json.loads((APP / 'data/public-index.json').read_text(encoding='utf-8'))
test = json.loads((APP / 'data/demo-test.json').read_text(encoding='utf-8'))
listening = json.loads((APP / 'data/listening-test.json').read_text(encoding='utf-8'))
writing = json.loads((APP / 'data/writing-test.json').read_text(encoding='utf-8'))
js = (APP / 'bank.js').read_text(encoding='utf-8')
prefix = 'window.IELTS_BANK = '
assert js.startswith(prefix) and js.rstrip().endswith(';')
bundle = json.loads(js[len(prefix):].strip().removesuffix(';'))
assert bundle == {'publicIndex': index, 'readingTest': test, 'listeningTest': listening, 'writingTest': writing}
season_content = json.loads((APP / 'data/season-content.json').read_text(encoding='utf-8'))
season_js = (APP / 'season-content.js').read_text(encoding='utf-8')
season_prefix = 'window.IELTS_SEASON_CONTENT = '
assert season_js.startswith(season_prefix) and season_js.rstrip().endswith(';')
assert json.loads(season_js[len(season_prefix):].strip().removesuffix(';')) == season_content
assert season_content['seasonId'] == index['season']['id']
for field in ('reading', 'listening', 'writing', 'speaking'):
    authored = season_content[field]
    assert len({item['id'] for item in authored}) == len(authored), field
    for item in authored:
        assert item.get('rights', {}).get('allowPublicRedistribution') is True, item['id']
        assert item['rights'].get('evidence'), item['id']
        assert item['title'] and item.get('sourceUrl', '').startswith('https://'), item['id']
        if field in ('reading', 'listening'):
            assert item['questions'], item['id']
            assert all(q['id'] and q['prompt'] and q['answer'] and q['explanation'] for q in item['questions'])
            assert all(all(isinstance(a, str) and a.strip() for a in q.get('accepted', []))
                       for q in item['questions'])
            if field == 'reading':
                assert item['paragraphs']
            else:
                assert item['sentences']
                assert len(item['sentences']) == len(item['sentenceAudio'])
                assert (APP / item['audio']).stat().st_size > 1000
                assert all((APP / audio).stat().st_size > 1000 for audio in item['sentenceAudio'])
        if field == 'writing':
            assert item['prompt'] and item['minimumWords'] in (150, 250) and item['sourceTitle']
        if field == 'speaking':
            assert item['questions'] and item['sourceTitle']

checked = date.fromisoformat(index['checkedAt'])
season = season_for(checked)
assert index['schemaVersion'] == 3
assert index['season'] == season.as_dict()
assert set(index['futureMonths']).issubset(season.months)
assert index['sourceStatus']
for field in ('reading', 'listening', 'writing', 'speaking', 'recallLeads'):
    items = index[field]
    unique_key = 'id' if field in ('reading', 'listening', 'speaking') else 'url'
    assert len({x[unique_key] for x in items}) == len(items), field
    assert all(x['url'].startswith('https://') and x['month'] in season.months for x in items), field
    assert all(not x.get('date') or date.fromisoformat(x['date']) <= checked for x in items), field
    assert all(isinstance(x.get('reportedAppearances'), list) for x in items), field
    for item in items:
        if item.get('kind') == 'reported_topic':
            assert item.get('sourceTitle') and item.get('sourceId') and item.get('title'), item['id']
            if item.get('reportedPeriod'):
                start, end = item['reportedPeriod'].split('—')
                assert season.start <= date.fromisoformat(start) <= date.fromisoformat(end) <= checked
        for report in item['reportedAppearances']:
            assert date.fromisoformat(report['date']) <= checked
            assert report['sourceUrl'] == item['url']
            assert report['verification'] == 'third_party_report_only'
    with (ROOT / 'question-bank/current' / f'{field}.csv').open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(items), field
    assert [x[unique_key] for x in rows] == [x[unique_key] for x in items], field
manifest = json.loads((ROOT / 'question-bank/current/manifest.json').read_text(encoding='utf-8'))
assert manifest['season'] == index['season']
assert manifest['checkedAt'] == index['checkedAt']
assert manifest['counts'] == {field: len(index[field]) for field in ('reading', 'listening', 'writing', 'speaking', 'recallLeads')}

assert test['durationMinutes'] == 60 and len(test['passages']) == 3
assert len(test['questions']) == 40 and [q['number'] for q in test['questions']] == list(range(1, 41))
passages = {p['id']: p for p in test['passages']}
for passage in passages.values():
    assert len(re.findall(r"\b[\w'-]+\b", ' '.join(p['text'] for p in passage['paragraphs']))) >= 700
for q in test['questions']:
    labels = {p['label'] for p in passages[q['passage']]['paragraphs']}
    assert q['answer'].strip() and q['explanation'].strip()
    assert q['evidence'] in labels or q['evidence'] == 'A-G' or all(x in labels for x in q['evidence'].split(' and '))
assert len(listening['sections']) == 4 and len(listening['questions']) == 40
assert [q['number'] for q in listening['questions']] == list(range(1, 41))
for section in listening['sections']:
    assert (APP / section['audio']).stat().st_size > 100_000
    assert len(section['transcript'].split()) > 200
    assert len(section.get('sentences', [])) >= 15
    assert [s['number'] for s in section['sentences']] == list(range(1, len(section['sentences']) + 1))
    for sentence in section['sentences']:
        assert sentence['text'] and sentence['audio'].startswith('audio/sentences/')
        assert (APP / sentence['audio']).stat().st_size > 2_000
for q in listening['questions']:
    assert q['answer'].strip() and q['explanation'].strip()
assert [task['minimumWords'] for task in writing['tasks']] == [150, 250]
print('OK:', season.id, {field: len(index[field]) for field in ('reading', 'listening', 'writing', 'speaking', 'recallLeads')},
      f"40R/40L/2W/{sum(len(s['sentences']) for s in listening['sections'])} sentence clips local practice")
