# -*- coding: utf-8 -*-
"""
v4.6 最终验证测试
"""

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, Tuple, List
from enum import Enum
import copy

class Role(Enum):
    FARMER = "农夫"
    MERCHANT = "商人"
    SCHOLAR = "学者"
    MONK = "僧侣"

class Vow(Enum):
    DILIGENT = "勤劳致福"
    POOR_GIRL = "贫女一灯"
    WEALTH = "财施功德"
    MERCHANT_HEART = "大商人之心"
    TEACH = "传道授业"
    TEACHER = "万世师表"
    ARHAT = "阿罗汉果"
    BODHISATTVA = "菩萨道"

# v4.6 配置
CONFIG = {
    # 初始资源
    "farmer": (5, 2, 2),      # 财, 福, 慧
    "merchant": (8, 1, 1),
    "scholar": (3, 2, 5),     # v4.5: 福+1, 慧+1
    "monk": (0, 4, 3),        # v4.5: 福+1
    
    # 被动
    "labor_farmer": 1,
    "practice_scholar": 2,     # v4.5: +2
    "donate_merchant": 2,      # v4.5: +2
    
    # 发愿条件
    "diligent_fu": 14,         # v4.6: 降低（移除每回合+1后）
    "poor_girl_fu": 18,        # v4.6: 降低
    "teach_hui": 16,
    "teacher_fu": 12,
    "teacher_hui": 18,
    "arhat_hui": 18,
    "bodhisattva_fu": 15,
    
    # 农夫发愿每回合奖励
    "farmer_vow_per_round": 0,  # v4.6核心: 移除
}

@dataclass
class Player:
    role: Role
    wealth: int = 0
    fu: int = 0
    hui: int = 0
    vow: Optional[Vow] = None
    faith: str = "secular"
    donate_count: int = 0
    save_count: int = 0

@dataclass 
class Being:
    cost: int
    fu: int
    hui: int
    stay: int = 0

def run_game():
    roles = list(Role)
    random.shuffle(roles)
    players = []
    
    for role in roles[:4]:
        p = Player(role=role)
        if role == Role.FARMER:
            p.wealth, p.fu, p.hui = CONFIG["farmer"]
        elif role == Role.MERCHANT:
            p.wealth, p.fu, p.hui = CONFIG["merchant"]
        elif role == Role.SCHOLAR:
            p.wealth, p.fu, p.hui = CONFIG["scholar"]
        else:
            p.wealth, p.fu, p.hui = CONFIG["monk"]
        
        # 信仰
        if role == Role.MONK:
            p.faith = random.choice(["small", "great"])
        else:
            p.faith = random.choices(["secular", "small", "great"], [0.3, 0.4, 0.3])[0]
        
        if p.faith == "secular":
            p.wealth += 4
        elif p.faith == "small":
            p.fu += 1
            p.hui += 1
        else:
            p.fu += 1
            p.hui += 2
            p.wealth -= 2
        
        # 发愿
        vow_map = {
            Role.FARMER: [Vow.DILIGENT, Vow.POOR_GIRL],
            Role.MERCHANT: [Vow.WEALTH, Vow.MERCHANT_HEART],
            Role.SCHOLAR: [Vow.TEACH, Vow.TEACHER],
            Role.MONK: [Vow.ARHAT, Vow.BODHISATTVA],
        }
        p.vow = random.choice(vow_map[role])
        players.append(p)
    
    beings = [Being(2,2,1), Being(2,2,1), Being(3,3,1), Being(3,2,2),
              Being(3,1,3), Being(4,2,2), Being(4,4,1), Being(5,3,3)]
    random.shuffle(beings)
    active = [beings.pop(), beings.pop()]
    calamity = 0
    saved = 0
    
    for round_num in range(1, 7):
        # 发愿奖励
        for p in players:
            if p.vow in [Vow.DILIGENT, Vow.POOR_GIRL]:
                p.fu += CONFIG["farmer_vow_per_round"]  # v4.6: 0
            elif p.vow == Vow.WEALTH:
                p.wealth += 1
            elif p.vow == Vow.BODHISATTVA:
                p.fu += 1
            else:
                p.hui += 1
        
        # 事件
        event = random.choices(["disaster", "misfortune", "blessing"], [0.45, 0.25, 0.3])[0]
        if event == "disaster":
            calamity += 4
            for p in players:
                if random.random() > 0.5:
                    p.wealth -= 2
                    p.fu += 1
                else:
                    p.wealth -= 1
        elif event == "misfortune":
            calamity += 3
        else:
            for p in players:
                p.fu += 1
                if p.faith != "secular":
                    p.fu += 1
        
        # 个人事件
        if round_num % 2 == 1:
            for p in players:
                if random.random() > 0.3:
                    p.fu += 1
                if random.random() > 0.5:
                    p.hui += 1
        
        # 众生
        for b in active:
            b.stay += 1
        for b in [x for x in active if x.stay >= 2]:
            calamity += 4
            active.remove(b)
        if beings:
            active.append(beings.pop())
        
        # 行动
        for p in players:
            for _ in range(2):
                if p.hui >= 5 and active:
                    affordable = [b for b in active if p.wealth >= max(1, b.cost - 1)]
                    if affordable:
                        b = min(affordable, key=lambda x: x.cost)
                        p.wealth -= max(1, b.cost - 1)
                        p.fu += b.fu
                        p.hui += b.hui
                        if p.faith != "secular":
                            p.fu += 1
                        if p.role == Role.MERCHANT and p.save_count == 0:
                            p.wealth += 2
                        active.remove(b)
                        saved += 1
                        p.save_count += 1
                        continue
                
                if p.vow == Vow.WEALTH and p.donate_count < 3 and p.wealth >= 2:
                    p.wealth -= 2
                    fu_gain = 2
                    if p.role == Role.MERCHANT:
                        fu_gain += CONFIG["donate_merchant"]
                    if p.faith != "secular":
                        fu_gain += 1
                    p.fu += fu_gain
                    p.donate_count += 1
                    calamity = max(0, calamity - 1)
                    continue
                
                if p.hui < 5:
                    gain = 2
                    if p.role == Role.SCHOLAR:
                        gain += CONFIG["practice_scholar"]
                    p.hui += gain
                    continue
                
                if p.wealth >= 2 and random.random() > 0.4:
                    p.wealth -= 2
                    fu_gain = 2
                    if p.role == Role.MERCHANT:
                        fu_gain += CONFIG["donate_merchant"]
                    if p.faith != "secular":
                        fu_gain += 1
                    p.fu += fu_gain
                    p.donate_count += 1
                    calamity = max(0, calamity - 1)
                    continue
                
                gain = 3
                if p.role == Role.FARMER:
                    gain += CONFIG["labor_farmer"]
                if p.faith == "secular":
                    gain += 1
                p.wealth += gain
        
        calamity += 1
        if round_num % 2 == 0:
            for p in players:
                if p.wealth >= 1:
                    p.wealth -= 1
                else:
                    p.fu -= 1
        
        if calamity >= 20:
            break
    
    team_win = calamity <= 12 and saved >= 5
    
    # 计分
    results = []
    for p in players:
        total = p.fu + p.hui
        if total < 10: base = 10
        elif total < 15: base = 15
        elif total < 20: base = 25
        elif total < 25: base = 35
        elif total < 30: base = 45
        elif total < 35: base = 55
        else: base = 65
        
        # 发愿奖惩
        vow_bonus = 0
        if team_win:
            if p.vow == Vow.DILIGENT:
                vow_bonus = 12 if p.fu >= CONFIG["diligent_fu"] else -4
            elif p.vow == Vow.POOR_GIRL:
                vow_bonus = 18 if p.fu >= CONFIG["poor_girl_fu"] and p.wealth <= 5 else -6
            elif p.vow == Vow.WEALTH:
                vow_bonus = 12 if p.donate_count >= 3 else -4
            elif p.vow == Vow.MERCHANT_HEART:
                vow_bonus = 16 if p.fu >= 16 and p.save_count >= 2 else -6
            elif p.vow == Vow.TEACH:
                vow_bonus = 12 if p.hui >= CONFIG["teach_hui"] else -4
            elif p.vow == Vow.TEACHER:
                vow_bonus = 16 if p.fu >= CONFIG["teacher_fu"] and p.hui >= CONFIG["teacher_hui"] else -6
            elif p.vow == Vow.ARHAT:
                vow_bonus = 12 if p.hui >= CONFIG["arhat_hui"] else -4
            elif p.vow == Vow.BODHISATTVA:
                vow_bonus = 18 if p.fu >= CONFIG["bodhisattva_fu"] and p.save_count >= 3 else -8
        
        score = base + vow_bonus if team_win else 0
        results.append({
            "role": p.role.value,
            "vow": p.vow.value,
            "fu": p.fu,
            "hui": p.hui,
            "score": score,
            "vow_bonus": vow_bonus,
        })
    
    winner = max(results, key=lambda x: x["score"]) if team_win else None
    return {"team_win": team_win, "winner": winner["role"] if winner else None, "players": results}

def simulate(n=5000):
    team_wins = 0
    role_wins = defaultdict(int)
    role_scores = defaultdict(list)
    vow_success = defaultdict(lambda: {"s": 0, "t": 0})
    
    for _ in range(n):
        r = run_game()
        if r["team_win"]:
            team_wins += 1
            if r["winner"]:
                role_wins[r["winner"]] += 1
        
        for p in r["players"]:
            role_scores[p["role"]].append(p["score"])
            vow_success[p["vow"]]["t"] += 1
            if p["vow_bonus"] > 0:
                vow_success[p["vow"]]["s"] += 1
    
    rates = {k: v / team_wins * 100 if team_wins > 0 else 0 for k, v in role_wins.items()}
    vals = [v for v in rates.values() if v > 0]
    diff = max(vals) - min(vals) if len(vals) >= 2 else 0
    
    return {
        "n": n,
        "team_win_rate": team_wins / n * 100,
        "role_win_rates": rates,
        "role_avg_scores": {k: sum(v)/len(v) if v else 0 for k, v in role_scores.items()},
        "diff": diff,
        "vow_rates": {k: v["s"]/v["t"]*100 if v["t"] > 0 else 0 for k, v in vow_success.items()},
    }

def main():
    print("=" * 65)
    print("《功德轮回》v4.6 最终验证测试")
    print("=" * 65)
    print()
    print("v4.6 核心改动:")
    print("  - 农夫发愿: 移除'每回合+1福'，改为降低达成条件")
    print("  - 勤劳致福: 福≥14 (原福≥15+每回合+1)")
    print("  - 贫女一灯: 福≥18 (原福≥20+每回合+1)")
    print("  - 商人布施: +2福 (原+1)")
    print("  - 学者修行: +2慧 (原+1)")
    print()
    
    r = simulate(10000)
    
    print(f"模拟局数: {r['n']}")
    print(f"团队胜率: {r['team_win_rate']:.1f}%")
    print()
    
    print("职业胜率:")
    print("-" * 40)
    for role in ["农夫", "商人", "学者", "僧侣"]:
        rate = r["role_win_rates"].get(role, 0)
        score = r["role_avg_scores"].get(role, 0)
        bar = "#" * int(rate / 2)
        print(f"  {role}: {rate:5.1f}% (平均{score:.1f}) {bar}")
    
    print(f"\n胜率差距: {r['diff']:.1f}%")
    
    print("\n发愿达成率:")
    print("-" * 40)
    for vow, rate in sorted(r["vow_rates"].items(), key=lambda x: x[1], reverse=True):
        bar = "#" * int(rate / 5)
        print(f"  {vow}: {rate:5.1f}% {bar}")
    
    print("\n" + "=" * 65)
    
    # 评估
    vals = list(r["role_win_rates"].values())
    max_v, min_v = max(vals), min(v for v in vals if v > 0)
    
    if r["diff"] < 10:
        print("✅ 平衡状态: 优秀 (差距<10%)")
    elif r["diff"] < 15:
        print("✅ 平衡状态: 良好 (差距<15%)")
    elif r["diff"] < 20:
        print("⚠️ 平衡状态: 尚可 (差距<20%)")
    else:
        print("❌ 平衡状态: 需改进 (差距≥20%)")
    
    farmer_vow_ok = r["vow_rates"].get("勤劳致福", 0) >= 50
    print(f"✅ 农夫发愿达成率合理" if farmer_vow_ok else "⚠️ 农夫发愿可能过难")
    
    print("=" * 65)

if __name__ == "__main__":
    main()
