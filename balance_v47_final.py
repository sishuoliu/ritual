# -*- coding: utf-8 -*-
"""
v4.7 最终平衡测试 - 基于方案B微调
"""

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from enum import Enum
import json

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

@dataclass
class Config:
    farmer: tuple = (5, 2, 2)
    merchant: tuple = (8, 1, 1)
    scholar: tuple = (3, 2, 4)
    monk: tuple = (0, 4, 3)
    labor_farmer: int = 1
    donate_merchant: int = 1
    practice_scholar: int = 1
    practice_monk: int = 0
    diligent_fu: int = 17
    poor_girl_fu: int = 22
    teach_hui: int = 16
    teacher_hui: int = 18
    arhat_hui: int = 18
    bodhisattva_fu: int = 16

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

class Sim:
    def __init__(self, c: Config):
        self.c = c
    
    def run(self):
        c = self.c
        roles = list(Role)
        random.shuffle(roles)
        players = []
        
        for role in roles[:4]:
            p = Player(role=role)
            if role == Role.FARMER:
                p.wealth, p.fu, p.hui = c.farmer
            elif role == Role.MERCHANT:
                p.wealth, p.fu, p.hui = c.merchant
            elif role == Role.SCHOLAR:
                p.wealth, p.fu, p.hui = c.scholar
            else:
                p.wealth, p.fu, p.hui = c.monk
            
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
            for p in players:
                if p.vow in [Vow.DILIGENT, Vow.POOR_GIRL]:
                    p.fu += 1  # 保留农夫每回合+1福
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
                        fu = 2 + (c.donate_merchant if p.role == Role.MERCHANT else 0)
                        if p.faith != "secular":
                            fu += 1
                        p.fu += fu
                        p.donate_count += 1
                        calamity = max(0, calamity - 1)
                        continue
                    
                    if p.hui < 5:
                        gain = 2
                        if p.role == Role.SCHOLAR:
                            gain += c.practice_scholar
                        if p.role == Role.MONK:
                            gain += c.practice_monk
                        p.hui += gain
                        continue
                    
                    if p.wealth >= 2 and random.random() > 0.4:
                        p.wealth -= 2
                        fu = 2 + (c.donate_merchant if p.role == Role.MERCHANT else 0)
                        if p.faith != "secular":
                            fu += 1
                        p.fu += fu
                        p.donate_count += 1
                        calamity = max(0, calamity - 1)
                        continue
                    
                    gain = 3 + (c.labor_farmer if p.role == Role.FARMER else 0)
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
                    vb = 12 if p.fu >= c.diligent_fu else -4
                elif p.vow == Vow.POOR_GIRL:
                    vb = 18 if p.fu >= c.poor_girl_fu and p.wealth <= 5 else -6
                elif p.vow == Vow.WEALTH:
                    vb = 12 if p.donate_count >= 3 else -4
                elif p.vow == Vow.MERCHANT_HEART:
                    vb = 16 if p.fu >= 16 and p.save_count >= 2 else -6
                elif p.vow == Vow.TEACH:
                    vb = 12 if p.hui >= c.teach_hui else -4
                elif p.vow == Vow.TEACHER:
                    vb = 16 if p.fu >= 12 and p.hui >= c.teacher_hui else -6
                elif p.vow == Vow.ARHAT:
                    vb = 12 if p.hui >= c.arhat_hui else -4
                elif p.vow == Vow.BODHISATTVA:
                    vb = 18 if p.fu >= c.bodhisattva_fu and p.save_count >= 3 else -8
            
            res.append({"role": p.role.value, "vow": p.vow.value, "fu": p.fu, "hui": p.hui, "score": base + vb if win else 0, "vb": vb})
        
        winner = max(res, key=lambda x: x["score"]) if win else None
        return {"win": win, "winner": winner["role"] if winner else None, "res": res}
    
    def sim(self, n=10000):
        tw = 0
        rw = defaultdict(int)
        vs = defaultdict(lambda: [0, 0])
        scores = defaultdict(list)
        
        for _ in range(n):
            r = self.run()
            if r["win"]:
                tw += 1
                if r["winner"]:
                    rw[r["winner"]] += 1
            for p in r["res"]:
                vs[p["vow"]][1] += 1
                if p["vb"] > 0:
                    vs[p["vow"]][0] += 1
                scores[p["role"]].append(p["score"])
        
        rates = {k: v / tw * 100 if tw > 0 else 0 for k, v in rw.items()}
        vals = [v for v in rates.values() if v > 0]
        diff = max(vals) - min(vals) if len(vals) >= 2 else 0
        vow = {k: v[0]/v[1]*100 if v[1] > 0 else 0 for k, v in vs.items()}
        avg = {k: sum(v)/len(v) if v else 0 for k, v in scores.items()}
        
        return {"tw": tw/n*100, "rates": rates, "diff": diff, "vow": vow, "avg": avg}

def t(name, c, n=10000):
    r = Sim(c).sim(n)
    return name, c, r

def main():
    print("=" * 70)
    print("v4.7 最终平衡测试 - 保留农夫每回合+1福")
    print("=" * 70)
    
    # 基于方案B微调
    configs = [
        # 方案B基线
        ("B基线", Config(
            diligent_fu=24, poor_girl_fu=30,
            merchant=(8, 2, 1), scholar=(4, 2, 5), monk=(1, 5, 5),
            donate_merchant=2, practice_scholar=2, arhat_hui=14,
        )),
        
        # 微调1: 略降低农夫条件
        ("B-1: 农夫-1", Config(
            diligent_fu=23, poor_girl_fu=29,
            merchant=(8, 2, 1), scholar=(4, 2, 5), monk=(1, 5, 5),
            donate_merchant=2, practice_scholar=2, arhat_hui=14,
        )),
        
        # 微调2: 略提高僧侣
        ("B-2: 僧侣+", Config(
            diligent_fu=24, poor_girl_fu=30,
            merchant=(8, 2, 1), scholar=(4, 2, 5), monk=(1, 6, 5),
            donate_merchant=2, practice_scholar=2, arhat_hui=14, bodhisattva_fu=14,
        )),
        
        # 微调3: 略提高商人
        ("B-3: 商人+", Config(
            diligent_fu=24, poor_girl_fu=30,
            merchant=(9, 2, 1), scholar=(4, 2, 5), monk=(1, 5, 5),
            donate_merchant=2, practice_scholar=2, arhat_hui=14,
        )),
        
        # 微调4: 略降低学者
        ("B-4: 学者-", Config(
            diligent_fu=24, poor_girl_fu=30,
            merchant=(8, 2, 1), scholar=(3, 2, 5), monk=(1, 5, 5),
            donate_merchant=2, practice_scholar=2, arhat_hui=14,
        )),
        
        # 组合微调
        ("B-5: 综合", Config(
            diligent_fu=23, poor_girl_fu=29,
            merchant=(8, 2, 1), scholar=(4, 2, 5), monk=(1, 6, 5),
            donate_merchant=2, practice_scholar=2, arhat_hui=14, bodhisattva_fu=14,
        )),
        
        # 进一步平衡
        ("B-6: 深度", Config(
            diligent_fu=23, poor_girl_fu=29,
            merchant=(9, 2, 1), scholar=(3, 2, 5), monk=(1, 6, 5),
            donate_merchant=2, practice_scholar=2, arhat_hui=14, bodhisattva_fu=14,
        )),
        
        # 最终方案
        ("B-7: 最终", Config(
            diligent_fu=24, poor_girl_fu=30,
            merchant=(8, 2, 2), scholar=(4, 2, 5), monk=(1, 5, 5),
            donate_merchant=2, practice_scholar=2, arhat_hui=14, bodhisattva_fu=14,
        )),
    ]
    
    results = []
    for name, c, n in [t(n, c, 15000) for n, c in configs]:
        results.append((name, c, n))
    
    print("\n" + "=" * 70)
    print(f"{'配置':<12} {'差距':>6} {'农夫':>6} {'商人':>6} {'学者':>6} {'僧侣':>6} {'勤劳':>6} {'阿罗汉':>6}")
    print("-" * 70)
    
    for name, c, r in results:
        ra = r["rates"]
        vo = r["vow"]
        print(f"{name:<12} {r['diff']:>5.1f}% {ra.get('农夫',0):>5.0f}% {ra.get('商人',0):>5.0f}% {ra.get('学者',0):>5.0f}% {ra.get('僧侣',0):>5.0f}% {vo.get('勤劳致福',0):>5.0f}% {vo.get('阿罗汉果',0):>5.0f}%")
    
    # 找最佳
    best = min(results, key=lambda x: x[2]["diff"])
    
    print("\n" + "=" * 70)
    print(f"推荐配置: {best[0]}")
    print("=" * 70)
    
    c = best[1]
    r = best[2]
    
    print(f"\n初始资源:")
    print(f"  农夫: 财{c.farmer[0]}, 福{c.farmer[1]}, 慧{c.farmer[2]}")
    print(f"  商人: 财{c.merchant[0]}, 福{c.merchant[1]}, 慧{c.merchant[2]}")
    print(f"  学者: 财{c.scholar[0]}, 福{c.scholar[1]}, 慧{c.scholar[2]}")
    print(f"  僧侣: 财{c.monk[0]}, 福{c.monk[1]}, 慧{c.monk[2]}")
    
    print(f"\n被动技能:")
    print(f"  农夫劳作: +{c.labor_farmer} 财富")
    print(f"  商人布施: +{c.donate_merchant} 福")
    print(f"  学者修行: +{c.practice_scholar} 慧")
    print(f"  僧侣修行: +{c.practice_monk} 慧")
    
    print(f"\n发愿条件:")
    print(f"  勤劳致福: 福≥{c.diligent_fu}")
    print(f"  贫女一灯: 福≥{c.poor_girl_fu} 且 财≤5")
    print(f"  传道授业: 慧≥{c.teach_hui}")
    print(f"  万世师表: 福≥12 且 慧≥{c.teacher_hui}")
    print(f"  阿罗汉果: 慧≥{c.arhat_hui}")
    print(f"  菩萨道:   福≥{c.bodhisattva_fu} 且 渡化≥3")
    
    print(f"\n平衡结果:")
    ra = r["rates"]
    vo = r["vow"]
    print(f"  职业胜率差距: {r['diff']:.1f}%")
    print(f"  农夫: {ra.get('农夫',0):.1f}%")
    print(f"  商人: {ra.get('商人',0):.1f}%")
    print(f"  学者: {ra.get('学者',0):.1f}%")
    print(f"  僧侣: {ra.get('僧侣',0):.1f}%")
    
    print(f"\n发愿达成率:")
    for v, rate in sorted(vo.items(), key=lambda x: x[1], reverse=True):
        print(f"  {v}: {rate:.1f}%")
    
    # 保存
    final = {
        "version": "v4.7",
        "description": "保留农夫每回合+1福，通过提高发愿条件+增强其他职业实现平衡",
        "config": {
            "farmer": c.farmer,
            "merchant": c.merchant,
            "scholar": c.scholar,
            "monk": c.monk,
            "labor_farmer": c.labor_farmer,
            "donate_merchant": c.donate_merchant,
            "practice_scholar": c.practice_scholar,
            "practice_monk": c.practice_monk,
            "diligent_fu": c.diligent_fu,
            "poor_girl_fu": c.poor_girl_fu,
            "teach_hui": c.teach_hui,
            "teacher_hui": c.teacher_hui,
            "arhat_hui": c.arhat_hui,
            "bodhisattva_fu": c.bodhisattva_fu,
        },
        "result": {
            "diff": r["diff"],
            "rates": r["rates"],
            "vow": r["vow"],
        }
    }
    
    with open("balance_v47_recommended.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n配置已保存到 balance_v47_recommended.json")

if __name__ == "__main__":
    main()
