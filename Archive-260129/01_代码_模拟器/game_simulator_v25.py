# -*- coding: utf-8 -*-
"""
《救赎之路》v2.5 大规模模拟测试
六道系统平衡修正版

v2.4问题：
- 官员76%胜率（声望自动增长过强）
- 寡妇/富商/地主几乎无法获胜

v2.5修正：
1. 官员：声望不再自动增长，需要主动"赴朝"获取；清官道加分降低
2. 寡妇：菩萨状态门槛降低（功德≥12），渡化加分提高
3. 富商：善财道门槛降低（捐献≥12），初始金钱增加
4. 地主：舍宅道加分提高，传承点机制增强
5. 僧侣：涅槃道条件放宽
6. 农民：维持（已平衡）
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
    
    # 寡妇·菩萨道
    bodhisattva_mode: bool = False
    liberation_turn: int = 0
    salvation_points: int = 0
    beings_saved: int = 0
    saved_players: Set = field(default_factory=set)
    
    # 富商·善财道
    charity_mode: bool = False
    total_donated: int = 0
    
    # 地主·舍宅道
    temple_built: bool = False
    land_donated: int = 0
    legacy_points: int = 0
    
    # 官员·清官道
    retired: bool = False
    petitions: int = 0
    court_visits: int = 0  # 赴朝次数
    
    # 农民·勤劳道
    labor_points: int = 0
    daily_good_deeds: int = 0
    harvest_shared: int = 0
    
    def __post_init__(self):
        if self.role == Role.MERCHANT:
            self.grain, self.coins, self.land = 2, 8, 0  # v2.5: 初始金钱从6增加到8
        elif self.role == Role.LANDLORD:
            self.grain, self.coins, self.land = 3, 2, 3  # v2.5: 初始土地从2增加到3
        elif self.role == Role.OFFICIAL:
            self.grain, self.coins, self.land = 2, 4, 1
            self.reputation = 1  # v2.5: 初始声望从2降到1
        elif self.role == Role.FARMER:
            self.grain, self.coins, self.land = 4, 2, 0
            self.action_points = 3
        elif self.role == Role.WIDOW:
            self.grain, self.coins, self.land, self.merit = 2, 3, 0, 3  # v2.5: 初始功德从2增加到3
        elif self.role == Role.MONK:
            self.dharma_power = 6  # v2.5: 初始法力从5增加到6
    
    def get_total_resources(self) -> int:
        return self.grain + self.coins + self.land * 5
    
    def check_path_completion(self) -> tuple:
        """检查是否完成专属道路"""
        if self.role == Role.WIDOW:
            # v2.5: 菩萨道降低门槛
            if self.bodhisattva_mode and self.beings_saved >= 4:
                return (True, "菩萨道", 40)
            elif self.bodhisattva_mode and self.beings_saved >= 2:
                return (True, "菩萨道（小成）", 25)
            return (False, "", 0)
            
        elif self.role == Role.MONK:
            # v2.5: 涅槃道条件放宽
            if self.dharma_power <= 3 and self.grant_points >= 12:
                return (True, "涅槃道", 35)
            return (False, "", 0)
            
        elif self.role == Role.MERCHANT:
            # v2.5: 善财道门槛降低
            if self.total_donated >= 15 and self.coins <= 5:
                return (True, "善财道", 40)
            elif self.total_donated >= 10:
                return (True, "善财道（小成）", 20)
            return (False, "", 0)
            
        elif self.role == Role.LANDLORD:
            # v2.5: 舍宅道加分提高
            if self.land_donated >= 3 and self.temple_built:
                return (True, "舍宅道", 45)
            elif self.land_donated >= 2 or self.temple_built:
                return (True, "舍宅道（小成）", 25)
            return (False, "", 0)
            
        elif self.role == Role.OFFICIAL:
            # v2.5: 清官道加分降低
            if self.retired and self.petitions >= 4:
                return (True, "清官道", 35)
            elif self.retired or self.petitions >= 3:
                return (True, "清官道（小成）", 18)
            return (False, "", 0)
            
        elif self.role == Role.FARMER:
            if self.daily_good_deeds >= 5 and self.harvest_shared >= 3:
                return (True, "勤劳道", 40)
            elif self.daily_good_deeds >= 3 or self.harvest_shared >= 2:
                return (True, "勤劳道（小成）", 20)
            return (False, "", 0)
        
        return (False, "", 0)
    
    def get_final_score(self) -> float:
        # 基础分
        if self.role == Role.MONK:
            base_score = self.grant_points * 2 + self.merit
        else:
            resource_bonus = self.get_total_resources() // 3  # v2.5: 资源加分从÷2改为÷3
            base_score = self.merit * 2 + self.reputation + resource_bonus  # v2.5: 声望系数从×2降到×1
        
        # 专属道路加分
        path_complete, path_name, path_bonus = self.check_path_completion()
        if path_complete:
            base_score += path_bonus
        
        # 额外专属加分
        if self.role == Role.FARMER:
            base_score += self.labor_points
        elif self.role == Role.WIDOW and self.bodhisattva_mode:
            base_score += self.salvation_points * 3 + self.beings_saved * 5
        elif self.role == Role.MERCHANT:
            base_score += self.total_donated  # v2.5: 从÷2改为全额
        elif self.role == Role.LANDLORD:
            base_score += self.legacy_points * 2 + self.land_donated * 5
        elif self.role == Role.OFFICIAL:
            base_score += self.petitions * 5
        
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
                p.grain += 2  # v2.5: 从1增加到2
                p.labor_points += 1
            elif p.role == Role.WIDOW:
                if not p.bodhisattva_mode:
                    p.merit += 1  # v2.5: 每轮+1功德（从每2轮改为每轮）
            elif p.role == Role.MONK:
                if not p.retreat_mode:
                    p.dharma_power = min(10, p.dharma_power + 1)
                else:
                    p.grant_points += 2
            elif p.role == Role.OFFICIAL:
                # v2.5: 官员声望不再自动增长
                pass
            elif p.role == Role.MERCHANT:
                # v2.5: 富商每轮+1金钱（经商收入）
                p.coins += 1
    
    def event_phase(self, game):
        event_type = random.randint(1, 6)
        
        if event_type == 1:  # 皇恩浩荡
            for p in game["players"]:
                if p.role == Role.OFFICIAL:
                    p.reputation += 2
                    p.court_visits += 1
                p.merit += 1
                
        elif event_type == 2:  # 天灾
            for p in game["players"]:
                p.grain = max(0, p.grain - 2)
            for p in game["players"]:
                if p.role == Role.OFFICIAL and p.reputation >= 2:
                    if random.random() > 0.4:
                        p.reputation -= 1
                        p.petitions += 1
                        p.merit += 2
                        for f in game["players"]:
                            if f.role in [Role.FARMER, Role.WIDOW]:
                                f.grain += 1
                                
        elif event_type == 3:  # 法会
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
                    
        elif event_type == 4:  # 无常
            valid_targets = [p for p in game["players"] if p.life > 1]
            if valid_targets:
                target = random.choice(valid_targets)
                target.life -= 1
                target.awakening_tokens += 1
                
        elif event_type == 5:  # 丰收
            for p in game["players"]:
                if p.role == Role.FARMER:
                    p.grain += 3
                elif p.role == Role.LANDLORD:
                    p.grain += p.land
                    
        else:  # 商机
            for p in game["players"]:
                if p.role == Role.MERCHANT:
                    p.coins += 3
    
    def action_phase(self, game):
        for p in game["players"]:
            ap = 3 if p.role == Role.FARMER else 2
            
            self.check_state_transitions(p, game)
            
            while ap > 0:
                action = self.decide_action(p, game, ap)
                ap = self.execute_action(p, game, action, ap)
    
    def check_state_transitions(self, p, game):
        # v2.5: 寡妇菩萨状态门槛降低
        if p.role == Role.WIDOW and not p.bodhisattva_mode:
            if (p.merit >= 12 and p.reputation == 0 and 
                p.get_total_resources() <= 8):
                p.bodhisattva_mode = True
                p.liberation_turn = game["current_round"]
        
        if p.role == Role.MONK and game["current_round"] >= 6:
            if p.dharma_power <= 5 and p.grant_points >= 6:
                p.retreat_mode = True
        
        if p.role == Role.OFFICIAL and game["current_round"] >= 7:
            if not p.retired and p.reputation >= 4 and p.petitions >= 2:
                if random.random() > 0.4:
                    p.retired = True
                    p.merit += p.reputation * 2
                    p.reputation = 0
        
        if p.role == Role.MERCHANT and not p.charity_mode:
            if p.total_donated >= 8:
                p.charity_mode = True
    
    def execute_action(self, p, game, action, ap) -> int:
        if action == "none":
            return 0
        
        # 通用行动
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
                p.merit += 2  # v2.5: 匿名捐献功德从1增加到2
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
        
        # 寡妇·菩萨道
        elif action == "save_being":
            targets = [t for t in game["players"] 
                      if t != p and t.role != Role.MONK and t.merit < 20]
            if targets:
                target = min(targets, key=lambda x: x.merit)
                merit_given = 4  # v2.5: 从3增加到4
                target.merit += merit_given
                p.salvation_points += merit_given
                if id(target) not in p.saved_players:
                    p.saved_players.add(id(target))
                    p.beings_saved += 1
            return ap - 1
        
        # 僧侣·涅槃道
        elif action == "grant":
            if p.dharma_power >= 2:
                targets = [t for t in game["players"] if t != p]
                if targets:
                    target = random.choice(targets)
                    grant = min(4, p.dharma_power)  # v2.5: 从3增加到4
                    p.dharma_power -= grant
                    target.merit += grant
                    p.grant_points += grant
            return ap - 1
        
        # 富商·善财道
        elif action == "grand_charity":
            if p.coins >= 5:
                donation = min(p.coins - 2, 6)
                p.coins -= donation
                p.total_donated += donation
                p.merit += donation // 2
                for other in game["players"]:
                    if other != p and other.role != Role.MONK:
                        other.coins += 1
            return ap - 1
        
        # 地主·舍宅道
        elif action == "donate_land":
            if p.land >= 1:
                p.land -= 1
                p.land_donated += 1
                p.merit += 4  # v2.5: 从3增加到4
                if p.land_donated >= 2 and not p.temple_built:
                    p.temple_built = True
                    p.merit += 6
            return ap - 1
            
        elif action == "build_temple":
            if p.land >= 2 and not p.temple_built:
                p.land -= 2
                p.land_donated += 2
                p.temple_built = True
                p.merit += 12  # v2.5: 从10增加到12
            return ap - 1
        
        # 官员·清官道
        elif action == "go_to_court":
            # v2.5: 新行动 - 赴朝（主动获取声望）
            p.reputation += 2
            p.court_visits += 1
            return ap - 1
            
        elif action == "petition":
            if p.reputation >= 2:
                p.reputation -= 1
                p.petitions += 1
                p.merit += 3  # v2.5: 从2增加到3
                targets = [t for t in game["players"] 
                          if t != p and t.role not in [Role.MONK, Role.OFFICIAL]]
                if targets:
                    target = min(targets, key=lambda x: x.merit)
                    target.merit += 2
            return ap - 1
            
        elif action == "retire":
            if not p.retired and p.reputation >= 3:
                p.merit += p.reputation * 2
                p.retired = True
                p.reputation = 0
            return ap - 1
        
        # 农民·勤劳道
        elif action == "daily_good":
            if p.grain >= 1:
                p.grain -= 1
                p.merit += 2  # v2.5: 从1增加到2
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
                p.merit += 4  # v2.5: 从3增加到4
            return ap - 1
        
        return ap - 1
    
    def decide_action(self, player, game, remaining_ap) -> str:
        actions = []
        p = player
        round_num = game["current_round"]
        
        # 寡妇
        if p.role == Role.WIDOW:
            if p.bodhisattva_mode:
                targets = [t for t in game["players"] 
                          if t != p and t.role != Role.MONK and t.merit < 20]
                if targets:
                    actions.append(("save_being", 0.85))
            if p.coins >= 4:
                actions.append(("donate_anonymous", 0.5))
            elif p.coins >= 3:
                actions.append(("donate", 0.4))
        
        # 僧侣
        elif p.role == Role.MONK:
            if p.dharma_power >= 3:
                actions.append(("grant", 0.75))
            elif p.dharma_power >= 2:
                actions.append(("grant", 0.5))
        
        # 富商
        elif p.role == Role.MERCHANT:
            if p.charity_mode and p.coins >= 5:
                actions.append(("grand_charity", 0.7))
            if p.coins >= 4:
                actions.append(("donate_anonymous", 0.5))
            if p.coins >= 3:
                actions.append(("donate", 0.4))
            if p.grain >= 3:
                actions.append(("trade", 0.6))
        
        # 地主
        elif p.role == Role.LANDLORD:
            if p.land >= 2 and not p.temple_built and round_num >= 4:
                actions.append(("build_temple", 0.65))
            if p.land >= 1 and round_num >= 5:
                actions.append(("donate_land", 0.55))
            if p.coins >= 4 and p.land < 4 and round_num <= 6:
                actions.append(("buy_land", 0.5))
            if p.coins >= 3:
                actions.append(("donate", 0.3))
        
        # 官员
        elif p.role == Role.OFFICIAL:
            if p.reputation <= 2 and not p.retired:
                actions.append(("go_to_court", 0.7))
            if p.reputation >= 3 and not p.retired:
                actions.append(("petition", 0.6))
            if p.reputation >= 5 and round_num >= 6 and not p.retired:
                actions.append(("retire", 0.5))
            if p.coins >= 4:
                actions.append(("donate_anonymous", 0.4))
        
        # 农民
        elif p.role == Role.FARMER:
            if p.grain >= 5:
                actions.append(("share_harvest", 0.65))
            if p.grain >= 2:
                actions.append(("daily_good", 0.6))
            if p.grain >= 3:
                actions.append(("trade", 0.4))
            if p.coins >= 3:
                actions.append(("donate", 0.3))
        
        if p.awakening_tokens > 0:
            actions.append(("use_awakening", 0.85))
        
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
                "path_bonus": path_bonus,
                "total_resources": p.get_total_resources()
            })
        
        sorted_results = sorted(results, key=lambda x: x["final_score"], reverse=True)
        winner = sorted_results[0]
        
        win_type = winner["path_name"] if winner["path_complete"] else "standard"
        
        return {
            "winner": winner["role"], 
            "win_type": win_type, 
            "scores": results
        }
    
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
    
    with open("batch_simulation_results_v25.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*70)
    print("BATCH SIMULATION RESULTS - Path to Salvation v2.5")
    print("(Six Paths System - Balanced)")
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
        
        print(f"\n[Path Completion Rates]")
        for role, data in r["path_completions"].items():
            if data["rate"] > 0:
                paths_str = ", ".join([f"{k}:{v:.1f}%" for k, v in data["paths"].items()])
                print(f"  {role}: {data['rate']:.1f}% ({paths_str})")
    
    print("\n" + "="*70)
    print("Results saved to batch_simulation_results_v25.json")
    
    return all_results

if __name__ == "__main__":
    main()
