# SDGNode — SDG 地理空间能力节点

基于 [GeoNexus-SDK](file:///D:/Repos/GeoNexus/GeoNexus-SDK)（GeoCard / GeoMCP / GeoNode / Recipe / GAAG）
把 SDG 监测评估的**数据源、空间分析工具与 AI 模型**注册为可发现、可校验、可调用、
可复现、可治理的地理空间能力。

## 文档

| 文档 | 内容 |
|---|---|
| `docs/SDG监测评估_数据源与地理空间AI技术体系梳理.md` | SDG 数据源 × GIS 软件 × 空间分析 × AI 模型全景梳理（资源侧） |
| `docs/GeoNexus-SDG能力注册技术方案.md` | GeoCard 注册技术方案：可注册性分析、架构、五条管线、Profile、路线图（方案侧） |

## 仓库结构

```
profile/        SDGNode Profile：sdg-extension.schema.json（geonexus:sdg 扩展校验）
                capabilities-vocabulary.yaml（能力受控词表 v0）· naming.yaml（ID 命名规范）
sources/        管线 3 API 数据源清单（*.source.yaml：UNSD/WDI/FAOSTAT/GBIF/GDACS）
scripts/        generate_api_cards.py（清单→成对卡工厂）· validate_cards.py（四层质量门）
                register_batch.py / start_sdg_node.py（**平台能力节点启动器**：advertise+自注册算力+委托）
                start_mcp_bridge.py / check_discovery.py（P0 发现链）
                run_recipe_e2e.py / harvest_stac.py / check_skills_live.py（P1 执行链）
                check_model_invoke.py（P2 模型闭环）· final_acceptance.py（单进程串起全部验收）
                check_capability_node.py（平台注册→发现→委托调用 5 项）· verify_live_node.py（对在跑节点的外部核验）
sdgnode_skills/ 公共算子 handler（clip-stack/zonal/lcrpgr/report-render/ndvi/transition/water）+ 合成研究区
                + self_compute.py（自注册算力卡：实时 CPU/内存探测，GPU 诚实声明）
services/       model_provider.py（MODEL.md 线上约定的契约参考服务：/osdg /pm25 /prithvi/jobs）
cards/          GeoCard 卡片库（data / model / skill / knowledge / compute / workflow / harvest / generated）
recipes/        Recipe 方案库（recipe://sdg/<indicator>@semver）
state/          registry.json / recipes.json / demo/（运行态）· runs/（证据链落盘，仓库根）
```

## 卡片库清单（P0–P2 落地：41 张文件卡 + 运行时自注册卡 + 1 Recipe）

- **data ×17**：Sentinel-2 L2A、Sentinel-1 GRD、Landsat C2L2（collection 级 STAC 目录卡）；
  WorldCover 2024、JRC GSW 1.4、GHS-BUILT-S、GHS-POP、Hansen GFC 1.12、WorldPop 2020、
  EOG VIIRS 夜光（restricted）、OSM 中国城市要素、中国城市边界（draft）；
  API 统计源 ×5（工厂生成：UNSD/WDI/FAOSTAT/GBIF/GDACS，statistical 语义）
- **model ×4**：Prithvi-EO-2.0-600M-TL（batch/GPU）、samgeo-SAM2（inference/GPU）、
  OSDG 2.0 文本分类（CPU）、PM2.5-GBDT（CPU）
- **skill ×9**：zonal-statistics、clip-stack（draft）、lcrpgr（draft）、report.render
  ＋ fetch-unsd/wdi/faostat/gbif/gdacs（工厂生成，与 API 数据卡成对）
- **knowledge ×5**：UNSD 指标定义卡 ×3（11.3.1 / 15.3.1 / 6.6.1，GeoAgent 路由表）、
  CBAS 地球大数据报告 2024、能力词表 v0
- **compute ×2**：GPU 推理池（1×A10）、CPU 批处理池；另有**运行时自注册算力卡** `sdg.compute.sdg-node.self-pool`
  （节点开机构造、真实 CPU/内存探测、GPU 诚实声明 none，不落盘——见"平台能力节点"）
- **workflow ×1**：`geocard.case.sdg-11-3-1-chn-2020`（复合案例卡，沿 SDK sdg_15_3_1 范式）
- **recipe ×1**：`recipe://sdg/11-3-1-lcrpgr@1.0.0`（4 步 DAG：边界→裁剪对齐→LCRPGR→报告）
- **harvest ×1（P1）**：STAC fixture 管线采集的 Sentinel-2 L2A Item 卡（管线 1 演示，默认 restricted）
- **generated ×N（P1）**：`report.11-3-1-lcrpgr.report.run-*`（端到端每次运行一张产物卡 · GAAG report 合约；当前 2 张）

## 验收状态（本机实测，均可重放）

| 阶段 | 内容 | 结果 |
|---|---|---|
| P0 | 40 卡 pending→approve、registry 三查、GeoMCP geo.capabilities/describe/plan/2002 语义、MCP 桥 geo_* 工具 | ✅ check_discovery 14/14 |
| P1 | 合成数据端到端跑 `recipe://sdg/11-3-1-lcrpgr@1.0.0`（武汉：LCR≈4.49%/年、PGR≈1.22%/年、11.3.1≈3.68——**合成口径仅验管线**）→ GAAG report 合约 satisfied（sha256+章节可核验）→ 报告卡入册；8 个算子装载进 GeoNode 且 `geo.execute` 实测；STAC fixture 采集 | ✅ run_recipe_e2e + check_skills_live |
| P2 | 契约参考服务（services/model_provider.py）：OSDG/PM2.5 `invoke_model` 成功路径、samgeo 算力门禁拒绝（**零字节外发**：/samgeo 计数 0）、prithvi batch submit→poll→collect、registry 算力发现→retarget 真实改址；3 张实测模型卡 trust.verified=true | ✅ check_model_invoke 5/5 |
| 最终 | final_acceptance.py 单进程串起 P0/P1/P2（线程内服务、自动选空闲端口） | ✅ 11/11 PASS，exit 0 |
| 平台能力节点 | start_sdg_node.py 注册式启动（advertise 42 条重宣 + 自注册算力卡 + 委托绑定）；check_capability_node 注册视图/检索发现/直调/**跨节点委托**/算力闭环；verify_live_node 对在跑生产节点做外部核验 | ✅ 5/5 + 4/4 PASS，exit 0 |

注：P2 模型服务是**契约级参考实现**（词法分类/代理公式/批作业桩，全部诚实标记 synthetic/v0），
不含真实权重；真实权重接入按技术方案管线 4 替换服务内部即可——卡契约、门禁、验收脚本不变。

## 快速开始

```bash
# 1) 重新生成 API 数据源成对卡（sources/*.source.yaml → cards/）
python scripts/generate_api_cards.py

# 2) 四层质量门：L1 SDK JSON Schema · L2 Profile（命名/词表/扩展/合规/模型协议）
#    L3 SDK 实加载（load_geocard + ContractValidator 自检 + 可见性继承）
#    L4 Recipe（load_recipe + materialize 冒烟）
python scripts/validate_cards.py --sdk-src D:\Repos\GeoNexus\GeoNexus-SDK\src

# 3) 作为 GeoNexus Platform 能力节点启动（注册 + 自述算力 + 委托，advertise 默认开启）
geonexus registry start --persist state/registry.json --recipes state/recipes.json --api-key $KEY --health-probe
python -m uvicorn services.model_provider:app --host 127.0.0.1 --port 8801   # 模型服务（算力卡申报的模型运行地）
python scripts/start_sdg_node.py --port 8793 --registry http://127.0.0.1:8790 --api-key $KEY --with-skills --refresh
#    对**在跑节点**从平台侧核验（发现 + 直调 + 跨节点委托）：
python scripts/verify_live_node.py
python scripts/start_mcp_bridge.py --port 9000 --with-skills   # LLM 客户端经 MCP 发现 geo_*
#    评审治理走 register_batch.py（pending→approve）；能力节点自带 advertise 走自宣注册

# 4) 单机一键全链路验收（P0 发现 + P1 执行 + P2 模型闭环；线程内服务，跑完即停）
python scripts/final_acceptance.py

# 分步验收
python scripts/check_discovery.py       # P0：registry search → GeoMCP geo.* → MCP 桥（需 3 服务在跑）
python scripts/run_recipe_e2e.py        # P1：Recipe 端到端 + GAAG 报告合约 + 生成报告卡
python scripts/harvest_stac.py          # P1：管线 1 STAC 采集（fixture 离线模式）
python scripts/check_skills_live.py     # P1：节点装载算子后 geo.execute 实测（自带线程内服务）
python scripts/check_model_invoke.py    # P2：invoke_model 成功/门禁拒绝/批作业/算力发现 5 项
python scripts/check_capability_node.py # 平台能力节点：注册视图/发现/直调/跨节点委托/算力闭环（单进程）
```

## 平台能力节点（注册 → 被发现 → 被调用）

SDGNode 就是一个 **GeoNexus Platform 能力节点**，`start_sdg_node.py` 一次启动完成三件事：

1. **注册（advertise）**：把全部 GeoCard + 8 个 GeoSkill 推送到平台 registry，
   条目 `node_url` = 本节点 GeoMCP 实时地址；`--refresh` 先注销旧条目再重宣（幂等重部署）。
   平台 `/nodes` 聚合视图即可见：`cards=41 skills=8` + 健康探测。
2. **自述算力**：开机构造 `sdg.compute.sdg-node.self-pool`（真实 CPU 核数/内存探测；
   GPU 只有显式声明 `SDGNODE_GPU=1xA100` 才上报——**不虚报**，否则门禁会错误放行 GPU 模型）。
   该卡以 `node_url=模型服务基址` 单独注册（SDK 语义：compute 条目的 node_url 即"模型将在哪里运行"），
   供 `resolve_compute_capabilities` / `invoke_model` 算力门禁发现。
3. **委托（set_registry）**：任何绑定平台的节点都能成为**联邦入口**——
   `geo.execute` 引用非本节点资产时，按平台 `node_url` **一跳转发**给 owner 执行、结果原路返回
   （`__geonode_delegate` 标记防环）。验收 C4/V3b：0 技能的 `region-b-gateway`/`region-c-entry`
   成功调用到 SDGNode 上的算子，即"被平台发现和调用"的实证。

## 跨机部署（让其他电脑上的平台发现并调用本节点）

演示态全绑 `127.0.0.1`，外部不可达。跨机只需三处改成**局域网可路由地址**（本机实测 `192.168.100.101`，验证 N1–N5 全过）：

```bash
# 1) 模型服务监听所有接口（算力卡申报的"模型运行地"必须与之一致）
python -m uvicorn services.model_provider:app --host 0.0.0.0 --port 8801

# 2) 能力节点：--host 0.0.0.0 监听 + --endpoint/--model-endpoint 宣告局域网地址
#    --registry 指向**平台机器**的 registry（不在本机时填 http://<平台IP>:8790）
python scripts/start_sdg_node.py --host 0.0.0.0 --port 8793 \
  --endpoint http://192.168.100.101:8793 \
  --model-endpoint http://192.168.100.101:8801 \
  --registry http://<平台机器IP>:8790 --api-key <平台写钥> --with-skills --refresh

# 3) Windows 防火墙放行入站（管理员 PowerShell）
netsh advfirewall firewall add rule name="SDGNode GeoMCP" dir=in action=allow protocol=TCP localport=8793
netsh advfirewall firewall add rule name="SDGNode Model" dir=in action=allow protocol=TCP localport=8801

# 平台机器验证（发现）：GET http://192.168.100.101:8793/health · 注册中心 /nodes 应出现
# 该 node_url（health_probe 开启时 healthy=true）；调用侧直接跑 verify_live_node.py --node http://192.168.100.101:8793
```

要点与边界：
- **宣告地址 = 别人路由到你的地址**：`--endpoint` 写 `127.0.0.1` 时平台条目即便在册，跨机委托/健康探测也会失败——启动器把监听、宣告、算力申报三个地址解耦，正是为此。NAT/云主机场景需宣告公网或映射后的地址。
- 委托是**一跳**：平台入口节点把请求转到 owner 的 `node_url`，owner 结果原路返回；`__geonode_delegate` 防环。
- **安全边界**：节点执行端点当前无鉴权（演示态）；跨机生产建议——registry 写钥必配（advertise 已带）、节点侧配 `forward_api_key` 与自身 apikey、公网场景置于 TLS 反代之后；受限数据卡的 visibility 治理（restricted/404 语义）在平台检索侧生效。
- 重启节点加 `--refresh` 即可把平台全部条目重宣到实时地址（幂等运维动作）。

## 设计原则（与 SDK 对齐）

1. **卡描述而不包含**：卡是门面，执行 DAG 在 Recipe；数据留在主权节点，计算下推（CAFE）。
2. **契约先行**：无契约（时空/列/输入输出）不可注册；越权请求得 2000 + reasons，而非模糊失败。
3. **口径钉死**：指标基准年/方法版本 `scope: fixed`；换口径=换指标定义，走 fork+重审。
4. **结论可溯源**：运行产物报告走 report 合约（run/recipe/params/data_snapshot + checksum）。
5. **可见性继承**：复合案例的有效可见性=min(内容组件)；受限数据引用即降级（404 语义）。
6. **加法式扩展**：SDG 绑定只走顶层 `geonexus:sdg` 扩展 + 本仓库 Profile Schema，不改 SDK。

