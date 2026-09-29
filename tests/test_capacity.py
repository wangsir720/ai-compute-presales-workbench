import os
import pytest

from acp.models import load_products, load_scenario
from acp import capacity

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD = os.path.join(HERE, "data", "products.json")
SCN = lambda n: os.path.join(HERE, "config", "scenarios", n)


@pytest.fixture
def products():
    return load_products(PROD)


@pytest.fixture
def x86_8():
    return load_products(PROD)[0]  # X86-GPU-8U8


def test_training_flops_formula():
    # C = 6 N D
    assert capacity.training_flops(70, 1) == pytest.approx(6 * 70e9 * 1e9)


def test_inference_flops_per_token():
    assert capacity.inference_flops_per_token(70) == pytest.approx(2 * 70e9)


def test_vram_weights_overhead():
    # 70B bf16 → 70 * 2 * 1.2 = 168 GB
    assert capacity.vram_weights_gb(70, 2) == pytest.approx(168.0)


def test_kv_bytes_default_scales_with_model():
    a = capacity.kv_bytes_per_token(70, 2)
    b = capacity.kv_bytes_per_token(13, 1)
    assert a > b
    assert a == int(70e9 * 2 * 4e-5)


def test_inference_plan_x86_8u8(products, x86_8):
    scn = load_scenario(SCN("llm-inference-service.yaml"))
    cap = capacity.plan_capacity(scn, x86_8)
    assert cap["vram_weights_gb"] == pytest.approx(168.0)
    assert cap["vram_need_gb"] == pytest.approx(902.0, abs=1)
    assert cap["cards_for_vram"] == 12
    assert cap["bottleneck"] == "vram"
    assert cap["servers"] == 2
    assert cap["actual_cards"] == 16


def test_inference_plan_kunpeng_ascend(products):
    scn = load_scenario(SCN("llm-inference-service.yaml"))
    kp = [p for p in products if p.sku == "KP-ASC-8U8"][0]
    cap = capacity.plan_capacity(scn, kp)
    assert cap["cards_for_vram"] == 15
    assert cap["servers"] == 2
    assert cap["actual_cards"] == 16


def test_appliance_fits_single_node(products):
    scn = load_scenario(SCN("inference-appliance.yaml"))
    sku = [p for p in products if p.sku == "X86-GPU-4U4"][0]
    cap = capacity.plan_capacity(scn, sku)
    assert cap["servers"] == 1
    assert cap["actual_cards"] == 4


def test_training_plan_servers(products):
    scn = load_scenario(SCN("training-cluster.yaml"))
    sku = [p for p in products if p.sku == "X86-GPU-8U8"][0]
    plan = capacity.plan_training(scn, sku)
    assert plan["servers_for_target"] == 2
    assert plan["days_one_server"] == pytest.approx(30.7, abs=0.5)


def test_required_tps_zero_latency_safe():
    assert capacity.required_tps(100, 500, 0) == 0
