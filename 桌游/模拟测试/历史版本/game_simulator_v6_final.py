"""
《功德轮回：众生百态》v1.3 最终平衡版

核心问题：渡化累积奖励让先渡化者优势过大

解决方案：
1. 渡化累积奖励改为固定值（不再累加）
2. 引入"合作渡化"机制：多人参与，福均分
3. 农夫能力改为：被他人帮助时，双方各+1福
4. 重新调整各角色能力
"""

import random
import statistics
import math
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

# ═══════════════════════════════════════════════════════════════════════════════
#                   v1.3 最终平衡版配置
# ═══════════════════════════════════════════════════════════════════════════════

ROLE_INIT = {
    RoleType.FARMER: {"wealth": 4, "fu": 2, "hui": 1},   # 福优势
    RoleType.MERCHANT: {"wealth": 6, "fu": 1, "hui": 1}, # 财富优势
    RoleType.OFFICIAL: {"wealth": 4, "fu": 1, "hui": 2}, # 慧优势
    RoleType.MONK: {"wealth": 3, "fu": 1, "hui": 3},     # 慧大优势
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
    SentientBeing("高僧", 5, 3, 5),  # 高慧奖励
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
    
    def _choose_action(self, player: Player, strategy: Strategy, player_idx: int) -> ActionType:
        calamity_urgent = self.state.calamity >= 14
        calamity_danger = self.state.calamity >= 8
        remaining_rounds = self.state.max_rounds - self.state.current_round
        saves_needed = self.state.save_required - self.state.saved_count
        urgent_beings = [b for b in self.state.sentient_area if b.turns_in_area >= 1]
        affordable_beings = [b for b in self.state.sentient_area if player.wealth >= b.cost]
        
        if strategy == Strategy.SELFISH:
            return ActionType.PRACTICE
        
        elif strategy == Strategy.ALTRUISTIC:
            if calamity_urgent and player.wealth >= 2:
                return ActionType.PROTECT
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
            if saves_needed > 0 and affordable_beings:
                if saves_needed >= remaining_rounds or random.random() > 0.4:
                    return ActionType.SAVE
            # 福慧平衡决策
            if player.fu < player.hui - 2 and player.wealth >= 3:
                return ActionType.DONATE
            if player.hui < player.fu - 2:
                return ActionType.PRACTICE
            # 随机在修行和布施之间选择
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
            if saves_needed > remaining_rounds and affordable_beings:
                return ActionType.SAVE
            if player.wealth < 4:
                return ActionType.LABOR
            if affordable_beings and random.random() > 0.5:
                return ActionType.SAVE
            # 福慧平衡
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
            player.wealth += 3
            # 农夫特殊：劳作时获得少量福（勤劳本身是美德）
            if role == RoleType.FARMER:
                player.fu += 1
            
        elif action == ActionType.PRACTICE:
            base_hui = 2
            # 僧侣修行+1慧
            if role == RoleType.MONK:
                base_hui += 1
            # 官员修行时也+1福（以身作则）
            if role == RoleType.OFFICIAL:
                player.fu += 1
            player.hui += base_hui
            
        elif action == ActionType.DONATE:
            if player.wealth >= 3:
                player.wealth -= 3
                base_fu = 2
                base_hui = 1  # 布施也增加慧
                # 商人布施+1福
                if role == RoleType.MERCHANT:
                    base_fu += 1
                player.fu += base_fu
                player.hui += base_hui
                self.state.calamity = max(0, self.state.calamity - 1)
                player.helped_this_turn = True
            else:
                player.wealth += 3
                
        elif action == ActionType.PROTECT:
            if player.wealth >= 2:
                player.wealth -= 2
                player.fu += 2  # 护法福+2
                player.hui += 1  # 护法也增慧
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
                player.fu += being.fu_reward
                player.hui += being.hui_reward
                
                # 固定渡化奖励（不再累加）
                player.save_count += 1
                player.fu += 2  # 固定+2福
                
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
                player.helped_this_turn = True
            else:
                player.wealth += 3
    
    def _monk_special_action(self, monk_idx: int):
        """僧侣讲法：目标+2福+1慧，自己+2福+1慧（无消耗版）"""
        monk = self.state.players[monk_idx]
        strategy = self.strategies[monk_idx]
        
        # 僧侣每轮自动讲法（不消耗）
        if strategy in [Strategy.ALTRUISTIC, Strategy.BALANCED, Strategy.SMART]:
            others = [(i, p) for i, p in enumerate(self.state.players) if i != monk_idx]
            if others:
                target_idx, target = min(others, key=lambda x: x[1].fu)
                target.fu += 2
                target.hui += 1
                monk.fu += 2
                monk.hui += 1
                monk.helped_this_turn = True
    
    def _update_help_streak(self):
        for player in self.state.players:
            if player.helped_this_turn:
                player.help_streak += 1
                if player.help_streak >= 3:
                    player.fu += 1
                    player.hui += 1  # 持续帮助福慧都增加
            else:
                player.help_streak = 0
    
    def _evaluate_dao(self, player: Player) -> tuple:
        fu = player.fu
        hui = player.hui
        save_count = player.save_count
        help_streak = player.help_streak
        
        daos = []
        
        if fu >= 15 and hui >= 15 and help_streak >= 4:
            daos.append(("菩萨道", 20))
        if fu >= 20 and hui >= 10:
            daos.append(("布施道", 16))
        if save_count >= 3 and fu >= 15:
            daos.append(("济世道", 15))
        if hui >= 20 and fu >= 10:
            daos.append(("禅修道", 16))
        if fu >= 12 and hui >= 12 and abs(fu - hui) <= 5:
            daos.append(("居士道", 14))
        if fu >= 22 or hui >= 22:
            daos.append(("觉悟道", 18))
        
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
        
        return total, dao_name, base_score, dao_bonus
    
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
        
        scores = []
        for p in self.state.players:
            total, dao_name, base, dao_bonus = self._calculate_final_score(p)
            scores.append({
                "total": total,
                "dao": dao_name,
                "fu": p.fu,
                "hui": p.hui,
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
        print("《功德轮回》v1.3 最终平衡性测试")
        print(f"模拟次数: {self.num_simulations}局/配置")
        print("=" * 80)
        
        print("\n【核心调整】")
        print("1. 渡化累积奖励改为固定+2福")
        print("2. 布施同时+2福+1慧")
        print("3. 护法同时+2福+1慧")
        print("4. 农夫劳作+1福，商人布施+1福")
        print("5. 官员修行+1福，僧侣修行+1慧")
        print("6. 僧侣讲法：无消耗，双方各+2福+1慧")
        
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
            
            role_data = defaultdict(lambda: {"wins": 0, "fu": [], "hui": [], "scores": [], "games": 0})
            
            for r in results:
                for i, role in enumerate(r["player_roles"]):
                    role_data[role]["games"] += 1
                    role_data[role]["fu"].append(r["player_scores"][i]["fu"])
                    role_data[role]["hui"].append(r["player_scores"][i]["hui"])
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
                    avg_score = statistics.mean(data["scores"]) if data["scores"] else 0
                    print(f"    {role}: 胜率={win_rate:.1f}%, 福={avg_fu:.1f}, 慧={avg_hui:.1f}, 分={avg_score:.1f}")
        
        # 核心分析
        print("\n" + "=" * 80)
        print("最终平衡性评估")
        print("=" * 80)
        
        smart_data = all_results["全智能型"]["role_data"]
        team_wins = all_results["全智能型"]["team_wins"]
        
        win_rates = []
        score_avgs = []
        
        for role in ["农夫", "商人", "官员", "僧侣"]:
            data = smart_data[role]
            if team_wins > 0:
                win_rate = data["wins"] / team_wins * 100
                win_rates.append(win_rate)
                avg_score = statistics.mean(data["scores"])
                score_avgs.append(avg_score)
                print(f"\n{role}: 胜率={win_rate:.1f}%, 平均分={avg_score:.1f}")
        
        if win_rates:
            win_balance = 100 - statistics.stdev(win_rates)
            score_balance = 100 - statistics.stdev(score_avgs)
            overall = (win_balance + score_balance) / 2
            
            print(f"\n胜率平衡分: {win_balance:.1f}/100")
            print(f"得分平衡分: {score_balance:.1f}/100")
            print(f"综合平衡分: {overall:.1f}/100")
            
            stars = "★★★★★" if overall >= 85 else "★★★★☆" if overall >= 75 else "★★★☆☆" if overall >= 65 else "★★☆☆☆"
            print(f"\n评价: {stars}")
        
        # 设计指标
        print("\n" + "=" * 80)
        print("设计指标验证")
        print("=" * 80)
        
        smart_win = all_results["全智能型"]["team_win_rate"] * 100
        selfish_win = all_results["全自私型"]["team_win_rate"] * 100
        altruistic_win = all_results["全利他型"]["team_win_rate"] * 100
        
        checks = []
        
        checks.append(("合作是必须的", selfish_win < 5, f"自私策略{selfish_win:.1f}%"))
        checks.append(("智能策略可行", 30 <= smart_win <= 80, f"智能策略{smart_win:.1f}%"))
        checks.append(("利他有回报", altruistic_win > 5, f"利他策略{altruistic_win:.1f}%"))
        
        if win_rates:
            role_gap = max(win_rates) - min(win_rates)
            checks.append(("角色差距<30%", role_gap < 30, f"差距{role_gap:.1f}%"))
        
        for name, passed, detail in checks:
            status = "✓" if passed else "✗"
            print(f"  {status} {name}: {detail}")
        
        passed_count = sum(1 for _, p, _ in checks if p)
        print(f"\n通过指标: {passed_count}/{len(checks)}")
        
        return all_results


if __name__ == "__main__":
    tester = MonteCarloTester(num_simulations=5000)
    tester.run_full_test()
