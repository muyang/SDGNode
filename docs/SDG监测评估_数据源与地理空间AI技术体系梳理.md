# SDG 监测与评估：数据源、地理空间技术与 AI 工具体系梳理

> 本文档系统梳理支撑联合国 2030 可持续发展议程（17 个 SDG 目标、169 项具体目标、全球指标框架共 251 项指标条目 / 231 项唯一指标）监测与评估所需的：
> ① 数据源；② 地理空间信息技术与 GIS 软件；③ 空间分析方法；④ AI 模型与机器学习工具；⑤ 国际倡议与平台；⑥ 指标级映射与技术路线建议。
> 编制时间：2026-07（含 2024–2025 年最新进展）。

---

## 目录

1. [总体框架](#1-总体框架)
2. [SDG 数据源体系](#2-sdg-数据源体系)
3. [17 个目标的数据源与方法映射](#3-17-个目标的数据源与方法映射)
4. [地理信息技术与 GIS 软件](#4-地理信息技术与-gis-软件)
5. [空间分析方法体系](#5-空间分析方法体系)
6. [AI 模型与机器学习方法](#6-ai-模型与机器学习方法)
7. [国际组织、倡议与重大计划](#7-国际组织倡议与重大计划)
8. [典型技术路线与选型建议](#8-典型技术路线与选型建议)
9. [参考资源与链接](#9-参考资源与链接)

---

## 1. 总体框架

SDG 监测评估的数据-技术体系可概括为一个"金字塔 + 双支柱"：

```
决策支持（SDG 进展报告、政策模拟、预警、可视化仪表盘）
        ▲
信息 / 知识（指标计算、专题制图、变化检测、评估模型、AI 推理）
        ▲
数据融合（时空配准、数据立方体、格点化、统计-空间分解）
        ▲
观测采集（卫星遥感 / 航空与无人机 / 地面传感网 / 调查统计 / 社会感知大数据）
```

- **支柱一：官方统计**（国家统计系统 + 国际组织数据库）——权威、可比，但空间粒度粗（国家级）、更新慢、部分指标缺数据。
- **支柱二：地理空间数据与地球大数据**——时空连续、可下钻到地方（SDG 本地化监测），是填补数据空缺、实现"地理空间化评估"的核心手段。UN-GGIM（联合国全球地理空间信息管理专家委员会）与地球观测组织（GEO）均明确：231 项唯一指标中约一半以上可借助地理空间信息直接或间接监测，环境类指标几乎全部依赖遥感。

---

## 2. SDG 数据源体系

### 2.1 官方统计与权威数据库

| 类别 | 主要数据源 | 说明 |
|---|---|---|
| SDG 官方指标 | **UN SDG Global Database**（unstats.un.org/sdgs） | 231 项唯一指标的全球/区域/国家序列，含元数据仓库 |
| 综合评估 | **SDSN SDG Index & Dashboards**、Our World in Data SDG Tracker、OECD SDG 测量框架、Eurostat SDG 监测报告 | 指数化、可视化 |
| 发展统计 | 世界银行 **WDI**、IMF WEO、UN Comtrade（贸易）、世界银行 PIP（贫困） | SDG 1/8/10/17 |
| 农业粮食 | **FAOSTAT**、FAO FRA（森林资源评估）、AQUASTAT（水资源）、FAO GeoNetwork / Hand-in-Hand 地理空间平台 | SDG 2/6/15 |
| 健康 | WHO GHO、IHME GBD（全球疾病负担）、UNAIDS、UNICEF 免疫数据 | SDG 3 |
| 教育 | UNESCO UIS、世界银行教育数据 | SDG 4 |
| 劳动 | ILOSTAT | SDG 8 |
| 城市人居 | UN-Habitat（贫民窟数据、城市数据库）、UN DESA 城市化展望 | SDG 11 |
| 环境 | UNEP（排放差距报告、GeoPortal）、UNFCCC（NDC 登记）、IPCC 数据 | SDG 12/13 |
| 灾害 | **EM-DAT**（CRED）、DesInventar、GDACS（实时预警）、Think Hazard（风险画像） | SDG 1/11/13 |
| 冲突治理 | **ACLED**（地理编码冲突事件）、UCDP GED、世界银行 B-READY/治理指标 | SDG 16 |

**入户调查与普查**（提供子国家级数据的关键）：
- **DHS**（人口与健康调查，含 GIS 地理编码聚类数据）、**MICS**（UNICEF 多指标类集调查）、世界银行 **LSMS / LSMS-ISA**（含地理编码）、各国人口普查、农业普查、土地变更调查、经济普查。

### 2.2 卫星遥感与对地观测

**（1）按传感器类型**

| 类型 | 主要卫星/星座 | 典型 SDG 用途 |
|---|---|---|
| 中分辨率光学 | **Landsat 8/9**（30 m，1972 年以来连续档案；Landsat Next 规划中）、**Sentinel-2 A/B/C**（10 m）、MODIS/VIIRS（250–750 m）、HLS（Landsat+Sentinel-2 协调产品） | 土地覆盖、森林、农业、水体、城市扩张 |
| 高分辨率光学 | Planet（Dove 3 m 每日/SkySat 0.5 m）、Maxar、Airbus Pléiades/SPOT、吉林一号、高分二号、SuperView | 贫民窟识别、建筑物提取、耕地地块、公共空间 |
| SAR 雷达 | **Sentinel-1 A/B/C**（免费 10 m C 波段）、NISAR（2025 年发射，L/S 双频）、ALOS-2/4、TerraSAR-X、Capella、ICEYE、高分三号 | 全天候：洪涝、地表形变（InSAR）、水稻制图、山体滑坡 |
| 大气成分 | **Sentinel-5P TROPOMI**（NO₂/SO₂/CO/CH₄/O₃）、OCO-2/3、GOSAT、TEMPO、EMIT、高分五号；CO2M（哥白尼人为 CO₂，规划中） | SDG 13/11.6：排放与空气质量 |
| 激光雷达 | **GEDI**（森林结构/生物量）、ICESat-2（高程/海冰/树冠） | 森林碳汇、山地、海岸 |
| 高光谱 | EnMAP、PRISMA、DESIS、EMIT、珠海一号 | 水质、土壤、矿物、精细农业 |
| 热红外 | Landsat TIRS、ASTER、**SDGSAT-1 热红外载荷** | 地表温度、城市热岛、能源利用 |
| 夜光 | DMSP/OLS（1992–2013）、**VIIRS DNB**（EOG）、珞珈一号、**SDGSAT-1 微光成像仪（10 m 彩色夜光）** | 经济活动、电力可及性、贫困代理、城市化 |
| 气象 | 风云系列、Himawari、GOES、Terra/Aqua | 降水、温度、台风、干旱 |
| 林相/生物量 | ESA **Biomass**（2025 年发射，P 波段） | 森林生物量与碳储量 |

**（2）全球专题数据产品（"即取即用"）**

| 主题 | 代表产品 |
|---|---|
| 土地覆盖 | **ESA WorldCover 10 m**（2020/2021/2024 版）、ESRI Land Cover 10 m、Google **Dynamic World**（近实时）、ESA CCI LC、GlobeLand30、中国 LUCC 遥感监测数据集 |
| 人口格点 | **WorldPop**、GPW/GHS-POP（JRC）、LandScan（ORNL）、Meta 高分辨率人口图、中国 1 km 格点人口 |
| 建筑/城市 | **GHSL**（GHS-BUILT-S/POP/SMOD 城市度分级，SDG 11.3.1 官方推荐）、WSF 世界居住区足迹（DLR）、Google **Open Buildings**、Microsoft Building Footprints |
| 森林 | Hansen **Global Forest Change**（年损失/增益）、Global Forest Watch + GLAD/RADD 近实时毁林警报、JAXA 森林图 |
| 水体 | JRC **Global Surface Water**（1984– 变化，SDG 6.6.1 官方数据源）、Global River Database、水文站网 |
| 农田 | GFSAD 全球灌溉图、**MapSPAM/SPAM** 作物分布、各国耕地遥感产品 |
| 地形 | SRTM 30 m、Copernicus DEM、ALOS AW3D30 |
| 土壤 | **SoilGrids 250 m**、HWSD、国家土壤信息网格 |
| 生物多样性 | **GBIF**（物种出现记录）、OBIS（海洋）、**IUCN 红色名录空间数据**、eBird、iNaturalist、BirdLife |
| 保护区 | **WDPA**（UNEP-WCMC 世界保护区数据库，SDG 14.5.1/15.1.2 官方数据源）、Ramsar、Key Biodiversity Areas |
| 珊瑚/红树林 | Allen Coral Atlas、NOAA Coral Reef Watch（白化警报）、**Global Mangrove Watch** |
| 渔业 | **Global Fishing Watch**（AIS/VMS 船舶活动，IUU 捕捞监测） |
| 能源设施 | WRI **Global Power Plant Database**、Open Infra Map（电网）、Global Electrification Platform |
| 道路/交通 | OSM 路网、gROADS、GTFS 公交时刻表、Ookla Speedtest（宽带覆盖开放数据） |
| 大气质量 | **ACAG/V4 全球 PM2.5 格点**（卫星+模型融合）、OpenAQ/PurpleAir（监测站）、NASA POWER |
| 气候 | ERA5 再分析、CMIP6/ISIMIP（情景）、WorldClim、TerraClimate、CHIRPS 降水 |
| 碳排放 | **EDGAR**、Global Carbon Atlas、Climate TRACE |
| 灾害风险 | 洪水（Google Flood Hub/Flood Forecasting）、野火（NASA FIRMS）、滑坡（NASA LHASA）、干旱（SPI/SPEI、USGS FEWS） |

### 2.3 地理空间大数据（社会感知 / VGI / 物联网）

| 类别 | 数据源 | SDG 应用 |
|---|---|---|
| 志愿地理信息 | **OpenStreetMap**、Geo-Wiki、Mapillary/KartaView 街景 | 基础设施完备度、道路可及性、众包制图 |
| 移动信令 | 运营商 CDR、Google/Apple Mobility、GPS 轨迹（滴滴 GAIA、Grab） | 人口流动、通勤（SDG 11.2）、灾时疏散、经济活力 |
| POI/位置服务 | 高德/百度/Google Places、大众点评、美团 | 商业活力、公共服务设施密度、SDG 11.7 |
| 社交媒体 | 微博/X/Flickr（带地理标签） | 舆情、灾害应急、公众感知、事件探测 |
| 夜间灯光 | VIIRS/SDGSAT-1（见上） | 经济活动代理、贫困与不平等（SDG 1/10） |
| 物联网传感 | 空气/水质自动监测站、土壤墒情、智能电表、交通卡口 | SDG 3.9/6.3/7.3 实时监测 |
| 公民科学 | iNaturalist、eBird、GLOBE、Zooniverse、MapSwipe | 生物多样性（SDG 15）、灾害制图 |
| 电商平台 | 淘宝村、物流数据 | 数字包容、乡村发展（SDG 9/10） |

### 2.4 地面观测网络

- 气象/水文/生态台站：WMO GOS、各国气象水文局、**CERN**（中国生态系统研究网络）、FluxNet（通量塔）、BGC-Argo（海洋生物地球化学浮标）、GLOBUS 土壤网。
- 统计台账：环境统计年报、水资源公报、海洋生态环境公报、土地利用变更调查、林业普查。

### 2.5 重大专用平台与计划（SDG 定制）

| 平台 | 主办方 | 说明 |
|---|---|---|
| **SDGSAT-1 可持续发展科学卫星一号** | 中科院空天院 / CBAS | 2021-11 发射，全球首颗 SDG 专用科学卫星：热红外 + 微光（10 m 彩色夜光）+ 多光谱三载荷协同，刻画"人类活动痕迹"；开放科学数据计划（sdgsat.ac.cn） |
| **地球大数据支撑可持续发展目标报告**（年度） | CBAS / 可持续发展大数据国际研究中心 | 已评估 90+ 项指标（含中国全部环境类指标），是大数据填补 SDG 数据空缺的旗舰成果 |
| NASA **SDG Data Hub** / Earthdata | NASA | 面向 SDG 的地球观测数据产品与工具目录 |
| **GEO SDG 社区 / GEO Knowledge Hub** | GEO（地球观测组织） | 地球观测支撑 SDG 的案例、数据与最佳实践库 |
| FAO **Hand-in-Hand 地理空间平台** | FAO | 农业、粮食、土地、水、SDG 指标的地理空间分析门户 |
| UN-GGIM **SDG 地理空间最佳实践库** | UN-GGIM | 各国地理空间支撑 SDG 的 Good Practices |
| Copernicus（哥白尼计划） | EU/ESA | Sentinel 系列 + 气候、大气、海洋、应急等服务；**Copernicus Browser** 数据浏览 |

---

## 3. 17 个目标的数据源与方法映射

| SDG | 关键（可地理空间化）指标 | 核心数据源 | 关键技术/方法 |
|---|---|---|---|
| **1 无贫穷** | 1.1.1/1.2.1 贫困率；多维贫困 | 官方统计、DHS/MICS/LSMS、夜光、高分影像 | AI 贫困制图（夜光+影像特征→ML 估计消费/资产，如斯坦福 Atlas of Economic Development）；人口格点化（dasymetric）；小区域估计 |
| **2 零饥饿** | 2.3.1 农业生产力；2.4.1 可持续农业 | FAOSTAT、GFSAD/SPAM、Sentinel-1/2 时序、气象 | 作物类型制图（SAR+光学时序 DL）、产量估算（CNN/LSTM+ERA5）、物候监测、CropWatch/FEWS NET 预警 |
| **3 健康福祉** | 3.9.1 空气污染死亡；3.3 传染病；3.6 交通事故；3.8 服务覆盖 | ACAG PM2.5、Sentinel-5P、GBD、ACLED、OSM 路网、卫生设施位置 | PM2.5 反演（AOD+ML）、疾病风险制图（MAP）、**AccessMod / 2SFCA 医疗可及性**、道路暴露分析 |
| **4 优质教育** | 学校可达性、入学率空间差异 | UIS 统计、OSM 学校 POI、人口格点 | 网络分析、就学服务区建模、教育资源公平性空间统计 |
| **5 性别平等** | 各类调查性别指标 | DHS/MICS、时间利用调查、安全事件数据 | 空间分解、女性设施可及性（安全照明/公厕 POI）、文本挖掘舆情 |
| **6 清洁饮水** | 6.3.2 水质达标；6.4.2 用水压力；**6.6.1 水生态系统面积** | 地面监测站、AquaSat、Sentinel-2/3、**JRC Global Surface Water**、GRACE、AQUASTAT | 水体提取与长时序变化检测、水质参数反演（Chl-a/浊度/CDOM）、蒸散发与地下水储量遥感 |
| **7 经济适用能源** | 7.1.1 电力可及；7.2.1 可再生占比 | 夜光、Global Electrification Platform、GPPD、Global Solar/Wind Atlas、OpenInfraMap | 电网-聚落匹配、太阳能/风能资源评估、屋顶光伏潜力（3D 城市模型+DL） |
| **8 体面工作** | 经济活动空间分布 | ILOSTAT、夜光、POI、手机信令 | 夜光-GDP/就业回归与 ML 估算、经济活力指数 |
| **9 产业创新基建** | 道路通达性、宽带覆盖 | OSM/gROADS、Ookla、高分影像、工业用地产品 | 道路提取（DL：Ramp/DeepMind 道路）、乡村道路通达性（rural accessibility）、基建变化检测 |
| **10 减少不平等** | 子国家发展差异 | 统计+人口格点、夜光、GHSL | 空间不平等度量（LISA/基尼格点化）、城乡梯度分析 |
| **11 可持续城市** | **11.3.1 土地消耗率/人口增长率**；11.2.1 公交可及；11.5 灾害损失；11.6.2 PM2.5/垃圾；**11.7.1 公共开放空间**；11.1.1 贫民窟 | GHSL（官方推荐）、WorldCover、GTFS、GDACS、ACAG、高分影像 | 建成区提取与扩张分析、GTFS 等时圈公交覆盖、洪涝/滑坡制图、城市绿地提取+15 分钟可达性、非正规居住区 DL 分类、城市热岛（LST） |
| **12 负责任消费生产** | 12.2.1 物质足迹；废物管理 | IRP 物质流数据库、垃圾填埋场遥感、夜光 | 物质流分析、非法倾倒点识别、循环经济空间规划 |
| **13 气候行动** | 13.1.1 灾害；温室气体核算 | OCO-2/3、GOSAT、Sentinel-5P、EDGAR、CMIP6/ISIMIP、EM-DAT | 碳源汇反演、统计降尺度（ML）、气候暴露与脆弱性评估、灾害风险建模 |
| **14 水下生物** | 14.1.1 沿海富营养化；14.3.1 海洋酸化；14.4.1 IUU 捕捞；14.5.1 MPA 覆盖 | Sentinel-3 OC-CCI、BGC-Argo/GLODAP、**Global Fishing Watch AIS**、WDPA 海洋区、珊瑚/红树林产品 | 叶绿华与富营养化指数、白化警报、船舶行为异常检测、MPA 有效性评估 |
| **15 陆地生物** | **15.1.1 森林面积**；15.2.1 可持续森林；**15.3.1 土地退化（LDN）**；15.4.2 山地绿覆盖；15.5.1 红色名录指数 | Hansen GFC、ESA CCI、FRA、UNCCD LDN（土地覆盖+生产力+SOC 三指标）、MRV 山地平台、IUCN | 森林变化检测（LandTrendr/BFAST/CCDC）、LDN Toolbox、物种分布模型（MaxEnt/BIOMOD）、连通性（Circuitscape）、保护规划（Marxan/Zonation）、声学监测 AI（BirdNET） |
| **16 和平正义** | 冲突事件、机构可及性 | **ACLED**、UCDP GED、夜光 | 冲突热点时空分析（Gi*、扫描统计）、夜光扰动检测、司法设施可及性 |
| **17 伙伴关系** | 数据可及性、发展合作 | SDMX 统计交换、ODIN 数据开放指数、各国 SDI | 数据基础设施（SDI）评估、开放数据与互操作（STAC/OGC API）、数据缺口填补（地球大数据） |

---

## 4. 地理信息技术与 GIS 软件

### 4.1 数据获取技术

- **卫星遥感**（光学/SAR/高光谱/热红外/夜光/激光测高，见 §2.2）
- **航空遥感与无人机**：正射影像、倾斜摄影三维建模、机载 LiDAR（森林结构、电力线）、多光谱/高光谱无人机（精准农业、水体）
- **GNSS 测量**：控制测量、RTK 无人机航测、手持采集
- **InSAR/PS-InSAR/SBAS**：地表沉降、滑坡、冰川、地震形变（Sentinel-1 免费数据即可）
- **地面传感网/IoT**：环境与基础设施实时监测
- **移动测量与街景**：道路资产普查、店招/绿化识别（街景 + 深度学习）
- **众包制图**：HOT（人道主义开放地图）、MapSwipe

### 4.2 GIS 软件与平台

**（1）桌面 GIS / 遥感软件**

| 软件 | 性质 | 定位 |
|---|---|---|
| **ArcGIS Pro**（Esri） | 商业 | 全功能旗舰：Spatial Analyst、GeoAI（像素分类/目标检测/SAM 集成）、Insights、Urban、CityEngine、Mission Hub |
| **QGIS** | 开源 | 事实标准桌面 GIS；插件生态（Semi-Automatic Classification、TimeSerial、Deepness 深度学习插件、QGIS 处理框架） |
| GRASS GIS | 开源 | 栅格/地形/水文/景观分析，700+ 模块 |
| SAGA GIS | 开源 | 地形与地统计 |
| **ENVI / ENVI Met** | 商业 | 高光谱与多光谱定量遥感、城市微气候 |
| ERDAS Imagine（Hexagon） | 商业 | 摄影测量与遥感生产 |
| **eCognition**（Trimble） | 商业 | 面向对象的影像分析（OBIA）标准 |
| ESA **SNAP** / PolSARpro / MSTools | 免费 | SAR 处理链、极化与时序 |
| Orfeo ToolBox (OTB) | 开源 | 高性能遥感处理库（法国 CNES） |
| **SuperMap / MapGIS** | 国产 | 国内平台级 GIS（跨平台、二三维、分布式） |

**（2）WebGIS / 在线制图与发布**

- 服务端：**GeoServer**、MapServer、ArcGIS Enterprise/Online、GeoNode、52°North、MapStore
- 前端库：**Leaflet**、**OpenLayers**、**MapLibre GL JS**、Mapbox GL JS、**deck.gl**（大数据可视化）、**CesiumJS**（3D 地球/3D Tiles）、TerriaJS、Kepler.gl（时空轨迹）
- 门户/仪表盘：ArcGIS Hub/Dashboards、CKAN（数据门户）、Observable/Plotly Dash/Streamlit（自定义 SDG 仪表盘）

**（3）云计算与数据立方体平台**

| 平台 | 特点 |
|---|---|
| **Google Earth Engine (GEE)** | PB 级影像档案 + Python/JS API；SDG 评估首选（GSW、Dynamic World、AlphaEarth 嵌入均原生托管） |
| **Microsoft Planetary Computer + Pangeo** | STAC 目录、JupyterHub、开源科学栈（xarray/zarr/dask） |
| AWS（SageMaker Geospatial、Open Data、Earth on AWS） | 云原生处理与托管 |
| Sentinel Hub / EO Browser | Sentinel 系列快速浏览与 OGC/WMS 服务 |
| UP42、SkyFi、Descartes Labs、Pico | 商业遥感任务与处理市场 |
| **PIE-Engine**、阿里云 AI·Earth、华为云 EI Earth | 国内类 GEE 平台 |
| Open Data Cube、xcube（EOX） | 自建数据立方体 |

**（4）时空数据库与云原生格式**

- **PostGIS**（PostgreSQL 空间扩展，事实标准）、SpatiaLite、Oracle Spatial
- 分布式时空：**Apache Sedona**（原 GeoSpark，Spark/Flink 上的空间 SQL）、GeoMesa、ClickHouse/Elasticsearch geo
- 轻量分析：DuckDB-spatial
- 云原生格式：**COG**（云优化 GeoTIFF）、**STAC**（时空资产目录标准）、**Zarr**、**GeoParquet**、FlatGeobuf、PMTiles
- 网格索引：Uber **H3**、S2、geohash

**（5）开发库生态**

- Python：**GDAL/OGR**、**rasterio**、**geopandas**、shapely、pyproj、xarray + rioxarray + rasterstats、earthengine-api、folium/kepler.gl
- 空间统计：**PySAL**（esda / mgwr / spreg / pointpats / tobler）、scikit-learn、statsmodels
- 深度学习：**torchgeo**、**segment-geospatial (samgeo)**、raster-vision、deepforest（树冠检测）、IBM **TerraTorch**（基础模型微调）
- R：**sf / terra / raster**、spdep、gstat、biomod2、PresenceAbsence、INLA
- 水文地形：TauDEM、WhiteboxTools、pysheds、HEC-RAS、SWAT

### 4.3 标准、基础设施与治理

- **OGC 标准**：WMS/WFS/WCS/WMTS、**OGC API – Features/Tiles/Coverages**、STAC、3D Tiles、CityGML 3.0、GeoPackage、GeoSPARQL
- **ISO 19100 系列**（地理信息标准）、SDMX（统计交换）
- **SDI 空间数据基础设施**：INSPIRE（欧盟）、各国地理信息公共服务平台（如中国"天地图"）、元数据（ISO 19115）
- **UN-GGIM 综合地理空间信息框架（IGIF）**：8 条战略路径（治理、法律、政策、标准、能力、创新、伙伴关系等），是国家 SDI 支撑 SDG 的顶层设计工具
- **FAIR 数据原则**（可发现、可访问、可互操作、可重用）与数据主权、隐私（CDR/移动数据的匿名化、差分隐私）

---

## 5. 空间分析方法体系

### 5.1 遥感影像处理与信息提取

- 预处理：辐射定标、大气校正（Sen2Cor/6S/ACOLITE）、几何校正、镶嵌、去云（DSen2、SpA-GAN）
- 时序分析：**LandTrendr、BFAST/BFAST2、CCDC**、谐波回归（phenology）、合成（月度/年度中值）、突变检测
- 光谱指数：NDVI/EVI/SAVI（植被）、NDWI/MNDWI（水体）、NDBI（建成区）、NDMI（湿度）、LST（地表温度）、AOD（气溶胶）、SAVI/BSI（裸土）
- 变化检测：直接分类比较、变化向量分析、CVA、深度学习变化检测（Siamese CNN、BIT、ChangeFormer）

### 5.2 分类与分割

- 传统 ML：随机森林、SVM、XGBoost、kNN（GEE 上大规模应用的主力）
- 深度学习：U-Net 系、DeepLabV3+、HRNet、**SegFormer、Mask2Former、Swin-UNet**；时序：TempCNN、ConvLSTM、3D-CNN
- 面向对象（OBIA）：eCognition 多尺度分割 + 特征工程
- 通用分割：**SAM/SAM2 + GeoSAM/samgeo**（提示式分割任意地物）、Grounded-SAM（文本提示）
- 目标检测：YOLOv8/11、RT-DETR——船舶、车辆、建筑物、风力机、鲸类

### 5.3 空间统计与地统计

- 空间自相关：**Global/Local Moran's I、LISA、Getis-Ord Gi\***、Kulldorff 时空扫描统计（SaTScan）——识别 SDG 指标的热点/冷点与不平等格局
- 地统计：变异函数、**克里金**（普通/泛/协同）、序贯指示模拟——插值环境变量
- 空间回归：**GWR/MGWR**（地理加权回归）、SAR/SEM/SLX/**SDM**（空间计量）——分析 SDG 指标的空间溢出与驱动因素
- 贝叶斯层次模型：R-INLA、CAR/BYM（疾病制图）、Stan/PyMC——小区域估计与不确定性量化
- 面积插值与格点化：**dasymetric mapping**（用土地覆盖约束把行政统计分解到格点，SDG"地理空间化"的核心手段）、pycnophylactic 插值；注意 MAUP（可变面积单元问题）

### 5.4 可达性与网络分析

- 网络分析：服务区、OD 成本矩阵、最短路（**OSRM、Valhalla、OpenTripPlanner、pgRouting**）
- 等时圈分析：多模式出行 15 分钟城市、SDG 11.7.1 公共空间可达
- **两步移动搜索法（2SFCA）及改进**：医疗/教育/绿地供需匹配
- **AccessMod**（WHO）：地形+路网+土地覆盖的步行/车行医疗可及性建模（SDG 3.8）
- 公交可及性：GTFS + GTFS-Builder（SDG 11.2.1 官方方法）、重力模型
- 街巷空间：Space Syntax（空间句法）、步行适宜性指数

### 5.5 土地利用变化与模拟

- 转移矩阵、景观格局指数（**FRAGSTATS**、pylandstats）
- 元胞自动机模型：**FLUS、PLUS**、CA-Markov、SLEUTH、CLUE-S、Land Change Modeler（Idrisi/TerrSet）
- 情景模拟：与 SSP/RCP 情景耦合，评估 SDG 路径（如城市扩张 vs 耕地保护权衡）

### 5.6 生态系统服务与自然资本

- **InVEST**（碳储量、产水量、泥沙保持、生境质量、授粉、海岸带防护——直接服务 SDG 6/13/14/15）
- ARIES for SEEA、LUCI、SolVES（文化服务）、自然资本核算（SEEA-EA 框架）
- 生态红线/保护优先区：**Zonation、Marxan**、保护地有效性评估

### 5.7 水文、灾害与气候

- 水文模型：SWAT、HEC-HMS/RAS、VIC、HAND 淹没模型
- 洪涝：SAR 洪水提取（Sentinel-1 阈值/DL）、Google Flood Hub 预报、淹没-暴露-损失链（与人口/资产格点叠加算 SDG 11.5/13.1）
- 滑坡：易发性制图（ML：RF/XGBoost/DL）+ InSAR 形变早期识别（NASA LHASA）
- 干旱：SPI/SPEI、遥感植被状态指数 VCI/TCI、FEWS NET
- 野火：FIRMS 火点、烧伤迹地（dNBR）、火险预报
- 气候降尺度：统计/ML 降尺度（DeepSD）、ISIMIP 多模式集合、气候风险指数

### 5.8 大气与环境健康

- PM2.5/NO₂ 估算：卫星 AOD/TROPOMI + 地面站 + ML（RF/GBDT/CNN/时空图网络）→ SDG 3.9.1/11.6.2
- 化学传输模型：WRF-Chem、GEOS-Chem、CMAQ（模拟与归因）
- 水质反演：Sentinel-2/3 + ML（Chl-a、浊度、透明度）→ SDG 6.3.2/14.1
- 碳监测：柱浓度卫星（OCO/GOSAT）+ 自底向上清单交叉验证

### 5.9 海洋与海岸带

- SST/叶绿华/初级生产力（OC-CCI）、珊瑚白化热应力（DHW）、红树林变化（GMW）
- 船舶监测：AIS 大数据时空分析、非法捕捞识别（Global Fishing Watch 模型）
- 海岸线变迁、海平面上升暴露分析

### 5.10 城市三维与数字孪生

- 三维城市模型：CityGML/3D Tiles、CityEngine 程序化建模、BIM+GIS
- 城市气候：UMEP（SUEWS/能量平衡）、通风廊道、热岛缓解情景
- 太阳能潜力：屋顶提取（DL）+ 辐照模拟
- **数字孪生地球**：EU **Destination Earth**、ESA Digital Twin Earth、NVIDIA **Earth-2**（AI 天气/气候模拟加速）

### 5.11 社会经济地理大数据方法

- 夜光经济计量：夜光-GDP/贫困/就业回归与校准（跨传感器一致性处理）
- 手机信令/轨迹：OD 流、居住地-工作地推断、职住平衡、灾时人口流动
- POI 混合用途：功能混合度、生活圈评估（15 分钟生活圈）
- 文本地理挖掘：地名解析（geoparsing）、事件地理编码（ACLED 模式）、SDG 相关性文本分类（OSDG）

---

## 6. AI 模型与机器学习方法

### 6.1 经典机器学习（表格与栅格特征）

- **随机森林 / XGBoost / LightGBM / CatBoost**：SDG 指标预测、土地利用分类、贫困估计、灾害易发性——仍是地球大数据 SDG 评估的主力（如 AlphaEarth 嵌入 + GBDT 即可产出全球制图）
- SVM、kNN、GLM/GAM（可解释基线）
- 聚类：K-means、DBSCAN/HDBSCAN（城市类型分区、贫民窟聚落形态）
- 降维/嵌入：PCA、UMAP、t-SNE

### 6.2 深度学习任务模型（判别式）

| 任务 | 代表模型 | SDG 场景 |
|---|---|---|
| 语义分割 | U-Net/DeepLabV3+/HRNet/SegFormer/Mask2Former | 土地覆盖、水体、建成区、绿地 |
| 时序分类 | TempCNN、ConvLSTM、3D-CNN、Transformer-TS | 作物类型、物候、变化检测 |
| 目标检测 | YOLO 系、Faster R-CNN、DETR/RT-DETR | 建筑物、船舶、车辆、风机、油罐 |
| 实例/全景分割 | Mask R-CNN、Mask2Former | 建筑足迹（Google/Microsoft 全球建筑图即此类管线） |
| 变化检测 | Siamese CNN、BIT、ChangeFormer、SNUNet | 城市扩张、毁林、灾后评估 |
| 超分/融合 | ESRGAN、SRCNN、DSen2（SAR 去云）、全色锐化 | 数据增强、低成本高分产品 |
| 图神经网络 | GCN/GraphSAGE/STGCN | 城市系统、交通流、基础设施网络韧性 |
| 生成模型 | GAN/扩散模型 | 云去除、SAR-光学转换、情景模拟数据增广 |
| 序列/预测 | LSTM、TFT、N-BEATS | 产量、水位、能源负荷、灾害损失预测 |

### 6.3 遥感/地球观测基础模型（Foundation Models，2023–2025 重点）

**通用多光谱/多时序基础模型：**

| 模型 | 机构/时间 | 特点 |
|---|---|---|
| **Prithvi-EO-2.0**（300M/600M） | NASA + IBM + Jülich，2024-12 | ViT-MAE，预训练于 420 万 HLS 30 m 时序切片；配 TerraTorch 微调工具链；洪水/火烧迹地/作物等下游任务 |
| **Clay v1.5** | Clay Foundation，Apache 2.0 | 多传感器 MAE（S1/S2/L8-9/NAIP/MODIS 等 7000 万切片），嵌入可用于相似度检索与分类 |
| **AlphaEarth Foundations** | Google DeepMind，2025-07 | 不发布权重而发布**预计算嵌入场**：GEE 原生 10 m 年度 64 维嵌入（2017– ），融合光学/SAR/热/高程/气候/文本；用 RF/GBDT 即可做稀疏标签全球制图 |
| **TerraMind** | IBM + ESA，2025（ICCV） | "任意模态"生成式基础模型（S1/S2/LULC/DEM/ captions 等），ESA 官方合作 |
| **RingMo / RingMo-Aerial / RingMo-Agent** | 中科院空天院 | 国产遥感基础模型系列，Agent 版支持多平台多模态推理 |
| **SkySense / SkySense++ / SkySense V2 / SkySense-O** | 武汉大学等（CVPR24 / NMI25 / ICCV25） | 多模态通用解译；V2 统一多模态；O 版面向开放世界 |
| SatMAE / ScaleMAE / DOFA / CROMA / Satlas | 学界/Allen AI | MAE 与多传感器波长编码路线 |
| **Presto** | Harvest AI | 像元级农业时序基础模型（产量/物候） |
| SatCLIP / Galileo | Microsoft | 位置编码基础模型（用地理嵌入替代手工特征） |
| HyperSIGMA / SpectralGPT / HyperFree | 武大等 | 高光谱基础模型 |
| SARATR-X / SUMMIT / WV-Net | 学界 | SAR 目标识别/时序基础模型 |
| TiMo / RoMA / RingMamba | 2025 | Mamba（状态空间模型）路线的遥感时序基础模型 |
| **Panopticon / AnySat / Copernicus-FM** | 2025 | "任意传感器"统一模型（跨分辨率/跨尺度/跨模态） |

**使用模式：**
1. **微调模式**：基础模型 + LoRA/adapter + 少量标注 → 下游分割/检测（TerraTorch、torchgeo、HuggingFace `ibm-nasa-geospatial`）；
2. **嵌入模式**：提取 patch token / 预计算嵌入 → 喂给 RF/XGBoost → 快速制图（AlphaEarth 为典型，免 GPU 推理）；
3. **零样本/检索模式**：CLIP 类模型文本-影像检索、相似场景挖掘。
4. 基准提示：**GEO-Bench-2**（2025）表明 EO 专用基础模型优于自然图像预训练模型，但**没有单一模型全面领先**——按传感器/分辨率/任务选型。

**通用视觉基础模型的地理化应用：** SAM/SAM2（→ samgeo/GeoSAM/RemoteSAM）、DINOv2 特征 + 地理嵌入。

### 6.4 视觉-语言模型（VLM）与 LLM

**遥感 VLM / MLLM（影像问答、描述、指代分割、推理）：**
- SkyEyeGPT、RSGPT、LHRS-Bot(-Nova)、GeoChat、EarthGPT-X、TEOChat（时序对地观测对话）、VHM、EarthDial、GeoPixel（像素级指代）、LISAt（语言指令分割）、Geo-R1 / RSThinker（强化学习/思维链推理）、UrbanLLaVA（城市多模态）

**通用 LLM 在 SDG 监测中的用途：**
- **SDG 文本分类**：**OSDG / OSDG 2.0**（多语言开源工具，按 SDG 分类论文/专利/文本）、Elsevier SDG 映射、大学 SDG 报告自动标注
- 指标与事件抽取：从国家自愿国别评估报告（VNR）、统计年鉴、新闻中抽取结构化指标
- **SDG 知识图谱**：指标-数据-政策-文献关联（Wikidata SDG 本体、SDG KG），支持因果链与协同/权衡分析
- RAG 政策问答与合规审查（如 ESG/SDG 对齐评估）
- **LLM Agent 驱动 GIS 工作流**：自然语言 → SQL(PostGIS)/PyQGIS/GEE 代码自动生成；MapGPT、ArcGIS Assistant / GeoAI 代理、各类"Text-to-GIS"研究
- 多模态大模型（GPT-4V/Gemini）辅助地图审读、图表理解与报告生成

### 6.5 AI for SDG 典型应用（按主题）

| 主题 | 代表工作/产品 | 相关 SDG |
|---|---|---|
| 贫困与经济制图 | Jean et al. 2016 (Science) 迁移学习贫困估计；Yeh et al. 2020 (Nat. Commun.)；斯坦福 **Atlas of Economic Development**；世界银行贫困地理图谱 | 1, 2, 10 |
| 全球建筑/居住区 | Microsoft Global ML Building Footprints、Google Open Buildings、GHSL/WSF | 9, 11 |
| 全球道路 | Google/DeepMind OSM 道路提取（非洲等）、Ramp | 9, 11.2 |
| 非正规居住区（贫民窟） | 高分影像 + DL 形态学分类（联合国人居署合作研究） | 11.1 |
| 粮食安全 | CropWatch、FEWS NET、Presto/FARM 产量模型、粮价预测 | 2 |
| 空气质量 | ACAG 卫星 PM2.5、城市级 ML 预报（如伦敦/北京）、Microsoft AI for Good Air Quality | 3.9, 11.6 |
| 疾病风险 | Malaria Atlas Project、登革热气候适宜性、疫苗覆盖 ML 估计 | 3 |
| 森林与碳 | GFW/GLAD/RADD 警报、DLR 生物量（Biomass 卫星+AI）、毁林驱动因素归因 | 13, 15 |
| 土地退化 LDN | UNCCD 三指标 + 遥感生产力分解 | 15.3 |
| 水 | 洪水制图（Clay/Prithvi 下游洪水基准）、径流预报（LSTM）、水质 ML 反演 | 6, 11.5, 13 |
| 生物多样性 | eBird+iNaturalist + 物种分布 ML、BioSound/BirdNET 声学、相机陷阱 AI（Wildlife Insights、MegaDetector） | 14, 15 |
| 灾害预警 | Google Flood Forecasting、NASA LHASA 滑坡、野火 FireCAST | 11, 13 |
| 能源 | 屋顶光伏潜力 DL、风机/油罐检测、电网规划优化 | 7, 13 |
| 城市热与气候适应 | LST + 3D 形态 + ML 情景模拟 | 11, 13 |

### 6.6 AI 工程化、可信与治理

- **训练/微调框架**：torchgeo、TerraTorch、segment-geospatial、raster-vision、HuggingFace 🤗（`ibm-nasa-geospatial`、ESA 模型库）、PyTorch Lightning
- **MLOps 与可复现**：MLflow、Kubeflow、DVC；数据侧用 STAC + COG/Zarr + 数据立方体保证可复现的样本集构建；模型卡（Datasheets/Model Cards）
- **不确定性量化与可解释性**：贝叶斯 NN、深度集成、**conformal prediction**；SHAP、Integrated Gradients、Grad-CAM——SDG 官方统计场景对可解释性要求高
- **偏差与伦理**：训练样本地理偏差（全球南方数据稀疏）、夜光对贫困估计的系统性偏差、移动/社媒数据隐私（差分隐私、聚合最低人数门槛）、AI 结果的验证与地面真值网络
- **边缘/在轨 AI**：ESA Φ-sat-1/2（星上推理）、Wildfire 卫星边缘检测——降低下行带宽、实现近实时监测
- **国际治理**：UN "AI for Good"（ITU 主办峰会）、UNESCO AI 伦理建议、UN SG "AI 惠益全人类"顾问委员会报告、GEO AI 地球观测原则

---

## 7. 国际组织、倡议与重大计划

| 组织/倡议 | 角色 |
|---|---|
| **UN-GGIM**（联合国全球地理空间信息管理专家委员会） | 全球地理空间治理顶层设计；**IGIF** 综合框架；地理空间支撑 SDG 工作组与最佳实践库；与 UNSD 联合推动"指标地理空间化" |
| **UNSD**（联合国统计司） | SDG 全球指标数据库与元数据；SDG 报告 |
| **GEO**（地球观测组织） | GEOSS/GEO Knowledge Hub、SDG 社区实践、CEOS 协作 |
| **CEOS**（对地观测卫星委员会） | 各航天机构 SDG 数据产品协同（WGissD、SDG 任务队） |
| **CBAS / 可持续发展大数据国际研究中心**（北京） | **SDGSAT-1 卫星**、《地球大数据支撑可持续发展目标报告》、CASEarth |
| **ISDE**（国际数字地球学会） | Digital Earth 科学计划、数字地球节点 |
| **NASA** | Earthdata / SDG Data Hub、DEVELOP 计划、HLS/GEDI/ICESat-2/NISAR、POWER |
| **ESA / 欧盟** | Copernicus（Sentinel + 服务）、WorldCover、Φ-lab AI、Destination Earth 数字孪生 |
| **世界银行** | WDI、LSMS、Geospatial 团队、贫困地理图谱、GDP 夜光研究 |
| **FAO** | Hand-in-Hand 平台、AQUASTAT、FRA、WaPOR（水生产力） |
| **UNEP / UN-Habitat / UNDP** | 环境数据门户、城市监测（City Prosperity Index）、Data Futures Platform |
| **SDSN** | SDG Index、SDG Transformation Center（含地理空间工具指南） |
| **WRI** | Global Forest Watch、Aqueduct 水风险、数据开放工具 |
| **UNEP-WCMC** | WDPA、Protected Planet |
| **ITU AI for Good** | AI 与 SDG 融合的国际平台（标准、案例、峰会） |
| **UN Global Pulse** | 大数据（含地理空间）发展与人道应用 |
| **Group：OSDG.ai** | 开源 SDG 文本分类社区基础设施 |

---

## 8. 典型技术路线与选型建议

### 8.1 参考工作流（从数据到 SDG 仪表盘）

```
① 需求与指标定义（SDG 官方元数据 → 可地理空间化的代理指标）
② 数据获取（GEE/Planetary Computer/STAC 目录检索 → COG/Zarr 数据立方体）
③ 预处理（辐射/大气校正、云掩膜、时序合成；或直接用 HLS/ARD 产品）
④ 信息提取
   - 快速原型：GEE + RF/XGBoost
   - 高精度：基础模型嵌入（AlphaEarth/Prithvi/Clay）+ GBDT，或 torchgeo 微调分割
⑤ 统计-空间融合（dasymetric 格点化、面积加权、行政单元汇总、不确定性传播）
⑥ 空间分析（热点/回归/可达性/模拟 → 指标计算与驱动归因）
⑦ 验证（地面真值、交叉验证、与官方统计对账）
⑧ 发布与服务（PostGIS + GeoServer/STAC API + MapLibre/Cesium 前端）
⑨ 仪表盘与报告（SDG 进展可视化、VNR 支撑、政策情景模拟）
⑩ 运维（数据更新管道、模型再训练、版本与元数据管理）
```

### 8.2 选型速查

| 需求 | 首选方案 |
|---|---|
| 全球/全国尺度快速评估 | GEE（WorldCover + GHSL + 夜光 + RF） |
| 精细城市指标（贫民窟、绿地、公共空间） | 高分影像（Planet/国产高分）+ DL 分割（samgeo/Mask2Former）+ QGIS/ArcGIS |
| 缺标注样本地区制图 | 基础模型嵌入 + GBDT（AlphaEarth 模式）或少量样本微调（Prithvi/TerraTorch） |
| 统计指标的地理空间分解 | dasymetric + GHSL/WorldPop + 空间回归（MGWR/SDM） |
| 灾害暴露评估 | Sentinel-1 洪水/SAR 形变 + 人口资产格点（GHSL/WorldPop）+ GDACS |
| 服务公平性（医疗/教育/绿地/公交） | AccessMod / 2SFCA / GTFS + OSRM 等时圈 |
| 生态与碳 | InVEST + Hansen GFC + GEDI/ICESat-2 + LDN Toolbox |
| 报告与文献的 SDG 对齐 | OSDG 2.0 / LLM 分类 + 人工复核 |
| 平台工程 | STAC + COG/Zarr + PostGIS + GeoServer + MapLibre；重分析场景用 Planetary Computer/Pangeo |
| 国产替代 | SuperMap/MapGIS + PIE-Engine/阿里云 + SDGSAT-1/高分数据 + 国产基础模型（RingMo、SkySense） |

### 8.3 关键注意事项

1. **口径一致性**：遥感代理指标必须与官方指标定义（UNSD 元数据）对齐并注明偏差；用于国家报告需与统计部门协同。
2. **时空可比性**：传感器更换（如 Landsat→HLS 协调）、夜光跨代（DMSP→VIIRS）需要校准；云覆盖区（热带）优先 SAR。
3. **尺度效应**：MAUP、生态谬误；子国家分解结果应做敏感性分析。
4. **不确定性传播**：从像元分类误差到指标汇总误差的传递；报告置信区间。
5. **数据伦理与主权**：移动/社媒数据脱敏聚合；全球南方样本代表性；开源许可（Clay 为 Apache 2.0，部分商业数据受限）。
6. **可持续运维**：优先选有长期档案承诺的数据（Landsat/Sentinel 40+ 年）与开放标准（STAC/OGC）。

---

## 9. 参考资源与链接

**官方指标与统计**
- UN SDG Indicators 全球数据库与元数据：<https://unstats.un.org/sdgs/>（指标框架 251 条目/231 唯一指标）
- UN-GGIM 综合地理空间信息框架（IGIF）：<https://ggim.un.org/>
- SDSN SDG Transformation Center 地理空间指南：<https://sdgtransformationcenter.org/geospatial>
- 世界银行：国家和城市如何利用地理空间数据监测 SDG：<https://blogs.worldbank.org/zh/opendata/how-are-countries-and-cities-using-geospatial-data-monitor-their-sdgs>
- 拉美 Agenda 2030 地理可视化工具目录：<https://agenda2030lac.org/estadisticas/other-tools-geographic-visualization-sdgs.html>

**地球大数据与 SDGSAT**
- SDGSAT-1 开放科学计划：<https://www.sdgsat.ac.cn/>
- CBAS 可持续发展科学卫星/地球大数据报告：<https://www.cbas.ac.cn/>
- 《地球大数据支撑可持续发展目标报告（2023/2024）》
- 全球地理信息数据产品支撑 SDG 指标监测（2025，Remote Sensing Applications）：<https://www.sciencedirect.com/science/article/abs/pii/S2352938525003143>

**基础模型与 AI**
- Awesome Remote Sensing Foundation Models（持续更新的模型清单）：<https://github.com/Jack-bo1220/Awesome-Remote-Sensing-Foundation-Models>
- Prithvi-EO-2.0：<https://arxiv.org/abs/2412.02732>，权重：<https://huggingface.co/ibm-nasa-geospatial>
- AlphaEarth Foundations：<https://arxiv.org/abs/2507.22291>（GEE 数据集 `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL`）
- TerraMind（IBM/ESA）：<https://arxiv.org/abs/2504.11171>，<https://github.com/IBM/terramind>
- SkySense++（Nature Machine Intelligence 2025）：<https://www.nature.com/articles/s42256-025-01078-8>
- OSDG SDG 文本分类：<https://osdg.ai/>，论文 <https://arxiv.org/abs/2005.14569>

**数据平台**
- Google Earth Engine Data Catalog：<https://earthengine.google.com/>
- Microsoft Planetary Computer：<https://planetarycomputer.microsoft.com/>
- Copernicus Browser：<https://browser.dataspace.copernicus.eu/>
- NASA Earthdata / SDG Data Hub：<https://www.earthdata.nasa.gov/>
- Global Forest Watch：<https://www.globalforestwatch.org/>；WRI Aqueduct：<https://www.wri.org/aqueduct>
- JRC Global Surface Water Explorer：<https://global-surface-water.appspot.com/>
- GHSL：<https://ghsl.jrc.ec.europa.eu/>；WorldPop：<https://www.worldpop.org/>；WDPA：<https://www.protectedplanet.net/>
- Global Fishing Watch：<https://globalfishingwatch.org/>；GBIF：<https://www.gbif.org/>
- FAO Hand-in-Hand：<https://data-in-action.fao.org/>

---

*本文档为 SDGNode 仓库的基础知识梳理文档，可随项目演进持续更新（建议按"数据源目录 → 指标-数据映射 → 技术栈选型"三层维护）。*
