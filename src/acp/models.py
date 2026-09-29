"""数据模型：机型库与场景加载。"""

import json
import yaml
from dataclasses import dataclass, field


@dataclass
class ServerSKU:
    sku: str
    category: str               # gpu_server / cpu_server / switch / storage / rack / cooling / pdu
    cpu_arch: str = "x86"       # x86 / kunpeng
    accel: str = ""             # nvidia-class / ascend-class / ""
    cards: int = 0              # 加速卡数量（GPU/NPU），CPU 类为 0
    per_card_vram_gb: float = 0.0
    per_card_bf16_tflops: float = 0.0
    tdp_w: float = 0.0
    price_ref: float = 0.0
    localization: float = 0.0   # 国产替代加权 0..1：鲲鹏+昇腾=1.0，x86=0.6
    note: str = ""

    def is_accelerator(self):
        return self.cards > 0

    def total_vram_gb(self):
        return self.cards * self.per_card_vram_gb

    def peak_tflops(self):
        return self.cards * self.per_card_bf16_tflops


@dataclass
class ModelSpec:
    name: str
    params_b: float
    avg_in_tokens: int = 1500
    avg_out_tokens: int = 600


@dataclass
class WorkloadScenario:
    sid: str
    name: str
    kind: str                   # inference / training / appliance
    precision: str = "bf16"     # bf16 / fp16 / int8
    models: list = field(default_factory=list)
    concurrency: int = 0
    latency_target_s: float = 3.0
    ctx_len: int = 8192
    train_tokens_b: float = 0.0
    cooling: str = "air"        # air / cold-plate / immersion
    power_price: float = 0.8
    solution_price: float = 0.0
    years: int = 3
    kv_bytes_per_token: int = 0
    train_days: int = 30

    BYTES = {"bf16": 2, "fp16": 2, "fp32": 4, "int8": 1, "int4": 0.5}

    def precision_bytes(self):
        return self.BYTES.get(self.precision, 2)

    def max_model(self):
        return max(self.models, key=lambda m: m.params_b)

    def total_params_b(self):
        return sum(m.params_b for m in self.models)


def load_products(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [ServerSKU(**d) for d in raw]


def load_scenario(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    models = [ModelSpec(**m) for m in raw.pop("models", [])]
    return WorkloadScenario(models=models, **raw)
