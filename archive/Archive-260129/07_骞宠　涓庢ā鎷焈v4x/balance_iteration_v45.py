# -*- coding: utf-8 -*-
"""
《功德轮回》v4.5 深度平衡迭代
根据测试结果进行针对性调整
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

class AIStrategy(Enum):
    VOW_FOCUSED = "发愿导向"
    TEAM_FOCUSED = "团队导向"
    BALANCED = "平衡型"

@dataclass
class GameConfig:
    """游戏参数配置"""
    # 胜利条件
    calamity_limit: int = 20
    calamity_win_threshold: int = 12
    save_target: int = 5
    max_rounds: int = 6
    
    # 初始资源
    init_farmer: Tuple[int, int, int] = (5, 2, 2)
    init_merchant: Tuple[int, int, int] = (8, 1, 1)
    init_scholar: Tuple[int, int, int] = (3, 2, 4)
    init_monk: Tuple[int, int, int] = (0, 4, 3)
    
    # 信仰
    secular_wealth_bonus: int = 4
    
    # 行动
    labor_base: int = 3
    labor_farmer_bonus: int = 1
    labor_secular_bonus: int = 1
    practice_base: int = 2
    practice_scholar_bonus: int = 1
    donate_cost: int = 2
    donate_fu_base: int = 2
    donate_merchant_bonus: int = 1
    
    # 发愿条件 - 核心调整项
    vow_diligent_fu: int = 17
    vow_poor_girl_fu: int = 22
    vow_poor_girl_wealth: int = 5
    vow_wealth_merit_count: int = 3
    vow_great_merchant_fu: int = 16
    vow_great_merchant_save: int = 2
    vow_teach_hui: int = 16
    vow_teacher_fu: int = 12
    vow_teacher_hui: int = 18
    vow_arhat_hui: int = 18
    vow_bodhisattva_fu: int = 16
    vow_bodhisattva_save: int = 3
    
    # 发愿奖励 - 核心调整项
    farmer_vow_fu_per_round: int = 1  # 农夫发愿每回合福
    other_vow_reward_per_round: int = 1
    
    # 奖惩
    vow_simple_reward: int = 12
    vow_simple_penalty: int = 4
    vow_hard_reward: int = 16
    vow_hard_penalty: int = 6
    
    # 劫难
    disaster_calamity: int = 4
    misfortune_calamity: int = 3
    timeout_penalty: int = 4
    calamity_per_round: int = 1
    
    # 事件权重
    disaster_weight: float = 0.45
    misfortune_weight: float = 0.25
    blessing_weight: float = 0.30

@dataclass
class Player:
    role: Role
    faith: FaithState = FaithState.SECULAR
    wealth: int = 0
    fu: int = 0
    hui: int = 0
    vow: Optional[Vow] = None
    bodhisattva_vow: Optional[BodhisattvaVow] = None
    strategy: AIStrategy = AIStrategy.BALANCED
    
    donate_count: int = 0
    save_count: int = 0
    help_count: int = 0
    skill_uses: int = 2
    puxian_supply: int = 0
    guanyin_helped: set = field(default_factory=set)
    
    fu_total: int = 0
    hui_total: int = 0
    
    def init_resources(self, config: GameConfig):
        if self.role == Role.FARMER:
            self.wealth, self.fu, self.hui = config.init_farmer
        elif self.role == Role.MERCHANT:
            self.wealth, self.fu, self.hui = config.init_merchant
        elif self.role == Role.SCHOLAR:
            self.wealth, self.fu, self.hui = config.init_scholar
        elif self.role == Role.MONK:
            self.wealth, self.fu, self.hui = config.init_monk
    
    def apply_faith(self, faith: FaithState, config: GameConfig):
        if faith == FaithState.SECULAR:
            self.wealth += config.secular_wealth_bonus
        elif faith == FaithState.SMALL_VEHICLE:
            self.fu += 1
            self.hui += 1
        self.faith = faith
    
    def apply_great_vehicle(self, config: GameConfig):
        self.wealth -= 2
        self.hui += 1
        self.faith = FaithState.GREAT_VEHICLE
    
    def get_score(self) -> int:
        total = self.fu + self.hui
        if total < 10: base = 10
        elif total < 15: base = 15
        elif total < 20: base = 25
        elif total < 25: base = 35
        elif total < 30: base = 45
        elif total < 35: base = 55
        else: base = 65
        if self.fu < 5 or self.hui < 5:
            base = base // 2
        return base
    
    def check_vow(self, config: GameConfig) -> Tuple[int, int]:
        reward, penalty = 0, 0
        
        if self.vow == Vow.DILIGENT_FORTUNE:
            if self.fu >= config.vow_diligent_fu:
                reward = config.vow_simple_reward
            else:
                penalty = config.vow_simple_penalty
        elif self.vow == Vow.POOR_GIRL_LAMP:
            if self.fu >= config.vow_poor_girl_fu and self.wealth <= config.vow_poor_girl_wealth:
                reward = config.vow_hard_reward + 2
            else:
                penalty = config.vow_hard_penalty
        elif self.vow == Vow.WEALTH_MERIT:
            if self.donate_count >= config.vow_wealth_merit_count:
                reward = config.vow_simple_reward
            else:
                penalty = config.vow_simple_penalty
        elif self.vow == Vow.GREAT_MERCHANT:
            if self.fu >= config.vow_great_merchant_fu and self.save_count >= config.vow_great_merchant_save:
                reward = config.vow_hard_reward
            else:
                penalty = config.vow_hard_penalty
        elif self.vow == Vow.TEACH_WISDOM:
            if self.hui >= config.vow_teach_hui:
                reward = config.vow_simple_reward
            else:
                penalty = config.vow_simple_penalty
        elif self.vow == Vow.TEACHER_MODEL:
            if self.fu >= config.vow_teacher_fu and self.hui >= config.vow_teacher_hui:
                reward = config.vow_hard_reward
            else:
                penalty = config.vow_hard_penalty
        elif self.vow == Vow.ARHAT:
            if self.hui >= config.vow_arhat_hui:
                reward = config.vow_simple_reward
            else:
                penalty = config.vow_simple_penalty
        elif self.vow == Vow.BODHISATTVA:
            if self.fu >= config.vow_bodhisattva_fu and self.save_count >= config.vow_bodhisattva_save:
                reward = config.vow_hard_reward + 2
            else:
                penalty = config.vow_hard_penalty + 2
        
        return reward, penalty

@dataclass
class Being:
    cost: int
    fu_reward: int
    hui_reward: int
    stay: int = 0

class GameSimulator:
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
                p.apply_faith(FaithState.SECULAR, self.config)
            elif faith == FaithState.SMALL_VEHICLE:
                p.apply_faith(FaithState.SMALL_VEHICLE, self.config)
            else:
                p.apply_faith(FaithState.SMALL_VEHICLE, self.config)
                p.apply_great_vehicle(self.config)
            
            # 发愿选择
            vow_map = {
                Role.FARMER: [Vow.DILIGENT_FORTUNE, Vow.POOR_GIRL_LAMP],
                Role.MERCHANT: [Vow.WEALTH_MERIT, Vow.GREAT_MERCHANT],
                Role.SCHOLAR: [Vow.TEACH_WISDOM, Vow.TEACHER_MODEL],
                Role.MONK: [Vow.ARHAT, Vow.BODHISATTVA],
            }
            p.vow = random.choices(vow_map[role], [0.5, 0.5])[0]
            p.strategy = random.choice(list(AIStrategy))
            
            if p.faith == FaithState.GREAT_VEHICLE:
                p.bodhisattva_vow = random.choice(list(BodhisattvaVow))
            
            players.append(p)
        
        beings = [copy.copy(b) for b in self.beings]
        random.shuffle(beings)
        active = [beings.pop(), beings.pop()]
        calamity = 0
        saved = 0
        
        for round_num in range(1, 7):
            # 发愿奖励 - 关键调整点
            for p in players:
                if p.vow in [Vow.DILIGENT_FORTUNE, Vow.POOR_GIRL_LAMP]:
                    p.fu += self.config.farmer_vow_fu_per_round
                elif p.vow == Vow.WEALTH_MERIT:
                    p.wealth += 1
                elif p.vow == Vow.BODHISATTVA:
                    p.fu += 1
                else:
                    p.hui += 1
            
            # 集体事件
            event = random.choices(
                ["disaster", "misfortune", "blessing"],
                [self.config.disaster_weight, self.config.misfortune_weight, self.config.blessing_weight]
            )[0]
            
            if event == "disaster":
                calamity += self.config.disaster_calamity
                # 囚徒困境
                choices = []
                for p in players:
                    coop_prob = 0.5
                    if p.faith == FaithState.GREAT_VEHICLE:
                        coop_prob += 0.2
                    if calamity >= 12:
                        coop_prob += 0.2
                    choices.append("A" if random.random() < coop_prob else "B")
                
                a_count = choices.count("A")
                if a_count == 4:
                    calamity -= 2
                    for p in players:
                        p.fu += 1
                        p.wealth -= 1
                elif a_count == 0:
                    calamity += 3
                else:
                    calamity += (4 - a_count) - a_count
                    for i, p in enumerate(players):
                        if choices[i] == "A":
                            p.wealth -= 2
                            p.fu += 1 if a_count >= 2 else 0
                        else:
                            p.wealth -= 1
            
            elif event == "misfortune":
                calamity += self.config.misfortune_calamity
                for p in players:
                    if random.random() > 0.5:
                        p.wealth -= 1
            
            else:  # blessing
                effect = random.choice(["wealth", "fu", "hui", "calamity"])
                if effect == "wealth":
                    for p in players:
                        p.wealth += 1
                elif effect == "fu":
                    for p in players:
                        p.fu += 1
                        if p.faith != FaithState.SECULAR:
                            p.fu += 1
                elif effect == "hui":
                    for p in players:
                        p.hui += 1
                        if p.faith != FaithState.SECULAR:
                            p.hui += 1
                else:
                    calamity = max(0, calamity - 2)
            
            # 个人事件（奇数回合）
            if round_num % 2 == 1:
                for p in players:
                    effect = random.choices(
                        ["fu", "hui", "wealth", "fu_hui", "none"],
                        [0.3, 0.25, 0.2, 0.15, 0.1]
                    )[0]
                    if effect == "fu":
                        p.fu += random.randint(1, 2)
                    elif effect == "hui":
                        p.hui += random.randint(1, 2)
                    elif effect == "wealth":
                        p.wealth += random.randint(1, 3)
                    elif effect == "fu_hui":
                        p.fu += 1
                        p.hui += 1
            
            # 众生
            for b in active:
                b.stay += 1
            timeout = [b for b in active if b.stay >= 2]
            for b in timeout:
                calamity += self.config.timeout_penalty
                active.remove(b)
            if beings:
                active.append(beings.pop())
            
            # 行动
            for p in players:
                for _ in range(2):
                    action = self._decide_action(p, active, calamity)
                    
                    if action == "save" and p.hui >= 5 and active:
                        affordable = [b for b in active if self._can_afford(p, b)]
                        if affordable:
                            b = min(affordable, key=lambda x: x.cost)
                            cost = max(1, b.cost - (1 if p.role in [Role.SCHOLAR, Role.MONK] else 0) - (1 if p.faith == FaithState.SECULAR else 0))
                            if p.role == Role.MERCHANT:
                                cost += 1
                            cost = max(1, cost)
                            
                            if p.role == Role.MONK and p.wealth < cost:
                                fu_used = min(2, cost - p.wealth)
                                p.fu -= fu_used
                                p.wealth -= (cost - fu_used)
                            else:
                                p.wealth -= cost
                            
                            if p.role == Role.SCHOLAR:
                                p.hui -= 1
                            
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
                    
                    if action == "donate" and p.wealth >= 2:
                        p.wealth -= 2
                        fu_gain = 2
                        if p.role == Role.MERCHANT:
                            fu_gain += self.config.donate_merchant_bonus
                        if p.faith != FaithState.SECULAR:
                            fu_gain += 1
                        p.fu += fu_gain
                        p.donate_count += 1
                        calamity = max(0, calamity - 1)
                        continue
                    
                    if action == "protect" and p.wealth >= 2:
                        p.wealth -= 2
                        p.fu += 1
                        calamity = max(0, calamity - 2)
                        continue
                    
                    if action == "practice":
                        gain = self.config.practice_base
                        if p.role == Role.SCHOLAR:
                            gain += self.config.practice_scholar_bonus
                        p.hui += gain
                        continue
                    
                    if action == "labor":
                        gain = self.config.labor_base
                        if p.role == Role.FARMER:
                            gain += self.config.labor_farmer_bonus
                        if p.faith == FaithState.SECULAR:
                            gain += self.config.labor_secular_bonus
                        p.wealth += gain
            
            # 结算
            calamity += self.config.calamity_per_round
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
            score = p.get_score()
            vow_r, vow_p = p.check_vow(self.config)
            final = score + vow_r - vow_p if team_win else 0
            
            results.append({
                "role": p.role.value,
                "faith": p.faith.value,
                "vow": p.vow.value,
                "fu": p.fu,
                "hui": p.hui,
                "score": final,
                "vow_bonus": vow_r - vow_p,
            })
        
        winner = max(results, key=lambda x: x["score"]) if team_win else None
        
        return {
            "team_win": team_win,
            "calamity": calamity,
            "saved": saved,
            "winner": winner["role"] if winner else None,
            "players": results
        }
    
    def _decide_action(self, p: Player, active: List, calamity: int) -> str:
        if calamity >= 15 and p.wealth >= 2:
            return "protect"
        
        if p.hui >= 5 and active:
            affordable = [b for b in active if self._can_afford(p, b)]
            if affordable:
                return "save"
        
        # 发愿导向
        if p.vow == Vow.WEALTH_MERIT and p.donate_count < 3 and p.wealth >= 2:
            return "donate"
        
        if p.hui < 5:
            return "practice"
        
        if p.wealth >= 2 and random.random() > 0.4:
            return "donate"
        
        if p.wealth < 4:
            return "labor"
        
        return "practice"
    
    def _can_afford(self, p: Player, b: Being) -> bool:
        cost = b.cost
        if p.role == Role.MERCHANT:
            cost += 1
        elif p.role in [Role.SCHOLAR, Role.MONK]:
            cost -= 1
        if p.faith == FaithState.SECULAR:
            cost -= 1
        cost = max(1, cost)
        
        if p.role == Role.MONK:
            return p.wealth + min(2, p.fu) >= cost
        return p.wealth >= cost
    
    def simulate(self, n: int = 2000) -> Dict:
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
        
        return {
            "team_win_rate": team_wins / n * 100,
            "role_win_rates": {k: v / team_wins * 100 if team_wins > 0 else 0 for k, v in role_wins.items()},
            "role_avg_scores": {k: sum(v)/len(v) if v else 0 for k, v in role_scores.items()},
            "vow_rates": {k: v["s"]/v["t"]*100 if v["t"] > 0 else 0 for k, v in vow_success.items()},
        }

def test_config(name: str, config: GameConfig, n: int = 2000) -> Dict:
    sim = GameSimulator(config)
    r = sim.simulate(n)
    
    rates = r["role_win_rates"]
    max_r = max(rates.values()) if rates else 0
    min_r = min(v for v in rates.values() if v > 0) if any(v > 0 for v in rates.values()) else 0
    
    print(f"\n{name}")
    print(f"  团队胜率: {r['team_win_rate']:.1f}%")
    print(f"  职业胜率: 农夫{rates.get('农夫',0):.1f}% 商人{rates.get('商人',0):.1f}% 学者{rates.get('学者',0):.1f}% 僧侣{rates.get('僧侣',0):.1f}%")
    print(f"  胜率差距: {max_r - min_r:.1f}%")
    print(f"  发愿达成: 勤劳{r['vow_rates'].get('勤劳致福',0):.0f}% 贫女{r['vow_rates'].get('贫女一灯',0):.0f}% 财施{r['vow_rates'].get('财施功德',0):.0f}% 传道{r['vow_rates'].get('传道授业',0):.0f}%")
    
    return r

def main():
    print("=" * 60)
    print("《功德轮回》v4.5 深度平衡迭代")
    print("=" * 60)
    
    # 基线
    base = GameConfig()
    r_base = test_config("[基线] 原配置", base, 3000)
    
    # 迭代1：提高农夫发愿条件
    c1 = GameConfig(vow_diligent_fu=19, vow_poor_girl_fu=24)
    r1 = test_config("[迭代1] 农夫发愿条件+2", c1, 3000)
    
    # 迭代2：降低农夫发愿每回合奖励
    c2 = GameConfig(vow_diligent_fu=19, vow_poor_girl_fu=24, farmer_vow_fu_per_round=0)
    r2 = test_config("[迭代2] 农夫发愿每回合0福", c2, 3000)
    
    # 迭代3：提升商人/学者
    c3 = GameConfig(
        vow_diligent_fu=19,
        vow_poor_girl_fu=24,
        farmer_vow_fu_per_round=0,
        donate_merchant_bonus=2,  # 商人布施+2
        practice_scholar_bonus=2,  # 学者修行+2
    )
    r3 = test_config("[迭代3] 商人布施+2，学者修行+2", c3, 3000)
    
    # 迭代4：降低农夫初始资源
    c4 = GameConfig(
        init_farmer=(4, 1, 2),  # 财-1，福-1
        vow_diligent_fu=18,
        vow_poor_girl_fu=23,
        farmer_vow_fu_per_round=1,  # 恢复
        donate_merchant_bonus=2,
        practice_scholar_bonus=2,
    )
    r4 = test_config("[迭代4] 农夫初始资源降低", c4, 3000)
    
    # 迭代5：综合调整
    c5 = GameConfig(
        init_farmer=(4, 1, 2),
        init_scholar=(3, 2, 5),  # 学者慧+1
        init_monk=(1, 4, 3),     # 僧侣财+1
        vow_diligent_fu=19,
        vow_poor_girl_fu=24,
        vow_teach_hui=15,        # 学者发愿条件降低
        vow_arhat_hui=16,        # 僧侣发愿条件降低
        donate_merchant_bonus=2,
        practice_scholar_bonus=2,
    )
    r5 = test_config("[迭代5] 综合调整", c5, 3000)
    
    # 迭代6：进一步平衡
    c6 = GameConfig(
        init_farmer=(4, 1, 2),
        init_scholar=(4, 2, 5),  # 学者财+1
        init_monk=(1, 5, 3),     # 僧侣福+1
        vow_diligent_fu=20,      # 更高
        vow_poor_girl_fu=25,
        vow_teach_hui=14,
        vow_teacher_hui=16,
        vow_arhat_hui=15,
        vow_bodhisattva_fu=14,
        donate_merchant_bonus=2,
        practice_scholar_bonus=2,
    )
    r6 = test_config("[迭代6] 深度调整", c6, 3000)
    
    # 迭代7：激进调整
    c7 = GameConfig(
        init_farmer=(3, 1, 2),   # 农夫财-2
        init_merchant=(8, 2, 1), # 商人福+1
        init_scholar=(4, 2, 5),
        init_monk=(1, 5, 4),     # 僧侣慧+1
        vow_diligent_fu=21,
        vow_poor_girl_fu=26,
        vow_teach_hui=14,
        vow_teacher_hui=15,
        vow_arhat_hui=14,
        vow_bodhisattva_fu=13,
        donate_merchant_bonus=2,
        practice_scholar_bonus=2,
        labor_farmer_bonus=0,    # 农夫劳作无奖励
    )
    r7 = test_config("[迭代7] 激进调整", c7, 3000)
    
    # 找最佳配置
    results = [
        ("基线", r_base),
        ("迭代1", r1),
        ("迭代2", r2),
        ("迭代3", r3),
        ("迭代4", r4),
        ("迭代5", r5),
        ("迭代6", r6),
        ("迭代7", r7),
    ]
    
    print("\n" + "=" * 60)
    print("配置对比")
    print("=" * 60)
    print(f"{'配置':<10} {'团队胜率':>8} {'农夫':>6} {'商人':>6} {'学者':>6} {'僧侣':>6} {'差距':>6}")
    print("-" * 60)
    
    best = None
    best_diff = 999
    
    for name, r in results:
        rates = r["role_win_rates"]
        vals = [v for v in rates.values() if v > 0]
        diff = max(vals) - min(vals) if vals else 0
        
        print(f"{name:<10} {r['team_win_rate']:>7.1f}% {rates.get('农夫',0):>5.1f}% {rates.get('商人',0):>5.1f}% {rates.get('学者',0):>5.1f}% {rates.get('僧侣',0):>5.1f}% {diff:>5.1f}%")
        
        if diff < best_diff and r["team_win_rate"] >= 60:
            best_diff = diff
            best = name
    
    print(f"\n最佳配置: {best} (胜率差距: {best_diff:.1f}%)")
    
    # 保存最佳配置
    if best == "迭代7":
        final_config = {
            "init_farmer": [3, 1, 2],
            "init_merchant": [8, 2, 1],
            "init_scholar": [4, 2, 5],
            "init_monk": [1, 5, 4],
            "vow_diligent_fu": 21,
            "vow_poor_girl_fu": 26,
            "vow_teach_hui": 14,
            "vow_teacher_hui": 15,
            "vow_arhat_hui": 14,
            "vow_bodhisattva_fu": 13,
            "donate_merchant_bonus": 2,
            "practice_scholar_bonus": 2,
            "labor_farmer_bonus": 0,
        }
    elif best == "迭代6":
        final_config = {
            "init_farmer": [4, 1, 2],
            "init_scholar": [4, 2, 5],
            "init_monk": [1, 5, 3],
            "vow_diligent_fu": 20,
            "vow_poor_girl_fu": 25,
            "vow_teach_hui": 14,
            "vow_teacher_hui": 16,
            "vow_arhat_hui": 15,
            "vow_bodhisattva_fu": 14,
            "donate_merchant_bonus": 2,
            "practice_scholar_bonus": 2,
        }
    else:
        final_config = {}
    
    with open("final_balance_config.json", "w", encoding="utf-8") as f:
        json.dump(final_config, f, ensure_ascii=False, indent=2)
    
    print(f"\n最终配置已保存到 final_balance_config.json")

if __name__ == "__main__":
    main()
