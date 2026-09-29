"""液冷 PUE 与三年 TCO、毛利敏感性测算。"""

# PUE 取业界参考中值：风冷 1.5–1.8、冷板 1.2–1.3、浸没 1.05–1.15。
PUE = {"air": 1.6, "cold-plate": 1.25, "immersion": 1.1}
PUE_NOTE = "PUE 取业界参考区间中值；不同机房与地区会有偏差，落地以设计院测算为准。"
COGS_RATIO = 0.7          # 渠道成本约为公开档位价的 7 折，用于毛利基准
OPEX_RATIO = 0.08         # 年运维约为硬件成本的 8%


def pue_for(cooling):
    return PUE.get(cooling, 1.6)


def it_power_w(items):
    """items: [{power_w, qty}] 求和。"""
    return sum(i["power_w"] * i["qty"] for i in items)


def annual_energy_kwh(it_w, pue, hours=8760):
    return it_w * hours * pue / 1000.0


def electricity_cost(kwh, price):
    return kwh * price


def tco_3yr(hardware_capex, it_w, pue, price, years=3,
            cogs_ratio=COGS_RATIO, opex_ratio=OPEX_RATIO):
    """返回成本拆解 dict。硬件成本按 cogs_ratio 折算，避免用公开档位价高估成本。"""
    cost_basis = hardware_capex * cogs_ratio
    energy = annual_energy_kwh(it_w, pue)
    elec_year = electricity_cost(energy, price)
    opex_year = cost_basis * opex_ratio
    total = cost_basis + years * (elec_year + opex_year)
    return {
        "cost_basis": round(cost_basis, 0),
        "pue": pue,
        "annual_energy_kwh": round(energy, 0),
        "annual_elec": round(elec_year, 0),
        "annual_opex": round(opex_year, 0),
        "elec_3yr": round(elec_year * years, 0),
        "opex_3yr": round(opex_year * years, 0),
        "total": round(total, 0),
    }


def gross_margin(solution_price, tco_total):
    return round(solution_price - tco_total, 0)


def margin_sensitivity(solution_price, tco_total, discounts=(0.0, 0.05, 0.10, 0.15)):
    return {d: round(solution_price * (1 - d) - tco_total, 0) for d in discounts}
