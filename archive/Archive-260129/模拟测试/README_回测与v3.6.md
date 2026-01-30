# 《功德轮回》回测系统与 v3.6 平衡调优

## 1. 回测系统说明

### 1.1 文件与职责

| 文件 | 职责 |
|------|------|
| `game_simulator_v3.5_final.py` | 主模拟器；支持事件牌/众生牌注入、种子、save_required/max_rounds/calamity_limit |
| `backtest_system.py` | 完善回测：可复现种子、多配置、失败原因细分、事件卡参数化、综合排名分 |
| `balance_tuning_v36.py` | v3.6 平衡调优脚本：多方案对比（事件卡微调 + 渡化门槛），输出推荐方案 |

### 1.2 模拟器扩展（v3.5 → 回测用）

- **种子可复现**：`GameSimulator(..., rng=random.Random(seed))`，骰子与行动随机均用 `self.rng`。
- **事件牌注入**：`event_effects=list of {"name","effect"}`，用于微调事件效果（如 calamity、fu_all、hui_all）。
- **众生牌注入**：`beings_template=list of SentientBeing or dict`，用于调整众生池。
- **全局参数**：`save_required`、`max_rounds`、`calamity_limit`，便于敏感性分析。

### 1.3 回测配置（BacktestConfig）

- `seed`：固定则结果可复现。
- `num_sims`：每配置局数（建议 ≥500）。
- `configs`：多组 (名称, 策略列表, 皈依列表)，默认 6 组（全皈依+平衡、全不皈依+平衡、商人财富、农夫福德、学者智慧、僧侣福德）。
- `event_deck_factory`：可调用或事件列表，用于事件卡调参。
- `save_required` / `max_rounds` / `calamity_limit`：覆盖默认值。
- `multi_seed_count`：>0 时用多种子跑，可看胜率方差。

### 1.4 输出指标

- **团队胜率**：每配置的团队胜利比例。
- **失败原因**：劫难过高 / 渡化不足 / 两者皆有。
- **综合排名分**：各配置下角色按胜率排名 1–4 名得 +2/+1/-1/-2，加总；目标各角色接近 0。
- **最终劫难/渡化**：均值、标准差、中位数（在 BalanceTester 中已有）。

---

## 2. 平衡调优思路（批判性、不单点调数）

- **不在单一机制上反复上下调**：同时考虑事件卡、渡化门槛、众生数量、生存消耗等。
- **重点微调事件卡**：v3.5 失败原因 100% 为渡化不足，通过减轻负面事件（旱灾/洪水/瘟疫）、增强正面（国泰民安）使劫难相关失败占比出现，并保持胜率在合理区间。
- **可选杠杆**：`save_required` 6→5、众生池数量、生存消耗频率等，在脚本中通过不同方案对比。

---

## 3. 事件卡 v3.6 微调表（推荐）

在保持 8 张事件种类不变前提下，仅调数值：

| 事件名 | v3.5 效果 | v3.6 推荐（方案A） | 说明 |
|--------|-----------|--------------------|------|
| 旱灾 | calamity +2 | calamity +1 | 减轻负面 |
| 洪水 | calamity +2 | calamity +1 | 减轻负面 |
| 瘟疫 | calamity +3, wealth_all -1 | calamity +2, wealth_all -1 | 减轻负面 |
| 国泰民安 | calamity -2 | calamity -3 | 略增强正面 |
| 丰收/法会/高僧开示/浴佛节 | 不变 | 不变 | - |

- **方案B**：同上事件 + `save_required=5`（降低渡化门槛，进一步分散失败原因）。
- **方案C**：旱灾/洪水保持 +2，瘟疫改为 +2，国泰民安 -2；用于保留一定劫难压力，使劫难失败仍有一定占比。

---

## 4. 如何运行

### 4.1 环境

- Python 3.7+，无额外依赖（仅标准库 + dataclasses）。

### 4.2 运行回测 + 平衡调优

在 **模拟测试** 目录下执行（保证能正确加载同目录下的 `game_simulator_v3.5_final.py`）：

```bash
cd 桌游/模拟测试
python balance_tuning_v36.py
```

或在项目根目录用完整路径（若路径含中文无法执行，可先 `cd` 到 `桌游\模拟测试` 再运行）：

```bash
python "桌游/模拟测试/balance_tuning_v36.py"
```

脚本会输出：

- 基线（v3.5 默认事件、save_required=6）的胜率与失败原因；
- 方案A/B/C 的胜率、失败原因占比、综合排名分；
- 推荐采用方案及对应事件卡与参数。

### 4.3 仅跑回测（自定义配置）

```python
from backtest_system import BacktestConfig, run_full_backtest, default_event_deck

cfg = BacktestConfig(seed=42, num_sims=500, event_deck_factory=default_event_deck)
summary = run_full_backtest(cfg)
print(summary["rank_scores"])
print(summary["results_by_config"][0][1]["fail_reasons"])
```

---

## 5. v3.6 最终版参数汇总

- **事件卡**：见上表（方案A 为推荐默认）。
- **渡化门槛**：`save_required=6`（方案B 可选 5）。
- **其他规则**：与 v3.5 一致（发愿、皈依、投资、持续帮助、团队合作 AI 等）。
- **平衡目标**：全皈依+平衡胜率 85–92%；失败原因中劫难相关占约 5–25%；综合排名分各角色尽量接近 0（农夫 v3.5 为 -8，可通过事件卡与渡化门槛缓解）。

---

## 6. 版本记录

- **v3.5**：综合平衡版，6 配置，综合排名分；失败原因 100% 渡化不足。
- **v3.6**：完善回测系统（种子、事件/众生注入、失败细分）；事件卡微调与多方案平衡调优；推荐方案 A/B/C 及使用说明。
