# -*- coding: utf-8 -*-
"""
《救赎之路》v2.3 大规模模拟测试
新增机制：寡妇"发大愿·渡众生"菩萨道

v2.3核心改动：
1. 寡妇解脱后进入"菩萨状态"，不直接获得加分
2. 菩萨状态下，寡妇每渡化一位众生（帮助其他玩家获得功德）获得渡化点
3. 寡妇最终得分 = 基础分 + 渡化点×5
4. 农民增加"勤劳加分"：每轮+1分
5. 僧侣涅槃加分提高到+40
6. 其他角色解脱加分维持+30
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict
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
    
    # v2.3 寡妇专属
    bodhisattva_mode: bool = False  # 菩萨状态
    liberation_turn: int = 0  # 解脱的回合
    salvation_points: int = 0  # 渡化点
    beings_saved: int = 0  # 渡化的众生数量
    
    # v2.3 农民专属
    labor_points: int = 0  # 勤劳积分
    
    def __post_init__(self):
        if self.role == Role.MERCHANT:
            self.grain, self.coins, self.land = 2, 6, 0
        elif self.role == Role.LANDLORD:
            self.grain, self.coins, self.land = 3, 2, 2
        elif self.role == Role.OFFICIAL:
            self.grain, self.coins, self.land = 2, 4, 1
        elif self.role == Role.FARMER:
            self.grain, self.coins, self.land = 4, 2, 0
            self.action_points = 3
        elif self.role == Role.WIDOW:
            self.grain, self.coins, self.land, self.merit = 2, 2, 0, 2
        elif self.role == Role.MONK:
            self.dharma_power = 5
    
    def get_total_resources(self) -> int:
        return self.grain + self.coins + self.land * 5
    
    def check_liberation_condition(self) -> bool:
        """检查是否满足解脱条件（不含菩萨状态判断）"""
        if self.role == Role.MONK:
            return self.dharma_power <= 2 and self.grant_points >= 15
        elif self.role == Role.WIDOW:
            # 寡妇解脱条件：功德≥25，声望=0，资源≤3
            return (self.merit >= 25 and 
                    self.reputation == 0 and 
                    self.get_total_resources() <= 3)
        else:
            return (self.merit >= 20 and 
                    self.reputation == 0 and 
                    self.get_total_resources() <= 3)
    
    def check_liberation(self) -> bool:
        """最终解脱判定"""
        if self.role == Role.WIDOW:
            # 寡妇必须经历菩萨状态并渡化至少2位众生才算真正解脱
            return self.bodhisattva_mode and self.beings_saved >= 2
        else:
            return self.check_liberation_condition()
    
    def get_final_score(self) -> float:
        if self.role == Role.MONK:
            base_score = self.grant_points * 2
            # v2.3: 僧侣涅槃加分+40
            if self.check_liberation():
                base_score += 40
        elif self.role == Role.WIDOW:
            resource_bonus = self.get_total_resources() // 2
            base_score = self.merit * 2 + self.reputation * 3 + resource_bonus
            # v2.3: 寡妇得分来自渡化点
            if self.bodhisattva_mode:
                # 菩萨状态：渡化点×5 + 每位众生额外+5
                base_score += self.salvation_points * 5 + self.beings_saved * 5
        elif self.role == Role.FARMER:
            resource_bonus = self.get_total_resources() // 2
            base_score = self.merit * 2 + self.reputation * 3 + resource_bonus
            # v2.3: 农民勤劳加分
            base_score += self.labor_points
            if self.check_liberation():
                base_score += 30
        else:
            resource_bonus = self.get_total_resources() // 2
            base_score = self.merit * 2 + self.reputation * 3 + resource_bonus
            if self.check_liberation():
                base_score += 30
        
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
            elif p.role == Role.FARMER:
                p.grain += 1
                # v2.3: 农民每轮获得勤劳积分
                p.labor_points += 1
            elif p.role == Role.WIDOW:
                if not p.bodhisattva_mode:
                    # 正常状态：偶数回合获得功德
                    if game["current_round"] % 2 == 0:
                        p.merit += 1
                # 菩萨状态在行动阶段处理
            elif p.role == Role.MONK:
                if not p.retreat_mode:
                    p.dharma_power = min(10, p.dharma_power + 1)
                else:
                    p.grant_points += 2
    
    def event_phase(self, game):
        event_type = random.randint(1, 5)
        if event_type == 1:  # Imperial blessing
            for p in game["players"]:
                if p.role == Role.OFFICIAL:
                    p.reputation += 1
                p.merit += 1
        elif event_type == 2:  # Drought
            for p in game["players"]:
                p.grain = max(0, p.grain - 2)
            sorted_players = sorted(game["players"], key=lambda x: x.grain)
            for p in sorted_players[:2]:
                if p.role != Role.MONK:
                    p.grain += 1
        elif event_type == 3:  # Dharma assembly
            participants = 0
            for p in game["players"]:
                if p.role == Role.MONK:
                    continue
                if p.coins >= 2 and random.random() > 0.3:
                    p.coins -= 2
                    p.merit += 1
                    participants += 1
                elif p.role == Role.WIDOW:
                    p.merit += 1
                    participants += 1
            for p in game["players"]:
                if p.role == Role.MONK:
                    p.grant_points += participants
        elif event_type == 4:  # Impermanence
            valid_targets = [p for p in game["players"] if p.life > 1]
            if valid_targets:
                target = random.choice(valid_targets)
                target.life -= 1
                target.awakening_tokens += 1
        else:  # Prosperity
            for p in game["players"]:
                if p.role == Role.MERCHANT:
                    p.coins += 2
    
    def action_phase(self, game):
        for p in game["players"]:
            ap = 3 if p.role == Role.FARMER else 2
            
            # 检查寡妇是否进入菩萨状态
            if p.role == Role.WIDOW and not p.bodhisattva_mode:
                if p.check_liberation_condition():
                    p.bodhisattva_mode = True
                    p.liberation_turn = game["current_round"]
            
            # 僧侣闭关判断
            if p.role == Role.MONK and game["current_round"] >= 8:
                if p.dharma_power <= 3 and p.grant_points >= 10:
                    p.retreat_mode = True
            
            while ap > 0:
                action = self.decide_action(p, game, ap)
                if action == "donate":
                    if p.coins >= 3:
                        p.coins -= 3
                        p.merit += 1
                        if p.role == Role.WIDOW and not p.bodhisattva_mode:
                            p.merit += 1
                        p.reputation += 1
                        for mp in game["players"]:
                            if mp.role == Role.MONK:
                                mp.dharma_power = min(10, mp.dharma_power + 1)
                    ap -= 1
                elif action == "donate_anonymous":
                    if p.coins >= 4:
                        p.coins -= 4
                        p.merit += 1
                        if p.role == Role.WIDOW and not p.bodhisattva_mode:
                            p.merit += 1
                        for mp in game["players"]:
                            if mp.role == Role.MONK:
                                mp.dharma_power = min(10, mp.dharma_power + 1)
                    ap -= 1
                elif action == "trade":
                    if p.grain >= 3:
                        p.grain -= 3
                        p.coins += 3 if p.role == Role.MERCHANT else 2
                elif action == "buy_land":
                    cost = 5 if p.role == Role.LANDLORD else 6
                    if p.coins >= cost and p.land < 5:
                        p.coins -= cost
                        p.land += 1
                    ap -= 1
                elif action == "donate_land":
                    if p.land >= 1:
                        p.land -= 1
                        p.merit += 3
                        p.reputation += 2
                    ap -= 1
                elif action == "transfer":
                    if p.merit >= 2:
                        targets = [t for t in game["players"] if t != p and t.role != Role.MONK]
                        if targets:
                            target = random.choice(targets)
                            transfer = min(2, p.merit - 1)
                            p.merit -= transfer
                            target.merit += transfer
                            p.merit += 1
                    ap -= 1
                elif action == "grant":
                    if p.dharma_power >= 2:
                        targets = [t for t in game["players"] if t != p]
                        if targets:
                            target = random.choice(targets)
                            grant = min(3, p.dharma_power)
                            p.dharma_power -= grant
                            target.merit += grant
                            p.grant_points += grant
                    ap -= 1
                elif action == "use_awakening":
                    p.awakening_tokens -= 1
                    p.merit += 3
                    ap -= 1
                # v2.3: 寡妇菩萨状态专属行动 - 渡众生
                elif action == "save_being":
                    # 选择一个功德较低的众生
                    targets = [t for t in game["players"] 
                              if t != p and t.role != Role.MONK and t.merit < 15]
                    if targets:
                        # 优先选择功德最低的
                        target = min(targets, key=lambda x: x.merit)
                        # 渡化：给予功德
                        merit_given = 3
                        target.merit += merit_given
                        p.salvation_points += merit_given
                        # 检查是否首次渡化此人
                        if not hasattr(p, 'saved_players'):
                            p.saved_players = set()
                        if id(target) not in p.saved_players:
                            p.saved_players.add(id(target))
                            p.beings_saved += 1
                    ap -= 1
                else:
                    break
    
    def decide_action(self, player, game, remaining_ap) -> str:
        actions = []
        
        # v2.3: 寡妇菩萨状态优先渡众生
        if player.role == Role.WIDOW and player.bodhisattva_mode:
            targets = [t for t in game["players"] 
                      if t != player and t.role != Role.MONK and t.merit < 15]
            if targets:
                actions.append("save_being")
                # 菩萨状态下优先渡众生
                if random.random() > 0.3:
                    return "save_being"
        
        if player.coins >= 3 and player.role != Role.MONK:
            actions.append("donate")
            if player.coins >= 4:
                actions.append("donate_anonymous")
        if player.grain >= 3:
            actions.append("trade")
        if player.coins >= 6 and player.land < 5 and player.role not in [Role.WIDOW, Role.MONK]:
            actions.append("buy_land")
        if player.role == Role.LANDLORD and player.land >= 1:
            actions.append("donate_land")
        if player.merit >= 2:
            targets = [t for t in game["players"] if t != player and t.role != Role.MONK]
            if targets:
                actions.append("transfer")
        if player.role == Role.MONK and player.dharma_power >= 2:
            actions.append("grant")
        if player.awakening_tokens > 0:
            actions.append("use_awakening")
        
        if not actions:
            return "none"
        
        # Strategy based on role and game state
        if player.reputation >= 3 and "donate" in actions:
            return "donate"
        if player.role == Role.LANDLORD and game["current_round"] >= 7:
            if "donate_land" in actions and player.get_total_resources() > 8:
                return "donate_land"
        if player.role == Role.OFFICIAL and "donate" in actions and random.random() > 0.3:
            return "donate"
        
        return random.choice(actions)
    
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
            liberation = p.check_liberation()
            score = p.get_final_score()
            
            extra_info = {}
            if p.role == Role.WIDOW:
                extra_info["bodhisattva"] = p.bodhisattva_mode
                extra_info["beings_saved"] = p.beings_saved
                extra_info["salvation_points"] = p.salvation_points
            elif p.role == Role.FARMER:
                extra_info["labor_points"] = p.labor_points
            
            results.append({
                "role": p.role.value,
                "merit": p.merit,
                "reputation": p.reputation,
                "grant_points": p.grant_points if p.role == Role.MONK else 0,
                "final_score": score,
                "liberation": liberation,
                "total_resources": p.get_total_resources(),
                **extra_info
            })
        
        sorted_results = sorted(results, key=lambda x: x["final_score"], reverse=True)
        winner = sorted_results[0]
        
        # 判断胜利类型
        if winner["liberation"]:
            if winner["role"] == "寡妇":
                win_type = "bodhisattva"  # 菩萨道胜利
            elif winner["role"] == "僧侣":
                win_type = "nirvana"  # 涅槃胜利
            else:
                win_type = "liberation"  # 解脱胜利
        else:
            win_type = "standard"
        
        return {"winner": winner["role"], "win_type": win_type, "scores": results}
    
    def run_batch(self, num_games: int) -> Dict:
        role_wins = {role.value: 0 for role in Role}
        role_scores = {role.value: [] for role in Role}
        win_types = {"standard": 0, "liberation": 0, "nirvana": 0, "bodhisattva": 0}
        
        # 额外统计
        widow_bodhisattva_count = 0
        widow_beings_saved = []
        farmer_labor_points = []
        
        for _ in range(num_games):
            result = self.run_game()
            role_wins[result["winner"]] += 1
            win_types[result["win_type"]] += 1
            
            for p in result["scores"]:
                role_scores[p["role"]].append(p["final_score"])
                
                if p["role"] == "寡妇":
                    if p.get("bodhisattva", False):
                        widow_bodhisattva_count += 1
                    widow_beings_saved.append(p.get("beings_saved", 0))
                elif p["role"] == "农民":
                    farmer_labor_points.append(p.get("labor_points", 0))
        
        return {
            "total_games": num_games,
            "role_win_rates": {k: v/num_games*100 for k, v in role_wins.items()},
            "role_avg_scores": {k: sum(v)/len(v) if v else 0 for k, v in role_scores.items()},
            "role_score_std": {k: (sum((x - sum(v)/len(v))**2 for x in v)/len(v))**0.5 if v else 0 
                              for k, v in role_scores.items()},
            "win_types": {k: v/num_games*100 for k, v in win_types.items()},
            "widow_stats": {
                "bodhisattva_rate": widow_bodhisattva_count/num_games*100,
                "avg_beings_saved": sum(widow_beings_saved)/len(widow_beings_saved) if widow_beings_saved else 0
            },
            "farmer_stats": {
                "avg_labor_points": sum(farmer_labor_points)/len(farmer_labor_points) if farmer_labor_points else 0
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
    
    # Save results
    with open("batch_simulation_results_v23.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    # Print summary
    print("\n" + "="*70)
    print("BATCH SIMULATION RESULTS - Path to Salvation v2.3")
    print("(With Bodhisattva Mechanism)")
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
        
        print("\n[Average Scores (Std Dev)]")
        for role in sorted(r["role_avg_scores"].keys(), key=lambda x: r["role_avg_scores"][x], reverse=True):
            avg = r["role_avg_scores"][role]
            std = r["role_score_std"][role]
            print(f"  {role}: {avg:6.1f} (+/- {std:.1f})")
        
        print(f"\n[Victory Types]")
        for vtype, rate in sorted(r["win_types"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {vtype}: {rate:5.1f}%")
        
        print(f"\n[Widow Bodhisattva Stats]")
        print(f"  Bodhisattva Rate: {r['widow_stats']['bodhisattva_rate']:.1f}%")
        print(f"  Avg Beings Saved: {r['widow_stats']['avg_beings_saved']:.2f}")
        
        print(f"\n[Farmer Labor Stats]")
        print(f"  Avg Labor Points: {r['farmer_stats']['avg_labor_points']:.1f}")
    
    print("\n" + "="*70)
    print("Results saved to batch_simulation_results_v23.json")
    
    return all_results

if __name__ == "__main__":
    main()
