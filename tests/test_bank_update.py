from __future__ import annotations

import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from bank_update import collect, due_for_daily_refresh, parse_tuonidefu, parse_yaquan, season_for


def fake_fetch(url: str) -> str:
    if '/recalls/2026-09' in url:
        return '<a href="/reading/2026-sep-hf-1"></a><a href="/listening/2026-sep-hf-1"></a>'
    if '/recalls/2027-01' in url:
        return '<a href="/reading/2027-jan-hf-1"></a><a href="/listening/2027-jan-hf-1"></a>'
    if 'yaquan.site' in url:
        return ('<a href="/paper/old">old</a><span>Task 2 · 2026.9.16北京</span>'
                '<a href="/paper/new">new</a><span>Task 1 · 2027.1.2上海</span>'
                '<a href="/paper/future">future</a><span>Task 2 · 2027.1.3上海</span>')
    return ''


class SeasonTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(season_for(date(2026, 4, 30)).id, '2026-01_2026-04')
        self.assertEqual(season_for(date(2026, 5, 1)).id, '2026-05_2026-08')
        self.assertEqual(season_for(date(2026, 8, 31)).id, '2026-05_2026-08')
        self.assertEqual(season_for(date(2026, 9, 1)).id, '2026-09_2026-12')
        self.assertEqual(season_for(date(2027, 1, 1)).id, '2027-01_2027-04')

    def test_rollover_clears_previous_season(self):
        old = collect(date(2026, 12, 31), fake_fetch)
        self.assertEqual([x['month'] for x in old['reading']], ['2026-09'])
        new = collect(date(2027, 1, 2), fake_fetch, old)
        self.assertEqual(new['season']['id'], '2027-01_2027-04')
        self.assertEqual([x['month'] for x in new['reading']], ['2027-01'])
        self.assertEqual([x['month'] for x in new['writing']], ['2027-01'])
        self.assertFalse(any('2026' in x['url'] for field in ('reading','listening','writing','recallLeads') for x in new[field]))

    def test_same_season_failure_retains_previous_source(self):
        old = collect(date(2026, 9, 16), fake_fetch)
        def offline(_url: str) -> str:
            raise OSError('offline')
        new = collect(date(2026, 9, 17), offline, old)
        self.assertEqual(new['reading'], old['reading'])
        self.assertEqual(new['writing'], old['writing'])
        self.assertTrue(any(x['retainedFromSameSeason'] for x in new['sourceStatus']))

    def test_new_season_failure_does_not_retain_old_bank(self):
        old = collect(date(2026, 12, 31), fake_fetch)
        def offline(_url: str) -> str:
            raise OSError('offline')
        new = collect(date(2027, 1, 1), offline, old)
        self.assertFalse(any(new[field] for field in ('reading','listening','writing','recallLeads')))
        self.assertEqual(new['season']['id'], '2027-01_2027-04')

    def test_future_writing_is_not_published(self):
        items = parse_yaquan(fake_fetch('https://www.yaquan.site'), season_for(date(2027, 1, 2)), date(2027, 1, 2))
        self.assertEqual([x['url'] for x in items], ['https://www.yaquan.site/paper/new'])

    def test_daily_run_beijing_time(self):
        tz = ZoneInfo('Asia/Shanghai')
        yesterday = date(2026, 10, 26)
        self.assertFalse(due_for_daily_refresh(datetime(2026,10,27,7,59,tzinfo=tz), yesterday))
        self.assertTrue(due_for_daily_refresh(datetime(2026,10,27,8,0,tzinfo=tz), yesterday))
        self.assertFalse(due_for_daily_refresh(datetime(2026,10,27,8,1,tzinfo=tz), date(2026,10,27)))

    def test_weekly_recap_excludes_previous_and_future_periods(self):
        html = ''.join(
            f'<a href="/blogs/{n}" aria-label="阅读文章：{title}"><div create_timestamp="{day}T01:00:00Z">'
            for n, title, day in [
                (1, '8月29日-9月5日雅思考试回忆', '2026-09-06'),
                (2, '9月21日-9月27日雅思机考回忆', '2026-09-27'),
                (3, '11月雅思机考回忆', '2026-11-02'),
                (4, '10月雅思口语回忆', '2026-10-12'),
            ])
        items = parse_tuonidefu(html, season_for(date(2026,10,27)), date(2026,10,27))
        self.assertEqual([x['id'] for x in items], ['T-2'])


if __name__ == '__main__':
    unittest.main()
