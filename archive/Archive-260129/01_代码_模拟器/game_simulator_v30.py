# -*- coding: utf-8 -*-
"""
《救赎之路》v3.0 七角色学术版
基于宗教经济学框架的完整模拟

七角色：
1. 皇帝（Emperor）- 功德使，天命道
2. 僧伽（Sangha）- 福田，涅槃道
3. 护法（Patron）- 檀越，善财道
4. 田主（Landowner）- 土地经济，舍宅道
5. 士人（Scholar）- 儒佛互动，清名道
6. 农人（Peasant）- 实践宗教性，勤劳道
7. 虔信女（Upasika）- 在家修行，菩萨道
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from enum import Enum
import json
import time

class Role(Enum):
    EMPEROR = "皇帝"
    SANGHA = "僧伽"
    PATRON = "护法"
    LANDOWNER = "田主"
    SCHOLAR = "士人"
    PEASANT = "农人"
    UPASIKA = "虔信女"

@dataclass
class Player:
    role: Role
    grain: int = 0
    coins: int = 0
    land: int = 0
    merit: int = 0
    reputation: int = 0
    
    # 角色专属资源
    dharma_power: int = 0      # 法力（僧伽）
    grant_points: int = 0       # 授德点（僧伽）
    dragon_qi: int = 0          # 龙气（皇帝）
    prestige: int = 0           # 威望（皇帝/士人）
    literary_fame: int = 0      # 文名（士人）
    total_donated: int = 0      # 累计捐献（护法）
    land_donated: int = 0       # 捐献土地（田主）
    legacy_points: int = 0      # 传承点（田主）
    temple_built: bool = False  # 是否建寺
    labor_points: int = 0       # 勤劳积分（农人）
    daily_good_deeds: int = 0   # 日行一善次数
    harvest_shared: int = 0     # 分享收成次数
    
    # 虔信女专属
    bodhisattva_mode: bool = False
    salvation_points: int = 0
    beings_saved: int = 0
    saved_players: Set = field(default_factory=set)
    merit_transfers: int = 0    # 回向次数
    
    # 皇帝专属
    bestowals: int = 0          # 钦赐次数
    
    # 士人专属
    inscriptions: int = 0       # 撰碑次数
    
    # 状态
    life: int = 10
    action_points: int = 2
    awakening_tokens: int = 0
    retreat_mode: bool = False
    charity_mode: bool = False
    retired: bool = False
    
    def __post_init__(self):
        if self.role == Role.EMPEROR:
            self.grain, self.coins, self.land = 5, 8, 2
            self.prestige = 5
            self.dragon_qi = 3
        elif self.role == Role.SANGHA:
            self.dharma_power = 8
            self.merit = 3
            self.grain, self.coins, self.land = 0, 0, 0
        elif self.role == Role.PATRON:
            self.grain, self.coins, self.land = 2, 12, 0
        elif self.role == Role.LANDOWNER:
            self.grain, self.coins, self.land = 4, 2, 4
        elif self.role == Role.SCHOLAR:
            self.grain, self.coins, self.land = 2, 4, 1
            self.prestige = 3
            self.literary_fame = 2
        elif self.role == Role.PEASANT:
            self.grain, self.coins, self.land = 6, 2, 0
            self.action_points = 3
        elif self.role == Role.UPASIKA:
            self.grain, self.coins, self.land = 2, 3, 0
            self.merit = 5
    
    def get_total_resources(self) -> int:
        return self.grain + self.coins + self.land * 5
    
    def check_path_completion(self) -> tuple:
        if self.role == Role.EMPEROR:
            if self.dragon_qi >= 12 and self.bestowals >= 4 and self.prestige >= 6:
                return (True, "天命道", 45)
            elif self.dragon_qi >= 8 and self.bestowals >= 2:
                return (True, "天命道（小成）", 25)
            return (False, "", 0)
            
        elif self.role == Role.SANGHA:
            if self.dharma_power <= 2 and self.grant_points >= 15:
                return (True, "涅槃道", 50)
            elif self.grant_points >= 10:
                return (True, "涅槃道（小成）", 25)
            return (False, "", 0)
            
        elif self.role == Role.PATRON:
            if self.total_donated >= 20 and self.coins <= 5:
                return (True, "善财道", 50)
            elif self.total_donated >= 12:
                return (True, "善财道（小成）", 28)
            return (False, "", 0)
            
        elif self.role == Role.LANDOWNER:
            if self.land_donated >= 4 and self.temple_built:
                return (True, "舍宅道", 55)
            elif self.land_donated >= 2 or self.temple_built:
                return (True, "舍宅道（小成）", 28)
            return (False, "", 0)
            
        elif self.role == Role.SCHOLAR:
            if self.prestige >= 8 and self.literary_fame >= 5 and self.inscriptions >= 3:
                return (True, "清名道", 45)
            elif self.inscriptions >= 2 or self.literary_fame >= 4:
                return (True, "清名道（小成）", 22)
            return (False, "", 0)
            
        elif self.role == Role.PEASANT:
            if self.daily_good_deeds >= 6 and self.harvest_shared >= 4:
                return (True, "勤劳道", 50)
            elif self.daily_good_deeds >= 3 or self.harvest_shared >= 2:
                return (True, "勤劳道（小成）", 25)
            return (False, "", 0)
            
        elif self.role == Role.UPASIKA:
            if self.bodhisattva_mode and self.beings_saved >= 4:
                return (True, "菩萨道", 45)
            elif self.bodhisattva_mode and self.beings_saved >= 2:
                return (True, "菩萨道（小成）", 25)
            return (False, "", 0)
        
        return (False, "", 0)
    
    def get_final_score(self) -> float:
        path_complete, path_name, path_bonus = self.check_path_completion()
        resource_bonus = self.get_total_resources() // 4
        
        if self.role == Role.EMPEROR:
            base_score = self.dragon_qi * 3 + self.prestige * 2 + self.merit * 2 + resource_bonus
        elif self.role == Role.SANGHA:
            base_score = self.grant_points * 3 + self.merit * 2
        elif self.role == Role.PATRON:
            base_score = self.merit * 2 + self.total_donated + resource_bonus
        elif self.role == Role.LANDOWNER:
            base_score = self.merit * 2 + self.legacy_points * 2 + self.land_donated * 5 + resource_bonus
        elif self.role == Role.SCHOLAR:
            base_score = self.merit * 2 + self.prestige * 2 + self.literary_fame * 3 + resource_bonus
        elif self.role == Role.PEASANT:
            base_score = self.merit * 2 + self.labor_points * 2 + resource_bonus
        elif self.role == Role.UPASIKA:
            base_score = self.merit * 2 + resource_bonus
            if self.bodhisattva_mode:
                base_score += self.salvation_points * 3 + self.beings_saved * 6
        else:
            base_score = self.merit * 2 + resource_bonus
        
        if path_complete:
            base_score += path_bonus
        
        return base_score

class GameSimulator:
    def __init__(self):
        pass
        
    def create_game(self):
        roles = list(Role)
        random.shuffle(roles)
        players = [Player(role=role) for role in roles[:7]]  # 7角色
        return {"players": players, "current_round": 1}
    
    def production_phase(self, game):
        for p in game["players"]:
            if p.role == Role.EMPEROR:
                p.coins += 1  # 国库收入
            elif p.role == Role.SANGHA:
                if not p.retreat_mode:
                    p.dharma_power = min(10, p.dharma_power + 1)
                else:
                    p.grant_points += 3
            elif p.role == Role.PATRON:
                p.coins += 2  # 商业收入
            elif p.role == Role.LANDOWNER:
                p.grain += p.land
                p.legacy_points += max(1, p.land // 2)
            elif p.role == Role.SCHOLAR:
                if game["current_round"] % 2 == 0:
                    p.literary_fame += 1
            elif p.role == Role.PEASANT:
                p.grain += 2
                p.labor_points += 1
            elif p.role == Role.UPASIKA:
                if not p.bodhisattva_mode:
                    p.merit += 1  # 诵经忏悔
    
    def event_phase(self, game):
        event_type = random.randint(1, 6)
        
        if event_type == 1:  # 皇恩浩荡
            for p in game["players"]:
                if p.role == Role.EMPEROR:
                    p.dragon_qi += 1
                    p.prestige += 1
                p.merit += 1
                
        elif event_type == 2:  # 天灾
            for p in game["players"]:
                p.grain = max(0, p.grain - 2)
            # 皇帝可以救灾
            for p in game["players"]:
                if p.role == Role.EMPEROR and p.dragon_qi >= 1:
                    if random.random() > 0.5:
                        p.dragon_qi -= 1
                        p.merit += 3
                        for f in game["players"]:
                            if f.role in [Role.PEASANT, Role.UPASIKA]:
                                f.grain += 2
                                
        elif event_type == 3:  # 法会
            participants = 0
            for p in game["players"]:
                if p.role == Role.SANGHA:
                    continue
                if p.coins >= 2 and random.random() > 0.3:
                    p.coins -= 2
                    p.merit += 1
                    participants += 1
                    if p.role == Role.PATRON:
                        p.total_donated += 2
            for p in game["players"]:
                if p.role == Role.SANGHA:
                    p.grant_points += participants
                    
        elif event_type == 4:  # 无常
            valid_targets = [p for p in game["players"] if p.life > 1]
            if valid_targets:
                target = random.choice(valid_targets)
                target.life -= 1
                target.awakening_tokens += 1
                
        elif event_type == 5:  # 丰收
            for p in game["players"]:
                if p.role == Role.PEASANT:
                    p.grain += 3
                elif p.role == Role.LANDOWNER:
                    p.grain += p.land
                    
        else:  # 商机
            for p in game["players"]:
                if p.role == Role.PATRON:
                    p.coins += 3
    
    def action_phase(self, game):
        for p in game["players"]:
            ap = 3 if p.role == Role.PEASANT else 2
            if p.role == Role.UPASIKA and p.bodhisattva_mode:
                ap += 2
            
            self.check_state_transitions(p, game)
            
            while ap > 0:
                action = self.decide_action(p, game, ap)
                ap = self.execute_action(p, game, action, ap)
    
    def check_state_transitions(self, p, game):
        if p.role == Role.UPASIKA and not p.bodhisattva_mode:
            if p.merit >= 10 and p.merit_transfers >= 3:
                p.bodhisattva_mode = True
        
        if p.role == Role.SANGHA and game["current_round"] >= 5:
            if p.dharma_power <= 5 and p.grant_points >= 6:
                p.retreat_mode = True
        
        if p.role == Role.PATRON and not p.charity_mode:
            if p.total_donated >= 8:
                p.charity_mode = True
    
    def execute_action(self, p, game, action, ap) -> int:
        if action == "none":
            return 0
        
        # ===== 皇帝行动 =====
        elif action == "bestow":
            if p.coins >= 2:
                targets = [t for t in game["players"] if t != p]
                if targets:
                    target = random.choice(targets)
                    p.coins -= 2
                    target.merit += 3
                    p.dragon_qi += 2
                    p.prestige += 1
                    p.bestowals += 1
            return ap - 1
            
        elif action == "prayer_edict":
            if p.dragon_qi >= 1:
                sangha = [t for t in game["players"] if t.role == Role.SANGHA]
                if sangha:
                    s = sangha[0]
                    if s.dharma_power >= 1:
                        p.dragon_qi -= 1
                        s.dharma_power -= 1
                        p.dragon_qi += 2
                        s.grant_points += 2
            return ap - 1
        
        # ===== 僧伽行动 =====
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
            
        elif action == "chant":
            if p.dharma_power >= 2:
                targets = [t for t in game["players"] if t != p]
                if targets:
                    target = random.choice(targets)
                    p.dharma_power -= 2
                    target.merit += 2
                    p.grant_points += 1
            return ap - 1
        
        # ===== 护法行动 =====
        elif action == "donate":
            if p.coins >= 3:
                p.coins -= 3
                p.merit += 1
                if p.role == Role.PATRON:
                    p.total_donated += 3
                elif p.role == Role.UPASIKA and not p.bodhisattva_mode:
                    p.merit += 1
                p.reputation += 1
                for mp in game["players"]:
                    if mp.role == Role.SANGHA:
                        mp.dharma_power = min(10, mp.dharma_power + 1)
            return ap - 1
            
        elif action == "grand_charity":
            if p.coins >= 6:
                donation = min(p.coins - 2, 8)
                p.coins -= donation
                p.total_donated += donation
                p.merit += donation // 2
            return ap - 1
            
        elif action == "build_temple_patron":
            if p.coins >= 10:
                p.coins -= 10
                p.merit += 8
                p.total_donated += 10
            return ap - 1
        
        # ===== 田主行动 =====
        elif action == "buy_land":
            cost = 4
            if p.coins >= cost and p.land < 6:
                p.coins -= cost
                p.land += 1
            return ap - 1
            
        elif action == "donate_land":
            if p.land >= 1:
                p.land -= 1
                p.land_donated += 1
                p.merit += 5
                if p.land_donated >= 2 and not p.temple_built:
                    p.temple_built = True
                    p.merit += 8
            return ap - 1
            
        elif action == "build_temple":
            if p.land >= 2 and not p.temple_built:
                p.land -= 2
                p.land_donated += 2
                p.temple_built = True
                p.merit += 15
            return ap - 1
        
        # ===== 士人行动 =====
        elif action == "write_inscription":
            if p.literary_fame >= 1:
                p.literary_fame -= 1
                p.prestige += 2
                p.inscriptions += 1
                # 给寺院加功德
                for mp in game["players"]:
                    if mp.role == Role.SANGHA:
                        mp.grant_points += 1
            return ap - 1
            
        elif action == "compose_poem":
            p.merit += 1
            p.literary_fame += 1
            return ap - 1
            
        elif action == "discuss_dharma":
            sangha = [t for t in game["players"] if t.role == Role.SANGHA]
            if sangha:
                p.merit += 2
                sangha[0].grant_points += 1
            return ap - 1
        
        # ===== 农人行动 =====
        elif action == "daily_good":
            if p.grain >= 1:
                p.grain -= 1
                p.merit += 2
                p.daily_good_deeds += 1
            return ap - 1
            
        elif action == "share_harvest":
            if p.grain >= 3:
                p.grain -= 2
                targets = [t for t in game["players"] if t != p and t.role != Role.SANGHA]
                if targets:
                    target = min(targets, key=lambda x: x.grain)
                    target.grain += 2
                    p.merit += 2
                    p.harvest_shared += 1
            return ap - 1
            
        elif action == "supply_sangha":
            if p.grain >= 2:
                p.grain -= 2
                p.merit += 1
                for mp in game["players"]:
                    if mp.role == Role.SANGHA:
                        mp.dharma_power = min(10, mp.dharma_power + 1)
            return ap - 1
        
        # ===== 虔信女行动 =====
        elif action == "transfer_merit":
            if p.merit >= 2:
                p.merit -= 2
                p.salvation_points += 3
                p.merit_transfers += 1
            return ap - 1
            
        elif action == "save_being":
            targets = [t for t in game["players"] 
                      if t != p and t.role != Role.SANGHA and t.merit < 20]
            if targets:
                target = min(targets, key=lambda x: x.merit)
                merit_given = 4
                target.merit += merit_given
                p.salvation_points += merit_given
                if id(target) not in p.saved_players:
                    p.saved_players.add(id(target))
                    p.beings_saved += 1
            return ap - 1
        
        # ===== 通用行动 =====
        elif action == "trade":
            if p.grain >= 3:
                p.grain -= 3
                p.coins += 2
            return ap
            
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
        
        if p.role == Role.EMPEROR:
            if p.coins >= 2:
                actions.append(("bestow", 0.7))
            if p.dragon_qi >= 1:
                actions.append(("prayer_edict", 0.5))
        
        elif p.role == Role.SANGHA:
            if p.dharma_power >= 3:
                actions.append(("grant", 0.8))
            if p.dharma_power >= 2:
                actions.append(("chant", 0.6))
        
        elif p.role == Role.PATRON:
            if p.charity_mode and p.coins >= 6:
                actions.append(("grand_charity", 0.75))
            if p.coins >= 10:
                actions.append(("build_temple_patron", 0.6))
            if p.coins >= 3:
                actions.append(("donate", 0.5))
            if p.grain >= 3:
                actions.append(("trade", 0.6))
        
        elif p.role == Role.LANDOWNER:
            if p.land >= 2 and not p.temple_built and round_num >= 3:
                actions.append(("build_temple", 0.7))
            if p.land >= 1 and round_num >= 4:
                actions.append(("donate_land", 0.6))
            if p.coins >= 4 and p.land < 5 and round_num <= 5:
                actions.append(("buy_land", 0.5))
        
        elif p.role == Role.SCHOLAR:
            if p.literary_fame >= 1 and round_num >= 3:
                actions.append(("write_inscription", 0.7))
            actions.append(("compose_poem", 0.5))
            actions.append(("discuss_dharma", 0.4))
        
        elif p.role == Role.PEASANT:
            if p.grain >= 4:
                actions.append(("share_harvest", 0.7))
            if p.grain >= 2:
                actions.append(("daily_good", 0.65))
            if p.grain >= 2:
                actions.append(("supply_sangha", 0.5))
            if p.grain >= 3:
                actions.append(("trade", 0.35))
        
        elif p.role == Role.UPASIKA:
            if p.bodhisattva_mode:
                targets = [t for t in game["players"] 
                          if t != p and t.role != Role.SANGHA and t.merit < 20]
                if targets:
                    actions.append(("save_being", 0.85))
            else:
                if p.merit >= 2:
                    actions.append(("transfer_merit", 0.7))
                if p.coins >= 3:
                    actions.append(("donate", 0.5))
        
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
    
    with open("batch_simulation_results_v30.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*70)
    print("BATCH SIMULATION RESULTS - Path to Salvation v3.0")
    print("(Seven Roles Academic Edition)")
    print("="*70)
    
    for size in test_sizes:
        r = all_results[size]
        print(f"\n{'='*70}")
        print(f"  {size} GAMES ({r['elapsed_seconds']}s)")
        print(f"{'='*70}")
        
        print("\n[Win Rates - 7 Roles]")
        for role, rate in sorted(r["role_win_rates"].items(), key=lambda x: x[1], reverse=True):
            bar = "#" * int(rate / 2)
            print(f"  {role}: {rate:6.2f}% {bar}")
        
        print("\n[Average Scores]")
        for role in sorted(r["role_avg_scores"].keys(), key=lambda x: r["role_avg_scores"][x], reverse=True):
            avg = r["role_avg_scores"][role]
            std = r["role_score_std"][role]
            print(f"  {role}: {avg:6.1f} (+/- {std:.1f})")
        
        print(f"\n[Victory Types - Seven Paths]")
        for vtype, rate in sorted(r["win_types"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {vtype}: {rate:5.2f}%")
    
    print("\n" + "="*70)
    print("Results saved to batch_simulation_results_v30.json")
    
    return all_results

if __name__ == "__main__":
    main()
