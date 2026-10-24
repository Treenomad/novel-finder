"""中文寻书：Python 3.10+，无第三方依赖。"""
import argparse
import hashlib
import json
import re
import sys
import ssl
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

API = 'https://gutendex.com/books/'
OFFICIAL = dict(id='zongheng:408586', title='逆天邪神', authors=['火星引力'], source='纵横中文网', url='https://www.zongheng.com/detail/408586', downloadable=False, formats={}, reason='官方目录标注 VIP；未核实整本下载授权。', evidence='https://api.zongheng.com/app/directory/408586', checked_on='2026-10-24')


def trusted(url, hosts):
    p = urlparse(url)
    if p.scheme != 'https' or p.hostname not in hosts or p.username or p.password or p.port not in (None, 443):
        raise ValueError('来源地址不在允许范围内')


def fetch(url, hosts):
    trusted(url, hosts)
    context = ssl.create_default_context()
    if Path('/etc/ssl/cert.pem').is_file():
        context.load_verify_locations('/etc/ssl/cert.pem')
    with urlopen(Request(url, headers={'User-Agent': 'NovelFinder/0.1'}), timeout=30, context=context) as r:
        trusted(r.url, hosts)
        body = r.read(20_000_001)
        if len(body) > 20_000_000:
            raise ValueError('文件过大')
        return body


def api(url):
    return json.loads(fetch(url, {'gutendex.com'}))


def normalize(b):
    permitted = b.get('copyright') is False and 'zh' in b.get('languages', []) and b.get('media_type') == 'Text'
    f = b.get('formats', {})
    txt = f.get('text/plain; charset=utf-8') or f.get('text/plain')
    return dict(id='gutenberg:' + str(b['id']), title=b['title'], authors=[a['name'] for a in b.get('authors', [])], source='Project Gutenberg / Gutendex', url='https://www.gutenberg.org/ebooks/' + str(b['id']), downloadable=bool(permitted and txt), formats={'txt': txt} if permitted and txt else {}, reason='目录按美国公版标注；需核实所在地适用情况，保留原文件许可。' if permitted else '未确认中文公版状态')


def search(query, pages=1, getter=api):
    if not query.strip():
        raise ValueError('请输入书名或作者')
    books = [dict(OFFICIAL)] if query in ('逆天邪神', '火星引力') else []
    warnings, seen = [], set()
    url = API + '?' + urlencode(dict(search=query, languages='zh', copyright='false'))
    try:
        for _ in range(pages):
            if not url or url in seen:
                break
            trusted(url, {'gutendex.com'})
            seen.add(url)
            data = getter(url)
            books.extend(normalize(b) for b in data['results'])
            url = data.get('next')
    except (OSError, ValueError, KeyError) as e:
        warnings.append('在线目录查询失败：' + str(e))
    return dict(query=query, results=list({b['id']: b for b in books}.values()), warnings=warnings)


def download(book_id, directory, getter=api, fetcher=fetch):
    if book_id == OFFICIAL['id']:
        raise ValueError(OFFICIAL['reason'] + OFFICIAL['url'])
    if not re.fullmatch(r'gutenberg:[1-9][0-9]*', book_id):
        raise ValueError('请使用搜索结果中的 gutenberg:数字 ID')
    number = book_id.split(':')[1]
    raw = getter(API + number)
    if str(raw['id']) != number:
        raise ValueError('作品 ID 不匹配')
    book = normalize(raw)
    if not book['downloadable']:
        raise ValueError('没有已核实的中文公版 TXT 来源')
    url = book['formats']['txt']
    hosts = {'www.gutenberg.org', 'gutenberg.org'}
    trusted(url, hosts)
    payload = fetcher(url, hosts)
    text = payload.decode('utf-8-sig')
    if '*** START OF THE PROJECT GUTENBERG' not in text.upper() or '*** END OF THE PROJECT GUTENBERG' not in text.upper():
        raise ValueError('缺少文件首尾标记，无法确认完整性')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    name = re.sub(r'[^\w -]', '_', book['title'])[:80]
    path = directory / (number + '-' + name + '.txt')
    with path.open('xb') as f:
        f.write(payload)
    receipt = dict(book, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(), download_url=url)
    path.with_suffix('.receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest='command', required=True)
    s = subs.add_parser('search')
    s.add_argument('query')
    s.add_argument('--pages', type=int, choices=range(1, 11), default=1)
    d = subs.add_parser('download')
    d.add_argument('id')
    d.add_argument('--output', default='downloads')
    d.add_argument('--confirm-local-rights', action='store_true')
    a = p.parse_args()
    try:
        if a.command == 'search':
            print(json.dumps(search(a.query, a.pages), ensure_ascii=False, indent=2))
        else:
            if not a.confirm_local_rights:
                raise ValueError('请先核实所在地权利，并添加 --confirm-local-rights')
            print(download(a.id, a.output))
        return 0
    except (OSError, ValueError, KeyError) as e:
        print('错误：' + str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
