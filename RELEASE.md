# 发布与版本机制

`VERSION` 是本 Skill 的唯一版本源（采用 `MAJOR.MINOR.PATCH`）。所有发布均以展开源码、同版本 `.skill` 安装包和 `SHA256SUMS` 三件套交付。

## 版本规则

- `PATCH`：不改变输入、调用预算、Sheet 结构或指标含义的修复、文档和测试更新。
- `MINOR`：默认采集策略、调用预算、报告结构、标签枚举或可见分析口径发生兼容性变化。
- `MAJOR`：输入契约、既有输出含义或安装方式发生不兼容变化。

每次升级必须同步修改 `VERSION`、`SKILL.md` frontmatter/正文、`agents/openai.yaml`、`README.md`、`CHANGELOG.md`，并更新安装包文件名。

## 本地发布步骤

在 Skill 根目录执行：

```powershell
$env:PYTHONUTF8 = '1'
python scripts/package_release.py --build
python scripts/package_release.py --check
python C:\Users\Administrator\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
python -m unittest discover -s tests -p 'test_*.py'
```

`package_release.py` 会从展开源码生成 `sellersprite-market-keywords-v<VERSION>.skill`，并写入 `SHA256SUMS`。校验时会解包比对每个发布文件的内容；缓存、Python 字节码、旧版 `.skill` 和 `SHA256SUMS` 本身不进入安装包。

## GitHub 更新机制

1. 从 `main` 创建 `release/sellersprite-market-keywords-v<VERSION>` 分支。
2. 提交展开源码、当前 `.skill` 和 `SHA256SUMS`；不得提交任务 `raw/`、`cache/`、`output/`、密钥或 `__pycache__/`。
3. 创建草稿 PR 到 `main`。`.github/workflows/validate-sellersprite-market-keywords.yml` 必须通过 Skill 结构校验、单元测试和安装包一致性校验。
4. 人工审阅并合并后，再创建同名 Git tag：`sellersprite-market-keywords-v<VERSION>`。旧版本安装包继续保留，回滚使用 Git revert 或重新安装旧包。

## 发布验收

- GitHub 上 `VERSION`、README、CHANGELOG、Skill frontmatter、`agents/openai.yaml` 均指向同一版本。
- `SHA256SUMS` 中的安装包哈希与上传文件一致，且包内文件与展开源码逐文件一致。
- PR 的自动校验通过，合并后复读 `main` 的版本和哈希文件。

