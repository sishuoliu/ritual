"""
《功德轮回：众生百态》v3.0 最终版模拟器

版本说明：
- 渡化差异化：不同职业付出不同资源
- 发愿系统：持续奖励+失败惩罚
- 资源递减：资源多者收益递减
- 皈依选择：皈依/不皈依都有活路
- 详细统计：所有行为收益分析

作者：AI助手
日期：2026年1月28日
"""

import random
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

# ===== 骰子系统 =====
def roll_2d6() -> int:
    return random.randint(1, 6) + random.randint(1, 6)

def dice_result(roll: int) -> str:
    if roll <= 4: return "CRIT_FAIL"
    elif roll <= 7: return "FAIL"
    elif roll <= 9: return "SUCCESS"
    else: return "CRIT_SUCCESS"

# ===== 角色系统 =====
class RoleType(Enum):
    FARMER = "农夫"
    MERCHANT = "商人"
    SCHOLAR = "学者"
    MONK = "僧侣"

class RefugeChoice(Enum):
    REFUGE = "皈依者"
    NON_REFUGE = "不皈依者"

# 角色初始值
ROLE_INIT = {
    RoleType.FARMER: {"wealth": 5, "fu": 2, "hui": 2},
    RoleType.MERCHANT: {"wealth": 8, "fu": 1, "hui": 1},
    RoleType.SCHOLAR: {"wealth": 3, "fu": 1, "hui": 4},
    RoleType.MONK: {"wealth": 0, "fu": 3, "hui": 3},
}

# 渡化成本差异（基于众生卡基础成本）
SAVE_COST = {
    RoleType.FARMER: {"wealth": 0, "fu": 0, "hui": 0},  # 标准成本
    RoleType.MERCHANT: {"wealth": 1, "fu": 0, "hui": 0},  # 多付1钱
    RoleType.SCHOLAR: {"wealth": -1, "fu": 0, "hui": 1},  # 少付1钱但付1慧
    RoleType.MONK: {"wealth": -1, "fu": 1, "hui": 0},  # 少付1钱但付1福
}

# 发愿系统
VOWS = {
    RoleType.FARMER: [
        {"name": "勤劳致福", "difficulty": "easy", "condition": "fu>=18", 
         "per_round": {"fu": 1}, "reward": 12, "penalty": -4},
        {"name": "贫女一灯", "difficulty": "hard", "condition": "fu>=25 and wealth<=3", 
         "per_round": {"fu": 2}, "reward": 24, "penalty": -8},
    ],
    RoleType.MERCHANT: [
        {"name": "财施功德", "difficulty": "easy", "condition": "donate_count>=4", 
         "per_round": {"wealth": 1, "hui": 1}, "reward": 14, "penalty": -4},
        {"name": "布施长者", "difficulty": "medium", "condition": "fu>=20 and save_count>=2", 
         "per_round": {"fu": 1, "hui": 1}, "reward": 20, "penalty": -8},
    ],
    RoleType.SCHOLAR: [
        {"name": "传道授业", "difficulty": "medium", "condition": "teach_count>=3", 
         "per_round": {"hui": 1}, "reward": 14, "penalty": -4},
        {"name": "万世师表", "difficulty": "hard", "condition": "hui>=26 and fu>=16", 
         "per_round": {"hui": 1}, "reward": 18, "penalty": -6},
    ],
    RoleType.MONK: [
        {"name": "阿罗汉果", "difficulty": "medium", "condition": "hui>=25", 
         "per_round": {"hui": 1}, "reward": 14, "penalty": -6},
        {"name": "菩萨道", "difficulty": "hard", "condition": "fu>=22 and save_count>=3", 
         "per_round": {"fu": 1}, "reward": 20, "penalty": -10},
    ],
}

# ===== 众生卡 =====
@dataclass
class SentientBeing:
    name: str
    base_cost: int
    fu_reward: int
    hui_reward: int
    turns_in_area: int = 0

SENTIENT_BEINGS = [
    SentientBeing("饥民", 2, 2, 1),
    SentientBeing("病者", 2, 2, 1),
    SentientBeing("孤儿", 3, 3, 1),
    SentientBeing("寡妇", 3, 2, 2),
    SentientBeing("落魄书生", 3, 1, 3),
    SentientBeing("迷途商贾", 4, 2, 2),
    SentientBeing("悔过恶人", 4, 4, 1),
    SentientBeing("垂死老者", 5, 3, 3),
]

# ===== 事件卡 =====
SHARED_EVENTS = [
    {"name": "旱灾", "effect": {"calamity": 2}},
    {"name": "洪水", "effect": {"calamity": 2}},
    {"name": "瘟疫", "effect": {"calamity": 3, "wealth_all": -1}},
    {"name": "丰收", "effect": {"wealth_all": 2}},
    {"name": "法会", "effect": {"fu_all": 1, "hui_all": 1}},
    {"name": "高僧开示", "effect": {"hui_all": 2}},
    {"name": "国泰民安", "effect": {"calamity": -2}},
    {"name": "浴佛节", "effect": {"fu_all": 2}},
]

# ===== 玩家状态 =====
@dataclass
class Player:
    role: RoleType
    refuge: RefugeChoice
    wealth: int
    fu: int
    hui: int
    vow: Optional[Dict] = None
    vow_active: bool = False
    
    # 行动统计
    save_count: int = 0
    donate_count: int = 0
    teach_count: int = 0
    protect_count: int = 0
    labor_count: int = 0
    practice_count: int = 0
    starve_count: int = 0
    help_streak: int = 0
    
    # 收益来源统计
    fu_from_save: int = 0
    fu_from_donate: int = 0
    fu_from_protect: int = 0
    fu_from_event: int = 0
    fu_from_vow: int = 0
    hui_from_practice: int = 0
    hui_from_save: int = 0
    hui_from_event: int = 0
    hui_from_vow: int = 0
    wealth_from_labor: int = 0
    wealth_from_invest: int = 0

# ===== 游戏状态 =====
@dataclass
class GameState:
    players: List[Player]
    calamity: int = 0
    sentient_area: List[SentientBeing] = field(default_factory=list)
    saved_count: int = 0
    current_round: int = 0
    max_rounds: int = 6
    event_deck: List[Dict] = field(default_factory=list)
    being_deck: List[SentientBeing] = field(default_factory=list)
    save_required: int = 6

# ===== 策略 =====
class Strategy(Enum):
    BALANCED = "平衡型"
    WEALTH_FOCUS = "财富型"
    MERIT_FOCUS = "福德型"
    WISDOM_FOCUS = "智慧型"

# ===== 游戏模拟器 =====
class GameSimulator:
    def __init__(self, strategies: List[Strategy] = None, refuges: List[RefugeChoice] = None):
        self.strategies = strategies or [Strategy.BALANCED] * 4
        self.refuges = refuges or [RefugeChoice.REFUGE] * 4
        self.state = None
    
    def initialize_game(self):
        roles = list(RoleType)
        players = []
        for i, role in enumerate(roles):
            init = ROLE_INIT[role]
            refuge = RefugeChoice.REFUGE if role == RoleType.MONK else self.refuges[i]
            player = Player(role, refuge, init["wealth"], init["fu"], init["hui"])
            
            # 皈依加成
            if refuge == RefugeChoice.REFUGE:
                player.fu += 1
                player.hui += 1
            else:
                player.wealth += 3
            
            # 分配发愿
            vows = VOWS[role]
            player.vow = random.choice(vows)
            player.vow_active = True
            
            players.append(player)
        
        self.state = GameState(players=players)
        self.state.event_deck = [e.copy() for e in SHARED_EVENTS]
        random.shuffle(self.state.event_deck)
        self.state.being_deck = [SentientBeing(b.name, b.base_cost, b.fu_reward, b.hui_reward) 
                                  for b in SENTIENT_BEINGS]
        random.shuffle(self.state.being_deck)
    
    def _diminishing_return(self, resource_amount: int, base_gain: int) -> int:
        """资源递减收益：资源越多，收益越少"""
        if resource_amount >= 20:
            return max(1, base_gain - 2)
        elif resource_amount >= 15:
            return max(1, base_gain - 1)
        return base_gain
    
    def _get_save_cost(self, player: Player, being: SentientBeing) -> Dict:
        """计算渡化成本"""
        role_cost = SAVE_COST[player.role]
        return {
            "wealth": being.base_cost + role_cost["wealth"],
            "fu": role_cost["fu"],
            "hui": role_cost["hui"],
        }
    
    def _can_save(self, player: Player) -> bool:
        """检查是否能渡化（慧≥5）"""
        return player.hui >= 5
    
    def _evaluate_action(self, player: Player, action: str, player_idx: int) -> float:
        """评估行动价值"""
        strategy = self.strategies[player_idx]
        role = player.role
        fu, hui, wealth = player.fu, player.hui, player.wealth
        calamity = self.state.calamity
        
        # 策略权重
        w_fu = 1.0
        w_hui = 1.0
        w_wealth = 0.3
        
        if strategy == Strategy.WEALTH_FOCUS:
            w_wealth = 1.0
            w_fu = 0.5
        elif strategy == Strategy.MERIT_FOCUS:
            w_fu = 1.5
        elif strategy == Strategy.WISDOM_FOCUS:
            w_hui = 1.5
        
        # 紧急度
        urgency = 1.0 + max(0, (calamity - 8) / 10)
        
        score = 0
        
        if action == "LABOR":
            if role == RoleType.MONK:
                return -10
            gain = 3 if player.refuge == RefugeChoice.REFUGE else 4
            gain = self._diminishing_return(wealth, gain)
            score = gain * w_wealth
            if wealth < 4:
                score += 3
        
        elif action == "PRACTICE":
            base = 2
            if role == RoleType.SCHOLAR:
                base = 3
            elif role == RoleType.MONK:
                base = 2
            gain = self._diminishing_return(hui, base)
            if player.refuge == RefugeChoice.REFUGE:
                gain += 1
            score = gain * w_hui
        
        elif action == "DONATE":
            if wealth < 3:
                return -5
            fu_gain = 2
            hui_gain = 1
            if role == RoleType.MERCHANT:
                # 商人布施递减（财富多时收益低）
                fu_gain = self._diminishing_return(wealth, 3)
                hui_gain = 2
            if calamity >= 10:
                fu_gain += 1
            score = fu_gain * w_fu * urgency + hui_gain * w_hui
        
        elif action == "SAVE":
            if not self._can_save(player):
                return -10
            affordable = [b for b in self.state.sentient_area 
                         if self._can_afford_save(player, b)]
            if not affordable:
                return -5
            best = max(affordable, key=lambda b: b.fu_reward + b.hui_reward)
            # 渡化递减
            save_bonus = max(0, 2 - player.save_count)
            fu_gain = self._diminishing_return(fu, best.fu_reward + save_bonus)
            hui_gain = best.hui_reward
            # 僧侣渡化加成（不用出钱）
            if role == RoleType.MONK:
                score += 3
            score += fu_gain * w_fu + hui_gain * w_hui
            # 紧急众生
            if any(b.turns_in_area >= 1 for b in affordable):
                score += 5
        
        elif action == "PROTECT":
            if wealth < 2:
                return -5
            fu_gain = 2
            if calamity >= 10:
                fu_gain += 1
            score = fu_gain * w_fu * urgency + w_hui
        
        elif action == "TEACH":
            if role != RoleType.SCHOLAR:
                return -10
            # 学者讲学递减
            fu_gain = self._diminishing_return(fu, 2)
            hui_gain = self._diminishing_return(hui, 1)
            score = fu_gain * w_fu + hui_gain * w_hui + 2  # 帮助他人加分
        
        elif action == "ALMS":
            if role != RoleType.MONK:
                return -10
            score = 2 * w_wealth + w_fu + w_hui
        
        elif action == "CEREMONY":
            if role != RoleType.MONK:
                return -10
            score = 4 * w_wealth - 2 * w_fu - w_hui
            if wealth < 1:
                score += 5
        
        return score
    
    def _can_afford_save(self, player: Player, being: SentientBeing) -> bool:
        cost = self._get_save_cost(player, being)
        return (player.wealth >= cost["wealth"] and 
                player.fu >= cost["fu"] and 
                player.hui >= cost["hui"])
    
    def _choose_action(self, player: Player, player_idx: int) -> str:
        role = player.role
        
        if role == RoleType.MONK:
            actions = ["ALMS", "CEREMONY", "SAVE", "PROTECT", "PRACTICE"]
        elif role == RoleType.SCHOLAR:
            actions = ["LABOR", "PRACTICE", "TEACH", "DONATE", "SAVE", "PROTECT"]
        else:
            actions = ["LABOR", "PRACTICE", "DONATE", "SAVE", "PROTECT"]
        
        scores = [(a, self._evaluate_action(player, a, player_idx) + random.gauss(0, 1)) 
                  for a in actions]
        return max(scores, key=lambda x: x[1])[0]
    
    def _execute_action(self, player: Player, action: str, player_idx: int):
        role = player.role
        
        if action == "LABOR":
            gain = 3 if player.refuge == RefugeChoice.REFUGE else 4
            gain = self._diminishing_return(player.wealth, gain)
            player.wealth += gain
            player.wealth_from_labor += gain
            player.labor_count += 1
        
        elif action == "PRACTICE":
            base = 2
            if role == RoleType.SCHOLAR:
                base = 3
            roll = roll_2d6()
            result = dice_result(roll)
            bonus = 1 if result == "CRIT_SUCCESS" else (-1 if result == "CRIT_FAIL" else 0)
            gain = self._diminishing_return(player.hui, max(1, base + bonus))
            if player.refuge == RefugeChoice.REFUGE:
                gain += 1
            player.hui += gain
            player.hui_from_practice += gain
            player.practice_count += 1
        
        elif action == "DONATE":
            if player.wealth >= 3:
                player.wealth -= 3
                fu_gain = 2
                hui_gain = 1
                if role == RoleType.MERCHANT:
                    fu_gain = self._diminishing_return(player.wealth, 3)
                    hui_gain = 2
                if self.state.calamity >= 10:
                    fu_gain += 1
                player.fu += fu_gain
                player.hui += hui_gain
                player.fu_from_donate += fu_gain
                self.state.calamity = max(0, self.state.calamity - 1)
                player.donate_count += 1
        
        elif action == "SAVE":
            if not self._can_save(player):
                return
            affordable = [b for b in self.state.sentient_area 
                         if self._can_afford_save(player, b)]
            if affordable:
                being = max(affordable, key=lambda b: b.fu_reward + b.hui_reward)
                cost = self._get_save_cost(player, being)
                player.wealth -= cost["wealth"]
                player.fu -= cost["fu"]
                player.hui -= cost["hui"]
                
                save_bonus = max(0, 2 - player.save_count)
                fu_gain = self._diminishing_return(player.fu, being.fu_reward + save_bonus)
                hui_gain = being.hui_reward
                
                player.fu += fu_gain
                player.hui += hui_gain
                player.fu_from_save += fu_gain
                player.hui_from_save += hui_gain
                player.save_count += 1
                self.state.saved_count += 1
                self.state.sentient_area.remove(being)
        
        elif action == "PROTECT":
            if player.wealth >= 2:
                player.wealth -= 2
                fu_gain = 2
                if self.state.calamity >= 10:
                    fu_gain += 1
                player.fu += fu_gain
                player.hui += 1
                player.fu_from_protect += fu_gain
                self.state.calamity = max(0, self.state.calamity - 2)
                player.protect_count += 1
        
        elif action == "TEACH":
            fu_gain = self._diminishing_return(player.fu, 2)
            hui_gain = self._diminishing_return(player.hui, 1)
            player.fu += fu_gain
            player.hui += hui_gain
            player.fu_from_event += fu_gain
            player.hui_from_practice += hui_gain
            # 帮助最低福者
            others = [p for i, p in enumerate(self.state.players) if i != player_idx]
            if others:
                target = min(others, key=lambda p: p.fu)
                target.fu += 1
                target.hui += 1
            player.teach_count += 1
        
        elif action == "ALMS":
            roll = roll_2d6()
            result = dice_result(roll)
            if result in ["SUCCESS", "CRIT_SUCCESS"]:
                player.wealth += 3
                player.fu += 1
                player.fu_from_event += 1
            else:
                player.wealth += 1
            player.hui += 1
            player.hui_from_practice += 1
        
        elif action == "CEREMONY":
            player.wealth += 4
            player.fu = max(0, player.fu - 2)
            player.hui = max(0, player.hui - 1)
    
    def _apply_vow_bonus(self, player: Player):
        """发愿每回合奖励"""
        if player.vow_active and player.vow:
            per_round = player.vow.get("per_round", {})
            if "fu" in per_round:
                player.fu += per_round["fu"]
                player.fu_from_vow += per_round["fu"]
            if "hui" in per_round:
                player.hui += per_round["hui"]
                player.hui_from_vow += per_round["hui"]
            if "wealth" in per_round:
                player.wealth += per_round["wealth"]
    
    def _check_vow(self, player: Player) -> int:
        """检查发愿是否达成"""
        if not player.vow:
            return 0
        
        vow = player.vow
        condition = vow["condition"]
        
        ctx = {
            "fu": player.fu,
            "hui": player.hui,
            "wealth": player.wealth,
            "save_count": player.save_count,
            "donate_count": player.donate_count,
            "teach_count": player.teach_count,
        }
        
        try:
            if eval(condition, {"__builtins__": {}}, ctx):
                return vow["reward"]
            else:
                return vow["penalty"]
        except:
            return 0
    
    def _run_event_phase(self):
        if self.state.event_deck:
            event = self.state.event_deck.pop(0)
            effect = event.get("effect", {})
            
            if "calamity" in effect:
                self.state.calamity = max(0, self.state.calamity + effect["calamity"])
            if "wealth_all" in effect:
                for p in self.state.players:
                    p.wealth = max(0, p.wealth + effect["wealth_all"])
            if "fu_all" in effect:
                for p in self.state.players:
                    bonus = 1.5 if p.refuge == RefugeChoice.REFUGE else 1.0
                    gain = int(effect["fu_all"] * bonus)
                    p.fu += gain
                    p.fu_from_event += gain
            if "hui_all" in effect:
                for p in self.state.players:
                    bonus = 1.5 if p.refuge == RefugeChoice.REFUGE else 1.0
                    gain = int(effect["hui_all"] * bonus)
                    p.hui += gain
                    p.hui_from_event += gain
    
    def _run_sentient_phase(self):
        for being in self.state.sentient_area[:]:
            being.turns_in_area += 1
            if being.turns_in_area >= 2:
                self.state.calamity += 3
                self.state.sentient_area.remove(being)
        
        if self.state.being_deck:
            self.state.sentient_area.append(self.state.being_deck.pop(0))
    
    def _apply_survival_cost(self):
        if self.state.current_round % 2 == 0:
            for player in self.state.players:
                player.wealth -= 1
                if player.wealth < 0:
                    player.wealth = 0
                    player.fu = max(0, player.fu - 1)
                    player.hui = max(0, player.hui - 1)
                    player.starve_count += 1
    
    def calculate_score(self, player: Player) -> float:
        """计算得分（金钱不计入）"""
        fu, hui = player.fu, player.hui
        base = math.sqrt(max(1, fu * hui)) * 3
        
        # 皈依加分
        refuge_bonus = 0
        if player.refuge == RefugeChoice.REFUGE:
            if fu >= 15 and hui >= 15:
                refuge_bonus = 16
            elif fu >= 12 and hui >= 12:
                refuge_bonus = 12
        else:
            if fu >= 20 and hui >= 20:
                refuge_bonus = 18
            elif fu >= 16 and hui >= 16:
                refuge_bonus = 10
        
        # 发愿加分/惩罚
        vow_bonus = self._check_vow(player)
        
        return base + refuge_bonus + vow_bonus
    
    def run_game(self) -> Tuple[bool, List[Dict]]:
        self.initialize_game()
        
        for round_num in range(1, self.state.max_rounds + 1):
            self.state.current_round = round_num
            
            self._run_event_phase()
            self._run_sentient_phase()
            
            for i, player in enumerate(self.state.players):
                self._apply_vow_bonus(player)
                for _ in range(2):
                    action = self._choose_action(player, i)
                    self._execute_action(player, action, i)
            
            self._apply_survival_cost()
            
            if self.state.calamity >= 20:
                break
        
        team_win = (self.state.calamity <= 12 and 
                   self.state.saved_count >= self.state.save_required)
        
        results = []
        for player in self.state.players:
            score = self.calculate_score(player) if team_win else 0
            vow_result = self._check_vow(player)
            results.append({
                "role": player.role,
                "refuge": player.refuge,
                "fu": player.fu,
                "hui": player.hui,
                "wealth": player.wealth,
                "score": score,
                "vow_success": vow_result > 0,
                "vow_bonus": vow_result,
                # 行动统计
                "save_count": player.save_count,
                "donate_count": player.donate_count,
                "teach_count": player.teach_count,
                "protect_count": player.protect_count,
                "labor_count": player.labor_count,
                "practice_count": player.practice_count,
                "starve_count": player.starve_count,
                # 收益来源
                "fu_from_save": player.fu_from_save,
                "fu_from_donate": player.fu_from_donate,
                "fu_from_protect": player.fu_from_protect,
                "fu_from_event": player.fu_from_event,
                "fu_from_vow": player.fu_from_vow,
                "hui_from_practice": player.hui_from_practice,
                "hui_from_save": player.hui_from_save,
                "hui_from_event": player.hui_from_event,
                "hui_from_vow": player.hui_from_vow,
            })
        
        return team_win, results

# ===== 测试器 =====
class BalanceTester:
    def __init__(self, num_simulations: int = 300):
        self.num_simulations = num_simulations
    
    def test_configuration(self, strategies: List[Strategy], 
                           refuges: List[RefugeChoice]) -> Dict:
        role_stats = {role: {
            "wins": 0, "scores": [], "fu": [], "hui": [], "wealth": [],
            "vow_success": 0, "vow_bonus": [],
            "save": [], "donate": [], "teach": [], "protect": [], "labor": [], "practice": [],
            "starve": [],
            "fu_save": [], "fu_donate": [], "fu_protect": [], "fu_event": [], "fu_vow": [],
            "hui_practice": [], "hui_save": [], "hui_event": [], "hui_vow": [],
        } for role in RoleType}
        
        team_wins = 0
        
        for _ in range(self.num_simulations):
            sim = GameSimulator(strategies, refuges)
            team_win, results = sim.run_game()
            
            if team_win:
                team_wins += 1
                winner_idx = max(range(len(results)), key=lambda i: results[i]["score"])
                
                for i, r in enumerate(results):
                    role = r["role"]
                    stats = role_stats[role]
                    
                    stats["scores"].append(r["score"])
                    stats["fu"].append(r["fu"])
                    stats["hui"].append(r["hui"])
                    stats["wealth"].append(r["wealth"])
                    stats["vow_bonus"].append(r["vow_bonus"])
                    
                    if r["vow_success"]:
                        stats["vow_success"] += 1
                    if i == winner_idx:
                        stats["wins"] += 1
                    
                    # 行动统计
                    stats["save"].append(r["save_count"])
                    stats["donate"].append(r["donate_count"])
                    stats["teach"].append(r["teach_count"])
                    stats["protect"].append(r["protect_count"])
                    stats["labor"].append(r["labor_count"])
                    stats["practice"].append(r["practice_count"])
                    stats["starve"].append(r["starve_count"])
                    
                    # 收益来源
                    stats["fu_save"].append(r["fu_from_save"])
                    stats["fu_donate"].append(r["fu_from_donate"])
                    stats["fu_protect"].append(r["fu_from_protect"])
                    stats["fu_event"].append(r["fu_from_event"])
                    stats["fu_vow"].append(r["fu_from_vow"])
                    stats["hui_practice"].append(r["hui_from_practice"])
                    stats["hui_save"].append(r["hui_from_save"])
                    stats["hui_event"].append(r["hui_from_event"])
                    stats["hui_vow"].append(r["hui_from_vow"])
        
        return {"team_wins": team_wins, "role_stats": role_stats}
    
    def run_full_test(self):
        print("=" * 80)
        print("《功德轮回》v3.0 最终版平衡性测试")
        print(f"模拟次数: {self.num_simulations}局/组")
        print("=" * 80)
        
        print("\n【v3.0 核心机制】")
        print("• 渡化差异：商人多付钱/学者付慧/僧侣免费")
        print("• 发愿系统：每回合奖励+成功/失败结算")
        print("• 资源递减：资源多者收益递减")
        print("• 皈依选择：皈依+1福慧/不皈依+3财富")
        print("• 渡化门槛：慧≥5")
        
        # 测试组合
        configs = [
            ("全皈依+平衡", [Strategy.BALANCED]*4, [RefugeChoice.REFUGE]*4),
            ("混合皈依", [Strategy.BALANCED]*4, 
             [RefugeChoice.NON_REFUGE, RefugeChoice.NON_REFUGE, 
              RefugeChoice.REFUGE, RefugeChoice.REFUGE]),
            ("财富策略", 
             [Strategy.BALANCED, Strategy.WEALTH_FOCUS, Strategy.BALANCED, Strategy.BALANCED],
             [RefugeChoice.REFUGE]*4),
            ("福德策略", 
             [Strategy.MERIT_FOCUS, Strategy.BALANCED, Strategy.BALANCED, Strategy.BALANCED],
             [RefugeChoice.REFUGE]*4),
        ]
        
        all_results = []
        
        for name, strategies, refuges in configs:
            print(f"\n{'='*80}")
            print(f"【{name}】")
            print("=" * 80)
            
            result = self.test_configuration(strategies, refuges)
            all_results.append((name, result))
            
            team_wins = result["team_wins"]
            team_rate = team_wins / self.num_simulations * 100
            print(f"\n团队胜率: {team_rate:.1f}%\n")
            
            if team_wins == 0:
                print("  无胜利局")
                continue
            
            # 输出角色统计
            for role in RoleType:
                stats = result["role_stats"][role]
                if not stats["scores"]:
                    continue
                
                win_rate = stats["wins"] / team_wins * 100
                avg_score = sum(stats["scores"]) / len(stats["scores"])
                avg_fu = sum(stats["fu"]) / len(stats["fu"])
                avg_hui = sum(stats["hui"]) / len(stats["hui"])
                avg_wealth = sum(stats["wealth"]) / len(stats["wealth"])
                vow_rate = stats["vow_success"] / team_wins * 100
                
                print(f"  {role.value}: 胜率={win_rate:.1f}%, 分数={avg_score:.1f}")
                print(f"    福={avg_fu:.1f}, 慧={avg_hui:.1f}, 财={avg_wealth:.1f}")
                print(f"    发愿成功率={vow_rate:.1f}%")
        
        # 详细收益分析
        print(f"\n{'='*80}")
        print("【详细收益分析（全皈依+平衡）】")
        print("=" * 80)
        
        result = all_results[0][1]
        if result["team_wins"] > 0:
            print(f"\n{'角色':<8} {'福-渡化':<8} {'福-布施':<8} {'福-护法':<8} {'福-事件':<8} {'福-发愿':<8}")
            print("-" * 50)
            for role in RoleType:
                stats = result["role_stats"][role]
                if stats["fu_save"]:
                    fs = sum(stats["fu_save"]) / len(stats["fu_save"])
                    fd = sum(stats["fu_donate"]) / len(stats["fu_donate"])
                    fp = sum(stats["fu_protect"]) / len(stats["fu_protect"])
                    fe = sum(stats["fu_event"]) / len(stats["fu_event"])
                    fv = sum(stats["fu_vow"]) / len(stats["fu_vow"])
                    print(f"{role.value:<8} {fs:<8.1f} {fd:<8.1f} {fp:<8.1f} {fe:<8.1f} {fv:<8.1f}")
            
            print(f"\n{'角色':<8} {'慧-修行':<8} {'慧-渡化':<8} {'慧-事件':<8} {'慧-发愿':<8}")
            print("-" * 40)
            for role in RoleType:
                stats = result["role_stats"][role]
                if stats["hui_practice"]:
                    hp = sum(stats["hui_practice"]) / len(stats["hui_practice"])
                    hs = sum(stats["hui_save"]) / len(stats["hui_save"])
                    he = sum(stats["hui_event"]) / len(stats["hui_event"])
                    hv = sum(stats["hui_vow"]) / len(stats["hui_vow"])
                    print(f"{role.value:<8} {hp:<8.1f} {hs:<8.1f} {he:<8.1f} {hv:<8.1f}")
            
            print(f"\n{'角色':<8} {'渡化次':<8} {'布施次':<8} {'劳作次':<8} {'修行次':<8} {'饥饿次':<8}")
            print("-" * 50)
            for role in RoleType:
                stats = result["role_stats"][role]
                if stats["save"]:
                    s = sum(stats["save"]) / len(stats["save"])
                    d = sum(stats["donate"]) / len(stats["donate"])
                    l = sum(stats["labor"]) / len(stats["labor"])
                    p = sum(stats["practice"]) / len(stats["practice"])
                    st = sum(stats["starve"]) / len(stats["starve"])
                    print(f"{role.value:<8} {s:<8.1f} {d:<8.1f} {l:<8.1f} {p:<8.1f} {st:<8.1f}")
        
        # 汇总比较
        print(f"\n{'='*80}")
        print("【汇总比较】")
        print("=" * 80)
        print(f"{'组合':<20} {'团队胜率':<12} {'最强':<10} {'最弱':<10} {'差距'}")
        print("-" * 60)
        
        for name, result in all_results:
            team_wins = result["team_wins"]
            team_rate = team_wins / self.num_simulations * 100
            
            if team_wins > 0:
                win_rates = [(role, stats["wins"] / team_wins * 100) 
                            for role, stats in result["role_stats"].items() if stats["wins"] >= 0]
                if win_rates:
                    best = max(win_rates, key=lambda x: x[1])
                    worst = min(win_rates, key=lambda x: x[1])
                    gap = best[1] - worst[1]
                    print(f"{name:<20} {team_rate:<12.1f}% {best[0].value:<10} {worst[0].value:<10} {gap:.1f}%")
                else:
                    print(f"{name:<20} {team_rate:<12.1f}% N/A")
            else:
                print(f"{name:<20} {team_rate:<12.1f}% N/A")

if __name__ == "__main__":
    tester = BalanceTester(num_simulations=300)
    tester.run_full_test()
