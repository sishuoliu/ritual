# -*- coding: utf-8 -*-
"""
最终平衡验证测试
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from collections import defaultdict
import copy

class Role(Enum):
    FARMER = "农夫"
    MERCHANT = "商人"
    SCHOLAR = "学者"
    MONK = "僧侣"

class FaithState(Enum):
    SECULAR = "不皈依"
    SMALL_VEHICLE = "小乘"
    GREAT_VEHICLE = "大乘"

class Vow(Enum):
    DILIGENT_FORTUNE = "勤劳致福"
    POOR_GIRL_LAMP = "贫女一灯"
    WEALTH_MERIT = "财施功德"
    GREAT_MERCHANT = "大商人之心"
    TEACH_WISDOM = "传道授业"
    TEACHER_MODEL = "万世师表"
    ARHAT = "阿罗汉果"
    BODHISATTVA = "菩萨道"

# v4.5 平衡配置
CONFIG = {
    # 初始资源 [财富, 福, 慧]
    "init_farmer": (4, 2, 2),
    "init_merchant": (8, 1, 1),
    "init_scholar": (3, 2, 5),
    "init_monk": (1, 4, 3),
    
    # 被动技能
    "labor_farmer_bonus": 0,  # 农夫劳作无额外奖励
    "practice_scholar_bonus": 2,  # 学者修行+2
    "donate_merchant_bonus": 2,  # 商人布施+2
    
    # 发愿条件
    "vow_diligent_fu": 20,
    "vow_poor_girl_fu": 28,
    "vow_teacher_fu": 12,
    "vow_teacher_hui": 18,
    "vow_arhat_hui": 18,
    "vow_bodhisattva_fu": 15,
}

@dataclass
class Player:
    role: Role
    faith: FaithState = FaithState.SECULAR
    wealth: int = 0
    fu: int = 0
    hui: int = 0
    vow: Optional[Vow] = None
    donate_count: int = 0
    save_count: int = 0
    
    def init_resources(self):
        if self.role == Role.FARMER:
            self.wealth, self.fu, self.hui = CONFIG["init_farmer"]
        elif self.role == Role.MERCHANT:
            self.wealth, self.fu, self.hui = CONFIG["init_merchant"]
        elif self.role == Role.SCHOLAR:
            self.wealth, self.fu, self.hui = CONFIG["init_scholar"]
        elif self.role == Role.MONK:
            self.wealth, self.fu, self.hui = CONFIG["init_monk"]
    
    def get_score(self) -> int:
        total = self.fu + self.hui
        if total < 10: base = 10
        elif total < 15: base = 15
        elif total < 20: base = 25
        elif total < 25: base = 35
        elif total < 30: base = 45
        elif total < 35: base = 55
        else: base = 65
        if self.fu < 5 or self.hui < 5: base //= 2
        return base
    
    def check_vow(self) -> int:
        if self.vow == Vow.DILIGENT_FORTUNE:
            return 12 if self.fu >= CONFIG["vow_diligent_fu"] else -4
        elif self.vow == Vow.POOR_GIRL_LAMP:
            return 18 if self.fu >= CONFIG["vow_poor_girl_fu"] and self.wealth <= 5 else -6
        elif self.vow == Vow.WEALTH_MERIT:
            return 12 if self.donate_count >= 3 else -4
        elif self.vow == Vow.GREAT_MERCHANT:
            return 16 if self.fu >= 18 and self.save_count >= 2 else -6
        elif self.vow == Vow.TEACH_WISDOM:
            return 12 if self.hui >= 18 else -4
        elif self.vow == Vow.TEACHER_MODEL:
            return 16 if self.fu >= CONFIG["vow_teacher_fu"] and self.hui >= CONFIG["vow_teacher_hui"] else -6
        elif self.vow == Vow.ARHAT:
            return 12 if self.hui >= CONFIG["vow_arhat_hui"] else -4
        elif self.vow == Vow.BODHISATTVA:
            return 18 if self.fu >= CONFIG["vow_bodhisattva_fu"] and self.save_count >= 3 else -8
        return 0

@dataclass
class Being:
    cost: int
    fu_reward: int
    hui_reward: int
    stay: int = 0

class Simulator:
    def __init__(self):
        self.beings = [Being(2,2,1), Being(2,2,1), Being(3,3,1), Being(3,2,2),
                       Being(3,1,3), Being(4,2,2), Being(4,4,1), Being(5,3,3)]
    
    def run_game(self):
        roles = list(Role)
        random.shuffle(roles)
        players = []
        
        for role in roles[:4]:
            p = Player(role=role)
            p.init_resources()
            
            faith = random.choices([FaithState.SECULAR, FaithState.SMALL_VEHICLE, FaithState.GREAT_VEHICLE], [0.3, 0.4, 0.3])[0]
            if faith == FaithState.SECULAR:
                p.wealth += 4
            elif faith == FaithState.SMALL_VEHICLE:
                p.fu += 1
                p.hui += 1
            else:
                p.fu += 1
                p.hui += 1
                p.wealth -= 2
                p.hui += 1
            p.faith = faith
            
            vow_map = {
                Role.FARMER: [Vow.DILIGENT_FORTUNE, Vow.POOR_GIRL_LAMP],
                Role.MERCHANT: [Vow.WEALTH_MERIT, Vow.GREAT_MERCHANT],
                Role.SCHOLAR: [Vow.TEACH_WISDOM, Vow.TEACHER_MODEL],
                Role.MONK: [Vow.ARHAT, Vow.BODHISATTVA],
            }
            p.vow = random.choice(vow_map[role])
            players.append(p)
        
        beings = [copy.copy(b) for b in self.beings]
        random.shuffle(beings)
        active = [beings.pop(), beings.pop()]
        calamity = 0
        saved = 0
        
        for round_num in range(1, 7):
            # 发愿奖励
            for p in players:
                if p.vow in [Vow.DILIGENT_FORTUNE, Vow.POOR_GIRL_LAMP, Vow.BODHISATTVA]:
                    p.fu += 1
                elif p.vow == Vow.WEALTH_MERIT:
                    p.wealth += 1
                else:
                    p.hui += 1
            
            # 事件
            event = random.choices(["disaster", "blessing"], [0.5, 0.5])[0]
            if event == "disaster":
                calamity += 3
                for p in players:
                    if random.random() > 0.5:
                        p.wealth -= 2
                        p.fu += 1
                    else:
                        p.wealth -= 1
            else:
                for p in players:
                    p.fu += 1
                calamity -= 1
            
            # 众生
            for b in active:
                b.stay += 1
            timeout = [b for b in active if b.stay >= 2]
            for b in timeout:
                calamity += 4
                active.remove(b)
            if beings:
                active.append(beings.pop())
            
            # 行动
            for p in players:
                for _ in range(2):
                    if p.hui >= 5 and active:
                        affordable = [b for b in active if p.wealth >= b.cost - 1]
                        if affordable:
                            b = min(affordable, key=lambda x: x.cost)
                            p.wealth -= max(1, b.cost - 1)
                            p.fu += b.fu_reward
                            p.hui += b.hui_reward
                            if p.faith != FaithState.SECULAR:
                                p.fu += 1
                            active.remove(b)
                            saved += 1
                            p.save_count += 1
                            continue
                    
                    if p.hui < 5:
                        gain = 2
                        if p.role == Role.SCHOLAR:
                            gain += CONFIG["practice_scholar_bonus"]
                        p.hui += gain
                    elif p.wealth >= 2 and random.random() > 0.4:
                        p.wealth -= 2
                        fu_gain = 2
                        if p.role == Role.MERCHANT:
                            fu_gain += CONFIG["donate_merchant_bonus"]
                        if p.faith != FaithState.SECULAR:
                            fu_gain += 1
                        p.fu += fu_gain
                        p.donate_count += 1
                        calamity -= 1
                    else:
                        gain = 3
                        if p.role == Role.FARMER:
                            gain += CONFIG["labor_farmer_bonus"]
                        if p.faith == FaithState.SECULAR:
                            gain += 1
                        p.wealth += gain
            
            calamity += 1
            
            if calamity >= 20:
                break
        
        team_win = calamity <= 12 and saved >= 5
        
        results = []
        for p in players:
            score = p.get_score() + p.check_vow() if team_win else 0
            results.append({
                "role": p.role.value,
                "faith": p.faith.value,
                "vow": p.vow.value,
                "score": score,
                "fu": p.fu,
                "hui": p.hui,
            })
        
        winner = max(results, key=lambda x: x["score"]) if team_win else None
        
        return {"team_win": team_win, "winner": winner["role"] if winner else None, "players": results}
    
    def run_simulation(self, n=5000):
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
                if r["team_win"] and p["score"] > 0:
                    vow_success[p["vow"]]["s"] += 1
        
        print("=" * 60)
        print("v4.5 最终平衡验证 (5000局)")
        print("=" * 60)
        print(f"\n团队胜率: {team_wins/n*100:.1f}%")
        print("\n职业胜率:")
        for role in ["农夫", "商人", "学者", "僧侣"]:
            rate = role_wins[role] / team_wins * 100 if team_wins > 0 else 0
            score = sum(role_scores[role]) / len(role_scores[role]) if role_scores[role] else 0
            bar = "#" * int(rate / 2)
            print(f"  {role}: {rate:5.1f}% (平均{score:.1f}) {bar}")
        
        print("\n发愿成功率:")
        for vow, d in sorted(vow_success.items(), key=lambda x: x[1]["s"]/max(1,x[1]["t"]), reverse=True):
            rate = d["s"] / d["t"] * 100 if d["t"] > 0 else 0
            print(f"  {vow}: {rate:.1f}%")
        
        # 平衡评估
        rates = [role_wins[r.value] / team_wins * 100 if team_wins > 0 else 0 for r in Role]
        max_rate = max(rates)
        min_rate = min(rates) if min(rates) > 0 else 1
        ratio = max_rate / min_rate
        
        print(f"\n平衡评估: 最大/最小胜率比 = {ratio:.2f}")
        if ratio < 1.5:
            print("✅ 平衡状态：优秀")
        elif ratio < 2.0:
            print("✅ 平衡状态：良好")
        elif ratio < 3.0:
            print("⚠️ 平衡状态：尚可")
        else:
            print("❌ 平衡状态：需改进")

if __name__ == "__main__":
    Simulator().run_simulation(5000)
