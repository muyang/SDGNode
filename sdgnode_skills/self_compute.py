"""自注册算力卡（能力节点向平台声明"我是谁的算力候选"）。

resolve_compute_capabilities(registry_url) 读 type:compute 卡的 access.endpoint /
注册条目的 node_url 作为候选算力——所以自注册卡的 endpoint 指向**模型服务基址**
（invoke_model 过门禁后 provider 会 retarget 到这里），而不是 GeoMCP 端口。
"""
from __future__ import annotations

import ctypes
import os
import socket


def host_cpu_count() -> int:
    return os.cpu_count() or 1


def host_ram_gb() -> float | None:
    """尽力探测物理内存（GB）：Windows GlobalMemoryStatusEx，POSIX sysconf。"""
    try:
        if os.name == "nt":
            class _MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            ms = _MEMORYSTATUSEX()
            ms.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
                return round(ms.ullTotalPhys / 2**30, 1)
            return None
        page = os.sysconf("SC_PAGE_SIZE")
        pages = os.sysconf("SC_PHYS_PAGES")
        return round(page * pages / 2**30, 1)
    except Exception:  # noqa: BLE001
        return None


def host_gpu_declare() -> str:
    """诚实声明：自注册算力卡只说**本节点实际部署的能力**。

    SDGNode 当前只部署 CPU 契约模型服务（services/model_provider.py），
    即便本机装有 nvidia-smi 也不虚报 GPU——虚报会让 GPU 模型的算力门禁
    错误放行、把请求打到没有 GPU 服务的节点。真实 GPU 池接入后，
    用环境变量 SDGNODE_GPU="1xA100" 显式声明即可。
    """
    return os.environ.get("SDGNODE_GPU", "none")


def build_self_compute_card(model_endpoint: str, node_name: str = "sdg-node",
                            api_base: str | None = None) -> dict:
    """构造本机算力自注册卡（type: compute）。

    model_endpoint: 该算力池的模型服务基址（invoke 门禁 retarget 目标）。
    api_base: 本节点 GeoMCP 地址（写进 provenance，便于人读拓扑）。
    """
    cpu = host_cpu_count()
    ram = host_ram_gb()
    gpu = host_gpu_declare()
    host = socket.gethostname()
    card = {
        "geocard_version": "1.0",
        "id": f"sdg.compute.sdg-node.self-pool",
        "type": "compute",
        "name": f"SDGNode 自注册算力池（{host}）",
        "description": (
            f"SDGNode 能力节点开机自注册的实时算力声明：{cpu} 核 / "
            f"{ram if ram is not None else '未知'} GiB / GPU={gpu}。"
            "endpoint 指向同机模型服务基址，供 resolve_compute_capabilities 发现。"
        ),
        "tags": ["compute", "self-registered", "live"],
        "capabilities": ["model-inference", "batch-compute"],
        "runtime": {"cpu": cpu, "memory": f"{int(ram)}Gi" if ram else "8Gi", "gpu": gpu},
        "access": {
            "protocol": "https",
            "endpoint": model_endpoint.rstrip("/"),
            "auth": "apikey",
        },
        "provenance": {
            "provider": "SDGNode",
            "source": f"self-registration by {node_name}",
            "lineage": f"built-in 探测 @ {api_base or node_name}",
        },
        "license": "Apache-2.0",
        "compliance": {"sovereignty": "local-node", "sensitivity": "public"},
        "trust": {"verified": True, "score": 0.8},
    }
    return card
