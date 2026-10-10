"""合成研究区（离线演示数据）。

**这些数据是合成的**，仅用于打通管线与验收端到端契约；不是真实 GHSL/WorldPop 观测。
真实执行路径 = Recipe 物化 → CAFE 下推到数据主权节点 → 返回结果（数据不动）。
城市集：北京/上海/广州/武汉（与 Recipe enum 对齐）。

目录约定（每城市一份，幂等再生成）：state/demo/<city>/
  aoi.geojson        城市分析边界（合成方块）
  mask.tif           AOI 栅格掩膜（300×300 网格，uint8）
  built_up_<year>.tif 建成区两期（0/1，uint8，中心盘 + 随年份扩张）
  pop_<year>.tif      人口两期（float32 高斯面，总量随年份增长）
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds

CITIES = {
    "北京": (116.40, 39.90),
    "上海": (121.47, 31.23),
    "广州": (113.26, 23.13),
    "武汉": (114.35, 30.55),
}
GRID = 300          # 300×300 像元
SPAN = 0.35         # 每边 0.35°（≈35km），足够演示增长曲线
METERS_PER_DEG = 111_000.0


def _transform(lon0: float, lat0: float) -> rasterio.Affine:
    # 网格覆盖 [lon0, lat0] × [lon0+SPAN, lat0+SPAN]（lat0 为南边界）
    return from_bounds(lon0, lat0, lon0 + SPAN, lat0 + SPAN, GRID, GRID)


def _city_bbox(city: str):
    lon, lat = CITIES[city]
    lon0, lat0 = lon - SPAN / 2, lat - SPAN / 2
    return lon0, lat0, lon0 + SPAN, lat0 + SPAN + SPAN


def _aoi_polygon(lon0: float, lat0: float) -> dict:
    # 方块 AOI（合成），占网格外围 80%
    d = GRID / 2
    cx, cy = lon0 + SPAN / 2, lat0 + SPAN / 2
    r = SPAN * 0.4
    ring = [
        [cx - r, cy - r], [cx + r, cy - r], [cx + r, cy + r], [cx - r, cy + r], [cx - r, cy - r]
    ]
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "synthetic-AOI", "sdgnode:synthetic": True},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        }],
    }


def _disk_builtup(radius_frac: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:GRID, 0:GRID]
    c = GRID / 2
    d = np.hypot(xx - c, yy - c) / (GRID / 2)
    noise = rng.normal(0, 0.05, (GRID, GRID))
    return ((d + noise) < radius_frac).astype(np.uint8)


def _gauss_pop(total: float, sigma_frac: float) -> np.ndarray:
    yy, xx = np.mgrid[0:GRID, 0:GRID]
    c = GRID / 2
    sigma = GRID * sigma_frac / 2
    g = np.exp(-(((xx - c) ** 2 + (yy - c) ** 2) / (2 * sigma ** 2)))
    return (g / g.sum() * total).astype(np.float32)


def _write_tif(path: Path, arr: np.ndarray, dtype: str, bbox, nodata=None) -> str:
    lon0, lat0, lon1, lat1 = bbox
    tf = _transform(lon0, lat0)
    with rasterio.open(
        path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1,
        dtype=dtype, crs="EPSG:4326", transform=tf,
    ) as dst:
        dst.write(arr, 1)
    return str(path)


def ensure(city: str, base: Path, baseline: int = 2015, year: int = 2020) -> dict:
    """幂等生成（或返回既有）城市合成研究区，返回路径+口径元数据。"""
    if city not in CITIES:
        raise ValueError(f"未知演示城市 {city}（可选 {list(CITIES)}）")
    d = Path(base) / city
    d.mkdir(parents=True, exist_ok=True)
    bbox = _city_bbox(city)
    lon0, lat0 = bbox[0], bbox[1]
    meta_path = d / "meta.json"
    paths = {
        "aoi": d / "aoi.geojson", "mask": d / "mask.tif",
        "built_up_t0": d / f"built_up_{baseline}.tif", "built_up_t1": d / f"built_up_{year}.tif",
        "pop_t0": d / f"pop_{baseline}.tif", "pop_t1": d / f"pop_{year}.tif",
    }
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("baseline") == baseline and meta.get("year") == year and all(p.exists() for p in paths.values()):
            return {"dir": str(d), **{k: str(v) for k, v in paths.items()}, "meta": meta}

    # 合成口径：建成区半径 2015=0.35 → 每年 +2.2%（复利），人口 2015=1000万 → 年 +2.5%
    dt = year - baseline
    r0, r1 = 0.35, min(0.35 * (1.022 ** dt), 0.95)
    p0, p1 = 1.0e7, 1.0e7 * (1.025 ** dt)
    cell_area_m2 = (SPAN / GRID * METERS_PER_DEG) ** 2

    paths["aoi"].write_text(json.dumps(_aoi_polygon(lon0, lat0), ensure_ascii=False), encoding="utf-8")
    poly = _aoi_polygon(lon0, lat0)["features"][0]["geometry"]
    from shapely.geometry import shape
    mask_arr = rasterize([(shape(poly), 1)], out_shape=(GRID, GRID), transform=_transform(lon0, lat0), fill=0, dtype="uint8")
    _write_tif(paths["mask"], mask_arr, "uint8", bbox)
    _write_tif(paths["built_up_t0"], _disk_builtup(r0, seed=baseline), "uint8", bbox)
    _write_tif(paths["built_up_t1"], _disk_builtup(r1, seed=year), "uint8", bbox)
    _write_tif(paths["pop_t0"], _gauss_pop(p0, 0.5), "float32", bbox)
    _write_tif(paths["pop_t1"], _gauss_pop(p1, 0.6), "float32", bbox)

    meta = {
        "synthetic": True, "city": city, "baseline": baseline, "year": year,
        "grid": GRID, "cell_area_m2": cell_area_m2, "note": "离线演示数据；真实路径经 CAFE 下推读取 GHSL/WorldPop",
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"dir": str(d), **{k: str(v) for k, v in paths.items()}, "meta": meta}
