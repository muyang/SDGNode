# SDG 能力注册技术方案 —— 基于 GeoNexus-SDK GeoCard 体系

> **版本**：v0.1（设计稿）　**日期**：2026-07
> **依据**：
> ① 本仓库《SDG监测评估_数据源与地理空间AI技术体系梳理.md》（数据/工具/模型清单）；
> ② GeoNexus-SDK 本地检出 `D:\Repos\GeoNexus\GeoNexus-SDK`（README、docs/GEOCARD.md、GEOMCP.md、MODEL.md、ARCHITECTURE.md、DATA_REGISTRATION.md、schemas/geocard.schema.json、src/geonexus/{geocard,gaag,recipe,model,adapters,registry,federation,ggihs,cafe,geotask,agent,kg,security,web}、examples/sdg_15_3_1）。
>
> **目标**：把已梳理的 SDG 数据源、GIS/空间分析工具与 AI 模型，按 GeoCard 七类资产模型注册为**可发现、可校验、可调用、可复现、可治理**的能力，供 GeoNexus-SDK 客户端（MCP 桥 / Java 客户端 / Web BFF / Python SDK）使用，并支撑 SDG 指标级评估方案的沉淀与复用。

---

## 目录

1. [GeoNexus-SDK 设计理念要点（方案依据）](#1-geonexus-sdk-设计理念要点方案依据)
2. [SDG 资源可注册性总体分析](#2-sdg-资源可注册性总体分析)
3. [总体架构：SDGNode = SDG 域 GeoNode 网络](#3-总体架构sdgnode--sdg-域-geonode-网络)
4. [能力注册规范（SDGNode Profile）](#4-能力注册规范sdgnode-profile)
5. [五条注册管线](#5-五条注册管线)
6. [示例卡片与 Recipe](#6-示例卡片与-recipe)
7. [客户端发现与使用路径](#7-客户端发现与使用路径)
8. [优先指标-能力绑定矩阵](#8-优先指标-能力绑定矩阵)
9. [实施路线图（P0–P4）](#9-实施路线图p0p4)
10. [SDK 缺口与扩展建议](#10-sdk-缺口与扩展建议)
11. [风险与对策](#11-风险与对策)
- [附录 A：能力词表 v0](#附录-a能力词表-v0)
- [附录 B：首批注册清单（30 卡）](#附录-b首批注册清单30-卡)
- [附录 C：协议与命令速查](#附录-c协议与命令速查)

---

## 1. GeoNexus-SDK 设计理念要点（方案依据）

### 1.1 核心循环与主权原则

```
GeoCard（描述资产与可执行契约）
   ↓
Registry / Discovery（节点知道自己拥有什么卡）
   ↓
Contract Validation（CRS / bbox / 时间窗 / 波段 / 分辨率是否满足请求）
   ↓
GeoMCP（JSON-RPC 2.0 携带地理空间上下文）
   ↓
GeoNode（主权执行边界）→ GeoSkill（可复用能力）→ Result
```

- **数据主权**："数据不动，计算移动"（CAFE 下推引擎）。没有中央数据仓库；节点是对等的，注册中心发现节点而非吸收节点。
- **卡描述而不包含**：GeoCard 是门面（facade），只持有引用（composition.components 是 id 指针），执行 DAG 在 recipe_ref 指向的 Recipe 里。

### 1.2 GeoCard v1.0（schemas/geocard.schema.json）

- **必填**：`geocard_version`（"0.1"|"1.0"）、`id`（`^[A-Za-z0-9][A-Za-z0-9._-]*$`）、`type`、`name`、`description`。
- **七类资产**：`data` / `model` / `skill` / `agent` / `workflow` / `knowledge` / `compute`。
- **契约段**：`spatial`（bbox/crs/resolution/geometry）、`temporal`（start/end/interval）、`bands`、`inputs`/`outputs`、`capabilities`、`access`（protocol/endpoint/auth/format）、`provenance`、`license`（SPDX 或 {name,url}）、`compliance`（sovereignty/restrictions/sensitivity∈{public,restricted,sensitive,secret}）、`trust`（verified/score）、`runtime`（cpu/memory/gpu）、`interface`、`rendering`。
- **1.x 加法段**：`composition`（组件引用：id/role/step/required/alias + template）、`params`（参数契约：name/type/enum/min/max/**scope∈{reusable,fixed}**/target）、`recipe_ref`（`recipe://ns/name@semver` + **data_snapshot**）。
- **顶层扩展策略**：`additionalProperties: true`，未知顶层键必须是 object/array，命名空间化（如 `geonexus:*`）→ **SDG 绑定字段以此方式扩展，不改 SDK**（见 §4.3）。
- **ContractValidator**：CRS 等价（pyproj）、bbox 相交、时间窗重叠、波段覆盖、分辨率不粗于请求；缺声明产生 warning（"cannot verify"）而非静默通过；不满足 → GeoMCP 错误 **2000 CONTRACT_NOT_SATISFIED**（附 reasons）。
- **可见性继承**（geocard/visibility.py）：复合卡有效可见性 = min(自身, 各**承载内容**组件)；门控角色 GATING_ROLES = data/model/knowledge/workflow，skill/compute 不门控；组件不可解析 → 整体不可见（**404 而非 403**）；未知 → 降级为 restricted，绝不 public。

### 1.3 GeoMCP 协议面（docs/GEOMCP.md, MODEL.md, RECIPE.md）

- 冻结方法（1.x）：`geo.capabilities`、`geo.describe`、`geo.execute`、`geo.health`。
- 加法扩展：`geo.plan`（Recipe 物化为 RunPlan，capability `recipe_planning`；错误 2005 RECIPE_NOT_FOUND / 2006 RECIPE_PARAM_INVALID）、`geo.invoke`（模型调用，capability `model_invocation`；**门禁拒绝也是 result 而非 error**，返回 `status:failed + error_code + reasons`）。
- `spatial`/`temporal` 是协议一等公民；传输：HTTP `POST /geomcp`（FastAPI）+ MCP 桥（`mcp run --bare` stdio / `mcp serve` Streamable HTTP，暴露 geo_* 工具给 LLM 客户端）。
- 错误码：-32700…-32603（JSON-RPC）；2000 契约不满足、2001 技能不存在、2002 卡不存在、2003 执行失败、2004 参数无效。

### 1.4 GAAG 合约注册中心（src/geonexus/gaag/）

- 流水线：**scan → metadata →（可选 LLM 描述）→ embed → register → search → gate**。
- **8 类合约**（contract_types.CONTRACT_SCHEMAS）：

| 合约 | 必填字段 | 典型扩展名 | 对 SDG 的意义 |
|---|---|---|---|
| raster | crs/bbox/resolution/bands | .tif/.vrt/.img | 遥感产品 |
| vector | crs/bbox/geometry_types | .geojson/.gpkg/.shp | 边界/OSM/保护区 |
| temporal | crs/bbox/time_start/time_end/time_interval | .nc/.zarr | ERA5、数据立方体 |
| volume3d | crs/bbox/z_min/z_max | .voxel/.3dtiles | 三维城市 |
| pointcloud | crs/bbox/point_count | .las/.laz | LiDAR |
| **statistical** | **columns/record_count**（可选 spatial_key/time_key/units/aggregation） | .csv/.parquet/.xlsx | **统计数据库（FAOSTAT/WDI/UNSD）原生可注册** |
| text | content_type/language | .pdf/.md/.docx | 报告/指标定义/知识文档 |
| **report** | **format/checksum/source_run/recipe/params/data_snapshot** | .html/.pdf/.docx | **评估结论：必填的是"来源四件套"而非字数** |

- 语义检索：`embed.py` 双模式——FeatureEmbedder（确定性 64 维词法哈希，离线可用）与 LLM embedder（`GEONEXUS_LLM_API_KEY`，OpenAI 兼容）；`pgvector_store.py` 提供 Postgres 向量检索。
- 门控：`ContractGate`（合约满足度）+ `validate_contract`（按类型必填字段校验）+ `detect_asset_type`。

### 1.5 Recipe 与知识产品治理（docs/RECIPE.md、examples/sdg_15_3_1）

- Recipe：`recipe://ns/name@semver`，含 `params`（带 target 落点与 reusable/fixed 作用域）、`requires`（卡 id）、`steps`（kind: skill，uses/depends_on/params/inputs=`step://s1/mask`/outputs/timeout/max_attempts/resources）、`entrypoint`、`outputs`（name/from/role/media_type）、`data_snapshot`。
- `materialize(recipe, params, run_id) → RunPlan`（先契约校验，`${params.x}` 替换，`task_id='<run>:<step>'`）；`deliverables(plan)` 返回结论**不含 url**（产物位置是运行环境的决定）。
- RecipeRegistry：**pending → approved → rejected** 评审词汇（与卡注册共享 geonexus.review）；`resolve()` 只取最新 APPROVED；**`fork()` 是复用的可执行定义**（新地址、自己的参数、源不动、回到 pending）；注册中心 HTTP 服务化（`POST/GET/DELETE /recipes`、`/recipes/{address}/approve|reject`、`/recipes/fork`），审批是治理行为（多版本歧义 → 409）。
- 运行产物 → `report_card_from_run(plan, …)` 自动生成 knowledge 卡（interface.type=report，composition 角色由 recipe 推导，provenance 指向 run）→ 报告合约注册（无来源四件套拒绝入册）。
- **SDK 已有 SDG 示例**：`examples/sdg_15_3_1/recipe.yaml`（SDG 15.3.1 土地退化：2 数据 + 1 算子 + 1 报告，baseline 参数 `scope: fixed` 钉死指标口径）——本方案的指标 Recipe 库直接沿用该范式。

### 1.6 模型调用契约（docs/MODEL.md）

```
model GeoCard → ① 输入契约(card.inputs 必填项)
              → ② 算力门禁 match_resource(card, compute capabilities)
                   不匹配 → 带理由拒绝，一个字节都不发出去
              → ③ provider  InferenceProvider（同步 HTTP）
                            BatchProvider（submit → poll → collect）
                   门禁选中的节点会 retarget 调用目标
              → ④ 输出契约(card.outputs 必填项)
```

- provider 按 `card.access.protocol` 选择：`batch/job/oge-job/https+batch` → BatchProvider；`http/https/rest/inference/空` → InferenceProvider；其他（如 grpc）**明确报错不猜**。
- 线上约定：`POST {endpoint}` `{"model","inputs","params","request_id"}` → `{"outputs":{…}}`；Batch：POST → `{"job_id","status"}`，GET 轮询到终态。
- `ModelBackend` 把模型调用接入 GeoTask（同一状态机/租约/重试/观测）；调度器按 `cpu_cores/memory_mb/gpu_count(+gpu_kind)` 准入（reject ≠ blocked：装不下=部署错误，暂时没容量=排队），支持优先级+公平轮转+回填。
- 错误码：`no_compatible_compute`、`input_missing`、`invalid_spec`、`resource_unavailable`、`executor_lost`、`timeout`、`execution_error`。
- **明确不做**：不在 GeoNode 进程内托管模型、不做训练/微调/评测生命周期、不自动解引用资产。→ 模型权重托管与推理服务由 SDGNode 侧提供（§5 管线 4）。

### 1.7 适配器与联邦（现状即战力）

| 适配器 | 能力 | 对本方案的价值 |
|---|---|---|
| `adapters/stac.py` | STAC Item → GeoCard（bbox/proj:epsg/gsd/datetime/eo:bands/assets.href 映射） | Sentinel/Landsat/PC/EarthSearch 目录直采 |
| `adapters/stac_write.py` | GeoCard → STAC Item（round trip） | 反向发布，与外部 STAC 生态互通 |
| `adapters/sentinel_hub.py` | **CDSE STAC 搜索 + Sentinel Hub WMS/WMTS** → GeoCard + GAAG 合约 | Copernicus 数据开箱即用 |
| `adapters/osm.py` | **Overpass API**（building/water/road/landuse，镜像故障转移）→ GeoCard → GAAG | VGI 数据开箱即用 |
| `adapters/ogc*.py` | Features 导入、**Processes 写侧**（geo.execute 驱动 OGC 进程）、Coverages（CoverageJSON→NDVI→GeoTIFF）、Records、Tiles、WMS 传统服务 | 各国 SDI/国标服务接入 |
| `adapters/oge_*.py` | OGE 平台双向引用映射（Personal:MyData/Asset/Process、Platform:Coverage/Product、Tms）、credential、executor、skill、card builder | 批处理平台作业（protocol `oge-job` → BatchProvider） |

联邦与运维：`registry`（peer sync + 健康探测 + API-Key + 持久化）、`federation`（下推执行）、GeoNode 委托 + 健康感知路由、`ggihs`（跨注册中心目录/健康聚合 + dashboard）、`geotask`（状态机/事件 seq 回放/幂等/对账）、`cafe`（唯一推下引擎：中心路由/租约 + 本地/远程 worker）、`security/legal_ontology`（法律本体）、`kg`（通用知识图谱原语 + Neo4j 存储）、`agent`（llm_planner/code_agent/data_agent/reflective/llm_repair）、`web`（BFF：auth/datasets/tasks）。

CLI 面（注册与运维入口）：`card validate|inspect|import-stac|import-ogc|import-ogc-process|import-ogc-coverage|import-ogc-records|import-ogc-tiles|import-ogc-legacy|export-stac`；`recipe validate|inspect|plan|register|search|fork`；`registry start|sync|register|search|skill register|skill list`；`node start`；`mcp run|serve|import`；`agent run|ask`；`task list|show|events|reconcile`；`ggihs start`；`web start`；`inspector`；`init`。

---

## 2. SDG 资源可注册性总体分析

### 2.1 判定框架：五问 + 决策树

一项 SDG 资源能否注册为 GeoCard 能力，判五问：

1. **有稳定身份吗？**（可命名、可版本化 → `id` + data_snapshot/semver）
2. **契约可声明吗？**（时空范围/波段/列定义/输入输出 → GAAG 8 类合约 + ContractValidator 五检）
3. **接口可程序化到达吗？**（文件 / HTTP API / STAC / OGC / Overpass / CLI / 推理端点）
4. **许可与合规可界定吗？**（SPDX license + compliance.sovereignty/sensitivity/restrictions）
5. **有执行入口吗？**（数据可读 / 模型可调 / 技能可跑 / 方案可复现 / 结论可溯源）

```
资源
├─ 数据集（栅格/矢量/立方体/点云/统计表/文本）
│    ├─ 有 STAC/OGC/Overpass/CDSE 端点 ──→ data 卡【现成适配器直采】
│    ├─ 本地/托管文件 ──────────────────→ data 卡【上传管线：scan→GAAG 合约→评审】
│    └─ 纯 REST API（统计/主题服务）────→ data 卡(statistical) + 伴生 fetch skill【管线 3】
├─ 训练模型
│    ├─ 开放权重可自部署 ──→ model 卡 + 推理服务封装【管线 4】
│    ├─ 仅 API（自托管端点）→ model 卡（access=服务端点）
│    └─ 权重不开放且无 API → knowledge 目录卡（describe-only，trust.verified=false）
├─ 算法/工具
│    ├─ 可容器化/CLI 无头 ──→ skill 卡（GeoNode 技能）【管线 4b】
│    ├─ 有 OGC Processes / OGE 端点 → 远程 skill（ogc_exec / oge_skill 现成）
│    └─ 交互式桌面软件 ────→ 不注册（作客户端/制卡工具，或抽取无头引擎）
├─ 组合方案（指标评估流程）──→ workflow 卡 + Recipe【管线 5】
├─ 结论/文档/指标定义 ──────→ knowledge 卡（运行产物走 report 合约）
└─ 算力（GPU/HPC/批队列）───→ compute 卡（CAFE worker + 调度器准入）
```

### 2.2 总体映射表（上轮梳理清单 → GeoCard）

> 可得性：**A=现成机制直接注册**；**B=需薄封装**（skill/provider/YAML 工厂）；**C=需开发**（recipe/算子）；**D=仅目录卡**（可发现不可执行）。

| # | 资源类别（上轮梳理） | 代表实例 | GeoCard 类型 | GAAG 合约 | 注册机制 | 可得性 | 优先级 |
|---|---|---|---|---|---|---|---|
| 1 | 卫星影像目录 | Sentinel-1/2、Landsat C2L2（CDSE/PC/EarthSearch） | data | raster | `sentinel_hub` 适配器 / `card import-stac` | **A** | P0 |
| 2 | 全球土地覆盖/水体/森林产品 | ESA WorldCover、JRC GSW、Hansen GFC、Dynamic World | data | raster | STAC 导入或文件上传管线 | A/B | P0 |
| 3 | 人口/城市格点产品 | WorldPop、GHSL（GHS-BUILT-S/POP/SMOD）、LandScan(受限) | data | raster | 文件上传管线（`raster_to_geocard`） | A | P0 |
| 4 | 大气/气候数据立方体 | ERA5、TerraClimate、CHIRPS、CMIP6/ISIMIP | data | temporal（Zarr/NetCDF） | 文件/对象存储卡 + temporal 合约扫描 | A | P1 |
| 5 | 夜光数据 | VIIRS DNB（EOG，需注册）、珞珈一号、SDGSAT-1 微光 | data | raster | 卡 + `access.auth: apikey`；compliance.restricted | B | P1 |
| 6 | 统计数据库 API | UN SDG Global Database、WDI、FAOSTAT、WHO GHO、ILOSTAT | data | **statistical** | **管线 3：数据卡 + fetch skill 配对** | B | P0 |
| 7 | 入户调查微数据 | DHS（地理编码聚类）、MICS、LSMS | data | statistical/vector | 上传管线；`sensitivity: restricted/sensitive` + sovereignty | B | P2 |
| 8 | VGI/开放地图 | OSM 要素、POI、GTFS | data | vector | **`osm.py` Overpass 适配器（现成）**；GTFS 走文件卡 | **A** | P0 |
| 9 | 生物多样性/保护区 | WDPA、GBIF API、IUCN 红色名录、GFW 警报 | data | vector/statistical | OGC Features 导入 / 管线 3（GBIF、GFW API） | A/B | P1 |
| 10 | 灾害/实时服务 | GDACS、NASA FIRMS、OpenAQ、Global Fishing Watch | data + fetch skill | statistical/vector | 管线 3（API 配对） | B | P1 |
| 11 | 排放/碳数据 | EDGAR、Global Carbon Atlas、Climate TRACE | data | statistical/raster | 文件卡 / 管线 3 | A/B | P2 |
| 12 | 遥感基础模型 | Prithvi-EO-2.0、Clay v1.5、TerraMind、samgeo(SAM2)、Presto、RingMo | model | —（卡即契约） | **管线 4：HF 权重 → InferenceProvider/BatchProvider 服务 + model 卡 + compute 门禁** | B | P1 |
| 13 | 任务专用模型 | 洪水提取、建筑足迹、作物分类、PM2.5-GBDT、贫困估计、OSDG 文本分类（spatial:false） | model | — | 管线 4（CPU/GPU 皆可） | B | P1 |
| 14 | 权重不开放的模型 | AlphaEarth（GEE 内嵌入）、SkySense V2 | knowledge（目录卡）+ GEE wrapper skill | text | D + B（消费端封装） | D | P2 |
| 15 | 空间统计算法 | 热点 Gi*、Moran's I、GWR/MGWR、克里金、dasymetric、zonal stats | skill | — | GeoNode 技能（PySAL/rasterstats 封装，容器化） | B | P1 |
| 16 | 遥感分析算法 | NDVI/指数、变化检测（LandTrendr/BFAST/CCDC）、转移矩阵、水体提取、LCRPGR | skill | — | GeoNode 技能（GDAL/rasterio/GEE 封装） | B | P0–P1 |
| 17 | 领域模型工具 | InVEST、AccessMod、SWAT、MaxEnt、Circuitscape、Marxan | skill | — | 容器化无头封装（每服务一子技能） | B/C | P2 |
| 18 | 桌面 GIS 引擎的无头部分 | GRASS CLI、SNAP gpt、OTB、GDAL 工具链 | skill | — | 容器化技能 | B | P2 |
| 19 | 远程处理平台 | OGC API Processes 服务、OGE EMS、GEE | skill（远程） | — | `ogc_exec` / `oge_skill` 现成；GEE 需 wrapper（合规标注） | A/B | P2 |
| 20 | 指标评估方案 | SDG 15.3.1（**SDK 已有示例**）、11.3.1、6.6.1、3.9.1、15.1.1、14.5.1… | workflow + recipe | report（产物） | **管线 5：recipe + 复合卡 + fork/审批治理** | C | P2–P3 |
| 21 | 指标定义/元数据 | UNSD 231 项唯一指标元数据、tier、custodian | knowledge | text | YAML 工厂批量制卡 + `geonexus:sdg` 扩展 | B | P0 |
| 22 | 报告/评估结论 | CBAS《地球大数据支撑 SDG 报告》、VNR、运行产物报告 | knowledge | text / **report** | 静态文档走 text；运行产物走 `report_card_from_run`（来源四件套） | A/B | P1 |
| 23 | SDG 知识图谱 | 指标-数据-能力-政策关联 | knowledge（引用 kg 存储） | — | `geonexus.kg`（Neo4j）+ 知识卡指针 | C | P4 |
| 24 | 算力 | GPU 推理节点、HPC 批队列 | compute | — | compute 卡（runtime）+ CAFE worker 注册 | **A** | P0 |
| 25 | 桌面 GIS（交互） | QGIS、ArcGIS Pro、eCognition、ENVI | **不注册** | — | 客户端角色：MCP 桥/Java 客户端发现与调用；或制卡工具 | — | — |
| 26 | SaaS 平台整体 | GEE、ArcGIS Online、UP42、PIE-Engine | **不整体注册** | — | 桥接其目录（STAC）与进程（OGC/OGE）接口；平台整体注册违背主权与契约原则 | — | — |

**结论**：上轮梳理的资源中，约 **70% 可直接或用现成适配器注册**（1–4、8、21、22、24 类），**25% 需薄封装**（5–7、9–13、15–16 类：API fetch skill、模型推理服务、算法容器化），**5% 需方案级开发或仅目录化**（14、17、19–20、23 类）。桌面 GIS 与 SaaS 平台整体不注册（角色错位），但其无头引擎、目录与进程接口可桥接。

### 2.3 不能/不宜注册的情形（边界声明）

| 情形 | 处理 |
|---|---|
| 交互式桌面软件（QGIS/ArcGIS Pro GUI） | 作为**客户端**：通过 `geonexus mcp serve`（Streamable HTTP）或 Java 客户端接入；或作为制卡/审卡工作台 |
| 集中式 SaaS 平台整体（GEE、ArcGIS Online） | 与"数据不动计算移动"的联邦主权原则冲突；仅桥接其**标准接口**（GEE 数据集 → wrapper skill + 目录卡，标注 `compliance.restrictions: ["platform-dependent"]`） |
| 权重与 API 均不开放的模型（AlphaEarth 权重、SkySense V2） | 登记 **knowledge 目录卡**（可发现、describe-only、`trust.verified: false`、access 指向官方文档）；其可消费产物（如 GEE 中 AlphaEarth 嵌入数据集）另行注册数据卡 + wrapper skill |
| 敏感微数据（DHS 地理编码、手机信令 CDR） | 可注册但 `compliance.sensitivity: sensitive/restricted` + `sovereignty` 声明；依靠**可见性继承**保证复合案例不外泄（404 语义）；聚合最小人数门槛写入 skill 契约 |
| 无法声明契约的资源（无范围、无列定义、无版本） | GAAG `validate_contract` 拒绝入册——契约缺失即不可注册（这正是设计意图：没有卡的发现是猜测，没有卡的执行不可验证） |

---

## 3. 总体架构：SDGNode = SDG 域 GeoNode 网络

```
 客户端层   LLM 助手/Agent（MCP 桥: geo_capabilities/geo_describe/geo_execute/geo_plan/geo_invoke）
            Java 客户端 · Python SDK（RegistryClient/ContractValidator/invoke_model）· Web BFF（上传/评审/检索）
            QGIS/ArcGIS 等桌面 GIS（作为 MCP/HTTP 客户端）
     │
 协议层     GeoMCP JSON-RPC 2.0（POST /geomcp，HTTP）＋ MCP 桥（stdio / Streamable HTTP）
     │      geo.capabilities / describe / execute / health ＋ geo.plan ＋ geo.invoke
     │
 治理层     共享 Registry（cards + skills + recipes；pending→approved→rejected；API-Key；peer sync）
            GAAG 合约注册中心（scan→embed→register→search→gate；pgvector 语义检索）
            ContractValidator（CRS/bbox/时间/波段/分辨率）· 可见性继承 · report 合约
            security/legal_ontology（许可校验）· GGIHS（跨注册中心目录/健康聚合 + dashboard）
     │
 编排层     GeoAgent（llm_planner：自然语言目标→能力检索→DAG 管线）· Recipe 物化（geo.plan→RunPlan）
            GeoTask（状态机/事件 seq/幂等/对账）· 调度器（cpu/mem/gpu 准入、优先级、公平、回填）
            CAFE 下推引擎（中心路由/租约 + 本地/远程 worker —— 计算到数据）
     │
 能力节点层（各自主权，数据不动）
   ┌──────────────┬───────────────┬────────────────┬────────────────┐
   │ 数据中心节点  │ 统计 API 节点  │ 模型推理节点(GPU)│ HPC 批处理节点  │
   │ STAC/COG/Zarr│ UNSD/FAOSTAT/ │ Prithvi/Clay/  │ 大范围制图作业  │
   │ 文件库+扫描   │ WDI/GBIF +    │ samgeo/OSDG/   │ BatchProvider  │
   │ OSM/CDSE 采集│ fetch skills  │ PM2.5 + compute│ (submit/poll/  │
   │              │               │ 卡             │  collect)      │
   └──────────────┴───────────────┴────────────────┴────────────────┘
   （机构联邦节点：CBAS/统计部门/高校各运行 GeoNode，peer sync + 健康感知路由 + 委托）
     │
 接入层（五条注册管线，见 §5）
   STAC/服务采集 · 文件上传+GAAG 扫描 · API 数据源工厂 · 模型封装 · Recipe 方案沉淀
```

**设计立场**：SDGNode 不复制 SDK，而是作为 SDG 领域的**卡片目录 + 节点部署 + 领域 Profile**：
- 本仓库维护：卡片 YAML 库、Recipe 库、词表与 Profile Schema、注册脚本/CI、领域 skill 与 provider 封装；
- 运行时依赖：`pip install geonexus-sdk[mcp]`，按 §3 拓扑起 registry/node/provider 进程。

---

## 4. 能力注册规范（SDGNode Profile）

### 4.1 ID 与命名规范（符合 `^[A-Za-z0-9][A-Za-z0-9._-]*$`）

| 类型 | 模式 | 示例 |
|---|---|---|
| data | `sdg.data.<provider>.<product>[-<version>]` | `sdg.data.esa.worldcover-2024`、`sdg.data.jrc.gsw-1.4`、`sdg.data.unsd.sdgdb` |
| model | `sdg.model.<family>.<variant>` | `sdg.model.prithvi.eo2-600m-tl`、`sdg.model.osdg.classifier-v2` |
| skill | `sdg.skill.<domain>.<name>` | `sdg.skill.urban.lcrpgr`、`sdg.skill.stats.fetch-faostat` |
| knowledge | `sdg.knowledge.<source>.<topic>` | `sdg.knowledge.unsd.indicator-11.3.1` |
| compute | `sdg.compute.<site>.<pool>` | `sdg.compute.local.gpu-a10` |
| workflow 案例 | `geocard.case.sdg-<indicator>-<region>-<year>`（沿 SDK 示例风格） | `geocard.case.sdg-11-3-1-chn-2020` |
| recipe | `recipe://sdg/<indicator-slug>@<semver>` | `recipe://sdg/11-3-1-lcrpgr@1.0.0` |

> 注意：SDK 示例中存在带空格的技能 id（"2026.9.16 SDG15.3.1"），不符合 GeoCard id pattern；SDGNode Profile **强制**上表模式，CI 用 `card validate` 把关。

### 4.2 capabilities 受控词表（v0，附录 A 全表）

按域分组的封闭词表（新增须走 PR 评审），保证 `registry search --capability` 与 GAAG 语义门控的召回质量：
`land-cover` `land-cover-change` `built-up-extent` `population-grid` `nightlights` `water-extent` `water-quality` `forest-change` `flood-mapping` `drought-index` `pm25-exposure` `accessibility` `dasymetric-disaggregation` `transition-matrix` `ldn-assessment` `protected-area-ratio` `crop-mapping` `yield-estimation` `poverty-estimation` `spatial-hotspot` `gwr-analysis` `zonal-statistics` `indicator-query` `report-render` …

### 4.3 SDG 绑定扩展字段（顶层扩展，schema 政策允许）

```yaml
geonexus:sdg:                     # 必须是 object（顶层扩展政策）
  goals: [11]                     # SDG 目标号
  indicators: ["11.3.1"]          # 指标编号（唯一指标口径）
  tier: "I"                       # 联合国指标分级
  custodian: "UN-Habitat"         # 保管机构
  unit: "ratio"                   # 计量单位
  disaggregation: ["national", "subnational", "city"]
  requires_capabilities: ["built-up-extent", "population-grid", "zonal-statistics"]  # 知识卡：算此指标所需能力
  related_cards: ["sdg.data.jrc.ghs-built-s", "sdg.data.jrc.ghs-pop"]               # 指标卡 → 绑定资产
```

- **指标知识卡**（`sdg.knowledge.unsd.indicator-*`）持有 `requires_capabilities` + `related_cards`，成为 **LLM planner / GeoAgent 的"指标→能力"路由表**：自然语言问"评估某市土地消耗率"→ 命中指标卡 → 得到所需 capability → registry search 找 data/model/skill 卡 → 组 DAG。
- SDGNode 仓库另备 `profile/sdg-extension.schema.json`（JSON Schema）在 CI 中校验扩展字段——**不修改 SDK schema**，利用其顶层 `additionalProperties: true` 政策。

### 4.4 契约字段填写指南（按资产类型）

| 卡类型 | 必填/关键段 | 要点 |
|---|---|---|
| data（栅格） | spatial(bbox/crs/resolution) + temporal + bands + access(protocol/endpoint/auth/format) + license + provenance + compliance | STAC 源用 `access.protocol: stac`；文件源 `https/s3`；ERA5 类 `format: Zarr` |
| data（统计/API） | GAAG statistical 合约（columns/record_count/spatial_key/time_key）；GeoCard 可无 spatial 段（非空间路径已被 SDK 验收覆盖，`spatial:false`） | 配对 fetch skill 的 id 写入 `geonexus:sdg.related_cards` 或 tags |
| model | inputs/outputs（**required 项即调用契约**）+ runtime(gpu/cpu/memory) + access.protocol(`https`\|`batch`) + interface{type: inference-http} + provenance（HF repo/论文）+ license + trust | 权重不进卡；endpoint 指推理服务；`trust.verified` 仅在通过冒烟测试后置 true |
| skill | inputs/outputs + capabilities + interface{type: geomcp-skill, version} | 远程 OGC/OGE 技能由适配器生成，标注底层服务 |
| workflow（案例卡） | composition.components（id/role/step/alias）+ params（reusable/fixed + target）+ recipe_ref（含 data_snapshot） | **口径参数必须 `scope: fixed`**（如基准年、指标定义版本），复用自由度放 reusable |
| knowledge | text 合约（content_type/language）+ interface.type（`indicator-definition`\|`report`\|`ontology`）+ provenance | 运行产物报告只能由 `report_card_from_run` 生成（来源四件套 + checksum） |
| compute | runtime(cpu/memory/gpu) + capabilities（`inference`/`batch`）+ access.endpoint | 调度器按声明准入；GPU 显存仅在声明时记账 |

### 4.5 合规与可见性分级策略

| sensitivity | 适用 | 示例 |
|---|---|---|
| public | 开放许可产品、开源模型 | Copernicus/Sentinel、WorldCover、GHSL、WorldPop、OSM、Prithvi/Clay（Apache/MIT） |
| restricted | 免费注册后使用、学术许可 | EOG VIIRS 夜光、LandScan、SDGSAT-1（开放科学计划需申请）、ACAG（非商业） |
| sensitive | 微数据、可定位到个体/小群体 | DHS 地理编码聚类、手机信令、入户调查微数据 |
| secret | 保留级 | （SDG 场景一般不用） |

- `compliance.sovereignty`：`CN`（高分/国产统计/SDGSAT-1 数据节点）、`EU`（Copernicus）、`US`（NASA/USGS/EOG）、`intl`（UN/世界银行/FAO）。
- 复合案例卡引用 restricted/sensitive 组件 → **可见性继承**自动降级；对不可见者返回 404。
- license 用 SPDX；非标许可用 `{name, url}` + `compliance.restrictions`（如 `["no-commercial-use", "platform-dependent"]`）；`security/legal_ontology` 在注册门控中校验组合合法性（如"案例卡 CC-BY 但引用 NC 数据"→ 拒绝或降级）。

---

## 5. 五条注册管线

### 管线 1：STAC / 标准服务采集（现成适配器，P0）

```
CDSE/Planetary Computer/EarthSearch/Sentinel Hub
  → adapters.sentinel_hub / stac.py / card import-stac / import-ogc-* 
  → GeoCard(data) → GAAG 合约 → register(status=pending) → 评审 approve → 可发现
```

- 命令面：`geonexus card import-stac <url>`、`card import-ogc <url> --collection X`、`card import-ogc-records/-tiles/-coverage`、`card import-ogc-legacy`（WMS/WMTS）。
- **粒度策略（防卡目录爆炸）**：注册 **collection 级目录卡**（一张卡描述整个产品：时空范围=全集、access 指 STAC endpoint），item 级检索留给运行期 STAC API；目录卡的 `recipe_ref.data_snapshot` 记录采集时的 catalog 版本。
- 定时同步：cron/GitHub Action 跑采集脚本 → 新版本 → pending → 评审；`registry sync` 做节点间对等同步。
- OSM：`adapters/osm.py`（Overpass，building/water/road/landuse 模板 + 镜像故障转移）直接产卡入 GAAG。

### 管线 2：文件上传 + GAAG 扫描（现成机制，P0）

```
upload（GeoTIFF/GPKG/NC/Zarr/LAS/CSV/Parquet/PDF…）
  → metadata.inspect_raster / gaag.scanner.scan_*（8 类合约按扩展名 detect_asset_type）
  →（可选）LLM 生成描述（GEONEXUS_LLM_API_KEY；缺省 FeatureEmbedder 离线可用）
  → embed → GAAGContract → register(pending) → 评审 → approve
```

- Web BFF REST：`POST /api/datasets/upload → /submit → /pending → /approve|reject`（geonexus-web 参考 UI）。
- 适用：GHSL/GSW/Hansen/SoilGrids 文件库、国产数据产品（中国 LUCC、行政边界、统计年鉴表）、夜光产品本地镜像。
- 统计表格自动抽取 columns/record_count/spatial_key → statistical 合约（FAOSTAT 快照、年鉴 CSV）。

### 管线 3：API 数据源工厂（data 卡 + fetch skill 配对，薄封装，P0–P1）★需 SDGNode 开发

**模式**：REST 统计/主题 API 没有空间契约与执行入口，拆成两半注册——
1. **数据卡**（knowledge-of-data）：描述该 API 的覆盖范围（指标清单、国家/年份维度、更新频率）、statistical 合约（columns 由源 schema 生成）、`access.protocol: https`、`geonexus:sdg` 指标绑定；
2. **伴生 fetch skill**（在统计 API 节点上）：`inputs: {indicator, area, year_start, year_end}` → 调 API → 输出 CSV/GeoJSON（挂接到国家边界矢量做空间化）→ 供 recipe step 引用（`uses: sdg.skill.stats.fetch-faostat`）。

- YAML 工厂：`sources/*.source.yaml`（清单：base_url、认证、指标维度、列 schema、SDG 绑定）→ 脚本批量生成数据卡 + skill 卡 → `card validate` → 注册。
- 首批覆盖：UN SDG Global Database、世界银行 WDI、FAOSTAT、WHO GHO、GBIF、GFW（森林警报）、GDACS、NASA POWER、OpenAQ。
- 这正是"数据卡+算子"分离对 SDG 的意义：**指标口径（知识卡）与数据获取（skill）与评估算法（skill）三者独立演进**。

### 管线 4：模型封装（HF 权重 → provider 服务 → model 卡，P1–P2）

```
HuggingFace 权重（Prithvi-EO-2.0 / Clay / samgeo / OSDG / 自训 GBDT）
  → SDGNode 侧 FastAPI 封装（遵循 MODEL.md 线上约定）
      · InferenceProvider:  POST /invoke {"model","inputs","params","request_id"} → {"outputs"}
      · BatchProvider:      POST → {"job_id","status"} ; GET /{job_id} 轮询 → outputs
  → model 卡（inputs/outputs 契约 + runtime.gpu + access.protocol https|batch）
  → compute 卡（GPU 节点 runtime 声明）注册进 CAFE worker 池
  → geo.invoke：输入契约 → 算力门禁(match_resource, retarget) → provider → 输出契约
  → ModelBackend → GeoTask 调度器（准入/优先级/公平/回填）
```

- **首批 5 个模型服务**（示例）：
  | 模型 | 任务 | provider | runtime | SDG 用途 |
  |---|---|---|---|---|
  | Prithvi-EO-2.0-600M-TL | 时序嵌入/微调头（洪水、火烧迹地、作物） | Batch（HPC） | 1×A100 | 13/15/2 |
  | Clay v1.5 | 嵌入 + 相似度检索 + 洪水/土地覆盖头 | Inference | 1×A10 | 6/11/13/15 |
  | samgeo（SAM2） | 提示式分割（水体、建成区、绿地） | Inference | 1×T4 | 6/11 |
  | OSDG 2.0 | 文本 → SDG 标签（CPU） | Inference | none | 17（文献/报告对齐） |
  | PM2.5-GBDT | AOD+气象 → PM2.5 格点（CPU） | Inference | none | 3.9.1/11.6.2 |
- **不做**（沿 SDK 边界）：不托管训练/微调/评测；权重与镜像由 SDGNode 模型仓库管理，卡内 `provenance.lineage` 记录权重版本与镜像 digest（可复现性）。
- 权重不开放者 → knowledge 目录卡（§2.3）。

### 管线 5：方案沉淀（Recipe + 案例卡 + 报告合约，P2–P3）

```
指标评估方法论 → recipe.yaml（params/requires/steps/outputs/data_snapshot）
  → geonexus recipe validate → recipe register --url（pending）→ 评审 approve
案例卡（workflow）：composition(数据/算子/报告引用) + params(reusable|fixed) + recipe_ref
  → 客户端 geo.plan(recipe, params, run_id) → RunPlan
  → CAFE/GeoTask 执行（steps → skills/models，下推到数据所在节点）
  → deliverables → report_card_from_run → knowledge 卡（report 合约：checksum + run/recipe/params/snapshot）
  → 复用：recipe fork（换区域/年份，方法参数 fixed 不动）→ 新地址 → 评审 → 运行
```

- 治理要点（全部为 SDK 现成语义）：只有 APPROVED 版本可被 resolve（审批门不可绕过）；fork 是复用的可执行定义；报告无来源四件套拒绝入册；可见性继承防"引用即泄露"。
- SDGNode 定义报告模板 `tpl.sdg-report`（composition.template 绑定）：指标口径说明 + 数据快照 + 图表 + 不确定性声明。

---

## 6. 示例卡片与 Recipe

### 6.1 data 卡：ESA WorldCover（STAC 目录级）

```yaml
geocard_version: "1.0"
id: sdg.data.esa.worldcover-2024
type: data
name: ESA WorldCover 2024（10 m 全球土地覆盖）
description: >-
  ESA WorldCover 10 m 全球土地覆盖产品（2024 版），11 类土地覆盖，
  支撑 SDG 11.3.1 / 15.1.1 / 15.3.1 等指标的土地覆盖分量。
tags: [land-cover, global, 10m, sdg:15, sdg:11]
spatial:
  bbox: [-180, -90, 180, 90]
  crs: "EPSG:4326"
  resolution: 10
temporal:
  start: "2024-01-01T00:00:00Z"
  end: "2024-12-31T23:59:59Z"
  interval: "P1Y"
bands:
  - {name: map, dtype: uint8, units: "class", description: "11 类土地覆盖分类码"}
capabilities: [land-cover, land-cover-change]
access:
  protocol: stac
  endpoint: "https://catalogue.dataspace.copernicus.eu/stac/collections/worldcover"
  auth: none
  format: COG
provenance:
  provider: ESA / VITO
  source: "https://esa-worldcover.org"
  lineage: "Sentinel-1/2 融合分类；2020→2021→2024 版本序列"
license: "CC-BY-4.0"
compliance: {sovereignty: EU, sensitivity: public}
trust: {verified: true, score: 0.95}
geonexus:sdg:
  goals: [11, 15]
  indicators: ["11.3.1", "15.1.1", "15.3.1"]
  custodian: "ESA"
```

### 6.2 data 卡：UN SDG 全球指标数据库（statistical + fetch skill 配对）

```yaml
geocard_version: "1.0"
id: sdg.data.unsd.sdgdb
type: data
name: UN SDG Global Database（官方指标序列）
description: >-
  联合国统计司 SDG 全球指标数据库：231 项唯一指标的国家/区域年度序列与元数据。
  非空间表格资产（spatial:false 语义），空间化由伴生技能与国家边界矢量完成。
tags: [statistics, sdg-official, indicator-series, non-spatial]
capabilities: [indicator-query]
access:
  protocol: https
  endpoint: "https://unstats.un.org/sdgapi/sdg"
  auth: none
  format: JSON/CSV
provenance: {provider: UNSD, source: "https://unstats.un.org/sdgs/"}
license: {name: "UN Terms of Use", url: "https://www.un.org/en/about-us/terms-of-use"}
compliance: {sovereignty: intl, sensitivity: public}
trust: {verified: true, score: 0.99}
geonexus:sdg:
  goals: [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]
  related_cards: ["sdg.skill.stats.fetch-unsd"]
# GAAG statistical 合约（注册时扫描生成）：columns=[series, geoAreaCode, timePeriodStart, value, ...]
```

伴生技能卡（要点）：

```yaml
id: sdg.skill.stats.fetch-unsd
type: skill
name: UNSD SDG 指标序列获取
description: 按 indicator/area/时间窗查询 UNSD API，返回 CSV 与（可选）国家面空间化 GeoJSON。
interface: {type: geomcp-skill, version: "1.0"}
capabilities: [indicator-query]
inputs:
  - {name: indicator, type: string, required: true, description: "如 15.3.1"}
  - {name: area_codes, type: array, required: false}
  - {name: year_start, type: number, required: false}
  - {name: year_end, type: number, required: false}
  - {name: spatialize, type: boolean, required: false, description: "与国家边界矢量连接输出 GeoJSON"}
outputs:
  - {name: series_csv, type: file}
  - {name: series_geojson, type: file}
access: {protocol: geomcp, endpoint: "http://sdg-stats-node:8787", auth: apikey}
```

### 6.3 model 卡：Prithvi-EO-2.0-600M（Batch provider + 算力门禁）

```yaml
geocard_version: "1.0"
id: sdg.model.prithvi.eo2-600m-tl
type: model
name: Prithvi-EO-2.0-600M-TL（NASA/IBM 对地观测基础模型）
description: >-
  ViT-MAE 多时序基础模型（HLS 30 m 预训练，含经纬度/DOY 嵌入的 TL 变体）。
  下游头：洪水淹没、火烧迹地、作物类型。批作业模式（大范围推理）。
tags: [foundation-model, hls, flood, burned-area, crop, sdg:2, sdg:13, sdg:15]
capabilities: [flood-mapping, burned-area-mapping, crop-mapping, eo-embeddings]
interface: {type: inference-http, version: "1.0"}
inputs:
  - {name: chips, type: raster, required: true, description: "HLS 时序切片 COG/Zarr 引用列表"}
  - {name: time_indices, type: array, required: true}
  - {name: head, type: string, required: true, description: "flood|burned|crop|embeddings"}
outputs:
  - {name: class_map, type: raster}
  - {name: embeddings, type: array}
runtime: {cpu: 8, memory: "64Gi", gpu: "1xA100"}
access:
  protocol: batch            # → BatchProvider（submit/poll/collect），不会静默降级为同步
  endpoint: "http://sdg-model-node:8801/prithvi"
  auth: apikey
provenance:
  provider: NASA + IBM + Jülich
  source: "https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-600M-TL"
  lineage: "arXiv:2412.02732；SDGNode 镜像 digest sha256:…；TerraTorch 微调头 v0.3"
license: "Apache-2.0"
compliance: {sovereignty: US, sensitivity: public}
trust: {verified: true, score: 0.9}
```

### 6.4 skill 卡：SDG 11.3.1 土地消耗率算子

```yaml
geocard_version: "1.0"
id: sdg.skill.urban.lcrpgr
type: skill
name: 土地消耗率/人口增长率（LCRPGR, SDG 11.3.1）
description: >-
  输入建成区栅格（GHS-BUILT-S）与人口栅格（GHS-POP）两期数据与城市边界，
  按 UN-Habitat 口径计算土地消耗率、人口增长率及其比值。
interface: {type: geomcp-skill, version: "1.0"}
capabilities: [built-up-extent, population-grid, zonal-statistics, lcrpgr]
inputs:
  - {name: built_up_t0, type: raster, required: true}
  - {name: built_up_t1, type: raster, required: true}
  - {name: population_t0, type: raster, required: true}
  - {name: population_t1, type: raster, required: true}
  - {name: aoi, type: vector, required: true, description: "城市分析边界"}
outputs:
  - {name: lcr, type: number, description: "土地消耗率"}
  - {name: pgr, type: number, description: "人口增长率"}
  - {name: lcrpgr, type: number}
  - {name: transition_map, type: raster}
access: {protocol: geomcp, endpoint: "http://sdg-analysis-node:8787", auth: apikey}
tags: [sdg:11, urban, indicator-operator]
geonexus:sdg: {goals: [11], indicators: ["11.3.1"], custodian: "UN-Habitat"}
```

### 6.5 knowledge 卡：指标定义（planner 路由表）

```yaml
geocard_version: "1.0"
id: sdg.knowledge.unsd.indicator-11.3.1
type: knowledge
name: SDG 11.3.1 指标定义与计算方法（Land consumption rate to population growth rate）
description: >-
  UNSD 官方口径：LCRPGR = 土地消耗率 / 人口增长率；数据源推荐 GHSL；
  本卡是 GeoAgent 的指标→能力路由入口。
interface: {type: indicator-definition, version: "2025"}
capabilities: [indicator-query]
provenance: {provider: UNSD/UN-Habitat, source: "https://unstats.un.org/sdgs/metadata/"}
license: "CC-BY-4.0"
compliance: {sovereignty: intl, sensitivity: public}
trust: {verified: true, score: 0.99}
geonexus:sdg:
  goals: [11]
  indicators: ["11.3.1"]
  tier: "I"
  custodian: "UN-Habitat"
  unit: "ratio"
  disaggregation: ["city", "national"]
  requires_capabilities: [built-up-extent, population-grid, zonal-statistics, lcrpgr, report-render]
  related_cards:
    - sdg.data.jrc.ghs-built-s
    - sdg.data.jrc.ghs-pop
    - sdg.skill.urban.lcrpgr
    - recipe://sdg/11-3-1-lcrpgr@1.0.0
```

### 6.6 workflow 案例卡 + Recipe：SDG 11.3.1（沿 15.3.1 示例范式）

```yaml
# ---- 案例卡 ----
geocard_version: "1.0"
id: geocard.case.sdg-11-3-1-chn-2020
type: workflow
name: SDG 11.3.1 土地消耗率评估（中国城市 2020）
description: 3 数据 + 1 算子 + 1 报告：可复用、可溯源的城市土地消耗评估整体方案。
spatial: {bbox: [73.5, 3.8, 135.1, 53.6], crs: "EPSG:4326"}
temporal: {start: "2015-01-01T00:00:00Z", end: "2020-12-31T00:00:00Z"}
composition:
  components:
    - {id: sdg.data.jrc.ghs-built-s, role: data, step: s2}
    - {id: sdg.data.jrc.ghs-pop, role: data, step: s2}
    - {id: sdg.data.boundary.chn-cities, role: data, step: s1}
    - {id: sdg.skill.urban.lcrpgr, role: skill, step: s3}
    - {id: report.sdg1131.chn.2020, role: knowledge, step: s4, alias: report}
  template: tpl.sdg-report
params:
  params:
    - {name: year, type: integer, required: true, minimum: 2015, maximum: 2025, target: s3.params.year}
    - {name: city, type: enum, enum: ["北京", "上海", "广州", "武汉"], default: "北京", target: s1.params.city}
    - {name: baseline, type: integer, scope: fixed, default: 2015,
       description: "基准年钉死：换基准年 = 换指标口径，不是换参数"}
    - {name: method, type: string, scope: fixed, default: "UN-Habitat 2025", target: s3.params.method}
recipe_ref:
  recipe_id: "recipe://sdg/11-3-1-lcrpgr@1.0.0"
  entrypoint: s1
  data_snapshot: {ghs: "R2023A", boundary: "2024.12"}
tags: [sdg:11, urban, case]
```

```yaml
# ---- Recipe（recipe://sdg/11-3-1-lcrpgr@1.0.0，节选）----
recipe_version: "1.0"
id: recipe://sdg/11-3-1-lcrpgr@1.0.0
name: SDG 11.3.1 LCRPGR 评估（可复用方案）
license: CC-BY-4.0
params:
  - {name: year, type: integer, required: true, minimum: 2015, maximum: 2025, target: s3.params.year}
  - {name: city, type: enum, enum: ["北京", "上海", "广州", "武汉"], default: "北京", target: s1.params.city}
  - {name: baseline, type: integer, scope: fixed, default: 2015}
requires: [sdg.data.boundary.chn-cities, sdg.data.jrc.ghs-built-s, sdg.data.jrc.ghs-pop, sdg.skill.urban.lcrpgr]
steps:
  - id: s1
    kind: skill
    uses: sdg.data.boundary.chn-cities
    description: 取目标城市行政边界，生成分析掩膜。
    params: {city: "${params.city}"}
    outputs: {aoi: 城市边界（GeoJSON）, mask: 栅格化掩膜}
  - id: s2
    kind: skill
    uses: sdg.skill.raster.clip-stack
    depends_on: [s1]
    description: 按掩膜裁剪并对齐两期 GHS 建成区与人口栅格。
    inputs: {mask: "step://s1/mask"}
    outputs: {built_up_t0: 基期建成区, built_up_t1: 目标期建成区, pop_t0: 基期人口, pop_t1: 目标期人口}
  - id: s3
    kind: skill
    uses: sdg.skill.urban.lcrpgr
    depends_on: [s2]
    params: {year: "${params.year}", baseline: "${params.baseline}"}
    inputs:
      built_up_t0: "step://s2/built_up_t0"
      built_up_t1: "step://s2/built_up_t1"
      population_t0: "step://s2/pop_t0"
      population_t1: "step://s2/pop_t1"
      aoi: "step://s1/aoi"
    outputs: {lcr: 土地消耗率, pgr: 人口增长率, lcrpgr: 比值, transition_map: 变化图}
    timeout_seconds: 1800
    resources: {cpu: 4, memory_mb: 8192}
  - id: s4
    kind: skill
    uses: sdg.skill.report.render
    depends_on: [s3]
    description: 按 tpl.sdg-report 渲染带图、带口径说明、带数据快照的评估报告。
    params: {format: html, template: tpl.sdg-report, title: "SDG 11.3.1 土地消耗率评估"}
    inputs: {lcrpgr: "step://s3/lcrpgr", transition_map: "step://s3/transition_map"}
    outputs: {report: 报告文件}
entrypoint: s1
outputs:
  - {name: lcrpgr_value, from: s3.lcrpgr, role: data, media_type: application/json}
  - {name: transition_map, from: s3.transition_map, role: data, media_type: image/tiff}
  - {name: report, from: s4.report, role: knowledge, media_type: text/html}
data_snapshot: {ghs: "R2023A", boundary: "2024.12"}
```

运行产物报告由 `report_card_from_run(plan, …)` 自动生成 knowledge 卡（checksum + run/recipe/params/snapshot 四件套），无来源拒绝入册——**评估结论从此可被安全引用**。

### 6.7 compute 卡

```yaml
geocard_version: "1.0"
id: sdg.compute.local.gpu-a10
type: compute
name: SDGNode 本地 GPU 推理池（1×A10）
description: 承载 samgeo/Clay/OSDG 等中小模型同步推理；CAFE worker 已接入。
capabilities: [inference]
runtime: {cpu: 16, memory: "64Gi", gpu: "1xA10"}
access: {protocol: geomcp, endpoint: "http://sdg-model-node:8787", auth: apikey}
compliance: {sovereignty: local-node, sensitivity: public}
```

---

## 7. 客户端发现与使用路径

### 7.1 发现（Discovery）

| 客户端 | 路径 |
|---|---|
| LLM 助手（本 GUI、Claude、其他 MCP host） | `geonexus mcp serve --port 9000`（Streamable HTTP）或 `mcp run --bare`（stdio）→ MCP 工具 `geo_capabilities` / `geo_describe` / `geo_execute` / `geo_plan` / `geo_invoke` |
| Python | `RegistryClient.search(capability="land-cover", bbox=[…])`（仅 approved）→ `ContractValidator().check(card, …)` |
| Java | 轻量 GeoMCP 客户端（SpatialContext/TemporalContext/ExecuteRequest） |
| Web | BFF 搜索 + GGIHS 跨注册中心聚合 dashboard |
| CLI | `geonexus registry search --capability lcrpgr`、`inspector` |

典型发现链（语义层）：自然语言目标 → GeoAgent `llm_planner` → 指标知识卡（`requires_capabilities`）→ GAAG 语义检索（pgvector，中英跨语言建议启用 LLM embedder）→ 候选 data/model/skill 卡 → ContractValidator 逐卡校验 → DAG。

### 7.2 使用（四种执行入口）

1. **`geo.execute`**（即席技能调用）：`skill + geocards + spatial/temporal + params` → 契约校验（2000 拒绝附 reasons）→ 节点本地技能或远程 OGC/OGE 技能 → outputs。
2. **`geo.plan` + 执行**（方案复用）：recipe 地址 + 参数 → RunPlan（先契约、`${params.x}` 替换）→ CAFE/GeoTask 下推执行 → deliverables → 报告卡。
3. **`geo.invoke`**（模型调用）：输入契约 → 算力门禁（不匹配零字节外发，result 内 `error_code=no_compatible_compute + reasons`）→ provider（同步/批）→ 输出契约校验。
4. **`agent ask`**（自然语言目标）：`geonexus agent ask "评估武汉市 2020 年土地消耗率"` → planner 检索能力 → DAG → 执行 → 报告卡（P4 打通）。

### 7.3 治理动作

- 注册：管线 1–5 → `status=pending`（对发现不可见）→ 评审 `POST /cards/{id}/approve|reject`（API-Key 门控）；recipe 同词汇（`/recipes/{address}/approve`，多版本歧义 → 409）。
- 复用：`recipe fork`（新地址、改 reusable 参数、fixed 口径不动、回 pending 重审）。
- 审计：报告合约四件套 + checksum；`task events`（seq 回放）；可见性继承（404 语义）；legal ontology 许可校验。

---

## 8. 优先指标-能力绑定矩阵

| 指标 | data 卡 | model 卡 | skill 卡 | Recipe | 状态 |
|---|---|---|---|---|---|
| **15.3.1 LDN** | WorldCover/CCI、SoilGrids SOC、边界 | —（可选生产力模型） | transition-matrix、ldn-calculator、report-render | **SDK 已有示例**（扩展 LDN 三子指标：覆盖+生产力+SOC） | ★ 最快见效 |
| **11.3.1 LCRPGR** | GHS-BUILT-S、GHS-POP、城市边界 | —（可选建筑分割） | lcrpgr、clip-stack、report-render | §6.6 已设计 | P3 首批 |
| **6.6.1 水生态面积** | JRC GSW、Sentinel-1/2（CDSE 现成适配器） | samgeo 水体分割 | water-extent-change、gsw-trend | 待编写 | P3 |
| **3.9.1 空气污染暴露** | ACAG PM2.5、GHS-POP、S5P NO₂ | PM2.5-GBDT（首批模型服务） | exposure-overlay（人口加权） | 待编写 | P3 |
| **15.1.1 森林面积** | Hansen GFC、WorldCover | — | forest-area-change、glad-alert-fetch | 待编写 | P2 |
| **14.5.1 MPA 覆盖** | WDPA、EEZ 边界 | — | protected-coverage-ratio | 待编写 | P2 |
| **11.7.1 公共开放空间** | 高分影像、WorldCover 城市绿地类 | 绿地分割（Clay 头/samgeo） | greenspace-ratio、isochrone-access | 待编写 | P4（高分数据许可） |
| **13.1.1 灾害暴露** | GDACS、Sentinel-1、GHS-POP | Prithvi 洪水头（Batch） | flood-extract、exposure-assessment | 待编写 | P3–P4 |
| **1.1/1.4 贫困制图** | 夜光 VIIRS（restricted）、OSM（现成适配器）、DHS 聚类（sensitive） | poverty-estimator | dasymetric、poverty-inference | 待编写 | P4（合规前置） |
| **2.4.1 作物/产量** | Sentinel-2 STAC、ERA5 Zarr、cropland 图 | Presto / Prithvi crop 头 | crop-mapping、yield-estimate | 待编写 | P4（大批作业） |

**能力缺口清单**（需 SDGNode 开发的 skill，按复用度排序）：`clip-stack`、`zonal-statistics`、`transition-matrix`、`exposure-overlay`、`dasymetric`、`report-render`（模板引擎）、`water-extent-change`、`lcrpgr`、`protected-area-ratio`、各源 `fetch-*`。前 6 个是多指标共享的"公共算子"，优先实现。

---

## 9. 实施路线图（P0–P4）

### P0（第 1–2 周）：Profile 与首批注册
- 交付：命名规范/词表 v0/`geonexus:sdg` 扩展 + Profile Schema（CI 校验）；**30 张首批卡**（附录 B）；registry（`registry start --persist --api-key`）+ 评审流跑通；MCP 桥连通（`mcp serve`）。
- 验收：`card validate` 全绿；`registry search --capability …` 命中且仅返回 approved；`geo.describe` 返回完整卡；GAAG `validate_contract` 能拒绝缺字段卡；MCP 客户端可列 capabilities。

### P1（第 3–6 周）：数据管线与公共算子
- 交付：管线 1 定时采集（CDSE/PC/EarthSearch collection 级卡 ×10+）；管线 2 文件入库（GHSL/GSW/Hansen/边界/统计快照）；OSM 适配器接入；管线 3 首批 5 个 API 源（UNSD/WDI/FAOSTAT/GBIF/GDACS）+ fetch skill；**6 个公共算子 skill**（clip-stack、zonal-statistics、transition-matrix、ndvi/indices、report-render、water-extent）容器化上节点。
- 验收：e2e 脚本（仿 `scripts/acceptance_recipe_e2e.py`）：真实 STAC 数据 → geo.execute 跑 zonal stats/转移矩阵成功；OSM building 查询 → GAAG 入册 → 语义检索命中；契约外请求返回 2000+reasons。

### P2（第 7–9 周）：模型调用闭环
- 交付：管线 4 首批 5 个模型服务（Prithvi/Clay/samgeo/OSDG/PM2.5）+ model 卡 + compute 卡 + CAFE worker 接入；ModelBackend→GeoTask；调度器准入（GPU 记账）。
- 验收：`geo.invoke` 成功路径（真 HTTP 服务）；无 GPU 时 `no_compatible_compute` 带 reasons 且**零请求外发**（计数断言）；Batch submit/poll/collect 全路径；门禁结论 retarget 生效。

### P3（第 10–13 周）：指标方案库与报告治理
- 交付：管线 5：Recipe ×4（15.3.1 扩展、11.3.1、6.6.1、3.9.1）+ 案例卡 + 报告模板 tpl.sdg-report；fork/approve 治理演练；可见性继承测试（restricted 组件 → 案例 404）。
- 验收：每指标一条 acceptance 链：fork → 改参数 → approve → geo.plan → 运行 → 下载报告；报告卡含四件套 + checksum；未审批 recipe 不可 resolve（审批门不可绕过）；引用 sensitive 组件的案例对匿名调用者不可见（404 而非 403）。

### P4（第 14 周起）：联邦与智能化
- 交付：≥2 个机构注册中心（peer sync + GGIHS 聚合面板）；健康感知路由 + 委托；GeoAgent `agent ask` 自然语言→指标卡→能力检索→DAG→运行→报告；KG（Neo4j）指标-能力-政策图谱；pgvector + LLM embedder 中英跨语言语义检索；扩展指标（11.7.1、13.1.1、1.x 贫困、2.4.1）。
- 验收：跨注册中心发现 + 下推执行；agent 端到端产出可溯源报告；中文目标语句命中率评测。

---

## 10. SDK 缺口与扩展建议

全部建议均在 SDK 的**加法式扩展政策**内（顶层扩展字段、新适配器、新 skill），不要求改动已冻结契约：

| # | 缺口 | 影响 | 对策（SDGNode 侧 / 上游建议） |
|---|---|---|---|
| 1 | 无 REST/CSV-W/SDMX 适配器 | 统计 API 源不能像 STAC 一样直采 | 管线 3 的"数据卡+fetch skill"配对模式覆盖；建议上游加 `adapters/rest.py`（additive） |
| 2 | stac.py 是 Item 级 | collection 级目录卡需自行聚合 | 采集脚本做 collection 级卡（§5 管线 1 粒度策略） |
| 3 | GEE 无适配器且与主权原则相悖 | AlphaEarth/Dynamic World 等 GEE 原生资产 | wrapper skill（服务端持 service account）+ 目录卡；`restrictions: [platform-dependent]`；不镜像数据 |
| 4 | 不托管模型/无训练评测生命周期（设计如此） | 模型服务需自建 | SDGNode 模型仓库 + FastAPI provider 模板（管线 4）；权重/镜像 digest 进 provenance |
| 5 | agent 类型尚属"future" | agent 卡暂不可执行 | P4 前只登记描述性 agent 卡，不依赖其行为契约 |
| 6 | FeatureEmbedder 是词法级 | 中文查询/跨语言召回弱 | 启用 LLM embedder（`GEONEXUS_LLM_API_KEY`）+ pgvector；词表 v0 统一中英术语 |
| 7 | GeoCard `bands` 段不适配统计表 | 统计资产契约靠 GAAG statistical | 卡+合约互补（卡管发现/合规，GAAG 合约管字段级校验）——现有机制已够 |
| 8 | 扩展字段无官方校验 | `geonexus:sdg` 可能写歪 | SDGNode Profile Schema + CI（`card validate` 之外叠加 jsonschema 校验） |
| 9 | gRPC provider 明确不支持 | 高性能推理接入受限 | 统一走 HTTP/Batch；性能敏感场景在节点内网部署 |
| 10 | 产品版本漂移（WorldCover 2020/2021/2024） | 评估结论可比性 | id 带版本后缀 + `data_snapshot` 记录 + 报告合约固定快照（机制已备，规范执行） |

---

## 11. 风险与对策

| 风险 | 对策 |
|---|---|
| **许可/合规**（LandScan、Planet、ACAG 非商业、DHS 微数据） | compliance 三级声明 + legal ontology 门控 + 可见性继承；商业数据默认 restricted，案例卡引用即降级 |
| **数据主权/跨境**（高分数据、国家统计、DHS） | sovereignty 字段 + 节点本地化部署 + CAFE 下推（计算到数据，结果小体积出境）+ 聚合最小门槛写入 skill 契约 |
| **卡目录爆炸**（全球产品 item 级） | collection 级目录卡 + GGIHS 聚合 + 语义检索替代全量列举 |
| **可复现性**（权重/镜像/数据版本漂移） | provenance.lineage（权重版本+镜像 digest）+ data_snapshot + 报告 checksum；"答案变了因为数据动了"与"因为重跑了"可区分（recipe_ref.data_snapshot 语义） |
| **SDK 未完成部分**（agent、gRPC、REST 适配） | 路线图把强依赖排到 P4；P0–P3 只用已冻结契约与已验收机制 |
| **口径一致性**（遥感代理 vs 官方指标） | 指标知识卡固化官方定义（UNSD 元数据），方法参数 `scope: fixed`，报告强制含口径说明章节（tpl.sdg-report） |
| **评审瓶颈**（pending 积压） | 采集管线自动预检（schema+contract+legal）→ 人工只审语义与合规分级；批量审批脚本 + 409 歧义保护 |

---

## 附录 A：能力词表 v0

```
# 土地/覆盖
land-cover, land-cover-change, built-up-extent, impervious-surface, urban-morphology,
transition-matrix, ldn-assessment, forest-change, forest-cover, cropland-extent,
# 水
water-extent, water-quality, flood-mapping, drought-index, groundwater-stress,
# 大气/气候
pm25-estimation, pm25-exposure, no2-column, ghg-emission, climate-downscaling,
# 人口/社会
population-grid, dasymetric-disaggregation, nightlights, poverty-estimation,
accessibility, public-transport-access, greenspace-access,
# 生态/保护
protected-area-ratio, species-distribution, habitat-connectivity, coral-bleaching,
mangrove-extent, red-list-index,
# 农业
crop-mapping, yield-estimation, phenology,
# 灾害
landslide-susceptibility, fire-detection, storm-exposure, exposure-overlay,
# 分析原语
zonal-statistics, spatial-hotspot, gwr-analysis, kriging, network-isochrone,
# 平台原语
indicator-query, report-render, data-fetch, eo-embeddings, segmentation, change-detection
```

## 附录 B：首批注册清单（30 卡，P0）

| 类别 | 卡 |
|---|---|
| data×12 | Sentinel-2 L2A（CDSE collection 卡）、Sentinel-1 GRD（CDSE）、Landsat C2L2（PC/EarthSearch）、ESA WorldCover 2024、JRC GSW 1.4、JRC GHS-BUILT-S、JRC GHS-POP、Hansen GFC v1.12、WorldPop 2020、VIIRS 夜光（restricted）、OSM 中国城市要素（Overpass 模板卡）、UN SDG Global Database（statistical） |
| data(API)×4 | WDI、FAOSTAT、GBIF、GDACS（各配 fetch skill 卡） |
| knowledge×5 | UNSD 指标卡 ×3（15.3.1 / 11.3.1 / 6.6.1）、CBAS 地球大数据 SDG 报告 2024（text 合约）、SDGNode 词表卡 |
| model×3 | OSDG 分类器（CPU）、samgeo-SAM2（GPU）、PM2.5-GBDT（CPU）——先以目录卡+stub provider 注册，P2 转正式服务 |
| skill×4 | fetch-unsd、fetch-faostat、zonal-statistics、report-render |
| compute×2 | 本地 GPU 池（1×A10）、CPU 批队列 |

## 附录 C：协议与命令速查

**GeoMCP 方法**：`geo.capabilities` / `geo.describe` / `geo.execute` / `geo.health`（冻结）＋ `geo.plan`（recipe_planning）＋ `geo.invoke`（model_invocation）。
**错误码**：-32700/-32600/-32601/-32602/-32603；2000 契约不满足、2001 技能不存在、2002 卡不存在、2003 执行失败、2004 参数无效、2005 RECIPE_NOT_FOUND、2006 RECIPE_PARAM_INVALID；模型：no_compatible_compute / input_missing / invalid_spec / resource_unavailable / executor_lost / timeout / execution_error。
**常用命令**：

```bash
pip install "geonexus-sdk[mcp]"
geonexus registry start --persist registry.json --api-key $KEY     # 共享注册中心
geonexus node start                                                # 能力节点（GeoMCP :8787）
geonexus card validate cards/sdg.data.esa.worldcover-2024.yaml     # 卡校验
geonexus card import-stac <stac-url>                               # STAC 直采
geonexus card import-ogc <url> --collection lakes                  # OGC Features 导入
geonexus registry register <card.yaml> --status pending            # 提交评审
geonexus recipe validate recipes/sdg-11-3-1.yaml && \
geonexus recipe register recipes/sdg-11-3-1.yaml --url http://registry:8790
geonexus recipe fork recipe://sdg/11-3-1-lcrpgr@1.0.0 --params '{"city":"武汉"}' --url …
geonexus mcp serve --port 9000                                     # MCP 桥（LLM 客户端）
geonexus agent ask "评估武汉市 2020 年土地消耗率"                    # 自然语言目标
geonexus task events <task_id> --since 3                           # 事件回放
geonexus ggihs start                                               # 跨注册中心聚合
geonexus web start                                                 # BFF（上传/评审/检索）
```

---

*本方案与《SDG监测评估_数据源与地理空间AI技术体系梳理.md》配套：前者回答"有什么资源"，本文回答"如何把它们变成 GeoNexus 网络上可发现、可调用、可治理的能力"。落地时以 SDK `docs/GEOCARD.md`、`GEOMCP.md`、`MODEL.md`、`RECIPE.md`、`DATA_REGISTRATION.md` 为规范基准，以 `tests/conformance/` 与 `scripts/acceptance_recipe_e2e.py` 风格编写验收脚本。*
