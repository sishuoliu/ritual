# -*- coding: utf-8 -*-
"""
救赎之路 v5.0 模拟器 - 简化重构版
- 4种资源（财富/功德/影响/土地）
- 6种角色，统一行动系统
- 统一道路难度
- 增强互动（竞标/交易模拟）
"""

import random
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import time

# ═══════════════════════════════════════════════════════════════════
#                           枚举与常量
# ═══════════════════════════════════════════════════════════════════

class Role(Enum):
    SANGHA = "僧伽"
    MERCHANT = "商贾"
    LANDOWNER = "地主"
    SCHOLAR = "文士"
    PEASANT = "农夫"
    DEVOTEE = "信女"

PLAYER_CONFIG = {
    3: [Role.SANGHA, Role.MERCHANT, Role.PEASANT],
    4: [Role.SANGHA, Role.MERCHANT, Role.PEASANT, Role.LANDOWNER],
    5: [Role.SANGHA, Role.MERCHANT, Role.PEASANT, Role.LANDOWNER, Role.DEVOTEE],
    6: [Role.SANGHA, Role.MERCHANT, Role.PEASANT, Role.LANDOWNER, Role.DEVOTEE, Role.SCHOLAR],
}

class ScoreSource(Enum):
    MECHANISM = "机制"
    EVENT = "事件"
    INTERACTION = "互动"
    PATH = "道路"
    AUCTION = "竞标"

# ═══════════════════════════════════════════════════════════════════
#                           事件卡定义 (30张)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class EventCard:
    id: int
    name: str
    category: str
    copies: int

EVENT_CARDS = [
    # 天象类 6张
    EventCard(1, "丰年", "天象", 2),
    EventCard(2, "祥瑞", "天象", 2),
    EventCard(3, "灾异", "天象", 2),
    # 法会类 6张
    EventCard(4, "盂兰盆会", "法会", 2),
    EventCard(5, "讲经法会", "法会", 2),
    EventCard(6, "忏悔法会", "法会", 2),
    # 世俗类 6张
    EventCard(7, "商队", "世俗", 2),
    EventCard(8, "科举", "世俗", 2),
    EventCard(9, "集市", "世俗", 2),
    # 灾难类 6张
    EventCard(10, "旱灾", "灾难", 2),
    EventCard(11, "盗匪", "灾难", 2),
    EventCard(12, "瘟疫", "灾难", 2),
    # 机缘类 6张
    EventCard(13, "高僧", "机缘", 2),
    EventCard(14, "顿悟", "机缘", 2),
    EventCard(15, "福报", "机缘", 2),
]

def build_event_deck() -> List[EventCard]:
    deck = []
    for card in EVENT_CARDS:
        for _ in range(card.copies):
            deck.append(card)
    random.shuffle(deck)
    return deck

# ═══════════════════════════════════════════════════════════════════
#                           玩家类
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Player:
    role: Role
    player_id: int
    num_players: int = 6
    
    # 4种资源
    wealth: int = 0      # 财富
    merit: int = 0       # 功德
    influence: int = 0   # 影响
    land: int = 0        # 土地
    
    action_points: int = 2
    
    # 道路追踪
    total_donated: int = 0       # 累计布施财富
    kindness_count: int = 0      # 善行次数
    kindness_targets: Set = field(default_factory=set)  # 善行对象
    transfer_count: int = 0      # 回向次数
    transfer_targets: Set = field(default_factory=set)  # 回向对象
    farming_count: int = 0       # 耕作次数
    land_donated: int = 0        # 捐地数量
    has_built_temple: bool = False
    
    # 竞标统计
    auction_wins: int = 0
    
    # 得分来源追踪
    score_sources: Dict = field(default_factory=lambda: {
        ScoreSource.MECHANISM: 0,
        ScoreSource.EVENT: 0,
        ScoreSource.INTERACTION: 0,
        ScoreSource.PATH: 0,
        ScoreSource.AUCTION: 0,
    })
    
    def __post_init__(self):
        """根据角色设置初始资源"""
        if self.role == Role.SANGHA:
            self.wealth = 2
            self.merit = 3
            self.influence = 6
            self.land = 0
            self.action_points = 2
        elif self.role == Role.MERCHANT:
            self.wealth = 10
            self.merit = 1
            self.influence = 2
            self.land = 0
            self.action_points = 2
        elif self.role == Role.LANDOWNER:
            self.wealth = 4
            self.merit = 1
            self.influence = 2
            self.land = 3
            self.action_points = 2
        elif self.role == Role.SCHOLAR:
            self.wealth = 4
            self.merit = 2
            self.influence = 4
            self.land = 0
            self.action_points = 2
        elif self.role == Role.PEASANT:
            self.wealth = 6
            self.merit = 1
            self.influence = 1
            self.land = 1
            self.action_points = 3
        elif self.role == Role.DEVOTEE:
            self.wealth = 4
            self.merit = 4
            self.influence = 2
            self.land = 0
            self.action_points = 2
    
    def add_merit(self, amount: int, source: ScoreSource):
        self.merit += amount
        self.score_sources[source] += amount * 2
    
    def check_path_completion(self, num_players: int) -> Tuple[bool, str, int]:
        """检查道路完成情况 - 统一难度"""
        # 人数调整系数
        path_multiplier = 1.0
        if num_players == 3:
            path_multiplier = 1.3
        elif num_players == 6:
            path_multiplier = 0.9
        
        base_bonus = 25
        small_bonus = 12
        
        if self.role == Role.SANGHA:
            # 涅槃道：消耗8影响 + 曾对3位不同玩家回向
            if len(self.transfer_targets) >= 3:
                return (True, "涅槃道", int(base_bonus * path_multiplier))
            elif len(self.transfer_targets) >= 2:
                return (True, "涅槃道（小成）", int(small_bonus * path_multiplier))
        
        elif self.role == Role.MERCHANT:
            # 善财道：累计布施≥15 + 影响≥4
            if self.total_donated >= 15 and self.influence >= 4:
                return (True, "善财道", int(base_bonus * path_multiplier))
            elif self.total_donated >= 10:
                return (True, "善财道（小成）", int(small_bonus * path_multiplier))
        
        elif self.role == Role.LANDOWNER:
            # 舍宅道：已建寺 + 捐地≥2
            if self.has_built_temple and self.land_donated >= 2:
                return (True, "舍宅道", int(base_bonus * path_multiplier))
            elif self.land_donated >= 1 or self.has_built_temple:
                return (True, "舍宅道（小成）", int(small_bonus * path_multiplier))
        
        elif self.role == Role.SCHOLAR:
            # 清名道：影响≥8 + 对2位不同玩家善行
            if self.influence >= 8 and len(self.kindness_targets) >= 2:
                return (True, "清名道", int(base_bonus * path_multiplier))
            elif self.influence >= 6 or len(self.kindness_targets) >= 1:
                return (True, "清名道（小成）", int(small_bonus * path_multiplier))
        
        elif self.role == Role.PEASANT:
            # 勤劳道：善行≥4 + 耕作≥3
            if self.kindness_count >= 4 and self.farming_count >= 3:
                return (True, "勤劳道", int(base_bonus * path_multiplier))
            elif self.kindness_count >= 2 or self.farming_count >= 2:
                return (True, "勤劳道（小成）", int(small_bonus * path_multiplier))
        
        elif self.role == Role.DEVOTEE:
            # 菩萨道：回向≥3 + 对3位不同玩家给予功德
            targets_helped = self.transfer_targets | self.kindness_targets
            if self.transfer_count >= 3 and len(targets_helped) >= 3:
                return (True, "菩萨道", int(base_bonus * path_multiplier))
            elif self.transfer_count >= 2 or len(targets_helped) >= 2:
                return (True, "菩萨道（小成）", int(small_bonus * path_multiplier))
        
        return (False, "", 0)
    
    def get_final_score(self, num_players: int) -> float:
        """计算最终得分"""
        # 基础分：功德×2 + 影响×1 + 财富÷3 + 土地×2
        base_score = self.merit * 2 + self.influence + self.wealth / 3 + self.land * 2
        
        # 道路加分
        path_complete, path_name, path_bonus = self.check_path_completion(num_players)
        if path_complete:
            self.score_sources[ScoreSource.PATH] = path_bonus
        
        total = base_score + path_bonus
        return total
    
    def get_score_breakdown(self) -> Dict:
        return {
            source.value: points 
            for source, points in self.score_sources.items()
        }

# ═══════════════════════════════════════════════════════════════════
#                           游戏模拟器
# ═══════════════════════════════════════════════════════════════════

class GameSimulator:
    def __init__(self, num_players: int = 6):
        if num_players < 3 or num_players > 6:
            raise ValueError("Player count must be 3-6")
        self.num_players = num_players
        self.roles = PLAYER_CONFIG[num_players]
        
    def create_game(self) -> Dict:
        players = []
        for i, role in enumerate(self.roles):
            players.append(Player(role=role, player_id=i, num_players=self.num_players))
        
        return {
            "players": players,
            "round": 1,
            "event_deck": build_event_deck(),
            "temple_fund": 0,  # 寺院基金
            "round_events": [],
        }
    
    def find_by_role(self, game: Dict, role: Role) -> Optional[Player]:
        for p in game["players"]:
            if p.role == role:
                return p
        return None
    
    # ─────────────────────────────────────────────────────────────
    #                        事件处理
    # ─────────────────────────────────────────────────────────────
    
    def process_event(self, game: Dict, event: EventCard):
        players = game["players"]
        
        if event.id == 1:  # 丰年
            for p in players:
                p.wealth += 2
        
        elif event.id == 2:  # 祥瑞
            for p in players:
                p.add_merit(1, ScoreSource.EVENT)
        
        elif event.id == 3:  # 灾异
            for p in players:
                # AI选择：财富多则减财富，否则减功德
                if p.wealth >= 2:
                    p.wealth -= 2
                elif p.merit >= 1:
                    p.merit = max(0, p.merit - 1)
        
        elif event.id == 4:  # 盂兰盆会
            for p in players:
                if p.wealth >= 2:
                    p.wealth -= 2
                    p.add_merit(2, ScoreSource.EVENT)
        
        elif event.id == 5:  # 讲经法会
            highest_inf = max(players, key=lambda x: x.influence)
            for p in players:
                if p == highest_inf:
                    p.add_merit(2, ScoreSource.EVENT)
                else:
                    p.add_merit(1, ScoreSource.EVENT)
        
        elif event.id == 6:  # 忏悔法会
            # 简化：所有人+1功德
            for p in players:
                p.add_merit(1, ScoreSource.EVENT)
        
        elif event.id == 7:  # 商队
            for p in players:
                if p.wealth >= 2:
                    p.wealth -= 2
                    p.add_merit(1, ScoreSource.EVENT)
        
        elif event.id == 8:  # 科举
            for p in players:
                if p.influence >= 5:
                    p.add_merit(2, ScoreSource.EVENT)
                    p.influence += 1
        
        elif event.id == 9:  # 集市
            # 简化：促进交易，所有人+1财富
            for p in players:
                p.wealth += 1
        
        elif event.id == 10:  # 旱灾
            for p in players:
                if p.wealth >= 3:
                    p.wealth -= 3
                else:
                    game["temple_fund"] += 2
        
        elif event.id == 11:  # 盗匪
            richest = max(players, key=lambda x: x.wealth)
            if richest.wealth >= 4:
                richest.wealth -= 4
            else:
                richest.influence = max(0, richest.influence - 2)
        
        elif event.id == 12:  # 瘟疫
            for p in players:
                if p.merit >= 1:
                    p.merit -= 1
                else:
                    p.influence = max(0, p.influence - 2)
        
        elif event.id == 13:  # 高僧
            lowest = min(players, key=lambda x: x.merit)
            lowest.add_merit(3, ScoreSource.EVENT)
        
        elif event.id == 14:  # 顿悟
            # 随机一人获益
            lucky = random.choice(players)
            lucky.add_merit(2, ScoreSource.EVENT)
            lucky.influence += 1
        
        elif event.id == 15:  # 福报
            highest_merit = max(players, key=lambda x: x.merit)
            highest_merit.wealth += 2
    
    # ─────────────────────────────────────────────────────────────
    #                        生产阶段
    # ─────────────────────────────────────────────────────────────
    
    def production_phase(self, game: Dict):
        for p in game["players"]:
            if p.role == Role.SANGHA:
                p.influence += 2
            elif p.role == Role.MERCHANT:
                p.wealth += 3
            elif p.role == Role.LANDOWNER:
                p.wealth += p.land
            elif p.role == Role.SCHOLAR:
                if game["round"] % 2 == 0:
                    p.influence += 2
                else:
                    p.influence += 1
            elif p.role == Role.PEASANT:
                p.wealth += 2
            elif p.role == Role.DEVOTEE:
                p.add_merit(1, ScoreSource.MECHANISM)
    
    # ─────────────────────────────────────────────────────────────
    #                        竞标法会（第3、6轮）
    # ─────────────────────────────────────────────────────────────
    
    def auction_phase(self, game: Dict):
        if game["round"] not in [3, 6]:
            return
        
        players = game["players"]
        bids = []
        
        # 每个玩家根据策略出价
        for p in players:
            max_bid = min(p.wealth, 5)  # 最多出5
            if p.role == Role.MERCHANT:
                bid = min(max_bid, 4)  # 商贾愿意出更多
            elif p.role == Role.SANGHA:
                bid = min(max_bid, 2)  # 僧伽出较少
            else:
                bid = min(max_bid, 3)
            bids.append((p, bid))
        
        # 排序找出最高出价的2人
        bids.sort(key=lambda x: -x[1])
        winners = bids[:min(2, len(bids))]
        
        for p, bid in winners:
            if bid > 0:
                p.wealth -= bid
                game["temple_fund"] += bid
                p.add_merit(3, ScoreSource.AUCTION)
                p.influence += 1
                p.auction_wins += 1
    
    # ─────────────────────────────────────────────────────────────
    #                        行动阶段
    # ─────────────────────────────────────────────────────────────
    
    def action_phase(self, game: Dict):
        players = game["players"]
        
        # 追赶机制：功德最低者+1行动点
        min_merit = min(p.merit for p in players)
        for p in players:
            p.action_points = 3 if p.role == Role.PEASANT else 2
            if p.merit == min_merit and p.merit < 10:
                p.action_points += 1
        
        # 第8轮（往生之轮）效果翻倍
        multiplier = 2 if game["round"] == 8 else 1
        
        for p in players:
            while p.action_points > 0:
                action = self.decide_action(p, game)
                if action is None:
                    break
                
                self.execute_action(p, action, game, multiplier)
                p.action_points -= 1
    
    def decide_action(self, player: Player, game: Dict) -> Optional[str]:
        """AI决策行动"""
        role = player.role
        
        # 优先完成道路
        if role == Role.SANGHA:
            if player.influence >= 2 and len(player.transfer_targets) < 3:
                return "transfer"  # 回向以完成道路
            elif player.influence >= 2:
                return "practice"
            elif player.wealth >= 3:
                return "donate"
        
        elif role == Role.MERCHANT:
            if player.wealth >= 8 and not player.has_built_temple:
                return "build_temple"
            elif player.wealth >= 5:
                return "donate"
            elif player.wealth >= 3:
                return "donate"
        
        elif role == Role.LANDOWNER:
            if player.land >= 2 and not player.has_built_temple:
                return "build_temple_land"
            elif player.land >= 1 and player.land_donated < 2:
                return "donate_land"
            elif player.wealth >= 3:
                return "donate"
            else:
                return "farm"
        
        elif role == Role.SCHOLAR:
            if player.wealth >= 1 and len(player.kindness_targets) < 2:
                return "kindness"
            elif player.influence >= 2:
                return "practice"
            elif player.wealth >= 3:
                return "donate"
        
        elif role == Role.PEASANT:
            if player.kindness_count < 4 and player.wealth >= 1:
                return "kindness"
            elif player.farming_count < 3:
                return "farm"
            elif player.wealth >= 1:
                return "kindness"
        
        elif role == Role.DEVOTEE:
            if player.merit >= 2 and player.transfer_count < 3:
                return "transfer"
            elif player.wealth >= 1:
                return "kindness"
            elif player.wealth >= 3:
                return "donate"
        
        return None
    
    def execute_action(self, player: Player, action: str, game: Dict, multiplier: int = 1):
        """执行行动"""
        players = game["players"]
        others = [p for p in players if p.player_id != player.player_id]
        
        if action == "donate":  # 布施
            cost = 5 if player.role == Role.MERCHANT else 3
            gain = 2 if player.role == Role.MERCHANT else 1
            if player.wealth >= cost:
                player.wealth -= cost
                player.total_donated += cost
                player.add_merit(gain * multiplier, ScoreSource.MECHANISM)
        
        elif action == "practice":  # 修行
            cost = 2
            gain = 2 if player.role == Role.SANGHA else 1
            if player.influence >= cost:
                player.influence -= cost
                player.add_merit(gain * multiplier, ScoreSource.MECHANISM)
        
        elif action == "kindness":  # 善行
            cost = 0 if player.role == Role.PEASANT else 1
            gain = 2 if player.role == Role.DEVOTEE else 1
            
            if player.wealth >= cost:
                if cost > 0:
                    player.wealth -= cost
                player.kindness_count += 1
                player.add_merit(gain * multiplier, ScoreSource.MECHANISM)
                
                if others:
                    target = random.choice(others)
                    target.add_merit(gain * multiplier, ScoreSource.INTERACTION)
                    player.kindness_targets.add(target.player_id)
        
        elif action == "transfer":  # 回向
            cost = 2
            target_gain = 4 if player.role == Role.DEVOTEE else 3
            self_gain = 1
            
            if player.merit >= cost:
                player.merit -= cost
                player.transfer_count += 1
                player.influence += self_gain
                
                if others:
                    target = random.choice(others)
                    target.add_merit(target_gain * multiplier, ScoreSource.INTERACTION)
                    player.transfer_targets.add(target.player_id)
        
        elif action == "farm":  # 耕作
            base_gain = 2
            if player.role == Role.LANDOWNER:
                base_gain += player.land
            player.wealth += base_gain
            player.farming_count += 1
        
        elif action == "build_temple":  # 建寺（财富）
            cost_wealth = 8
            cost_influence = 2
            if player.wealth >= cost_wealth and player.influence >= cost_influence:
                player.wealth -= cost_wealth
                player.influence -= cost_influence
                player.has_built_temple = True
                player.add_merit(5 * multiplier, ScoreSource.MECHANISM)
        
        elif action == "build_temple_land":  # 建寺（土地）
            if player.land >= 2:
                player.land -= 2
                player.land_donated += 2
                player.has_built_temple = True
                player.add_merit(5 * multiplier, ScoreSource.MECHANISM)
        
        elif action == "donate_land":  # 捐地
            if player.land >= 1:
                player.land -= 1
                player.land_donated += 1
                player.add_merit(3 * multiplier, ScoreSource.MECHANISM)
                player.influence += 1
    
    # ─────────────────────────────────────────────────────────────
    #                        运行游戏
    # ─────────────────────────────────────────────────────────────
    
    def run_game(self) -> Dict:
        game = self.create_game()
        
        for round_num in range(1, 9):  # 8轮
            game["round"] = round_num
            
            # 天机阶段
            if game["event_deck"]:
                event = game["event_deck"].pop()
                game["round_events"].append(event.name)
                self.process_event(game, event)
            
            # 生产阶段
            self.production_phase(game)
            
            # 竞标法会（第3、6轮）
            self.auction_phase(game)
            
            # 行动阶段
            self.action_phase(game)
            
            # 中期检查点（第4轮）- 调整行动点
            if round_num == 4:
                sorted_players = sorted(game["players"], key=lambda x: x.merit, reverse=True)
                if len(sorted_players) >= 2:
                    sorted_players[0].action_points = max(1, sorted_players[0].action_points - 1)
                    sorted_players[-1].action_points += 1
        
        # 计算最终得分
        results = []
        for p in game["players"]:
            final_score = p.get_final_score(self.num_players)
            path_complete, path_name, path_bonus = p.check_path_completion(self.num_players)
            
            results.append({
                "role": p.role.value,
                "score": round(final_score, 1),
                "merit": p.merit,
                "influence": p.influence,
                "wealth": p.wealth,
                "path_completed": path_name if path_complete else "",
                "path_bonus": path_bonus if path_complete else 0,
                "score_breakdown": p.get_score_breakdown(),
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        winner = results[0]["role"]
        
        return {
            "winner": winner,
            "results": results,
            "events": game["round_events"],
            "num_players": self.num_players,
        }
    
    def run_batch(self, num_games: int) -> Dict:
        wins = defaultdict(int)
        total_scores = defaultdict(list)
        path_completions = defaultdict(int)
        source_totals = defaultdict(lambda: defaultdict(float))
        
        for _ in range(num_games):
            result = self.run_game()
            wins[result["winner"]] += 1
            
            for r in result["results"]:
                role = r["role"]
                total_scores[role].append(r["score"])
                if r["path_completed"]:
                    path_completions[r["path_completed"]] += 1
                
                for source, points in r["score_breakdown"].items():
                    source_totals[role][source] += points
        
        stats = {
            "num_games": num_games,
            "num_players": self.num_players,
            "roles_used": [r.value for r in self.roles],
            "win_rates": {},
            "avg_scores": {},
            "path_completion_rates": {},
            "score_source_breakdown": {},
        }
        
        for role in [r.value for r in self.roles]:
            if role in wins:
                stats["win_rates"][role] = round(wins[role] / num_games * 100, 2)
            else:
                stats["win_rates"][role] = 0
            
            if role in total_scores:
                scores = total_scores[role]
                stats["avg_scores"][role] = round(sum(scores) / len(scores), 2)
            
            if role in source_totals:
                sources = source_totals[role]
                stats["score_source_breakdown"][role] = {
                    source: round(points / num_games, 2)
                    for source, points in sources.items()
                }
        
        for path, count in path_completions.items():
            stats["path_completion_rates"][path] = round(count / num_games * 100, 2)
        
        return stats


# ═══════════════════════════════════════════════════════════════════
#                           主程序
# ═══════════════════════════════════════════════════════════════════

def main():
    results_all = {}
    
    for num_players in [3, 4, 5, 6]:
        print(f"\n{'='*60}")
        print(f"Testing {num_players}-player game (v5.0 Streamlined)...")
        print(f"{'='*60}")
        
        simulator = GameSimulator(num_players)
        
        for batch_size in [100, 1000, 10000]:
            print(f"  Running {batch_size} games...", end=" ")
            start = time.time()
            stats = simulator.run_batch(batch_size)
            elapsed = time.time() - start
            print(f"Done in {elapsed:.2f}s")
            
            key = f"{num_players}p_{batch_size}"
            results_all[key] = stats
        
        # 打印10000局结果
        stats = results_all[f"{num_players}p_10000"]
        print(f"\n  [10000 games summary - v5.0]")
        print(f"  Roles: {', '.join(stats['roles_used'])}")
        print(f"  Win rates:")
        for role, rate in sorted(stats["win_rates"].items(), key=lambda x: -x[1]):
            print(f"    {role}: {rate}%")
        print(f"  Avg scores:")
        for role, score in sorted(stats["avg_scores"].items(), key=lambda x: -x[1]):
            print(f"    {role}: {score}")
        print(f"  Path completion rates:")
        for path, rate in sorted(stats["path_completion_rates"].items(), key=lambda x: -x[1])[:6]:
            print(f"    {path}: {rate}%")
    
    with open("simulation_results_v5.json", "w", encoding="utf-8") as f:
        json.dump(results_all, f, ensure_ascii=False, indent=2)
    
    print("\n\nResults saved to simulation_results_v5.json")
    return results_all


if __name__ == "__main__":
    main()
