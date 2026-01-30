"""
《功德轮回：众生百态》v1.4 僧侣托钵机制

核心设计：
1. 僧侣不能劳作（符合佛教现实）
2. 僧侣被他人"请"时有两种选择：
   - 清修：少量财富(+1)，但福慧都增加(+1福+2慧)
   - 应酬：较多财富(+3)，但福慧减少(-1福-1慧)
3. 其他玩家可以"供养"僧侣（给钱给僧侣，双方都获得福）
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
    # 僧侣专属
    ALMS = "托钵"           # 清修托钵：+1财富+1福+2慧
    CEREMONY = "法事"       # 应酬法事：+3财富-1福-1慧
    TEACH = "讲法"          # 讲法：给他人+2福+1慧，自己+1福
    # 供养僧侣（其他角色对僧侣使用）
    SUPPORT_MONK = "供养"   # 给僧侣+2财富，双方各+1福

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
    supported_this_turn: bool = False  # 是否被供养

# 角色初始值
ROLE_INIT = {
    RoleType.FARMER: {"wealth": 5, "fu": 1, "hui": 1},
    RoleType.MERCHANT: {"wealth": 6, "fu": 1, "hui": 1},
    RoleType.OFFICIAL: {"wealth": 5, "fu": 1, "hui": 1},
    RoleType.MONK: {"wealth": 2, "fu": 2, "hui": 3},  # 僧侣初始财富低
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
            p.supported_this_turn = False
        
        for i, player in enumerate(self.state.players):
            strategy = self.strategies[i]
            for _ in range(player.actions_per_turn):
                action = self._choose_action(player, strategy, i)
                self._execute_action(player, action, i)
    
    def _choose_action(self, player: Player, strategy: Strategy, player_idx: int) -> ActionType:
        calamity_urgent = self.state.calamity >= 14
        calamity_danger = self.state.calamity >= 8
        remaining_rounds = self.state.max_rounds - self.state.current_round
        saves_needed = self.state.save_required - self.state.saved_count
        urgent_beings = [b for b in self.state.sentient_area if b.turns_in_area >= 1]
        affordable_beings = [b for b in self.state.sentient_area if player.wealth >= b.cost]
        
        is_monk = player.role == RoleType.MONK
        monk_idx = self._get_monk_idx()
        has_monk = monk_idx is not None and monk_idx != player_idx
        
        # ═══════════════════════════════════════════════════════════════════════
        # 僧侣专属决策
        # ═══════════════════════════════════════════════════════════════════════
        if is_monk:
            if strategy == Strategy.SELFISH:
                # 自私僧侣：贪财做法事
                return ActionType.CEREMONY
            
            elif strategy == Strategy.ALTRUISTIC:
                # 利他僧侣：优先讲法
                if calamity_urgent and player.wealth >= 2:
                    return ActionType.PROTECT
                if player.wealth < 2:
                    return ActionType.ALMS  # 清修托钵
                return ActionType.TEACH
            
            elif strategy == Strategy.SMART:
                # 智能僧侣：根据情况选择
                if calamity_urgent and player.wealth >= 2:
                    return ActionType.PROTECT
                if player.wealth < 3:
                    # 需要钱时，根据福慧决定
                    if player.fu > player.hui:
                        return ActionType.ALMS  # 福够了，清修
                    else:
                        return ActionType.CEREMONY  # 福不够，做法事赚钱
                if urgent_beings and affordable_beings:
                    return ActionType.SAVE
                if player.fu < player.hui:
                    return ActionType.TEACH  # 讲法增福
                return ActionType.PRACTICE  # 修行增慧
            
            else:  # BALANCED
                if calamity_danger and player.wealth >= 2:
                    if random.random() > 0.5:
                        return ActionType.PROTECT
                if player.wealth < 3:
                    if random.random() > 0.3:
                        return ActionType.ALMS
                    else:
                        return ActionType.CEREMONY
                if urgent_beings and affordable_beings:
                    return ActionType.SAVE
                if random.random() > 0.5:
                    return ActionType.TEACH
                return ActionType.PRACTICE
        
        # ═══════════════════════════════════════════════════════════════════════
        # 非僧侣角色决策
        # ═══════════════════════════════════════════════════════════════════════
        
        if strategy == Strategy.SELFISH:
            return ActionType.PRACTICE
        
        elif strategy == Strategy.ALTRUISTIC:
            if calamity_urgent and player.wealth >= 2:
                return ActionType.PROTECT
            # 供养僧侣（如果有僧侣且自己财富够）
            if has_monk and player.wealth >= 5 and random.random() > 0.5:
                return ActionType.SUPPORT_MONK
            if urgent_beings and affordable_beings:
                return ActionType.SAVE
            if player.wealth >= 3:
                return ActionType.DONATE
            return ActionType.LABOR
        
        elif strategy == Strategy.SMART:
            if calamity_urgent and player.wealth >= 2:
                return ActionType.PROTECT
            if urgent_beings:
                affordable_urgent = [b for b in urgent_beings if player.wealth >= b.cost]
                if affordable_urgent:
                    return ActionType.SAVE
            if player.wealth < 4:
                return ActionType.LABOR
            # 考虑供养僧侣
            if has_monk and player.wealth >= 6:
                monk = self.state.players[monk_idx]
                if monk.wealth < 3 and random.random() > 0.6:
                    return ActionType.SUPPORT_MONK
            if saves_needed > 0 and affordable_beings:
                if saves_needed >= remaining_rounds or random.random() > 0.4:
                    return ActionType.SAVE
            if player.fu < player.hui - 2 and player.wealth >= 3:
                return ActionType.DONATE
            if player.hui < player.fu - 2:
                return ActionType.PRACTICE
            if player.wealth >= 3 and random.random() > 0.5:
                return ActionType.DONATE
            return ActionType.PRACTICE
        
        else:  # BALANCED
            if calamity_danger and player.wealth >= 2 and random.random() > 0.6:
                return ActionType.PROTECT
            if urgent_beings:
                affordable_urgent = [b for b in urgent_beings if player.wealth >= b.cost]
                if affordable_urgent:
                    return ActionType.SAVE
            # 供养僧侣
            if has_monk and player.wealth >= 5 and random.random() > 0.7:
                return ActionType.SUPPORT_MONK
            if saves_needed > remaining_rounds and affordable_beings:
                return ActionType.SAVE
            if player.wealth < 4:
                return ActionType.LABOR
            if affordable_beings and random.random() > 0.5:
                return ActionType.SAVE
            if player.fu < player.hui - 2 and player.wealth >= 3:
                return ActionType.DONATE
            if player.hui < player.fu - 2:
                return ActionType.PRACTICE
            if random.random() > 0.5:
                return ActionType.PRACTICE
            return ActionType.LABOR
    
    def _execute_action(self, player: Player, action: ActionType, player_idx: int):
        role = player.role
        
        if action == ActionType.LABOR:
            if role == RoleType.MONK:
                # 僧侣不能劳作！
                player.wealth += 1  # 只能获得很少
                player.fu -= 1      # 且损失福（不务正业）
            else:
                player.wealth += 3
            
        elif action == ActionType.PRACTICE:
            base_hui = 2
            if role == RoleType.MONK:
                base_hui += 1
            player.hui += base_hui
            
        elif action == ActionType.DONATE:
            if player.wealth >= 3:
                player.wealth -= 3
                player.fu += 2
                player.hui += 1
                self.state.calamity = max(0, self.state.calamity - 1)
                player.helped_this_turn = True
            else:
                player.wealth += 3
                
        elif action == ActionType.PROTECT:
            if player.wealth >= 2:
                player.wealth -= 2
                player.fu += 2
                player.hui += 1
                self.state.calamity = max(0, self.state.calamity - 2)
                player.helped_this_turn = True
            else:
                player.wealth += 3
                
        elif action == ActionType.SAVE:
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
                player.fu += being.fu_reward + 2
                player.hui += being.hui_reward
                
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # 僧侣专属行动
        # ═══════════════════════════════════════════════════════════════════════
        
        elif action == ActionType.ALMS:
            # 清修托钵：少量财富，福慧增加
            player.wealth += 1
            player.fu += 1
            player.hui += 2
            
        elif action == ActionType.CEREMONY:
            # 应酬法事：较多财富，福慧减少
            player.wealth += 3
            player.fu = max(0, player.fu - 1)
            player.hui = max(0, player.hui - 1)
            
        elif action == ActionType.TEACH:
            # 讲法：给福最低的其他玩家
            others = [(i, p) for i, p in enumerate(self.state.players) if i != player_idx]
            if others:
                target_idx, target = min(others, key=lambda x: x[1].fu)
                target.fu += 2
                target.hui += 1
                player.fu += 1
                player.helped_this_turn = True
        
        # ═══════════════════════════════════════════════════════════════════════
        # 供养僧侣
        # ═══════════════════════════════════════════════════════════════════════
        
        elif action == ActionType.SUPPORT_MONK:
            monk_idx = self._get_monk_idx()
            if monk_idx is not None and player.wealth >= 2:
                monk = self.state.players[monk_idx]
                player.wealth -= 2
                monk.wealth += 2
                player.fu += 1
                monk.fu += 1
                player.helped_this_turn = True
    
    def _update_help_streak(self):
        for player in self.state.players:
            if player.helped_this_turn:
                player.help_streak += 1
                if player.help_streak >= 3:
                    player.fu += 1
                    player.hui += 1
            else:
                player.help_streak = 0
    
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
        total = base_score + dao_bonus
        
        return total, dao_name
    
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
            scores.append({
                "total": total,
                "dao": dao_name,
                "fu": p.fu,
                "hui": p.hui,
                "wealth": p.wealth,
            })
        
        result = {
            "team_win": self.state.team_win,
            "final_calamity": self.state.calamity,
            "saved_count": self.state.saved_count,
            "player_scores": scores,
            "player_roles": [p.role.value for p in self.state.players],
            "winner_idx": None,
            "winner_role": None,
        }
        
        if self.state.team_win:
            winner_idx = max(range(len(scores)), key=lambda i: scores[i]["total"])
            result["winner_idx"] = winner_idx
            result["winner_role"] = self.state.players[winner_idx].role.value
        
        return result


class MonteCarloTester:
    def __init__(self, num_simulations: int = 5000):
        self.num_simulations = num_simulations
    
    def run_full_test(self):
        print("=" * 80)
        print("《功德轮回》v1.4 僧侣托钵机制测试")
        print(f"模拟次数: {self.num_simulations}局/配置")
        print("=" * 80)
        
        print("\n【僧侣机制设计】")
        print("• 僧侣不能劳作（劳作只+1财富且-1福）")
        print("• 托钵（清修）：+1财富+1福+2慧")
        print("• 法事（应酬）：+3财富-1福-1慧")
        print("• 讲法：给他人+2福+1慧，自己+1福")
        print("• 可被供养：他人-2财富，双方各+1福")
        
        configs = [
            ("全智能型", [Strategy.SMART] * 4),
            ("全平衡型", [Strategy.BALANCED] * 4),
            ("全利他型", [Strategy.ALTRUISTIC] * 4),
            ("全自私型", [Strategy.SELFISH] * 4),
            ("混合型", [Strategy.SMART, Strategy.BALANCED, Strategy.ALTRUISTIC, Strategy.SELFISH]),
        ]
        
        all_results = {}
        
        for name, strategies in configs:
            results = []
            for _ in range(self.num_simulations):
                sim = GameSimulator(4, strategies)
                results.append(sim.run_game())
            
            team_wins = sum(1 for r in results if r["team_win"])
            
            role_data = defaultdict(lambda: {"wins": 0, "fu": [], "hui": [], "wealth": [], "scores": [], "games": 0})
            
            for r in results:
                for i, role in enumerate(r["player_roles"]):
                    role_data[role]["games"] += 1
                    role_data[role]["fu"].append(r["player_scores"][i]["fu"])
                    role_data[role]["hui"].append(r["player_scores"][i]["hui"])
                    role_data[role]["wealth"].append(r["player_scores"][i]["wealth"])
                    role_data[role]["scores"].append(r["player_scores"][i]["total"])
                    if r["team_win"] and r["winner_idx"] == i:
                        role_data[role]["wins"] += 1
            
            all_results[name] = {
                "team_win_rate": team_wins / len(results),
                "avg_calamity": statistics.mean(r["final_calamity"] for r in results),
                "avg_saved": statistics.mean(r["saved_count"] for r in results),
                "role_data": role_data,
                "team_wins": team_wins,
            }
            
            print(f"\n【{name}】")
            print(f"  团队胜率: {team_wins/len(results)*100:.1f}%")
            print(f"  平均劫难: {all_results[name]['avg_calamity']:.1f}")
            print(f"  平均渡化: {all_results[name]['avg_saved']:.1f}")
            
            if team_wins > 0:
                print("  角色表现:")
                for role in ["农夫", "商人", "官员", "僧侣"]:
                    data = role_data[role]
                    win_rate = data["wins"] / team_wins * 100 if team_wins > 0 else 0
                    avg_fu = statistics.mean(data["fu"]) if data["fu"] else 0
                    avg_hui = statistics.mean(data["hui"]) if data["hui"] else 0
                    avg_wealth = statistics.mean(data["wealth"]) if data["wealth"] else 0
                    avg_score = statistics.mean(data["scores"]) if data["scores"] else 0
                    print(f"    {role}: 胜率={win_rate:.1f}%, 福={avg_fu:.1f}, 慧={avg_hui:.1f}, 财={avg_wealth:.1f}, 分={avg_score:.1f}")
        
        # 详细分析
        print("\n" + "=" * 80)
        print("角色平衡性分析（智能策略）")
        print("=" * 80)
        
        smart_data = all_results["全智能型"]["role_data"]
        team_wins = all_results["全智能型"]["team_wins"]
        
        win_rates = []
        
        for role in ["农夫", "商人", "官员", "僧侣"]:
            data = smart_data[role]
            if team_wins > 0:
                win_rate = data["wins"] / team_wins * 100
                win_rates.append(win_rate)
                avg_score = statistics.mean(data["scores"])
                print(f"\n{role}: 胜率={win_rate:.1f}%, 平均分={avg_score:.1f}")
        
        if win_rates:
            max_rate = max(win_rates)
            min_rate = min(win_rates)
            gap = max_rate - min_rate
            balance = 100 - statistics.stdev(win_rates)
            
            print(f"\n胜率差距: {gap:.1f}%")
            print(f"平衡分: {balance:.1f}/100")
            
            if gap < 20:
                print("评价: ★★★★★ 非常平衡")
            elif gap < 30:
                print("评价: ★★★★☆ 比较平衡")
            elif gap < 40:
                print("评价: ★★★☆☆ 一般")
            else:
                print("评价: ★★☆☆☆ 需要调整")
        
        # 僧侣选择分析
        print("\n" + "=" * 80)
        print("僧侣策略抉择验证")
        print("=" * 80)
        
        selfish_monk = all_results["全自私型"]["role_data"]["僧侣"]
        smart_monk = all_results["全智能型"]["role_data"]["僧侣"]
        
        if selfish_monk["fu"] and smart_monk["fu"]:
            print(f"\n自私僧侣（做法事赚钱）:")
            print(f"  平均福: {statistics.mean(selfish_monk['fu']):.1f}")
            print(f"  平均慧: {statistics.mean(selfish_monk['hui']):.1f}")
            print(f"  平均财: {statistics.mean(selfish_monk['wealth']):.1f}")
            
            print(f"\n智能僧侣（平衡托钵/讲法）:")
            print(f"  平均福: {statistics.mean(smart_monk['fu']):.1f}")
            print(f"  平均慧: {statistics.mean(smart_monk['hui']):.1f}")
            print(f"  平均财: {statistics.mean(smart_monk['wealth']):.1f}")
        
        return all_results


if __name__ == "__main__":
    tester = MonteCarloTester(num_simulations=5000)
    tester.run_full_test()
