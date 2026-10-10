"""SDGNode 公共算子技能包（P1）。

- operators.py：真实栅格算子 handler（rasterio/numpy/shapely），契约 = cards/skill/*.yaml
- synth.py：合成研究区（离线演示数据，明确标记 synthetic；生产环境走 CAFE 下推到数据主权节点）
- register_all(node)：把算子注册进 GeoNode（geo.execute 可用），skill 名 = GeoCard id
"""
from __future__ import annotations

from .operators import HANDLERS, SKILL_CARDS, register_all

__all__ = ["HANDLERS", "SKILL_CARDS", "register_all"]
