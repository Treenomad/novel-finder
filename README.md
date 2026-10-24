# Career Finder · 行业与岗位学习搜索

输入**公司、岗位、行业和工作主线**，生成有来源的知识框架、证书候选与检索计划。

从原 Novel Finder 改造：保留来源查询、去重、网络错误提示的思路；移除找小说与下载正文功能。为避免增加仓库，暂沿用 `novel-finder` 仓库地址。项目使用 Python 3.9+，无第三方依赖。

## 直接使用：中控 CQE 案例

```sh
python3 career_finder.py
open reports/latest.html   # macOS；Windows 可直接双击生成的 HTML
```

Mac 也可以在项目目录双击 `生成学习报告.command`。如果 macOS 阻止脚本运行，使用上面的终端命令。

无需密钥即可查看人工查证的案例、知识体系、证书门槛和可点击的搜索入口。快照不是实时全网搜索。

示例画像：中控技术质量管理部 CQE（客户质量工程师），工业自动化／流程工业自动化；覆盖客诉闭环、硬件可靠性、软件与系统交付三条线。见 [画像](examples/supcon-cqe.json) 和 [示例报告](docs/supcon-cqe-report.md)。不包含个人姓名、客户资料、内部日志或公司保密文件。

## 自定义画像

```sh
python3 career_finder.py --company '你的公司' --role '你的岗位' --industry '你的行业'
python3 career_finder.py --profile examples/supcon-cqe.json --output reports/my-report
```

JSON 中 `focus` 可选 `complaints`（客诉）、`hardware`（硬件）、`software`（软件/交付），支持多选；`company_domains` 可填写经你确认的官网域名。

当前已核实的知识框架仅覆盖工业自动化客户质量岗位。其他画像会生成对应搜索计划，不伪造其他行业的体系和证书；其他公司不会继承中控专属产品来源。

## 真正的在线搜索（可选）

接入 [Brave Search API](https://api-dashboard.search.brave.com/documentation/quickstart)。自备密钥并设置 `BRAVE_SEARCH_API_KEY` 环境变量，再运行：

```sh
python3 career_finder.py --online --query-limit 3
```

一次默认最多 3 次查询，每次最多 5 条线索；可调整到 1—7 次。调用量可能产生服务商费用；项目不提供或购买 API 额度。密钥只通过请求头发送给 Brave，不写入报告或仓库。在线查询会将画像形成的检索词发给搜索服务，不要填入客户机密。

未设置密钥时会明确提示，并以退出码 2 标识在线检索未完成，仍生成可读报告。无需密钥也可以点击报告内的检索链接，在浏览器自行搜索。

新搜索结果只是**原文未核验的线索**。机构域名匹配不等于证书规则已经核实，也不自动追加到推荐清单。不会宣称搜索了互联网所有页面，也不会把 HTTP 可访问当成资格或有效性核验。

## 输出与证据

默认生成 `reports/latest.html`、`.md`、`.json`：

- 知识模块、学习顺序、实践成果和原始来源链接；岗位映射明确标为编辑建议。
- 发证机构、证书类型、适用场景、门槛和未知资格。
- 来源题名、机构、原始片段与中文直译、访问状态、核验日期。
- 资料快照、未核验线索与待核实候选分开显示；快照超过 90 天提示重新查证。

岗位 **Customer Quality Engineer** 不等于 ASQ **Certified Quality Engineer**。ISO 9001 组织认证、培训结业证、个人专业认证和机构专项证书也不是同一类。

建议优先级不是公司要求或就业效果承诺。实际报名前需核对经验、学历、语言、预算、所在地考试可用性和企业认可情况。当前不自动评分、生成所谓成功概率，也不自动报名。

## 验证与维护

```sh
python3 -m unittest discover -s tests -v
```

见 [验证记录](docs/verification.md)。资料在 `data/automation_quality.json`，核验日期为 2026-10-24；历史代码仍在 Git 历史中。在线接口用固定响应测试，未使用真实付费密钥调用，不将模拟测试写成实时 API 验证成功。
