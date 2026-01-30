# -*- coding: utf-8 -*-
"""
《救赎之路》v2.8 最终平衡版
六道系统 - 基于v2.7数据的精确调整

v2.7问题：
- 地主54%（过高）、寡妇23%/农民18%（良好）
- 僧侣0%、富商0.06%（过低）、官员4.5%（偏低）

v2.8调整：
1. 地主：舍宅道从60降到42，小成从32降到22
2. 僧侣：涅槃道从35提高到52
3. 富商：善财道从45提高到55，小成从22提高到32
4. 官员：清官道从45提高到52，小成从28提高到35
5. 农民：勤劳道从55降到48（略微调低）
6. 寡妇：菩萨道从40降到38（略微调低）
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Set
from enum import Enum
import json
import time

class Role(Enum):
    MERCHANT = "富商"
    LANDLORD = "地主"
    OFFICIAL = "官员"
    FARMER = "农民"
    WIDOW = "寡妇"
    MONK = "僧侣"

@dataclass
class Player:
    role: Role
    grain: int = 0
    coins: int = 0
    land: int = 0
    merit: int = 0
    reputation: int = 0
    dharma_power: int = 0
    grant_points: int = 0
    life: int = 10
    action_points: int = 2
    awakening_tokens: int = 0
    retreat_mode: bool = False
    
    bodhisattva_mode: bool = False
    liberation_turn: int = 0
    salvation_points: int = 0
    beings_saved: int = 0
    saved_players: Set = field(default_factory=set)
    
    charity_mode: bool = False
    total_donated: int = 0
    
    temple_built: bool = False
    land_donated: int = 0
    legacy_points: int = 0
    
    retired: bool = False
    petitions: int = 0
    court_visits: int = 0
    
    labor_points: int = 0
    daily_good_deeds: int = 0
    harvest_shared: int = 0
    
    def __post_init__(self):
        if self.role == Role.MERCHANT:
            self.grain, self.coins, self.land = 2, 10, 0
        elif self.role == Role.LANDLORD:
            self.grain, self.coins, self.land = 3, 2, 3
        elif self.role == Role.OFFICIAL:
            self.grain, self.coins, self.land = 2, 4, 1
            self.reputation = 0
        elif self.role == Role.FARMER:
            self.grain, self.coins, self.land = 5, 2, 0
            self.action_points = 3
        elif self.role == Role.WIDOW:
            self.grain, self.coins, self.land, self.merit = 2, 3, 0, 4
        elif self.role == Role.MONK:
            self.dharma_power = 8
    
    def get_total_resources(self) -> int:
        return self.grain + self.coins + self.land * 5
    
    def check_path_completion(self) -> tuple:
        if self.role == Role.WIDOW:
            if self.bodhisattva_mode and self.beings_saved >= 4:
                return (True, "菩萨道", 38)
            elif self.bodhisattva_mode and self.beings_saved >= 2:
                return (True, "菩萨道（小成）", 22)
            return (False, "", 0)
            
        elif self.role == Role.MONK:
            # v2.8: 涅槃道大幅提高
            if self.dharma_power <= 3 and self.grant_points >= 12:
                return (True, "涅槃道", 52)
            return (False, "", 0)
            
        elif self.role == Role.MERCHANT:
            # v2.8: 善财道大幅提高
            if self.total_donated >= 15 and self.coins <= 5:
                return (True, "善财道", 55)
            elif self.total_donated >= 10:
                return (True, "善财道（小成）", 32)
            return (False, "", 0)
            
        elif self.role == Role.LANDLORD:
            # v2.8: 舍宅道大幅降低
            if self.land_donated >= 3 and self.temple_built:
                return (True, "舍宅道", 42)
            elif self.land_donated >= 2 or self.temple_built:
                return (True, "舍宅道（小成）", 22)
            return (False, "", 0)
            
        elif self.role == Role.OFFICIAL:
            # v2.8: 清官道提高
            if self.retired and self.petitions >= 5:
                return (True, "清官道", 52)
            elif self.retired or self.petitions >= 4:
                return (True, "清官道（小成）", 35)
            return (False, "", 0)
            
        elif self.role == Role.FARMER:
            # v2.8: 勤劳道略微降低
            if self.daily_good_deeds >= 5 and self.harvest_shared >= 3:
                return (True, "勤劳道", 48)
            elif self.daily_good_deeds >= 3 or self.harvest_shared >= 2:
                return (True, "勤劳道（小成）", 26)
            return (False, "", 0)
        
        return (False, "", 0)
    
    def get_final_score(self) -> float:
        if self.role == Role.MONK:
            base_score = self.grant_points * 3 + self.merit  # v2.8: 授德点×3
        else:
            resource_bonus = self.get_total_resources() // 4
            base_score = self.merit * 2 + self.reputation + resource_bonus
        
        path_complete, path_name, path_bonus = self.check_path_completion()
        if path_complete:
            base_score += path_bonus
        
        if self.role == Role.FARMER:
            base_score += self.labor_points * 2
        elif self.role == Role.WIDOW and self.bodhisattva_mode:
            base_score += self.salvation_points * 2 + self.beings_saved * 6
        elif self.role == Role.MERCHANT:
            base_score += int(self.total_donated * 1.2)  # v2.8: 从×1提高到×1.2
        elif self.role == Role.LANDLORD:
            base_score += self.legacy_points * 2 + self.land_donated * 5  # v2.8: 降低加分
        elif self.role == Role.OFFICIAL:
            base_score += self.petitions * 5  # v2.8: 从4提高到5
        
        return base_score

class GameSimulator:
    def __init__(self):
        pass
        
    def create_game(self):
        roles = list(Role)
        random.shuffle(roles)
        players = [Player(role=role) for role in roles[:6]]
        return {"players": players, "current_round": 1}
    
    def production_phase(self, game):
        for p in game["players"]:
            if p.role == Role.LANDLORD:
                p.grain += p.land
                p.legacy_points += max(1, p.land // 2)
            elif p.role == Role.FARMER:
                p.grain += 2
                p.labor_points += 1
            elif p.role == Role.WIDOW:
                if not p.bodhisattva_mode:
                    p.merit += 2
                else:
                    p.merit += 1
            elif p.role == Role.MONK:
                if not p.retreat_mode:
                    p.dharma_power = min(10, p.dharma_power + 1)
                else:
                    p.grant_points += 3
            elif p.role == Role.MERCHANT:
                p.coins += 2
    
    def event_phase(self, game):
        event_type = random.randint(1, 6)
        
        if event_type == 1:
            for p in game["players"]:
                if p.role == Role.OFFICIAL:
                    p.reputation += 2
                    p.court_visits += 1
                p.merit += 1
                
        elif event_type == 2:
            for p in game["players"]:
                p.grain = max(0, p.grain - 2)
            for p in game["players"]:
                if p.role == Role.OFFICIAL and p.reputation >= 1:
                    if random.random() > 0.4:
                        p.reputation = max(0, p.reputation - 1)
                        p.petitions += 1
                        p.merit += 3
                        for f in game["players"]:
                            if f.role in [Role.FARMER, Role.WIDOW]:
                                f.grain += 1
                                
        elif event_type == 3:
            participants = 0
            for p in game["players"]:
                if p.role == Role.MONK:
                    continue
                if p.coins >= 2 and random.random() > 0.3:
                    p.coins -= 2
                    p.merit += 1
                    participants += 1
                    if p.role == Role.MERCHANT:
                        p.total_donated += 2
                elif p.role == Role.WIDOW:
                    p.merit += 1
                    participants += 1
            for p in game["players"]:
                if p.role == Role.MONK:
                    p.grant_points += participants
                    
        elif event_type == 4:
            valid_targets = [p for p in game["players"] if p.life > 1]
            if valid_targets:
                target = random.choice(valid_targets)
                target.life -= 1
                target.awakening_tokens += 1
                
        elif event_type == 5:
            for p in game["players"]:
                if p.role == Role.FARMER:
                    p.grain += 3
                elif p.role == Role.LANDLORD:
                    p.grain += p.land
                    
        else:
            for p in game["players"]:
                if p.role == Role.MERCHANT:
                    p.coins += 3
    
    def action_phase(self, game):
        for p in game["players"]:
            ap = 3 if p.role == Role.FARMER else 2
            if p.role == Role.WIDOW and p.bodhisattva_mode:
                ap += 2
            
            self.check_state_transitions(p, game)
            
            while ap > 0:
                action = self.decide_action(p, game, ap)
                ap = self.execute_action(p, game, action, ap)
    
    def check_state_transitions(self, p, game):
        if p.role == Role.WIDOW and not p.bodhisattva_mode:
            if (p.merit >= 8 and p.reputation == 0 and 
                p.get_total_resources() <= 10):
                p.bodhisattva_mode = True
                p.liberation_turn = game["current_round"]
        
        if p.role == Role.MONK and game["current_round"] >= 5:
            if p.dharma_power <= 6 and p.grant_points >= 5:
                p.retreat_mode = True
        
        if p.role == Role.OFFICIAL and game["current_round"] >= 7:
            if not p.retired and p.reputation >= 3 and p.petitions >= 3:
                if random.random() > 0.4:
                    p.retired = True
                    p.merit += p.reputation * 2
                    p.reputation = 0
        
        if p.role == Role.MERCHANT and not p.charity_mode:
            if p.total_donated >= 6:
                p.charity_mode = True
    
    def execute_action(self, p, game, action, ap) -> int:
        if action == "none":
            return 0
        
        elif action == "donate":
            if p.coins >= 3:
                p.coins -= 3
                p.merit += 1
                if p.role == Role.WIDOW and not p.bodhisattva_mode:
                    p.merit += 1
                if p.role == Role.MERCHANT:
                    p.total_donated += 3
                p.reputation += 1
                for mp in game["players"]:
                    if mp.role == Role.MONK:
                        mp.dharma_power = min(10, mp.dharma_power + 1)
            return ap - 1
            
        elif action == "donate_anonymous":
            if p.coins >= 4:
                p.coins -= 4
                p.merit += 2
                if p.role == Role.WIDOW and not p.bodhisattva_mode:
                    p.merit += 1
                if p.role == Role.MERCHANT:
                    p.total_donated += 4
                for mp in game["players"]:
                    if mp.role == Role.MONK:
                        mp.dharma_power = min(10, mp.dharma_power + 1)
            return ap - 1
            
        elif action == "trade":
            if p.grain >= 3:
                p.grain -= 3
                p.coins += 4 if p.role == Role.MERCHANT else 2
            return ap
            
        elif action == "buy_land":
            cost = 4 if p.role == Role.LANDLORD else 6
            if p.coins >= cost and p.land < 5:
                p.coins -= cost
                p.land += 1
            return ap - 1
        
        elif action == "save_being":
            targets = [t for t in game["players"] 
                      if t != p and t.role != Role.MONK and t.merit < 25]
            if targets:
                target = min(targets, key=lambda x: x.merit)
                merit_given = 4
                target.merit += merit_given
                p.salvation_points += merit_given
                if id(target) not in p.saved_players:
                    p.saved_players.add(id(target))
                    p.beings_saved += 1
            return ap - 1
        
        elif action == "grant":
            if p.dharma_power >= 2:
                targets = [t for t in game["players"] if t != p]
                if targets:
                    target = random.choice(targets)
                    grant = min(4, p.dharma_power)
                    p.dharma_power -= grant
                    target.merit += grant
                    p.grant_points += grant
            return ap - 1
        
        elif action == "grand_charity":
            if p.coins >= 5:
                donation = min(p.coins - 2, 8)
                p.coins -= donation
                p.total_donated += donation
                p.merit += donation // 2
                for other in game["players"]:
                    if other != p and other.role != Role.MONK:
                        other.coins += 1
            return ap - 1
        
        elif action == "donate_land":
            if p.land >= 1:
                p.land -= 1
                p.land_donated += 1
                p.merit += 4
                if p.land_donated >= 2 and not p.temple_built:
                    p.temple_built = True
                    p.merit += 6
            return ap - 1
            
        elif action == "build_temple":
            if p.land >= 2 and not p.temple_built:
                p.land -= 2
                p.land_donated += 2
                p.temple_built = True
                p.merit += 12
            return ap - 1
        
        elif action == "go_to_court":
            p.reputation += 1
            p.court_visits += 1
            return ap - 1
            
        elif action == "petition":
            if p.reputation >= 1:
                p.reputation = max(0, p.reputation - 1)
                p.petitions += 1
                p.merit += 3
                targets = [t for t in game["players"] 
                          if t != p and t.role not in [Role.MONK, Role.OFFICIAL]]
                if targets:
                    target = min(targets, key=lambda x: x.merit)
                    target.merit += 2
            return ap - 1
            
        elif action == "retire":
            if not p.retired and p.reputation >= 2:
                p.merit += p.reputation * 2
                p.retired = True
                p.reputation = 0
            return ap - 1
        
        elif action == "daily_good":
            if p.grain >= 1:
                p.grain -= 1
                p.merit += 2
                p.daily_good_deeds += 1
            return ap - 1
            
        elif action == "share_harvest":
            if p.grain >= 3:
                p.grain -= 2
                targets = [t for t in game["players"] 
                          if t != p and t.role != Role.MONK]
                if targets:
                    target = min(targets, key=lambda x: x.grain)
                    target.grain += 2
                    p.merit += 2
                    p.harvest_shared += 1
            return ap - 1
        
        elif action == "use_awakening":
            if p.awakening_tokens > 0:
                p.awakening_tokens -= 1
                p.merit += 4
            return ap - 1
        
        return ap - 1
    
    def decide_action(self, player, game, remaining_ap) -> str:
        actions = []
        p = player
        round_num = game["current_round"]
        
        if p.role == Role.WIDOW:
            if p.bodhisattva_mode:
                targets = [t for t in game["players"] 
                          if t != p and t.role != Role.MONK and t.merit < 25]
                if targets:
                    actions.append(("save_being", 0.9))
            else:
                if p.coins >= 4:
                    actions.append(("donate_anonymous", 0.6))
                elif p.coins >= 3:
                    actions.append(("donate", 0.5))
        
        elif p.role == Role.MONK:
            if p.dharma_power >= 3:
                actions.append(("grant", 0.85))
            elif p.dharma_power >= 2:
                actions.append(("grant", 0.7))
        
        elif p.role == Role.MERCHANT:
            if p.charity_mode and p.coins >= 5:
                actions.append(("grand_charity", 0.8))
            if p.coins >= 4:
                actions.append(("donate_anonymous", 0.6))
            if p.coins >= 3:
                actions.append(("donate", 0.5))
            if p.grain >= 3:
                actions.append(("trade", 0.65))
        
        elif p.role == Role.LANDLORD:
            if p.land >= 2 and not p.temple_built and round_num >= 3:
                actions.append(("build_temple", 0.7))
            if p.land >= 1 and round_num >= 4:
                actions.append(("donate_land", 0.6))
            if p.coins >= 4 and p.land < 4 and round_num <= 5:
                actions.append(("buy_land", 0.5))
            if p.coins >= 3:
                actions.append(("donate", 0.3))
        
        elif p.role == Role.OFFICIAL:
            if p.reputation <= 1 and not p.retired:
                actions.append(("go_to_court", 0.75))
            if p.reputation >= 2 and not p.retired:
                actions.append(("petition", 0.7))
            if p.reputation >= 4 and round_num >= 6 and not p.retired:
                actions.append(("retire", 0.6))
            if p.coins >= 4:
                actions.append(("donate_anonymous", 0.35))
        
        elif p.role == Role.FARMER:
            if p.grain >= 5:
                actions.append(("share_harvest", 0.75))
            if p.grain >= 2:
                actions.append(("daily_good", 0.7))
            if p.grain >= 3:
                actions.append(("trade", 0.35))
            if p.coins >= 3:
                actions.append(("donate", 0.25))
        
        if p.awakening_tokens > 0:
            actions.append(("use_awakening", 0.9))
        
        if not actions:
            return "none"
        
        actions.sort(key=lambda x: x[1], reverse=True)
        
        for action, priority in actions:
            if random.random() < priority:
                return action
        
        return actions[0][0] if actions else "none"
    
    def run_game(self) -> Dict:
        game = self.create_game()
        
        for round_num in range(1, 11):
            game["current_round"] = round_num
            self.production_phase(game)
            self.event_phase(game)
            self.action_phase(game)
            for p in game["players"]:
                p.life -= 1
        
        results = []
        for p in game["players"]:
            path_complete, path_name, path_bonus = p.check_path_completion()
            score = p.get_final_score()
            
            results.append({
                "role": p.role.value,
                "merit": p.merit,
                "reputation": p.reputation,
                "final_score": score,
                "path_complete": path_complete,
                "path_name": path_name,
                "path_bonus": path_bonus
            })
        
        sorted_results = sorted(results, key=lambda x: x["final_score"], reverse=True)
        winner = sorted_results[0]
        
        win_type = winner["path_name"] if winner["path_complete"] else "standard"
        
        return {"winner": winner["role"], "win_type": win_type, "scores": results}
    
    def run_batch(self, num_games: int) -> Dict:
        role_wins = {role.value: 0 for role in Role}
        role_scores = {role.value: [] for role in Role}
        path_wins = {}
        path_completions = {role.value: {"count": 0, "paths": {}} for role in Role}
        
        for _ in range(num_games):
            result = self.run_game()
            role_wins[result["winner"]] += 1
            
            win_type = result["win_type"]
            path_wins[win_type] = path_wins.get(win_type, 0) + 1
            
            for p in result["scores"]:
                role_scores[p["role"]].append(p["final_score"])
                if p["path_complete"]:
                    path_completions[p["role"]]["count"] += 1
                    pn = p["path_name"]
                    path_completions[p["role"]]["paths"][pn] = \
                        path_completions[p["role"]]["paths"].get(pn, 0) + 1
        
        return {
            "total_games": num_games,
            "role_win_rates": {k: v/num_games*100 for k, v in role_wins.items()},
            "role_avg_scores": {k: sum(v)/len(v) if v else 0 for k, v in role_scores.items()},
            "role_score_std": {k: (sum((x - sum(v)/len(v))**2 for x in v)/len(v))**0.5 if v else 0 
                              for k, v in role_scores.items()},
            "win_types": {k: v/num_games*100 for k, v in path_wins.items()},
            "path_completions": {
                k: {
                    "rate": v["count"]/num_games*100,
                    "paths": {pk: pv/num_games*100 for pk, pv in v["paths"].items()}
                } for k, v in path_completions.items()
            }
        }

def main():
    simulator = GameSimulator()
    
    test_sizes = [100, 1000, 10000]
    all_results = {}
    
    for size in test_sizes:
        print(f"Running {size} games simulation...")
        start = time.time()
        results = simulator.run_batch(size)
        elapsed = time.time() - start
        results["elapsed_seconds"] = round(elapsed, 2)
        all_results[size] = results
        print(f"  Completed in {elapsed:.2f} seconds")
    
    with open("batch_simulation_results_v28.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*70)
    print("BATCH SIMULATION RESULTS - Path to Salvation v2.8")
    print("(Six Paths - Final Balance v2)")
    print("="*70)
    
    for size in test_sizes:
        r = all_results[size]
        print(f"\n{'='*70}")
        print(f"  {size} GAMES ({r['elapsed_seconds']}s)")
        print(f"{'='*70}")
        
        print("\n[Win Rates]")
        for role, rate in sorted(r["role_win_rates"].items(), key=lambda x: x[1], reverse=True):
            bar = "#" * int(rate / 2)
            print(f"  {role}: {rate:6.2f}% {bar}")
        
        print("\n[Average Scores]")
        for role in sorted(r["role_avg_scores"].keys(), key=lambda x: r["role_avg_scores"][x], reverse=True):
            avg = r["role_avg_scores"][role]
            std = r["role_score_std"][role]
            print(f"  {role}: {avg:6.1f} (+/- {std:.1f})")
        
        print(f"\n[Victory Types]")
        for vtype, rate in sorted(r["win_types"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {vtype}: {rate:5.2f}%")
    
    print("\n" + "="*70)
    print("Results saved to batch_simulation_results_v28.json")
    
    return all_results

if __name__ == "__main__":
    main()
