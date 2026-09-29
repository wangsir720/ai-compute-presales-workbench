"""AI 算力售前工作台：容量测算 / 双生态选型 / 液冷 PUE 与 TCO / 方案书生成。"""

from .models import ServerSKU, ModelSpec, WorkloadScenario, load_products, load_scenario
from .capacity import (
    training_flops, inference_flops_per_token, vram_weights_gb,
    vram_kv_gb, cards_for_vram, per_card_tps, required_tps, cards_for_throughput,
    plan_capacity,
)
from .selection import selection_matrix, recommend
from .tco import pue_for, PUE_NOTE, annual_energy_kwh, tco_3yr, gross_margin, margin_sensitivity
from .bom import build_bom
from .redfish import redfish_precheck, RedfishIssue

__all__ = [
    "ServerSKU", "ModelSpec", "WorkloadScenario", "load_products", "load_scenario",
    "training_flops", "inference_flops_per_token", "vram_weights_gb", "vram_kv_gb",
    "cards_for_vram", "per_card_tps", "required_tps", "cards_for_throughput",
    "plan_capacity", "selection_matrix", "recommend", "pue_for", "PUE_NOTE",
    "annual_energy_kwh", "tco_3yr", "gross_margin", "margin_sensitivity",
    "build_bom", "redfish_precheck", "RedfishIssue",
]
