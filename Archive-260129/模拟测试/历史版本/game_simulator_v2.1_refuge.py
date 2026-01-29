"""
《功德轮回：众生百态》v2.1 皈依抉择版

版本说明：
- v2.1: 皈依系统+渡化门槛+金钱机制
  - 渡化需要慧≥5
  - 皈依选择：皈依者/不皈依者
  - 金钱利滚利（投资回报）
  - 劫难越高布施越有价值
  - 金钱不计入最终得分
  - 多策略组合测试

作者：AI助手
日期：2026年1月28日
"""

import random
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math
from itertools import product

# ===== 骰子系统 =====
def roll_2d6() -> int:
    return random.randint(1, 6) + random.randint(1, 6)

def dice_result(roll: int) -> str:
    if roll <= 4:
        return "CRIT_FAIL"
    elif roll <= 7:
        return "FAIL"
    elif roll <= 9:
        return "SUCCESS"
    else:
        return "CRIT_SUCCESS"

# ===== 角色系统 =====
class RoleType(Enum):
    FARMER = "农夫"
    MERCHANT = "商人"
    SCHOLAR = "学者"
    MONK = "僧侣"

class RefugeChoice(Enum):
    """皈依选择"""
    REFUGE = "皈依者"      # 皈依三宝
    NON_REFUGE = "不皈依者"  # 世俗修行

# 角色初始值 v2.1.2
ROLE_INIT = {
    RoleType.FARMER: {"wealth": 4, "fu": 2, "hui": 3},
    RoleType.MERCHANT: {"wealth": 6, "fu": 1, "hui": 3},  # 商人慧+2（经商悟道）
    RoleType.SCHOLAR: {"wealth": 2, "fu": 1, "hui": 4},  # 学者慧降低
    RoleType.MONK: {"wealth": 0, "fu": 3, "hui": 4},
}

# ===== 众生卡 =====
@dataclass
class SentientBeing:
    name: str
    cost: int
    fu_reward: int
    hui_reward: int
    turns_in_area: int = 0
    special: str = ""

SENTIENT_BEINGS = [
    SentientBeing("饥民", 2, 2, 1, 0, ""),
    SentientBeing("病者", 2, 2, 1, 0, ""),
    SentientBeing("孤儿", 3, 3, 1, 0, ""),
    SentientBeing("寡妇", 3, 2, 2, 0, ""),
    SentientBeing("落魄书生", 3, 1, 3, 0, ""),
    SentientBeing("迷途商贾", 4, 2, 2, 0, ""),
    SentientBeing("悔过恶人", 4, 4, 1, 0, ""),
    SentientBeing("垂死老者", 5, 3, 3, 0, ""),
    SentientBeing("绝望工匠", 4, 2, 2, 0, ""),
    SentientBeing("沉沦官吏", 5, 2, 4, 0, ""),
    SentientBeing("迷信村民", 3, 2, 2, 0, ""),
    SentientBeing("问道青年", 4, 2, 3, 0, ""),
]

# ===== 事件卡 =====
SHARED_EVENTS = [
    {"name": "旱灾", "effect": {"calamity": 2}},
    {"name": "洪水", "effect": {"calamity": 2}},
    {"name": "瘟疫", "effect": {"calamity": 3, "wealth_all": -1}},
    {"name": "战乱", "effect": {"calamity": 3}},
    {"name": "丰收", "effect": {"wealth_all": 2}},
    {"name": "法会", "effect": {"fu_all": 1, "hui_all": 1}},
    {"name": "高僧开示", "effect": {"hui_all": 2}},
    {"name": "国泰民安", "effect": {"calamity": -2}},
    {"name": "浴佛节", "effect": {"fu_all": 1}},
    {"name": "盂兰盆节", "effect": {"fu_all": 2}},
    {"name": "商路开通", "effect": {"wealth_all": 3}},
    {"name": "天灾预兆", "effect": {"calamity": 2}},
]

# ===== 行动类型 =====
class ActionType(Enum):
    LABOR = "劳作"
    PRACTICE = "修行"
    DONATE = "布施"
    SAVE = "渡化"
    PROTECT = "护法"
    INVEST = "投资"      # 新增：金钱利滚利
    SUPPORT_MONK = "供养"
    TEACH = "讲学"
    ALMS = "托钵"
    CEREMONY = "法事"

# ===== 策略枚举 =====
class Strategy(Enum):
    BALANCED = "平衡型"
    WEALTH_FIRST = "财富优先"  # 前期攒钱
    MERIT_FIRST = "福德优先"   # 前期做好事
    WISDOM_FIRST = "智慧优先"  # 重慧
    GREEDY = "贪婪型"         # 金钱制胜尝试

# ===== 玩家状态 =====
@dataclass
class Player:
    role: RoleType
    refuge: RefugeChoice
    wealth: int
    fu: int
    hui: int
    investment: int = 0  # 投资金额
    
    save_count: int = 0
    donate_count: int = 0
    teach_count: int = 0
    protect_count: int = 0
    labor_count: int = 0
    starve_count: int = 0
    help_streak: int = 0
    max_streak: int = 0
    helped_this_turn: bool = False
    
    fu_from_save: int = 0
    fu_from_donate: int = 0
    fu_from_protect: int = 0
    fu_from_event: int = 0
    hui_from_practice: int = 0
    hui_from_save: int = 0
    hui_from_event: int = 0

# ===== 游戏状态 =====
@dataclass
class GameState:
    players: List[Player]
    calamity: int = 0
    sentient_area: List[SentientBeing] = field(default_factory=list)
    saved_count: int = 0
    current_round: int = 0
    max_rounds: int = 6
    shared_event_deck: List[Dict] = field(default_factory=list)
    being_deck: List[SentientBeing] = field(default_factory=list)
    event_modifiers: Dict = field(default_factory=dict)
    save_required: int = 6
    
    def __post_init__(self):
        if not self.shared_event_deck:
            self.shared_event_deck = [e.copy() for e in SHARED_EVENTS]
            random.shuffle(self.shared_event_deck)
        if not self.being_deck:
            self.being_deck = [SentientBeing(b.name, b.cost, b.fu_reward, b.hui_reward, 0, b.special)
                              for b in SENTIENT_BEINGS]
            random.shuffle(self.being_deck)

# ===== 游戏模拟器 =====
class GameSimulator:
    def __init__(self, num_players: int = 4, strategies: List[Strategy] = None,
                 refuge_choices: List[RefugeChoice] = None):
        self.num_players = num_players
        self.strategies = strategies or [Strategy.BALANCED] * num_players
        self.refuge_choices = refuge_choices or [RefugeChoice.REFUGE] * num_players
        self.state = None
    
    def initialize_game(self):
        roles = list(RoleType)[:self.num_players]
        players = []
        for i, role in enumerate(roles):
            init = ROLE_INIT[role]
            # 僧侣必须皈依
            refuge = RefugeChoice.REFUGE if role == RoleType.MONK else self.refuge_choices[i]
            player = Player(role, refuge, init["wealth"], init["fu"], init["hui"])
            
            # 皈依者加成：初始+1福+1慧
            if refuge == RefugeChoice.REFUGE:
                player.fu += 1
                player.hui += 1
            # 不皈依者加成：初始+3财富
            else:
                player.wealth += 3
            
            players.append(player)
        self.state = GameState(players=players)
    
    def _get_monk_idx(self) -> Optional[int]:
        for i, p in enumerate(self.state.players):
            if p.role == RoleType.MONK:
                return i
        return None
    
    def run_shared_event(self):
        if not self.state.shared_event_deck:
            return
        event = self.state.shared_event_deck.pop(0)
        effect = event.get("effect", {})
        
        if "calamity" in effect:
            self.state.calamity = max(0, self.state.calamity + effect["calamity"])
        if "wealth_all" in effect:
            for p in self.state.players:
                p.wealth = max(0, p.wealth + effect["wealth_all"])
        if "fu_all" in effect:
            for p in self.state.players:
                # 皈依者事件福收益+50%
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
    
    def run_sentient_phase(self):
        for being in self.state.sentient_area[:]:
            being.turns_in_area += 1
            if being.turns_in_area >= 2:
                self.state.calamity += 3
                self.state.sentient_area.remove(being)
        
        if self.state.being_deck:
            new = self.state.being_deck.pop(0)
            self.state.sentient_area.append(new)
    
    def _evaluate_action(self, player: Player, action: ActionType, player_idx: int) -> float:
        """评估行动预期收益"""
        role = player.role
        strategy = self.strategies[player_idx]
        fu, hui, wealth = player.fu, player.hui, player.wealth
        remaining = self.state.max_rounds - self.state.current_round
        calamity = self.state.calamity
        
        # 策略权重
        fu_weight = 1.0
        hui_weight = 1.0
        wealth_weight = 0.3
        
        if strategy == Strategy.WEALTH_FIRST:
            wealth_weight = 1.0
            if self.state.current_round <= 3:
                fu_weight = 0.3
        elif strategy == Strategy.MERIT_FIRST:
            fu_weight = 1.5
            wealth_weight = 0.2
        elif strategy == Strategy.WISDOM_FIRST:
            hui_weight = 1.5
        elif strategy == Strategy.GREEDY:
            wealth_weight = 1.5
            fu_weight = 0.5
        
        # 劫难紧急度：越高布施越有价值
        calamity_multiplier = 1.0 + max(0, (calamity - 6) / 6)
        
        score = 0
        
        if action == ActionType.LABOR:
            if role == RoleType.MONK:
                return -10
            score = 3 * wealth_weight
            if wealth < 4:
                score += 3
        
        elif action == ActionType.PRACTICE:
            base = 2
            if role == RoleType.SCHOLAR:
                base = 3
            score = base * hui_weight
        
        elif action == ActionType.DONATE:
            if wealth < 3:
                return -5
            fu_gain = 2
            if role == RoleType.MERCHANT:
                fu_gain = 4
            # 劫难越高布施越有价值
            score = fu_gain * fu_weight * calamity_multiplier + hui_weight
        
        elif action == ActionType.PROTECT:
            if wealth < 2:
                return -5
            score = (2 * fu_weight + hui_weight) * calamity_multiplier
        
        elif action == ActionType.SAVE:
            # 渡化需要慧≥5
            if hui < 5:
                return -10
            affordable = [b for b in self.state.sentient_area if wealth >= b.cost]
            if not affordable:
                return -5
            best = max(affordable, key=lambda b: (b.fu_reward + b.hui_reward) / b.cost)
            save_bonus = max(0, 2 - player.save_count)
            score = (best.fu_reward + save_bonus) * fu_weight + best.hui_reward * hui_weight
            urgent = [b for b in affordable if b.turns_in_area >= 1]
            if urgent:
                score += 5
        
        elif action == ActionType.INVEST:
            if wealth < 5:
                return -5
            # 投资回报：后期收益更高
            expected_return = 3 * remaining * 0.5 * wealth_weight
            score = expected_return
        
        elif action == ActionType.TEACH:
            if role != RoleType.SCHOLAR:
                return -10
            score = 2 * fu_weight + hui_weight
        
        elif action == ActionType.ALMS:
            if role != RoleType.MONK:
                return -10
            score = 2 * wealth_weight + fu_weight + hui_weight
        
        elif action == ActionType.CEREMONY:
            if role != RoleType.MONK:
                return -10
            # 法事：财富多但损福慧
            score = 4 * wealth_weight - 2 * fu_weight - hui_weight
            if wealth < 1:
                score += 5
        
        elif action == ActionType.SUPPORT_MONK:
            monk_idx = self._get_monk_idx()
            if monk_idx is None or monk_idx == player_idx:
                return -10
            if wealth < 2:
                return -5
            score = 2 * fu_weight
        
        return score
    
    def _choose_action(self, player: Player, player_idx: int) -> ActionType:
        role = player.role
        strategy = self.strategies[player_idx]
        
        if role == RoleType.MONK:
            actions = [ActionType.ALMS, ActionType.CEREMONY, ActionType.SAVE, 
                      ActionType.PROTECT, ActionType.PRACTICE]
        elif role == RoleType.SCHOLAR:
            actions = [ActionType.LABOR, ActionType.PRACTICE, ActionType.TEACH,
                      ActionType.DONATE, ActionType.SAVE, ActionType.PROTECT,
                      ActionType.INVEST, ActionType.SUPPORT_MONK]
        else:
            actions = [ActionType.LABOR, ActionType.PRACTICE, ActionType.DONATE,
                      ActionType.SAVE, ActionType.PROTECT, ActionType.INVEST,
                      ActionType.SUPPORT_MONK]
        
        scores = [(a, self._evaluate_action(player, a, player_idx) + random.gauss(0, 1)) 
                  for a in actions]
        best = max(scores, key=lambda x: x[1])[0]
        return best
    
    def _execute_action(self, player: Player, action: ActionType, player_idx: int):
        role = player.role
        calamity = self.state.calamity
        
        if action == ActionType.LABOR:
            if role == RoleType.MONK:
                player.wealth += 1
                player.fu = max(0, player.fu - 1)
            else:
                # 不皈依者劳作+4财富（世俗成功）
                gain = 4 if player.refuge == RefugeChoice.NON_REFUGE else 3
                player.wealth += gain
            player.labor_count += 1
        
        elif action == ActionType.PRACTICE:
            base = 2
            if role == RoleType.SCHOLAR:
                base = 3
            roll = roll_2d6()
            result = dice_result(roll)
            bonus = 1 if result == "CRIT_SUCCESS" else (-1 if result == "CRIT_FAIL" else 0)
            gain = max(1, base + bonus)
            # 皈依者修行+1慧
            if player.refuge == RefugeChoice.REFUGE:
                gain += 1
            player.hui += gain
            player.hui_from_practice += gain
        
        elif action == ActionType.DONATE:
            if player.wealth >= 3:
                player.wealth -= 3
                fu_gain = 2
                hui_gain = 1
                if role == RoleType.MERCHANT:
                    fu_gain = 2  # 商人布施福与普通人相同
                    hui_gain = 2  # 商人布施+2慧（结缘悟道）
                # 劫难越高布施越有价值（但有上限）
                if calamity >= 10:
                    fu_gain += 1
                player.fu += fu_gain
                player.fu_from_donate += fu_gain
                player.hui += hui_gain
                player.hui_from_event += hui_gain
                self.state.calamity = max(0, self.state.calamity - 1)
                player.donate_count += 1
                player.helped_this_turn = True
        
        elif action == ActionType.PROTECT:
            if player.wealth >= 2:
                player.wealth -= 2
                fu_gain = 2
                if calamity >= 10:
                    fu_gain += 2
                elif calamity >= 6:
                    fu_gain += 1
                player.fu += fu_gain
                player.fu_from_protect += fu_gain
                player.hui += 1
                self.state.calamity = max(0, self.state.calamity - 2)
                player.protect_count += 1
                player.helped_this_turn = True
        
        elif action == ActionType.SAVE:
            # 渡化门槛：慧≥5
            if player.hui < 5:
                return
            affordable = [b for b in self.state.sentient_area if player.wealth >= b.cost]
            if affordable:
                being = max(affordable, key=lambda b: (b.fu_reward + b.hui_reward) / b.cost)
                player.wealth -= being.cost
                save_bonus = max(0, 2 - player.save_count)
                fu_gain = being.fu_reward + save_bonus
                hui_gain = being.hui_reward
                player.fu += fu_gain
                player.hui += hui_gain
                player.fu_from_save += fu_gain
                player.hui_from_save += hui_gain
                player.save_count += 1
                self.state.saved_count += 1
                self.state.sentient_area.remove(being)
                player.helped_this_turn = True
        
        elif action == ActionType.INVEST:
            if player.wealth >= 5:
                player.investment += 5
                player.wealth -= 5
        
        elif action == ActionType.TEACH:
            player.hui += 1
            player.hui_from_practice += 1
            player.fu += 2
            player.fu_from_event += 2
            others = [p for i, p in enumerate(self.state.players) if i != player_idx]
            if others:
                target = min(others, key=lambda p: p.fu)
                target.fu += 1
                target.hui += 1
            player.teach_count += 1
            player.helped_this_turn = True
        
        elif action == ActionType.ALMS:
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
        
        elif action == ActionType.CEREMONY:
            player.wealth += 4
            player.fu = max(0, player.fu - 2)
            player.hui = max(0, player.hui - 1)
        
        elif action == ActionType.SUPPORT_MONK:
            monk_idx = self._get_monk_idx()
            if monk_idx is not None and player.wealth >= 2:
                player.wealth -= 2
                monk = self.state.players[monk_idx]
                monk.wealth += 2
                monk.fu += 1
                player.fu += 2
                player.fu_from_donate += 2
                player.helped_this_turn = True
    
    def _update_help_streak(self):
        for player in self.state.players:
            if player.helped_this_turn:
                player.help_streak += 1
                player.max_streak = max(player.max_streak, player.help_streak)
                if player.help_streak >= 3 and player.help_streak <= 4:
                    fu_bonus = 1
                    hui_bonus = 1
                    if player.role == RoleType.FARMER:
                        fu_bonus = 2
                    player.fu += fu_bonus
                    player.hui += hui_bonus
                    player.fu_from_event += fu_bonus
                    player.hui_from_event += hui_bonus
            else:
                player.help_streak = 0
    
    def _apply_survival_and_investment(self):
        """生存消耗 + 投资回报"""
        if self.state.current_round % 2 == 0:
            for player in self.state.players:
                # 投资回报：每2轮+30%
                if player.investment > 0:
                    returns = int(player.investment * 0.3)
                    player.wealth += returns
                
                # 生存消耗
                player.wealth -= 1
                if player.wealth < 0:
                    player.wealth = 0
                    player.fu = max(0, player.fu - 1)
                    player.hui = max(0, player.hui - 1)
                    player.starve_count += 1
    
    def _settle_investment(self, player: Player):
        """游戏结束时结算投资"""
        if player.investment > 0:
            # 返还本金（不计入得分）
            player.wealth += player.investment
            player.investment = 0
    
    def calculate_score(self, player: Player) -> float:
        """计算得分：金钱不计入"""
        fu, hui = player.fu, player.hui
        base = math.sqrt(max(1, fu * hui)) * 3
        
        # 皈依者加分
        refuge_bonus = 0
        if player.refuge == RefugeChoice.REFUGE:
            if fu >= 15 and hui >= 15:
                refuge_bonus = 16  # 福慧双修
            elif fu >= 12 and hui >= 12:
                refuge_bonus = 12
        else:
            # 不皈依者：需要更高福慧才能获得加分
            if fu >= 20 and hui >= 20:
                refuge_bonus = 18  # 世俗觉悟（更难但可达成）
            elif fu >= 16 and hui >= 16:
                refuge_bonus = 10
        
        return base + refuge_bonus
    
    def run_game(self) -> Tuple[bool, List[Dict]]:
        self.initialize_game()
        
        for round_num in range(1, self.state.max_rounds + 1):
            self.state.current_round = round_num
            self.run_shared_event()
            self.run_sentient_phase()
            
            for i, player in enumerate(self.state.players):
                for _ in range(2):
                    action = self._choose_action(player, i)
                    self._execute_action(player, action, i)
            
            self._update_help_streak()
            self._apply_survival_and_investment()
            
            for player in self.state.players:
                player.helped_this_turn = False
            
            if self.state.calamity >= 20:
                break
        
        # 结算投资
        for player in self.state.players:
            self._settle_investment(player)
        
        team_win = (self.state.calamity <= 12 and 
                   self.state.saved_count >= self.state.save_required)
        
        results = []
        for i, player in enumerate(self.state.players):
            score = self.calculate_score(player) if team_win else 0
            results.append({
                "role": player.role,
                "refuge": player.refuge,
                "strategy": self.strategies[i],
                "fu": player.fu,
                "hui": player.hui,
                "wealth": player.wealth,
                "score": score,
                "save_count": player.save_count,
                "donate_count": player.donate_count,
                "starve_count": player.starve_count,
            })
        
        return team_win, results

# ===== 多策略组合测试器 =====
class StrategyTester:
    def __init__(self, num_simulations: int = 200):
        self.num_simulations = num_simulations
    
    def test_strategy_combination(self, strategies: List[Strategy], 
                                   refuges: List[RefugeChoice]) -> Dict:
        """测试特定策略+皈依组合"""
        role_stats = {role: {"wins": 0, "scores": [], "fu": [], "hui": [], "wealth": []}
                     for role in RoleType}
        team_wins = 0
        
        for _ in range(self.num_simulations):
            sim = GameSimulator(4, strategies, refuges)
            team_win, results = sim.run_game()
            
            if team_win:
                team_wins += 1
                winner_idx = max(range(len(results)), key=lambda i: results[i]["score"])
                for i, r in enumerate(results):
                    role = r["role"]
                    role_stats[role]["scores"].append(r["score"])
                    role_stats[role]["fu"].append(r["fu"])
                    role_stats[role]["hui"].append(r["hui"])
                    role_stats[role]["wealth"].append(r["wealth"])
                    if i == winner_idx:
                        role_stats[role]["wins"] += 1
        
        return {
            "team_win_rate": team_wins / self.num_simulations * 100,
            "role_stats": role_stats,
            "team_wins": team_wins
        }
    
    def run_full_test(self):
        print("=" * 80)
        print("《功德轮回》v2.1 皈依抉择版 - 多策略组合测试")
        print(f"每组测试模拟次数: {self.num_simulations}局")
        print("=" * 80)
        
        print("\n【v2.1 新机制】")
        print("• 渡化门槛：慧≥5才能渡化")
        print("• 皈依选择：皈依者/不皈依者")
        print("• 金钱利滚利：投资5财→每2轮+30%")
        print("• 劫难越高布施越有价值")
        print("• 金钱不计入最终得分")
        
        # 测试组合1：全平衡+全皈依
        print("\n" + "=" * 80)
        print("【组合1：全平衡策略 + 全皈依】")
        print("=" * 80)
        result1 = self.test_strategy_combination(
            [Strategy.BALANCED] * 4,
            [RefugeChoice.REFUGE] * 4
        )
        self._print_result(result1)
        
        # 测试组合2：全平衡+混合皈依
        print("\n" + "=" * 80)
        print("【组合2：全平衡策略 + 混合皈依（农夫商人不皈依）】")
        print("=" * 80)
        result2 = self.test_strategy_combination(
            [Strategy.BALANCED] * 4,
            [RefugeChoice.NON_REFUGE, RefugeChoice.NON_REFUGE, 
             RefugeChoice.REFUGE, RefugeChoice.REFUGE]
        )
        self._print_result(result2)
        
        # 测试组合3：财富优先策略（商人）
        print("\n" + "=" * 80)
        print("【组合3：商人财富优先 + 其他平衡】")
        print("=" * 80)
        result3 = self.test_strategy_combination(
            [Strategy.BALANCED, Strategy.WEALTH_FIRST, 
             Strategy.BALANCED, Strategy.BALANCED],
            [RefugeChoice.REFUGE] * 4
        )
        self._print_result(result3)
        
        # 测试组合4：贪婪策略测试
        print("\n" + "=" * 80)
        print("【组合4：商人贪婪策略（不皈依）测试】")
        print("=" * 80)
        result4 = self.test_strategy_combination(
            [Strategy.BALANCED, Strategy.GREEDY, 
             Strategy.BALANCED, Strategy.BALANCED],
            [RefugeChoice.REFUGE, RefugeChoice.NON_REFUGE, 
             RefugeChoice.REFUGE, RefugeChoice.REFUGE]
        )
        self._print_result(result4)
        
        # 测试组合5：福德优先vs智慧优先
        print("\n" + "=" * 80)
        print("【组合5：农夫福德优先 + 学者智慧优先】")
        print("=" * 80)
        result5 = self.test_strategy_combination(
            [Strategy.MERIT_FIRST, Strategy.BALANCED, 
             Strategy.WISDOM_FIRST, Strategy.BALANCED],
            [RefugeChoice.REFUGE] * 4
        )
        self._print_result(result5)
        
        # 汇总比较
        print("\n" + "=" * 80)
        print("【汇总比较】")
        print("=" * 80)
        print(f"{'组合':<30} {'团队胜率':<12} {'最强角色':<15} {'商人胜率'}")
        print("-" * 70)
        
        configs = [
            ("全皈依+平衡", result1),
            ("混合皈依+平衡", result2),
            ("商人财富优先", result3),
            ("商人贪婪不皈依", result4),
            ("福德vs智慧", result5),
        ]
        
        for name, r in configs:
            team_rate = r["team_win_rate"]
            if r["team_wins"] > 0:
                best_role = max(r["role_stats"].items(), 
                               key=lambda x: x[1]["wins"])[0].value
                merchant_wins = r["role_stats"][RoleType.MERCHANT]["wins"]
                merchant_rate = merchant_wins / r["team_wins"] * 100
            else:
                best_role = "N/A"
                merchant_rate = 0
            print(f"{name:<30} {team_rate:<12.1f}% {best_role:<15} {merchant_rate:.1f}%")
    
    def _print_result(self, result: Dict):
        team_rate = result["team_win_rate"]
        team_wins = result["team_wins"]
        print(f"\n团队胜率: {team_rate:.1f}%\n")
        
        if team_wins == 0:
            print("  无胜利局")
            return
        
        for role in RoleType:
            stats = result["role_stats"][role]
            if not stats["scores"]:
                continue
            
            win_rate = stats["wins"] / team_wins * 100
            avg_score = sum(stats["scores"]) / len(stats["scores"])
            avg_fu = sum(stats["fu"]) / len(stats["fu"])
            avg_hui = sum(stats["hui"]) / len(stats["hui"])
            avg_wealth = sum(stats["wealth"]) / len(stats["wealth"])
            
            print(f"  {role.value}: 胜率={win_rate:.1f}%")
            print(f"    福={avg_fu:.1f}, 慧={avg_hui:.1f}, 财富={avg_wealth:.1f}, 分={avg_score:.1f}")

if __name__ == "__main__":
    tester = StrategyTester(num_simulations=300)
    tester.run_full_test()
