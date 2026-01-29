"""
《功德轮回：众生百态》v1.0 游戏模拟器 v3 - 最终平衡版

基于v2测试结果的平衡性调整：
1. 游戏过易(92%胜率) → 增加难度
2. 农夫过强(57%) → 削弱劳作加成
3. 僧侣过弱(0%) → 大幅加强讲法
4. 渡化数量固定 → 增加变数
"""

import random
import statistics
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum
from collections import defaultdict

class ActionType(Enum):
    LABOR = "劳作"
    PRACTICE = "修行"
    DONATE = "布施"
    SAVE = "渡化"
    PROTECT = "护法"

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

# ═══════════════════════════════════════════════════════════════════════════════
#                   平衡调整后的游戏数据
# ═══════════════════════════════════════════════════════════════════════════════

# 角色初始值调整
ROLE_INIT = {
    RoleType.FARMER: {"wealth": 4, "merit": 2},
    RoleType.MERCHANT: {"wealth": 5, "merit": 1},   # 降低初始财富 6→5
    RoleType.OFFICIAL: {"wealth": 4, "merit": 2},   # 调整
    RoleType.MONK: {"wealth": 3, "merit": 3},       # 增加初始财富 2→3
}

# 众生卡调整：提高费用，增加奖励差异
SENTIENT_BEINGS = [
    SentientBeing("饥民", 3, 2),
    SentientBeing("病人", 4, 3),
    SentientBeing("孤儿", 3, 3, special="wealth_next"),
    SentientBeing("老者", 2, 2),
    SentientBeing("流浪者", 5, 4),
    SentientBeing("冤魂", 6, 5, special="calamity_minus1"),
    SentientBeing("恶人", 7, 6, special="calamity_plus1_per_turn"),
    SentientBeing("富商", 4, 3, special="wealth_all"),
    SentientBeing("官吏", 5, 4),
    SentientBeing("将军", 6, 5, special="calamity_minus2"),
    SentientBeing("皇族", 9, 8),
    SentientBeing("高僧", 6, 7),  # 增加功德奖励
]

# 事件卡调整：增加劫难压力
EVENTS = [
    # 劫难事件（增加频率和强度）
    Event("旱灾", "disaster", {"calamity": 3}),
    Event("洪水", "disaster", {"calamity": 3}),
    Event("瘟疫", "disaster", {"calamity": 3, "wealth_all": -1}),
    Event("战乱", "disaster", {"calamity": 4}),
    Event("饥荒", "disaster", {"calamity": 3}),
    Event("妖邪", "disaster", {"calamity": 3}),
    Event("地震", "disaster", {"calamity": 4}),
    Event("蝗灾", "disaster", {"calamity": 3, "wealth_all": -1}),
    # 机遇事件
    Event("丰收", "opportunity", {"wealth_all": 2}),
    Event("法会", "opportunity", {"merit_all": 1}),
    Event("施主到来", "opportunity", {"wealth_all": 1}),
    Event("高僧开示", "opportunity", {"merit_all": 1}),
    Event("国泰民安", "opportunity", {"calamity": -2}),
    Event("佛诞节", "opportunity", {"free_save": True}),
    # 选择事件
    Event("乞丐求施", "choice", {"cost": 1, "merit": 1}),
    Event("迷途者", "choice", {"cost": 2, "merit": 2}),
    Event("恶人忏悔", "choice", {"merit_cost": 2, "calamity": -2}),
    Event("渡河", "choice", {"cost": 1, "merit_both": 1}),
]

class Strategy(Enum):
    BALANCED = "平衡型"
    SELFISH = "自私型"
    ALTRUISTIC = "利他型"
    SMART = "智能型"
    RANDOM = "随机型"

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
    calamity_limit: int = 20
    calamity_win_max: int = 12
    save_required: int = 6
    
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
        
    def initialize_game(self):
        roles = list(RoleType)[:self.num_players]
        players = []
        for role in roles:
            init = ROLE_INIT[role]
            players.append(Player(role, init["wealth"], init["merit"]))
        self.state = GameState(players=players)
        
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
        if "free_save" in effect:
            self.state.event_modifiers["free_save"] = True
            
        if event.event_type == "choice":
            for i, player in enumerate(self.state.players):
                strategy = self.strategies[i]
                if "cost" in effect and "merit" in effect:
                    if player.wealth >= effect["cost"]:
                        if strategy in [Strategy.ALTRUISTIC, Strategy.BALANCED, Strategy.SMART]:
                            player.wealth -= effect["cost"]
                            player.merit += effect["merit"]
    
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
        
        if strategy == Strategy.RANDOM:
            return random.choice(list(ActionType)[:5])
        
        elif strategy == Strategy.SELFISH:
            return ActionType.PRACTICE
        
        elif strategy == Strategy.ALTRUISTIC:
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
            # 紧急处理
            if calamity_urgent and player.wealth >= 2:
                return ActionType.PROTECT
            
            # 防止超时
            if urgent_beings:
                affordable_urgent = [b for b in urgent_beings if player.wealth >= b.cost]
                if affordable_urgent:
                    return ActionType.SAVE
            
            # 资源管理
            if player.wealth < 4:
                return ActionType.LABOR
            
            # 渡化优先（如果需要）
            if saves_needed > 0 and affordable_beings:
                if saves_needed >= remaining_rounds or random.random() > 0.3:
                    return ActionType.SAVE
            
            # 劫难管理
            if calamity_danger and player.wealth >= 3:
                if random.random() > 0.5:
                    return ActionType.DONATE
            
            # 积累功德
            return ActionType.PRACTICE
        
        else:  # BALANCED
            if calamity_danger and player.wealth >= 2:
                if random.random() > 0.5:
                    return ActionType.PROTECT
            
            if urgent_beings:
                affordable_urgent = [b for b in urgent_beings if player.wealth >= b.cost]
                if affordable_urgent:
                    return ActionType.SAVE
            
            if saves_needed > remaining_rounds and affordable_beings:
                return ActionType.SAVE
            
            if player.wealth < 4:
                return ActionType.LABOR
            
            if affordable_beings and random.random() > 0.4:
                return ActionType.SAVE
            
            if player.wealth >= 5 and random.random() > 0.5:
                return ActionType.PRACTICE
            
            return ActionType.LABOR
    
    def _execute_action(self, player: Player, action: ActionType, player_idx: int):
        if action == ActionType.LABOR:
            # 农夫加成降低：只有第一次劳作+1
            player.wealth += 3
            
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
        """僧侣讲法：大幅加强版
        消耗1功德 → 目标+3功德，自己+1功德
        净增益：团队+3功德
        """
        monk = self.state.players[monk_idx]
        strategy = self.strategies[monk_idx]
        
        if strategy in [Strategy.ALTRUISTIC, Strategy.BALANCED, Strategy.SMART]:
            if monk.merit >= 2:
                others = [(i, p) for i, p in enumerate(self.state.players) if i != monk_idx]
                if others:
                    target_idx, target = min(others, key=lambda x: x[1].merit)
                    monk.merit -= 1
                    target.merit += 3  # 加强：2→3
                    monk.merit += 1   # 自己也+1
    
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
    def __init__(self, num_simulations: int = 3000):
        self.num_simulations = num_simulations
    
    def run_full_test(self):
        print("=" * 80)
        print("《功德轮回》v1.0 最终平衡性测试报告")
        print(f"模拟次数: {self.num_simulations}局/配置")
        print("=" * 80)
        
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
            
            role_data = defaultdict(lambda: {"wins": 0, "merits": [], "games": 0})
            for r in results:
                for i, role in enumerate(r["player_roles"]):
                    role_data[role]["games"] += 1
                    role_data[role]["merits"].append(r["player_merits"][i])
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
                print("  角色胜率（团队胜利时）:")
                for role in ["农夫", "商人", "官员", "僧侣"]:
                    data = role_data[role]
                    win_rate = data["wins"] / team_wins * 100
                    avg_merit = statistics.mean(data["merits"]) if data["merits"] else 0
                    print(f"    {role}: {win_rate:.1f}% (功德:{avg_merit:.1f})")
        
        # 角色平衡性分析
        print("\n" + "=" * 80)
        print("角色平衡性综合分析（智能策略）")
        print("=" * 80)
        
        smart_data = all_results["全智能型"]["role_data"]
        team_wins = all_results["全智能型"]["team_wins"]
        
        win_rates = []
        merit_avgs = []
        
        for role in ["农夫", "商人", "官员", "僧侣"]:
            data = smart_data[role]
            if team_wins > 0:
                win_rate = data["wins"] / team_wins * 100
                win_rates.append(win_rate)
                avg_merit = statistics.mean(data["merits"]) if data["merits"] else 0
                merit_avgs.append(avg_merit)
                print(f"\n{role}:")
                print(f"  胜率: {win_rate:.1f}%")
                print(f"  平均功德: {avg_merit:.1f}")
        
        if win_rates:
            balance_score = 100 - statistics.stdev(win_rates)
            merit_balance = 100 - statistics.stdev(merit_avgs) * 2
            
            print(f"\n胜率平衡分: {balance_score:.1f}/100")
            print(f"功德平衡分: {merit_balance:.1f}/100")
            
            overall = (balance_score + merit_balance) / 2
            print(f"综合平衡分: {overall:.1f}/100")
            
            if overall >= 85:
                print("\n评价: ★★★★★ 非常平衡")
            elif overall >= 75:
                print("\n评价: ★★★★☆ 比较平衡")
            elif overall >= 65:
                print("\n评价: ★★★☆☆ 一般")
            else:
                print("\n评价: ★★☆☆☆ 需要调整")
        
        # 难度评估
        print("\n" + "=" * 80)
        print("难度评估")
        print("=" * 80)
        
        smart_win = all_results["全智能型"]["team_win_rate"] * 100
        selfish_win = all_results["全自私型"]["team_win_rate"] * 100
        
        print(f"\n智能策略胜率: {smart_win:.1f}%")
        if 50 <= smart_win <= 70:
            print("  → 难度适中 ✓")
        elif smart_win > 70:
            print("  → 偏简单")
        else:
            print("  → 偏困难")
        
        print(f"\n自私策略胜率: {selfish_win:.1f}%")
        if selfish_win < 5:
            print("  → 合作是必须的 ✓")
        else:
            print("  → 警告：自私策略不应该有高胜率")
        
        # 生成最终建议
        print("\n" + "=" * 80)
        print("平衡性建议")
        print("=" * 80)
        
        recommendations = []
        
        if smart_win > 70:
            recommendations.append("- 增加劫难事件强度或频率")
            recommendations.append("- 提高众生渡化费用")
        elif smart_win < 50:
            recommendations.append("- 降低劫难事件强度")
            recommendations.append("- 增加正面事件数量")
        
        if win_rates:
            max_role_idx = win_rates.index(max(win_rates))
            min_role_idx = win_rates.index(min(win_rates))
            roles = ["农夫", "商人", "官员", "僧侣"]
            
            if max(win_rates) - min(win_rates) > 15:
                recommendations.append(f"- {roles[max_role_idx]}过强，考虑削弱其能力")
                recommendations.append(f"- {roles[min_role_idx]}过弱，考虑加强其能力")
        
        if recommendations:
            for r in recommendations:
                print(r)
        else:
            print("当前平衡性良好，无需大幅调整")
        
        return all_results


if __name__ == "__main__":
    tester = MonteCarloTester(num_simulations=3000)
    tester.run_full_test()
