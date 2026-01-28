# -*- coding: utf-8 -*-
"""
救赎之路 v7.1 - 双骰子系统
基于v7.0骰子版，新增"修行骰子"（悟道骰子）

两个骰子系统：
1. 福报骰子：生产阶段，影响资源获取
2. 悟道骰子：修行行动时，影响功德获取

设计原则：
- 悟道骰子只在修行时使用
- 影响可控（±1功德范围）
- 福田道受益最大（配合修行效率+100%）
- 增加修行的随机性和趣味性
"""

import random
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import time
from statistics import mean, stdev


class Path(Enum):
    NIRVANA = "福田道"
    CHARITY = "布施道"
    TEMPLE = "土地道"
    CULTURE = "文化道"
    DILIGENCE = "勤劳道"
    SALVATION = "渡化道"


class AIStrategy(Enum):
    AGGRESSIVE = "激进型"
    CONSERVATIVE = "保守型"
    BALANCED = "平衡型"
    RANDOM = "随机型"
    OPPORTUNISTIC = "机会型"


class ScoreSource(Enum):
    MECHANISM = "机制"
    EVENT = "事件"
    INTERACTION = "互动"
    PATH = "道路"
    PRODUCTION_DICE = "福报骰子"
    PRACTICE_DICE = "悟道骰子"


class ProductionDiceResult(Enum):
    """福报骰子结果 - 生产阶段"""
    NORMAL = "平常"           # 1-2: 标准生产
    SMALL_FORTUNE = "小福"    # 3-4: +1财富
    GREAT_FORTUNE = "大福"    # 5-6: +1财富 +1影响


class PracticeDiceResult(Enum):
    """悟道骰子结果 - 修行行动"""
    DISTRACTION = "心散"       # 1: 功德-1（最低0）
    ORDINARY = "平凡"          # 2-3: 标准修行
    INSIGHT = "感悟"           # 4-5: 功德+1
    ENLIGHTENMENT = "顿悟"     # 6: 功德+2，并+1影响


@dataclass
class EventCard:
    id: int
    name: str
    category: str
    copies: int


EVENT_CARDS = [
    EventCard(1, "丰年", "天象", 2),
    EventCard(2, "祥瑞", "天象", 2),
    EventCard(3, "灾异", "天象", 2),
    EventCard(4, "盂兰盆会", "法会", 2),
    EventCard(5, "讲经法会", "法会", 2),
    EventCard(6, "水陆法会", "法会", 2),
    EventCard(7, "商队", "世俗", 2),
    EventCard(8, "科举", "世俗", 2),
    EventCard(9, "集市", "世俗", 2),
    EventCard(10, "旱灾", "灾难", 2),
    EventCard(11, "盗匪", "灾难", 2),
    EventCard(12, "瘟疫", "灾难", 2),
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


@dataclass
class Player:
    player_id: int
    path: Path
    strategy: AIStrategy
    num_players: int = 4
    
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
    practice_count: int = 0  # 新增：修行次数追踪
    
    # 骰子统计
    production_dice_bonus_wealth: int = 0
    production_dice_bonus_influence: int = 0
    practice_dice_bonus_merit: int = 0
    practice_dice_bonus_influence: int = 0
    practice_dice_results: List = field(default_factory=list)
    production_dice_results: List = field(default_factory=list)
    
    score_sources: Dict = field(default_factory=lambda: {
        ScoreSource.MECHANISM: 0,
        ScoreSource.EVENT: 0,
        ScoreSource.INTERACTION: 0,
        ScoreSource.PATH: 0,
        ScoreSource.PRODUCTION_DICE: 0,
        ScoreSource.PRACTICE_DICE: 0,
    })
    
    def __post_init__(self):
        """应用道路启动奖励 - 骰子版调整"""
        if self.path == Path.NIRVANA:
            self.influence += 6
            self.merit += 2
        elif self.path == Path.CHARITY:
            self.wealth += 7
        elif self.path == Path.TEMPLE:
            self.land += 1
            self.wealth += 1
        elif self.path == Path.CULTURE:
            self.influence += 3
            self.wealth += 2
        elif self.path == Path.DILIGENCE:
            self.wealth += 2
            self.base_action_points = 3
        elif self.path == Path.SALVATION:
            self.merit += 5
            self.influence += 3
    
    def add_merit(self, amount: int, source: ScoreSource):
        self.merit += amount
        self.score_sources[source] += amount * 2
    
    def get_path_bonus_multiplier(self, action: str) -> float:
        if self.path == Path.NIRVANA and action == "practice":
            return 2.0
        elif self.path == Path.CHARITY and action == "donate":
            return 1.75
        elif self.path == Path.CULTURE and action == "kindness":
            return 1.5
        elif self.path == Path.SALVATION and action == "transfer":
            return 2.0
        return 1.0
    
    def check_path_completion(self, num_players: int) -> Tuple[bool, str, int]:
        multiplier = 1.0
        if num_players == 3:
            multiplier = 1.2
        elif num_players >= 5:
            multiplier = 0.9
        
        base_bonus = 25
        small_bonus = 12
        
        # 4人模式福田道条件调整
        transfer_target_req = 2 if num_players == 4 else 3
        
        if self.path == Path.NIRVANA:
            if len(self.transfer_targets) >= transfer_target_req and self.influence_spent >= 4:
                return (True, "福田道", int(base_bonus * multiplier))
            elif len(self.transfer_targets) >= 1:
                return (True, "福田道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.CHARITY:
            if self.total_donated >= 12 and self.influence >= 3:
                return (True, "布施道", int(base_bonus * multiplier))
            elif self.total_donated >= 7:
                return (True, "布施道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.TEMPLE:
            if self.has_built_temple and self.land_donated >= 3:
                return (True, "土地道", int(base_bonus * multiplier))
            elif self.has_built_temple or self.land_donated >= 2:
                return (True, "土地道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.CULTURE:
            if self.influence >= 7 and len(self.kindness_targets) >= 3:
                return (True, "文化道", int(base_bonus * multiplier))
            elif self.influence >= 5 or len(self.kindness_targets) >= 2:
                return (True, "文化道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.DILIGENCE:
            if self.kindness_count >= 5 and self.farming_count >= 5:
                return (True, "勤劳道", int(base_bonus * multiplier))
            elif self.kindness_count >= 3 or self.farming_count >= 3:
                return (True, "勤劳道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.SALVATION:
            all_helped = self.transfer_targets | self.kindness_targets
            if self.transfer_count >= 3 and len(all_helped) >= 2:
                return (True, "渡化道", int(base_bonus * multiplier))
            elif self.transfer_count >= 1 or len(all_helped) >= 1:
                return (True, "渡化道（小成）", int(small_bonus * multiplier))
        
        return (False, "", 0)
    
    def get_final_score(self, num_players: int) -> float:
        base_score = self.merit * 2 + self.influence + self.wealth / 3 + self.land * 2
        path_complete, path_name, path_bonus = self.check_path_completion(num_players)
        if path_complete:
            self.score_sources[ScoreSource.PATH] = path_bonus
        return base_score + path_bonus


class AIDecisionMaker:
    @staticmethod
    def decide_action(player: Player, game: Dict, others: List[Player]) -> Optional[str]:
        strategy = player.strategy
        
        if strategy == AIStrategy.RANDOM:
            return AIDecisionMaker._random_action(player, others)
        elif strategy == AIStrategy.AGGRESSIVE:
            return AIDecisionMaker._aggressive_action(player, others)
        elif strategy == AIStrategy.CONSERVATIVE:
            return AIDecisionMaker._conservative_action(player, others)
        elif strategy == AIStrategy.BALANCED:
            return AIDecisionMaker._balanced_action(player, others)
        elif strategy == AIStrategy.OPPORTUNISTIC:
            return AIDecisionMaker._opportunistic_action(player, game, others)
        return None
    
    @staticmethod
    def _get_available_actions(player: Player, others: List[Player]) -> List[str]:
        actions = []
        if player.wealth >= 3:
            actions.append("donate")
        if player.influence >= 2:
            actions.append("practice")
        if player.wealth >= 1 and others:
            actions.append("kindness")
        if player.merit >= 2 and others:
            actions.append("transfer")
        actions.append("farm")
        if not player.has_built_temple:
            if player.wealth >= 8 and player.influence >= 2:
                actions.append("build_temple")
            elif player.land >= 2:
                actions.append("build_temple_land")
        if player.land >= 1:
            actions.append("donate_land")
        return actions
    
    @staticmethod
    def _random_action(player: Player, others: List[Player]) -> Optional[str]:
        actions = AIDecisionMaker._get_available_actions(player, others)
        return random.choice(actions) if actions else None
    
    @staticmethod
    def _aggressive_action(player: Player, others: List[Player]) -> Optional[str]:
        if not player.has_built_temple:
            if player.land >= 2:
                return "build_temple_land"
            if player.wealth >= 8 and player.influence >= 2:
                return "build_temple"
        if player.wealth >= 6:
            return "donate"
        if player.merit >= 2 and others:
            return "transfer"
        if player.influence >= 2:
            return "practice"
        if player.wealth >= 3:
            return "donate"
        if player.wealth >= 1 and others:
            return "kindness"
        return "farm"
    
    @staticmethod
    def _conservative_action(player: Player, others: List[Player]) -> Optional[str]:
        if player.wealth < 5:
            return "farm"
        if player.wealth >= 1 and others:
            return "kindness"
        if player.wealth >= 6:
            return "donate"
        if player.influence >= 3:
            return "practice"
        return "farm"
    
    @staticmethod
    def _balanced_action(player: Player, others: List[Player]) -> Optional[str]:
        path = player.path
        
        if path == Path.NIRVANA:
            # 福田道优先修行
            if player.influence >= 2:
                return "practice"
            if player.merit >= 2 and others and len(player.transfer_targets) < 3:
                return "transfer"
        
        elif path == Path.CHARITY:
            if player.wealth >= 3:
                return "donate"
            return "farm"
        
        elif path == Path.TEMPLE:
            if not player.has_built_temple and player.land >= 2:
                return "build_temple_land"
            if player.land >= 1 and player.land_donated < 2:
                return "donate_land"
            return "farm"
        
        elif path == Path.CULTURE:
            if player.wealth >= 1 and others and len(player.kindness_targets) < 3:
                return "kindness"
            if player.influence >= 2:
                return "practice"
        
        elif path == Path.DILIGENCE:
            if player.kindness_count < 4 and player.wealth >= 1 and others:
                return "kindness"
            if player.farming_count < 4:
                return "farm"
        
        elif path == Path.SALVATION:
            if player.merit >= 2 and others:
                return "transfer"
            if player.wealth >= 1 and others:
                return "kindness"
        
        actions = AIDecisionMaker._get_available_actions(player, others)
        return random.choice(actions) if actions else None
    
    @staticmethod
    def _opportunistic_action(player: Player, game: Dict, others: List[Player]) -> Optional[str]:
        round_num = game["round"]
        if round_num <= 3:
            if player.wealth < 8:
                return "farm"
            if player.wealth >= 3:
                return "donate"
        elif round_num <= 6:
            return AIDecisionMaker._balanced_action(player, others)
        else:
            if not player.has_built_temple and player.land >= 2:
                return "build_temple_land"
            if player.wealth >= 3:
                return "donate"
            if player.merit >= 2 and others:
                return "transfer"
        return AIDecisionMaker._balanced_action(player, others)
    
    @staticmethod
    def decide_event_option(player: Player, event: EventCard) -> str:
        if player.strategy == AIStrategy.RANDOM:
            return random.choice(["A", "B"])
        if event.category in ["法会", "机缘"]:
            if player.strategy == AIStrategy.AGGRESSIVE:
                return "A"
        return random.choice(["A", "B"])


class GameSimulator:
    def __init__(self, num_players: int = 4, 
                 use_production_dice: bool = True,
                 use_practice_dice: bool = True):
        if num_players < 3 or num_players > 6:
            raise ValueError("Player count must be 3-6")
        
        self.num_players = num_players
        self.use_production_dice = use_production_dice
        self.use_practice_dice = use_practice_dice
        self.all_paths = list(Path)[:num_players]
        
        # 统计
        self.production_dice_stats = defaultdict(int)
        self.practice_dice_stats = defaultdict(int)
    
    def _roll_production_dice(self) -> Tuple[ProductionDiceResult, int, int]:
        """福报骰子"""
        roll = random.randint(1, 6)
        if roll <= 2:
            return (ProductionDiceResult.NORMAL, 0, 0)
        elif roll <= 4:
            return (ProductionDiceResult.SMALL_FORTUNE, 1, 0)
        else:
            return (ProductionDiceResult.GREAT_FORTUNE, 1, 1)
    
    def _roll_practice_dice(self) -> Tuple[PracticeDiceResult, int, int]:
        """
        悟道骰子 - 修行时掷骰
        
        Returns:
            (结果类型, 额外功德, 额外影响)
        """
        roll = random.randint(1, 6)
        if roll == 1:
            return (PracticeDiceResult.DISTRACTION, -1, 0)  # 心散：-1功德
        elif roll <= 3:
            return (PracticeDiceResult.ORDINARY, 0, 0)      # 平凡：无加成
        elif roll <= 5:
            return (PracticeDiceResult.INSIGHT, 1, 0)       # 感悟：+1功德
        else:
            return (PracticeDiceResult.ENLIGHTENMENT, 2, 1) # 顿悟：+2功德 +1影响
    
    def create_game(self, paths: List[Path] = None, 
                    strategies: List[AIStrategy] = None) -> Dict:
        if paths is None:
            paths = random.sample(self.all_paths, self.num_players)
        if strategies is None:
            strategies = [random.choice(list(AIStrategy)) for _ in range(self.num_players)]
        
        players = []
        for i in range(self.num_players):
            players.append(Player(
                player_id=i,
                path=paths[i],
                strategy=strategies[i],
                num_players=self.num_players
            ))
        
        return {
            "players": players,
            "round": 1,
            "event_deck": build_event_deck(),
        }
    
    def process_event(self, game: Dict, event: EventCard):
        for p in game["players"]:
            option = AIDecisionMaker.decide_event_option(p, event)
            
            if event.id == 1:  # 丰年
                if option == "A":
                    p.wealth += 3
                else:
                    p.add_merit(1, ScoreSource.EVENT)
                    p.influence += 1
            elif event.id == 2:  # 祥瑞
                if option == "A":
                    p.add_merit(2, ScoreSource.EVENT)
                else:
                    p.influence += 2
            elif event.id == 3:  # 灾异
                if option == "A":
                    p.wealth = max(0, p.wealth - 3)
                else:
                    p.merit = max(0, p.merit - 2)
            elif event.id == 4:  # 盂兰盆会
                if option == "A" and p.wealth >= 2:
                    p.wealth -= 2
                    p.add_merit(3, ScoreSource.EVENT)
            elif event.id == 5:  # 讲经法会
                if option == "A" and p.influence >= 1:
                    p.influence -= 1
                    p.add_merit(2, ScoreSource.EVENT)
                else:
                    p.add_merit(1, ScoreSource.EVENT)
            elif event.id == 6:  # 水陆法会
                if option == "A" and p.wealth >= 3:
                    p.wealth -= 3
                    p.add_merit(4, ScoreSource.EVENT)
            elif event.id == 7:  # 商队
                if option == "A":
                    p.wealth += 3
                elif p.wealth >= 3:
                    p.wealth -= 3
                    p.add_merit(2, ScoreSource.EVENT)
            elif event.id == 8:  # 科举
                if option == "A" and p.influence >= 5:
                    p.add_merit(2, ScoreSource.EVENT)
                else:
                    p.influence += 1
            elif event.id == 9:  # 集市
                if option == "A":
                    p.wealth += 2
                else:
                    p.add_merit(1, ScoreSource.EVENT)
            elif event.id == 10:  # 旱灾
                if option == "A":
                    p.wealth = max(0, p.wealth - 3)
                else:
                    p.merit = max(0, p.merit - 1)
                    p.influence = max(0, p.influence - 1)
            elif event.id == 11:  # 盗匪
                if option == "A":
                    p.wealth = max(0, p.wealth - 4)
                else:
                    p.influence = max(0, p.influence - 2)
            elif event.id == 12:  # 瘟疫
                if option == "A":
                    p.merit = max(0, p.merit - 2)
                else:
                    p.influence = max(0, p.influence - 2)
            elif event.id == 13:  # 高僧
                if option == "A":
                    p.add_merit(3, ScoreSource.EVENT)
                else:
                    p.add_merit(2, ScoreSource.EVENT)
                    p.influence += 1
            elif event.id == 14:  # 顿悟
                if option == "A":
                    p.add_merit(2, ScoreSource.EVENT)
                    p.influence += 1
                else:
                    p.influence += 3
            elif event.id == 15:  # 福报
                if option == "A":
                    p.wealth += 2
                    p.add_merit(1, ScoreSource.EVENT)
                else:
                    p.add_merit(1, ScoreSource.EVENT)
                    p.influence += 2
    
    def production_phase(self, game: Dict):
        for p in game["players"]:
            # 基础产出
            p.wealth += 2
            p.influence += 1
            
            # 土地产出
            land_bonus = 1 if p.path in [Path.TEMPLE, Path.DILIGENCE] else 0
            p.wealth += p.land * (1 + land_bonus)
            
            # 福报骰子
            if self.use_production_dice:
                result, extra_w, extra_i = self._roll_production_dice()
                p.production_dice_results.append(result)
                p.production_dice_bonus_wealth += extra_w
                p.production_dice_bonus_influence += extra_i
                p.wealth += extra_w
                p.influence += extra_i
                self.production_dice_stats[result.value] += 1
                p.score_sources[ScoreSource.PRODUCTION_DICE] += extra_i + extra_w / 3
    
    def execute_action(self, player: Player, action: str, game: Dict, 
                       others: List[Player]):
        multiplier = player.get_path_bonus_multiplier(action)
        
        if action == "donate":
            if player.wealth >= 3:
                player.wealth -= 3
                player.total_donated += 3
                merit_gain = int(1 * multiplier)
                player.add_merit(merit_gain, ScoreSource.MECHANISM)
        
        elif action == "practice":
            if player.influence >= 2:
                player.influence -= 2
                player.influence_spent += 2
                player.practice_count += 1
                
                # 基础功德（应用道路加成）
                base_merit = int(1 * multiplier)
                
                # 悟道骰子
                dice_merit = 0
                dice_influence = 0
                if self.use_practice_dice:
                    result, extra_m, extra_i = self._roll_practice_dice()
                    player.practice_dice_results.append(result)
                    self.practice_dice_stats[result.value] += 1
                    
                    # 道路加成也应用于骰子额外功德
                    dice_merit = int(extra_m * multiplier)
                    dice_influence = extra_i
                    
                    player.practice_dice_bonus_merit += dice_merit
                    player.practice_dice_bonus_influence += dice_influence
                    player.influence += dice_influence
                    
                    # 记录骰子得分来源
                    dice_score = dice_merit * 2 + dice_influence
                    player.score_sources[ScoreSource.PRACTICE_DICE] += dice_score
                
                # 总功德 = 基础 + 骰子加成（不能为负）
                total_merit = max(0, base_merit + dice_merit)
                player.add_merit(total_merit, ScoreSource.MECHANISM)
        
        elif action == "kindness":
            if player.wealth >= 1 and others:
                player.wealth -= 1
                player.kindness_count += 1
                merit_gain = int(1 * multiplier)
                player.add_merit(merit_gain, ScoreSource.MECHANISM)
                target = random.choice(others)
                target.add_merit(1, ScoreSource.INTERACTION)
                player.kindness_targets.add(target.player_id)
        
        elif action == "transfer":
            if player.merit >= 2 and others:
                player.merit -= 2
                player.transfer_count += 1
                player.influence += 1
                target_gain = int(3 * multiplier)
                target = random.choice(others)
                target.add_merit(target_gain, ScoreSource.INTERACTION)
                player.transfer_targets.add(target.player_id)
        
        elif action == "farm":
            base_gain = 2
            if player.path in [Path.TEMPLE, Path.DILIGENCE]:
                base_gain += 1
            player.wealth += base_gain
            player.farming_count += 1
        
        elif action == "build_temple":
            if player.wealth >= 8 and player.influence >= 2:
                player.wealth -= 8
                player.influence -= 2
                player.influence_spent += 2
                player.has_built_temple = True
                player.add_merit(5, ScoreSource.MECHANISM)
        
        elif action == "build_temple_land":
            if player.land >= 2:
                player.land -= 2
                player.land_donated += 2
                player.has_built_temple = True
                player.add_merit(5, ScoreSource.MECHANISM)
        
        elif action == "donate_land":
            if player.land >= 1:
                player.land -= 1
                player.land_donated += 1
                player.influence += 1
                player.add_merit(3, ScoreSource.MECHANISM)
    
    def action_phase(self, game: Dict):
        players = game["players"]
        for p in players:
            if p.path == Path.DILIGENCE:
                p.action_points = 3
            else:
                p.action_points = p.base_action_points
            
            others = [o for o in players if o.player_id != p.player_id]
            
            while p.action_points > 0:
                action = AIDecisionMaker.decide_action(p, game, others)
                if action is None:
                    break
                self.execute_action(p, action, game, others)
                p.action_points -= 1
    
    def run_game(self, paths: List[Path] = None, 
                 strategies: List[AIStrategy] = None) -> Dict:
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
            path_complete, path_name, path_bonus = p.check_path_completion(self.num_players)
            
            results.append({
                "path": p.path.value,
                "strategy": p.strategy.value,
                "score": round(score, 1),
                "merit": p.merit,
                "influence": p.influence,
                "wealth": p.wealth,
                "path_completed": path_name if path_complete else "",
                "practice_count": p.practice_count,
                "practice_dice_bonus_merit": p.practice_dice_bonus_merit,
                "practice_dice_bonus_influence": p.practice_dice_bonus_influence,
                "production_dice_bonus_wealth": p.production_dice_bonus_wealth,
                "production_dice_bonus_influence": p.production_dice_bonus_influence,
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "winner_path": results[0]["path"],
            "winner_strategy": results[0]["strategy"],
            "results": results,
        }


def run_comprehensive_test(num_players: int = 4, 
                           games: int = 10000,
                           use_production_dice: bool = True,
                           use_practice_dice: bool = True) -> Dict:
    """运行全面测试"""
    print(f"\n{'='*60}")
    print(f"Testing: {num_players}p, production_dice={use_production_dice}, practice_dice={use_practice_dice}")
    print(f"Running {games} games...")
    print(f"{'='*60}")
    
    start = time.time()
    
    sim = GameSimulator(num_players, use_production_dice, use_practice_dice)
    
    path_wins = defaultdict(int)
    path_games = defaultdict(int)
    path_scores = defaultdict(list)
    path_practice_counts = defaultdict(list)
    path_practice_dice_merit = defaultdict(list)
    
    for _ in range(games):
        result = sim.run_game()
        path_wins[result["winner_path"]] += 1
        
        for r in result["results"]:
            path_games[r["path"]] += 1
            path_scores[r["path"]].append(r["score"])
            path_practice_counts[r["path"]].append(r["practice_count"])
            path_practice_dice_merit[r["path"]].append(r["practice_dice_bonus_merit"])
    
    elapsed = time.time() - start
    print(f"Completed in {elapsed:.2f}s")
    
    # 计算统计
    target_rate = 100 / num_players
    stats = {
        "num_players": num_players,
        "games": games,
        "use_production_dice": use_production_dice,
        "use_practice_dice": use_practice_dice,
        "target_win_rate": round(target_rate, 2),
        "path_stats": {},
        "balance_score": 0,
    }
    
    total_deviation = 0
    print(f"\n{'道路':<12} {'胜率':>8} {'目标':>8} {'偏差':>8} {'平均分':>8} {'修行次数':>10} {'骰子功德':>10}")
    print("-" * 76)
    
    for path in Path:
        pn = path.value
        if pn in path_games:
            wins = path_wins[pn]
            total = path_games[pn]
            rate = wins / total * 100 if total > 0 else 0
            deviation = rate - target_rate
            total_deviation += abs(deviation)
            
            avg_score = mean(path_scores[pn]) if path_scores[pn] else 0
            avg_practice = mean(path_practice_counts[pn]) if path_practice_counts[pn] else 0
            avg_dice_merit = mean(path_practice_dice_merit[pn]) if path_practice_dice_merit[pn] else 0
            
            status = "✓" if abs(deviation) < 8 else "✗"
            print(f"{pn:<12} {rate:>7.1f}% {target_rate:>7.1f}% {deviation:>+7.1f}% {avg_score:>8.1f} {avg_practice:>10.1f} {avg_dice_merit:>+10.1f} {status}")
            
            stats["path_stats"][pn] = {
                "win_rate": round(rate, 2),
                "deviation": round(deviation, 2),
                "avg_score": round(avg_score, 2),
                "avg_practice_count": round(avg_practice, 2),
                "avg_practice_dice_merit": round(avg_dice_merit, 2),
            }
    
    stats["balance_score"] = round(total_deviation / num_players, 2)
    print(f"\n平衡分数: {stats['balance_score']:.2f} (越低越好，<5为合格)")
    
    # 骰子统计
    if use_practice_dice:
        print(f"\n悟道骰子分布:")
        total_rolls = sum(sim.practice_dice_stats.values())
        for result, count in sim.practice_dice_stats.items():
            pct = count / total_rolls * 100 if total_rolls > 0 else 0
            print(f"  {result}: {count} ({pct:.1f}%)")
    
    return stats


def run_ab_test(num_players: int = 4, games: int = 10000):
    """A/B测试：对比有无悟道骰子"""
    print("\n" + "="*70)
    print(f"A/B TEST: 悟道骰子影响分析 ({num_players}人模式)")
    print("="*70)
    
    # 对照组：只有福报骰子
    print("\n[对照组] 只有福报骰子（v7.0）")
    control = run_comprehensive_test(num_players, games, 
                                     use_production_dice=True, 
                                     use_practice_dice=False)
    
    # 实验组：双骰子
    print("\n[实验组] 福报骰子 + 悟道骰子（v7.1）")
    experiment = run_comprehensive_test(num_players, games,
                                        use_production_dice=True,
                                        use_practice_dice=True)
    
    # 对比分析
    print("\n" + "="*60)
    print("对比分析")
    print("="*60)
    print(f"{'道路':<12} {'v7.0胜率':>10} {'v7.1胜率':>10} {'变化':>10}")
    print("-" * 44)
    
    for path in Path:
        pn = path.value
        ctrl_rate = control["path_stats"].get(pn, {}).get("win_rate", 0)
        exp_rate = experiment["path_stats"].get(pn, {}).get("win_rate", 0)
        change = exp_rate - ctrl_rate
        print(f"{pn:<12} {ctrl_rate:>9.1f}% {exp_rate:>9.1f}% {change:>+9.1f}%")
    
    print(f"\n平衡分数变化: {control['balance_score']:.2f} → {experiment['balance_score']:.2f}")
    
    return {"control": control, "experiment": experiment}


if __name__ == "__main__":
    print("《救赎之路》v7.1 双骰子系统测试")
    print("新增：悟道骰子（修行时掷骰）")
    
    all_results = {}
    
    for np in [4, 5, 6]:
        result = run_ab_test(np, 10000)
        all_results[f"{np}p"] = result
    
    # 保存结果
    with open("v71_practice_dice_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print("\n结果已保存到 v71_practice_dice_results.json")
