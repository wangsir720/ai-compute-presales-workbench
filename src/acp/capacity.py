"""算力容量测算引擎：FLOPs、显存、卡数推算。

所有公式以公开资料可复现的方式定义，系数在 README「数据来源与口径」中说明。
显存单位统一用十进制 GB（1 GB = 1e9 bytes），与常见显卡标称（如 80 GB HBM）一致。
"""

import math
from .models import ServerSKU, WorkloadScenario

WEIGHTS_OVERHEAD = 1.2     # 权重显存冗余：激活/碎片的经验系数
UTIL = 0.5                 # 单卡有效算力利用率（吞吐估算）
BATCH_EFF = 0.7            # 批量效率：静态批处理对峰值的实际利用
# KV 缓存随模型规模近似线性：kv/token ≈ 权重字节数 × 该系数（量级估计，详见 README 局限）
KV_COEF = 4e-5


def training_flops(params_b, tokens_b):
    """训练总算力：C = 6 N D。"""
    return 6.0 * params_b * 1e9 * tokens_b * 1e9


def inference_flops_per_token(params_b):
    """推理每 token 算力：2 N。"""
    return 2.0 * params_b * 1e9


def inference_total_flops(params_b, in_tokens, out_tokens):
    return 2.0 * params_b * 1e9 * (in_tokens + out_tokens)


def vram_weights_gb(params_b, precision_bytes, overhead=WEIGHTS_OVERHEAD):
    return params_b * 1e9 * precision_bytes * overhead / 1e9


def kv_bytes_per_token(params_b, precision_bytes, overridden=0):
    if overridden and overridden > 0:
        return overridden
    return int(params_b * 1e9 * precision_bytes * KV_COEF)


def vram_kv_gb(concurrency, ctx_len, kv_bytes_per_token):
    return concurrency * ctx_len * kv_bytes_per_token / 1e9


def cards_for_vram(vram_gb, per_card_vram_gb):
    if per_card_vram_gb <= 0:
        return 0
    return math.ceil(vram_gb / per_card_vram_gb)


def per_card_tps(per_card_bf16_tflops, params_b, util=UTIL):
    denom = 2.0 * params_b * 1e9
    if denom <= 0:
        return 0.0
    return per_card_bf16_tflops * 1e12 * util / denom


def required_tps(concurrency, avg_out_tokens, latency_target_s):
    if latency_target_s <= 0:
        return 0.0
    return concurrency * avg_out_tokens / latency_target_s


def cards_for_throughput(req_tps, per_card_tps, batch_eff=BATCH_EFF):
    if per_card_tps <= 0:
        return 0
    return math.ceil(req_tps / (per_card_tps * batch_eff))


def plan_capacity(scn: WorkloadScenario, sku: ServerSKU):
    """对场景里最大模型做容量规划，返回显存/吞吐两个约束下的卡数与服务器数。"""
    m = scn.max_model()
    pb = scn.precision_bytes()
    w = vram_weights_gb(m.params_b, pb)
    kv_bpt = kv_bytes_per_token(m.params_b, pb, scn.kv_bytes_per_token)
    kv = vram_kv_gb(scn.concurrency, scn.ctx_len, kv_bpt)
    vram_need = w + kv
    c_vram = cards_for_vram(vram_need, sku.per_card_vram_gb)
    pct = per_card_tps(sku.per_card_bf16_tflops, m.params_b)
    rtps = required_tps(scn.concurrency, m.avg_out_tokens, scn.latency_target_s)
    c_tput = cards_for_throughput(rtps, pct)
    raw = max(c_vram, c_tput)
    servers = math.ceil(raw / sku.cards) if sku.cards > 0 else 0
    return {
        "model": m.name,
        "params_b": m.params_b,
        "vram_weights_gb": round(w, 1),
        "vram_kv_gb": round(kv, 1),
        "vram_need_gb": round(vram_need, 1),
        "kv_bytes_per_token": kv_bpt,
        "cards_for_vram": c_vram,
        "per_card_tps": round(pct, 1),
        "required_tps": round(rtps, 1),
        "cards_for_tput": c_tput,
        "bottleneck": "vram" if c_vram >= c_tput else "throughput",
        "raw_cards": raw,
        "servers": servers,
        "actual_cards": servers * sku.cards,
        "accel": sku.accel,
    }


def plan_training(scn: WorkloadScenario, sku: ServerSKU, util=0.4):
    """训练场景：在给定天数内训完所需服务器数。"""
    m = scn.max_model()
    total_flops = training_flops(m.params_b, scn.train_tokens_b)
    if sku.cards <= 0:
        return {"servers": 0, "days": None}
    per_gpu_flops_s = sku.per_card_bf16_tflops * 1e12 * util
    per_server_flops_s = per_gpu_flops_s * sku.cards
    seconds_needed = total_flops / per_server_flops_s if per_server_flops_s > 0 else 0
    days_needed = seconds_needed / 86400.0
    servers_for_target = math.ceil(days_needed / scn.train_days) if scn.train_days > 0 else 0
    return {
        "model": m.name,
        "total_flops": total_flops,
        "days_one_server": round(days_needed, 1),
        "servers_for_target": servers_for_target,
        "accel": sku.accel,
    }
