"""
《功德轮回：众生百态》v1.7 详细统计版

v1.7 修改：
1. 每回合扣除1财富维持生存（财富<0时-1福-1慧）
2. 农夫不再有劳作+慧，改为"渡化费用-1"
3. 增加详细统计：福慧来源分析
4. 持续帮助奖励：门槛降低为2轮

v1.6 保留：
- 托钵：+2财富+1福+1慧
- 法事：+4财富-2福-2慧
- 讲法：他人+2福+1慧，自己+1福
- 商人布施+1福
"""

import random
import statistics
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from collections import defaultdict

class ActionType(Enum):
    LABOR = "劳作"
    PRACTICE = "修行"
    DONATE = "布施"
    SAVE = "渡化"
    PROTECT = "护法"
    ALMS = "托钵"
    CEREMONY = "法事"
    TEACH = "讲法"
    SUPPORT_MONK = "供养"

class RoleType(Enum):
    FARMER = "农夫"
    MERCHANT = "商人"
    OFFICIAL = "官员"
    MONK = "僧侣"

@dataclass
class SentientBeing:
    name: str
    cost: int
    fu_reward: int
    hui_reward: int = 0
    turns_in_area: int = 0
    special: str = ""

@dataclass
class Player:
    role: RoleType
    wealth: int
    fu: int
    hui: int
    actions_per_turn: int = 2
    help_streak: int = 0
    save_count: int = 0
    helped_this_turn: bool = False
    # v1.7: 详细统计字段
    fu_from_save: int = 0       # 来自渡化的福
    fu_from_donate: int = 0     # 来自布施的福
    fu_from_protect: int = 0    # 来自护法的福
    fu_from_streak: int = 0     # 来自持续帮助的福
    fu_from_teach: int = 0      # 来自讲法的福
    fu_from_alms: int = 0       # 来自托钵的福
    hui_from_practice: int = 0  # 来自修行的慧
    hui_from_streak: int = 0    # 来自持续帮助的慧
    hui_from_alms: int = 0      # 来自托钵的慧
    hui_from_save: int = 0      # 来自渡化的慧
    max_streak: int = 0         # 最大连续帮助轮数
    labor_count: int = 0        # 劳作次数
    starve_count: int = 0       # 饥饿次数

# v1.7.1: 重新调整初始值
ROLE_INIT = {
    RoleType.FARMER: {"wealth": 4, "fu": 1, "hui": 1},   # 无特殊优势
    RoleType.MERCHANT: {"wealth": 6, "fu": 0, "hui": 1}, # 财富优势
    RoleType.OFFICIAL: {"wealth": 5, "fu": 2, "hui": 2}, # 福慧双优势
    RoleType.MONK: {"wealth": 1, "fu": 2, "hui": 3},     # 低财富，高福慧
}

SENTIENT_BEINGS = [
    SentientBeing("饥民", 3, 3, 1),
    SentientBeing("病人", 4, 3, 2),
    SentientBeing("孤儿", 3, 4, 1),
    SentientBeing("老者", 2, 2, 1),
    SentientBeing("流浪者", 4, 4, 2),
    SentientBeing("冤魂", 5, 4, 2, special="calamity_minus1"),
    SentientBeing("恶人", 6, 5, 3, special="calamity_plus1_per_turn"),
    SentientBeing("富商", 4, 3, 2, special="wealth_all"),
    SentientBeing("官吏", 5, 4, 2),
    SentientBeing("将军", 5, 4, 3, special="calamity_minus2"),
    SentientBeing("皇族", 7, 5, 4),
    SentientBeing("高僧", 5, 3, 5),
]

EVENTS = [
    {"name": "旱灾", "type": "disaster", "calamity": 2},
    {"name": "洪水", "type": "disaster", "calamity": 2},
    {"name": "瘟疫", "type": "disaster", "calamity": 2, "wealth_all": -1},
    {"name": "战乱", "type": "disaster", "calamity": 3},
    {"name": "饥荒", "type": "disaster", "calamity": 2},
    {"name": "妖邪", "type": "disaster", "calamity": 2},
    {"name": "丰收", "type": "opportunity", "wealth_all": 2},
    {"name": "法会", "type": "opportunity", "fu_all": 1, "hui_all": 1},
    {"name": "施主到来", "type": "opportunity", "wealth_all": 2},
    {"name": "高僧开示", "type": "opportunity", "hui_all": 2},
    {"name": "国泰民安", "type": "opportunity", "calamity": -2},
    {"name": "佛诞节", "type": "opportunity", "free_save": True, "fu_all": 1},
]

class Strategy(Enum):
    BALANCED = "平衡型"
    SELFISH = "自私型"
    ALTRUISTIC = "利他型"
    SMART = "智能型"

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
    game_over: bool = False
    team_win: bool = False
    event_modifiers: Dict = field(default_factory=dict)
    calamity_limit: int = 20
    calamity_win_max: int = 12
    save_required: int = 6
    
    def __post_init__(self):
        if not self.event_deck:
            self.event_deck = [e.copy() for e in EVENTS]
            random.shuffle(self.event_deck)
        if not self.being_deck:
            self.being_deck = [SentientBeing(b.name, b.cost, b.fu_reward, b.hui_reward, 0, b.special) 
                              for b in SENTIENT_BEINGS]
            random.shuffle(self.being_deck)


class GameSimulator:
    def __init__(self, num_players: int = 4, strategies: List[Strategy] = None):
        self.num_players = num_players
        self.strategies = strategies or [Strategy.BALANCED] * num_players
        self.state = None
        
    def initialize_game(self):
        roles = list(RoleType)[:self.num_players]
        players = []
        for role in roles:
            init = ROLE_INIT[role]
            players.append(Player(role, init["wealth"], init["fu"], init["hui"]))
        self.state = GameState(players=players)
    
    def _get_monk_idx(self) -> Optional[int]:
        for i, p in enumerate(self.state.players):
            if p.role == RoleType.MONK:
                return i
        return None
        
    def run_event_phase(self):
        if not self.state.event_deck:
            return
        event = self.state.event_deck.pop(0)
        
        if "calamity" in event:
            self.state.calamity = max(0, self.state.calamity + event["calamity"])
        if "wealth_all" in event:
            for p in self.state.players:
                p.wealth = max(0, p.wealth + event["wealth_all"])
        if "fu_all" in event:
            for p in self.state.players:
                p.fu += event["fu_all"]
        if "hui_all" in event:
            for p in self.state.players:
                p.hui += event["hui_all"]
        if "free_save" in event:
            self.state.event_modifiers["free_save"] = True
    
    def run_sentient_phase(self):
        for being in self.state.sentient_area:
            being.turns_in_area += 1
            if being.special == "calamity_plus1_per_turn":
                self.state.calamity += 1
        
        timeout_beings = [b for b in self.state.sentient_area if b.turns_in_area >= 2]
        for being in timeout_beings:
            self.state.calamity += 3
            self.state.sentient_area.remove(being)
        
        if self.state.being_deck:
            new_being = self.state.being_deck.pop(0)
            self.state.sentient_area.append(new_being)
    
    def run_action_phase(self):
        for p in self.state.players:
            p.helped_this_turn = False
        
        for i, player in enumerate(self.state.players):
            strategy = self.strategies[i]
            for _ in range(player.actions_per_turn):
                action = self._choose_action(player, strategy, i)
                self._execute_action(player, action, i)
    
    def _evaluate_action_score(self, player: Player, action: ActionType, player_idx: int) -> float:
        """评估单个行动的预期收益分数"""
        role = player.role
        fu, hui, wealth = player.fu, player.hui, player.wealth
        remaining_rounds = self.state.max_rounds - self.state.current_round
        saves_needed = self.state.save_required - self.state.saved_count
        calamity = self.state.calamity
        
        # 福慧平衡系数：差距越大，需要补充的那个价值越高
        fu_need = max(0, hui - fu) * 0.5  # 福不足时，福的额外价值
        hui_need = max(0, fu - hui) * 0.5  # 慧不足时，慧的额外价值
        
        # 紧急度系数
        calamity_urgency = max(0, (calamity - 8) / 12) * 2
        save_urgency = max(0, (saves_needed - remaining_rounds) / 3) * 2
        
        # 渡化递减奖励预估
        save_bonus = max(0, 3 - player.save_count)
        
        score = 0
        
        if action == ActionType.LABOR:
            if role == RoleType.MONK:
                return -10  # 僧侣不应劳作
            score = 3 * 0.3  # 财富价值较低
            # 如果财富紧张，劳作价值更高
            if wealth < 4:
                score += 2
            if wealth < 2:
                score += 3
        
        elif action == ActionType.PRACTICE:
            score = 2 + hui_need  # 基础慧+额外需求
            if role == RoleType.MONK:
                score += 1  # 僧侣修行加成
        
        elif action == ActionType.DONATE:
            if wealth < 3:
                return -5  # 财富不够
            fu_gain = 2
            if role == RoleType.MERCHANT:
                fu_gain = 3
            score = fu_gain + fu_need + 1  # 福+慧+减劫难
            score += calamity_urgency * 0.5
        
        elif action == ActionType.PROTECT:
            if wealth < 2:
                return -5
            score = 2 + fu_need + 1 + calamity_urgency * 2  # 护法在劫难紧急时很有价值
        
        elif action == ActionType.SAVE:
            affordable = [b for b in self.state.sentient_area if wealth >= b.cost]
            if not affordable:
                return -5
            # 找最有价值的众生
            best = max(affordable, key=lambda b: (b.fu_reward + b.hui_reward) / b.cost)
            official_bonus = 2 if role == RoleType.OFFICIAL else 0
            fu_gain = best.fu_reward + save_bonus + official_bonus
            hui_gain = best.hui_reward
            score = fu_gain + fu_need * 0.5 + hui_gain + hui_need * 0.5
            score += save_urgency * 3  # 渡化紧急时价值更高
            # 检查是否有超时众生
            urgent = [b for b in affordable if b.turns_in_area >= 1]
            if urgent:
                score += 5  # 紧急众生优先
        
        elif action == ActionType.ALMS:
            if role != RoleType.MONK:
                return -10
            score = 2 * 0.3 + 1 + fu_need + 1 + hui_need  # 财富+福+慧
        
        elif action == ActionType.CEREMONY:
            if role != RoleType.MONK:
                return -10
            score = 4 * 0.3 - 2 - fu_need - 2 - hui_need  # 财富-福-慧（通常负分）
        
        elif action == ActionType.TEACH:
            if role != RoleType.MONK:
                return -10
            score = 1 + fu_need + 3  # 自己+1福，帮助他人价值
            # 如果自己福低，讲法收益更高
            if fu < hui:
                score += 2
        
        elif action == ActionType.SUPPORT_MONK:
            monk_idx = self._get_monk_idx()
            if monk_idx is None or monk_idx == player_idx:
                return -10
            if wealth < 2:
                return -5
            monk = self.state.players[monk_idx]
            score = 2 + fu_need  # 供养获得福
            if monk.wealth < 2:
                score += 2  # 僧侣需要钱时更有价值
        
        return score
    
    def _choose_action_smart(self, player: Player, player_idx: int) -> ActionType:
        """智能决策：评估所有可能行动，选择最高分的"""
        role = player.role
        
        if role == RoleType.MONK:
            actions = [ActionType.ALMS, ActionType.CEREMONY, ActionType.TEACH,
                      ActionType.SAVE, ActionType.PROTECT, ActionType.PRACTICE]
        else:
            actions = [ActionType.LABOR, ActionType.PRACTICE, ActionType.DONATE,
                      ActionType.SAVE, ActionType.PROTECT, ActionType.SUPPORT_MONK]
        
        # 评估每个行动
        scores = [(a, self._evaluate_action_score(player, a, player_idx)) for a in actions]
        
        # 加入少量随机性，避免完全确定性（模拟真实玩家）
        for i, (a, s) in enumerate(scores):
            scores[i] = (a, s + random.gauss(0, 1))
        
        # 选择最高分
        best_action = max(scores, key=lambda x: x[1])[0]
        return best_action
    
    def _choose_action(self, player: Player, strategy: Strategy, player_idx: int) -> ActionType:
        # v1.8: 所有策略都使用智能决策，只是权重不同
        if strategy == Strategy.SELFISH:
            # 自私：只修行（僧侣只做法事）
            if player.role == RoleType.MONK:
                return ActionType.CEREMONY
            return ActionType.PRACTICE
        
        elif strategy == Strategy.ALTRUISTIC:
            # 利他：优先帮助，但使用智能选择具体行动
            action = self._choose_action_smart(player, player_idx)
            # 强制偏向帮助行动
            if player.wealth >= 3 and random.random() > 0.3:
                if player.role == RoleType.MONK:
                    return ActionType.TEACH
                return ActionType.DONATE
            return action
        
        else:  # SMART 和 BALANCED 都使用智能决策
            return self._choose_action_smart(player, player_idx)
    
    def _execute_action(self, player: Player, action: ActionType, player_idx: int):
        role = player.role
        
        if action == ActionType.LABOR:
            player.labor_count += 1  # v1.7: 统计
            if role == RoleType.MONK:
                player.wealth += 1
                player.fu = max(0, player.fu - 1)
            else:
                player.wealth += 3
                # v1.7: 移除农夫劳作+慧
            
        elif action == ActionType.PRACTICE:
            base_hui = 2
            if role == RoleType.MONK:
                base_hui += 1
            player.hui += base_hui
            player.hui_from_practice += base_hui  # v1.7: 统计
            
        elif action == ActionType.DONATE:
            if player.wealth >= 3:
                player.wealth -= 3
                base_fu = 2
                # 商人布施+2福（善于结缘）
                if role == RoleType.MERCHANT:
                    base_fu += 2
                player.fu += base_fu
                player.fu_from_donate += base_fu
                player.hui += 1
                self.state.calamity = max(0, self.state.calamity - 1)
                player.helped_this_turn = True
            else:
                player.wealth += 3
                
        elif action == ActionType.PROTECT:
            if player.wealth >= 2:
                player.wealth -= 2
                player.fu += 2
                player.fu_from_protect += 2  # v1.7: 统计
                player.hui += 1
                self.state.calamity = max(0, self.state.calamity - 2)
                player.helped_this_turn = True
            else:
                player.wealth += 3
                
        elif action == ActionType.SAVE:
            # v1.7.1: 移除农夫渡化费用-1，改用其他机制
            affordable = [b for b in self.state.sentient_area if player.wealth >= b.cost]
            if affordable:
                urgent = [b for b in affordable if b.turns_in_area >= 1]
                if urgent:
                    being = max(urgent, key=lambda b: (b.fu_reward + b.hui_reward) / b.cost)
                else:
                    being = max(affordable, key=lambda b: (b.fu_reward + b.hui_reward) / b.cost)
                
                actual_cost = being.cost
                if self.state.event_modifiers.get("free_save"):
                    actual_cost = 0
                    self.state.event_modifiers["free_save"] = False
                
                player.wealth -= actual_cost
                
                # v1.7.3: 渡化递减奖励（更激进）
                # 第1次+3福，第2次+2福，第3次+1福，第4次以上+0福
                save_bonus = max(0, 3 - player.save_count)
                
                # 官员渡化+2福（号召力）
                official_bonus = 2 if role == RoleType.OFFICIAL else 0
                
                fu_gain = being.fu_reward + save_bonus + official_bonus
                player.fu += fu_gain
                player.fu_from_save += fu_gain
                player.hui += being.hui_reward
                player.hui_from_save += being.hui_reward
                player.save_count += 1
                
                if being.special == "calamity_minus1":
                    self.state.calamity = max(0, self.state.calamity - 1)
                elif being.special == "calamity_minus2":
                    self.state.calamity = max(0, self.state.calamity - 2)
                elif being.special == "wealth_all":
                    for p in self.state.players:
                        p.wealth += 1
                
                self.state.sentient_area.remove(being)
                self.state.saved_count += 1
                player.helped_this_turn = True
            else:
                player.wealth += 3
        
        # 僧侣专属（最终数值）
        elif action == ActionType.ALMS:
            # 托钵：+2财富+1福+1慧
            player.wealth += 2
            player.fu += 1
            player.fu_from_alms += 1  # v1.7: 统计
            player.hui += 1
            player.hui_from_alms += 1  # v1.7: 统计
            
        elif action == ActionType.CEREMONY:
            # 法事：+4财富-2福-2慧
            player.wealth += 4
            player.fu = max(0, player.fu - 2)
            player.hui = max(0, player.hui - 2)
            
        elif action == ActionType.TEACH:
            # v1.8.4: 讲法是法布施，不算物质帮助，不计入持续帮助轨道
            others = [(i, p) for i, p in enumerate(self.state.players) if i != player_idx]
            if others:
                target_idx, target = min(others, key=lambda x: x[1].fu)
                target.fu += 1
                target.hui += 1
                player.fu += 1
                player.fu_from_teach += 1
                # 注意：不设置 helped_this_turn = True，法布施不计入持续帮助
        
        elif action == ActionType.SUPPORT_MONK:
            monk_idx = self._get_monk_idx()
            if monk_idx is not None and player.wealth >= 2:
                monk = self.state.players[monk_idx]
                player.wealth -= 2
                monk.wealth += 2
                player.fu += 2
                player.fu_from_donate += 2  # v1.7: 统计供养算布施
                monk.fu += 1
                player.helped_this_turn = True
    
    def _update_help_streak(self):
        for player in self.state.players:
            if player.helped_this_turn:
                player.help_streak += 1
                player.max_streak = max(player.max_streak, player.help_streak)
                # v1.8.2: 持续帮助奖励递减（连续3轮+1，4轮+1，5轮+0...）
                if player.help_streak >= 3 and player.help_streak <= 4:
                    fu_bonus = 1
                    hui_bonus = 1
                    # 农夫特殊：持续帮助加成更高
                    if player.role == RoleType.FARMER:
                        fu_bonus = 2
                    # 僧侣讲法已经算帮助，连续帮助奖励减半
                    if player.role == RoleType.MONK:
                        fu_bonus = 0
                    player.fu += fu_bonus
                    player.hui += hui_bonus
                    player.fu_from_streak += fu_bonus
                    player.hui_from_streak += hui_bonus
            else:
                player.help_streak = 0
    
    def _apply_survival_cost(self):
        """v1.8.1: 每2回合扣除1财富维持生存（降低难度）"""
        if self.state.current_round % 2 == 0:  # 只在偶数回合扣除
            for player in self.state.players:
                player.wealth -= 1
                if player.wealth < 0:
                    player.wealth = 0
                    player.fu = max(0, player.fu - 1)
                    player.hui = max(0, player.hui - 1)
                    player.starve_count += 1
    
    def _evaluate_dao(self, player: Player) -> tuple:
        fu = player.fu
        hui = player.hui
        
        daos = []
        if fu >= 15 and hui >= 15:
            daos.append(("菩萨道", 18))
        if fu >= 18 and hui >= 8:
            daos.append(("布施道", 15))
        if hui >= 18 and fu >= 8:
            daos.append(("禅修道", 15))
        if fu >= 12 and hui >= 12 and abs(fu - hui) <= 5:
            daos.append(("居士道", 14))
        if fu >= 20 or hui >= 20:
            daos.append(("觉悟道", 16))
        
        if daos:
            return max(daos, key=lambda x: x[1])
        return ("世俗道", 8)
    
    def run_settlement_phase(self):
        self._update_help_streak()
        self._apply_survival_cost()  # v1.7: 生存消耗
        self.state.event_modifiers = {}

        if self.state.calamity >= self.state.calamity_limit:
            self.state.game_over = True
            self.state.team_win = False
            return

        if self.state.current_round >= self.state.max_rounds:
            self.state.game_over = True
            if (self.state.calamity <= self.state.calamity_win_max and
                self.state.saved_count >= self.state.save_required):
                self.state.team_win = True
            else:
                self.state.team_win = False
    
    def _calculate_final_score(self, player: Player) -> tuple:
        fu = player.fu
        hui = player.hui
        
        if fu <= 0 or hui <= 0:
            base_score = 0
        else:
            base_score = math.sqrt(fu * hui) * 3
        
        dao_name, dao_bonus = self._evaluate_dao(player)
        return base_score + dao_bonus, dao_name
    
    def run_game(self) -> Dict:
        self.initialize_game()

        while not self.state.game_over:
            self.state.current_round += 1
            self.run_event_phase()
            self.run_sentient_phase()
            self.run_action_phase()
            self.run_settlement_phase()

        scores = []
        for p in self.state.players:
            total, dao_name = self._calculate_final_score(p)
            # v1.7: 更详细的统计数据
            scores.append({
                "total": total, 
                "dao": dao_name, 
                "fu": p.fu, 
                "hui": p.hui,
                "wealth": p.wealth,
                "save_count": p.save_count,
                "max_streak": p.max_streak,
                "labor_count": p.labor_count,
                "starve_count": p.starve_count,
                # 福来源分析
                "fu_from_save": p.fu_from_save,
                "fu_from_donate": p.fu_from_donate,
                "fu_from_protect": p.fu_from_protect,
                "fu_from_streak": p.fu_from_streak,
                "fu_from_teach": p.fu_from_teach,
                "fu_from_alms": p.fu_from_alms,
                # 慧来源分析
                "hui_from_practice": p.hui_from_practice,
                "hui_from_streak": p.hui_from_streak,
                "hui_from_save": p.hui_from_save,
                "hui_from_alms": p.hui_from_alms,
            })

        result = {
            "team_win": self.state.team_win,
            "final_calamity": self.state.calamity,
            "saved_count": self.state.saved_count,
            "player_scores": scores,
            "player_roles": [p.role.value for p in self.state.players],
            "winner_idx": None,
        }

        if self.state.team_win:
            winner_idx = max(range(len(scores)), key=lambda i: scores[i]["total"])
            result["winner_idx"] = winner_idx

        return result


class MonteCarloTester:
    def __init__(self, num_simulations: int = 5000):
        self.num_simulations = num_simulations
    
    def run_full_test(self):
        print("=" * 80)
        print("《功德轮回》v1.8.4 讲法区分版")
        print(f"模拟次数: {self.num_simulations}局")
        print("=" * 80)
        
        print("\n【核心机制】")
        print("• 智能AI评估每个行动的预期收益")
        print("• 渡化递减：第1-3次分别+3/+2/+1福")
        print("• 持续帮助（物质）：布施/渡化/护法/供养，连续3-4轮+1福+1慧")
        print("• 讲法是法布施，不计入持续帮助轨道")
        print("• 每2回合-1财富维持生存")
        
        # 只测试全智能型以获取详细数据
        strategies = [Strategy.SMART] * 4
        results = []
        for _ in range(self.num_simulations):
            sim = GameSimulator(4, strategies)
            results.append(sim.run_game())
        
        team_wins = sum(1 for r in results if r["team_win"])
        
        # 收集详细数据
        role_stats = defaultdict(lambda: {
            "wins": 0, "fu": [], "hui": [], "scores": [], "wealth": [],
            "save_count": [], "max_streak": [], "labor_count": [], "starve_count": [],
            "fu_from_save": [], "fu_from_donate": [], "fu_from_protect": [],
            "fu_from_streak": [], "fu_from_teach": [], "fu_from_alms": [],
            "hui_from_practice": [], "hui_from_streak": [], "hui_from_save": [], "hui_from_alms": [],
        })
        
        for r in results:
            for i, role in enumerate(r["player_roles"]):
                p = r["player_scores"][i]
                role_stats[role]["fu"].append(p["fu"])
                role_stats[role]["hui"].append(p["hui"])
                role_stats[role]["scores"].append(p["total"])
                role_stats[role]["wealth"].append(p["wealth"])
                role_stats[role]["save_count"].append(p["save_count"])
                role_stats[role]["max_streak"].append(p["max_streak"])
                role_stats[role]["labor_count"].append(p["labor_count"])
                role_stats[role]["starve_count"].append(p["starve_count"])
                role_stats[role]["fu_from_save"].append(p["fu_from_save"])
                role_stats[role]["fu_from_donate"].append(p["fu_from_donate"])
                role_stats[role]["fu_from_protect"].append(p["fu_from_protect"])
                role_stats[role]["fu_from_streak"].append(p["fu_from_streak"])
                role_stats[role]["fu_from_teach"].append(p["fu_from_teach"])
                role_stats[role]["fu_from_alms"].append(p["fu_from_alms"])
                role_stats[role]["hui_from_practice"].append(p["hui_from_practice"])
                role_stats[role]["hui_from_streak"].append(p["hui_from_streak"])
                role_stats[role]["hui_from_save"].append(p["hui_from_save"])
                role_stats[role]["hui_from_alms"].append(p["hui_from_alms"])
                if r["team_win"] and r["winner_idx"] == i:
                    role_stats[role]["wins"] += 1
        
        print(f"\n【全智能型】团队胜率: {team_wins/len(results)*100:.1f}%")
        
        win_rates = []
        for role in ["农夫", "商人", "官员", "僧侣"]:
            data = role_stats[role]
            win_rate = data["wins"] / team_wins * 100 if team_wins > 0 else 0
            win_rates.append(win_rate)
            print(f"\n  {role}: 胜率={win_rate:.1f}%")
            print(f"    福={statistics.mean(data['fu']):.1f}, 慧={statistics.mean(data['hui']):.1f}, 分={statistics.mean(data['scores']):.1f}")
            print(f"    财富={statistics.mean(data['wealth']):.1f}, 劳作={statistics.mean(data['labor_count']):.1f}, 饥饿={statistics.mean(data['starve_count']):.1f}")
            print(f"    渡化={statistics.mean(data['save_count']):.1f}, 连续帮助={statistics.mean(data['max_streak']):.1f}")
        
        # 福来源分析
        print("\n" + "=" * 80)
        print("福来源分析（平均值）")
        print("=" * 80)
        print(f"{'角色':6} {'渡化':>6} {'布施':>6} {'护法':>6} {'连续':>6} {'讲法':>6} {'托钵':>6}")
        for role in ["农夫", "商人", "官员", "僧侣"]:
            data = role_stats[role]
            print(f"{role:6} {statistics.mean(data['fu_from_save']):>6.1f} {statistics.mean(data['fu_from_donate']):>6.1f} "
                  f"{statistics.mean(data['fu_from_protect']):>6.1f} {statistics.mean(data['fu_from_streak']):>6.1f} "
                  f"{statistics.mean(data['fu_from_teach']):>6.1f} {statistics.mean(data['fu_from_alms']):>6.1f}")
        
        # 慧来源分析
        print("\n" + "=" * 80)
        print("慧来源分析（平均值）")
        print("=" * 80)
        print(f"{'角色':6} {'修行':>6} {'渡化':>6} {'连续':>6} {'托钵':>6}")
        for role in ["农夫", "商人", "官员", "僧侣"]:
            data = role_stats[role]
            print(f"{role:6} {statistics.mean(data['hui_from_practice']):>6.1f} {statistics.mean(data['hui_from_save']):>6.1f} "
                  f"{statistics.mean(data['hui_from_streak']):>6.1f} {statistics.mean(data['hui_from_alms']):>6.1f}")
        
        # 平衡性评价
        if win_rates and team_wins > 0:
            gap = max(win_rates) - min(win_rates)
            print("\n" + "=" * 80)
            print(f"胜率差距: {gap:.1f}%")
            if gap < 20:
                print("评价: ★★★★★ 非常平衡")
            elif gap < 30:
                print("评价: ★★★★☆ 比较平衡")
            elif gap < 40:
                print("评价: ★★★☆☆ 一般")
            else:
                print("评价: ★★☆☆☆ 需调整")
            
            # 识别主要问题
            print("\n【问题识别】")
            max_role = ["农夫", "商人", "官员", "僧侣"][win_rates.index(max(win_rates))]
            min_role = ["农夫", "商人", "官员", "僧侣"][win_rates.index(min(win_rates))]
            print(f"  最强角色: {max_role} ({max(win_rates):.1f}%)")
            print(f"  最弱角色: {min_role} ({min(win_rates):.1f}%)")
            
            # 分析最强角色的优势来源
            max_data = role_stats[max_role]
            print(f"\n  {max_role}优势来源:")
            sources = [
                ("渡化福", statistics.mean(max_data['fu_from_save'])),
                ("布施福", statistics.mean(max_data['fu_from_donate'])),
                ("护法福", statistics.mean(max_data['fu_from_protect'])),
                ("连续福", statistics.mean(max_data['fu_from_streak'])),
            ]
            sources.sort(key=lambda x: -x[1])
            for name, val in sources[:3]:
                print(f"    {name}: {val:.1f}")


if __name__ == "__main__":
    tester = MonteCarloTester(num_simulations=1000)  # 增加到1000次以获得更稳定结果
    tester.run_full_test()
