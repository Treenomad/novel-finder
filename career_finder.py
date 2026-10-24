"""Career Finder：公司 × 岗位 × 行业的来源检索与学习框架。"""
import argparse
import copy
import html
import json
import os
import ssl
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from minimax_support import load_env, analyze

ROOT = Path(__file__).resolve().parent
FOCUS = {'complaints': '客户投诉与现场闭环', 'hardware': '硬件可靠性与失效分析', 'software': '软件及系统交付质量'}
TRUSTED = {'asq.org', 'isa.org', 'iso.org', 'iec.ch', 'nist.gov', 'tuv.com', 'caq.org.cn'}


def canonical(url):
    p = urlparse(url)
    if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password:
        raise ValueError('无效的来源 URL')
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ('gclid', 'fbclid')]
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path.rstrip('/') or '/', '', urlencode(sorted(query)), ''))


def host_matches(host, domain):
    return host == domain or host.endswith('.' + domain)


def official_domain(url, company_domains=()):
    host = urlparse(url).hostname or ''
    return any(host_matches(host, d) for d in TRUSTED | set(company_domains))


def validate_profile(profile):
    for key in ('company', 'role', 'industry'):
        if not isinstance(profile.get(key), str) or not profile[key].strip() or len(profile[key]) > 200:
            raise ValueError(key + ' 需要 1—200 个字符')
    focus = profile.get('focus', list(FOCUS))
    if not isinstance(focus, list) or not focus or any(f not in FOCUS for f in focus):
        raise ValueError('focus 只能选择 complaints、hardware、software，且不能为空')
    domains = profile.get('company_domains', [])
    if not isinstance(domains, list):
        raise ValueError('company_domains 必须是域名列表')
    for d in domains:
        if not isinstance(d, str) or '.' not in d or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789.-' for c in d):
            raise ValueError('公司域名格式无效')
    return dict(profile, focus=list(dict.fromkeys(focus)), company_domains=domains)


def queries_for(p):
    base = f'{p["company"]} {p["role"]} {p["industry"]}'
    queries = [base + ' 岗位职责 产品 技术文档', base + ' 知识体系 学习 官方', base + ' 认证 证书 报考条件 官方', f'{p["industry"]} customer quality engineer body of knowledge certification']
    for focus in p['focus']:
        queries.append(f'{p["industry"]} {FOCUS[focus]} 标准 方法 官方')
    return [dict(query=q, search_url='https://www.bing.com/search?' + urlencode({'q': q})) for q in queries]


def fetch_json(url, headers):
    context = ssl.create_default_context()
    if Path('/etc/ssl/cert.pem').is_file():
        context.load_verify_locations('/etc/ssl/cert.pem')
    req = Request(url, headers={'User-Agent': 'CareerFinder/0.2', **headers})
    with urlopen(req, timeout=20, context=context) as response:
        body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError('搜索响应过大')
        return json.loads(body)


def online_search(queries, company_domains=(), key=None, getter=fetch_json, limit=3):
    key = key if key is not None else os.environ.get('BRAVE_SEARCH_API_KEY', '')
    if not key:
        return [], ['未执行在线搜索：未设置 BRAVE_SEARCH_API_KEY。可直接使用报告里的网页检索链接。'], 0
    found, warnings, completed = {}, [], 0
    for entry in queries[:limit]:
        endpoint = 'https://api.search.brave.com/res/v1/web/search?' + urlencode({'q': entry['query'], 'count': 5})
        try:
            data = getter(endpoint, {'X-Subscription-Token': key, 'Accept': 'application/json'})
            if not isinstance(data, dict) or not isinstance(data.get('web'), dict) or not isinstance(data['web'].get('results'), list):
                raise ValueError('搜索服务响应格式异常')
            completed += 1
            for item in data['web']['results']:
                try:
                    url = canonical(item['url'])
                    found.setdefault(url, dict(title=str(item.get('title', url)), url=url, snippet=str(item.get('description', '')), official_domain=official_domain(url, company_domains), verification='搜索线索，原文未核验；不据此推荐新证书'))
                except (ValueError, KeyError, TypeError):
                    continue
        except (OSError, ValueError, KeyError, TypeError):
            # 不回显请求头或异常对象，避免服务端报错中含有密钥。
            warnings.append('一条查询失败：搜索接口连接或响应异常；请检查密钥、配额与网络。')
    return sorted(found.values(), key=lambda x: not x['official_domain']), warnings, completed


def supported(p):
    role, industry = p['role'].casefold(), p['industry'].casefold()
    return any(x in role for x in ('cqe', '客户质量', 'customer quality')) and any(x in industry for x in ('自动化', 'automation', '流程工业', 'process industr'))


def build_report(profile, online=False, key=None, getter=fetch_json, limit=3, today=None):
    p = validate_profile(profile)
    data = json.loads((ROOT / 'data/automation_quality.json').read_text(encoding='utf-8'))
    now = today or datetime.now(ZoneInfo('Asia/Shanghai')).date()
    queries = queries_for(p)
    result = dict(profile=p, generated_on=now.isoformat(), evidence_checked_on=data['checked_on'], mode='已核验资料快照 + 按画像生成的检索计划（未在线搜索）', queries=queries, modules=[], certificates=[], sources=[], pending=[], discoveries=[], warnings=[], completed_queries=0)
    if supported(p):
        result['modules'] = [copy.deepcopy(m) for m in data['modules'] if set(m['focus']) & set(p['focus'])]
        result['certificates'] = [copy.deepcopy(c) for c in data['certificates'] if set(c['focus']) & set(p['focus'])]
        source_ids = {s for item in result['modules'] + result['certificates'] for s in item['source_ids']}
        supcon = any(x in p['company'].casefold() for x in ('中控技术', 'supcon'))
        if not supcon:
            source_ids -= {'supcon-dcs', 'supcon-sis'}
            for m in result['modules']:
                m['source_ids'] = [s for s in m['source_ids'] if s in source_ids]
                if m['id'] == 'systems':
                    m['source_ids'].append('nist-ot')
                    source_ids.add('nist-ot')
            result['warnings'].append('未核实该公司的产品与内部职责；已排除中控专属产品来源。')
        result['sources'] = [s for s in data['sources'] if s['id'] in source_ids]
        result['pending'] = data['pending']
    else:
        result['warnings'].append('当前无该行业与岗位的已核验知识框架；仅生成检索计划，不套用工业 CQE 证书建议。')
    if (now - date.fromisoformat(data['checked_on'])).days > 90:
        result['warnings'].append('资料核验日期距今超过 90 天：报名条件、标准版本及有效性需重新核验。')
    if online:
        results, warnings, completed = online_search(queries, p['company_domains'], key, getter, limit)
        result.update(discoveries=results, completed_queries=completed, mode='已核验资料快照 + 在线检索线索' if completed else '在线检索未完成；保留快照与检索计划')
        result['warnings'].extend(warnings)
    return result


def markdown(r):
    p = r['profile']
    lines = ['# Career Finder · 岗位学习与认证搜索', '', f'画像：{p["company"]} / {p["role"]} / {p["industry"]}', f'工作主线：{"、".join(FOCUS[x] for x in p["focus"])}', f'生成：{r["generated_on"]}；来源核验：{r["evidence_checked_on"]}', f'运行模式：{r["mode"]}；成功在线查询：{r["completed_queries"]}', '', '框架与优先级是基于公开资料的编辑建议，不是公司内部岗位标准，也不代表雇主认可某证书。尚缺：工作年限、学历、预算、英语水平、内部职责与考证报销政策。', '岗位 CQE = 客户质量工程师；ASQ CQE = Certified Quality Engineer，两者不得混同。', '建议先完成真实问题的证据链和改善成果，再按工作任务选择证书；不以证书数量衡量能力。', '']
    if r['warnings']:
        lines += ['## 需要注意', ''] + ['- ' + w for w in r['warnings']] + ['']
    if r.get('ai_analysis'):
        lines += ['## MiniMax 行动建议（AI 生成，未经人工核验）', '', r['ai_analysis'], '']
    sources = {s['id']: s for s in r['sources']}
    def links(ids):
        return '；'.join(f'[{sources[s]["organization"]}：{sources[s]["title_zh"]}]({sources[s]["url"]})' for s in ids if s in sources)
    lines += ['## 知识体系（编辑建议）', '']
    for i, m in enumerate(r['modules'], 1):
        lines += [f'### {i}. {m["title"]} · {m["priority"]}', '', *['- ' + t for t in m['topics']], '', '实践成果：' + m['deliverable'], '依据：' + links(m['source_ids']), '']
    if r['modules']:
        lines += ['学习顺序：先补客诉闭环和系统架构；硬件、软件两条线随实际案例并行；统计工具服务于真实改进；SIS 与 OT 按项目深化。此顺序是建议，不是考证要求。', '', '标准版本：ISO 官网当前页为 ISO 9001:2026；企业正在执行哪个版本与过渡安排需内部确认。NIST SP 800-82r3 页面同时提示 r4 草案，勿将草案当成已发布正式版。', '']
    lines += ['## 个人认证与专项证书候选', '', '“官方”指发证机构的原始规则；不是国家职业资格的统一背书。费用、考点和语言以报名时官网为准；没有验证到的字段不填写。', '']
    for c in r['certificates']:
        lines += ['### ' + c['name'], '', '- 发证机构／类型：' + c['issuer'] + '／' + c['kind'], '- 建议优先级：' + c['priority'], '- 实际使用条件：' + c['use_when'], '- 官网条件：' + c['requirements'], '- 你的报考资格：' + c['eligibility'], '- 区分：' + c['caution'], '- 原始规则：' + links(c['source_ids']), '']
    lines += ['ISO 9001 是组织质量管理体系标准，不是 ISO 直接颁发的个人证书；培训内审员结业证、人员注册资格和组织体系认证需分别核实。', '']
    if r['pending']:
        lines += ['## 待核实候选（不计入已核验建议）', '']
        for c in r['pending']:
            lines += [f'- [{c["name"]}]({c["url"]})：{c["status"]} {c["next_check"]}', '']
    lines += ['## 按画像生成的全网检索入口', '', '链接是待执行的检索，不代表已搜索所有网页。在线接口也不能穷尽全网。', '']
    lines += [f'- [{q["query"]}]({q["search_url"]})' for q in r['queries']]
    lines += ['', '## 本次在线发现（尚未核验原文）', '']
    for d in r['discoveries']:
        label = '机构域名匹配，内容仍待核验' if d['official_domain'] else '普通网络线索'
        lines += [f'- [{d["title"]}]({d["url"]}) · {label}', '']
    if not r['discoveries']:
        lines += ['本次未取得新增线索；请结合上方模式与警告判断是否执行过在线查询。', '']
    lines += ['## 原始来源与中文直译', '']
    categories = ['企业与机构官网', '学术网站', '标准与监管机构', '行业媒体']
    def source_order(s):
        digits = ''.join(c for c in s['published'] if c.isdigit()).ljust(8, '0')
        return (categories.index(s['category']), s['published'] == '页面未标明', -int(digits or '0'))
    for s in sorted(r['sources'], key=source_order):
        lines += ['### ' + s['title'], '', '中文标题（直译）：' + s['title_zh'], '- 机构：' + s['organization'], '- 来源分类：' + s['category'], '- 页面日期：' + s['published'], '- 核验：' + s['verified_at'] + '，' + s['verification'], '- 访问状态：' + s['access'], f'- [原始页面]({s["url"]})', '- 来源片段：' + s['excerpt'], '- 中文直译：' + s['excerpt_zh'], '']
    return '\n'.join(lines)


def html_report(text):
    import re
    def inline(line):
        # 先转义全文，再仅将合法 HTTP(S) Markdown 链接变为超链接。
        safe = html.escape(line)
        def link(m):
            url = html.unescape(m[2])
            try:
                canonical(url)
            except ValueError:
                return m[0]
            return '<a target="_blank" rel="noopener noreferrer" href="' + html.escape(url, quote=True) + '">' + m[1] + '</a>'
        return re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', link, safe)
    blocks = []
    for line in text.splitlines():
        if line.startswith('### '):
            blocks.append('<h3>' + inline(line[4:]) + '</h3>')
        elif line.startswith('## '):
            blocks.append('<h2>' + inline(line[3:]) + '</h2>')
        elif line.startswith('# '):
            blocks.append('<h1>' + inline(line[2:]) + '</h1>')
        elif line:
            blocks.append('<p>' + inline(line) + '</p>')
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Career Finder · 岗位学习报告</title><style>body{margin:0;background:#f3f6f8;color:#203345;font:16px/1.8 system-ui,sans-serif}main{max-width:960px;margin:36px auto;padding:32px;background:white;border-radius:18px}h1{font-size:30px}h2{margin-top:46px;border-top:1px solid #d8e4eb;padding-top:26px;color:#006b77}h3{margin-top:28px}p{overflow-wrap:anywhere;margin:10px 0}a{color:#006b99} @media(max-width:600px){main{margin:0;padding:20px;border-radius:0}}@media print{main{margin:0;padding:0}}</style><main>' + '\n'.join(blocks) + '</main></html>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, help='JSON 画像；不提供则使用中控 CQE 示例')
    parser.add_argument('--company')
    parser.add_argument('--role')
    parser.add_argument('--industry')
    parser.add_argument('--online', action='store_true', help='调用 Brave Search API，需要自备密钥')
    parser.add_argument('--no-ai', action='store_true', help='跳过 MiniMax 调用，不产生模型费用')
    parser.add_argument('--query-limit', type=int, choices=range(1, 8), default=3)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/latest')
    args = parser.parse_args()
    try:
        load_env(ROOT / '.env')
        custom = [args.company, args.role, args.industry]
        if args.profile and any(custom):
            raise ValueError('--profile 不可与三个画像参数混用')
        if any(custom) and not all(custom):
            raise ValueError('自定义画像需同时提供 --company、--role、--industry')
        if all(custom):
            profile = dict(company=args.company, role=args.role, industry=args.industry)
        else:
            profile = json.loads((args.profile or ROOT / 'examples/supcon-cqe.json').read_text(encoding='utf-8'))
        report = build_report(profile, args.online, limit=args.query_limit)
        if not args.no_ai:
            analysis, warning = analyze(report)
            if analysis:
                report['ai_analysis'] = analysis
            if warning:
                report['warnings'].append(warning)
        text = markdown(report)
        base = args.output
        base.parent.mkdir(parents=True, exist_ok=True)
        Path(str(base) + '.md').write_text(text, encoding='utf-8')
        Path(str(base) + '.html').write_text(html_report(text), encoding='utf-8')
        Path(str(base) + '.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('报告已生成：' + str(base) + '.html')
        print('模式：' + report['mode'])
        for warning in report['warnings']:
            print('提示：' + warning)
        return 2 if args.online and report['completed_queries'] == 0 else 0
    except (OSError, ValueError, KeyError) as e:
        print('错误：' + str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
