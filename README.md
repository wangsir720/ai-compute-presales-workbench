# ai-compute-presales-workbench · AI 算力售前工作台

把一次算力（AI 服务器 / 智算中心）售前方案，从"反复手算 + 拼文档"变成"一条命令出整套测算与方案包"。

输入一个场景需求（模型规模、并发、时延、上下文长度、散热方式、报价），输出：**容量测算 + 双生态选型评分 + 液冷 PUE 与三年 TCO + 毛利敏感性 + 国产化适配说明 + 架构图**。

> 个人学习项目，与任何厂商无关。机型为按公开通用规格抽象出的参数化档位，参数与价格为公开渠道档位参考值，正式项目以厂商正式彩页与报价为准。

---

## 一、要解决什么问题

算力售前阶段最耗时的不是讲产品，而是反复算、反复写：

| 痛点 | 常见做法 | 本项目的做法 |
|---|---|---|
| 显存 / 卡数靠经验拍 | 凭感觉估"大概 8 卡够" | 按参数量 × 精度反推权重显存 + KV 缓存，逐约束算卡数 |
| 选型靠熟 | 默认推某一款 | x86(NVIDIA) 与鲲鹏+昇腾双生态评分矩阵，可复核 |
| TCO 靠报价软件 | 手工填电费、算不清 PUE 影响 | 功耗 → 散热方式(PUE) → 三年电费/运维/毛利敏感性 |
| 方案书靠复制旧文档 | 改格式改半天、数字对不上 | Jinja2 模板渲染，数字全部来自测算结果 |
| 架构图靠拖拽 | 改一次重画一次 | 架构图 as code，改配置重跑即出图 |

---

## 二、方案构成

```
ai-compute-presales-workbench/
├── README.md
├── data/products.json          # 参数化机型库（11 个 SKU，4 类加速卡机型）
├── config/
│   ├── scenarios/              # 场景模板：推理服务 / 训练集群 / 推理一体机
│   └── redfish-demo.json      # Redfish 风格设备清单（含预置问题样本）
├── src/acp/
│   ├── models.py               # 机型库与场景加载
│   ├── capacity.py             # FLOPs / 显存 / 卡数测算
│   ├── selection.py            # 双生态选型评分矩阵
│   ├── tco.py                  # 液冷 PUE / 三年 TCO / 毛利敏感性
│   ├── bom.py                  # 工程量清单推导
│   ├── diagram.py              # 架构图 as code → SVG
│   ├── redfish.py              # Redfish 风格离线预检（不联网）
│   ├── reporting.py            # 模板渲染与 CSV 输出
│   └── cli.py                  # 命令行入口
├── templates/                  # 5 个交付物模板（Jinja2）
├── scripts/generate_all.py     # 一键生成全部场景交付物
├── tests/                      # 32 条单元测试
└── outputs/                    # 生成物（已提交，可直接查看）
```

### 容量测算引擎

- **训练算力**：`C = 6 N D`（N=参数量，D=训练 token 数）。
- **推理算力**：每 token `2 N`；单卡吞吐 `≈ 峰值 TFLOPS × 利用率 ÷ (2N)`。
- **权重显存**：`参数量 × 精度字节 × 1.2 冗余`；KV 缓存按 `并发 × 上下文长度 × 每 token 字节数` 估算。
- **卡数约束**：取「显存约束卡数」与「吞吐约束卡数」的最大值，再按机型卡数向上取整到服务器台数。

### 双生态选型

对每条加速卡机型（x86/NVIDIA 类、鲲鹏+昇腾类）评分，权重：显存贴合 0.30、吞吐贴合 0.25、国产替代 0.20、成本 0.25，输出降序排名与推荐机型。

### 液冷 PUE 与 TCO

- PUE 取业界参考中值：风冷 1.6 / 冷板 1.25 / 浸没 1.1。
- 年耗电 `= IT 功率 × 8760 × PUE ÷ 1000`；三年 TCO `= 硬件成本基准 + 3 ×(电费 + 运维)`。
- 硬件成本基准按公开档位价的 7 折折算；方案毛利 `= 报价 − 三年 TCO`，并给出 0/5/10/15% 折扣下的敏感性。

### Redfish 风格预检

对符合 Redfish 响应结构的设备清单做字段与阈值校验（状态、功耗区间、加速卡数量、内存下限），输出阻断项与提醒项。**本模块不建立任何网络连接**，生产环境对接真实设备请用 DMTF 官方库替换数据来源。

---

## 三、效果（本机实跑结果）

| 指标 | 结果 |
|---|---|
| 场景模板 | 3 个（大模型推理服务 / 训练集群 / AI 推理一体机） |
| 参数化机型 | 11 个 SKU，覆盖 x86/NVIDIA 与鲲鹏+昇腾双生态 |
| 单条命令产出 | 3 个场景共 15 份交付件（每场景 5 份文档 + BOM CSV + 架构图 SVG） |
| 单元测试 | 32 条，全部通过 |
| 生成耗时 | 3 个场景全量约 0.4 s |

### 测算样例：大模型推理服务平台（70B / bf16 / 并发 32 / 冷板液冷）

| 指标 | 结果 |
|---|---|
| 权重显存 | 168 GB（含 1.2 冗余） |
| KV 缓存显存 | 734 GB（按 5.6 MB/token 估算） |
| 显存总需求 | 902 GB → 显存约束卡数 12 |
| 推荐机型 | KP-ASC-8U8（鲲鹏+昇腾） |
| 部署规模 | 2 台（16 卡） |
| 三年 TCO | 约 275 万元，方案毛利约 145 万元 |

架构图（由 `diagram.py` 生成）：`outputs/llm-inference-service/06-系统架构图.svg`

---

## 四、快速开始

```bash
# 依赖
pip install -r requirements.txt

# 生成某一个场景的整套交付物
set PYTHONPATH=src
python -m acp.cli generate --scenario config/scenarios/llm-inference-service.yaml

# 生成全部场景
python scripts/generate_all.py

# 仅看各机型容量测算
python -m acp.cli compute --scenario config/scenarios/llm-inference-service.yaml

# 双生态选型评分
python -m acp.cli selection --scenario config/scenarios/llm-inference-service.yaml

# 液冷 PUE 与三年 TCO / 毛利
python -m acp.cli tco --scenario config/scenarios/llm-inference-service.yaml --sku KP-ASC-8U8

# Redfish 风格设备清单离线预检
python -m acp.cli redfish-check --inventory config/redfish-demo.json --accel 8

# 单元测试
python -m pytest tests -q
```

新增场景只需在 `config/scenarios/` 下加一个 YAML，重跑即可。

---

## 五、数据来源与口径

- 机型参数取自公开渠道可查的**通用规格档位**，用于方案测算，不引用任何厂商内部资料。
- `price_ref` 为公开渠道档位参考价，仅用于 TCO 测算，不代表任何厂商正式报价；硬件成本按 7 折折算为成本基准。
- KV 缓存按 `参数量 × 精度字节 × 4e-5` 的系数估算，为量级估计，落地以真实框架 profiling 为准。
- 双生态（鲲鹏+昇腾）能力描述为行业公开认知，具体算子覆盖与性能以厂商官方文档为准。

---

## 六、局限

- 机型库是参数化抽象档位，不是具体产品目录，不能直接用于选型报价。
- 显存/卡数模型未计入张量并行策略、流水线并行、通信开销与显存复用，实际部署需结合并行方案。
- KV 缓存系数为量级估计，长上下文、高并发场景的实测值与估算会有偏差。
- 单卡吞吐按峰值 × 利用率（0.5）估算，未计入通信与调度开销。
- TCO 只覆盖硬件、电费、运维三类，不含机房基建、专线、License 与运维人力外包。
- Redfish 预检为离线结构校验，不替代真实带外管理系统的注册与状态同步。

---

## 七、后续计划

- 接入真实并行策略（TP/PP/EP），把卡数测算从"单卡堆叠"推进到"集群拓扑"。
- 增加多模型混合部署的容量复用测算。
- 输出方案书 docx 版，减少最终排版环节。
