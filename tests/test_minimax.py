import tempfile
import unittest
from pathlib import Path
from minimax_support import load_env, analyze, post_json


class MiniMaxTests(unittest.TestCase):
    def test_local_env_no_execution_and_existing_env_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'.env'
            p.write_text('# comment\nMINIMAX_API_KEY="test-value"\nMINIMAX_MODEL=test-model\nOTHER=ignored\n')
            env={'MINIMAX_MODEL':'existing'}
            load_env(p, env)
            self.assertEqual(env, {'MINIMAX_MODEL':'existing','MINIMAX_API_KEY':'test-value'})

    def test_prompt_excludes_config_and_response_redacts_secret(self):
        r=dict(profile={},modules=[],certificates=[],sources=[],discoveries=[])
        def sender(url, payload, key):
            self.assertNotIn('private-test-key', str(payload))
            self.assertEqual(key, 'private-test-key')
            return {'choices':[{'finish_reason':'stop','message':{'content':'<think>internal</think>建议 private-test-key'}}]}
        text,warning=analyze(r, {'MINIMAX_API_KEY':'private-test-key'}, sender)
        self.assertFalse(warning)
        self.assertNotIn('private-test-key',text)
        self.assertNotIn('internal',text)

    def test_failures_keep_credentials_private(self):
        def fail(*_):
            raise OSError('private-test-key')
        r=dict(profile={},modules=[],certificates=[],sources=[],discoveries=[])
        text,warning=analyze(r, {'MINIMAX_API_KEY':'private-test-key'}, fail)
        self.assertEqual(text,'')
        self.assertTrue(warning)
        self.assertNotIn('private-test-key',warning)

    def test_untrusted_endpoint_rejected_before_transmission(self):
        for url in ('https://evil.example/v1/chat/completions','http://api.minimaxi.com/v1/chat/completions','https://api.minimaxi.com.evil.example/v1/chat/completions'):
            with self.assertRaises(ValueError):
                post_json(url, {}, 'dummy')

    def test_missing_key_never_sends(self):
        def fail(*_):
            self.fail('unexpected API request')
        self.assertEqual(analyze({}, {}, fail), ('',''))
