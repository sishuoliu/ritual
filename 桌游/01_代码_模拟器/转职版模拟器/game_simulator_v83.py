# -*- coding: utf-8 -*-
"""
救赎之路 v8.3 - 最终平衡
v8.2结果：4p=3.74[OK], 5p=6.80, 6p=5.15
调整：
- 5人：布施道太强(29.94%)→削弱，福田道太弱(8.6%)→增强
- 6人：勤劳道太强(23.38%)→削弱，福田道太弱(6.13%)→增强
"""

import random, json, time
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
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

class VictoryType(Enum):
    SCORE = "得分胜利"
    EARLY = "提前胜利"

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
    mid_game_rank: int = 0
    
    def __post_init__(self):
        np = self.num_players
        
        if self.path == Path.NIRVANA:
            # 福田道：5-6人需要更多增强
            if np == 4:
                self.influence += 7
                self.merit += 4
            elif np == 5:
                self.influence += 7  # 从5增加到7
                self.merit += 4      # 从2增加到4
            else:
                self.influence += 7  # 从4增加到7
                self.merit += 4      # 从2增加到4
                
        elif self.path == Path.CHARITY:
            # 布施道：5-6人需削弱
            if np == 4:
                self.wealth += 5
            elif np == 5:
                self.wealth += 2      # 从3降到2
            else:
                self.wealth += 1      # 从2降到1
                
        elif self.path == Path.TEMPLE:
            if np == 4:
                self.land += 2
                self.wealth += 3
            elif np == 5:
                self.land += 1
                self.wealth += 2
            else:
                self.land += 1
                self.wealth += 1
                
        elif self.path == Path.CULTURE:
            self.influence += 2
            self.wealth += 2
            
        elif self.path == Path.DILIGENCE:
            self.base_action_points = 3
            self.action_points = 3
            if np == 5:
                self.wealth += 1
            # 6人不额外加资源
                
        elif self.path == Path.SALVATION:
            if np == 4:
                self.merit += 3
                self.influence += 1
            elif np == 5:
                self.merit += 2
            else:
                self.merit += 1
    
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
        if path_complete: base_score += path_bonus
        return base_score
    
    def get_rank(self, players: List['Player']) -> int:
        scores = [(p.get_current_score(), p.player_id) for p in players]
        scores.sort(reverse=True)
        for idx, (score, pid) in enumerate(scores):
            if pid == self.player_id: return idx + 1
        return len(players)
    
    def get_ascension_cost(self, players: List['Player']) -> Tuple[int, int, int]:
        base_merit = 5
        rank = self.get_rank(players)
        total_players = len(players)
        if rank <= total_players * 0.25: merit_cost = base_merit + 2
        elif rank > total_players * 0.5: merit_cost = base_merit - 2
        else: merit_cost = base_merit
        return (max(1, merit_cost), 3, 3)
    
    def can_ascend(self, players: List['Player'], round_num: int) -> bool:
        if self.has_ascended or not self.small_path_completed or round_num < 5: return False
        merit_cost, inf_cost, wealth_cost = self.get_ascension_cost(players)
        return self.merit >= merit_cost and self.influence >= inf_cost and self.wealth >= wealth_cost
    
    def ascend(self, players: List['Player']):
        merit_cost, inf_cost, wealth_cost = self.get_ascension_cost(players)
        self.initial_rank = self.get_rank(players)
        self.merit -= merit_cost; self.influence -= inf_cost; self.wealth -= wealth_cost
        self.has_ascended = True
        path_to_class = {Path.NIRVANA: AscensionClass.ARHAT, Path.CHARITY: AscensionClass.MAHADANAPATI, Path.TEMPLE: AscensionClass.TEMPLE_MASTER, Path.CULTURE: AscensionClass.MANJUSRI, Path.DILIGENCE: AscensionClass.WANDERING_MONK, Path.SALVATION: AscensionClass.BODHISATTVA}
        self.ascension_class = path_to_class[self.path]
    
    def check_early_victory(self, players: List['Player']) -> bool:
        if not self.has_ascended: return False
        np = len(players)
        
        if self.ascension_class == AscensionClass.ARHAT:
            return len(self.transfer_targets) >= np - 1 and self.merit >= 18 and self.influence_spent >= 8
        elif self.ascension_class == AscensionClass.MAHADANAPATI:
            donated_req = 35 + (np - 4) * 8  # 增加人数惩罚
            return self.total_donated >= donated_req and self.wealth <= 3 and self.merit >= 10
        elif self.ascension_class == AscensionClass.TEMPLE_MASTER:
            return self.has_built_temple and self.land_donated >= 5 and self.land <= 0 and self.merit >= 12
        elif self.ascension_class == AscensionClass.MANJUSRI:
            return len(self.kindness_targets) >= np - 1 and self.influence >= 12 and self.kindness_count >= 8
        elif self.ascension_class == AscensionClass.WANDERING_MONK:
            return self.kindness_count >= 18 and self.farming_count >= 18 and self.merit >= 12
        elif self.ascension_class == AscensionClass.BODHISATTVA:
            all_helped = self.transfer_targets | self.kindness_targets
            merit_req = 12 + (np - 4) * 2
            return len(all_helped) >= np - 1 and self.merit >= merit_req and self.transfer_count >= 5
        return False
    
    def get_ascension_bonus_multiplier(self, action: str) -> float:
        if not self.has_ascended: return 1.0
        bonuses = {(AscensionClass.ARHAT, "practice"): 0.5, (AscensionClass.ARHAT, "transfer"): 1.3, (AscensionClass.MAHADANAPATI, "donate"): 1.4, (AscensionClass.TEMPLE_MASTER, "donate_land"): 1.5, (AscensionClass.TEMPLE_MASTER, "farm"): 1.3, (AscensionClass.MANJUSRI, "kindness"): 1.5, (AscensionClass.WANDERING_MONK, "farm"): 1.2, (AscensionClass.WANDERING_MONK, "kindness"): 1.2, (AscensionClass.BODHISATTVA, "transfer"): 1.5}
        return bonuses.get((self.ascension_class, action), 1.0)
    
    def check_path_completion(self) -> Tuple[bool, str, int]:
        multiplier = 1.2 if self.num_players == 3 else (0.9 if self.num_players >= 5 else 1.0)
        base_bonus = 28; small_bonus = 14
        conditions = {Path.NIRVANA: (len(self.transfer_targets) >= 3 and self.influence_spent >= 4, len(self.transfer_targets) >= 1, "福田道"), Path.CHARITY: (self.total_donated >= 12 and self.influence >= 3, self.total_donated >= 7, "布施道"), Path.TEMPLE: (self.has_built_temple and self.land_donated >= 3, self.has_built_temple or self.land_donated >= 2, "土地道"), Path.CULTURE: (self.influence >= 7 and len(self.kindness_targets) >= 3, self.influence >= 5 or len(self.kindness_targets) >= 2, "文化道"), Path.DILIGENCE: (self.kindness_count >= 5 and self.farming_count >= 5, self.kindness_count >= 3 or self.farming_count >= 3, "勤劳道"), Path.SALVATION: (self.transfer_count >= 3 and len(self.transfer_targets | self.kindness_targets) >= 2, self.transfer_count >= 1 or len(self.kindness_targets) >= 1, "渡化道")}
        full_cond, small_cond, name = conditions[self.path]
        if full_cond: return (True, name, int(base_bonus * multiplier))
        elif small_cond: self.small_path_completed = True; return (True, f"{name}（小成）", int(small_bonus * multiplier))
        return (False, "", 0)
    
    def get_final_score(self) -> float:
        base_score = self.merit * 2 + self.influence + self.wealth / 3 + self.land * 2
        path_complete, _, path_bonus = self.check_path_completion()
        if self.has_ascended: base_score += 5
        return base_score + path_bonus
    
    def apply_ascension_abilities(self):
        if not self.has_ascended: return
        if self.ascension_class == AscensionClass.ARHAT: self.merit += 1
        elif self.ascension_class == AscensionClass.MAHADANAPATI: self.wealth += 2
        elif self.ascension_class == AscensionClass.TEMPLE_MASTER:
            if self.has_built_temple: self.merit += 1; self.wealth += 1
        elif self.ascension_class == AscensionClass.MANJUSRI:
            if self.influence >= 8: self.merit += 1
        elif self.ascension_class == AscensionClass.WANDERING_MONK: self.merit += 1

class AIDecisionMaker:
    @staticmethod
    def decide_action(player: Player, game: Dict, others: List[Player]) -> Optional[str]:
        strategy = player.strategy
        if strategy == AIStrategy.RANDOM: return AIDecisionMaker._random_action(player, others)
        elif strategy == AIStrategy.AGGRESSIVE: return AIDecisionMaker._aggressive_action(player, others, game)
        elif strategy == AIStrategy.CONSERVATIVE: return AIDecisionMaker._conservative_action(player, others)
        elif strategy == AIStrategy.BALANCED: return AIDecisionMaker._balanced_action(player, others, game)
        elif strategy == AIStrategy.OPPORTUNISTIC: return AIDecisionMaker._opportunistic_action(player, game, others)
        return None
    
    @staticmethod
    def _get_available_actions(player: Player, others: List[Player]) -> List[str]:
        actions = ["farm"]
        if player.wealth >= 3: actions.append("donate")
        if player.influence >= 2: actions.append("practice")
        if player.wealth >= 1 and others: actions.append("kindness")
        if player.merit >= 2 and others: actions.append("transfer")
        if not player.has_built_temple:
            if player.wealth >= 8 and player.influence >= 2: actions.append("build_temple")
            elif player.land >= 2: actions.append("build_temple_land")
        if player.land >= 1: actions.append("donate_land")
        return actions
    
    @staticmethod
    def _random_action(player: Player, others: List[Player]) -> Optional[str]:
        actions = AIDecisionMaker._get_available_actions(player, others)
        return random.choice(actions) if actions else None
    
    @staticmethod
    def _aggressive_action(player: Player, others: List[Player], game: Dict) -> Optional[str]:
        if not player.has_built_temple:
            if player.land >= 2: return "build_temple_land"
            if player.wealth >= 8 and player.influence >= 2: return "build_temple"
        if player.wealth >= 6: return "donate"
        if player.merit >= 2 and others: return "transfer"
        if player.influence >= 2: return "practice"
        if player.wealth >= 3: return "donate"
        return "farm"
    
    @staticmethod
    def _conservative_action(player: Player, others: List[Player]) -> Optional[str]:
        if player.wealth < 5: return "farm"
        if player.wealth >= 1 and others: return "kindness"
        if player.wealth >= 6: return "donate"
        if player.influence >= 3: return "practice"
        return "farm"
    
    @staticmethod
    def _balanced_action(player: Player, others: List[Player], game: Dict) -> Optional[str]:
        path = player.path
        if path == Path.NIRVANA:
            if player.merit >= 2 and others and len(player.transfer_targets) < 3: return "transfer"
            if player.influence >= 2: return "practice"
        elif path == Path.CHARITY:
            if player.wealth >= 3: return "donate"
            return "farm"
        elif path == Path.TEMPLE:
            if not player.has_built_temple and player.land >= 2: return "build_temple_land"
            if player.land >= 1 and player.land_donated < 3: return "donate_land"
            return "farm"
        elif path == Path.CULTURE:
            if player.wealth >= 1 and others and len(player.kindness_targets) < 3: return "kindness"
            if player.influence >= 2: return "practice"
        elif path == Path.DILIGENCE:
            if player.kindness_count < 5 and player.wealth >= 1 and others: return "kindness"
            if player.farming_count < 5: return "farm"
        elif path == Path.SALVATION:
            if player.merit >= 2 and others: return "transfer"
            if player.wealth >= 1 and others: return "kindness"
        return AIDecisionMaker._random_action(player, others)
    
    @staticmethod
    def _opportunistic_action(player: Player, game: Dict, others: List[Player]) -> Optional[str]:
        round_num = game["round"]
        if round_num <= 3:
            if player.wealth < 8: return "farm"
        elif round_num <= 6: return AIDecisionMaker._balanced_action(player, others, game)
        else:
            if not player.has_built_temple and player.land >= 2: return "build_temple_land"
            if player.wealth >= 3: return "donate"
        return AIDecisionMaker._balanced_action(player, others, game)
    
    @staticmethod
    def decide_ascension(player: Player, players: List[Player], round_num: int) -> bool:
        if not player.can_ascend(players, round_num): return False
        strategy = player.strategy
        rank = player.get_rank(players)
        total_players = len(players)
        if rank > total_players * 0.5: return random.random() < 0.75
        if strategy == AIStrategy.AGGRESSIVE: return random.random() < 0.55
        elif strategy == AIStrategy.CONSERVATIVE: return random.random() < 0.25
        elif strategy == AIStrategy.BALANCED: return random.random() < 0.45
        elif strategy == AIStrategy.OPPORTUNISTIC: return round_num >= 7
        return random.random() < 0.45

class GameSimulator:
    def __init__(self, np: int = 4): self.num_players = np
    def create_game(self, paths, strategies): return {"players": [Player(i, paths[i], strategies[i], self.num_players) for i in range(self.num_players)], "round": 1, "event_deck": build_event_deck(), "early_victory": False}
    def process_event(self, game, event):
        for p in game["players"]:
            option = random.choice(["A", "B"])
            if event.id in [1, 7, 9]: p.wealth += 3 if option == "A" else 0; p.merit += 0 if option == "A" else 1; p.influence += 0 if option == "A" else 1
            elif event.id in [2, 13, 14]: p.merit += 2 if option == "A" else 0; p.influence += 0 if option == "A" else 2
            elif event.id in [3, 10, 11, 12]: p.wealth = max(0, p.wealth - 3) if option == "A" else p.wealth; p.merit = max(0, p.merit - 1) if option == "B" else p.merit
            elif event.id in [4, 5, 6] and option == "A" and p.wealth >= 2: p.wealth -= 2; p.merit += 3
            else: p.influence += 1
    def production_phase(self, game):
        for p in game["players"]:
            p.wealth += 2; p.influence += 1
            land_bonus = 1 if p.path in [Path.TEMPLE, Path.DILIGENCE] else 0
            p.wealth += p.land * (1 + land_bonus)
            if p.has_ascended and p.ascension_class == AscensionClass.TEMPLE_MASTER: p.wealth += p.land
    def action_phase(self, game):
        for p in game["players"]:
            p.action_points = p.base_action_points
            if p.has_ascended and p.ascension_class == AscensionClass.WANDERING_MONK: p.action_points += 1
            others = [o for o in game["players"] if o.player_id != p.player_id]
            while p.action_points > 0:
                action = AIDecisionMaker.decide_action(p, game, others)
                if action is None: break
                self.execute_action(p, action, game, others); p.action_points -= 1
    def execute_action(self, p, action, game, others):
        m = p.get_ascension_bonus_multiplier(action)
        if action == "donate" and p.wealth >= 3: p.wealth -= 3; p.total_donated += 3; p.merit += int(1 * m); (random.choice(others).merit if p.has_ascended and p.ascension_class == AscensionClass.MAHADANAPATI and others else None)
        elif action == "practice":
            cost = 1 if p.has_ascended and p.ascension_class == AscensionClass.ARHAT else 2
            if p.influence >= cost: p.influence -= cost; p.influence_spent += cost; p.merit += 1
        elif action == "kindness" and p.wealth >= 1 and others:
            p.wealth -= 1; p.kindness_count += 1; p.merit += int(1 * m)
            t = random.choice(others); t.merit += 1; p.kindness_targets.add(t.player_id)
            if p.has_ascended and p.ascension_class == AscensionClass.MANJUSRI: p.influence += 1
            if p.has_ascended and p.ascension_class == AscensionClass.WANDERING_MONK: p.wealth += 1
        elif action == "transfer" and p.merit >= 2 and others:
            p.merit -= 2; p.transfer_count += 1
            t = random.choice(others); t.merit += int(3 * m); p.transfer_targets.add(t.player_id); p.influence += 1
            if p.has_ascended and p.ascension_class in [AscensionClass.ARHAT, AscensionClass.BODHISATTVA]: p.influence += 1
            if p.has_ascended and p.ascension_class == AscensionClass.BODHISATTVA: p.merit += 1
        elif action == "farm":
            base = 2 + (1 if p.path in [Path.TEMPLE, Path.DILIGENCE] else 0)
            if p.has_ascended and p.ascension_class == AscensionClass.WANDERING_MONK: base += 1
            if p.has_ascended and p.ascension_class == AscensionClass.TEMPLE_MASTER: base += 1
            p.wealth += int(base * m); p.farming_count += 1
        elif action == "build_temple" and p.wealth >= 8 and p.influence >= 2: p.wealth -= 8; p.influence -= 2; p.influence_spent += 2; p.has_built_temple = True; p.merit += 5
        elif action == "build_temple_land" and p.land >= 2: p.land -= 2; p.land_donated += 2; p.has_built_temple = True; p.merit += 5
        elif action == "donate_land" and p.land >= 1: p.land -= 1; p.land_donated += 1; p.influence += 1; p.merit += (4 if p.has_ascended and p.ascension_class == AscensionClass.TEMPLE_MASTER else 3)
    def run_game(self, paths, strategies):
        game = self.create_game(paths, strategies)
        for r in range(1, 11):
            game["round"] = r
            if r == 5: [setattr(p, 'mid_game_rank', p.get_rank(game["players"])) for p in game["players"]]
            if game["event_deck"]: self.process_event(game, game["event_deck"].pop())
            self.production_phase(game)
            [p.apply_ascension_abilities() for p in game["players"]]
            self.action_phase(game)
            [p.update_path_completion() for p in game["players"]]
            if r >= 5:
                for p in game["players"]:
                    if p.can_ascend(game["players"], r) and AIDecisionMaker.decide_ascension(p, game["players"], r): p.ascend(game["players"])
            for p in game["players"]:
                if p.check_early_victory(game["players"]): game["early_victory"] = True; return self._finish(game, p, VictoryType.EARLY)
        return self._finish(game, None, VictoryType.SCORE)
    def _finish(self, game, ew, vt):
        results = sorted([{"path": p.path.value, "ascended": p.has_ascended, "mid_game_rank": p.mid_game_rank, "score": round(p.get_final_score(), 1)} for p in game["players"]], key=lambda x: -x["score"])
        return {"winner_path": ew.path.value if ew else results[0]["path"], "victory_type": vt.value, "early_victory": game["early_victory"], "results": results}

class Tester:
    def __init__(self, np): self.num_players = np; self.simulator = GameSimulator(np); self.path_wins = defaultdict(int); self.path_games = defaultdict(int); self.path_early_wins = defaultdict(int); self.total_games = 0
    def run_test(self, n):
        all_paths = list(Path)[:self.num_players]; combos = list(permutations(all_paths)); per = max(1, n // len(combos))
        for paths in combos:
            for _ in range(per):
                r = self.simulator.run_game(list(paths), [random.choice(ALL_STRATEGIES) for _ in range(self.num_players)])
                self.total_games += 1; self.path_wins[r["winner_path"]] += 1
                if r["victory_type"] == VictoryType.EARLY.value: self.path_early_wins[r["winner_path"]] += 1
                for x in r["results"]: self.path_games[x["path"]] += 1
    def report(self):
        target = 100 / self.num_players; rates = {p: round(self.path_wins.get(p, 0) / self.path_games.get(p, 1) * 100, 2) for p in self.path_games}
        devs = [abs(r - target) for r in rates.values()]; bs = round(sum(devs) / len(devs), 2) if devs else 0
        total_early = sum(self.path_early_wins.values()); er = total_early / self.total_games * 100 if self.total_games > 0 else 0
        print(f"\n{self.num_players}P: balance={bs:.2f}, early={er:.1f}%")
        for p, r in sorted(rates.items(), key=lambda x: -x[1]):
            d = r - target; e = self.path_early_wins.get(p, 0); t = self.path_wins.get(p, 0); er2 = e / t * 100 if t > 0 else 0
            s = "[OK]" if abs(d) <= 5 else "[!]" if abs(d) <= 10 else "[X]"
            print(f"  {p}: {r}% ({d:+.1f}%) e:{er2:.0f}% {s}")
        return {"balance_score": bs, "path_win_rates": rates, "early_victory_rate": er}

def main():
    print("v8.3 - Final Balance")
    all_reports = {}
    for np in [4, 5, 6]:
        t = Tester(np); start = time.time(); t.run_test(10000); print(f"({time.time()-start:.1f}s)"); all_reports[f"{np}p"] = t.report()
    with open("v83_results.json", "w", encoding="utf-8") as f: json.dump(all_reports, f, ensure_ascii=False, indent=2)
    print("\nFINAL:"); all_ok = True
    for k, r in all_reports.items():
        bs = r["balance_score"]; s = "[OK]" if bs <= 5 else "[X]"
        if bs > 5: all_ok = False
        print(f"  {k}: {bs:.2f} {s}")
    if all_ok: print("\nALL BALANCED!")
    return all_reports

if __name__ == "__main__": main()
