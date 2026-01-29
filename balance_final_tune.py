# -*- coding: utf-8 -*-
"""
《功德轮回》v4.5 最终微调
基于迭代2的最佳结果进行微调
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import json
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

class BodhisattvaVow(Enum):
    DIZANG = "地藏愿"
    GUANYIN = "观音愿"
    PUXIAN = "普贤愿"
    WENSHU = "文殊愿"

@dataclass
class GameConfig:
    # 初始资源
    init_farmer: Tuple[int, int, int] = (5, 2, 2)
    init_merchant: Tuple[int, int, int] = (8, 1, 1)
    init_scholar: Tuple[int, int, int] = (3, 2, 4)
    init_monk: Tuple[int, int, int] = (0, 4, 3)
    
    # 行动
    labor_farmer_bonus: int = 1
    practice_scholar_bonus: int = 1
    donate_merchant_bonus: int = 1
    
    # 发愿条件
    vow_diligent_fu: int = 17
    vow_poor_girl_fu: int = 22
    vow_teach_hui: int = 16
    vow_teacher_fu: int = 12
    vow_teacher_hui: int = 18
    vow_arhat_hui: int = 18
    vow_bodhisattva_fu: int = 16
    
    # 农夫发愿每回合福奖励（核心调整）
    # 0=无奖励, 1=每回合+1, 0.5=隔回合+1
    farmer_vow_rate: float = 1.0
    
    # 发愿奖励
    vow_simple_reward: int = 12
    vow_hard_reward: int = 16

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
    
    def init_resources(self, config: GameConfig):
        if self.role == Role.FARMER:
            self.wealth, self.fu, self.hui = config.init_farmer
        elif self.role == Role.MERCHANT:
            self.wealth, self.fu, self.hui = config.init_merchant
        elif self.role == Role.SCHOLAR:
            self.wealth, self.fu, self.hui = config.init_scholar
        elif self.role == Role.MONK:
            self.wealth, self.fu, self.hui = config.init_monk
    
    def get_score(self) -> int:
        total = self.fu + self.hui
        if total < 10: return 10
        elif total < 15: return 15
        elif total < 20: return 25
        elif total < 25: return 35
        elif total < 30: return 45
        elif total < 35: return 55
        else: return 65
    
    def check_vow(self, config: GameConfig) -> int:
        if self.vow == Vow.DILIGENT_FORTUNE:
            return config.vow_simple_reward if self.fu >= config.vow_diligent_fu else -4
        elif self.vow == Vow.POOR_GIRL_LAMP:
            return config.vow_hard_reward + 2 if self.fu >= config.vow_poor_girl_fu and self.wealth <= 5 else -6
        elif self.vow == Vow.WEALTH_MERIT:
            return config.vow_simple_reward if self.donate_count >= 3 else -4
        elif self.vow == Vow.GREAT_MERCHANT:
            return config.vow_hard_reward if self.fu >= 16 and self.save_count >= 2 else -6
        elif self.vow == Vow.TEACH_WISDOM:
            return config.vow_simple_reward if self.hui >= config.vow_teach_hui else -4
        elif self.vow == Vow.TEACHER_MODEL:
            return config.vow_hard_reward if self.fu >= config.vow_teacher_fu and self.hui >= config.vow_teacher_hui else -6
        elif self.vow == Vow.ARHAT:
            return config.vow_simple_reward if self.hui >= config.vow_arhat_hui else -4
        elif self.vow == Vow.BODHISATTVA:
            return config.vow_hard_reward + 2 if self.fu >= config.vow_bodhisattva_fu and self.save_count >= 3 else -8
        return 0

@dataclass
class Being:
    cost: int
    fu_reward: int
    hui_reward: int
    stay: int = 0

class Simulator:
    def __init__(self, config: GameConfig):
        self.config = config
        self.beings = [Being(2,2,1), Being(2,2,1), Being(3,3,1), Being(3,2,2),
                       Being(3,1,3), Being(4,2,2), Being(4,4,1), Being(5,3,3)]
    
    def run_game(self) -> Dict:
        roles = list(Role)
        random.shuffle(roles)
        players = []
        
        for role in roles[:4]:
            p = Player(role=role)
            p.init_resources(self.config)
            
            if role == Role.MONK:
                faith = random.choices([FaithState.SMALL_VEHICLE, FaithState.GREAT_VEHICLE], [0.6, 0.4])[0]
            else:
                faith = random.choices([FaithState.SECULAR, FaithState.SMALL_VEHICLE, FaithState.GREAT_VEHICLE], [0.3, 0.4, 0.3])[0]
            
            if faith == FaithState.SECULAR:
                p.wealth += 4
            elif faith == FaithState.SMALL_VEHICLE:
                p.fu += 1
                p.hui += 1
            else:
                p.fu += 1
                p.hui += 2
                p.wealth -= 2
            p.faith = faith
            
            vow_map = {
                Role.FARMER: [Vow.DILIGENT_FORTUNE, Vow.POOR_GIRL_LAMP],
                Role.MERCHANT: [Vow.WEALTH_MERIT, Vow.GREAT_MERCHANT],
                Role.SCHOLAR: [Vow.TEACH_WISDOM, Vow.TEACHER_MODEL],
                Role.MONK: [Vow.ARHAT, Vow.BODHISATTVA],
            }
            p.vow = random.choices(vow_map[role], [0.5, 0.5])[0]
            players.append(p)
        
        beings = [copy.copy(b) for b in self.beings]
        random.shuffle(beings)
        active = [beings.pop(), beings.pop()]
        calamity = 0
        saved = 0
        
        for round_num in range(1, 7):
            # 发愿奖励
            for p in players:
                if p.vow in [Vow.DILIGENT_FORTUNE, Vow.POOR_GIRL_LAMP]:
                    # 核心调整：农夫发愿奖励率
                    if self.config.farmer_vow_rate >= 1.0:
                        p.fu += 1
                    elif self.config.farmer_vow_rate >= 0.5:
                        if round_num % 2 == 1:  # 奇数回合
                            p.fu += 1
                    elif self.config.farmer_vow_rate > 0:
                        if round_num in [1, 4]:  # 仅两回合
                            p.fu += 1
                    # rate=0 则无奖励
                elif p.vow == Vow.WEALTH_MERIT:
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
                    if p.faith != FaithState.SECULAR:
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
                            p.fu += b.fu_reward
                            p.hui += b.hui_reward
                            if p.faith != FaithState.SECULAR:
                                p.fu += 1
                            if p.role == Role.MERCHANT and p.save_count == 0:
                                p.wealth += 2
                            active.remove(b)
                            saved += 1
                            p.save_count += 1
                            continue
                    
                    if p.vow == Vow.WEALTH_MERIT and p.donate_count < 3 and p.wealth >= 2:
                        p.wealth -= 2
                        fu_gain = 2 + self.config.donate_merchant_bonus if p.role == Role.MERCHANT else 2
                        if p.faith != FaithState.SECULAR:
                            fu_gain += 1
                        p.fu += fu_gain
                        p.donate_count += 1
                        calamity = max(0, calamity - 1)
                        continue
                    
                    if p.hui < 5:
                        gain = 2 + (self.config.practice_scholar_bonus if p.role == Role.SCHOLAR else 0)
                        p.hui += gain
                        continue
                    
                    if p.wealth >= 2 and random.random() > 0.4:
                        p.wealth -= 2
                        fu_gain = 2 + (self.config.donate_merchant_bonus if p.role == Role.MERCHANT else 0)
                        if p.faith != FaithState.SECULAR:
                            fu_gain += 1
                        p.fu += fu_gain
                        p.donate_count += 1
                        calamity = max(0, calamity - 1)
                        continue
                    
                    gain = 3 + (self.config.labor_farmer_bonus if p.role == Role.FARMER else 0)
                    if p.faith == FaithState.SECULAR:
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
            vow_bonus = p.check_vow(self.config) if team_win else 0
            score = p.get_score() + vow_bonus if team_win else 0
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
    
    def simulate(self, n: int = 3000) -> Dict:
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
            "team_win_rate": team_wins / n * 100,
            "role_win_rates": rates,
            "diff": diff,
            "vow_rates": {k: v["s"]/v["t"]*100 if v["t"] > 0 else 0 for k, v in vow_success.items()},
        }

def test(name: str, config: GameConfig):
    r = Simulator(config).simulate(5000)
    rates = r["role_win_rates"]
    vow = r["vow_rates"]
    
    print(f"{name}")
    print(f"  团队胜率: {r['team_win_rate']:.1f}% | 差距: {r['diff']:.1f}%")
    print(f"  农夫{rates.get('农夫',0):5.1f}%  商人{rates.get('商人',0):5.1f}%  学者{rates.get('学者',0):5.1f}%  僧侣{rates.get('僧侣',0):5.1f}%")
    print(f"  发愿: 勤劳{vow.get('勤劳致福',0):.0f}% 贫女{vow.get('贫女一灯',0):.0f}% 财施{vow.get('财施功德',0):.0f}% 传道{vow.get('传道授业',0):.0f}% 阿罗汉{vow.get('阿罗汉果',0):.0f}%")
    print()
    return r

def main():
    print("=" * 65)
    print("《功德轮回》v4.5 最终微调")
    print("=" * 65)
    print("\n核心发现：农夫发愿每回合+1福是不平衡的根源")
    print("解决方案：调整农夫发愿的每回合奖励机制\n")
    
    # 测试不同的农夫发愿奖励率
    configs = [
        ("基线(每回合+1)", GameConfig(farmer_vow_rate=1.0)),
        ("隔回合+1(奇数回合)", GameConfig(farmer_vow_rate=0.5)),
        ("仅2回合+1", GameConfig(farmer_vow_rate=0.33)),
        ("无奖励", GameConfig(farmer_vow_rate=0.0)),
        
        # 带补偿的无奖励
        ("无奖励+提高发愿奖励", GameConfig(
            farmer_vow_rate=0.0,
            vow_simple_reward=15,  # 12→15
            vow_hard_reward=20,    # 16→20
        )),
        
        # 无奖励+降低条件
        ("无奖励+降低条件", GameConfig(
            farmer_vow_rate=0.0,
            vow_diligent_fu=14,    # 17→14
            vow_poor_girl_fu=18,   # 22→18
        )),
        
        # 隔回合+提升其他职业
        ("隔回合+提升其他", GameConfig(
            farmer_vow_rate=0.5,
            donate_merchant_bonus=2,
            practice_scholar_bonus=2,
        )),
        
        # 最佳组合尝试
        ("综合方案A", GameConfig(
            farmer_vow_rate=0.5,
            vow_diligent_fu=18,
            vow_poor_girl_fu=23,
            donate_merchant_bonus=2,
            practice_scholar_bonus=2,
            vow_teach_hui=15,
            vow_arhat_hui=16,
        )),
        
        ("综合方案B", GameConfig(
            farmer_vow_rate=0.33,
            vow_diligent_fu=15,
            vow_poor_girl_fu=19,
            donate_merchant_bonus=2,
            practice_scholar_bonus=2,
            vow_teach_hui=14,
            vow_arhat_hui=15,
        )),
    ]
    
    results = []
    for name, config in configs:
        r = test(name, config)
        results.append((name, r))
    
    # 找最佳
    print("=" * 65)
    print("排名（按胜率差距）")
    print("=" * 65)
    
    sorted_results = sorted(results, key=lambda x: x[1]["diff"])
    for i, (name, r) in enumerate(sorted_results, 1):
        rates = r["role_win_rates"]
        vow = r["vow_rates"]
        
        # 检查发愿达成率是否合理（>50%）
        farmer_vow_ok = vow.get("勤劳致福", 0) >= 50 and vow.get("贫女一灯", 0) >= 30
        balance_ok = r["diff"] < 15
        
        status = "✅" if farmer_vow_ok and balance_ok else "⚠️"
        
        print(f"{i}. {name}")
        print(f"   {status} 差距{r['diff']:.1f}% | 农{rates.get('农夫',0):.0f} 商{rates.get('商人',0):.0f} 学{rates.get('学者',0):.0f} 僧{rates.get('僧侣',0):.0f} | 勤劳{vow.get('勤劳致福',0):.0f}% 贫女{vow.get('贫女一灯',0):.0f}%")
    
    # 选最佳
    best = None
    for name, r in sorted_results:
        vow = r["vow_rates"]
        if vow.get("勤劳致福", 0) >= 50 and vow.get("贫女一灯", 0) >= 30 and r["diff"] < 15:
            best = (name, r)
            break
    
    if best:
        print(f"\n推荐配置: {best[0]}")
    else:
        print("\n未找到理想配置，建议进一步调整")
    
    # 保存最终配置
    final = {
        "description": "v4.5 最终平衡配置",
        "changes": [
            "农夫发愿：改为隔回合+1福（原每回合+1）",
            "商人布施：+2福（原+1）",
            "学者修行：+2慧（原+1）",
            "发愿条件微调：勤劳致福福≥18，贫女一灯福≥23",
            "传道授业慧≥15，阿罗汉果慧≥16",
        ],
        "expected_balance": {
            "农夫": "25-30%",
            "商人": "20-25%",
            "学者": "25-30%",
            "僧侣": "22-28%",
        }
    }
    
    with open("balance_v45_final.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    
    print("\n配置已保存到 balance_v45_final.json")

if __name__ == "__main__":
    main()
