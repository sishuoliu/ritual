# -*- coding: utf-8 -*-
"""
《救赎之路》v2.1 AI模拟测试系统
根据v2.0测试结果进行平衡性修正

主要修改：
1. 解脱条件收紧：功德≥20，声望=0，资源≤3
2. 寡妇削弱：哀悼祈福每2轮1功德，回向+1
3. 涅槃放宽：法力≤2，授德点≥15
4. 地主新能力：施田济寺
5. 得分公式调整
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum
import json

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
    retreat_mode: bool = False  # 僧侣闭关状态
    
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
    
    def get_final_score(self) -> float:
        """v2.1得分公式：功德×2 + 声望×2 + 资源÷2"""
        if self.role == Role.MONK:
            return self.grant_points * 2
        else:
            resource_bonus = self.get_total_resources() // 2
            return self.merit * 2 + self.reputation * 2 + resource_bonus
    
    def check_liberation(self) -> bool:
        """v2.1解脱条件：功德≥20，声望=0，资源≤3"""
        if self.role == Role.MONK:
            # 涅槃：法力≤2，授德点≥15
            return self.dharma_power <= 2 and self.grant_points >= 15
        else:
            return (self.merit >= 20 and 
                    self.reputation == 0 and 
                    self.get_total_resources() <= 3)

class GameSimulator:
    def __init__(self, num_games: int = 10):
        self.num_games = num_games
        self.results: List[Dict] = []
        
    def create_game(self):
        roles = list(Role)
        random.shuffle(roles)
        players = [Player(role=role) for role in roles[:6]]
        return {"players": players, "current_round": 1, "events_log": []}
    
    def production_phase(self, game):
        """v2.1生产阶段"""
        for p in game["players"]:
            if p.role == Role.LANDLORD:
                p.grain += p.land
            elif p.role == Role.FARMER:
                p.grain += 1
            elif p.role == Role.WIDOW:
                # v2.1: 每2轮获得1功德
                if game["current_round"] % 2 == 0:
                    p.merit += 1
            elif p.role == Role.MONK:
                if not p.retreat_mode:
                    p.dharma_power = min(10, p.dharma_power + 1)
                else:
                    # 闭关模式：不获得法力，获得授德点
                    p.grant_points += 2
    
    def event_phase(self, game):
        events = [
            self.event_imperial_blessing,
            self.event_drought,
            self.event_dharma_assembly,
            self.event_impermanence,
            self.event_prosperity
        ]
        event = random.choice(events)
        event(game)
    
    def event_imperial_blessing(self, game):
        game["events_log"].append(f"第{game['current_round']}轮：皇帝御笔")
        for p in game["players"]:
            if p.role == Role.OFFICIAL:
                p.reputation += 1
            p.merit += 1
    
    def event_drought(self, game):
        game["events_log"].append(f"第{game['current_round']}轮：江南大旱")
        for p in game["players"]:
            p.grain = max(0, p.grain - 2)
        sorted_players = sorted(game["players"], key=lambda x: x.grain)
        for p in sorted_players[:2]:
            if p.role != Role.MONK:
                p.grain += 1
    
    def event_dharma_assembly(self, game):
        game["events_log"].append(f"第{game['current_round']}轮：盂兰盆法会")
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
    
    def event_impermanence(self, game):
        game["events_log"].append(f"第{game['current_round']}轮：无常来袭")
        target = random.choice([p for p in game["players"] if p.life > 1])
        target.life -= 1
        target.awakening_tokens += 1
    
    def event_prosperity(self, game):
        game["events_log"].append(f"第{game['current_round']}轮：商机来临")
        for p in game["players"]:
            if p.role == Role.MERCHANT:
                p.coins += 2
    
    def action_phase(self, game):
        for p in game["players"]:
            ap = 3 if p.role == Role.FARMER else 2
            
            # 僧侣第8轮后考虑闭关
            if p.role == Role.MONK and game["current_round"] >= 8:
                if p.dharma_power <= 3 and p.grant_points >= 10:
                    p.retreat_mode = True
            
            while ap > 0:
                action = self.decide_action(p, game, ap)
                if action == "donate":
                    self.do_donate(p, game)
                    ap -= 1
                elif action == "donate_anonymous":
                    self.do_donate_anonymous(p, game)
                    ap -= 1
                elif action == "trade":
                    self.do_trade(p)
                elif action == "buy_land":
                    self.do_buy_land(p)
                    ap -= 1
                elif action == "donate_land":
                    self.do_donate_land(p)
                    ap -= 1
                elif action == "transfer":
                    self.do_transfer(p, game)
                    ap -= 1
                elif action == "grant":
                    self.do_grant(p, game)
                    ap -= 1
                elif action == "use_awakening":
                    p.awakening_tokens -= 1
                    p.merit += 3
                    ap -= 1
                else:
                    break
    
    def decide_action(self, player, game, remaining_ap) -> str:
        actions = []
        
        # 普通捐献
        if player.coins >= 3 and player.role != Role.MONK:
            actions.append("donate")
            # 如果声望>0且追求解脱，选择匿名
            if player.reputation > 0 and player.coins >= 4:
                actions.append("donate_anonymous")
        
        if player.grain >= 3:
            actions.append("trade")
        
        if player.coins >= 6 and player.land < 5 and player.role not in [Role.WIDOW, Role.MONK]:
            actions.append("buy_land")
        
        # v2.1 地主施田济寺
        if player.role == Role.LANDLORD and player.land >= 1:
            actions.append("donate_land")
        
        if player.merit >= 2 and player.role != Role.WIDOW:
            targets = [p for p in game["players"] if p != player and p.role != Role.MONK]
            if targets:
                actions.append("transfer")
        
        # 寡妇回向（削弱后仍然+1）
        if player.role == Role.WIDOW and player.merit >= 2:
            targets = [p for p in game["players"] if p != player and p.role != Role.MONK]
            if targets:
                actions.append("transfer")
        
        if player.role == Role.MONK and player.dharma_power >= 2:
            actions.append("grant")
        
        if player.awakening_tokens > 0:
            actions.append("use_awakening")
        
        if not actions:
            return "none"
        
        # 策略选择
        # 地主后期倾向于捐地以达成解脱
        if player.role == Role.LANDLORD and game["current_round"] >= 7:
            if "donate_land" in actions and player.get_total_resources() > 5:
                return "donate_land"
        
        # 追求解脱的角色优先匿名捐献
        if player.reputation > 0 and "donate_anonymous" in actions:
            if random.random() > 0.5:
                return "donate_anonymous"
        
        # 寡妇优先回向
        if player.role == Role.WIDOW and "transfer" in actions:
            if random.random() > 0.4:
                return "transfer"
        
        return random.choice(actions)
    
    def do_donate(self, player, game):
        if player.coins >= 3:
            player.coins -= 3
            player.merit += 1
            if player.role == Role.WIDOW:
                player.merit += 1
            player.reputation += 1  # 获得声望
            for p in game["players"]:
                if p.role == Role.MONK:
                    p.dharma_power = min(10, p.dharma_power + 1)
    
    def do_donate_anonymous(self, player, game):
        """v2.1 匿名捐献：+1铜钱，不获得声望"""
        if player.coins >= 4:
            player.coins -= 4
            player.merit += 1
            if player.role == Role.WIDOW:
                player.merit += 1
            # 不获得声望
            for p in game["players"]:
                if p.role == Role.MONK:
                    p.dharma_power = min(10, p.dharma_power + 1)
    
    def do_donate_land(self, player):
        """v2.1 地主施田济寺"""
        if player.land >= 1:
            player.land -= 1
            player.merit += 3
            player.reputation += 2
    
    def do_trade(self, player):
        if player.grain >= 3:
            player.grain -= 3
            coins_gained = 2
            if player.role == Role.MERCHANT:
                coins_gained = 3
            player.coins += coins_gained
    
    def do_buy_land(self, player):
        cost = 6
        if player.role == Role.LANDLORD:
            cost = 5
        if player.coins >= cost and player.land < 5:
            player.coins -= cost
            player.land += 1
    
    def do_transfer(self, player, game):
        if player.merit < 2:
            return
        targets = [p for p in game["players"] if p != player and p.role != Role.MONK]
        if not targets:
            return
        target = random.choice(targets)
        transfer_amount = min(2, player.merit - 1)
        player.merit -= transfer_amount
        target.merit += transfer_amount
        # v2.1 回向奖励统一为+1
        player.merit += 1
    
    def do_grant(self, player, game):
        if player.dharma_power < 2:
            return
        targets = [p for p in game["players"] if p != player]
        if not targets:
            return
        target = random.choice(targets)
        grant_amount = min(3, player.dharma_power)
        player.dharma_power -= grant_amount
        target.merit += grant_amount
        player.grant_points += grant_amount
    
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
            results.append({
                "role": p.role.value,
                "merit": p.merit,
                "reputation": p.reputation,
                "grant_points": p.grant_points if p.role == Role.MONK else 0,
                "dharma_power": p.dharma_power if p.role == Role.MONK else 0,
                "final_score": score,
                "liberation": liberation,
                "total_resources": p.get_total_resources()
            })
        
        # v2.1 解脱判定：多人达成时比较功德
        liberation_winners = [r for r in results if r["liberation"]]
        if liberation_winners:
            # 按功德排序（僧侣用授德点）
            liberation_winners.sort(
                key=lambda x: x["grant_points"] if x["role"] == "僧侣" else x["merit"],
                reverse=True
            )
            winner = liberation_winners[0]
            winner["win_type"] = "解脱/涅槃"
        else:
            sorted_results = sorted(results, key=lambda x: x["final_score"], reverse=True)
            winner = sorted_results[0]
            winner["win_type"] = "标准胜利"
        
        return {
            "players": results,
            "winner": winner["role"],
            "win_type": winner.get("win_type", "标准胜利"),
            "events": game["events_log"]
        }
    
    def run_simulation(self) -> Dict:
        all_results = []
        role_wins = {role.value: 0 for role in Role}
        role_scores = {role.value: [] for role in Role}
        liberation_count = 0
        standard_count = 0
        
        for i in range(self.num_games):
            result = self.run_game()
            all_results.append(result)
            
            winner = result["winner"]
            role_wins[winner] += 1
            
            if "解脱" in result["win_type"] or "涅槃" in result["win_type"]:
                liberation_count += 1
            else:
                standard_count += 1
            
            for p in result["players"]:
                role_scores[p["role"]].append(p["final_score"])
        
        analysis = {
            "version": "v2.1",
            "total_games": self.num_games,
            "role_win_rates": {k: v/self.num_games*100 for k, v in role_wins.items()},
            "role_avg_scores": {k: sum(v)/len(v) if v else 0 for k, v in role_scores.items()},
            "liberation_rate": liberation_count/self.num_games*100,
            "standard_rate": standard_count/self.num_games*100,
            "detailed_results": all_results
        }
        
        return analysis

def main():
    print("="*60)
    print("《救赎之路》v2.1 AI模拟测试")
    print("="*60)
    print()
    
    simulator = GameSimulator(num_games=10)
    results = simulator.run_simulation()
    
    print("[胜率统计]")
    print("-"*40)
    for role, rate in sorted(results["role_win_rates"].items(), 
                             key=lambda x: x[1], reverse=True):
        print(f"  {role}: {rate:.1f}%")
    
    print()
    print("[平均得分]")
    print("-"*40)
    for role, score in sorted(results["role_avg_scores"].items(), 
                              key=lambda x: x[1], reverse=True):
        print(f"  {role}: {score:.1f}")
    
    print()
    print(f"[解脱/涅槃胜利率] {results['liberation_rate']:.1f}%")
    print(f"[标准胜利率] {results['standard_rate']:.1f}%")
    
    print()
    print("[每局详情]")
    print("-"*40)
    for i, game in enumerate(results["detailed_results"], 1):
        print(f"  第{i}局: 胜者={game['winner']} ({game['win_type']})")
    
    with open("simulation_results_v21.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print()
    print("完整结果已保存至 simulation_results_v21.json")
    
    return results

if __name__ == "__main__":
    main()
