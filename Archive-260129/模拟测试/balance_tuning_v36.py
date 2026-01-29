# -*- coding: utf-8 -*-
"""
《功德轮回》v3.6 平衡调优脚本

- 批判性调试：不单在单一机制上反复调数值，从事件卡、渡化门槛、众生数量等多机制入手
- 重点微调事件卡：减轻负面事件、增强正面事件，使失败原因多样化（劫难/渡化/两者）
- 目标：全皈依+平衡胜率 85–92%，失败原因不再 100% 渡化不足，角色排名分更均衡
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_system import (
    BacktestConfig, run_full_backtest, run_single_backtest,
    default_event_deck, tuned_event_deck_v36, _default_configs, _std, _median,
)

# 从模拟器取类型
import importlib.util
_sim_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_simulator_v3.5_final.py")
_spec = importlib.util.spec_from_file_location("sim", _sim_path)
_sim = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sim)
RoleType = _sim.RoleType
Strategy = _sim.Strategy
RefugeChoice = _sim.RefugeChoice


def event_deck_v36_alt2():
    """微调方案2：再减轻瘟疫、国泰民安-3"""
    return [
        {"name": "旱灾", "effect": {"calamity": 1}},
        {"name": "洪水", "effect": {"calamity": 1}},
        {"name": "瘟疫", "effect": {"calamity": 2, "wealth_all": -1}},
        {"name": "丰收", "effect": {"wealth_all": 2}},
        {"name": "法会", "effect": {"fu_all": 1, "hui_all": 1}},
        {"name": "高僧开示", "effect": {"hui_all": 2}},
        {"name": "国泰民安", "effect": {"calamity": -3}},
        {"name": "浴佛节", "effect": {"fu_all": 2}},
    ]


def event_deck_v36_calamity_more():
    """微调方案3：保留一定负面，让劫难失败能出现（旱灾/洪水 2，国泰-2）"""
    return [
        {"name": "旱灾", "effect": {"calamity": 2}},
        {"name": "洪水", "effect": {"calamity": 2}},
        {"name": "瘟疫", "effect": {"calamity": 2, "wealth_all": -1}},
        {"name": "丰收", "effect": {"wealth_all": 2}},
        {"name": "法会", "effect": {"fu_all": 1, "hui_all": 1}},
        {"name": "高僧开示", "effect": {"hui_all": 2}},
        {"name": "国泰民安", "effect": {"calamity": -2}},
        {"name": "浴佛节", "effect": {"fu_all": 2}},
    ]


def event_deck_harsher():
    """方案D：加重负面事件，使劫难能导致失败（旱灾/洪水3，瘟疫4，国泰-1）"""
    return [
        {"name": "旱灾", "effect": {"calamity": 3}},
        {"name": "洪水", "effect": {"calamity": 3}},
        {"name": "瘟疫", "effect": {"calamity": 4, "wealth_all": -1}},
        {"name": "丰收", "effect": {"wealth_all": 2}},
        {"name": "法会", "effect": {"fu_all": 1, "hui_all": 1}},
        {"name": "高僧开示", "effect": {"hui_all": 2}},
        {"name": "国泰民安", "effect": {"calamity": -1}},
        {"name": "浴佛节", "effect": {"fu_all": 2}},
    ]


def event_deck_middle():
    """方案E：折中——适度负面，国泰略强（旱灾/洪水2，瘟疫3，国泰-2）"""
    return [
        {"name": "旱灾", "effect": {"calamity": 2}},
        {"name": "洪水", "effect": {"calamity": 2}},
        {"name": "瘟疫", "effect": {"calamity": 3, "wealth_all": -1}},
        {"name": "丰收", "effect": {"wealth_all": 2}},
        {"name": "法会", "effect": {"fu_all": 1, "hui_all": 1}},
        {"name": "高僧开示", "effect": {"hui_all": 2}},
        {"name": "国泰民安", "effect": {"calamity": -2}},
        {"name": "浴佛节", "effect": {"fu_all": 2}},
    ]


def main():
    num_sims = 800
    seed = 42
    configs = _default_configs()

    print("=" * 70)
    print("《功德轮回》v3.6 平衡调优")
    print("=" * 70)
    print(f"每配置 {num_sims} 局，种子 {seed}")
    print()

    # ---------- 基线：v3.5 默认事件 ----------
    print("[1] 基线（v3.5 默认事件，save_required=6）")
    cfg_baseline = BacktestConfig(seed=seed, num_sims=num_sims, configs=configs,
                                  event_deck_factory=default_event_deck, save_required=6)
    out_baseline = run_full_backtest(cfg_baseline)
    r0 = out_baseline["results_by_config"][0][1]
    print(f"    全皈依+平衡 胜率: {r0['team_win_rate']:.1f}%")
    print(f"    失败原因: 劫难={r0['fail_reasons']['calamity']}, 渡化={r0['fail_reasons']['save_count']}, 两者={r0['fail_reasons']['both']}")
    print(f"    排名分: {out_baseline['rank_scores']}")
    print()

    # ---------- 方案A：事件卡微调（减轻负面、国泰-3） ----------
    print("[2] 方案A：事件卡微调（旱灾/洪水1，瘟疫2，国泰-3）")
    cfg_a = BacktestConfig(seed=seed, num_sims=num_sims, configs=configs,
                           event_deck_factory=tuned_event_deck_v36, save_required=6)
    out_a = run_full_backtest(cfg_a)
    r_a = out_a["results_by_config"][0][1]
    print(f"    全皈依+平衡 胜率: {r_a['team_win_rate']:.1f}%")
    print(f"    失败原因: 劫难={r_a['fail_reasons']['calamity']}, 渡化={r_a['fail_reasons']['save_count']}, 两者={r_a['fail_reasons']['both']}")
    print(f"    排名分: {out_a['rank_scores']}")
    print()

    # ---------- 方案B：事件卡微调 + 渡化门槛降为5 ----------
    print("[3] 方案B：同方案A事件 + save_required=5")
    cfg_b = BacktestConfig(seed=seed, num_sims=num_sims, configs=configs,
                           event_deck_factory=tuned_event_deck_v36, save_required=5)
    out_b = run_full_backtest(cfg_b)
    r_b = out_b["results_by_config"][0][1]
    print(f"    全皈依+平衡 胜率: {r_b['team_win_rate']:.1f}%")
    print(f"    失败原因: 劫难={r_b['fail_reasons']['calamity']}, 渡化={r_b['fail_reasons']['save_count']}, 两者={r_b['fail_reasons']['both']}")
    print(f"    排名分: {out_b['rank_scores']}")
    print()

    # ---------- 方案C：保留一定负面事件，不降低渡化门槛 ----------
    print("[4] 方案C：事件微调（旱灾/洪水2，瘟疫2，国泰-2）")
    cfg_c = BacktestConfig(seed=seed, num_sims=num_sims, configs=configs,
                           event_deck_factory=event_deck_v36_calamity_more, save_required=6)
    out_c = run_full_backtest(cfg_c)
    r_c = out_c["results_by_config"][0][1]
    print(f"    全皈依+平衡 胜率: {r_c['team_win_rate']:.1f}%")
    print(f"    失败原因: 劫难={r_c['fail_reasons']['calamity']}, 渡化={r_c['fail_reasons']['save_count']}, 两者={r_c['fail_reasons']['both']}")
    print(f"    排名分: {out_c['rank_scores']}")
    print()

    # ---------- 方案D：加重负面事件，使劫难能导致失败 ----------
    print("[5] 方案D：加重负面（旱灾/洪水3，瘟疫4，国泰-1）")
    cfg_d = BacktestConfig(seed=seed, num_sims=num_sims, configs=configs,
                          event_deck_factory=event_deck_harsher, save_required=6)
    out_d = run_full_backtest(cfg_d)
    r_d = out_d["results_by_config"][0][1]
    print(f"    全皈依+平衡 胜率: {r_d['team_win_rate']:.1f}%")
    print(f"    失败原因: 劫难={r_d['fail_reasons']['calamity']}, 渡化={r_d['fail_reasons']['save_count']}, 两者={r_d['fail_reasons']['both']}")
    print(f"    排名分: {out_d['rank_scores']}")
    print()

    # ---------- 方案E：折中（旱灾/洪水2，瘟疫3，国泰-2） ----------
    print("[6] 方案E：折中（旱灾/洪水2，瘟疫3，国泰-2）")
    cfg_e = BacktestConfig(seed=seed, num_sims=num_sims, configs=configs,
                          event_deck_factory=event_deck_middle, save_required=6)
    out_e = run_full_backtest(cfg_e)
    r_e = out_e["results_by_config"][0][1]
    print(f"    全皈依+平衡 胜率: {r_e['team_win_rate']:.1f}%")
    print(f"    失败原因: 劫难={r_e['fail_reasons']['calamity']}, 渡化={r_e['fail_reasons']['save_count']}, 两者={r_e['fail_reasons']['both']}")
    print(f"    排名分: {out_e['rank_scores']}")
    print()

    # ---------- 方案F：每轮劫难+1 ----------
    print("[7] 方案F：基线事件 + 每轮劫难+1")
    cfg_f = BacktestConfig(seed=seed, num_sims=num_sims, configs=configs,
                          event_deck_factory=default_event_deck, save_required=6, calamity_per_round=1)
    out_f = run_full_backtest(cfg_f)
    r_f = out_f["results_by_config"][0][1]
    print(f"    全皈依+平衡 胜率: {r_f['team_win_rate']:.1f}%")
    print(f"    失败原因: 劫难={r_f['fail_reasons']['calamity']}, 渡化={r_f['fail_reasons']['save_count']}, 两者={r_f['fail_reasons']['both']}")
    print(f"    排名分: {out_f['rank_scores']}")
    print()

    # ---------- 方案G：每轮劫难+2（强压力，预期出现劫难失败） ----------
    print("[8] 方案G：基线事件 + 每轮劫难+2")
    cfg_g = BacktestConfig(seed=seed, num_sims=num_sims, configs=configs,
                          event_deck_factory=default_event_deck, save_required=6, calamity_per_round=2)
    out_g = run_full_backtest(cfg_g)
    r_g = out_g["results_by_config"][0][1]
    print(f"    全皈依+平衡 胜率: {r_g['team_win_rate']:.1f}%")
    print(f"    失败原因: 劫难={r_g['fail_reasons']['calamity']}, 渡化={r_g['fail_reasons']['save_count']}, 两者={r_g['fail_reasons']['both']}")
    print(f"    排名分: {out_g['rank_scores']}")
    print()

    # ---------- 汇总与推荐 ----------
    print("=" * 70)
    print("汇总与推荐")
    print("=" * 70)
    total_fail_baseline = num_sims - r0["team_wins"]
    total_fail_a = num_sims - r_a["team_wins"]
    total_fail_b = num_sims - r_b["team_wins"]
    total_fail_c = num_sims - r_c["team_wins"]

    def pct_fail_calamity(res):
        tf = num_sims - res["team_wins"]
        return (res["fail_reasons"]["calamity"] + res["fail_reasons"]["both"]) / tf * 100 if tf else 0

    print(f"基线    胜率={r0['team_win_rate']:.1f}% 劫难失败%={pct_fail_calamity(r0):.1f}% 排名分={out_baseline['rank_scores']}")
    print(f"方案A   胜率={r_a['team_win_rate']:.1f}% 劫难失败%={pct_fail_calamity(r_a):.1f}% 排名分={out_a['rank_scores']}")
    print(f"方案B   胜率={r_b['team_win_rate']:.1f}% 劫难失败%={pct_fail_calamity(r_b):.1f}% 排名分={out_b['rank_scores']}")
    print(f"方案C   胜率={r_c['team_win_rate']:.1f}% 劫难失败%={pct_fail_calamity(r_c):.1f}% 排名分={out_c['rank_scores']}")
    print(f"方案D   胜率={r_d['team_win_rate']:.1f}% 劫难失败%={pct_fail_calamity(r_d):.1f}% 排名分={out_d['rank_scores']}")
    print(f"方案E   胜率={r_e['team_win_rate']:.1f}% 劫难失败%={pct_fail_calamity(r_e):.1f}% 排名分={out_e['rank_scores']}")
    print(f"方案F   胜率={r_f['team_win_rate']:.1f}% 劫难失败%={pct_fail_calamity(r_f):.1f}% 排名分={out_f['rank_scores']}")
    print(f"方案G   胜率={r_g['team_win_rate']:.1f}% 劫难失败%={pct_fail_calamity(r_g):.1f}% 排名分={out_g['rank_scores']}")

    # 推荐：优先满足「失败原因多样化」且胜率在 85–92%，其次看排名分
    best = "基线"
    best_score = -1
    for label, res, rank in [
        ("方案A", r_a, out_a["rank_scores"]),
        ("方案B", r_b, out_b["rank_scores"]),
        ("方案C", r_c, out_c["rank_scores"]),
        ("方案D", r_d, out_d["rank_scores"]),
        ("方案E", r_e, out_e["rank_scores"]),
        ("方案F", r_f, out_f["rank_scores"]),
        ("方案G", r_g, out_g["rank_scores"]),
    ]:
        pct_cal = pct_fail_calamity(res)
        # 得分：劫难失败占比 5–25% 为佳，胜率 85–92% 为佳，农夫排名分接近 0 为佳
        score = 0
        if 5 <= pct_cal <= 25:
            score += 2
        elif pct_cal > 0:
            score += 1
        if 85 <= res["team_win_rate"] <= 92:
            score += 2
        elif 80 <= res["team_win_rate"] <= 95:
            score += 1
        farmer_score = rank.get("农夫", 0)
        if abs(farmer_score) <= 2:
            score += 1
        if score > best_score:
            best_score = score
            best = label

    print()
    print(f"推荐采用: {best}（综合失败多样化、胜率、角色平衡）")
    if best == "方案A":
        print("事件卡 v3.6: 旱灾/洪水 calamity=1, 瘟疫 calamity=2, 国泰民安 calamity=-3")
        print("save_required=6 保持不变")
    elif best == "方案B":
        print("事件卡 v3.6: 同方案A")
        print("save_required=5（降低渡化门槛）")
    elif best == "方案C":
        print("事件卡 v3.6: 旱灾/洪水 calamity=2, 瘟疫 calamity=2, 国泰民安 calamity=-2")
        print("save_required=6 保持不变")
    elif best == "方案D":
        print("事件卡: 旱灾/洪水 calamity=3, 瘟疫 calamity=4, 国泰民安 calamity=-1（劫难压力大）")
        print("save_required=6 保持不变")
    elif best == "方案E":
        print("事件卡: 旱灾/洪水 calamity=2, 瘟疫 calamity=3, 国泰民安 calamity=-2（折中）")
        print("save_required=6 保持不变")
    elif best == "方案F":
        print("事件卡: 保持 v3.5 默认 + 每轮劫难+1（calamity_per_round=1）")
        print("save_required=6 保持不变")
    elif best == "方案G":
        print("事件卡: 保持 v3.5 默认 + 每轮劫难+2（calamity_per_round=2）")
        print("save_required=6 保持不变")
    print()
    # 保存数值结果供报告使用
    try:
        import json
        summary = {
            "num_sims": num_sims,
            "seed": seed,
            "baseline": {"win_rate": r0["team_win_rate"], "fail": r0["fail_reasons"], "rank": out_baseline["rank_scores"]},
            "plan_a": {"win_rate": r_a["team_win_rate"], "fail": r_a["fail_reasons"], "rank": out_a["rank_scores"]},
            "plan_b": {"win_rate": r_b["team_win_rate"], "fail": r_b["fail_reasons"], "rank": out_b["rank_scores"]},
            "plan_g": {"win_rate": r_g["team_win_rate"], "fail": r_g["fail_reasons"], "rank": out_g["rank_scores"]},
        }
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tuning_results_v36.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print("(结果已写入 tuning_results_v36.json)")
    except Exception as e:
        print("(写入 JSON 跳过:", e, ")")
    return out_baseline, out_a, out_b, out_c, out_d, out_e, out_f, out_g


if __name__ == "__main__":
    main()
