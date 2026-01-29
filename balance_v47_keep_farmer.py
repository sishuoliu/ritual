# -*- coding: utf-8 -*-
"""
《功德轮回》v4.7 平衡迭代
保留农夫每回合+1福，通过其他方式平衡
"""

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
import copy
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
class GameConfig:
    """游戏配置"""
    # 初始资源 (财, 福, 慧)
    farmer: tuple = (5, 2, 2)
    merchant: tuple = (8, 1, 1)
    scholar: tuple = (3, 2, 4)
    monk: tuple = (0, 4, 3)
    
    # 被动技能
    labor_farmer: int = 1      # 农夫劳作额外财富
    donate_merchant: int = 1   # 商人布施额外福
    practice_scholar: int = 1  # 学者修行额外慧
    
    # 发愿每回合奖励
    farmer_vow_fu: int = 1     # 农夫发愿每回合福 (保留!)
    
    # 发愿条件
    diligent_fu: int = 17
    poor_girl_fu: int = 22
    poor_girl_wealth: int = 5
    teach_hui: int = 16
    teacher_fu: int = 12
    teacher_hui: int = 18
    arhat_hui: int = 18
    bodhisattva_fu: int = 16
    
    # 奖惩
    simple_reward: int = 12
    hard_reward: int = 16
    simple_penalty: int = 4
    hard_penalty: int = 6

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

class Simulator:
    def __init__(self, config: GameConfig):
        self.config = config
    
    def run_game(self):
        c = self.config
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
            # 发愿奖励 - 保留农夫每回合+1福!
            for p in players:
                if p.vow in [Vow.DILIGENT, Vow.POOR_GIRL]:
                    p.fu += c.farmer_vow_fu  # 保留!
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
                        fu_gain = 2 + (c.donate_merchant if p.role == Role.MERCHANT else 0)
                        if p.faith != "secular":
                            fu_gain += 1
                        p.fu += fu_gain
                        p.donate_count += 1
                        calamity = max(0, calamity - 1)
                        continue
                    
                    if p.hui < 5:
                        gain = 2 + (c.practice_scholar if p.role == Role.SCHOLAR else 0)
                        p.hui += gain
                        continue
                    
                    if p.wealth >= 2 and random.random() > 0.4:
                        p.wealth -= 2
                        fu_gain = 2 + (c.donate_merchant if p.role == Role.MERCHANT else 0)
                        if p.faith != "secular":
                            fu_gain += 1
                        p.fu += fu_gain
                        p.donate_count += 1
                        calamity = max(0, calamity - 1)
                        continue
                    
                    gain = 3 + (c.labor_farmer if p.role == Role.FARMER else 0)
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
            
            vow_bonus = 0
            if team_win:
                if p.vow == Vow.DILIGENT:
                    vow_bonus = c.simple_reward if p.fu >= c.diligent_fu else -c.simple_penalty
                elif p.vow == Vow.POOR_GIRL:
                    vow_bonus = c.hard_reward + 2 if p.fu >= c.poor_girl_fu and p.wealth <= c.poor_girl_wealth else -c.hard_penalty
                elif p.vow == Vow.WEALTH:
                    vow_bonus = c.simple_reward if p.donate_count >= 3 else -c.simple_penalty
                elif p.vow == Vow.MERCHANT_HEART:
                    vow_bonus = c.hard_reward if p.fu >= 16 and p.save_count >= 2 else -c.hard_penalty
                elif p.vow == Vow.TEACH:
                    vow_bonus = c.simple_reward if p.hui >= c.teach_hui else -c.simple_penalty
                elif p.vow == Vow.TEACHER:
                    vow_bonus = c.hard_reward if p.fu >= c.teacher_fu and p.hui >= c.teacher_hui else -c.hard_penalty
                elif p.vow == Vow.ARHAT:
                    vow_bonus = c.simple_reward if p.hui >= c.arhat_hui else -c.simple_penalty
                elif p.vow == Vow.BODHISATTVA:
                    vow_bonus = c.hard_reward + 2 if p.fu >= c.bodhisattva_fu and p.save_count >= 3 else -c.hard_penalty - 2
            
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
    
    def simulate(self, n=3000):
        team_wins = 0
        role_wins = defaultdict(int)
        role_scores = defaultdict(list)
        vow_success = defaultdict(lambda: {"s": 0, "t": 0})
        
        for _ in range(n):
            r = self.run_game()
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
            "team_rate": team_wins / n * 100,
            "rates": rates,
            "diff": diff,
            "vow": {k: v["s"]/v["t"]*100 if v["t"] > 0 else 0 for k, v in vow_success.items()},
            "scores": {k: sum(v)/len(v) if v else 0 for k, v in role_scores.items()},
        }

def test(name, config, n=5000):
    r = Simulator(config).simulate(n)
    rates = r["rates"]
    vow = r["vow"]
    
    print(f"\n{name}")
    print(f"  团队胜率: {r['team_rate']:.1f}%  差距: {r['diff']:.1f}%")
    print(f"  农夫{rates.get('农夫',0):5.1f}%  商人{rates.get('商人',0):5.1f}%  学者{rates.get('学者',0):5.1f}%  僧侣{rates.get('僧侣',0):5.1f}%")
    print(f"  勤劳{vow.get('勤劳致福',0):3.0f}% 贫女{vow.get('贫女一灯',0):3.0f}% 财施{vow.get('财施功德',0):3.0f}% 传道{vow.get('传道授业',0):3.0f}% 阿罗汉{vow.get('阿罗汉果',0):3.0f}% 菩萨道{vow.get('菩萨道',0):3.0f}%")
    return r

def main():
    print("=" * 70)
    print("《功德轮回》v4.7 平衡迭代 - 保留农夫每回合+1福")
    print("=" * 70)
    print("\n策略: 保留农夫发愿每回合+1福，通过以下方式平衡:")
    print("  1. 提高农夫发愿条件")
    print("  2. 降低农夫初始资源或被动技能")
    print("  3. 大幅增强其他职业")
    print("  4. 组合调整")
    
    # 基线
    print("\n" + "=" * 70)
    base = GameConfig()
    r0 = test("[基线] 原配置", base)
    
    # 方案1: 大幅提高农夫发愿条件
    print("\n--- 方案1: 提高农夫发愿条件 ---")
    c1a = GameConfig(diligent_fu=20, poor_girl_fu=26)
    test("[1a] 勤劳≥20, 贫女≥26", c1a)
    
    c1b = GameConfig(diligent_fu=22, poor_girl_fu=28)
    test("[1b] 勤劳≥22, 贫女≥28", c1b)
    
    c1c = GameConfig(diligent_fu=24, poor_girl_fu=30)
    test("[1c] 勤劳≥24, 贫女≥30", c1c)
    
    # 方案2: 降低农夫初始/被动
    print("\n--- 方案2: 削弱农夫 ---")
    c2a = GameConfig(farmer=(4, 1, 2), labor_farmer=0)  # 财-1, 福-1, 劳作无奖励
    test("[2a] 农夫初始(4,1,2), 劳作+0", c2a)
    
    c2b = GameConfig(farmer=(3, 1, 2), labor_farmer=0)  # 更激进
    test("[2b] 农夫初始(3,1,2), 劳作+0", c2b)
    
    # 方案3: 大幅增强其他职业
    print("\n--- 方案3: 增强其他职业 ---")
    c3a = GameConfig(
        donate_merchant=3,      # 商人布施+3福
        practice_scholar=3,     # 学者修行+3慧
        monk=(1, 5, 4),         # 僧侣增强
        arhat_hui=14,           # 阿罗汉条件降低
    )
    test("[3a] 商人+3, 学者+3, 僧侣增强", c3a)
    
    c3b = GameConfig(
        merchant=(8, 3, 1),     # 商人初始福+2
        scholar=(4, 3, 6),      # 学者全面增强
        monk=(2, 5, 4),         # 僧侣增强
        donate_merchant=2,
        practice_scholar=2,
        arhat_hui=14,
        bodhisattva_fu=12,
    )
    test("[3b] 其他职业初始资源大增", c3b)
    
    # 方案4: 组合 - 提高农夫条件 + 增强其他
    print("\n--- 方案4: 组合调整 ---")
    c4a = GameConfig(
        diligent_fu=21,
        poor_girl_fu=27,
        donate_merchant=2,
        practice_scholar=2,
        scholar=(3, 2, 5),
        monk=(1, 4, 4),
        arhat_hui=16,
    )
    test("[4a] 农夫条件+4, 其他+1", c4a)
    
    c4b = GameConfig(
        diligent_fu=22,
        poor_girl_fu=28,
        farmer=(4, 2, 2),       # 农夫财-1
        donate_merchant=2,
        practice_scholar=2,
        scholar=(4, 2, 5),
        monk=(1, 5, 4),
        arhat_hui=15,
        bodhisattva_fu=14,
    )
    test("[4b] 农夫条件+5且财-1, 其他职业增强", c4b)
    
    c4c = GameConfig(
        diligent_fu=23,
        poor_girl_fu=29,
        farmer=(4, 1, 2),       # 农夫财-1福-1
        labor_farmer=0,         # 劳作无奖励
        donate_merchant=2,
        practice_scholar=2,
        merchant=(8, 2, 1),
        scholar=(4, 2, 5),
        monk=(1, 5, 4),
        arhat_hui=15,
        bodhisattva_fu=13,
    )
    test("[4c] 农夫全削+条件高, 其他大增", c4c)
    
    # 方案5: 极端 - 农夫每回合+1福但奖励减半
    print("\n--- 方案5: 发愿奖励调整 ---")
    c5a = GameConfig(
        simple_reward=10,   # 简单发愿奖励降低
        hard_reward=14,
        diligent_fu=19,
        poor_girl_fu=25,
        donate_merchant=2,
        practice_scholar=2,
    )
    test("[5a] 简单发愿奖励降低(12→10)", c5a)
    
    # 方案6: 给其他职业也加每回合福
    print("\n--- 方案6: 其他职业发愿也加福 ---")
    # 这需要修改模拟器逻辑，暂时模拟效果
    c6a = GameConfig(
        merchant=(8, 1, 1),
        scholar=(3, 2, 4),
        monk=(0, 4, 3),
        # 商人财施功德改为每回合+1福(不是财富)
        # 学者传道授业改为每回合+1福+1慧
        # 通过增加初始福来模拟
        donate_merchant=2,
        practice_scholar=2,
    )
    test("[6a] 平衡：商人+2布施, 学者+2修行", c6a)
    
    print("\n" + "=" * 70)
    print("总结")
    print("=" * 70)
    
    # 运行最有希望的配置
    best_configs = [
        ("[4b] 综合方案", GameConfig(
            diligent_fu=22, poor_girl_fu=28,
            farmer=(4, 2, 2),
            donate_merchant=2, practice_scholar=2,
            scholar=(4, 2, 5), monk=(1, 5, 4),
            arhat_hui=15, bodhisattva_fu=14,
        )),
        ("[4c] 激进方案", GameConfig(
            diligent_fu=23, poor_girl_fu=29,
            farmer=(4, 1, 2), labor_farmer=0,
            donate_merchant=2, practice_scholar=2,
            merchant=(8, 2, 1), scholar=(4, 2, 5), monk=(1, 5, 4),
            arhat_hui=15, bodhisattva_fu=13,
        )),
    ]
    
    print("\n最终对比 (10000局):")
    results = []
    for name, config in best_configs:
        r = Simulator(config).simulate(10000)
        rates = r["rates"]
        print(f"\n{name}")
        print(f"  差距: {r['diff']:.1f}%")
        print(f"  农{rates.get('农夫',0):.0f} 商{rates.get('商人',0):.0f} 学{rates.get('学者',0):.0f} 僧{rates.get('僧侣',0):.0f}")
        print(f"  勤劳{r['vow'].get('勤劳致福',0):.0f}% 阿罗汉{r['vow'].get('阿罗汉果',0):.0f}%")
        results.append((name, config, r))
    
    # 保存最佳
    best = min(results, key=lambda x: x[2]["diff"])
    print(f"\n推荐配置: {best[0]} (差距{best[2]['diff']:.1f}%)")
    
    # 保存配置
    final = {
        "name": best[0],
        "farmer_vow_per_round": "+1福 (保留)",
        "diligent_fu": best[1].diligent_fu,
        "poor_girl_fu": best[1].poor_girl_fu,
        "farmer": best[1].farmer,
        "labor_farmer": best[1].labor_farmer,
        "merchant": best[1].merchant,
        "scholar": best[1].scholar,
        "monk": best[1].monk,
        "donate_merchant": best[1].donate_merchant,
        "practice_scholar": best[1].practice_scholar,
        "arhat_hui": best[1].arhat_hui,
        "bodhisattva_fu": best[1].bodhisattva_fu,
        "result": {
            "diff": best[2]["diff"],
            "rates": best[2]["rates"],
            "vow": best[2]["vow"],
        }
    }
    
    with open("balance_v47_final.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    
    print("\n配置已保存到 balance_v47_final.json")

if __name__ == "__main__":
    main()
