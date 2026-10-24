# 《逆天邪神》验证

核查日期：2026-10-24；作者：火星引力。

- 官方作品页：https://www.zongheng.com/detail/408586
- 官方目录：https://api.zongheng.com/app/directory/408586
- 官方目录标注 VIP；未核实整本下载授权。
- 预期：搜索返回正版入口；下载 zongheng:408586 拒绝，不访问章节或保存小说正文。
- 自动测试覆盖该行为、版权状态缺失/受限、网络故障、分页去重、原始文件保存、不完整文件拒绝、覆盖保护及域名校验。
- 下载成功测试用原创夹具，不代表《逆天邪神》整本下载成功。

## 实际运行结果

- `python3 -m unittest discover -s tests -v`：7 项通过。
- `python3 novel_finder.py search 逆天邪神`：纵横入口返回，在线目录查询成功，warnings 为空，无额外匹配结果。
- `python3 novel_finder.py download zongheng:408586 --confirm-local-rights`：退出码 1，提示 VIP 和未核实下载授权，未生成正文。
- 本机 Python 默认 CA 配置缺失；程序在存在系统 `/etc/ssl/cert.pem` 时加载该可信证书库，保持 HTTPS 证书验证开启。
