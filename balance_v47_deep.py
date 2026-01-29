# -*- coding: utf-8 -*-
"""
《功德轮回》v4.7 深度迭代 - 保留农夫每回合+1福
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
    practice_monk: int = 0  # 僧侣修行额外慧
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
            
            # 事件
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
            
            res.append({"role": p.role.value, "vow": p.vow.value, "score": base + vb if win else 0, "vb": vb})
        
        winner = max(res, key=lambda x: x["score"]) if win else None
        return {"win": win, "winner": winner["role"] if winner else None, "res": res}
    
    def sim(self, n=5000):
        tw = 0
        rw = defaultdict(int)
        vs = defaultdict(lambda: [0, 0])
        
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
        
        rates = {k: v / tw * 100 if tw > 0 else 0 for k, v in rw.items()}
        vals = [v for v in rates.values() if v > 0]
        diff = max(vals) - min(vals) if len(vals) >= 2 else 0
        vow = {k: v[0]/v[1]*100 if v[1] > 0 else 0 for k, v in vs.items()}
        
        return {"tw": tw/n*100, "rates": rates, "diff": diff, "vow": vow}

def t(name, c, n=5000):
    r = Sim(c).sim(n)
    ra = r["rates"]
    vo = r["vow"]
    print(f"{name}")
    print(f"  差距{r['diff']:5.1f}% | 农{ra.get('农夫',0):4.0f} 商{ra.get('商人',0):4.0f} 学{ra.get('学者',0):4.0f} 僧{ra.get('僧侣',0):4.0f}")
    print(f"  勤{vo.get('勤劳致福',0):3.0f} 贫{vo.get('贫女一灯',0):3.0f} 财{vo.get('财施功德',0):3.0f} 传{vo.get('传道授业',0):3.0f} 阿{vo.get('阿罗汉果',0):3.0f} 菩{vo.get('菩萨道',0):3.0f}")
    return r

def main():
    print("=" * 70)
    print("v4.7 深度迭代 - 保留农夫每回合+1福")
    print("=" * 70)
    
    # 基线
    t("[基线]", Config())
    
    # 核心问题：农夫发愿每回合+1福，6回合=6福
    # 解决方案：大幅提高条件 + 增强其他职业
    
    print("\n--- 提高农夫发愿条件 ---")
    for fu in range(20, 29, 2):
        t(f"[勤劳≥{fu}]", Config(diligent_fu=fu, poor_girl_fu=fu+6))
    
    print("\n--- 增强僧侣（阿罗汉过难）---")
    t("[阿罗汉≥16]", Config(arhat_hui=16))
    t("[阿罗汉≥14]", Config(arhat_hui=14))
    t("[阿罗汉≥14 + 僧侣修行+1]", Config(arhat_hui=14, practice_monk=1))
    t("[僧侣(1,5,4)]", Config(monk=(1, 5, 4)))
    t("[僧侣(1,5,5)]", Config(monk=(1, 5, 5)))
    
    print("\n--- 增强商人 ---")
    t("[布施+2]", Config(donate_merchant=2))
    t("[布施+3]", Config(donate_merchant=3))
    t("[商人(8,2,1) + 布施+2]", Config(merchant=(8, 2, 1), donate_merchant=2))
    
    print("\n--- 增强学者 ---")
    t("[修行+2]", Config(practice_scholar=2))
    t("[修行+3]", Config(practice_scholar=3))
    t("[学者(4,2,5) + 修行+2]", Config(scholar=(4, 2, 5), practice_scholar=2))
    t("[传道≥14]", Config(teach_hui=14))
    
    print("\n--- 综合方案 ---")
    
    # 方案A: 适度提高农夫 + 小幅增强其他
    ca = Config(
        diligent_fu=22, poor_girl_fu=28,
        donate_merchant=2, practice_scholar=2,
        arhat_hui=14, monk=(1, 5, 4),
    )
    t("[A] 农夫+5, 其他小增", ca)
    
    # 方案B: 大幅提高农夫 + 中度增强其他
    cb = Config(
        diligent_fu=24, poor_girl_fu=30,
        donate_merchant=2, practice_scholar=2,
        merchant=(8, 2, 1), scholar=(4, 2, 5),
        arhat_hui=14, monk=(1, 5, 5),
    )
    t("[B] 农夫+7, 其他中增", cb)
    
    # 方案C: 极端提高农夫 + 大幅增强其他
    cc = Config(
        diligent_fu=26, poor_girl_fu=32,
        donate_merchant=3, practice_scholar=3,
        merchant=(8, 3, 1), scholar=(4, 3, 6),
        arhat_hui=12, practice_monk=1, monk=(1, 6, 5),
        teach_hui=14, teacher_hui=16, bodhisattva_fu=14,
    )
    t("[C] 农夫+9, 其他大增", cc)
    
    # 方案D: 最激进
    cd = Config(
        diligent_fu=28, poor_girl_fu=34,
        donate_merchant=3, practice_scholar=3,
        merchant=(9, 3, 2), scholar=(5, 3, 6),
        arhat_hui=12, practice_monk=2, monk=(2, 6, 5),
        teach_hui=12, teacher_hui=14, bodhisattva_fu=12,
    )
    t("[D] 极端方案", cd)
    
    print("\n" + "=" * 70)
    print("10000局精确测试")
    print("=" * 70)
    
    configs = [
        ("[A] 农夫+5", ca),
        ("[B] 农夫+7", cb),
        ("[C] 农夫+9", cc),
        ("[D] 极端", cd),
    ]
    
    best = None
    best_diff = 999
    
    for name, c in configs:
        r = Sim(c).sim(10000)
        ra = r["rates"]
        vo = r["vow"]
        print(f"\n{name}")
        print(f"  差距: {r['diff']:.1f}%")
        print(f"  农{ra.get('农夫',0):.0f} 商{ra.get('商人',0):.0f} 学{ra.get('学者',0):.0f} 僧{ra.get('僧侣',0):.0f}")
        print(f"  勤{vo.get('勤劳致福',0):.0f}% 阿{vo.get('阿罗汉果',0):.0f}%")
        
        if r['diff'] < best_diff:
            best_diff = r['diff']
            best = (name, c, r)
    
    print(f"\n最佳配置: {best[0]} (差距{best_diff:.1f}%)")
    
    # 保存
    final = {
        "name": best[0],
        "config": {
            "farmer": best[1].farmer,
            "merchant": best[1].merchant,
            "scholar": best[1].scholar,
            "monk": best[1].monk,
            "labor_farmer": best[1].labor_farmer,
            "donate_merchant": best[1].donate_merchant,
            "practice_scholar": best[1].practice_scholar,
            "practice_monk": best[1].practice_monk,
            "diligent_fu": best[1].diligent_fu,
            "poor_girl_fu": best[1].poor_girl_fu,
            "teach_hui": best[1].teach_hui,
            "teacher_hui": best[1].teacher_hui,
            "arhat_hui": best[1].arhat_hui,
            "bodhisattva_fu": best[1].bodhisattva_fu,
        },
        "result": best[2],
    }
    
    with open("balance_v47_deep.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2, default=str)
    
    print("\n已保存到 balance_v47_deep.json")

if __name__ == "__main__":
    main()
