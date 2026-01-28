"""
《功德轮回：众生百态》v1.0 游戏模拟器
Monte Carlo 模拟测试平衡性

运行方式: python game_simulator.py
"""

import random
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum
from collections import defaultdict
import json

# ═══════════════════════════════════════════════════════════════════════════════
#                   游戏常量定义
# ═══════════════════════════════════════════════════════════════════════════════

class ActionType(Enum):
    LABOR = "劳作"        # +3财富
    PRACTICE = "修行"     # +2功德
    DONATE = "布施"       # -3财富, +2功德, 劫难-1
    SAVE = "渡化"         # -财富, +功德
    PROTECT = "护法"      # -2财富, 劫难-2

class RoleType(Enum):
    FARMER = "农夫"       # 劳作+1财富
    MERCHANT = "商人"     # 可交换资源
    OFFICIAL = "官员"     # 渡化可邀请他人
    MONK = "僧侣"         # 消耗1功德，他人+2功德

@dataclass
class SentientBeing:
    """众生卡"""
    name: str
    cost: int           # 渡化费用
    merit: int          # 功德奖励
    turns_in_area: int = 0
    special: str = ""

@dataclass
class Event:
    """事件卡"""
    name: str
    event_type: str     # "disaster", "opportunity", "choice"
    effect: Dict        # {"calamity": 2, "wealth_all": -1, ...}

@dataclass
class Player:
    """玩家"""
    role: RoleType
    wealth: int
    merit: int
    actions_per_turn: int = 2
    
    def can_afford(self, cost: int) -> bool:
        return self.wealth >= cost

# ═══════════════════════════════════════════════════════════════════════════════
#                   游戏数据
# ═══════════════════════════════════════════════════════════════════════════════

ROLE_INIT = {
    RoleType.FARMER: {"wealth": 4, "merit": 2},
    RoleType.MERCHANT: {"wealth": 6, "merit": 1},
    RoleType.OFFICIAL: {"wealth": 5, "merit": 1},
    RoleType.MONK: {"wealth": 2, "merit": 4},
}

SENTIENT_BEINGS = [
    SentientBeing("饥民", 3, 2),
    SentientBeing("病人", 4, 3),
    SentientBeing("孤儿", 3, 2, special="wealth_next"),
    SentientBeing("老者", 2, 2),
    SentientBeing("流浪者", 5, 4),
    SentientBeing("冤魂", 6, 5, special="calamity_minus1"),
    SentientBeing("恶人", 8, 6, special="calamity_plus1_per_turn"),
    SentientBeing("富商", 4, 2, special="wealth_all"),
    SentientBeing("官吏", 5, 3, special="action_plus1"),
    SentientBeing("将军", 7, 5, special="calamity_minus2"),
    SentientBeing("皇族", 10, 7, special="need_3_players"),
    SentientBeing("高僧", 6, 6),
]

EVENTS = [
    # 劫难事件
    Event("旱灾", "disaster", {"calamity": 2}),
    Event("洪水", "disaster", {"calamity": 3}),
    Event("瘟疫", "disaster", {"calamity": 2, "wealth_all": -1}),
    Event("战乱", "disaster", {"calamity": 4}),
    Event("饥荒", "disaster", {"calamity": 2, "save_cost": 2}),
    Event("妖邪", "disaster", {"calamity": 3, "no_practice": True}),
    # 机遇事件
    Event("丰收", "opportunity", {"wealth_all": 2}),
    Event("法会", "opportunity", {"merit_all": 1}),
    Event("施主到来", "opportunity", {"wealth_min": 3}),
    Event("高僧开示", "opportunity", {"merit_min": 2}),
    Event("国泰民安", "opportunity", {"calamity": -2}),
    Event("佛诞节", "opportunity", {"free_save": True}),
    # 选择事件
    Event("乞丐求施", "choice", {"cost": 1, "merit": 1}),
    Event("迷途者", "choice", {"cost": 2, "merit": 2}),
    Event("富商供养", "choice", {"wealth": 3, "merit": -1}),
    Event("恶人忏悔", "choice", {"merit_cost": 2, "calamity": -2}),
    Event("寺院修缮", "choice", {"cost_all": 1, "calamity_per": -1}),
    Event("渡河", "choice", {"cost": 1, "merit_both": 1}),
]

# ═══════════════════════════════════════════════════════════════════════════════
#                   AI策略定义
# ═══════════════════════════════════════════════════════════════════════════════

class Strategy(Enum):
    BALANCED = "平衡型"           # 均衡发展
    SELFISH = "自私型"            # 优先自己功德
    ALTRUISTIC = "利他型"         # 优先帮助团队
    GREEDY = "贪财型"             # 优先积累财富
    RANDOM = "随机型"             # 随机决策

# ═══════════════════════════════════════════════════════════════════════════════
#                   游戏状态
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GameState:
    """游戏状态"""
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
    
    def __post_init__(self):
        if not self.event_deck:
            self.event_deck = EVENTS.copy()
            random.shuffle(self.event_deck)
        if not self.being_deck:
            self.being_deck = [SentientBeing(b.name, b.cost, b.merit, 0, b.special) 
                              for b in SENTIENT_BEINGS]
            random.shuffle(self.being_deck)

# ═══════════════════════════════════════════════════════════════════════════════
#                   游戏逻辑
# ═══════════════════════════════════════════════════════════════════════════════

class GameSimulator:
    """游戏模拟器"""
    
    def __init__(self, num_players: int = 4, strategies: List[Strategy] = None):
        self.num_players = num_players
        self.strategies = strategies or [Strategy.BALANCED] * num_players
        self.state = None
        self.log = []
        
    def initialize_game(self):
        """初始化游戏"""
        roles = list(RoleType)[:self.num_players]
        players = []
        for role in roles:
            init = ROLE_INIT[role]
            players.append(Player(role, init["wealth"], init["merit"]))
        
        self.state = GameState(players=players)
        self.log = []
        
    def run_event_phase(self):
        """事件阶段"""
        if not self.state.event_deck:
            return
            
        event = self.state.event_deck.pop(0)
        self.log.append(f"事件: {event.name}")
        
        # 处理事件效果
        effect = event.effect
        
        if "calamity" in effect:
            self.state.calamity += effect["calamity"]
            
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
            
        # 记录事件修正
        if "save_cost" in effect:
            self.state.event_modifiers["save_cost_extra"] = effect["save_cost"]
        if "no_practice" in effect:
            self.state.event_modifiers["no_practice"] = True
        if "free_save" in effect:
            self.state.event_modifiers["free_save"] = True
            
        # 选择事件：简化处理，假设玩家会根据策略决定
        if event.event_type == "choice":
            self._handle_choice_event(event)
    
    def _handle_choice_event(self, event: Event):
        """处理选择事件"""
        effect = event.effect
        
        for i, player in enumerate(self.state.players):
            strategy = self.strategies[i]
            
            # 根据策略决定是否参与
            if "cost" in effect and "merit" in effect:
                if player.wealth >= effect["cost"]:
                    # 利他型和平衡型倾向参与
                    if strategy in [Strategy.ALTRUISTIC, Strategy.BALANCED]:
                        player.wealth -= effect["cost"]
                        player.merit += effect["merit"]
                    elif strategy == Strategy.RANDOM and random.random() > 0.5:
                        player.wealth -= effect["cost"]
                        player.merit += effect["merit"]
    
    def run_sentient_phase(self):
        """众生阶段"""
        # 增加现有众生的等待时间
        for being in self.state.sentient_area:
            being.turns_in_area += 1
            # 恶人特殊效果
            if being.special == "calamity_plus1_per_turn":
                self.state.calamity += 1
        
        # 检查超时
        timeout_beings = [b for b in self.state.sentient_area if b.turns_in_area >= 2]
        for being in timeout_beings:
            self.state.calamity += 3
            self.state.sentient_area.remove(being)
            self.log.append(f"众生超时: {being.name}, 劫难+3")
        
        # 新众生入场
        if self.state.being_deck:
            new_being = self.state.being_deck.pop(0)
            self.state.sentient_area.append(new_being)
            self.log.append(f"新众生: {new_being.name}")
    
    def run_action_phase(self):
        """行动阶段"""
        for i, player in enumerate(self.state.players):
            strategy = self.strategies[i]
            
            for _ in range(player.actions_per_turn):
                action = self._choose_action(player, strategy, i)
                self._execute_action(player, action, i)
    
    def _choose_action(self, player: Player, strategy: Strategy, player_idx: int) -> ActionType:
        """根据策略选择行动"""
        
        # 计算当前紧急程度
        calamity_urgent = self.state.calamity >= 15
        need_save = len(self.state.sentient_area) > 0 and any(
            b.turns_in_area >= 1 for b in self.state.sentient_area
        )
        
        # 获取可渡化的众生
        affordable_beings = [
            b for b in self.state.sentient_area 
            if player.wealth >= b.cost + self.state.event_modifiers.get("save_cost_extra", 0)
        ]
        
        if strategy == Strategy.RANDOM:
            actions = list(ActionType)
            return random.choice(actions)
        
        elif strategy == Strategy.SELFISH:
            # 优先修行获得功德
            if self.state.event_modifiers.get("no_practice"):
                if player.wealth >= 3:
                    return ActionType.DONATE
                return ActionType.LABOR
            return ActionType.PRACTICE
        
        elif strategy == Strategy.ALTRUISTIC:
            # 优先帮助团队
            if calamity_urgent and player.wealth >= 2:
                return ActionType.PROTECT
            if affordable_beings:
                return ActionType.SAVE
            if player.wealth >= 3:
                return ActionType.DONATE
            return ActionType.LABOR
        
        elif strategy == Strategy.GREEDY:
            # 优先积累财富
            if player.role == RoleType.FARMER:
                return ActionType.LABOR
            if player.wealth < 5:
                return ActionType.LABOR
            # 财富足够时才帮助
            if affordable_beings and player.wealth > 8:
                return ActionType.SAVE
            return ActionType.LABOR
        
        else:  # BALANCED
            # 平衡策略
            if calamity_urgent and player.wealth >= 2:
                return ActionType.PROTECT
            
            if need_save and affordable_beings:
                return ActionType.SAVE
            
            if player.wealth < 4:
                return ActionType.LABOR
            
            if player.wealth >= 6 and not self.state.event_modifiers.get("no_practice"):
                if random.random() > 0.5:
                    return ActionType.PRACTICE
                return ActionType.DONATE
            
            if self.state.event_modifiers.get("no_practice"):
                return ActionType.LABOR
            
            return ActionType.PRACTICE if random.random() > 0.4 else ActionType.LABOR
    
    def _execute_action(self, player: Player, action: ActionType, player_idx: int):
        """执行行动"""
        
        if action == ActionType.LABOR:
            bonus = 1 if player.role == RoleType.FARMER else 0
            player.wealth += 3 + bonus
            
        elif action == ActionType.PRACTICE:
            if not self.state.event_modifiers.get("no_practice"):
                player.merit += 2
            else:
                player.wealth += 3  # 不能修行时改为劳作
            
        elif action == ActionType.DONATE:
            if player.wealth >= 3:
                player.wealth -= 3
                player.merit += 2
                self.state.calamity = max(0, self.state.calamity - 1)
            else:
                player.wealth += 3  # 资源不足时改为劳作
                
        elif action == ActionType.PROTECT:
            if player.wealth >= 2:
                player.wealth -= 2
                self.state.calamity = max(0, self.state.calamity - 2)
            else:
                player.wealth += 3  # 资源不足时改为劳作
                
        elif action == ActionType.SAVE:
            cost_extra = self.state.event_modifiers.get("save_cost_extra", 0)
            affordable = [
                b for b in self.state.sentient_area 
                if player.wealth >= b.cost + cost_extra
            ]
            
            if affordable:
                # 选择性价比最高的众生
                being = max(affordable, key=lambda b: b.merit / (b.cost + cost_extra))
                actual_cost = being.cost + cost_extra
                
                # 检查是否免费渡化
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
                self.log.append(f"玩家{player_idx+1}渡化: {being.name}")
            else:
                player.wealth += 3  # 无法渡化时改为劳作
    
    def _monk_special_action(self, monk_idx: int):
        """僧侣特殊行动：讲法"""
        monk = self.state.players[monk_idx]
        strategy = self.strategies[monk_idx]
        
        # 利他型僧侣更倾向于讲法
        if strategy == Strategy.ALTRUISTIC and monk.merit >= 2:
            # 给功德最低的其他玩家
            others = [(i, p) for i, p in enumerate(self.state.players) if i != monk_idx]
            if others:
                target_idx, target = min(others, key=lambda x: x[1].merit)
                monk.merit -= 1
                target.merit += 2
                self.log.append(f"僧侣讲法给玩家{target_idx+1}")
    
    def run_settlement_phase(self):
        """结算阶段"""
        # 清除本轮事件修正
        self.state.event_modifiers = {}
        
        # 检查失败条件
        if self.state.calamity >= 20:
            self.state.game_over = True
            self.state.team_win = False
            self.log.append("劫难≥20，团队失败！")
            return
        
        # 检查是否最后一轮
        if self.state.current_round >= self.state.max_rounds:
            self.state.game_over = True
            if self.state.calamity <= 12 and self.state.saved_count >= 6:
                self.state.team_win = True
                self.log.append(f"团队胜利！劫难={self.state.calamity}, 渡化={self.state.saved_count}")
            else:
                self.state.team_win = False
                self.log.append(f"团队失败！劫难={self.state.calamity}, 渡化={self.state.saved_count}")
    
    def run_game(self) -> Dict:
        """运行一局游戏"""
        self.initialize_game()
        
        while not self.state.game_over:
            self.state.current_round += 1
            
            # 阶段1：事件
            self.run_event_phase()
            
            # 阶段2：众生
            self.run_sentient_phase()
            
            # 阶段3：行动
            self.run_action_phase()
            
            # 僧侣特殊行动
            for i, p in enumerate(self.state.players):
                if p.role == RoleType.MONK:
                    self._monk_special_action(i)
            
            # 阶段4：结算
            self.run_settlement_phase()
        
        # 收集结果
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


# ═══════════════════════════════════════════════════════════════════════════════
#                   Monte Carlo 模拟测试
# ═══════════════════════════════════════════════════════════════════════════════

class MonteCarloTester:
    """Monte Carlo 模拟测试器"""
    
    def __init__(self, num_simulations: int = 1000):
        self.num_simulations = num_simulations
        self.results = []
    
    def run_simulation(self, strategies: List[Strategy], num_players: int = 4) -> Dict:
        """运行指定策略组合的模拟"""
        results = []
        
        for _ in range(self.num_simulations):
            sim = GameSimulator(num_players, strategies)
            result = sim.run_game()
            results.append(result)
        
        return self._analyze_results(results)
    
    def _analyze_results(self, results: List[Dict]) -> Dict:
        """分析模拟结果"""
        team_wins = sum(1 for r in results if r["team_win"])
        
        # 按角色统计胜率
        role_wins = defaultdict(int)
        role_appearances = defaultdict(int)
        role_merits = defaultdict(list)
        
        for r in results:
            for i, role in enumerate(r["player_roles"]):
                role_appearances[role] += 1
                role_merits[role].append(r["player_merits"][i])
                if r["team_win"] and r["winner_role"] == role:
                    role_wins[role] += 1
        
        # 计算统计数据
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
            
            analysis["role_stats"][role] = {
                "win_rate": wins / appearances if appearances > 0 else 0,
                "avg_merit": statistics.mean(merits) if merits else 0,
                "merit_std": statistics.stdev(merits) if len(merits) > 1 else 0,
                "appearances": appearances,
            }
        
        return analysis
    
    def test_all_strategies(self):
        """测试不同策略组合"""
        print("=" * 80)
        print("《功德轮回》v1.0 Monte Carlo 平衡性测试")
        print(f"每种配置模拟 {self.num_simulations} 局")
        print("=" * 80)
        
        test_configs = [
            ("全平衡型", [Strategy.BALANCED] * 4),
            ("全自私型", [Strategy.SELFISH] * 4),
            ("全利他型", [Strategy.ALTRUISTIC] * 4),
            ("全贪财型", [Strategy.GREEDY] * 4),
            ("混合1（平衡+自私+利他+贪财）", 
             [Strategy.BALANCED, Strategy.SELFISH, Strategy.ALTRUISTIC, Strategy.GREEDY]),
            ("混合2（2平衡+2自私）", 
             [Strategy.BALANCED, Strategy.BALANCED, Strategy.SELFISH, Strategy.SELFISH]),
            ("混合3（2平衡+2利他）", 
             [Strategy.BALANCED, Strategy.BALANCED, Strategy.ALTRUISTIC, Strategy.ALTRUISTIC]),
            ("混合4（1自私+3利他）", 
             [Strategy.SELFISH, Strategy.ALTRUISTIC, Strategy.ALTRUISTIC, Strategy.ALTRUISTIC]),
            ("全随机型", [Strategy.RANDOM] * 4),
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
            
            print("\n角色表现:")
            for role, stats in result["role_stats"].items():
                print(f"  {role}: 胜率={stats['win_rate']*100:.1f}%, "
                      f"平均功德={stats['avg_merit']:.1f} (±{stats['merit_std']:.1f})")
        
        return all_results
    
    def test_role_balance(self):
        """专门测试角色平衡性"""
        print("\n" + "=" * 80)
        print("角色平衡性专项测试")
        print("=" * 80)
        
        # 使用平衡策略测试角色
        strategies = [Strategy.BALANCED] * 4
        results = []
        
        for _ in range(self.num_simulations):
            sim = GameSimulator(4, strategies)
            result = sim.run_game()
            results.append(result)
        
        # 统计每个角色的胜率和功德
        role_data = defaultdict(lambda: {"wins": 0, "games": 0, "merits": [], "wealth": []})
        
        for r in results:
            for i, role in enumerate(r["player_roles"]):
                role_data[role]["games"] += 1
                role_data[role]["merits"].append(r["player_merits"][i])
                role_data[role]["wealth"].append(r["player_wealth"][i])
                if r["team_win"] and r["winner_idx"] == i:
                    role_data[role]["wins"] += 1
        
        print("\n角色平衡性分析（平衡策略下）:")
        print("-" * 60)
        
        for role in ["农夫", "商人", "官员", "僧侣"]:
            data = role_data[role]
            if data["games"] > 0:
                win_rate = data["wins"] / data["games"] * 100
                avg_merit = statistics.mean(data["merits"])
                avg_wealth = statistics.mean(data["wealth"])
                merit_std = statistics.stdev(data["merits"]) if len(data["merits"]) > 1 else 0
                
                print(f"\n{role}:")
                print(f"  个人胜率: {win_rate:.1f}%")
                print(f"  平均功德: {avg_merit:.1f} (±{merit_std:.1f})")
                print(f"  平均财富: {avg_wealth:.1f}")
        
        # 计算平衡性指标
        win_rates = [role_data[r]["wins"] / role_data[r]["games"] * 100 
                    for r in ["农夫", "商人", "官员", "僧侣"] if role_data[r]["games"] > 0]
        
        if win_rates:
            balance_score = 100 - statistics.stdev(win_rates)
            print(f"\n平衡性得分: {balance_score:.1f}/100 (越高越平衡)")
            
            if balance_score >= 90:
                print("评价: ★★★★★ 非常平衡")
            elif balance_score >= 80:
                print("评价: ★★★★☆ 比较平衡")
            elif balance_score >= 70:
                print("评价: ★★★☆☆ 一般平衡")
            else:
                print("评价: ★★☆☆☆ 需要调整")
        
        return role_data
    
    def test_parameter_sensitivity(self):
        """参数敏感性测试"""
        print("\n" + "=" * 80)
        print("参数敏感性测试")
        print("=" * 80)
        
        # 测试不同劳作收益对游戏的影响
        original_labor = 3
        test_values = [2, 3, 4, 5]
        
        print("\n劳作收益敏感性测试:")
        print("-" * 40)
        
        # 由于我们无法在运行时修改常量，这里模拟分析
        # 实际测试需要修改游戏逻辑
        
        # 改为测试不同游戏轮数
        print("\n游戏轮数敏感性测试:")
        for rounds in [4, 5, 6, 7, 8]:
            results = []
            for _ in range(500):
                sim = GameSimulator(4, [Strategy.BALANCED] * 4)
                sim.initialize_game()
                sim.state.max_rounds = rounds
                result = sim.run_game()
                results.append(result)
            
            win_rate = sum(1 for r in results if r["team_win"]) / len(results) * 100
            avg_calamity = statistics.mean(r["final_calamity"] for r in results)
            
            print(f"  {rounds}轮: 团队胜率={win_rate:.1f}%, 平均劫难={avg_calamity:.1f}")


def run_comprehensive_test():
    """运行完整测试套件"""
    tester = MonteCarloTester(num_simulations=2000)
    
    # 1. 测试所有策略组合
    strategy_results = tester.test_all_strategies()
    
    # 2. 角色平衡性测试
    role_results = tester.test_role_balance()
    
    # 3. 参数敏感性测试
    tester.test_parameter_sensitivity()
    
    # 4. 生成总结报告
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    print("\n【核心发现】")
    
    # 分析团队胜率
    balanced_win = strategy_results["全平衡型"]["team_win_rate"]
    selfish_win = strategy_results["全自私型"]["team_win_rate"]
    altruistic_win = strategy_results["全利他型"]["team_win_rate"]
    
    print(f"\n1. 团队胜率分析:")
    print(f"   - 全平衡型: {balanced_win*100:.1f}%")
    print(f"   - 全自私型: {selfish_win*100:.1f}%")
    print(f"   - 全利他型: {altruistic_win*100:.1f}%")
    
    if selfish_win < balanced_win < altruistic_win:
        print("   → 结论: 利他行为确实有助于团队胜利 ✓")
    elif selfish_win > altruistic_win:
        print("   → 警告: 自私策略反而更容易赢，需要调整！")
    
    # 分析个人胜率
    print(f"\n2. 混合策略下的个人胜率:")
    mixed_stats = strategy_results["混合1（平衡+自私+利他+贪财）"]["role_stats"]
    for role, stats in mixed_stats.items():
        print(f"   - {role}: {stats['win_rate']*100:.1f}%")
    
    # 分析僧侣困境
    monk_stats = role_results.get("僧侣", {})
    farmer_stats = role_results.get("农夫", {})
    
    if monk_stats and farmer_stats:
        monk_win = monk_stats["wins"] / monk_stats["games"] * 100 if monk_stats["games"] > 0 else 0
        farmer_win = farmer_stats["wins"] / farmer_stats["games"] * 100 if farmer_stats["games"] > 0 else 0
        
        print(f"\n3. 僧侣困境分析:")
        print(f"   - 僧侣胜率: {monk_win:.1f}%")
        print(f"   - 农夫胜率: {farmer_win:.1f}%")
        
        if monk_win < farmer_win * 0.7:
            print("   → 警告: 僧侣明显弱势，讲法能力需要加强！")
        elif abs(monk_win - farmer_win) < 5:
            print("   → 结论: 角色平衡良好 ✓")
    
    return strategy_results, role_results


if __name__ == "__main__":
    run_comprehensive_test()
