import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
import career_finder as cf

PROFILE = json.loads((cf.ROOT/'examples/supcon-cqe.json').read_text())


class CareerTests(unittest.TestCase):
    def test_full_cqe_case_has_three_workstreams_and_traceable_sources(self):
        r = cf.build_report(PROFILE, today=date(2026, 10, 24))
        self.assertTrue({'complaints', 'hardware', 'software'} <= {m['id'] for m in r['modules']})
        ids = {s['id'] for s in r['sources']}
        for item in r['modules'] + r['certificates']:
            self.assertTrue(item['source_ids'])
            self.assertTrue(set(item['source_ids']) <= ids)
        self.assertEqual(r['completed_queries'], 0)
        self.assertIn('未在线搜索', r['mode'])

    def test_no_industry_framework_leaks_to_unrelated_role(self):
        r = cf.build_report(dict(company='示例银行', role='产品经理', industry='金融'))
        self.assertEqual(r['certificates'], [])
        self.assertEqual(r['modules'], [])
        self.assertIn('示例银行', r['queries'][0]['query'])

    def test_other_automation_company_does_not_inherit_supcon_products(self):
        r = cf.build_report(dict(PROFILE, company='示例自动化企业'))
        self.assertNotIn('supcon-dcs', {s['id'] for s in r['sources']})
        self.assertNotIn('supcon-sis', {s['id'] for s in r['sources']})
        self.assertTrue(r['modules'])

    def test_unknown_eligibility_is_not_reported_as_qualified(self):
        r = cf.build_report(PROFILE)
        cqe = next(c for c in r['certificates'] if c['id'] == 'asq-cqe')
        self.assertIn('未知', cqe['eligibility'])
        self.assertIn('不是 Customer Quality Engineer', cqe['caution'])
        self.assertIn('不提供学历年限豁免', next(s['excerpt_zh'] for s in r['sources'] if s['id']=='asq-gb'))

    def test_missing_key_is_explicit(self):
        r = cf.build_report(PROFILE, online=True, key='')
        self.assertEqual(r['completed_queries'], 0)
        self.assertTrue(r['warnings'])
        self.assertIn('未完成', r['mode'])

    def test_online_results_dedup_and_no_false_verification(self):
        def fake(url, headers):
            self.assertIn('q=', url)
            self.assertEqual(headers['X-Subscription-Token'], 'test-only')
            return {'web': {'results': [
                {'title':'ASQ', 'url':'https://www.asq.org/cert/quality-engineer?utm_source=a'},
                {'title':'ASQ duplicate', 'url':'https://www.asq.org/cert/quality-engineer'},
                {'title':'not ASQ', 'url':'https://asq.org.evil.example/cert'},
                {'title':'bad', 'url':'javascript:alert(1)'}]}}
        found, warnings, completed = cf.online_search(cf.queries_for(PROFILE), key='test-only', getter=fake, limit=1)
        self.assertEqual(completed, 1)
        self.assertFalse(warnings)
        self.assertEqual(len(found), 2)
        self.assertTrue(found[0]['official_domain'])
        self.assertFalse(found[1]['official_domain'])
        self.assertIn('未核验', found[0]['verification'])

    def test_api_failure_does_not_leak_key_or_fake_success(self):
        def fail(*_):
            raise OSError('SECRET-value')
        found, warnings, completed = cf.online_search(cf.queries_for(PROFILE), key='SECRET-value', getter=fail, limit=1)
        self.assertEqual(completed, 0)
        self.assertEqual(found, [])
        self.assertNotIn('SECRET', str(warnings))

    def test_stale_snapshot_warning(self):
        r = cf.build_report(PROFILE, today=date(2027, 3, 1))
        self.assertTrue(any('90 天' in w for w in r['warnings']))

    def test_malformed_provider_response_is_not_a_search_success(self):
        for response in (None, {'web': None}, {'web': {'results': 'invalid'}}):
            _, warnings, completed = cf.online_search(cf.queries_for(PROFILE), key='test', getter=lambda *_: response, limit=1)
            self.assertEqual(completed, 0)
            self.assertTrue(warnings)

    def test_focus_filters_optional_security_certificate(self):
        r = cf.build_report(dict(PROFILE, focus=['complaints']))
        self.assertNotIn('isa-ot', {c['id'] for c in r['certificates']})
        self.assertNotIn('hardware', {m['id'] for m in r['modules']})

    def test_html_escapes_untrusted_titles(self):
        rendered = cf.html_report('# <script>alert(1)</script>\n[bad](javascript:alert(1))\n[ASQ](https://asq.org)')
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('href="javascript:', rendered)
        self.assertIn('href="https://asq.org"', rendered)

    def test_invalid_profile_is_rejected(self):
        for profile in (dict(PROFILE, role=''), dict(PROFILE, focus=['unknown']), dict(PROFILE, company_domains=['bad/path'])):
            with self.assertRaises(ValueError):
                cf.build_report(profile)

    def test_cli_creates_readable_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = str(Path(tmp)/'report')
            with patch('sys.argv', ['career_finder.py', '--no-ai', '--output', base]):
                self.assertEqual(cf.main(), 0)
            for ext in ('html','md','json'):
                self.assertTrue(Path(base+'.'+ext).is_file())
            r=json.loads(Path(base+'.json').read_text())
            self.assertEqual(r['profile']['company'], '中控技术')
