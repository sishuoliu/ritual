# Balance Test - ASCII version
import random
from collections import defaultdict
from enum import Enum
from dataclasses import dataclass, field

class Path(Enum):
    NIRVANA = "Nirvana"      # Fu Tian Dao
    CHARITY = "Charity"      # Bu Shi Dao
    TEMPLE = "Temple"        # Tu Di Dao
    CULTURE = "Culture"      # Wen Hua Dao
    DILIGENCE = "Diligence"  # Qin Lao Dao
    SALVATION = "Salvation"  # Du Hua Dao

@dataclass
class Player:
    player_id: int
    path: Path
    wealth: int = 6
    merit: int = 2
    influence: int = 3
    land: int = 1
    action_points: int = 2
    has_built_temple: bool = False
    total_donated: int = 0
    land_donated: int = 0
    transfer_count: int = 0
    kindness_count: int = 0
    farming_count: int = 0
    transfer_targets: set = field(default_factory=set)
    kindness_targets: set = field(default_factory=set)
    influence_spent: int = 0
    
    def get_path_bonus(self, action):
        if self.path == Path.NIRVANA and action == "practice":
            return 2.0
        elif self.path == Path.CHARITY and action == "donate":
            return 2.0
        elif self.path == Path.CULTURE and action == "kindness":
            return 2.0
        elif self.path == Path.SALVATION and action == "transfer":
            return 2.0
        return 1.0
    
    def apply_starting_bonus(self):
        bonuses = {
            Path.NIRVANA: {"influence": 5, "merit": 2},
            Path.CHARITY: {"wealth": 6},
            Path.TEMPLE: {"land": 1, "wealth": 2},
            Path.CULTURE: {"influence": 2, "wealth": 2},
            Path.DILIGENCE: {},
            Path.SALVATION: {"merit": 5, "influence": 2},
        }
        bonus = bonuses.get(self.path, {})
        self.wealth += bonus.get("wealth", 0)
        self.merit += bonus.get("merit", 0)
        self.influence += bonus.get("influence", 0)
        self.land += bonus.get("land", 0)

class Simulator:
    def __init__(self, num_players):
        self.num_players = num_players
        
    def run_game(self, paths=None):
        if paths is None:
            paths = list(Path)[:self.num_players]
        
        players = [Player(i, paths[i]) for i in range(self.num_players)]
        for p in players:
            p.apply_starting_bonus()
            if p.path == Path.DILIGENCE:
                p.action_points = 3
        
        for round_num in range(1, 9):
            for p in players:
                p.wealth += 2 + p.land
                p.influence += 1
                if p.path == Path.TEMPLE:
                    p.wealth += p.land
            
            for p in players:
                p.action_points = 3 if p.path == Path.DILIGENCE else 2
                while p.action_points > 0:
                    action = self.choose_action(p, players)
                    if action:
                        self.execute_action(p, action, players)
                    p.action_points -= 1
        
        results = []
        for p in players:
            score = p.merit * 2 + p.influence + p.wealth / 3 + p.land * 2
            if p.total_donated >= 12 and p.influence >= 3:
                score += 25
            elif p.total_donated >= 7:
                score += 12
            results.append({"path": p.path.value, "score": score})
        
        winner = max(results, key=lambda x: x["score"])
        return {"winner_path": winner["path"], "results": results}
    
    def choose_action(self, player, all_players):
        actions = []
        if player.wealth >= 3:
            actions.append("donate")
        if player.influence >= 2:
            actions.append("practice")
        if player.wealth >= 1:
            actions.append("kindness")
        if player.merit >= 2:
            actions.append("transfer")
        actions.append("farm")
        
        if player.path == Path.CHARITY and "donate" in actions:
            return "donate" if random.random() < 0.6 else random.choice(actions)
        if player.path == Path.NIRVANA and "practice" in actions:
            return "practice" if random.random() < 0.6 else random.choice(actions)
        if player.path == Path.CULTURE and "kindness" in actions:
            return "kindness" if random.random() < 0.5 else random.choice(actions)
        if player.path == Path.SALVATION and "transfer" in actions:
            return "transfer" if random.random() < 0.5 else random.choice(actions)
        
        return random.choice(actions) if actions else None
    
    def execute_action(self, player, action, all_players):
        others = [p for p in all_players if p.player_id != player.player_id]
        m = player.get_path_bonus(action)
        
        if action == "donate" and player.wealth >= 3:
            player.wealth -= 3
            player.total_donated += 3
            player.merit += int(1 * m)
        elif action == "practice" and player.influence >= 2:
            player.influence -= 2
            player.influence_spent += 2
            player.merit += int(1 * m)
        elif action == "kindness" and player.wealth >= 1 and others:
            player.wealth -= 1
            player.kindness_count += 1
            player.merit += int(1 * m)
            target = random.choice(others)
            target.merit += int(1 * m)
            player.kindness_targets.add(target.player_id)
        elif action == "transfer" and player.merit >= 2 and others:
            player.merit -= 2
            player.transfer_count += 1
            target = random.choice(others)
            target.merit += int(3 * m)
            player.transfer_targets.add(target.player_id)
            player.influence += 1
        elif action == "farm":
            base = 2
            if player.path in [Path.TEMPLE, Path.DILIGENCE]:
                base += 1
            player.wealth += base
            player.farming_count += 1

def run_test(num_players, games=5000):
    print(f"\n{'='*50}")
    print(f"Testing {num_players} players ({games} games)")
    print(f"{'='*50}")
    
    sim = Simulator(num_players)
    wins = defaultdict(int)
    total = defaultdict(int)
    scores_sum = defaultdict(float)
    
    for _ in range(games):
        result = sim.run_game()
        wins[result["winner_path"]] += 1
        for r in result["results"]:
            total[r["path"]] += 1
            scores_sum[r["path"]] += r["score"]
    
    target_rate = 100 / num_players
    rates = {}
    
    for path in list(Path)[:num_players]:
        name = path.value
        rate = round(wins[name] / total[name] * 100, 2)
        avg_score = scores_sum[name] / total[name]
        rates[name] = rate
        deviation = rate - target_rate
        status = "OK" if abs(deviation) < 8 else "IMBALANCED"
        print(f"  {name:12}: {rate:5.1f}% (dev: {deviation:+5.1f}%) avg:{avg_score:5.1f} [{status}]")
    
    balance_score = sum(abs(r - target_rate) for r in rates.values()) / len(rates)
    status = "PASS" if balance_score < 5 else "NEEDS WORK"
    print(f"\n  Balance Score: {balance_score:.2f} [{status}]")
    
    return rates, balance_score

if __name__ == "__main__":
    print("="*60)
    print("Simple Edition Balance Test")
    print("All path bonuses = 2x (double)")
    print("="*60)
    
    all_scores = []
    for num_players in [4, 5, 6]:
        _, score = run_test(num_players, games=5000)
        all_scores.append(score)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    avg_score = sum(all_scores) / len(all_scores)
    print(f"Average Balance Score: {avg_score:.2f}")
    if avg_score < 5:
        print("RESULT: Overall balance is acceptable")
    else:
        print("RESULT: Needs further adjustment")
