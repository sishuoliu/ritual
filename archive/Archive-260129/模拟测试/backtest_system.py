# -*- coding: utf-8 -*-
"""
《功德轮回》完善回测系统 v1.0

设计目标：
- 更完善：种子可复现、多情景、失败原因细分、事件卡参数化
- 更真实：玩家顺序轮转、多策略组合、事件牌序/众生牌序随机
- 支持：敏感性分析、事件卡微调、跨机制平衡调试

参考：Monte Carlo 可复现性、多策略/偏置测试、限制性对局评估
"""

import random
import math
import json
import copy
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

# 从主模拟器导入（文件名含点，用 importlib）
import importlib.util
import os
_sim_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_simulator_v3.5_final.py")
_spec = importlib.util.spec_from_file_location("sim", _sim_path)
_sim = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sim)
GameSimulator = _sim.GameSimulator
RoleType = _sim.RoleType
Strategy = _sim.Strategy
RefugeChoice = _sim.RefugeChoice
SHARED_EVENTS = getattr(_sim, "SHARED_EVENTS", [])
SENTIENT_BEINGS = getattr(_sim, "SENTIENT_BEINGS", [])
SentientBeing = _sim.SentientBeing


# ========== 事件卡参数化（可调） ==========
def default_event_deck() -> List[Dict]:
    """默认事件牌（与 v3.5 一致），返回可修改的副本"""
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


def tuned_event_deck_v36() -> List[Dict]:
    """v3.6 微调：减轻负面事件、略增强正面，使失败原因不再 100% 渡化不足"""
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


# ========== 回测配置 ==========
@dataclass
class BacktestConfig:
    seed: Optional[int] = None
    num_sims: int = 1000
    configs: List[Tuple[str, List[Strategy], List[RefugeChoice]]] = field(default_factory=list)
    event_deck_factory: Any = None  # callable() -> list of event dicts
    save_required: Optional[int] = None
    max_rounds: Optional[int] = None
    calamity_limit: Optional[int] = None
    calamity_per_round: int = 0  # 每轮劫难增加值（用于使劫难失败能出现）
    multi_seed_count: int = 0  # 0 = single run with seed; >0 = run with N seeds for variance
    trace_rounds: bool = False  # 是否输出少数对局的回合轨迹（调试用）


def _default_configs() -> List[Tuple[str, List[Strategy], List[RefugeChoice]]]:
    return [
        ("全皈依+平衡", [Strategy.BALANCED]*4, [RefugeChoice.REFUGE]*4),
        ("全不皈依+平衡", [Strategy.BALANCED]*4, 
         [RefugeChoice.NON_REFUGE, RefugeChoice.NON_REFUGE, RefugeChoice.NON_REFUGE, RefugeChoice.REFUGE]),
        ("商人财富策略", [Strategy.BALANCED, Strategy.WEALTH_FOCUS, Strategy.BALANCED, Strategy.BALANCED], [RefugeChoice.REFUGE]*4),
        ("农夫福德策略", [Strategy.MERIT_FOCUS, Strategy.BALANCED, Strategy.BALANCED, Strategy.BALANCED], [RefugeChoice.REFUGE]*4),
        ("学者智慧策略", [Strategy.BALANCED, Strategy.BALANCED, Strategy.WISDOM_FOCUS, Strategy.BALANCED], [RefugeChoice.REFUGE]*4),
        ("僧侣福德策略", [Strategy.BALANCED, Strategy.BALANCED, Strategy.BALANCED, Strategy.MERIT_FOCUS], [RefugeChoice.REFUGE]*4),
    ]


# ========== 单次运行（带种子） ==========
def run_single_backtest(
    strategies: List[Strategy],
    refuges: List[RefugeChoice],
    num_sims: int,
    seed: Optional[int] = None,
    event_deck: Optional[List[Dict]] = None,
    save_required: Optional[int] = None,
    max_rounds: Optional[int] = None,
    calamity_limit: Optional[int] = None,
    calamity_per_round: int = 0,
) -> Dict:
    rng = random.Random(seed)
    role_stats = {role: {
        "wins": 0.0, "scores": [], "fu": [], "hui": [], "wealth": [],
        "vow_success": 0, "save": [], "donate": [], "starve": [],
    } for role in RoleType}
    team_wins = 0
    fail_reasons = {"calamity": 0, "save_count": 0, "both": 0}
    final_calamity = []
    final_saved = []

    for _ in range(num_sims):
        sim = GameSimulator(
            strategies=strategies,
            refuges=refuges,
            event_effects=event_deck,
            save_required=save_required,
            max_rounds=max_rounds,
            calamity_limit=calamity_limit,
            calamity_per_round=calamity_per_round,
            rng=rng,
        )
        team_win, results = sim.run_game()
        final_calamity.append(sim.state.calamity)
        final_saved.append(sim.state.saved_count)

        if team_win:
            team_wins += 1
            max_score = max(r["score"] for r in results)
            winners = [i for i, r in enumerate(results) if r["score"] == max_score]
            for i, r in enumerate(results):
                role = r["role"]
                role_stats[role]["scores"].append(r["score"])
                role_stats[role]["fu"].append(r["fu"])
                role_stats[role]["hui"].append(r["hui"])
                role_stats[role]["wealth"].append(r["wealth"])
                if r["vow_success"]:
                    role_stats[role]["vow_success"] += 1
                if i in winners:
                    role_stats[role]["wins"] += 1.0 / len(winners)
                role_stats[role]["save"].append(r["save_count"])
                role_stats[role]["donate"].append(r["donate_count"])
                role_stats[role]["starve"].append(r["starve_count"])
        else:
            c_fail = sim.state.calamity > 12
            s_fail = sim.state.saved_count < sim.state.save_required
            if c_fail and s_fail:
                fail_reasons["both"] += 1
            elif c_fail:
                fail_reasons["calamity"] += 1
            else:
                fail_reasons["save_count"] += 1

    total_fail = num_sims - team_wins
    return {
        "team_wins": team_wins,
        "team_win_rate": team_wins / num_sims * 100,
        "role_stats": role_stats,
        "fail_reasons": fail_reasons,
        "fail_calamity_pct": fail_reasons["calamity"] / total_fail * 100 if total_fail else 0,
        "fail_save_pct": fail_reasons["save_count"] / total_fail * 100 if total_fail else 0,
        "fail_both_pct": fail_reasons["both"] / total_fail * 100 if total_fail else 0,
        "final_calamity_mean": sum(final_calamity) / len(final_calamity),
        "final_calamity_std": _std(final_calamity),
        "final_saved_mean": sum(final_saved) / len(final_saved),
        "final_saved_std": _std(final_saved),
    }


def _std(lst: List[float]) -> float:
    if len(lst) < 2:
        return 0
    m = sum(lst) / len(lst)
    return math.sqrt(sum((x - m) ** 2 for x in lst) / len(lst))


def _median(lst: List[float]) -> float:
    if not lst:
        return 0
    s = sorted(lst)
    n = len(s)
    if n % 2 == 0:
        return (s[n//2 - 1] + s[n//2]) / 2
    return s[n//2]


# ========== 综合排名分 ==========
def compute_rank_scores(all_results: List[Tuple[str, Dict]]) -> Dict[RoleType, int]:
    rank_points = [+2, +1, -1, -2]
    role_total = {role: 0 for role in RoleType}
    for name, res in all_results:
        if res["team_wins"] <= 0:
            continue
        win_rates = [(role, res["role_stats"][role]["wins"] / res["team_wins"] * 100) 
                     for role in RoleType]
        sorted_rates = sorted(win_rates, key=lambda x: x[1], reverse=True)
        for i, (role, _) in enumerate(sorted_rates):
            role_total[role] += rank_points[i]
    return role_total


# ========== 主入口：完整回测 ==========
def run_full_backtest(config: Optional[BacktestConfig] = None) -> Dict:
    config = config or BacktestConfig()
    if not config.configs:
        config.configs = _default_configs()
    _deck = config.event_deck_factory or default_event_deck
    event_deck = _deck() if callable(_deck) else _deck
    event_deck = copy.deepcopy(event_deck) if event_deck else default_event_deck()

    all_results = []
    seeds_used = [config.seed] if config.multi_seed_count <= 0 else [
        (config.seed + i) if config.seed is not None else None for i in range(config.multi_seed_count)
    ]

    for seed in seeds_used:
        for name, strategies, refuges in config.configs:
            res = run_single_backtest(
                strategies=strategies,
                refuges=refuges,
                num_sims=config.num_sims,
                seed=seed,
                event_deck=event_deck,
                save_required=config.save_required,
                max_rounds=config.max_rounds,
                calamity_limit=config.calamity_limit,
                calamity_per_round=getattr(config, "calamity_per_round", 0),
            )
            all_results.append((name, res))

    # 若多种子，这里简化：只取第一个种子的各配置结果做排名分；多种子时可对 win_rate 取均值和方差
    rank_scores = compute_rank_scores(all_results[: len(config.configs)])

    return {
        "config": {
            "seed": config.seed,
            "num_sims": config.num_sims,
            "event_deck": event_deck,
            "save_required": config.save_required,
            "max_rounds": config.max_rounds,
        },
        "results_by_config": [(n, r) for n, r in all_results],
        "rank_scores": {r.value: rank_scores[r] for r in RoleType},
    }


# ========== 敏感性分析：单参数扫描 ==========
def run_sensitivity(
    param_name: str,
    param_values: List[Any],
    base_config: BacktestConfig,
    config_name: str = "全皈依+平衡",
) -> List[Dict]:
    """对 param_name 扫描 param_values，返回每组 win_rate 与 fail_reasons"""
    base_config.configs = base_config.configs or _default_configs()
    name, strategies, refuges = base_config.configs[0]
    event_deck_factory = base_config.event_deck_factory or default_event_deck
    out = []
    for v in param_values:
        if param_name == "save_required":
            res = run_single_backtest(strategies, refuges, base_config.num_sims, base_config.seed,
                                      event_deck_factory() if callable(event_deck_factory) else event_deck_factory,
                                      save_required=v, max_rounds=base_config.max_rounds, calamity_limit=base_config.calamity_limit)
        elif param_name == "event_calamity_negative":
            deck = event_deck_factory() if callable(event_deck_factory) else event_deck_factory
            deck = copy.deepcopy(deck)
            for e in deck:
                if e.get("name") in ("旱灾", "洪水") and "calamity" in e.get("effect", {}):
                    e["effect"] = {**e["effect"], "calamity": v}
            res = run_single_backtest(strategies, refuges, base_config.num_sims, base_config.seed,
                                      deck, base_config.save_required, base_config.max_rounds, base_config.calamity_limit)
        else:
            continue
        out.append({"param_value": v, "win_rate": res["team_win_rate"], "fail_reasons": res["fail_reasons"]})
    return out


if __name__ == "__main__":
    # 快速验证
    cfg = BacktestConfig(seed=42, num_sims=200, configs=_default_configs())
    summary = run_full_backtest(cfg)
    print("Win rates (first config):", summary["results_by_config"][0][1]["team_win_rate"])
    print("Rank scores:", summary["rank_scores"])
    print("Fail reasons (first):", summary["results_by_config"][0][1]["fail_reasons"])
