# 临时公开分享副本：SellerSprite Market Keywords

此仓库是临时分享副本，任何人都可以访问。源仓库保持私有且未修改。

- 当前 Skill 说明：[SKILL.md](SKILL.md)
- 当前打包版本：`sellersprite-market-keywords-v1.6.2.skill`
- 源目录中的历史版本包也随快照保留；当前版本以 `VERSION` 为准。
- 来源：`CN-Bobby/Bobby_Skills_Group`，提交 `ef447da2b9785c8ac921350c706dd858b18794f2`。

详见 [TEMPORARY_SHARE.md](TEMPORARY_SHARE.md)。

# sellersprite-market-keywords

SellerSprite MCP市场关键词调研Skill——以可选历史月份固定采集3页并收录全部去重词分析市场需求，以每ASIN一次当前查询生成自然/广告位矩阵与流量占比矩阵，并输出24月搜索量/ABA Rank趋势、动态集中度象限及严格证据产品方向。

- **版本**：1.6.2（详见 [CHANGELOG.md](CHANGELOG.md)）
- **安装**：使用 `sellersprite-market-keywords-v1.6.2.skill` 安装包；或直接以本目录作为Skill目录
- **入口**：[SKILL.md](SKILL.md)（触发词、使用流程、边界）
- **源码**：`scripts/`（Python 脚本）、`references/`（分析框架、指标定义、MCP 路由等）、`assets/`（报告模板）、`agents/`（Agent 配置）
- **发布机制**：[RELEASE.md](RELEASE.md)；`VERSION` 为唯一版本源，`scripts/package_release.py` 负责构建/校验安装包和 `SHA256SUMS`

> 本目录为展开源码，供审查与维护；分发请使用 `.skill` 安装包（两者内容一致，并由 `SHA256SUMS` 审计）。

