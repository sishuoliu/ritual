"""
《功德轮回：众生百态》v1.1 游戏模拟器
引入删掉的机制来改善平衡性：

1. 渡化参与奖励（累积）- 激励利他
2. 持续帮助轨道 - 激励持续帮助
3. 福慧双资源 - 区分自度/度人
4. 道的评定系统 - 多样化胜利路径
5. 角色能力加强 - 角色平衡
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
    merit: int  # 现在分为福奖励
    wisdom: int = 0  # 慧奖励
    turns_in_area: int = 0
    special: str = ""

@dataclass
class Player:
    role: RoleType
    wealth: int
    fu: int  # 福（帮助他人获得）
    hui: int  # 慧（自我修行获得）
    actions_per_turn: int = 2
    help_streak: int = 0  # 连续帮助轮数
    save_count: int = 0  # 渡化次数
    helped_this_turn: bool = False

# ═══════════════════════════════════════════════════════════════════════════════
#                   角色初始值（调整）
# ═══════════════════════════════════════════════════════════════════════════════

ROLE_INIT = {
    RoleType.FARMER: {"wealth": 4, "fu": 1, "hui": 1},   # 均衡
    RoleType.MERCHANT: {"wealth": 5, "fu": 1, "hui": 1}, # 财富优势
    RoleType.OFFICIAL: {"wealth": 4, "fu": 2, "hui": 1}, # 福优势
    RoleType.MONK: {"wealth": 2, "fu": 1, "hui": 3},     # 慧优势
}

# 众生卡（福慧分离）
SENTIENT_BEINGS = [
    SentientBeing("饥民", 3, 3, 0),      # 纯福
    SentientBeing("病人", 4, 3, 1),      # 福+慧
    SentientBeing("孤儿", 3, 3, 1),
    SentientBeing("老者", 2, 2, 1),
    SentientBeing("流浪者", 5, 4, 1),
    SentientBeing("冤魂", 6, 4, 2, special="calamity_minus1"),
    SentientBeing("恶人", 7, 5, 2, special="calamity_plus1_per_turn"),
    SentientBeing("富商", 4, 2, 2, special="wealth_all"),
    SentientBeing("官吏", 5, 3, 2),
    SentientBeing("将军", 6, 4, 2, special="calamity_minus2"),
    SentientBeing("皇族", 8, 6, 3),
    SentientBeing("高僧", 6, 3, 4),  # 高慧奖励
]

# 事件卡
EVENTS = [
    {"name": "旱灾", "type": "disaster", "calamity": 3},
    {"name": "洪水", "type": "disaster", "calamity": 3},
    {"name": "瘟疫", "type": "disaster", "calamity": 2, "wealth_all": -1},
    {"name": "战乱", "type": "disaster", "calamity": 4},
    {"name": "饥荒", "type": "disaster", "calamity": 3},
    {"name": "妖邪", "type": "disaster", "calamity": 3},
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
            self.being_deck = [SentientBeing(b.name, b.cost, b.merit, b.wisdom, 0, b.special) 
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
        # 重置每轮的帮助标记
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
            # 只修行
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
            if calamity_urgent and player.wealth >= 2:
                return ActionType.PROTECT
            if urgent_beings:
                affordable_urgent = [b for b in urgent_beings if player.wealth >= b.cost]
                if affordable_urgent:
                    return ActionType.SAVE
            if player.wealth < 4:
                return ActionType.LABOR
            if saves_needed > 0 and affordable_beings:
                if saves_needed >= remaining_rounds or random.random() > 0.3:
                    return ActionType.SAVE
            if calamity_danger and player.wealth >= 3:
                if random.random() > 0.5:
                    return ActionType.DONATE
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
        role = player.role
        
        if action == ActionType.LABOR:
            # 农夫劳作加成
            bonus = 1 if role == RoleType.FARMER else 0
            player.wealth += 3 + bonus
            
        elif action == ActionType.PRACTICE:
            # 修行获得慧
            # 僧侣修行加成
            bonus = 1 if role == RoleType.MONK else 0
            player.hui += 2 + bonus
            
        elif action == ActionType.DONATE:
            if player.wealth >= 3:
                player.wealth -= 3
                player.fu += 2  # 布施获得福
                self.state.calamity = max(0, self.state.calamity - 1)
                player.helped_this_turn = True
            else:
                player.wealth += 3
                
        elif action == ActionType.PROTECT:
            if player.wealth >= 2:
                player.wealth -= 2
                player.fu += 1  # 护法获得福
                self.state.calamity = max(0, self.state.calamity - 2)
                player.helped_this_turn = True
            else:
                player.wealth += 3
                
        elif action == ActionType.SAVE:
            affordable = [b for b in self.state.sentient_area if player.wealth >= b.cost]
            if affordable:
                urgent = [b for b in affordable if b.turns_in_area >= 1]
                if urgent:
                    being = max(urgent, key=lambda b: (b.merit + b.wisdom) / b.cost)
                else:
                    being = max(affordable, key=lambda b: (b.merit + b.wisdom) / b.cost)
                
                actual_cost = being.cost
                if self.state.event_modifiers.get("free_save"):
                    actual_cost = 0
                    self.state.event_modifiers["free_save"] = False
                
                player.wealth -= actual_cost
                
                # 渡化奖励：福+慧
                player.fu += being.merit
                player.hui += being.wisdom
                
                # 【新增】渡化累积奖励
                player.save_count += 1
                bonus_fu = player.save_count  # 第N次渡化额外+N福
                player.fu += bonus_fu
                
                # 官员渡化加成：额外+1福
                if role == RoleType.OFFICIAL:
                    player.fu += 1
                
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
        """僧侣讲法：消耗1慧，目标+2福+1慧，自己+1福"""
        monk = self.state.players[monk_idx]
        strategy = self.strategies[monk_idx]
        
        if strategy in [Strategy.ALTRUISTIC, Strategy.BALANCED, Strategy.SMART]:
            if monk.hui >= 3:  # 有足够慧才讲法
                others = [(i, p) for i, p in enumerate(self.state.players) if i != monk_idx]
                if others:
                    # 给福最低的其他玩家
                    target_idx, target = min(others, key=lambda x: x[1].fu)
                    monk.hui -= 1
                    target.fu += 2
                    target.hui += 1
                    monk.fu += 1  # 讲法者自己也获得福
                    monk.helped_this_turn = True
    
    def _update_help_streak(self):
        """更新连续帮助轨道"""
        for player in self.state.players:
            if player.helped_this_turn:
                player.help_streak += 1
                # 【持续帮助奖励】连续帮助3轮以上，每轮额外+1福
                if player.help_streak >= 3:
                    player.fu += 1
            else:
                player.help_streak = 0
    
    def _evaluate_dao(self, player: Player) -> tuple:
        """评定玩家的道并计算加分"""
        fu = player.fu
        hui = player.hui
        save_count = player.save_count
        help_streak = player.help_streak
        
        # 八种道的评定
        daos = []
        
        # 菩萨道（高福+高慧+持续帮助）
        if fu >= 15 and hui >= 10 and help_streak >= 4:
            daos.append(("菩萨道", 18))
        
        # 布施道（高福）
        if fu >= 18 and hui >= 6:
            daos.append(("布施道", 15))
        
        # 济世道（渡化多）
        if save_count >= 3 and fu >= 12:
            daos.append(("济世道", 14))
        
        # 禅修道（高慧）
        if hui >= 15 and fu >= 5:
            daos.append(("禅修道", 12))
        
        # 居士道（福慧均衡）
        if fu >= 10 and hui >= 10 and abs(fu - hui) <= 5:
            daos.append(("居士道", 13))
        
        # 觉悟道（极致）
        if fu >= 20 or hui >= 20:
            daos.append(("觉悟道", 16))
        
        if daos:
            best_dao = max(daos, key=lambda x: x[1])
            return best_dao
        else:
            return ("世俗道", 5)  # 未达成任何道
    
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
        """计算最终得分"""
        fu = player.fu
        hui = player.hui
        
        # 福慧乘积得分
        if fu <= 0 or hui <= 0:
            base_score = 0
        else:
            base_score = math.sqrt(fu * hui) * 3
        
        # 道的评定加分
        dao_name, dao_bonus = self._evaluate_dao(player)
        
        # 总分
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
        
        # 计算得分
        scores = []
        for p in self.state.players:
            total, dao_name, base, dao_bonus = self._calculate_final_score(p)
            scores.append({
                "total": total,
                "dao": dao_name,
                "base": base,
                "dao_bonus": dao_bonus,
                "fu": p.fu,
                "hui": p.hui,
                "save_count": p.save_count,
            })
        
        result = {
            "team_win": self.state.team_win,
            "final_calamity": self.state.calamity,
            "saved_count": self.state.saved_count,
            "player_scores": scores,
            "player_roles": [p.role.value for p in self.state.players],
            "winner_idx": None,
            "winner_role": None,
            "winner_dao": None,
        }
        
        if self.state.team_win:
            winner_idx = max(range(len(scores)), key=lambda i: scores[i]["total"])
            result["winner_idx"] = winner_idx
            result["winner_role"] = self.state.players[winner_idx].role.value
            result["winner_dao"] = scores[winner_idx]["dao"]
        
        return result


class MonteCarloTester:
    def __init__(self, num_simulations: int = 3000):
        self.num_simulations = num_simulations
    
    def run_full_test(self):
        print("=" * 80)
        print("《功德轮回》v1.1 平衡性测试（引入删掉的机制）")
        print(f"模拟次数: {self.num_simulations}局/配置")
        print("=" * 80)
        
        print("\n【引入的机制】")
        print("1. 福慧双资源系统")
        print("2. 渡化累积奖励（第N次渡化额外+N福）")
        print("3. 持续帮助轨道（连续帮助3轮以上每轮+1福）")
        print("4. 道的评定系统（8种道）")
        print("5. 角色能力加强（僧侣修行+1慧，官员渡化+1福）")
        
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
            
            role_data = defaultdict(lambda: {"wins": 0, "fu": [], "hui": [], "scores": [], "games": 0, "daos": defaultdict(int)})
            
            for r in results:
                for i, role in enumerate(r["player_roles"]):
                    role_data[role]["games"] += 1
                    role_data[role]["fu"].append(r["player_scores"][i]["fu"])
                    role_data[role]["hui"].append(r["player_scores"][i]["hui"])
                    role_data[role]["scores"].append(r["player_scores"][i]["total"])
                    if r["team_win"]:
                        role_data[role]["daos"][r["player_scores"][i]["dao"]] += 1
                        if r["winner_idx"] == i:
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
                print("  角色表现（团队胜利时）:")
                for role in ["农夫", "商人", "官员", "僧侣"]:
                    data = role_data[role]
                    win_rate = data["wins"] / team_wins * 100 if team_wins > 0 else 0
                    avg_fu = statistics.mean(data["fu"]) if data["fu"] else 0
                    avg_hui = statistics.mean(data["hui"]) if data["hui"] else 0
                    avg_score = statistics.mean(data["scores"]) if data["scores"] else 0
                    print(f"    {role}: 胜率={win_rate:.1f}%, 福={avg_fu:.1f}, 慧={avg_hui:.1f}, 得分={avg_score:.1f}")
        
        # 详细角色分析
        print("\n" + "=" * 80)
        print("角色平衡性详细分析（智能策略）")
        print("=" * 80)
        
        smart_data = all_results["全智能型"]["role_data"]
        team_wins = all_results["全智能型"]["team_wins"]
        
        win_rates = []
        for role in ["农夫", "商人", "官员", "僧侣"]:
            data = smart_data[role]
            if team_wins > 0:
                win_rate = data["wins"] / team_wins * 100
                win_rates.append(win_rate)
                avg_fu = statistics.mean(data["fu"])
                avg_hui = statistics.mean(data["hui"])
                avg_score = statistics.mean(data["scores"])
                
                print(f"\n{role}:")
                print(f"  胜率: {win_rate:.1f}%")
                print(f"  平均福: {avg_fu:.1f}")
                print(f"  平均慧: {avg_hui:.1f}")
                print(f"  平均得分: {avg_score:.1f}")
                
                # 道的分布
                if data["daos"]:
                    top_daos = sorted(data["daos"].items(), key=lambda x: -x[1])[:3]
                    print(f"  常见道: {', '.join(f'{d[0]}({d[1]})' for d in top_daos)}")
        
        if win_rates:
            balance_score = 100 - statistics.stdev(win_rates)
            print(f"\n胜率平衡分: {balance_score:.1f}/100")
            
            if balance_score >= 85:
                print("评价: ★★★★★ 非常平衡")
            elif balance_score >= 75:
                print("评价: ★★★★☆ 比较平衡")
            elif balance_score >= 65:
                print("评价: ★★★☆☆ 一般")
            else:
                print("评价: ★★☆☆☆ 需要调整")
        
        # 策略分析
        print("\n" + "=" * 80)
        print("策略效果分析")
        print("=" * 80)
        
        smart_win = all_results["全智能型"]["team_win_rate"] * 100
        selfish_win = all_results["全自私型"]["team_win_rate"] * 100
        altruistic_win = all_results["全利他型"]["team_win_rate"] * 100
        
        print(f"\n1. 智能策略胜率: {smart_win:.1f}%")
        if 50 <= smart_win <= 70:
            print("   → 难度适中 ✓")
        elif smart_win > 70:
            print("   → 偏简单")
        else:
            print("   → 偏困难")
        
        print(f"\n2. 自私策略胜率: {selfish_win:.1f}%")
        if selfish_win < 5:
            print("   → 合作是必须的 ✓")
        
        print(f"\n3. 利他策略胜率: {altruistic_win:.1f}%")
        if altruistic_win > 20:
            print("   → 利他策略得到改善 ✓")
        
        # 混合策略中的个人胜率
        print("\n4. 混合策略中的个人表现:")
        mixed_data = all_results["混合型"]["role_data"]
        mixed_wins = all_results["混合型"]["team_wins"]
        if mixed_wins > 0:
            for role in ["农夫", "商人", "官员", "僧侣"]:
                data = mixed_data[role]
                win_rate = data["wins"] / mixed_wins * 100
                print(f"   {role}: {win_rate:.1f}%")
        
        return all_results


if __name__ == "__main__":
    tester = MonteCarloTester(num_simulations=3000)
    tester.run_full_test()
