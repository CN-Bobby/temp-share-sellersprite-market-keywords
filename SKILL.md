---
name: sellersprite-market-keywords
description: 使用 SellerSprite MCP，基于一个或多个 Amazon ASIN、Node ID 或混合输入（须绑定站点），按可选历史月份批量发现市场关键词，分析需求、集中度、24个月搜索量与ABA排名趋势，并为直接输入ASIN输出自然位、广告位和流量占比矩阵及多Sheet Excel报告。This skill should be used when 用户要求分析 ASIN/竞品/类目 Node 的关键词市场、搜索需求、排名、趋势、季节性、市场进入评估，或生成关键词市场调研 Excel。不用于：查单个关键词搜索量、查单 ASIN 价格/评论/销量、纯 Listing 文案写作、纯广告报表诊断、与 Amazon 无关的通用 SEO。
metadata:
  version: "1.6.2"
  updated: "2026-08-29"
  short-description: "SellerSprite MCP市场关键词批量调研，输出Excel报告"
---

# SellerSprite 市场关键词调研

## 定位

本 SKILL 是**市场搜索需求、产品机会、季节性与市场进入策略分析器**，不是关键词下载器，也不是广告投放工具。成功标准：数据调用可控、语义理解正确、趋势可复用、结论带证据、不越过关键词数据能支持的证据边界。

## 总流程（必须按序执行）

```
阶段A 计划与预算 → 用户确认 → 阶段B 执行
  1. 解析输入 → input.json
  2. 输出调用预算（阶段A）→ 等用户确认（预计 >30 次时必须等待）
  3. Node 校验与榜单取样（仅 Node 输入）→ asin_pool.json
  4. 批量反查关键词 traffic_extend（固定3页×50词）→ raw/traffic_batch_<批次>_p<页>.json
  5. traffic_keyword 逐直接输入 ASIN 仅取当前第1页（100词）→ raw/traffic_keyword_current_<ASIN>_p1.json
  6. aggregate_batches.py + normalize_keywords.py + aggregate_asin_keyword_matrix.py → cache/*.json
  7. LLM 翻译校正 + 多标签分类 → classify_keywords.py → validate_labels.py
  8. select_trend_keywords.py → trend_keywords.json
  9. aba_research_trend 逐词拉历史 → raw/trend_*.json
 10. analyze_trends.py → trend_analysis.json
 11. LLM 分析引擎（需求地图/机会矩阵/严格证据产品假设/进入结论）→ analysis.json → validate_analysis.py
 12. build_excel_report.py → output/*.xlsx
 13. validate_report.py → 验收
 14. 对话内输出简版摘要 + present_files 交付 Excel
```

## 工作目录契约

每个调研任务在用户工作区下建独立目录（如 `keyword_research_<站点>_<日期>/`），结构固定：

```
<workdir>/
├── input.json              # 步骤1产出：解析后的输入
├── plan.json               # 步骤2产出：预算与确认记录
├── raw/                    # 所有 MCP 原始返回，一律先落盘再处理
│   ├── node_<nodeId>.json              # product_node 返回
│   ├── products_<nodeId>_p<页>.json    # product_research 返回
│   ├── traffic_batch_<批次>_p<页>.json # traffic_extend 返回；每批固定3页
│   ├── traffic_keyword_current_<ASIN>_p1.json # traffic_keyword 当前前100词
│   └── trend_<关键词slug>.json         # aba_research_trend 返回
├── cache/
│   ├── asin_pool.json        # 去重后 ASIN 池，含来源追踪
│   ├── keyword_master.json   # 合并去重后的关键词主表
│   ├── keyword_labeled.json  # LLM 翻译与标签后的主表
│   ├── trend_keywords.json   # 入选趋势词及入选原因
│   ├── trend_analysis.json   # 24 个月趋势计算结果
│   ├── asin_keyword_matrix.json # 同次响应聚合的当前排名+流量占比共享缓存
│   ├── analysis.json         # LLM 分析引擎结论
│   └── call_log.json         # 调用日志（工具/序号/范围/条数/成功/截断/补调用原因）
└── output/
    └── <站点>_keyword_market_report.xlsx
```

规则：

- 所有 MCP 返回**先原样写入 raw/ 再解析**，禁止只在内存中传递。
- 每次 MCP 调用前先在 `cache/call_log.json` 写入 `in_progress` 记录，返回后原位更新为成功或失败；应用崩溃后不得把边界不明的调用静默当作未执行。
- cache/ 即任务级缓存：同一任务内重复需求（转置、加图表、改翻译、改分类、重生成摘要）只允许读缓存重新计算，**不得新增 MCP 调用**。

## 步骤 1：输入解析

将用户输入解析为 `input.json`：

```json
{
  "groups": [
    {"marketplace": "DE", "asins": ["B0XXXXXXXX"], "node_ids": ["12345"], "node_top_n": 50}
  ],
  "options": {"data_month": "202607", "keyword_pool_pages": 3, "trend_months": 24, "core_trend_keywords": 5, "longtail_trend_keywords": 5, "trend_keyword_cap": 20, "current_ppc": true, "historical_ppc": false, "report_language": "zh-CN"}
}
```

规则：

- 每个 ASIN / Node 必须绑定站点（marketplace）；Node ID 不得脱离站点解释。
- 支持单/多 ASIN、单/多 Node、混合、多站点；多站点拆成多个 group。
- Skill不限制ASIN总数；同站点始终每20个自动分批。输入超过20个时，必须先明确展示批次数、逐函数调用量和预计等待时间，取得用户确认后再执行，不得静默截断。
- `node_top_n` 默认 50；仅当用户要求完整报告、Top50 词池未收敛或长尾不足时才扩到 100。
- ASIN 默认 `queryType: 1`（畅销变体）；仅当用户明确要诊断指定子 ASIN 时用 `queryType: 2`。
- `data_month` 可选，格式固定 `yyyyMM`；省略时使用执行当月。它只控制 `product_research.month` 与 `traffic_extend.historyDate`。逐ASIN矩阵固定取当前数据，`traffic_keyword` 不传 `month`；24个月趋势仍截止接口最新共同完整月。
- 新任务统一使用 `keyword_pool_pages: 3`：每批固定请求第1–3页，每页50词，三页按标准化关键词去重后全部收录，不设100词上限，不请求第4页。
- `keyword_pool_size` 仅为旧配置兼容：旧值50映射1页；旧值100映射3页。新任务不得继续写旧字段。

### 输入模式（决定报告口径，build 脚本自动识别）

| 模式 | 输入 | 定位 |
|---|---|---|
| **M1（默认推荐）** | 单 ASIN + Node ID | 市场+本品对比：市场靠哪些词 × 本品打中/漏掉哪些 → 差异化方向 |
| M2 | 人工判定的同类多 ASIN（≥5 个为宜） | 人工细分品类的关键词环境 |
| M3 | 纯 Node | 市场关键词环境（无本品对照） |
| M4 | 纯单 ASIN | 快速诊断，结论自动降级为初步判断并建议补 Node |

用户只给一个 ASIN 时，主动建议补一个上位 Node 组成 M1；用户坚持单跑则按 M4 执行并在报告中标注口径限制。M1 的对比（共有词/市场缺口词/本品差异词）由 build 脚本从来源字段确定性计算，不新增 MCP 调用，也不做量化蚕食分析（V1 排除项不变）。


## 步骤 2：阶段 A —— 计划与预算（强制）

调用任何 SellerSprite MCP 之前，先按 `references/mcp-routing.md` 的调用量公式估算，并向用户输出：

- 识别到的站点、ASIN 数、Node 数、每 Node 的 Top N、预计去重 ASIN 范围；
- 拟调用的 MCP 函数及各自次数、趋势词数量、基准总调用量；
- 可能增加调用的异常条件；哪些操作在本地完成、不消耗 MCP。

**预计调用量 > 30 次时必须等待用户明确同意**；用户说"直接执行"可跳过等待，但仍需告知预计调用量。将预算与确认结果写入 `plan.json`。

SellerSprite调用固定不超过8次/滚动60秒，相邻调用至少间隔7.5秒；限流等待属于正常运行状态，不得因为等待而停止任务。

调用量公式（A=去重直接 ASIN 数，N=Node 数，P_i=Node i 商品列表页数，U=合并去重 ASIN 数，T=趋势词数，K=`keyword_pool_pages`，新任务固定3）：

```
ASIN 模式:  ceil(A/20) × K + A + T
Node/混合:  N + ΣP_i + ceil(U/20) × K + A + T
```

`traffic_keyword` 每个直接输入ASIN固定1次，不读取 `total` 规划后续页，禁止请求第2页。纯Node模式 A=0，不调用矩阵接口。固定三页时，20个同站点ASIN、无Node、10个趋势词的标准M2预算固定为 `3+20+10=33` 次，Sorftime为0次；执行前必须确认。基准外只允许最多2次临时错误重试，权限/额度/参数错误不重试，硬上限35次。

允许最多 2 次自动修复型补调用；预计超出 2 次以上时暂停并征求用户确认。

## 步骤 3–4：数据采集

详细路由规则、字段清单、截断处理见 `references/mcp-routing.md`。要点：

- Node：先 `product_node` 校验取 `nodeIdPath` → `product_research` 取榜单（**必须 `variation: Y` 排除子变体**；禁止组合 filterSub/maxSubBsrRank，见 mcp-routing.md §3）→ **本地复核子类 BSR 与类目 code**（不得信任服务端过滤）→ 去重 ASIN 与重复子变体 → 写入 `asin_pool.json`。
- ASIN 反查：`traffic_extend`，每批最多20个同站点ASIN，按 `trafficPercentage` 降序，固定 `size=50`。固定请求第1、2、3页；即使第2页重复、短页或空页也继续请求第3页。三页按标准化关键词去重后全部保留，随后停止，禁止第4页。关键词总表、分析与趋势候选只能来自该指定月份词池；矩阵额外返回的词不得扩入。
- 逐ASIN矩阵：仅对用户直接输入的ASIN调 `traffic_keyword`，**不传 `month`**，固定 `page=1`、`size=100`、按 `trafficPercentage` 降序，不设置 `returnFields`。同一次响应同时抽取 `rankPosition.page/index/position`、`adPosition.page/index/position` 与 `trafficPercentage`，原样落盘为 `traffic_keyword_current_<ASIN>_p1.json`，禁止第2页。
  - 排名展示只用接口明确给出的 `page/index`，格式为 `P页-页内位`；不从总排名或固定页容量反推。矩阵单元格为 `自然位/广告位`，缺哪侧就保留空侧，两侧都缺失则空白。
  - 当前前100流量词中未匹配到总表关键词的单元格留空，含义仅为“未进入当前前100或字段缺失”，不得解释成确定无排名/无广告。
  - 旧版 `traffic_keyword_<ASIN>_p*.json` 历史/多页缓存不得冒充当前矩阵；聚合脚本只接受新文件名。
- **M1 来源归因（V1.2 实测沉淀）**：`traffic_extend` 返回**不包含逐词来源 ASIN**。M1 模式必须把输入 ASIN 拆成**单独一个批次**反查（`asinList=[输入ASIN]`），并在该批次的 raw 文件上标注 `_meta.asins=[输入ASIN]`；该批次独有的词判定为"本品覆盖词"，榜单批次词判定为"市场词"——这样脚本才能算出 共有/缺口/差异 三组对比。费用 +1 次调用，写入预算。
- `traffic_keyword_stat` / `traffic_source` 仍不是默认流程；`traffic_keyword` 仅用于直接输入ASIN的两个矩阵，不扩展到Node榜单样本。Sorftime不能提供等价的逐词流量贡献比例，标准报告不得再为排名额外调用Sorftime。
- 趋势：仅对入选趋势词调 `aba_research_trend`（`timeGranularity: M`），每词每站点只调一次；V1 不拉历史 PPC。

## 步骤 6–8：本地处理（脚本）

按序运行 scripts/（用可用的 Python 3 解释器，依赖仅标准库 + openpyxl）：

```bash
python scripts/aggregate_batches.py --workdir <workdir>
python scripts/normalize_keywords.py --workdir <workdir>
python scripts/aggregate_asin_keyword_matrix.py --workdir <workdir>
# → 然后由 LLM 完成翻译校正与多标签分类（见下），写回 keyword_labeled.json
python scripts/classify_keywords.py --workdir <workdir>
python scripts/validate_labels.py --workdir <workdir>
python scripts/select_trend_keywords.py --workdir <workdir>
```

LLM 负责的两步（不脚本化）：

1. **中文翻译校正**：按 `references/keyword-taxonomy.md` 的翻译规范，为每个关键词产出 校正中文 / 校正理由 / 置信度；原始关键词与 MCP 原译必须保留。
2. **多标签分类**：按同一文件的标签体系打需求属性标签（可多选）、相关度(A–D，附一句理由)与购买意图(高/中/低)，再由 `classify_keywords.py` 按固定优先级生成流量性质和 `traffic_type_reason`。人群、材料、功能、规格、场景、套装或配件词不得成为核心大词；`validate_labels.py` 冲突即停止生成。

字段口径（集中度、供需比等易混淆字段的定义与禁区）必须查 `references/metric-definitions.md`。

## 步骤 9–10：趋势

对 `trend_keywords.json` 中每词调一次 `aba_research_trend`，原始返回存 `raw/trend_<slug>.json`，然后：

```bash
python scripts/analyze_trends.py --workdir <workdir>
```

脚本完成：共同最新月对齐、截取最近 24 个完整月、环比/同比/变异系数/季节指数/峰谷/拐点等全部指标（口径见 `references/metric-definitions.md`）。缺月保留空白，不补 0、不插值。

## 步骤 11：LLM 分析引擎

读 `references/analysis-framework.md`，基于 cache 数据完成并写入 `cache/analysis.json`：

- 市场需求地图、高体量流量陷阱、点击—转化集中度象限、关键词机会矩阵；
- 产品定义假设、单品/套装/配件结构判断；
- 季节性与进入时间轴（用户未给开发/生产/运输周期时只给相对提前量，禁止编造精确日期）；
- 市场生命周期、市场进入结论（四档等级 + 证据 + 限制条件）、风险与验证清单。

每条重要结论必须带证据字段与置信度（高/中/低），句式与禁区见 `references/guardrails.md`。
产品方向只能使用实际关键词及其标签支持的产品形态、材料、功能、规格、人群和套装/配件；每行必须含来源关键词、数据证据、明确“假设”、置信度与待验证数据。写完运行 `python scripts/validate_analysis.py --workdir <workdir>`。

## 步骤 12–14：Excel 交付

```bash
python scripts/build_excel_report.py --workdir <workdir> --template <SKILL目录>/assets/keyword_market_report_template.xlsx
python scripts/validate_report.py --workdir <workdir>
```

- 工作簿13个Sheet的连续编号、固定顺序与格式规范见 `references/report-schema.md`；模板在assets/。矩阵为 `08/09`，最后三页依次为市场进入与风险、调研范围与调用、数据质量。首页通常为4图；没有有效点击/转化双指标时不保留空白图框，改为明确缺数提示。两张24月折线图的系列名必须为原始关键词，搜索量与ABA Rank图对同一关键词使用同一颜色；每个系列必须显式绑定连续24个月 `yyyy-MM` 分类轴，横轴隔月显示标签。
- 输出文件名固定为 `{站点}_{品类标签}_{口径}_{YYYYMMDD}.xlsx`（如 `US_女童泳装_ASIN+Node对比_20260816.xlsx`），由脚本生成；品类标签来自 analysis.json 的 `category_label` 字段。
- **报告只能由 build_excel_report.py 一次生成。禁止用 openpyxl/其他方式事后手工追加或修改图表、Sheet**——要改展示就改脚本或模板后重跑（缓存已覆盖，重跑不消耗 MCP）。
- validate_report.py 全绿后才能交付；失败项必须修复或向用户说明。
- 交付：present_files 展示 xlsx；对话中只给简版摘要（范围、调用量、生命周期、核心机会、进入结论、主要风险）。

## 禁止事项（硬约束）

1. 不做 ASIN/Node 关键词重叠的量化蚕食分析、SKU 组合关系分析；不做 Listing SEO 布词；不做广告分组/匹配/否定词/具体出价（V1 明确排除）。M1 模式的来源对比（共有词/缺口词/差异词）是允许且必需的，不属于蚕食分析。
2. 不拉历史 PPC；当前 PPC 只作为获客成本与竞争压力指标。
3. 缺失字段留空，不得填 0；不得用 `purchaseRate` 冒充转化集中度；不得把流量占比解释为市场份额；不得把同义词搜索量相加称为市场容量；多站点数据不得直接相加。
4. 原始关键词不得被中文替换；产品功能结论必须标记为"假设"。
5. 缓存已覆盖的操作（转置/12↔24月/加图表/改翻译/改分类/改颜色排序/拆分两个矩阵/重生成摘要）不得新增MCP调用；已有当前口径 `asin_keyword_matrix.json` 时重建矩阵不得调用MCP。
6. `ERROR_UNAUTHORIZED` 统一表述为“授权或额度拒绝”；只有账户状态或用户确认后才能进一步归因为额度耗尽或权限不足。权限/额度/参数错误不重试。
7. 禁止空泛表述（"市场潜力巨大""竞争非常激烈""建议差异化"等）——全部改写为带数据证据的句子，完整清单见 `references/guardrails.md`。

## 资源索引

| 文件 | 何时必读 |
|---|---|
| `references/mcp-routing.md` | 步骤 2–4（预算公式、接口参数、截断与补调用、调用日志格式） |
| `references/metric-definitions.md` | 步骤 5–10（字段口径、趋势指标公式、季节指数阈值） |
| `references/keyword-taxonomy.md` | 步骤 6（翻译规范、标签体系、相关度/购买意图定义、已知错译案例） |
| `references/analysis-framework.md` | 步骤 10（全部分析模块的算法与输出结构） |
| `references/report-schema.md` | 步骤 12（13 个 Sheet 的列定义与 Excel 格式规范） |
| `references/guardrails.md` | 步骤 11–14（文案禁区、置信度规范、异常处理、验收清单） |
| `scripts/*.py` | 步骤 5/7/9/11/12 按命令行执行，无需读入上下文 |
| `assets/keyword_market_report_template.xlsx` | 步骤 11 作为 --template 传入 |
| `RELEASE.md` / `scripts/package_release.py` | 修改或发布 Skill 时；版本、安装包与 GitHub PR 校验机制 |
