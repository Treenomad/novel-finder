# Novel Finder · 中文小说寻书

无第三方依赖的 Python 3.10+ 命令行工具。搜索中文书名或作者，展示正版入口，并下载可用的中文公版 TXT。

```sh
python3 novel_finder.py search '逆天邪神'
python3 novel_finder.py search '聊齋' --pages 2
python3 novel_finder.py download gutenberg:数字ID --confirm-local-rights
python3 -m unittest discover -s tests -v
```

将 `gutenberg:数字ID` 替换为搜索结果中的完整 ID。默认存入 downloads/，可用 --output 指定目录。

## 范围与来源

- 在线搜索接入 [Gutendex](https://gutendex.com/) 的 Gutenberg 中文目录，支持 1—10 页，分页去重。中文书名可尝试繁体写法。
- 《逆天邪神》采用内置、人工核实的[纵横正版入口](https://www.zongheng.com/detail/408586)，并非实时全网检索。其[官方目录](https://api.zongheng.com/app/directory/408586)标注 VIP；未核实整本下载授权，因此不会开放全文下载。
- 下载时重新核实中文、公版标记和 TXT 来源，仅接受 Gutenberg HTTPS 域名。保留原始文件及许可，拒绝覆盖已有小说文件。
- 检查 UTF-8 和 Gutenberg 首尾标记；保存字节数、SHA-256 与来源凭据。首尾齐全不代表已逐章核验原版。
- Gutenberg 公版标记以美国为范围，使用者应核实所在地适用情况；参阅[许可说明](https://www.gutenberg.org/policy/license.html)。
- 网络故障会报告 warnings，不冒充零结果。不覆盖全网，不绕过付费或访问限制。不支持 EPUB、断点续传或网页界面。

## 验证

见 [验证记录](docs/verification.md)。成功下载分支用原创夹具测试，不包含小说正文。下载文件不提交仓库。
