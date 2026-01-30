# -*- coding: utf-8 -*-
"""
《救赎之路》v2.4 大规模模拟测试
核心理念：每个角色拥有独特的"道"——专属胜利路径

六道系统：
1. 寡妇 - 菩萨道：发大愿，渡众生
2. 僧侣 - 涅槃道：授法度人，法力归零
3. 富商 - 善财道：散尽家财，功德圆满
4. 地主 - 舍宅道：捐献祖产，兴建寺院
5. 官员 - 清官道：致仕归隐，为民请命
6. 农民 - 勤劳道：质朴修行，日行一善

v2.4核心设计：
- 每个角色都有独特的终极行动和胜利加分
- 弱势角色（农民、官员）获得强力专属机制
- 强势角色（寡妇、地主）的专属机制需要更多投入
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
    
    # ===== 各角色专属状态 =====
    
    # 寡妇·菩萨道
    bodhisattva_mode: bool = False
    liberation_turn: int = 0
    salvation_points: int = 0
    beings_saved: int = 0
    saved_players: Set = field(default_factory=set)
    
    # 富商·善财道
    charity_mode: bool = False  # 散财模式
    total_donated: int = 0  # 累计捐献金额
    shanchi_enlightenment: bool = False  # 善财悟道
    
    # 地主·舍宅道
    temple_built: bool = False  # 是否已建寺
    land_donated: int = 0  # 累计捐献土地
    legacy_points: int = 0  # 传承点
    
    # 官员·清官道
    retired: bool = False  # 是否已致仕
    petitions: int = 0  # 为民请命次数
    reputation_sacrificed: int = 0  # 主动放弃的声望
    
    # 农民·勤劳道
    labor_points: int = 0  # 勤劳积分
    daily_good_deeds: int = 0  # 日行一善次数
    harvest_shared: int = 0  # 分享收成次数
    
    def __post_init__(self):
        if self.role == Role.MERCHANT:
            self.grain, self.coins, self.land = 2, 6, 0
        elif self.role == Role.LANDLORD:
            self.grain, self.coins, self.land = 3, 2, 2
        elif self.role == Role.OFFICIAL:
            self.grain, self.coins, self.land = 2, 4, 1
            self.reputation = 2  # 官员初始有声望
        elif self.role == Role.FARMER:
            self.grain, self.coins, self.land = 4, 2, 0
            self.action_points = 3
        elif self.role == Role.WIDOW:
            self.grain, self.coins, self.land, self.merit = 2, 2, 0, 2
        elif self.role == Role.MONK:
            self.dharma_power = 5
    
    def get_total_resources(self) -> int:
        return self.grain + self.coins + self.land * 5
    
    def check_path_completion(self) -> tuple:
        """检查是否完成专属道路，返回(是否完成, 道路名称, 加分)"""
        if self.role == Role.WIDOW:
            # 菩萨道：渡化≥3人
            if self.bodhisattva_mode and self.beings_saved >= 3:
                return (True, "菩萨道", 35)
            elif self.bodhisattva_mode and self.beings_saved >= 2:
                return (True, "菩萨道（小成）", 20)
            return (False, "", 0)
            
        elif self.role == Role.MONK:
            # 涅槃道：法力≤2，授德点≥15
            if self.dharma_power <= 2 and self.grant_points >= 15:
                return (True, "涅槃道", 40)
            return (False, "", 0)
            
        elif self.role == Role.MERCHANT:
            # 善财道：累计捐献≥20，且当前金钱≤3
            if self.total_donated >= 20 and self.coins <= 3:
                return (True, "善财道", 45)
            elif self.total_donated >= 15:
                return (True, "善财道（小成）", 25)
            return (False, "", 0)
            
        elif self.role == Role.LANDLORD:
            # 舍宅道：累计捐献土地≥3，且建寺
            if self.land_donated >= 3 and self.temple_built:
                return (True, "舍宅道", 50)
            elif self.land_donated >= 2:
                return (True, "舍宅道（小成）", 25)
            return (False, "", 0)
            
        elif self.role == Role.OFFICIAL:
            # 清官道：致仕 + 为民请命≥3次
            if self.retired and self.petitions >= 3:
                return (True, "清官道", 55)
            elif self.retired and self.petitions >= 2:
                return (True, "清官道（小成）", 30)
            return (False, "", 0)
            
        elif self.role == Role.FARMER:
            # 勤劳道：日行一善≥5次 + 分享收成≥3次
            if self.daily_good_deeds >= 5 and self.harvest_shared >= 3:
                return (True, "勤劳道", 50)
            elif self.daily_good_deeds >= 3 or self.harvest_shared >= 2:
                return (True, "勤劳道（小成）", 25)
            return (False, "", 0)
        
        return (False, "", 0)
    
    def get_final_score(self) -> float:
        # 基础分
        if self.role == Role.MONK:
            base_score = self.grant_points * 2
        else:
            resource_bonus = self.get_total_resources() // 2
            base_score = self.merit * 2 + self.reputation * 2 + resource_bonus
        
        # 专属道路加分
        path_complete, path_name, path_bonus = self.check_path_completion()
        if path_complete:
            base_score += path_bonus
        
        # 额外专属加分
        if self.role == Role.FARMER:
            base_score += self.labor_points  # 勤劳积分
        elif self.role == Role.WIDOW and self.bodhisattva_mode:
            base_score += self.salvation_points * 2  # 渡化点
        elif self.role == Role.MERCHANT:
            base_score += self.total_donated // 2  # 捐献奖励
        elif self.role == Role.LANDLORD:
            base_score += self.legacy_points  # 传承点
        elif self.role == Role.OFFICIAL:
            base_score += self.petitions * 3  # 请命奖励
        
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
                # 地主传承点：每轮+土地数÷2
                p.legacy_points += p.land // 2
            elif p.role == Role.FARMER:
                p.grain += 1
                p.labor_points += 1
            elif p.role == Role.WIDOW:
                if not p.bodhisattva_mode and game["current_round"] % 2 == 0:
                    p.merit += 1
            elif p.role == Role.MONK:
                if not p.retreat_mode:
                    p.dharma_power = min(10, p.dharma_power + 1)
                else:
                    p.grant_points += 2
            elif p.role == Role.OFFICIAL:
                # 官员每轮+1声望（除非已致仕）
                if not p.retired:
                    p.reputation += 1
    
    def event_phase(self, game):
        event_type = random.randint(1, 6)
        
        if event_type == 1:  # 皇恩浩荡
            for p in game["players"]:
                if p.role == Role.OFFICIAL and not p.retired:
                    p.reputation += 1
                p.merit += 1
                
        elif event_type == 2:  # 天灾旱荒
            for p in game["players"]:
                p.grain = max(0, p.grain - 2)
            # 官员可选择为民请命
            for p in game["players"]:
                if p.role == Role.OFFICIAL and not p.retired:
                    if p.reputation >= 2 and random.random() > 0.3:
                        p.reputation -= 1
                        p.petitions += 1
                        p.merit += 2
                        # 救济灾民
                        farmers = [x for x in game["players"] if x.role == Role.FARMER]
                        for f in farmers:
                            f.grain += 2
                            
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
                    p.coins += 2
    
    def action_phase(self, game):
        for p in game["players"]:
            ap = 3 if p.role == Role.FARMER else 2
            
            # 检查状态转换
            self.check_state_transitions(p, game)
            
            while ap > 0:
                action = self.decide_action(p, game, ap)
                ap = self.execute_action(p, game, action, ap)
    
    def check_state_transitions(self, p, game):
        """检查并触发状态转换"""
        # 寡妇菩萨状态
        if p.role == Role.WIDOW and not p.bodhisattva_mode:
            if (p.merit >= 20 and p.reputation == 0 and 
                p.get_total_resources() <= 5):
                p.bodhisattva_mode = True
                p.liberation_turn = game["current_round"]
        
        # 僧侣闭关
        if p.role == Role.MONK and game["current_round"] >= 7:
            if p.dharma_power <= 4 and p.grant_points >= 8:
                p.retreat_mode = True
        
        # 官员致仕判断（后期可选择）
        if p.role == Role.OFFICIAL and game["current_round"] >= 6:
            if not p.retired and p.reputation >= 5 and p.petitions >= 2:
                if random.random() > 0.5:
                    p.retired = True
                    p.merit += p.reputation  # 致仕时声望转化为功德
                    p.reputation = 0
        
        # 富商善财模式
        if p.role == Role.MERCHANT and not p.charity_mode:
            if p.total_donated >= 10:
                p.charity_mode = True
    
    def execute_action(self, p, game, action, ap) -> int:
        """执行行动，返回剩余行动点"""
        
        if action == "none":
            return 0
        
        # ===== 通用行动 =====
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
                p.merit += 1
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
                p.coins += 3 if p.role == Role.MERCHANT else 2
            return ap
            
        elif action == "buy_land":
            cost = 5 if p.role == Role.LANDLORD else 6
            if p.coins >= cost and p.land < 5:
                p.coins -= cost
                p.land += 1
            return ap - 1
        
        # ===== 寡妇·菩萨道专属 =====
        elif action == "save_being":
            targets = [t for t in game["players"] 
                      if t != p and t.role != Role.MONK and t.merit < 18]
            if targets:
                target = min(targets, key=lambda x: x.merit)
                merit_given = 3
                target.merit += merit_given
                p.salvation_points += merit_given
                if id(target) not in p.saved_players:
                    p.saved_players.add(id(target))
                    p.beings_saved += 1
            return ap - 1
        
        # ===== 僧侣·涅槃道专属 =====
        elif action == "grant":
            if p.dharma_power >= 2:
                targets = [t for t in game["players"] if t != p]
                if targets:
                    target = random.choice(targets)
                    grant = min(3, p.dharma_power)
                    p.dharma_power -= grant
                    target.merit += grant
                    p.grant_points += grant
            return ap - 1
        
        # ===== 富商·善财道专属 =====
        elif action == "grand_charity":
            # 大布施：一次性捐献大量金钱
            if p.coins >= 6:
                donation = min(p.coins - 1, 8)
                p.coins -= donation
                p.total_donated += donation
                p.merit += donation // 2
                # 散财给所有人
                for other in game["players"]:
                    if other != p and other.role != Role.MONK:
                        other.coins += 1
            return ap - 1
        
        # ===== 地主·舍宅道专属 =====
        elif action == "donate_land":
            if p.land >= 1:
                p.land -= 1
                p.land_donated += 1
                p.merit += 3
                p.reputation += 1
                # 检查是否可建寺
                if p.land_donated >= 2 and not p.temple_built:
                    p.temple_built = True
                    p.merit += 5  # 建寺功德
            return ap - 1
            
        elif action == "build_temple":
            # 直接捐2块地建寺
            if p.land >= 2 and not p.temple_built:
                p.land -= 2
                p.land_donated += 2
                p.temple_built = True
                p.merit += 10
            return ap - 1
        
        # ===== 官员·清官道专属 =====
        elif action == "petition":
            # 为民请命：消耗声望，获得功德，帮助弱势
            if p.reputation >= 2:
                p.reputation -= 1
                p.reputation_sacrificed += 1
                p.petitions += 1
                p.merit += 2
                # 帮助功德最低的玩家
                targets = [t for t in game["players"] 
                          if t != p and t.role not in [Role.MONK, Role.OFFICIAL]]
                if targets:
                    target = min(targets, key=lambda x: x.merit)
                    target.merit += 1
            return ap - 1
            
        elif action == "retire":
            # 致仕归隐
            if not p.retired and p.reputation >= 3:
                p.merit += p.reputation
                p.retired = True
                p.reputation = 0
            return ap - 1
        
        # ===== 农民·勤劳道专属 =====
        elif action == "daily_good":
            # 日行一善：消耗少量资源获得功德
            if p.grain >= 1:
                p.grain -= 1
                p.merit += 1
                p.daily_good_deeds += 1
            return ap - 1
            
        elif action == "share_harvest":
            # 分享收成：给其他玩家粮食
            if p.grain >= 3:
                p.grain -= 2
                targets = [t for t in game["players"] 
                          if t != p and t.role != Role.MONK]
                if targets:
                    target = min(targets, key=lambda x: x.grain)
                    target.grain += 2
                    p.merit += 1
                    p.harvest_shared += 1
            return ap - 1
        
        elif action == "use_awakening":
            if p.awakening_tokens > 0:
                p.awakening_tokens -= 1
                p.merit += 3
            return ap - 1
        
        return ap - 1
    
    def decide_action(self, player, game, remaining_ap) -> str:
        """AI决策逻辑"""
        actions = []
        p = player
        round_num = game["current_round"]
        
        # ===== 寡妇决策 =====
        if p.role == Role.WIDOW:
            if p.bodhisattva_mode:
                targets = [t for t in game["players"] 
                          if t != p and t.role != Role.MONK and t.merit < 18]
                if targets:
                    actions.append(("save_being", 0.8))  # 高优先级渡众生
            if p.coins >= 4:
                actions.append(("donate_anonymous", 0.4))
            if p.coins >= 3:
                actions.append(("donate", 0.3))
        
        # ===== 僧侣决策 =====
        elif p.role == Role.MONK:
            if p.dharma_power >= 3:
                actions.append(("grant", 0.7))
            elif p.dharma_power >= 2:
                actions.append(("grant", 0.5))
        
        # ===== 富商决策 =====
        elif p.role == Role.MERCHANT:
            if p.charity_mode and p.coins >= 6:
                actions.append(("grand_charity", 0.7))
            if p.coins >= 4:
                actions.append(("donate_anonymous", 0.4))
            if p.coins >= 3:
                actions.append(("donate", 0.3))
            if p.grain >= 3:
                actions.append(("trade", 0.5))
        
        # ===== 地主决策 =====
        elif p.role == Role.LANDLORD:
            if p.land >= 2 and not p.temple_built and round_num >= 5:
                actions.append(("build_temple", 0.6))
            if p.land >= 1 and round_num >= 6:
                actions.append(("donate_land", 0.5))
            if p.coins >= 5 and p.land < 4:
                actions.append(("buy_land", 0.4))
            if p.coins >= 3:
                actions.append(("donate", 0.2))
        
        # ===== 官员决策 =====
        elif p.role == Role.OFFICIAL:
            if p.reputation >= 4 and not p.retired:
                actions.append(("petition", 0.6))
            if p.reputation >= 5 and round_num >= 7 and not p.retired:
                actions.append(("retire", 0.5))
            if p.reputation >= 2:
                actions.append(("petition", 0.4))
            if p.coins >= 4:
                actions.append(("donate_anonymous", 0.3))
        
        # ===== 农民决策 =====
        elif p.role == Role.FARMER:
            if p.grain >= 4:
                actions.append(("share_harvest", 0.6))
            if p.grain >= 2:
                actions.append(("daily_good", 0.5))
            if p.grain >= 3:
                actions.append(("trade", 0.3))
            if p.coins >= 3:
                actions.append(("donate", 0.2))
        
        # 通用行动
        if p.awakening_tokens > 0:
            actions.append(("use_awakening", 0.8))
        
        if not actions:
            return "none"
        
        # 按优先级选择
        actions.sort(key=lambda x: x[1], reverse=True)
        
        # 有一定随机性
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
    
    with open("batch_simulation_results_v24.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*70)
    print("BATCH SIMULATION RESULTS - Path to Salvation v2.4")
    print("(Six Paths System)")
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
    print("Results saved to batch_simulation_results_v24.json")
    
    return all_results

if __name__ == "__main__":
    main()
