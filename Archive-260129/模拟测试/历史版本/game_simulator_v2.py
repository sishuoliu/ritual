"""
《功德轮回：众生百态》v1.0 游戏模拟器 v2
基于第一轮测试结果修复和优化

问题诊断：
1. 团队胜率过低（15%）- 游戏太难
2. 全贪财型100%胜率 - AI逻辑bug
3. 渡化数量不足 - 需要调整资源平衡
4. 僧侣弱势 - 讲法机制需要加强
"""

import random
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════════════════
#                   游戏常量定义
# ═══════════════════════════════════════════════════════════════════════════════

class ActionType(Enum):
    LABOR = "劳作"
    PRACTICE = "修行"
    DONATE = "布施"
    SAVE = "渡化"
    PROTECT = "护法"
    PREACH = "讲法"  # 僧侣专属

class RoleType(Enum):
    FARMER = "农夫"
    MERCHANT = "商人"
    OFFICIAL = "官员"
    MONK = "僧侣"

@dataclass
class SentientBeing:
    name: str
    cost: int
    merit: int
    turns_in_area: int = 0
    special: str = ""

@dataclass
class Event:
    name: str
    event_type: str
    effect: Dict

@dataclass
class Player:
    role: RoleType
    wealth: int
    merit: int
    actions_per_turn: int = 2
    
    def can_afford(self, cost: int) -> bool:
        return self.wealth >= cost

# ═══════════════════════════════════════════════════════════════════════════════
#                   游戏数据 v2（平衡性调整）
# ═══════════════════════════════════════════════════════════════════════════════

ROLE_INIT = {
    RoleType.FARMER: {"wealth": 4, "merit": 2},
    RoleType.MERCHANT: {"wealth": 6, "merit": 1},
    RoleType.OFFICIAL: {"wealth": 5, "merit": 1},
    RoleType.MONK: {"wealth": 2, "merit": 4},
}

# 调整众生卡：降低费用，增加功德奖励
SENTIENT_BEINGS = [
    SentientBeing("饥民", 2, 2),      # 降低费用 3→2
    SentientBeing("病人", 3, 3),      # 降低费用 4→3
    SentientBeing("孤儿", 2, 2, special="wealth_next"),
    SentientBeing("老者", 2, 2),
    SentientBeing("流浪者", 4, 4),    # 降低费用 5→4
    SentientBeing("冤魂", 5, 5, special="calamity_minus1"),
    SentientBeing("恶人", 6, 6, special="calamity_plus1_per_turn"),
    SentientBeing("富商", 3, 3, special="wealth_all"),  # 降低费用，增加功德
    SentientBeing("官吏", 4, 4, special="action_plus1"),
    SentientBeing("将军", 5, 5, special="calamity_minus2"),
    SentientBeing("皇族", 8, 8, special="need_coop"),   # 降低费用
    SentientBeing("高僧", 5, 6),
]

EVENTS = [
    # 劫难事件（减少频率和强度）
    Event("旱灾", "disaster", {"calamity": 2}),
    Event("洪水", "disaster", {"calamity": 2}),
    Event("瘟疫", "disaster", {"calamity": 2, "wealth_all": -1}),
    Event("战乱", "disaster", {"calamity": 3}),
    Event("饥荒", "disaster", {"calamity": 2}),
    Event("妖邪", "disaster", {"calamity": 2}),
    # 机遇事件（增加正面效果）
    Event("丰收", "opportunity", {"wealth_all": 3}),
    Event("法会", "opportunity", {"merit_all": 2}),
    Event("施主到来", "opportunity", {"wealth_all": 2}),
    Event("高僧开示", "opportunity", {"merit_all": 1}),
    Event("国泰民安", "opportunity", {"calamity": -2}),
    Event("佛诞节", "opportunity", {"free_save": True, "merit_all": 1}),
    # 选择事件
    Event("乞丐求施", "choice", {"cost": 1, "merit": 1}),
    Event("迷途者", "choice", {"cost": 2, "merit": 2}),
    Event("富商供养", "choice", {"wealth": 3, "merit": -1}),
    Event("恶人忏悔", "choice", {"merit_cost": 2, "calamity": -2}),
    Event("寺院修缮", "choice", {"cost_all": 1, "calamity_per": -1}),
    Event("渡河", "choice", {"cost": 1, "merit_both": 1}),
]

# ═══════════════════════════════════════════════════════════════════════════════
#                   AI策略定义 v2（更智能）
# ═══════════════════════════════════════════════════════════════════════════════

class Strategy(Enum):
    BALANCED = "平衡型"
    SELFISH = "自私型"
    ALTRUISTIC = "利他型"
    GREEDY = "贪财型"
    RANDOM = "随机型"
    SMART = "智能型"  # 新增：根据局势动态调整

@dataclass
class GameState:
    players: List[Player]
    calamity: int = 0
    sentient_area: List[SentientBeing] = field(default_factory=list)
    saved_count: int = 0
    current_round: int = 0
    max_rounds: int = 6
    event_deck: List[Event] = field(default_factory=list)
    being_deck: List[SentientBeing] = field(default_factory=list)
    game_over: bool = False
    team_win: bool = False
    event_modifiers: Dict = field(default_factory=dict)
    
    # 胜利条件（可调整）
    calamity_limit: int = 20      # 劫难上限
    calamity_win_max: int = 12    # 胜利时劫难需≤此值
    save_required: int = 6        # 需要渡化的众生数量
    
    def __post_init__(self):
        if not self.event_deck:
            self.event_deck = [Event(e.name, e.event_type, e.effect.copy()) for e in EVENTS]
            random.shuffle(self.event_deck)
        if not self.being_deck:
            self.being_deck = [SentientBeing(b.name, b.cost, b.merit, 0, b.special) 
                              for b in SENTIENT_BEINGS]
            random.shuffle(self.being_deck)


class GameSimulator:
    def __init__(self, num_players: int = 4, strategies: List[Strategy] = None):
        self.num_players = num_players
        self.strategies = strategies or [Strategy.BALANCED] * num_players
        self.state = None
        self.log = []
        
    def initialize_game(self):
        roles = list(RoleType)[:self.num_players]
        players = []
        for role in roles:
            init = ROLE_INIT[role]
            players.append(Player(role, init["wealth"], init["merit"]))
        self.state = GameState(players=players)
        self.log = []
        
    def run_event_phase(self):
        if not self.state.event_deck:
            return
            
        event = self.state.event_deck.pop(0)
        effect = event.effect
        
        if "calamity" in effect:
            self.state.calamity = max(0, self.state.calamity + effect["calamity"])
            
        if "wealth_all" in effect:
            for p in self.state.players:
                p.wealth = max(0, p.wealth + effect["wealth_all"])
                
        if "merit_all" in effect:
            for p in self.state.players:
                p.merit += effect["merit_all"]
                
        if "wealth_min" in effect:
            min_wealth_player = min(self.state.players, key=lambda p: p.wealth)
            min_wealth_player.wealth += effect["wealth_min"]
            
        if "merit_min" in effect:
            min_merit_player = min(self.state.players, key=lambda p: p.merit)
            min_merit_player.merit += effect["merit_min"]
            
        if "free_save" in effect:
            self.state.event_modifiers["free_save"] = True
            
        if event.event_type == "choice":
            self._handle_choice_event(event)
    
    def _handle_choice_event(self, event: Event):
        effect = event.effect
        for i, player in enumerate(self.state.players):
            strategy = self.strategies[i]
            if "cost" in effect and "merit" in effect:
                if player.wealth >= effect["cost"]:
                    if strategy in [Strategy.ALTRUISTIC, Strategy.BALANCED, Strategy.SMART]:
                        player.wealth -= effect["cost"]
                        player.merit += effect["merit"]
                    elif strategy == Strategy.RANDOM and random.random() > 0.5:
                        player.wealth -= effect["cost"]
                        player.merit += effect["merit"]
    
    def run_sentient_phase(self):
        # 增加等待时间
        for being in self.state.sentient_area:
            being.turns_in_area += 1
            if being.special == "calamity_plus1_per_turn":
                self.state.calamity += 1
        
        # 超时检查
        timeout_beings = [b for b in self.state.sentient_area if b.turns_in_area >= 2]
        for being in timeout_beings:
            self.state.calamity += 3
            self.state.sentient_area.remove(being)
        
        # 新众生
        if self.state.being_deck:
            new_being = self.state.being_deck.pop(0)
            self.state.sentient_area.append(new_being)
    
    def run_action_phase(self):
        for i, player in enumerate(self.state.players):
            strategy = self.strategies[i]
            
            for action_num in range(player.actions_per_turn):
                action = self._choose_action(player, strategy, i, action_num)
                self._execute_action(player, action, i)
    
    def _choose_action(self, player: Player, strategy: Strategy, 
                       player_idx: int, action_num: int) -> ActionType:
        
        # 计算紧急程度
        calamity_urgent = self.state.calamity >= 15
        calamity_danger = self.state.calamity >= 10
        
        # 计算剩余需要渡化的众生数
        remaining_rounds = self.state.max_rounds - self.state.current_round
        saves_needed = self.state.save_required - self.state.saved_count
        
        # 有即将超时的众生？
        urgent_beings = [b for b in self.state.sentient_area if b.turns_in_area >= 1]
        
        # 可渡化的众生
        affordable_beings = [
            b for b in self.state.sentient_area 
            if player.wealth >= b.cost
        ]
        
        if strategy == Strategy.RANDOM:
            return random.choice(list(ActionType)[:5])  # 排除讲法
        
        elif strategy == Strategy.SELFISH:
            # 纯粹追求个人功德
            if self.state.event_modifiers.get("no_practice"):
                return ActionType.LABOR
            return ActionType.PRACTICE
        
        elif strategy == Strategy.GREEDY:
            # 只劳作，偶尔渡化
            if player.wealth >= 10 and affordable_beings:
                return ActionType.SAVE
            return ActionType.LABOR
        
        elif strategy == Strategy.ALTRUISTIC:
            # 优先团队
            if calamity_urgent and player.wealth >= 2:
                return ActionType.PROTECT
            
            if urgent_beings and affordable_beings:
                return ActionType.SAVE
            
            if affordable_beings and saves_needed > remaining_rounds:
                return ActionType.SAVE
            
            if player.wealth >= 3:
                return ActionType.DONATE
            
            return ActionType.LABOR
        
        elif strategy == Strategy.SMART:
            # 智能策略：根据局势动态决策
            
            # 紧急：劫难高
            if calamity_urgent and player.wealth >= 2:
                return ActionType.PROTECT
            
            # 紧急：需要渡化
            if saves_needed > 0 and urgent_beings:
                if affordable_beings:
                    return ActionType.SAVE
            
            # 资源不足
            if player.wealth < 3:
                return ActionType.LABOR
            
            # 中期策略
            if self.state.current_round <= 3:
                # 前半局积累
                if player.wealth < 6:
                    return ActionType.LABOR
                if affordable_beings:
                    return ActionType.SAVE
                return ActionType.PRACTICE
            else:
                # 后半局执行
                if affordable_beings:
                    return ActionType.SAVE
                if player.wealth >= 3 and self.state.calamity > 5:
                    return ActionType.DONATE
                return ActionType.PRACTICE
        
        else:  # BALANCED
            # 平衡策略（改进版）
            
            if calamity_danger and player.wealth >= 2:
                if random.random() > 0.5:
                    return ActionType.PROTECT
            
            # 优先渡化即将超时的众生
            if urgent_beings:
                affordable_urgent = [b for b in urgent_beings if player.wealth >= b.cost]
                if affordable_urgent:
                    return ActionType.SAVE
            
            # 需要渡化更多
            if saves_needed > remaining_rounds and affordable_beings:
                return ActionType.SAVE
            
            # 资源不足
            if player.wealth < 4:
                return ActionType.LABOR
            
            # 有众生就渡化
            if affordable_beings:
                if random.random() > 0.3:
                    return ActionType.SAVE
            
            # 功德或财富
            if player.wealth >= 5:
                if random.random() > 0.4:
                    return ActionType.PRACTICE
                return ActionType.DONATE
            
            return ActionType.LABOR
    
    def _execute_action(self, player: Player, action: ActionType, player_idx: int):
        
        if action == ActionType.LABOR:
            bonus = 1 if player.role == RoleType.FARMER else 0
            player.wealth += 3 + bonus
            
        elif action == ActionType.PRACTICE:
            player.merit += 2
            
        elif action == ActionType.DONATE:
            if player.wealth >= 3:
                player.wealth -= 3
                player.merit += 2
                self.state.calamity = max(0, self.state.calamity - 1)
            else:
                player.wealth += 3
                
        elif action == ActionType.PROTECT:
            if player.wealth >= 2:
                player.wealth -= 2
                self.state.calamity = max(0, self.state.calamity - 2)
            else:
                player.wealth += 3
                
        elif action == ActionType.SAVE:
            affordable = [b for b in self.state.sentient_area if player.wealth >= b.cost]
            
            if affordable:
                # 优先渡化即将超时的
                urgent = [b for b in affordable if b.turns_in_area >= 1]
                if urgent:
                    being = max(urgent, key=lambda b: b.merit / b.cost)
                else:
                    being = max(affordable, key=lambda b: b.merit / b.cost)
                
                actual_cost = being.cost
                if self.state.event_modifiers.get("free_save"):
                    actual_cost = 0
                    self.state.event_modifiers["free_save"] = False
                
                player.wealth -= actual_cost
                player.merit += being.merit
                
                # 特殊效果
                if being.special == "calamity_minus1":
                    self.state.calamity = max(0, self.state.calamity - 1)
                elif being.special == "calamity_minus2":
                    self.state.calamity = max(0, self.state.calamity - 2)
                elif being.special == "wealth_all":
                    for p in self.state.players:
                        p.wealth += 1
                
                self.state.sentient_area.remove(being)
                self.state.saved_count += 1
            else:
                player.wealth += 3
    
    def _monk_special_action(self, monk_idx: int):
        """僧侣特殊行动：改进版讲法"""
        monk = self.state.players[monk_idx]
        strategy = self.strategies[monk_idx]
        
        # 僧侣讲法：消耗1功德，他人+2功德，自己也+1功德（修正）
        if strategy in [Strategy.ALTRUISTIC, Strategy.BALANCED, Strategy.SMART]:
            if monk.merit >= 3:  # 有足够功德才讲法
                others = [(i, p) for i, p in enumerate(self.state.players) if i != monk_idx]
                if others:
                    target_idx, target = min(others, key=lambda x: x[1].merit)
                    monk.merit -= 1
                    target.merit += 2
                    monk.merit += 1  # 讲法也是修行，自己+1
    
    def run_settlement_phase(self):
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
    
    def run_game(self) -> Dict:
        self.initialize_game()
        
        while not self.state.game_over:
            self.state.current_round += 1
            self.run_event_phase()
            self.run_sentient_phase()
            self.run_action_phase()
            
            for i, p in enumerate(self.state.players):
                if p.role == RoleType.MONK:
                    self._monk_special_action(i)
            
            self.run_settlement_phase()
        
        result = {
            "team_win": self.state.team_win,
            "final_calamity": self.state.calamity,
            "saved_count": self.state.saved_count,
            "player_merits": [p.merit for p in self.state.players],
            "player_wealth": [p.wealth for p in self.state.players],
            "player_roles": [p.role.value for p in self.state.players],
            "winner_idx": None,
            "winner_role": None,
        }
        
        if self.state.team_win:
            winner_idx = max(range(len(self.state.players)), 
                           key=lambda i: self.state.players[i].merit)
            result["winner_idx"] = winner_idx
            result["winner_role"] = self.state.players[winner_idx].role.value
        
        return result


class MonteCarloTester:
    def __init__(self, num_simulations: int = 1000):
        self.num_simulations = num_simulations
    
    def run_simulation(self, strategies: List[Strategy], num_players: int = 4) -> Dict:
        results = []
        for _ in range(self.num_simulations):
            sim = GameSimulator(num_players, strategies)
            result = sim.run_game()
            results.append(result)
        return self._analyze_results(results)
    
    def _analyze_results(self, results: List[Dict]) -> Dict:
        team_wins = sum(1 for r in results if r["team_win"])
        
        role_wins = defaultdict(int)
        role_appearances = defaultdict(int)
        role_merits = defaultdict(list)
        role_wealth = defaultdict(list)
        
        for r in results:
            for i, role in enumerate(r["player_roles"]):
                role_appearances[role] += 1
                role_merits[role].append(r["player_merits"][i])
                role_wealth[role].append(r["player_wealth"][i])
                if r["team_win"] and r["winner_role"] == role:
                    role_wins[role] += 1
        
        analysis = {
            "total_games": len(results),
            "team_win_rate": team_wins / len(results),
            "avg_calamity": statistics.mean(r["final_calamity"] for r in results),
            "avg_saved": statistics.mean(r["saved_count"] for r in results),
            "calamity_std": statistics.stdev(r["final_calamity"] for r in results) if len(results) > 1 else 0,
            "saved_std": statistics.stdev(r["saved_count"] for r in results) if len(results) > 1 else 0,
            "role_stats": {},
        }
        
        for role in role_appearances:
            wins = role_wins[role]
            appearances = role_appearances[role]
            merits = role_merits[role]
            wealth = role_wealth[role]
            
            # 只计算团队胜利局的胜率
            team_win_games = sum(1 for r in results if r["team_win"])
            
            analysis["role_stats"][role] = {
                "win_rate": wins / team_win_games if team_win_games > 0 else 0,
                "avg_merit": statistics.mean(merits) if merits else 0,
                "merit_std": statistics.stdev(merits) if len(merits) > 1 else 0,
                "avg_wealth": statistics.mean(wealth) if wealth else 0,
                "appearances": appearances,
            }
        
        return analysis
    
    def test_all_strategies(self):
        print("=" * 80)
        print("《功德轮回》v1.0 Monte Carlo 平衡性测试 (v2)")
        print(f"每种配置模拟 {self.num_simulations} 局")
        print("=" * 80)
        
        test_configs = [
            ("全平衡型", [Strategy.BALANCED] * 4),
            ("全智能型", [Strategy.SMART] * 4),
            ("全自私型", [Strategy.SELFISH] * 4),
            ("全利他型", [Strategy.ALTRUISTIC] * 4),
            ("混合（平衡+自私+利他+智能）", 
             [Strategy.BALANCED, Strategy.SELFISH, Strategy.ALTRUISTIC, Strategy.SMART]),
            ("混合（2智能+2平衡）", 
             [Strategy.SMART, Strategy.SMART, Strategy.BALANCED, Strategy.BALANCED]),
            ("混合（1自私+3智能）", 
             [Strategy.SELFISH, Strategy.SMART, Strategy.SMART, Strategy.SMART]),
        ]
        
        all_results = {}
        
        for name, strategies in test_configs:
            print(f"\n测试配置: {name}")
            print("-" * 40)
            
            result = self.run_simulation(strategies)
            all_results[name] = result
            
            print(f"团队胜率: {result['team_win_rate']*100:.1f}%")
            print(f"平均劫难: {result['avg_calamity']:.1f} (±{result['calamity_std']:.1f})")
            print(f"平均渡化: {result['avg_saved']:.1f} (±{result['saved_std']:.1f})")
            
            print("\n角色表现（团队胜利时的个人胜率）:")
            for role, stats in result["role_stats"].items():
                print(f"  {role}: 胜率={stats['win_rate']*100:.1f}%, "
                      f"平均功德={stats['avg_merit']:.1f}")
        
        return all_results
    
    def test_role_balance(self):
        print("\n" + "=" * 80)
        print("角色平衡性专项测试")
        print("=" * 80)
        
        strategies = [Strategy.SMART] * 4  # 使用智能策略
        results = []
        
        for _ in range(self.num_simulations):
            sim = GameSimulator(4, strategies)
            result = sim.run_game()
            results.append(result)
        
        role_data = defaultdict(lambda: {"wins": 0, "games": 0, "merits": [], "wealth": []})
        team_wins = 0
        
        for r in results:
            if r["team_win"]:
                team_wins += 1
            for i, role in enumerate(r["player_roles"]):
                role_data[role]["games"] += 1
                role_data[role]["merits"].append(r["player_merits"][i])
                role_data[role]["wealth"].append(r["player_wealth"][i])
                if r["team_win"] and r["winner_idx"] == i:
                    role_data[role]["wins"] += 1
        
        print(f"\n团队胜率: {team_wins/len(results)*100:.1f}%")
        print("\n角色平衡性分析（智能策略下）:")
        print("-" * 60)
        
        win_rates = []
        for role in ["农夫", "商人", "官员", "僧侣"]:
            data = role_data[role]
            if data["games"] > 0 and team_wins > 0:
                # 个人胜率 = 在团队胜利的局中，该角色获胜的比例
                win_rate = data["wins"] / team_wins * 100
                win_rates.append(win_rate)
                avg_merit = statistics.mean(data["merits"])
                avg_wealth = statistics.mean(data["wealth"])
                merit_std = statistics.stdev(data["merits"]) if len(data["merits"]) > 1 else 0
                
                print(f"\n{role}:")
                print(f"  个人胜率: {win_rate:.1f}%")
                print(f"  平均功德: {avg_merit:.1f} (±{merit_std:.1f})")
                print(f"  平均财富: {avg_wealth:.1f}")
        
        if win_rates:
            balance_score = 100 - statistics.stdev(win_rates)
            print(f"\n平衡性得分: {balance_score:.1f}/100")
            
            if balance_score >= 90:
                print("评价: ★★★★★ 非常平衡")
            elif balance_score >= 80:
                print("评价: ★★★★☆ 比较平衡")
            elif balance_score >= 70:
                print("评价: ★★★☆☆ 一般")
            else:
                print("评价: ★★☆☆☆ 需要调整")
                
            # 分析问题
            print("\n问题诊断:")
            max_role = ["农夫", "商人", "官员", "僧侣"][win_rates.index(max(win_rates))]
            min_role = ["农夫", "商人", "官员", "僧侣"][win_rates.index(min(win_rates))]
            
            if max(win_rates) - min(win_rates) > 10:
                print(f"  - {max_role} 过强 ({max(win_rates):.1f}%)")
                print(f"  - {min_role} 过弱 ({min(win_rates):.1f}%)")
            else:
                print("  - 角色间差距在可接受范围内")
        
        return role_data
    
    def test_difficulty_curve(self):
        """测试不同难度设置"""
        print("\n" + "=" * 80)
        print("难度曲线测试")
        print("=" * 80)
        
        difficulties = [
            ("简单", {"calamity_win_max": 15, "save_required": 4}),
            ("普通", {"calamity_win_max": 12, "save_required": 6}),
            ("困难", {"calamity_win_max": 10, "save_required": 7}),
            ("地狱", {"calamity_win_max": 8, "save_required": 8}),
        ]
        
        strategies = [Strategy.SMART] * 4
        
        for name, params in difficulties:
            results = []
            for _ in range(500):
                sim = GameSimulator(4, strategies)
                sim.initialize_game()
                sim.state.calamity_win_max = params["calamity_win_max"]
                sim.state.save_required = params["save_required"]
                
                while not sim.state.game_over:
                    sim.state.current_round += 1
                    sim.run_event_phase()
                    sim.run_sentient_phase()
                    sim.run_action_phase()
                    for i, p in enumerate(sim.state.players):
                        if p.role == RoleType.MONK:
                            sim._monk_special_action(i)
                    sim.run_settlement_phase()
                
                results.append(sim.run_game())
            
            win_rate = sum(1 for r in results if r["team_win"]) / len(results) * 100
            avg_saved = statistics.mean(r["saved_count"] for r in results)
            avg_calamity = statistics.mean(r["final_calamity"] for r in results)
            
            print(f"\n{name} (劫难≤{params['calamity_win_max']}, 渡化≥{params['save_required']}):")
            print(f"  团队胜率: {win_rate:.1f}%")
            print(f"  平均渡化: {avg_saved:.1f}")
            print(f"  平均劫难: {avg_calamity:.1f}")


def run_comprehensive_test():
    print("\n" + "=" * 80)
    print("《功德轮回》v1.0 完整平衡性测试报告")
    print("=" * 80)
    
    tester = MonteCarloTester(num_simulations=2000)
    
    # 1. 策略测试
    strategy_results = tester.test_all_strategies()
    
    # 2. 角色平衡
    role_results = tester.test_role_balance()
    
    # 3. 难度曲线
    tester.test_difficulty_curve()
    
    # 4. 总结
    print("\n" + "=" * 80)
    print("测试总结与建议")
    print("=" * 80)
    
    balanced_win = strategy_results["全平衡型"]["team_win_rate"]
    smart_win = strategy_results["全智能型"]["team_win_rate"]
    selfish_win = strategy_results["全自私型"]["team_win_rate"]
    altruistic_win = strategy_results["全利他型"]["team_win_rate"]
    
    print("\n【核心指标】")
    print(f"1. 智能策略团队胜率: {smart_win*100:.1f}%")
    print(f"   (理想范围: 50-70%)")
    
    if smart_win < 0.3:
        print("   → 游戏过难，建议降低众生渡化要求或劫难增长速度")
    elif smart_win > 0.8:
        print("   → 游戏过易，建议增加劫难或提高众生费用")
    else:
        print("   → 难度适中 ✓")
    
    print(f"\n2. 自私策略团队胜率: {selfish_win*100:.1f}%")
    if selfish_win < 0.1:
        print("   → 自私策略确实导致失败 ✓")
    else:
        print("   → 警告：自私策略不应该有高胜率")
    
    print("\n3. 策略多样性:")
    if abs(balanced_win - altruistic_win) < 0.15:
        print("   → 平衡和利他策略效果相近 ✓")
    else:
        print(f"   → 策略间差距较大，可能需要调整")
    
    # 角色分析
    print("\n4. 角色平衡:")
    for role, data in role_results.items():
        if data["games"] > 0:
            avg_merit = statistics.mean(data["merits"])
            print(f"   {role}: 平均功德 {avg_merit:.1f}")
    
    return strategy_results, role_results


if __name__ == "__main__":
    run_comprehensive_test()
