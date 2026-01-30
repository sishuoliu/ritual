# -*- coding: utf-8 -*-
"""v4.7 最终验证"""

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from enum import Enum

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

# v4.7 最终配置
CONFIG = {
    "farmer": (5, 2, 2),
    "merchant": (9, 2, 1),
    "scholar": (4, 2, 5),
    "monk": (1, 5, 5),
    "labor_farmer": 1,
    "donate_merchant": 2,
    "practice_scholar": 2,
    "diligent_fu": 24,
    "poor_girl_fu": 30,
    "arhat_hui": 14,
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
    c = CONFIG
    roles = list(Role)
    random.shuffle(roles)
    players = []
    
    for role in roles[:4]:
        p = Player(role=role)
        if role == Role.FARMER:
            p.wealth, p.fu, p.hui = c["farmer"]
        elif role == Role.MERCHANT:
            p.wealth, p.fu, p.hui = c["merchant"]
        elif role == Role.SCHOLAR:
            p.wealth, p.fu, p.hui = c["scholar"]
        else:
            p.wealth, p.fu, p.hui = c["monk"]
        
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
    
    for rnd in range(1, 7):
        # 发愿奖励 - 农夫保留每回合+1福
        for p in players:
            if p.vow in [Vow.DILIGENT, Vow.POOR_GIRL]:
                p.fu += 1
            elif p.vow == Vow.WEALTH:
                p.wealth += 1
            elif p.vow == Vow.BODHISATTVA:
                p.fu += 1
            else:
                p.hui += 1
        
        ev = random.choices(["d", "m", "b"], [0.45, 0.25, 0.3])[0]
        if ev == "d":
            calamity += 4
            for p in players:
                if random.random() > 0.5:
                    p.wealth -= 2
                    p.fu += 1
                else:
                    p.wealth -= 1
        elif ev == "m":
            calamity += 3
        else:
            for p in players:
                p.fu += 1
                if p.faith != "secular":
                    p.fu += 1
        
        if rnd % 2 == 1:
            for p in players:
                if random.random() > 0.3:
                    p.fu += 1
                if random.random() > 0.5:
                    p.hui += 1
        
        for b in active:
            b.stay += 1
        for b in [x for x in active if x.stay >= 2]:
            calamity += 4
            active.remove(b)
        if beings:
            active.append(beings.pop())
        
        for p in players:
            for _ in range(2):
                if p.hui >= 5 and active:
                    aff = [b for b in active if p.wealth >= max(1, b.cost - 1)]
                    if aff:
                        b = min(aff, key=lambda x: x.cost)
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
                    fu = 2 + (c["donate_merchant"] if p.role == Role.MERCHANT else 0)
                    if p.faith != "secular":
                        fu += 1
                    p.fu += fu
                    p.donate_count += 1
                    calamity = max(0, calamity - 1)
                    continue
                
                if p.hui < 5:
                    gain = 2 + (c["practice_scholar"] if p.role == Role.SCHOLAR else 0)
                    p.hui += gain
                    continue
                
                if p.wealth >= 2 and random.random() > 0.4:
                    p.wealth -= 2
                    fu = 2 + (c["donate_merchant"] if p.role == Role.MERCHANT else 0)
                    if p.faith != "secular":
                        fu += 1
                    p.fu += fu
                    p.donate_count += 1
                    calamity = max(0, calamity - 1)
                    continue
                
                gain = 3 + (c["labor_farmer"] if p.role == Role.FARMER else 0)
                if p.faith == "secular":
                    gain += 1
                p.wealth += gain
        
        calamity += 1
        if rnd % 2 == 0:
            for p in players:
                if p.wealth >= 1:
                    p.wealth -= 1
                else:
                    p.fu -= 1
        
        if calamity >= 20:
            break
    
    win = calamity <= 12 and saved >= 5
    
    res = []
    for p in players:
        t = p.fu + p.hui
        if t < 10: base = 10
        elif t < 15: base = 15
        elif t < 20: base = 25
        elif t < 25: base = 35
        elif t < 30: base = 45
        elif t < 35: base = 55
        else: base = 65
        
        vb = 0
        if win:
            if p.vow == Vow.DILIGENT:
                vb = 12 if p.fu >= c["diligent_fu"] else -4
            elif p.vow == Vow.POOR_GIRL:
                vb = 18 if p.fu >= c["poor_girl_fu"] and p.wealth <= 5 else -6
            elif p.vow == Vow.WEALTH:
                vb = 12 if p.donate_count >= 3 else -4
            elif p.vow == Vow.MERCHANT_HEART:
                vb = 16 if p.fu >= 16 and p.save_count >= 2 else -6
            elif p.vow == Vow.TEACH:
                vb = 12 if p.hui >= 16 else -4
            elif p.vow == Vow.TEACHER:
                vb = 16 if p.fu >= 12 and p.hui >= 18 else -6
            elif p.vow == Vow.ARHAT:
                vb = 12 if p.hui >= c["arhat_hui"] else -4
            elif p.vow == Vow.BODHISATTVA:
                vb = 18 if p.fu >= 16 and p.save_count >= 3 else -8
        
        res.append({"role": p.role.value, "vow": p.vow.value, "score": base + vb if win else 0, "vb": vb})
    
    winner = max(res, key=lambda x: x["score"]) if win else None
    return {"win": win, "winner": winner["role"] if winner else None, "res": res}

def main():
    print("=" * 65)
    print("《功德轮回》v4.7 最终验证")
    print("=" * 65)
    print()
    print("v4.7 配置:")
    print("  农夫: 财5,福2,慧2 | 劳作+1 | 发愿每回合+1福")
    print("  商人: 财9,福2,慧1 | 布施+2福")
    print("  学者: 财4,福2,慧5 | 修行+2慧")
    print("  僧侣: 财1,福5,慧5")
    print()
    print("  勤劳致福: 福≥24")
    print("  贫女一灯: 福≥30 且 财≤5")
    print("  阿罗汉果: 慧≥14")
    print()
    
    n = 20000
    tw = 0
    rw = defaultdict(int)
    vs = defaultdict(lambda: [0, 0])
    
    for _ in range(n):
        r = run_game()
        if r["win"]:
            tw += 1
            if r["winner"]:
                rw[r["winner"]] += 1
        for p in r["res"]:
            vs[p["vow"]][1] += 1
            if p["vb"] > 0:
                vs[p["vow"]][0] += 1
    
    rates = {k: v / tw * 100 if tw > 0 else 0 for k, v in rw.items()}
    vals = [v for v in rates.values() if v > 0]
    diff = max(vals) - min(vals) if len(vals) >= 2 else 0
    
    print(f"模拟局数: {n}")
    print(f"团队胜率: {tw/n*100:.1f}%")
    print()
    print("职业胜率:")
    print("-" * 40)
    for role in ["农夫", "商人", "学者", "僧侣"]:
        rate = rates.get(role, 0)
        bar = "#" * int(rate / 2)
        print(f"  {role}: {rate:5.1f}% {bar}")
    
    print(f"\n职业胜率差距: {diff:.1f}%")
    
    print("\n发愿达成率:")
    print("-" * 40)
    vow_rates = {k: v[0]/v[1]*100 if v[1] > 0 else 0 for k, v in vs.items()}
    for vow, rate in sorted(vow_rates.items(), key=lambda x: x[1], reverse=True):
        bar = "#" * int(rate / 5)
        print(f"  {vow}: {rate:5.1f}% {bar}")
    
    print("\n" + "=" * 65)
    if diff < 10:
        print("✅ 平衡状态: 优秀 (差距<10%)")
    elif diff < 15:
        print("✅ 平衡状态: 良好 (差距<15%)")
    else:
        print("⚠️ 平衡状态: 需改进 (差距≥15%)")
    print("=" * 65)

if __name__ == "__main__":
    main()
