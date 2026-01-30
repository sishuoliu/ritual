# -*- coding: utf-8 -*-
"""
Dice Configuration Optimization
Find the best dice parameters for game balance
"""

import random
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import time
from statistics import mean, stdev

# Enums
class Path(Enum):
    NIRVANA = "Futian"
    CHARITY = "Bushi"
    TEMPLE = "Tudi"
    CULTURE = "Wenhua"
    DILIGENCE = "Qinlao"
    SALVATION = "Duhua"

class AIStrategy(Enum):
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    RANDOM = "random"
    OPPORTUNISTIC = "opportunistic"

class DiceResult(Enum):
    NORMAL = "normal"
    SMALL_FORTUNE = "small_fortune"
    GREAT_FORTUNE = "great_fortune"

# Path definitions - v6.3 adjusted for balance
# KEY INSIGHT: Temple path (Tudi) is too strong because of land bonuses
# We need to adjust startup bonuses to balance
PATH_STARTUP = {
    Path.NIRVANA: {"influence": 5, "merit": 2},
    Path.CHARITY: {"wealth": 6},
    Path.TEMPLE: {"land": 1, "wealth": 2},  # Original
    Path.CULTURE: {"influence": 2, "wealth": 2},
    Path.DILIGENCE: {},
    Path.SALVATION: {"merit": 5, "influence": 2},
}

# Adjusted startup for balance testing
PATH_STARTUP_V2 = {
    Path.NIRVANA: {"influence": 6, "merit": 2},  # +1 influence
    Path.CHARITY: {"wealth": 7},  # +1 wealth
    Path.TEMPLE: {"land": 1, "wealth": 1},  # -1 wealth (nerf)
    Path.CULTURE: {"influence": 3, "wealth": 2},  # +1 influence
    Path.DILIGENCE: {"wealth": 2},  # +2 wealth startup
    Path.SALVATION: {"merit": 5, "influence": 3},  # +1 influence
}

EVENT_CARDS = [
    (1, "fengnian", 2), (2, "xiangrui", 2), (3, "zaiyi", 2),
    (4, "yulanpen", 2), (5, "jiangjing", 2), (6, "shuilu", 2),
    (7, "shangdui", 2), (8, "keju", 2), (9, "jishi", 2),
    (10, "hanzai", 2), (11, "daoguang", 2), (12, "wenyi", 2),
    (13, "gaoseng", 2), (14, "dunwu", 2), (15, "fubao", 2),
]

def build_event_deck():
    deck = []
    for eid, name, copies in EVENT_CARDS:
        for _ in range(copies):
            deck.append((eid, name))
    random.shuffle(deck)
    return deck

@dataclass
class Player:
    player_id: int
    path: Path
    strategy: AIStrategy
    num_players: int = 4
    use_v2_startup: bool = False
    
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
    
    dice_wealth_bonus: int = 0
    dice_influence_bonus: int = 0
    
    def __post_init__(self):
        startup = PATH_STARTUP_V2 if self.use_v2_startup else PATH_STARTUP
        bonus = startup.get(self.path, {})
        self.wealth += bonus.get("wealth", 0)
        self.merit += bonus.get("merit", 0)
        self.influence += bonus.get("influence", 0)
        self.land += bonus.get("land", 0)
    
    def get_path_bonus(self, action):
        if self.path == Path.NIRVANA and action == "practice":
            return 2.0
        elif self.path == Path.CHARITY and action == "donate":
            return 1.75
        elif self.path == Path.CULTURE and action == "kindness":
            return 1.5
        elif self.path == Path.SALVATION and action == "transfer":
            return 2.0
        return 1.0
    
    def check_path_completion(self, num_players):
        multiplier = 1.2 if num_players == 3 else (0.9 if num_players >= 5 else 1.0)
        base_bonus = 25
        small_bonus = 12
        
        if self.path == Path.NIRVANA:
            if len(self.transfer_targets) >= 3 and self.influence_spent >= 4:
                return (True, "full", int(base_bonus * multiplier))
            elif len(self.transfer_targets) >= 1:
                return (True, "small", int(small_bonus * multiplier))
        elif self.path == Path.CHARITY:
            if self.total_donated >= 12 and self.influence >= 3:
                return (True, "full", int(base_bonus * multiplier))
            elif self.total_donated >= 7:
                return (True, "small", int(small_bonus * multiplier))
        elif self.path == Path.TEMPLE:
            if self.has_built_temple and self.land_donated >= 3:
                return (True, "full", int(base_bonus * multiplier))
            elif self.has_built_temple or self.land_donated >= 2:
                return (True, "small", int(small_bonus * multiplier))
        elif self.path == Path.CULTURE:
            if self.influence >= 7 and len(self.kindness_targets) >= 3:
                return (True, "full", int(base_bonus * multiplier))
            elif self.influence >= 5 or len(self.kindness_targets) >= 2:
                return (True, "small", int(small_bonus * multiplier))
        elif self.path == Path.DILIGENCE:
            if self.kindness_count >= 5 and self.farming_count >= 5:
                return (True, "full", int(base_bonus * multiplier))
            elif self.kindness_count >= 3 or self.farming_count >= 3:
                return (True, "small", int(small_bonus * multiplier))
        elif self.path == Path.SALVATION:
            all_helped = self.transfer_targets | self.kindness_targets
            if self.transfer_count >= 3 and len(all_helped) >= 2:
                return (True, "full", int(base_bonus * multiplier))
            elif self.transfer_count >= 1 or len(all_helped) >= 1:
                return (True, "small", int(small_bonus * multiplier))
        return (False, "", 0)
    
    def get_final_score(self, num_players):
        base = self.merit * 2 + self.influence + self.wealth / 3 + self.land * 2
        _, _, path_bonus = self.check_path_completion(num_players)
        return base + path_bonus

class GameSimulator:
    def __init__(self, num_players=4, use_dice=False, dice_config=None, 
                 use_v2_startup=False):
        self.num_players = num_players
        self.use_dice = use_dice
        self.dice_config = dice_config or {
            "small_fortune_wealth": 1,
            "great_fortune_wealth": 1,
            "great_fortune_influence": 1
        }
        self.use_v2_startup = use_v2_startup
        self.all_paths = list(Path)[:num_players]
        self.dice_stats = defaultdict(int)
    
    def roll_dice(self):
        roll = random.randint(1, 6)
        if roll <= 2:
            return (DiceResult.NORMAL, 0, 0)
        elif roll <= 4:
            return (DiceResult.SMALL_FORTUNE, self.dice_config["small_fortune_wealth"], 0)
        else:
            return (DiceResult.GREAT_FORTUNE, 
                    self.dice_config["great_fortune_wealth"],
                    self.dice_config["great_fortune_influence"])
    
    def create_game(self, paths=None, strategies=None):
        if paths is None:
            paths = random.sample(self.all_paths, self.num_players)
        if strategies is None:
            strategies = [random.choice(list(AIStrategy)) for _ in range(self.num_players)]
        
        players = []
        for i in range(self.num_players):
            p = Player(i, paths[i], strategies[i], self.num_players)
            # Apply v2 startup manually if needed
            if self.use_v2_startup:
                # Reset to base and reapply v2
                p.wealth = 6
                p.merit = 2
                p.influence = 3
                p.land = 1
                bonus = PATH_STARTUP_V2.get(paths[i], {})
                p.wealth += bonus.get("wealth", 0)
                p.merit += bonus.get("merit", 0)
                p.influence += bonus.get("influence", 0)
                p.land += bonus.get("land", 0)
            players.append(p)
        
        return {
            "players": players,
            "round": 1,
            "event_deck": build_event_deck(),
        }
    
    def process_event(self, game, event):
        eid, name = event
        for p in game["players"]:
            option = random.choice(["A", "B"])
            
            if eid == 1:
                if option == "A":
                    p.wealth += 3
                else:
                    p.merit += 1
                    p.influence += 1
            elif eid == 2:
                if option == "A":
                    p.merit += 2
                else:
                    p.influence += 2
            elif eid == 3:
                if option == "A":
                    p.wealth = max(0, p.wealth - 3)
                else:
                    p.merit = max(0, p.merit - 2)
            elif eid == 4:
                if option == "A" and p.wealth >= 2:
                    p.wealth -= 2
                    p.merit += 3
            elif eid == 5:
                if option == "A" and p.influence >= 1:
                    p.influence -= 1
                    p.merit += 2
                else:
                    p.merit += 1
            elif eid == 6:
                if option == "A" and p.wealth >= 3:
                    p.wealth -= 3
                    p.merit += 4
            elif eid == 7:
                if option == "A":
                    p.wealth += 3
                elif p.wealth >= 3:
                    p.wealth -= 3
                    p.merit += 2
            elif eid == 8:
                if option == "A" and p.influence >= 5:
                    p.merit += 2
                else:
                    p.influence += 1
            elif eid == 9:
                if option == "A":
                    p.wealth += 2
                else:
                    p.merit += 1
            elif eid == 10:
                if option == "A":
                    p.wealth = max(0, p.wealth - 3)
                else:
                    p.merit = max(0, p.merit - 1)
                    p.influence = max(0, p.influence - 1)
            elif eid == 11:
                if option == "A":
                    p.wealth = max(0, p.wealth - 4)
                else:
                    p.influence = max(0, p.influence - 2)
            elif eid == 12:
                if option == "A":
                    p.merit = max(0, p.merit - 2)
                else:
                    p.influence = max(0, p.influence - 2)
            elif eid == 13:
                if option == "A":
                    p.merit += 3
                else:
                    p.merit += 2
                    p.influence += 1
            elif eid == 14:
                if option == "A":
                    p.merit += 2
                    p.influence += 1
                else:
                    p.influence += 3
            elif eid == 15:
                if option == "A":
                    p.wealth += 2
                    p.merit += 1
                else:
                    p.merit += 1
                    p.influence += 2
    
    def production_phase(self, game):
        for p in game["players"]:
            p.wealth += 2
            p.influence += 1
            
            land_bonus = 1 if p.path in [Path.TEMPLE, Path.DILIGENCE] else 0
            p.wealth += p.land * (1 + land_bonus)
            
            if self.use_dice:
                result, extra_w, extra_i = self.roll_dice()
                p.dice_wealth_bonus += extra_w
                p.dice_influence_bonus += extra_i
                p.wealth += extra_w
                p.influence += extra_i
                self.dice_stats[result.value] += 1
    
    def get_available_actions(self, player, others):
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
    
    def decide_action(self, player, game, others):
        actions = self.get_available_actions(player, others)
        
        if player.strategy == AIStrategy.RANDOM:
            return random.choice(actions)
        
        elif player.strategy == AIStrategy.AGGRESSIVE:
            if "build_temple_land" in actions:
                return "build_temple_land"
            if "build_temple" in actions:
                return "build_temple"
            if player.wealth >= 6 and "donate" in actions:
                return "donate"
            if "transfer" in actions:
                return "transfer"
            if "practice" in actions:
                return "practice"
            if "donate" in actions:
                return "donate"
            if "kindness" in actions:
                return "kindness"
            return "farm"
        
        elif player.strategy == AIStrategy.CONSERVATIVE:
            if player.wealth < 5:
                return "farm"
            if "kindness" in actions:
                return "kindness"
            if player.wealth >= 6 and "donate" in actions:
                return "donate"
            if player.influence >= 3 and "practice" in actions:
                return "practice"
            return "farm"
        
        elif player.strategy == AIStrategy.BALANCED:
            path = player.path
            if path == Path.NIRVANA:
                if "transfer" in actions and len(player.transfer_targets) < 3:
                    return "transfer"
                if "practice" in actions:
                    return "practice"
            elif path == Path.CHARITY:
                if "donate" in actions:
                    return "donate"
                return "farm"
            elif path == Path.TEMPLE:
                if "build_temple_land" in actions:
                    return "build_temple_land"
                if "donate_land" in actions and player.land_donated < 2:
                    return "donate_land"
                return "farm"
            elif path == Path.CULTURE:
                if "kindness" in actions and len(player.kindness_targets) < 3:
                    return "kindness"
                if "practice" in actions:
                    return "practice"
            elif path == Path.DILIGENCE:
                if player.kindness_count < 4 and "kindness" in actions:
                    return "kindness"
                if player.farming_count < 4:
                    return "farm"
            elif path == Path.SALVATION:
                if "transfer" in actions:
                    return "transfer"
                if "kindness" in actions:
                    return "kindness"
            return random.choice(actions)
        
        else:  # OPPORTUNISTIC
            round_num = game["round"]
            if round_num <= 3:
                if player.wealth < 8:
                    return "farm"
                if "donate" in actions:
                    return "donate"
            else:
                if "build_temple_land" in actions:
                    return "build_temple_land"
                if "donate" in actions:
                    return "donate"
                if "transfer" in actions:
                    return "transfer"
            return random.choice(actions)
    
    def execute_action(self, player, action, game, others):
        multiplier = player.get_path_bonus(action)
        
        if action == "donate":
            if player.wealth >= 3:
                player.wealth -= 3
                player.total_donated += 3
                player.merit += int(1 * multiplier)
        
        elif action == "practice":
            if player.influence >= 2:
                player.influence -= 2
                player.influence_spent += 2
                player.merit += int(1 * multiplier)
        
        elif action == "kindness":
            if player.wealth >= 1 and others:
                player.wealth -= 1
                player.kindness_count += 1
                player.merit += int(1 * multiplier)
                target = random.choice(others)
                target.merit += 1
                player.kindness_targets.add(target.player_id)
        
        elif action == "transfer":
            if player.merit >= 2 and others:
                player.merit -= 2
                player.transfer_count += 1
                player.influence += 1
                target = random.choice(others)
                target.merit += int(3 * multiplier)
                player.transfer_targets.add(target.player_id)
        
        elif action == "farm":
            base = 2
            if player.path in [Path.TEMPLE, Path.DILIGENCE]:
                base += 1
            player.wealth += base
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
                player.merit += 3
    
    def action_phase(self, game):
        players = game["players"]
        for p in players:
            p.action_points = 3 if p.path == Path.DILIGENCE else p.base_action_points
            others = [o for o in players if o.player_id != p.player_id]
            
            while p.action_points > 0:
                action = self.decide_action(p, game, others)
                if action is None:
                    break
                self.execute_action(p, action, game, others)
                p.action_points -= 1
    
    def run_game(self, paths=None, strategies=None):
        game = self.create_game(paths, strategies)
        
        for round_num in range(1, 9):
            game["round"] = round_num
            
            if game["event_deck"]:
                event = game["event_deck"].pop()
                self.process_event(game, event)
            
            self.production_phase(game)
            self.action_phase(game)
        
        results = []
        for p in game["players"]:
            score = p.get_final_score(self.num_players)
            results.append({
                "path": p.path.value,
                "score": round(score, 1),
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return {"winner_path": results[0]["path"], "results": results}


def run_test(num_players, games, use_dice, dice_config=None, use_v2_startup=False):
    sim = GameSimulator(num_players, use_dice, dice_config, use_v2_startup)
    
    path_wins = defaultdict(int)
    path_total = defaultdict(int)
    path_scores = defaultdict(list)
    
    for _ in range(games):
        result = sim.run_game()
        path_wins[result["winner_path"]] += 1
        for r in result["results"]:
            path_total[r["path"]] += 1
            path_scores[r["path"]].append(r["score"])
    
    win_rates = {}
    score_stats = {}
    for path in list(Path)[:num_players]:
        name = path.value
        if name in path_wins:
            win_rates[name] = round(path_wins[name] / path_total[name] * 100, 2)
            scores = path_scores[name]
            score_stats[name] = {
                "avg": round(mean(scores), 2),
                "std": round(stdev(scores), 2) if len(scores) > 1 else 0
            }
    
    return {"win_rates": win_rates, "score_stats": score_stats}


def calculate_balance_score(win_rates, target_rate):
    """Lower is better. 0 means perfect balance."""
    total_deviation = 0
    for path, rate in win_rates.items():
        deviation = abs(rate - target_rate)
        total_deviation += deviation
    return round(total_deviation, 2)


def main():
    print("=" * 70)
    print("Dice Configuration Optimization")
    print("=" * 70)
    
    # Test configurations
    dice_configs = [
        ("v1_baseline", {"small_fortune_wealth": 1, "great_fortune_wealth": 1, "great_fortune_influence": 1}),
        ("v2_no_influence", {"small_fortune_wealth": 1, "great_fortune_wealth": 1, "great_fortune_influence": 0}),
        ("v3_more_wealth", {"small_fortune_wealth": 2, "great_fortune_wealth": 2, "great_fortune_influence": 1}),
        ("v4_small_only", {"small_fortune_wealth": 1, "great_fortune_wealth": 0, "great_fortune_influence": 0}),
        ("v5_half_influence", {"small_fortune_wealth": 1, "great_fortune_wealth": 1, "great_fortune_influence": 0}),
    ]
    
    all_results = {}
    
    for num_players in [4, 6]:
        print(f"\n{'='*60}")
        print(f"Testing {num_players} Players")
        print(f"{'='*60}")
        
        target_rate = 100 / num_players
        player_results = {}
        
        # Baseline: no dice, original startup
        print("\n  [Baseline] No dice, original startup:")
        baseline = run_test(num_players, 8000, use_dice=False, use_v2_startup=False)
        baseline_score = calculate_balance_score(baseline["win_rates"], target_rate)
        print(f"    Balance score: {baseline_score}")
        for path, rate in baseline["win_rates"].items():
            status = "OK" if abs(rate - target_rate) < 8 else "BIAS"
            print(f"      {path}: {rate}% [{status}]")
        player_results["baseline"] = {"win_rates": baseline["win_rates"], "balance_score": baseline_score}
        
        # Test each dice config
        for config_name, dice_config in dice_configs:
            print(f"\n  [{config_name}] With dice:")
            result = run_test(num_players, 8000, use_dice=True, dice_config=dice_config, use_v2_startup=False)
            balance_score = calculate_balance_score(result["win_rates"], target_rate)
            improvement = baseline_score - balance_score
            print(f"    Balance score: {balance_score} (improvement: {improvement:+.1f})")
            for path, rate in result["win_rates"].items():
                status = "OK" if abs(rate - target_rate) < 8 else "BIAS"
                print(f"      {path}: {rate}% [{status}]")
            player_results[config_name] = {"win_rates": result["win_rates"], "balance_score": balance_score}
        
        # Test with v2 startup (adjusted for balance)
        print(f"\n  [v2_startup_with_dice] Adjusted startup + dice v1:")
        v2_result = run_test(num_players, 8000, use_dice=True, 
                            dice_config=dice_configs[0][1], use_v2_startup=True)
        v2_score = calculate_balance_score(v2_result["win_rates"], target_rate)
        improvement = baseline_score - v2_score
        print(f"    Balance score: {v2_score} (improvement: {improvement:+.1f})")
        for path, rate in v2_result["win_rates"].items():
            status = "OK" if abs(rate - target_rate) < 8 else "BIAS"
            print(f"      {path}: {rate}% [{status}]")
        player_results["v2_startup_with_dice"] = {"win_rates": v2_result["win_rates"], "balance_score": v2_score}
        
        all_results[f"{num_players}p"] = player_results
        
        # Find best config
        best_config = min(player_results.items(), key=lambda x: x[1]["balance_score"])
        print(f"\n  BEST CONFIG for {num_players}p: {best_config[0]} (score: {best_config[1]['balance_score']})")
    
    # Save results
    with open("dice_optimization_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print("\n" + "=" * 70)
    print("Results saved to dice_optimization_results.json")
    print("=" * 70)
    
    return all_results


if __name__ == "__main__":
    main()
