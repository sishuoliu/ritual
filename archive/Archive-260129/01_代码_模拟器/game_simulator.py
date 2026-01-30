# -*- coding: utf-8 -*-
"""
《救赎之路》v2.0 AI模拟测试系统
Path to Salvation v2.0 AI Simulation System

模拟6个AI玩家进行10局游戏，分析游戏平衡性
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
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
    """玩家类"""
    role: Role
    grain: int = 0
    coins: int = 0
    land: int = 0
    merit: int = 0
    reputation: int = 0
    dharma_power: int = 0  # 法力（僧侣专属）
    grant_points: int = 0  # 授德点（僧侣专属）
    life: int = 10
    action_points: int = 2
    awakening_tokens: int = 0  # 觉悟token
    
    def __post_init__(self):
        """根据角色设置初始资源"""
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
        """计算总资源价值"""
        return self.grain + self.coins + self.land * 5
    
    def get_final_score(self) -> float:
        """计算最终得分"""
        if self.role == Role.MONK:
            return self.grant_points * 2
        else:
            resource_bonus = self.get_total_resources() // 3
            return self.merit * 3 + self.reputation + resource_bonus
    
    def check_liberation(self) -> bool:
        """检查是否达成解脱"""
        if self.role == Role.MONK:
            return self.dharma_power == 0 and self.grant_points >= 12
        else:
            return self.merit >= 12 and self.reputation <= 3 and self.get_total_resources() <= 5

class AIStrategy(Enum):
    """AI策略类型"""
    AGGRESSIVE = "激进型"  # 早期大量捐献
    BALANCED = "平衡型"    # 均衡发展
    HOARDING = "囤积型"    # 先积累后捐献
    LIBERATION = "解脱型"  # 追求解脱胜利
    SOCIAL = "社交型"      # 重视回向和互动

@dataclass
class GameState:
    """游戏状态"""
    players: List[Player]
    current_round: int = 1
    total_rounds: int = 10
    events_log: List[str] = field(default_factory=list)
    
class GameSimulator:
    """游戏模拟器"""
    
    def __init__(self, num_games: int = 10):
        self.num_games = num_games
        self.results: List[Dict] = []
        
    def create_game(self) -> GameState:
        """创建新游戏"""
        roles = list(Role)
        random.shuffle(roles)
        players = [Player(role=role) for role in roles[:6]]
        return GameState(players=players)
    
    def assign_strategy(self, player: Player) -> AIStrategy:
        """为玩家分配AI策略"""
        if player.role == Role.MONK:
            return random.choice([AIStrategy.BALANCED, AIStrategy.LIBERATION])
        elif player.role == Role.WIDOW:
            return random.choice([AIStrategy.SOCIAL, AIStrategy.LIBERATION])
        elif player.role == Role.MERCHANT:
            return random.choice([AIStrategy.AGGRESSIVE, AIStrategy.BALANCED])
        elif player.role == Role.LANDLORD:
            return random.choice([AIStrategy.HOARDING, AIStrategy.BALANCED])
        else:
            return random.choice(list(AIStrategy))
    
    def production_phase(self, game: GameState):
        """生产阶段"""
        for p in game.players:
            if p.role == Role.LANDLORD:
                p.grain += p.land  # 每块土地产1粮
            elif p.role == Role.FARMER:
                p.grain += 1
            elif p.role == Role.WIDOW:
                p.merit += 1  # 哀悼祈福
            elif p.role == Role.MONK:
                p.dharma_power = min(10, p.dharma_power + 1)  # 冥想
    
    def event_phase(self, game: GameState):
        """事件阶段"""
        events = [
            self.event_imperial_blessing,
            self.event_drought,
            self.event_dharma_assembly,
            self.event_impermanence,
            self.event_prosperity
        ]
        event = random.choice(events)
        event(game)
    
    def event_imperial_blessing(self, game: GameState):
        """皇帝赐福"""
        game.events_log.append(f"第{game.current_round}轮：皇帝御笔")
        for p in game.players:
            if p.role == Role.OFFICIAL:
                p.reputation += 1
            p.merit += 1
    
    def event_drought(self, game: GameState):
        """江南大旱"""
        game.events_log.append(f"第{game.current_round}轮：江南大旱")
        # 所有人粮食-2
        for p in game.players:
            p.grain = max(0, p.grain - 2)
        # 粮食最少的2人获得救济
        sorted_players = sorted(game.players, key=lambda x: x.grain)
        for p in sorted_players[:2]:
            if p.role != Role.MONK:
                p.grain += 1
    
    def event_dharma_assembly(self, game: GameState):
        """盂兰盆法会"""
        game.events_log.append(f"第{game.current_round}轮：盂兰盆法会")
        participants = 0
        for p in game.players:
            if p.role == Role.MONK:
                continue
            # 随机决定是否参加（根据铜钱数量）
            if p.coins >= 2 and random.random() > 0.3:
                p.coins -= 2
                p.merit += 1
                participants += 1
            elif p.role == Role.WIDOW:  # 寡妇免费
                p.merit += 1
                participants += 1
        # 僧侣获得授德点
        for p in game.players:
            if p.role == Role.MONK:
                p.grant_points += participants
    
    def event_impermanence(self, game: GameState):
        """无常来袭"""
        game.events_log.append(f"第{game.current_round}轮：无常来袭")
        # 随机选择一人
        target = random.choice([p for p in game.players if p.life > 1])
        target.life -= 1
        target.awakening_tokens += 1  # 觉悟token
    
    def event_prosperity(self, game: GameState):
        """商机来临"""
        game.events_log.append(f"第{game.current_round}轮：商机来临")
        for p in game.players:
            if p.role == Role.MERCHANT:
                p.coins += 2
    
    def action_phase(self, game: GameState):
        """行动阶段"""
        for p in game.players:
            strategy = self.assign_strategy(p)
            ap = 3 if p.role == Role.FARMER else 2
            
            while ap > 0:
                action = self.decide_action(p, game, strategy, ap)
                if action == "donate":
                    self.do_donate(p, game)
                    ap -= 1
                elif action == "trade":
                    self.do_trade(p)
                    # 交易不消耗AP
                elif action == "buy_land":
                    self.do_buy_land(p)
                    ap -= 1
                elif action == "transfer":
                    self.do_transfer(p, game)
                    ap -= 1
                elif action == "grant" and p.role == Role.MONK:
                    self.do_grant(p, game)
                    ap -= 1
                elif action == "use_awakening":
                    p.awakening_tokens -= 1
                    p.merit += 3
                    ap -= 1
                else:
                    break  # 无有效行动
    
    def decide_action(self, player: Player, game: GameState, 
                      strategy: AIStrategy, remaining_ap: int) -> str:
        """决定行动"""
        actions = []
        
        # 可用行动检查
        if player.coins >= 3 and player.role != Role.MONK:
            actions.append("donate")
        if player.grain >= 3:
            actions.append("trade")  # 卖粮换钱
        if player.coins >= 6 and player.land < 5 and player.role not in [Role.WIDOW, Role.MONK]:
            actions.append("buy_land")
        if player.merit >= 2 and len([p for p in game.players if p != player and p.role != Role.MONK]) > 0:
            actions.append("transfer")
        if player.role == Role.MONK and player.dharma_power >= 2:
            actions.append("grant")
        if player.awakening_tokens > 0:
            actions.append("use_awakening")
        
        if not actions:
            return "none"
        
        # 根据策略选择
        if strategy == AIStrategy.AGGRESSIVE:
            if "donate" in actions:
                return "donate"
        elif strategy == AIStrategy.HOARDING:
            if game.current_round < 6:
                if "buy_land" in actions:
                    return "buy_land"
                if "trade" in actions:
                    return "trade"
            else:
                if "donate" in actions:
                    return "donate"
        elif strategy == AIStrategy.LIBERATION:
            if "donate" in actions and player.reputation <= 3:
                return "donate"
            if "transfer" in actions:
                return "transfer"
        elif strategy == AIStrategy.SOCIAL:
            if "transfer" in actions:
                return "transfer"
        
        return random.choice(actions)
    
    def do_donate(self, player: Player, game: GameState):
        """捐献"""
        if player.coins >= 3:
            player.coins -= 3
            player.merit += 1
            if player.role == Role.WIDOW:
                player.merit += 1  # 虔诚+1
            # 随机获得声望（非匿名）
            if random.random() > 0.3:
                player.reputation += 1
            # 僧侣获得法力
            for p in game.players:
                if p.role == Role.MONK:
                    p.dharma_power = min(10, p.dharma_power + 1)
    
    def do_trade(self, player: Player):
        """交易（卖粮换钱）"""
        if player.grain >= 3:
            player.grain -= 3
            coins_gained = 2
            if player.role == Role.MERCHANT:
                coins_gained = 3  # 富商交易加成
            player.coins += coins_gained
    
    def do_buy_land(self, player: Player):
        """购买土地"""
        cost = 6
        if player.role == Role.LANDLORD:
            cost = 5
        if player.coins >= cost and player.land < 5:
            player.coins -= cost
            player.land += 1
    
    def do_transfer(self, player: Player, game: GameState):
        """回向功德"""
        if player.merit < 2:
            return
        # 选择回向对象（随机）
        targets = [p for p in game.players if p != player and p.role != Role.MONK]
        if not targets:
            return
        target = random.choice(targets)
        transfer_amount = min(2, player.merit - 1)  # 保留1点
        player.merit -= transfer_amount
        target.merit += transfer_amount
        # 回向奖励
        if player.role == Role.WIDOW:
            player.merit += 2
        else:
            player.merit += 1
    
    def do_grant(self, player: Player, game: GameState):
        """僧侣授德"""
        if player.dharma_power < 2:
            return
        # 选择授德对象
        targets = [p for p in game.players if p != player]
        if not targets:
            return
        target = random.choice(targets)
        grant_amount = min(3, player.dharma_power)
        player.dharma_power -= grant_amount
        target.merit += grant_amount
        player.grant_points += grant_amount
    
    def aging_phase(self, game: GameState):
        """衰老阶段"""
        for p in game.players:
            p.life -= 1
    
    def run_game(self) -> Dict:
        """运行一局游戏"""
        game = self.create_game()
        
        for round_num in range(1, 11):
            game.current_round = round_num
            
            self.production_phase(game)
            self.event_phase(game)
            self.action_phase(game)
            self.aging_phase(game)
        
        # 计算结果
        results = []
        for p in game.players:
            liberation = p.check_liberation()
            score = p.get_final_score()
            results.append({
                "role": p.role.value,
                "merit": p.merit,
                "reputation": p.reputation,
                "grant_points": p.grant_points if p.role == Role.MONK else 0,
                "final_score": score,
                "liberation": liberation,
                "total_resources": p.get_total_resources()
            })
        
        # 确定胜者
        # 先检查解脱/涅槃
        liberation_winners = [r for r in results if r["liberation"]]
        if liberation_winners:
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
            "events": game.events_log
        }
    
    def run_simulation(self) -> Dict:
        """运行多局模拟"""
        all_results = []
        role_wins = {role.value: 0 for role in Role}
        role_scores = {role.value: [] for role in Role}
        liberation_count = 0
        
        for i in range(self.num_games):
            result = self.run_game()
            all_results.append(result)
            
            winner = result["winner"]
            role_wins[winner] += 1
            
            if result["win_type"] in ["解脱/涅槃", "解脱", "涅槃"]:
                liberation_count += 1
            
            for p in result["players"]:
                role_scores[p["role"]].append(p["final_score"])
        
        # 统计分析
        analysis = {
            "total_games": self.num_games,
            "role_win_rates": {k: v/self.num_games*100 for k, v in role_wins.items()},
            "role_avg_scores": {k: sum(v)/len(v) if v else 0 for k, v in role_scores.items()},
            "liberation_rate": liberation_count/self.num_games*100,
            "detailed_results": all_results
        }
        
        return analysis

def main():
    """主函数"""
    print("="*60)
    print("《救赎之路》v2.0 AI模拟测试")
    print("="*60)
    print()
    
    simulator = GameSimulator(num_games=10)
    results = simulator.run_simulation()
    
    print("【胜率统计】")
    print("-"*40)
    for role, rate in sorted(results["role_win_rates"].items(), 
                             key=lambda x: x[1], reverse=True):
        print(f"  {role}: {rate:.1f}%")
    
    print()
    print("【平均得分】")
    print("-"*40)
    for role, score in sorted(results["role_avg_scores"].items(), 
                              key=lambda x: x[1], reverse=True):
        print(f"  {role}: {score:.1f}分")
    
    print()
    print(f"【解脱/涅槃达成率】{results['liberation_rate']:.1f}%")
    
    print()
    print("【每局详情】")
    print("-"*40)
    for i, game in enumerate(results["detailed_results"], 1):
        print(f"第{i}局: 胜者={game['winner']} ({game['win_type']})")
    
    # 保存完整结果
    with open("simulation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print()
    print("完整结果已保存至 simulation_results.json")
    
    return results

if __name__ == "__main__":
    main()
