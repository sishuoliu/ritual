# -*- coding: utf-8 -*-
"""
救赎之路 v7.3 - 最终平衡版
核心调整：
1. 大幅提高提前胜利难度 -> 目标10-20%提前胜利率
2. 恢复v6.3的基础平衡参数
3. 转职主要是效率提升，而非胜利捷径
"""

import random
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import time
from itertools import permutations

class Path(Enum):
    NIRVANA = "福田道"
    CHARITY = "布施道"
    TEMPLE = "土地道"
    CULTURE = "文化道"
    DILIGENCE = "勤劳道"
    SALVATION = "渡化道"

class AscensionClass(Enum):
    ARHAT = "罗汉"
    MAHADANAPATI = "大檀越"
    TEMPLE_MASTER = "舍宅主"
    MANJUSRI = "文殊化身"
    WANDERING_MONK = "行脚僧"
    BODHISATTVA = "菩萨"

class AIStrategy(Enum):
    AGGRESSIVE = "激进型"
    CONSERVATIVE = "保守型"
    BALANCED = "平衡型"
    RANDOM = "随机型"
    OPPORTUNISTIC = "机会型"

ALL_PATHS = list(Path)
ALL_STRATEGIES = list(AIStrategy)

@dataclass
class EventCard:
    id: int
    name: str
    copies: int

EVENT_CARDS = [EventCard(i, f"Event{i}", 2) for i in range(1, 16)]

def build_event_deck():
    deck = []
    for card in EVENT_CARDS:
        for _ in range(card.copies):
            deck.append(card)
    random.shuffle(deck)
    return deck

@dataclass
class Player:
    player_id: int
    path: Path
    strategy: AIStrategy
    num_players: int = 4
    
    wealth: int = 6
    merit: int = 2
    influence: int = 3
    land: int = 1
    
    base_action_points: int = 2
    action_points: int = 2
    
    total_donated: int = 0
    influence_spent: int = 0
    kindness_count: int = 0
    kindness_targets: Set = field(default_factory=set)
    transfer_count: int = 0
    transfer_targets: Set = field(default_factory=set)
    farming_count: int = 0
    land_donated: int = 0
    has_built_temple: bool = False
    
    has_ascended: bool = False
    ascension_class: Optional[AscensionClass] = None
    small_path_completed: bool = False
    initial_rank: int = 0
    
    def __post_init__(self):
        # v7.3 恢复v6.3基础平衡
        if self.path == Path.NIRVANA:
            self.influence += 5
            self.merit += 2
        elif self.path == Path.CHARITY:
            self.wealth += 6
        elif self.path == Path.TEMPLE:
            self.land += 1
            self.wealth += 2
        elif self.path == Path.CULTURE:
            self.influence += 2
            self.wealth += 2
        elif self.path == Path.DILIGENCE:
            self.base_action_points = 3
            self.action_points = 3
        elif self.path == Path.SALVATION:
            self.merit += 5
            self.influence += 2
    
    def update_path_completion(self):
        if self.path == Path.NIRVANA:
            if len(self.transfer_targets) >= 1:
                self.small_path_completed = True
        elif self.path == Path.CHARITY:
            if self.total_donated >= 7:
                self.small_path_completed = True
        elif self.path == Path.TEMPLE:
            if self.has_built_temple or self.land_donated >= 2:
                self.small_path_completed = True
        elif self.path == Path.CULTURE:
            if self.influence >= 5 or len(self.kindness_targets) >= 2:
                self.small_path_completed = True
        elif self.path == Path.DILIGENCE:
            if self.kindness_count >= 3 or self.farming_count >= 3:
                self.small_path_completed = True
        elif self.path == Path.SALVATION:
            if self.transfer_count >= 1 or len(self.kindness_targets) >= 1:
                self.small_path_completed = True
    
    def get_current_score(self) -> float:
        base_score = self.merit * 2 + self.influence + self.wealth / 3 + self.land * 2
        path_complete, _, path_bonus = self.check_path_completion()
        if path_complete:
            base_score += path_bonus
        return base_score
    
    def get_rank(self, players: List['Player']) -> int:
        scores = [(p.get_current_score(), p.player_id) for p in players]
        scores.sort(reverse=True)
        for idx, (score, pid) in enumerate(scores):
            if pid == self.player_id:
                return idx + 1
        return len(players)
    
    def get_ascension_cost(self, players: List['Player']) -> Tuple[int, int, int]:
        base_merit = 5
        rank = self.get_rank(players)
        total_players = len(players)
        
        if rank <= total_players * 0.25:
            merit_cost = base_merit + 2
        elif rank > total_players * 0.5:
            merit_cost = base_merit - 2
        else:
            merit_cost = base_merit
        
        return (max(1, merit_cost), 3, 3)
    
    def can_ascend(self, players: List['Player'], round_num: int) -> bool:
        if self.has_ascended or not self.small_path_completed or round_num < 5:
            return False
        
        merit_cost, inf_cost, wealth_cost = self.get_ascension_cost(players)
        return (self.merit >= merit_cost and 
                self.influence >= inf_cost and 
                self.wealth >= wealth_cost)
    
    def ascend(self, players: List['Player']):
        merit_cost, inf_cost, wealth_cost = self.get_ascension_cost(players)
        self.initial_rank = self.get_rank(players)
        
        self.merit -= merit_cost
        self.influence -= inf_cost
        self.wealth -= wealth_cost
        self.has_ascended = True
        
        path_to_class = {
            Path.NIRVANA: AscensionClass.ARHAT,
            Path.CHARITY: AscensionClass.MAHADANAPATI,
            Path.TEMPLE: AscensionClass.TEMPLE_MASTER,
            Path.CULTURE: AscensionClass.MANJUSRI,
            Path.DILIGENCE: AscensionClass.WANDERING_MONK,
            Path.SALVATION: AscensionClass.BODHISATTVA,
        }
        self.ascension_class = path_to_class[self.path]
    
    def check_early_victory(self, players: List['Player']) -> bool:
        """v7.3 提前胜利条件大幅提高"""
        if not self.has_ascended:
            return False
        
        rank = self.get_rank(players)
        num_players = len(players)
        
        # 提前胜利需要完成道路完整条件 + 额外苛刻条件
        path_complete, path_name, _ = self.check_path_completion()
        if not path_complete or "(小成)" in path_name:
            return False  # 必须完成完整道路
        
        if self.ascension_class == AscensionClass.ARHAT:
            # 完成福田道 + 回向所有人 + 高功德
            targets_needed = num_players - 1
            merit_req = 15 - (rank - 1) * 2
            return len(self.transfer_targets) >= targets_needed and self.merit >= merit_req
        
        elif self.ascension_class == AscensionClass.MAHADANAPATI:
            # 完成布施道 + 捐献35 + 低财富
            return self.total_donated >= 35 and self.wealth <= rank + 2
        
        elif self.ascension_class == AscensionClass.TEMPLE_MASTER:
            # 完成土地道 + 捐地7 + 无土地
            return self.land_donated >= 7 and self.land == 0
        
        elif self.ascension_class == AscensionClass.MANJUSRI:
            # 完成文化道 + 善行所有人 + 高影响
            targets_needed = num_players - 1
            return len(self.kindness_targets) >= targets_needed and self.influence >= 12
        
        elif self.ascension_class == AscensionClass.WANDERING_MONK:
            # 完成勤劳道 + 善行15 + 耕作15
            return self.kindness_count >= 15 and self.farming_count >= 15
        
        elif self.ascension_class == AscensionClass.BODHISATTVA:
            # 完成渡化道 + 回向所有人 + 高功德
            targets_needed = num_players - 1
            merit_req = 12 - (rank - 1) * 2
            all_helped = self.transfer_targets | self.kindness_targets
            return len(all_helped) >= targets_needed and self.merit >= merit_req
        
        return False
    
    def get_ascension_bonus_multiplier(self, action: str) -> float:
        if not self.has_ascended:
            return 1.0
        
        bonuses = {
            (AscensionClass.ARHAT, "practice"): 0.5,
            (AscensionClass.MAHADANAPATI, "donate"): 1.5,
            (AscensionClass.TEMPLE_MASTER, "donate_land"): 1.5,
            (AscensionClass.MANJUSRI, "kindness"): 1.5,
            (AscensionClass.BODHISATTVA, "transfer"): 2.0,
        }
        return bonuses.get((self.ascension_class, action), 1.0)
    
    def check_path_completion(self) -> Tuple[bool, str, int]:
        multiplier = 1.2 if self.num_players == 3 else (0.9 if self.num_players >= 5 else 1.0)
        
        base_bonus = 25
        small_bonus = 12
        
        conditions = {
            Path.NIRVANA: (
                len(self.transfer_targets) >= 3 and self.influence_spent >= 4,
                len(self.transfer_targets) >= 1,
                "福田道"
            ),
            Path.CHARITY: (
                self.total_donated >= 12 and self.influence >= 3,
                self.total_donated >= 7,
                "布施道"
            ),
            Path.TEMPLE: (
                self.has_built_temple and self.land_donated >= 3,
                self.has_built_temple or self.land_donated >= 2,
                "土地道"
            ),
            Path.CULTURE: (
                self.influence >= 7 and len(self.kindness_targets) >= 3,
                self.influence >= 5 or len(self.kindness_targets) >= 2,
                "文化道"
            ),
            Path.DILIGENCE: (
                self.kindness_count >= 5 and self.farming_count >= 5,
                self.kindness_count >= 3 or self.farming_count >= 3,
                "勤劳道"
            ),
            Path.SALVATION: (
                self.transfer_count >= 3 and len(self.transfer_targets | self.kindness_targets) >= 2,
                self.transfer_count >= 1 or len(self.kindness_targets) >= 1,
                "渡化道"
            ),
        }
        
        full_cond, small_cond, name = conditions[self.path]
        
        if full_cond:
            return (True, name, int(base_bonus * multiplier))
        elif small_cond:
            self.small_path_completed = True
            return (True, f"{name}（小成）", int(small_bonus * multiplier))
        
        return (False, "", 0)
    
    def get_final_score(self) -> float:
        base_score = self.merit * 2 + self.influence + self.wealth / 3 + self.land * 2
        path_complete, _, path_bonus = self.check_path_completion()
        return base_score + path_bonus
    
    def apply_ascension_abilities(self):
        if not self.has_ascended:
            return
        
        if self.ascension_class == AscensionClass.ARHAT:
            self.merit += 1
        elif self.ascension_class == AscensionClass.MAHADANAPATI:
            self.wealth += 2
        elif self.ascension_class == AscensionClass.TEMPLE_MASTER:
            if self.has_built_temple:
                self.merit += 1
        elif self.ascension_class == AscensionClass.MANJUSRI:
            if self.influence >= 8:
                self.merit += 1

class AIDecisionMaker:
    @staticmethod
    def decide_action(player: Player, game: Dict, others: List[Player]) -> Optional[str]:
        # 转职后也继续使用道路策略，而不是只追求提前胜利
        strategy = player.strategy
        
        if strategy == AIStrategy.RANDOM:
            return AIDecisionMaker._random_action(player, others)
        elif strategy == AIStrategy.AGGRESSIVE:
            return AIDecisionMaker._aggressive_action(player, others, game)
        elif strategy == AIStrategy.CONSERVATIVE:
            return AIDecisionMaker._conservative_action(player, others)
        elif strategy == AIStrategy.BALANCED:
            return AIDecisionMaker._balanced_action(player, others, game)
        elif strategy == AIStrategy.OPPORTUNISTIC:
            return AIDecisionMaker._opportunistic_action(player, game, others)
        
        return None
    
    @staticmethod
    def _get_available_actions(player: Player, others: List[Player]) -> List[str]:
        actions = ["farm"]
        if player.wealth >= 3:
            actions.append("donate")
        if player.influence >= 2:
            actions.append("practice")
        if player.wealth >= 1 and others:
            actions.append("kindness")
        if player.merit >= 2 and others:
            actions.append("transfer")
        if not player.has_built_temple:
            if player.wealth >= 8 and player.influence >= 2:
                actions.append("build_temple")
            elif player.land >= 2:
                actions.append("build_temple_land")
        if player.land >= 1:
            actions.append("donate_land")
        return actions
    
    @staticmethod
    def _random_action(player: Player, others: List[Player]) -> Optional[str]:
        actions = AIDecisionMaker._get_available_actions(player, others)
        return random.choice(actions) if actions else None
    
    @staticmethod
    def _aggressive_action(player: Player, others: List[Player], game: Dict) -> Optional[str]:
        if not player.has_built_temple:
            if player.land >= 2:
                return "build_temple_land"
            if player.wealth >= 8 and player.influence >= 2:
                return "build_temple"
        
        if player.wealth >= 6:
            return "donate"
        if player.merit >= 2 and others:
            return "transfer"
        if player.influence >= 2:
            return "practice"
        if player.wealth >= 3:
            return "donate"
        return "farm"
    
    @staticmethod
    def _conservative_action(player: Player, others: List[Player]) -> Optional[str]:
        if player.wealth < 5:
            return "farm"
        if player.wealth >= 1 and others:
            return "kindness"
        if player.wealth >= 6:
            return "donate"
        if player.influence >= 3:
            return "practice"
        return "farm"
    
    @staticmethod
    def _balanced_action(player: Player, others: List[Player], game: Dict) -> Optional[str]:
        path = player.path
        if path == Path.NIRVANA:
            if player.merit >= 2 and others and len(player.transfer_targets) < 3:
                return "transfer"
            if player.influence >= 2:
                return "practice"
        elif path == Path.CHARITY:
            if player.wealth >= 3:
                return "donate"
            return "farm"
        elif path == Path.TEMPLE:
            if not player.has_built_temple and player.land >= 2:
                return "build_temple_land"
            if player.land >= 1 and player.land_donated < 3:
                return "donate_land"
            return "farm"
        elif path == Path.CULTURE:
            if player.wealth >= 1 and others and len(player.kindness_targets) < 3:
                return "kindness"
            if player.influence >= 2:
                return "practice"
        elif path == Path.DILIGENCE:
            if player.kindness_count < 5 and player.wealth >= 1 and others:
                return "kindness"
            if player.farming_count < 5:
                return "farm"
        elif path == Path.SALVATION:
            if player.merit >= 2 and others:
                return "transfer"
            if player.wealth >= 1 and others:
                return "kindness"
        
        return AIDecisionMaker._random_action(player, others)
    
    @staticmethod
    def _opportunistic_action(player: Player, game: Dict, others: List[Player]) -> Optional[str]:
        round_num = game["round"]
        
        if round_num <= 3:
            if player.wealth < 8:
                return "farm"
        elif round_num <= 6:
            return AIDecisionMaker._balanced_action(player, others, game)
        else:
            if not player.has_built_temple and player.land >= 2:
                return "build_temple_land"
            if player.wealth >= 3:
                return "donate"
        
        return AIDecisionMaker._balanced_action(player, others, game)
    
    @staticmethod
    def decide_ascension(player: Player, players: List[Player], round_num: int) -> bool:
        if not player.can_ascend(players, round_num):
            return False
        
        strategy = player.strategy
        rank = player.get_rank(players)
        total_players = len(players)
        
        # 弱者更倾向转职
        if rank > total_players * 0.5:
            return random.random() < 0.7
        
        if strategy == AIStrategy.AGGRESSIVE:
            return random.random() < 0.5
        elif strategy == AIStrategy.CONSERVATIVE:
            return random.random() < 0.2
        elif strategy == AIStrategy.BALANCED:
            return random.random() < 0.4
        elif strategy == AIStrategy.OPPORTUNISTIC:
            return round_num >= 7
        
        return random.random() < 0.4
    
    @staticmethod
    def decide_event_option(player: Player, event: EventCard) -> str:
        return random.choice(["A", "B"])

class GameSimulator:
    def __init__(self, num_players: int = 4):
        self.num_players = num_players
    
    def create_game(self, paths: List[Path], strategies: List[AIStrategy]) -> Dict:
        players = [
            Player(i, paths[i], strategies[i], self.num_players)
            for i in range(self.num_players)
        ]
        return {
            "players": players,
            "round": 1,
            "event_deck": build_event_deck(),
            "early_victory": False,
        }
    
    def process_event(self, game: Dict, event: EventCard):
        for p in game["players"]:
            option = random.choice(["A", "B"])
            
            if event.id in [1, 7, 9]:
                if option == "A":
                    p.wealth += 3
                else:
                    p.merit += 1
                    p.influence += 1
            elif event.id in [2, 13, 14]:
                if option == "A":
                    p.merit += 2
                else:
                    p.influence += 2
            elif event.id in [3, 10, 11, 12]:
                if option == "A":
                    p.wealth = max(0, p.wealth - 3)
                else:
                    p.merit = max(0, p.merit - 1)
            elif event.id in [4, 5, 6]:
                if option == "A" and p.wealth >= 2:
                    p.wealth -= 2
                    p.merit += 3
            else:
                p.influence += 1
    
    def production_phase(self, game: Dict):
        for p in game["players"]:
            p.wealth += 2
            p.influence += 1
            
            land_bonus = 1 if p.path in [Path.TEMPLE, Path.DILIGENCE] else 0
            p.wealth += p.land * (1 + land_bonus)
            
            if p.has_ascended and p.ascension_class == AscensionClass.TEMPLE_MASTER:
                p.wealth += p.land
    
    def action_phase(self, game: Dict):
        players = game["players"]
        
        for p in players:
            p.action_points = p.base_action_points
            if p.has_ascended and p.ascension_class == AscensionClass.WANDERING_MONK:
                p.action_points += 1
            
            others = [o for o in players if o.player_id != p.player_id]
            
            while p.action_points > 0:
                action = AIDecisionMaker.decide_action(p, game, others)
                if action is None:
                    break
                
                self.execute_action(p, action, game, others)
                p.action_points -= 1
    
    def execute_action(self, player: Player, action: str, game: Dict, others: List[Player]):
        multiplier = player.get_ascension_bonus_multiplier(action)
        
        if action == "donate":
            if player.wealth >= 3:
                player.wealth -= 3
                player.total_donated += 3
                player.merit += int(1 * multiplier)
                
                if player.has_ascended and player.ascension_class == AscensionClass.MAHADANAPATI:
                    if others:
                        random.choice(others).merit += 1
        
        elif action == "practice":
            cost = 1 if (player.has_ascended and player.ascension_class == AscensionClass.ARHAT) else 2
            if player.influence >= cost:
                player.influence -= cost
                player.influence_spent += cost
                player.merit += 1
        
        elif action == "kindness":
            if player.wealth >= 1 and others:
                player.wealth -= 1
                player.kindness_count += 1
                player.merit += int(1 * multiplier)
                
                target = random.choice(others)
                target.merit += 1
                player.kindness_targets.add(target.player_id)
                
                if player.has_ascended and player.ascension_class == AscensionClass.MANJUSRI:
                    player.influence += 1
                if player.has_ascended and player.ascension_class == AscensionClass.WANDERING_MONK:
                    player.wealth += 1
        
        elif action == "transfer":
            if player.merit >= 2 and others:
                player.merit -= 2
                player.transfer_count += 1
                
                target = random.choice(others)
                target.merit += int(3 * multiplier)
                player.transfer_targets.add(target.player_id)
                
                player.influence += 1
                if player.has_ascended and player.ascension_class in [AscensionClass.ARHAT, AscensionClass.BODHISATTVA]:
                    player.influence += 1
                if player.has_ascended and player.ascension_class == AscensionClass.BODHISATTVA:
                    player.merit += 1
        
        elif action == "farm":
            base_gain = 2
            if player.path in [Path.TEMPLE, Path.DILIGENCE]:
                base_gain += 1
            if player.has_ascended and player.ascension_class == AscensionClass.WANDERING_MONK:
                base_gain += 1
            player.wealth += base_gain
            player.farming_count += 1
        
        elif action == "build_temple":
            if player.wealth >= 8 and player.influence >= 2:
                player.wealth -= 8
                player.influence -= 2
                player.influence_spent += 2
                player.has_built_temple = True
                player.merit += 5
        
        elif action == "build_temple_land":
            if player.land >= 2:
                player.land -= 2
                player.land_donated += 2
                player.has_built_temple = True
                player.merit += 5
        
        elif action == "donate_land":
            if player.land >= 1:
                player.land -= 1
                player.land_donated += 1
                player.influence += 1
                merit_gain = 4 if (player.has_ascended and player.ascension_class == AscensionClass.TEMPLE_MASTER) else 3
                player.merit += merit_gain
    
    def run_game(self, paths: List[Path], strategies: List[AIStrategy]) -> Dict:
        game = self.create_game(paths, strategies)
        
        for round_num in range(1, 11):
            game["round"] = round_num
            
            if game["event_deck"]:
                self.process_event(game, game["event_deck"].pop())
            
            self.production_phase(game)
            
            for p in game["players"]:
                p.apply_ascension_abilities()
            
            self.action_phase(game)
            
            for p in game["players"]:
                p.update_path_completion()
            
            if round_num >= 5:
                for p in game["players"]:
                    if p.can_ascend(game["players"], round_num):
                        if AIDecisionMaker.decide_ascension(p, game["players"], round_num):
                            p.ascend(game["players"])
            
            for p in game["players"]:
                if p.check_early_victory(game["players"]):
                    game["early_victory"] = True
                    return self._finish_game(game, p)
        
        return self._finish_game(game, None)
    
    def _finish_game(self, game: Dict, early_winner: Optional[Player]) -> Dict:
        results = []
        for p in game["players"]:
            results.append({
                "path": p.path.value,
                "strategy": p.strategy.value,
                "ascended": p.has_ascended,
                "initial_rank": p.initial_rank,
                "score": round(p.get_final_score(), 1),
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        winner = early_winner.path.value if early_winner else results[0]["path"]
        
        return {
            "winner_path": winner,
            "early_victory": game["early_victory"],
            "results": results,
        }

class ComprehensiveTester:
    def __init__(self, num_players: int = 4):
        self.num_players = num_players
        self.simulator = GameSimulator(num_players)
        
        self.path_wins = defaultdict(int)
        self.path_games = defaultdict(int)
        self.ascension_count = defaultdict(int)
        self.ascension_wins = defaultdict(int)
        self.early_victory_count = 0
        self.underdog_wins = 0
        self.underdog_ascensions = 0
        self.total_games = 0
    
    def run_test(self, num_games: int):
        all_paths = list(Path)[:self.num_players]
        path_combos = list(permutations(all_paths))
        games_per_combo = max(1, num_games // len(path_combos))
        
        for paths in path_combos:
            for _ in range(games_per_combo):
                strategies = [random.choice(ALL_STRATEGIES) for _ in range(self.num_players)]
                result = self.simulator.run_game(list(paths), strategies)
                self._record(result)
    
    def _record(self, result: Dict):
        self.total_games += 1
        winner_path = result["winner_path"]
        self.path_wins[winner_path] += 1
        
        for r in result["results"]:
            self.path_games[r["path"]] += 1
            if r["ascended"]:
                self.ascension_count[r["path"]] += 1
                if r["path"] == winner_path:
                    self.ascension_wins[r["path"]] += 1
                if r["initial_rank"] > self.num_players * 0.5:
                    self.underdog_ascensions += 1
                    if r["path"] == winner_path:
                        self.underdog_wins += 1
        
        if result["early_victory"]:
            self.early_victory_count += 1
    
    def print_report(self) -> Dict:
        target_rate = 100 / self.num_players
        
        path_win_rates = {}
        for path, games in self.path_games.items():
            wins = self.path_wins.get(path, 0)
            rate = wins / games * 100 if games > 0 else 0
            path_win_rates[path] = round(rate, 2)
        
        ascension_rates = {}
        for path, games in self.path_games.items():
            asc = self.ascension_count.get(path, 0)
            rate = asc / games * 100 if games > 0 else 0
            ascension_rates[path] = round(rate, 2)
        
        deviations = [abs(rate - target_rate) for rate in path_win_rates.values()]
        balance_score = round(sum(deviations) / len(deviations), 2) if deviations else 0
        
        early_rate = round(self.early_victory_count / self.total_games * 100, 2) if self.total_games > 0 else 0
        underdog_rate = round(self.underdog_wins / self.underdog_ascensions * 100, 2) if self.underdog_ascensions > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"  TEST REPORT - {self.num_players} PLAYERS (v7.3)")
        print(f"{'='*60}")
        print(f"Total games: {self.total_games}")
        print(f"Target win rate: {target_rate:.1f}%")
        print(f"Balance score: {balance_score:.2f} (target <5)")
        
        print(f"\n  [Path Win Rates]")
        for path, rate in sorted(path_win_rates.items(), key=lambda x: -x[1]):
            dev = rate - target_rate
            status = "[OK]" if abs(dev) <= 5 else "[!]" if abs(dev) <= 10 else "[X]"
            print(f"    {path}: {rate}% ({dev:+.1f}%) {status}")
        
        print(f"\n  [Ascension Rates]")
        for path, rate in sorted(ascension_rates.items(), key=lambda x: -x[1]):
            print(f"    {path}: {rate}%")
        
        print(f"\n  [Key Metrics]")
        print(f"    Early victory rate: {early_rate}% (target: 10-20%)")
        print(f"    Underdog win rate: {underdog_rate}%")
        
        return {
            "balance_score": balance_score,
            "path_win_rates": path_win_rates,
            "early_victory_rate": early_rate,
            "ascension_rates": ascension_rates,
        }

def main():
    print("=" * 60)
    print("  Path to Salvation v7.3 - Final Balance Test")
    print("=" * 60)
    
    all_reports = {}
    
    for num_players in [4, 5, 6]:
        print(f"\nTesting {num_players}-player game...")
        
        tester = ComprehensiveTester(num_players)
        start = time.time()
        tester.run_test(10000)
        elapsed = time.time() - start
        
        print(f"Time: {elapsed:.2f}s ({tester.total_games / elapsed:.0f} games/s)")
        report = tester.print_report()
        all_reports[f"{num_players}p"] = report
    
    with open("v73_test_results.json", "w", encoding="utf-8") as f:
        json.dump(all_reports, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print("Summary:")
    for key, report in all_reports.items():
        bs = report["balance_score"]
        ev = report["early_victory_rate"]
        status = "[OK]" if bs <= 5 and 5 <= ev <= 25 else "[NEEDS WORK]"
        print(f"  {key}: balance={bs:.2f}, early_victory={ev}% {status}")
    
    return all_reports

if __name__ == "__main__":
    main()
