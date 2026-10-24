import tempfile
import unittest
from pathlib import Path
from novel_finder import search, download, normalize, trusted


def book():
    return dict(id=1, title='原创测试', authors=[], languages=['zh'], copyright=False, media_type='Text', formats={'text/plain; charset=utf-8': 'https://www.gutenberg.org/1.txt'})


class Tests(unittest.TestCase):
    def test_requested_novel(self):
        result = search('逆天邪神', getter=lambda _: dict(results=[], next=None))
        self.assertEqual(result['results'][0]['id'], 'zongheng:408586')
        self.assertFalse(result['results'][0]['downloadable'])
        with self.assertRaisesRegex(ValueError, 'VIP'):
            download('zongheng:408586', '.')

    def test_restricted_or_unknown(self):
        for status in (True, None, 0):
            b = book()
            b['copyright'] = status
            self.assertFalse(normalize(b)['downloadable'])

    def test_pagination(self):
        calls = []
        def get(url):
            calls.append(url)
            return dict(results=[book()], next='https://gutendex.com/books/?page=2')
        self.assertEqual(len(search('测试', 2, get)['results']), 1)
        self.assertEqual(len(calls), 2)

    def test_network_failure(self):
        def fail(_):
            raise OSError('offline')
        r = search('逆天邪神', getter=fail)
        self.assertTrue(r['warnings'])
        self.assertEqual(len(r['results']), 1)

    def test_download_and_overwrite(self):
        payload = b'*** START OF THE PROJECT GUTENBERG EBOOK TEST ***\nOriginal fixture\n*** END OF THE PROJECT GUTENBERG EBOOK TEST ***'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(download('gutenberg:1', tmp, lambda _: book(), lambda *_: payload))
            self.assertEqual(path.read_bytes(), payload)
            self.assertTrue(path.with_suffix('.receipt.json').exists())
            with self.assertRaises(FileExistsError):
                download('gutenberg:1', tmp, lambda _: book(), lambda *_: payload)

    def test_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                download('gutenberg:1', tmp, lambda _: book(), lambda *_: b'incomplete')
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_bad_sources(self):
        for url in ('http://www.gutenberg.org/a', 'https://evil.example/a', 'https://user@www.gutenberg.org/a'):
            with self.assertRaises(ValueError):
                trusted(url, {'www.gutenberg.org'})
        with self.assertRaises(ValueError):
            download('../../x', '.')
