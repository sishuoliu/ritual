# -*- coding: utf-8 -*-
"""
救赎之路 v7.1 - 修复版全面测试
修复：
1. 小成检测在每轮执行
2. 转职机制正常工作
3. 平衡性调整：勤劳道削弱，福田道加强
"""

import random
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import time
from itertools import permutations

# ===================================================================
#                           枚举与常量
# ===================================================================

class Path(Enum):
    NIRVANA = "福田道"
    CHARITY = "布施道"
    TEMPLE = "土地道"
    CULTURE = "文化道"
    DILIGENCE = "勤劳道"
    SALVATION = "渡化道"

class AscensionClass(Enum):
    ARHAT = "罗汉"
    MAHADANAPATI = "大檀越"
    TEMPLE_MASTER = "舍宅主"
    MANJUSRI = "文殊化身"
    WANDERING_MONK = "行脚僧"
    BODHISATTVA = "菩萨"

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
    ASCENSION = "转职"

ALL_PATHS = list(Path)
ALL_STRATEGIES = list(AIStrategy)

# ===================================================================
#                           事件卡
# ===================================================================

@dataclass
class EventCard:
    id: int
    name: str
    category: str
    copies: int
    option_a: str
    option_b: str

EVENT_CARDS = [
    EventCard(1, "丰年", "天象", 2, "+3财富", "+1功德+1影响"),
    EventCard(2, "祥瑞", "天象", 2, "+2功德", "+2影响"),
    EventCard(3, "灾异", "天象", 2, "-3财富", "-2功德"),
    EventCard(4, "盂兰盆会", "法会", 2, "消耗2财富+3功德", "不参与"),
    EventCard(5, "讲经法会", "法会", 2, "消耗1影响+2功德", "+1功德"),
    EventCard(6, "水陆法会", "法会", 2, "消耗3财富+4功德", "不参与"),
    EventCard(7, "商队", "世俗", 2, "+3财富", "3财富换2功德"),
    EventCard(8, "科举", "世俗", 2, "影响>=5:+2功德", "+1影响"),
    EventCard(9, "集市", "世俗", 2, "+2财富", "+1功德"),
    EventCard(10, "旱灾", "灾难", 2, "-3财富", "-1功德-1影响"),
    EventCard(11, "盗匪", "灾难", 2, "-4财富", "-2影响"),
    EventCard(12, "瘟疫", "灾难", 2, "-2功德", "-2影响"),
    EventCard(13, "高僧", "机缘", 2, "+3功德", "+2功德+1影响"),
    EventCard(14, "顿悟", "机缘", 2, "+2功德+1影响", "+3影响"),
    EventCard(15, "福报", "机缘", 2, "+2财富+1功德", "+1功德+2影响"),
]

def build_event_deck():
    deck = []
    for card in EVENT_CARDS:
        for _ in range(card.copies):
            deck.append(card)
    random.shuffle(deck)
    return deck

# ===================================================================
#                           玩家类 (v7.1修复版)
# ===================================================================

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
    
    has_ascended: bool = False
    ascension_class: Optional[AscensionClass] = None
    small_path_completed: bool = False
    ascension_round: int = 0
    
    score_sources: Dict = field(default_factory=lambda: {
        ScoreSource.MECHANISM: 0,
        ScoreSource.EVENT: 0,
        ScoreSource.INTERACTION: 0,
        ScoreSource.PATH: 0,
        ScoreSource.ASCENSION: 0,
    })
    
    initial_rank: int = 0
    
    def __post_init__(self):
        # v7.1 平衡调整
        if self.path == Path.NIRVANA:
            # 福田道加强：+6影响+3功德（原+5影响+2功德）
            self.influence += 6
            self.merit += 3
        elif self.path == Path.CHARITY:
            self.wealth += 6
        elif self.path == Path.TEMPLE:
            # 土地道略微削弱：+1土地+1财富（原+1土地+2财富）
            self.land += 1
            self.wealth += 1
        elif self.path == Path.CULTURE:
            self.influence += 2
            self.wealth += 2
        elif self.path == Path.DILIGENCE:
            # 勤劳道削弱：只有额外行动点，无其他启动奖励
            self.base_action_points = 3
            self.action_points = 3
        elif self.path == Path.SALVATION:
            self.merit += 5
            self.influence += 2
    
    def update_path_completion(self):
        """每轮检查并更新道路完成状态（修复版）"""
        if self.path == Path.NIRVANA:
            # 福田道小成条件放宽：回向1人即可
            if len(self.transfer_targets) >= 1:
                self.small_path_completed = True
        
        elif self.path == Path.CHARITY:
            if self.total_donated >= 7:
                self.small_path_completed = True
        
        elif self.path == Path.TEMPLE:
            if self.has_built_temple or self.land_donated >= 2:
                self.small_path_completed = True
        
        elif self.path == Path.CULTURE:
            if self.influence >= 5 or len(self.kindness_targets) >= 2:
                self.small_path_completed = True
        
        elif self.path == Path.DILIGENCE:
            # 勤劳道小成条件提高：需要更多行动
            if self.kindness_count >= 4 or self.farming_count >= 4:
                self.small_path_completed = True
        
        elif self.path == Path.SALVATION:
            if self.transfer_count >= 1 or len(self.kindness_targets) >= 1:
                self.small_path_completed = True
    
    def get_current_score(self) -> float:
        base_score = self.merit * 2 + self.influence + self.wealth / 3 + self.land * 2
        path_complete, _, path_bonus = self.check_path_completion()
        if path_complete:
            base_score += path_bonus
        return base_score
    
    def get_rank(self, players: List['Player']) -> int:
        scores = [(p.get_current_score(), p.player_id) for p in players]
        scores.sort(reverse=True)
        for idx, (score, pid) in enumerate(scores):
            if pid == self.player_id:
                return idx + 1
        return len(players)
    
    def get_ascension_cost(self, players: List['Player']) -> Tuple[int, int, int]:
        base_merit = 5
        base_influence = 3
        base_wealth = 3
        
        rank = self.get_rank(players)
        total_players = len(players)
        
        # 动态成本调整
        if rank <= total_players * 0.25:  # 前25%强者
            merit_cost = base_merit + 2
        elif rank > total_players * 0.5:  # 后50%弱者
            merit_cost = base_merit - 2
        else:
            merit_cost = base_merit
        
        return (max(1, merit_cost), base_influence, base_wealth)
    
    def can_ascend(self, players: List['Player'], round_num: int) -> bool:
        if self.has_ascended:
            return False
        if not self.small_path_completed:
            return False
        if round_num < 5:
            return False
        
        merit_cost, inf_cost, wealth_cost = self.get_ascension_cost(players)
        return (self.merit >= merit_cost and 
                self.influence >= inf_cost and 
                self.wealth >= wealth_cost)
    
    def ascend(self, players: List['Player'], round_num: int):
        merit_cost, inf_cost, wealth_cost = self.get_ascension_cost(players)
        
        self.initial_rank = self.get_rank(players)
        
        self.merit -= merit_cost
        self.influence -= inf_cost
        self.wealth -= wealth_cost
        
        self.has_ascended = True
        self.ascension_round = round_num
        
        if self.path == Path.NIRVANA:
            self.ascension_class = AscensionClass.ARHAT
        elif self.path == Path.CHARITY:
            self.ascension_class = AscensionClass.MAHADANAPATI
        elif self.path == Path.TEMPLE:
            self.ascension_class = AscensionClass.TEMPLE_MASTER
        elif self.path == Path.CULTURE:
            self.ascension_class = AscensionClass.MANJUSRI
        elif self.path == Path.DILIGENCE:
            self.ascension_class = AscensionClass.WANDERING_MONK
        elif self.path == Path.SALVATION:
            self.ascension_class = AscensionClass.BODHISATTVA
    
    def check_early_victory(self, players: List['Player']) -> bool:
        if not self.has_ascended:
            return False
        
        rank = self.get_rank(players)
        
        if self.ascension_class == AscensionClass.ARHAT:
            # 放宽条件：回向4人（原5人）
            merit_req = max(4, 12 - (rank - 1) * 2)
            return len(self.transfer_targets) >= 4 and self.merit >= merit_req
        
        elif self.ascension_class == AscensionClass.MAHADANAPATI:
            # 放宽条件：捐献20（原25）
            wealth_max = 3 + rank
            return self.total_donated >= 20 and self.wealth <= wealth_max
        
        elif self.ascension_class == AscensionClass.TEMPLE_MASTER:
            # 放宽条件：捐地4（原5）
            return (self.has_built_temple and 
                    self.land_donated >= 4 and 
                    self.land <= rank)
        
        elif self.ascension_class == AscensionClass.MANJUSRI:
            # 放宽条件：善行4人（原5人）
            inf_req = max(4, 10 - (rank - 1) * 2)
            return self.influence >= inf_req and len(self.kindness_targets) >= 4
        
        elif self.ascension_class == AscensionClass.WANDERING_MONK:
            # 提高条件：善行10+耕作10（原8+8）
            wealth_req = max(2, 8 - (rank - 1) * 2)
            return (self.kindness_count >= 10 and 
                    self.farming_count >= 10 and 
                    self.wealth >= wealth_req)
        
        elif self.ascension_class == AscensionClass.BODHISATTVA:
            # 放宽条件：回向4次（原5次）
            merit_req = max(3, 10 - (rank - 1) * 2)
            all_helped = self.transfer_targets | self.kindness_targets
            return (self.transfer_count >= 4 and 
                    len(all_helped) >= 4 and 
                    self.merit >= merit_req)
        
        return False
    
    def get_ascension_bonus_multiplier(self, action: str) -> float:
        if not self.has_ascended:
            return 1.0
        
        if self.ascension_class == AscensionClass.ARHAT:
            if action == "practice":
                return 0.5
        elif self.ascension_class == AscensionClass.MAHADANAPATI:
            if action == "donate":
                return 1.5
        elif self.ascension_class == AscensionClass.TEMPLE_MASTER:
            if action == "donate_land":
                return 1.5
        elif self.ascension_class == AscensionClass.MANJUSRI:
            if action == "kindness":
                return 1.5
        elif self.ascension_class == AscensionClass.BODHISATTVA:
            if action == "transfer":
                return 2.0
        
        return 1.0
    
    def check_path_completion(self) -> Tuple[bool, str, int]:
        multiplier = 1.0
        if self.num_players == 3:
            multiplier = 1.2
        elif self.num_players >= 5:
            multiplier = 0.9
        
        base_bonus = 25
        small_bonus = 12
        
        if self.path == Path.NIRVANA:
            if len(self.transfer_targets) >= 3 and self.influence_spent >= 4:
                return (True, "福田道", int(base_bonus * multiplier))
            elif len(self.transfer_targets) >= 1:
                self.small_path_completed = True
                return (True, "福田道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.CHARITY:
            if self.total_donated >= 12 and self.influence >= 3:
                return (True, "布施道", int(base_bonus * multiplier))
            elif self.total_donated >= 7:
                self.small_path_completed = True
                return (True, "布施道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.TEMPLE:
            if self.has_built_temple and self.land_donated >= 3:
                return (True, "土地道", int(base_bonus * multiplier))
            elif self.has_built_temple or self.land_donated >= 2:
                self.small_path_completed = True
                return (True, "土地道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.CULTURE:
            if self.influence >= 7 and len(self.kindness_targets) >= 3:
                return (True, "文化道", int(base_bonus * multiplier))
            elif self.influence >= 5 or len(self.kindness_targets) >= 2:
                self.small_path_completed = True
                return (True, "文化道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.DILIGENCE:
            # 勤劳道条件提高
            if self.kindness_count >= 6 and self.farming_count >= 6:
                return (True, "勤劳道", int(base_bonus * multiplier))
            elif self.kindness_count >= 4 or self.farming_count >= 4:
                self.small_path_completed = True
                return (True, "勤劳道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.SALVATION:
            all_helped = self.transfer_targets | self.kindness_targets
            if self.transfer_count >= 3 and len(all_helped) >= 2:
                return (True, "渡化道", int(base_bonus * multiplier))
            elif self.transfer_count >= 1 or len(all_helped) >= 1:
                self.small_path_completed = True
                return (True, "渡化道（小成）", int(small_bonus * multiplier))
        
        return (False, "", 0)
    
    def get_final_score(self) -> float:
        base_score = self.merit * 2 + self.influence + self.wealth / 3 + self.land * 2
        path_complete, path_name, path_bonus = self.check_path_completion()
        if path_complete:
            self.score_sources[ScoreSource.PATH] = path_bonus
        return base_score + path_bonus
    
    def apply_ascension_abilities(self):
        if not self.has_ascended:
            return
        
        if self.ascension_class == AscensionClass.ARHAT:
            self.add_merit(1, ScoreSource.ASCENSION)
        elif self.ascension_class == AscensionClass.MAHADANAPATI:
            self.wealth += 2
        elif self.ascension_class == AscensionClass.TEMPLE_MASTER:
            if self.has_built_temple:
                self.add_merit(1, ScoreSource.ASCENSION)
        elif self.ascension_class == AscensionClass.MANJUSRI:
            if self.influence >= 8:
                self.add_merit(1, ScoreSource.ASCENSION)
    
    def add_merit(self, amount: int, source: ScoreSource):
        self.merit += amount
        self.score_sources[source] += amount * 2

# ===================================================================
#                           AI决策
# ===================================================================

class AIDecisionMaker:
    @staticmethod
    def decide_action(player: Player, game: Dict, others: List[Player]) -> Optional[str]:
        strategy = player.strategy
        
        if strategy == AIStrategy.RANDOM:
            return AIDecisionMaker._random_action(player, others)
        elif strategy == AIStrategy.AGGRESSIVE:
            return AIDecisionMaker._aggressive_action(player, others, game)
        elif strategy == AIStrategy.CONSERVATIVE:
            return AIDecisionMaker._conservative_action(player, others)
        elif strategy == AIStrategy.BALANCED:
            return AIDecisionMaker._balanced_action(player, others, game)
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
    def _aggressive_action(player: Player, others: List[Player], game: Dict) -> Optional[str]:
        if player.has_ascended:
            action = AIDecisionMaker._pursue_early_victory(player, others)
            if action:
                return action
        
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
    def _balanced_action(player: Player, others: List[Player], game: Dict) -> Optional[str]:
        if player.has_ascended:
            action = AIDecisionMaker._pursue_early_victory(player, others)
            if action:
                return action
        
        path = player.path
        if path == Path.NIRVANA:
            if player.merit >= 2 and others and len(player.transfer_targets) < 3:
                return "transfer"
            if player.influence >= 2:
                return "practice"
        elif path == Path.CHARITY:
            if player.wealth >= 3:
                return "donate"
            return "farm"
        elif path == Path.TEMPLE:
            if not player.has_built_temple and player.land >= 2:
                return "build_temple_land"
            if player.land >= 1 and player.land_donated < 3:
                return "donate_land"
            return "farm"
        elif path == Path.CULTURE:
            if player.wealth >= 1 and others and len(player.kindness_targets) < 3:
                return "kindness"
            if player.influence >= 2:
                return "practice"
        elif path == Path.DILIGENCE:
            if player.kindness_count < 6 and player.wealth >= 1 and others:
                return "kindness"
            if player.farming_count < 6:
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
            if player.has_ascended:
                action = AIDecisionMaker._pursue_early_victory(player, others)
                if action:
                    return action
            return AIDecisionMaker._balanced_action(player, others, game)
        else:
            if player.has_ascended:
                action = AIDecisionMaker._pursue_early_victory(player, others)
                if action:
                    return action
            if not player.has_built_temple and player.land >= 2:
                return "build_temple_land"
            if player.wealth >= 3:
                return "donate"
            if player.merit >= 2 and others:
                return "transfer"
        
        return AIDecisionMaker._balanced_action(player, others, game)
    
    @staticmethod
    def _pursue_early_victory(player: Player, others: List[Player]) -> Optional[str]:
        if player.ascension_class == AscensionClass.ARHAT:
            if len(player.transfer_targets) < 4 and player.merit >= 2 and others:
                return "transfer"
            if player.influence >= 2:
                return "practice"
        
        elif player.ascension_class == AscensionClass.MAHADANAPATI:
            if player.total_donated < 20 and player.wealth >= 3:
                return "donate"
            return "farm"
        
        elif player.ascension_class == AscensionClass.TEMPLE_MASTER:
            if player.land_donated < 4 and player.land >= 1:
                return "donate_land"
            return "farm"
        
        elif player.ascension_class == AscensionClass.MANJUSRI:
            if len(player.kindness_targets) < 4 and player.wealth >= 1 and others:
                return "kindness"
            if player.influence < 8 and player.influence >= 2:
                return "practice"
        
        elif player.ascension_class == AscensionClass.WANDERING_MONK:
            if player.kindness_count < 10 and player.wealth >= 1 and others:
                return "kindness"
            if player.farming_count < 10:
                return "farm"
        
        elif player.ascension_class == AscensionClass.BODHISATTVA:
            if player.transfer_count < 4 and player.merit >= 2 and others:
                return "transfer"
            all_helped = player.transfer_targets | player.kindness_targets
            if len(all_helped) < 4 and player.wealth >= 1 and others:
                return "kindness"
        
        return None
    
    @staticmethod
    def decide_ascension(player: Player, players: List[Player], round_num: int) -> bool:
        if not player.can_ascend(players, round_num):
            return False
        
        strategy = player.strategy
        
        if strategy == AIStrategy.RANDOM:
            return random.random() < 0.6  # 提高转职倾向
        
        merit_cost, inf_cost, wealth_cost = player.get_ascension_cost(players)
        rank = player.get_rank(players)
        total_players = len(players)
        
        if strategy == AIStrategy.AGGRESSIVE:
            # 激进型：更容易转职
            if rank > total_players * 0.5:  # 弱者
                return True
            elif player.merit >= merit_cost + 1:
                return True
            return random.random() < 0.5
        
        if strategy == AIStrategy.CONSERVATIVE:
            # 保守型：更谨慎但也会转职
            if rank > total_players * 0.5 and player.merit >= merit_cost + 2:
                return True
            return random.random() < 0.3
        
        if strategy == AIStrategy.BALANCED:
            # 平衡型：根据情况
            if rank > total_players * 0.5:
                return True
            elif player.merit >= merit_cost + 1:
                return random.random() < 0.7
            return random.random() < 0.4
        
        if strategy == AIStrategy.OPPORTUNISTIC:
            # 机会型：后期更容易转职
            if round_num >= 7:
                return True
            elif rank > total_players * 0.5:
                return True
            return random.random() < 0.5
        
        return False
    
    @staticmethod
    def decide_event_option(player: Player, event: EventCard) -> str:
        return random.choice(["A", "B"])

# ===================================================================
#                           游戏模拟器
# ===================================================================

class GameSimulator:
    def __init__(self, num_players: int = 4):
        self.num_players = num_players
    
    def create_game(self, paths: List[Path], strategies: List[AIStrategy]) -> Dict:
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
            "early_victory": False,
            "early_victor": None,
            "early_victor_path": None,
        }
    
    def process_event(self, game: Dict, event: EventCard):
        for p in game["players"]:
            option = AIDecisionMaker.decide_event_option(p, event)
            
            if event.id == 1:
                if option == "A":
                    p.wealth += 3
                else:
                    p.add_merit(1, ScoreSource.EVENT)
                    p.influence += 1
            elif event.id == 2:
                if option == "A":
                    p.add_merit(2, ScoreSource.EVENT)
                else:
                    p.influence += 2
            elif event.id == 3:
                if option == "A":
                    p.wealth = max(0, p.wealth - 3)
                else:
                    p.merit = max(0, p.merit - 2)
            elif event.id == 4:
                if option == "A" and p.wealth >= 2:
                    p.wealth -= 2
                    p.add_merit(3, ScoreSource.EVENT)
            elif event.id == 5:
                if option == "A" and p.influence >= 1:
                    p.influence -= 1
                    p.add_merit(2, ScoreSource.EVENT)
                else:
                    p.add_merit(1, ScoreSource.EVENT)
            elif event.id == 6:
                if option == "A" and p.wealth >= 3:
                    p.wealth -= 3
                    p.add_merit(4, ScoreSource.EVENT)
            elif event.id == 7:
                if option == "A":
                    p.wealth += 3
                elif p.wealth >= 3:
                    p.wealth -= 3
                    p.add_merit(2, ScoreSource.EVENT)
            elif event.id == 8:
                if option == "A" and p.influence >= 5:
                    p.add_merit(2, ScoreSource.EVENT)
                else:
                    p.influence += 1
            elif event.id == 9:
                if option == "A":
                    p.wealth += 2
                else:
                    p.add_merit(1, ScoreSource.EVENT)
            elif event.id == 10:
                if option == "A":
                    p.wealth = max(0, p.wealth - 3)
                else:
                    p.merit = max(0, p.merit - 1)
                    p.influence = max(0, p.influence - 1)
            elif event.id == 11:
                if option == "A":
                    p.wealth = max(0, p.wealth - 4)
                else:
                    p.influence = max(0, p.influence - 2)
            elif event.id == 12:
                if option == "A":
                    p.merit = max(0, p.merit - 2)
                else:
                    p.influence = max(0, p.influence - 2)
            elif event.id == 13:
                if option == "A":
                    p.add_merit(3, ScoreSource.EVENT)
                else:
                    p.add_merit(2, ScoreSource.EVENT)
                    p.influence += 1
            elif event.id == 14:
                if option == "A":
                    p.add_merit(2, ScoreSource.EVENT)
                    p.influence += 1
                else:
                    p.influence += 3
            elif event.id == 15:
                if option == "A":
                    p.wealth += 2
                    p.add_merit(1, ScoreSource.EVENT)
                else:
                    p.add_merit(1, ScoreSource.EVENT)
                    p.influence += 2
    
    def production_phase(self, game: Dict):
        for p in game["players"]:
            p.wealth += 2
            p.influence += 1
            
            # 土地道和勤劳道土地产出削弱
            land_bonus = 1 if p.path == Path.TEMPLE else 0
            p.wealth += p.land * (1 + land_bonus)
            
            if p.has_ascended and p.ascension_class == AscensionClass.TEMPLE_MASTER:
                p.wealth += p.land
    
    def action_phase(self, game: Dict):
        players = game["players"]
        
        for p in players:
            p.action_points = p.base_action_points
            if p.has_ascended and p.ascension_class == AscensionClass.WANDERING_MONK:
                p.action_points += 1
            
            others = [o for o in players if o.player_id != p.player_id]
            
            while p.action_points > 0:
                action = AIDecisionMaker.decide_action(p, game, others)
                if action is None:
                    break
                
                self.execute_action(p, action, game, others)
                p.action_points -= 1
    
    def execute_action(self, player: Player, action: str, game: Dict, others: List[Player]):
        multiplier = player.get_ascension_bonus_multiplier(action)
        
        if action == "donate":
            if player.wealth >= 3:
                player.wealth -= 3
                player.total_donated += 3
                merit_gain = int(1 * multiplier)
                player.add_merit(merit_gain, ScoreSource.MECHANISM)
                
                if player.has_ascended and player.ascension_class == AscensionClass.MAHADANAPATI:
                    if others:
                        target = random.choice(others)
                        target.add_merit(1, ScoreSource.INTERACTION)
        
        elif action == "practice":
            cost = 2
            if player.has_ascended and player.ascension_class == AscensionClass.ARHAT:
                cost = 1
            
            if player.influence >= cost:
                player.influence -= cost
                player.influence_spent += cost
                merit_gain = int(1 * multiplier)
                player.add_merit(merit_gain, ScoreSource.MECHANISM)
        
        elif action == "kindness":
            if player.wealth >= 1 and others:
                player.wealth -= 1
                player.kindness_count += 1
                merit_gain = int(1 * multiplier)
                player.add_merit(merit_gain, ScoreSource.MECHANISM)
                
                target = random.choice(others)
                target.add_merit(1, ScoreSource.INTERACTION)
                player.kindness_targets.add(target.player_id)
                
                if player.has_ascended and player.ascension_class == AscensionClass.MANJUSRI:
                    player.influence += 1
                
                if player.has_ascended and player.ascension_class == AscensionClass.WANDERING_MONK:
                    player.wealth += 1
        
        elif action == "transfer":
            if player.merit >= 2 and others:
                player.merit -= 2
                player.transfer_count += 1
                
                target_gain = int(3 * multiplier)
                target = random.choice(others)
                target.add_merit(target_gain, ScoreSource.INTERACTION)
                player.transfer_targets.add(target.player_id)
                
                player.influence += 1
                
                if player.has_ascended and player.ascension_class == AscensionClass.ARHAT:
                    player.influence += 1
                
                if player.has_ascended and player.ascension_class == AscensionClass.BODHISATTVA:
                    player.influence += 1
                    player.add_merit(1, ScoreSource.ASCENSION)
        
        elif action == "farm":
            base_gain = 2
            # 勤劳道耕作削弱：不再有额外收益
            if player.path == Path.TEMPLE:
                base_gain += 1
            if player.has_ascended and player.ascension_class == AscensionClass.WANDERING_MONK:
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
                merit_gain = 3
                if player.has_ascended and player.ascension_class == AscensionClass.TEMPLE_MASTER:
                    merit_gain = 4
                player.add_merit(merit_gain, ScoreSource.MECHANISM)
    
    def path_completion_phase(self, game: Dict):
        """每轮检查道路完成状态（新增）"""
        for p in game["players"]:
            p.update_path_completion()
    
    def ascension_phase(self, game: Dict):
        if game["round"] < 5:
            return
        
        players = game["players"]
        for p in players:
            if p.can_ascend(players, game["round"]):
                if AIDecisionMaker.decide_ascension(p, players, game["round"]):
                    p.ascend(players, game["round"])
    
    def check_early_victory(self, game: Dict) -> Optional[Player]:
        players = game["players"]
        for p in players:
            if p.check_early_victory(players):
                return p
        return None
    
    def run_game(self, paths: List[Path], strategies: List[AIStrategy]) -> Dict:
        game = self.create_game(paths, strategies)
        
        for round_num in range(1, 11):
            game["round"] = round_num
            
            if game["event_deck"]:
                event = game["event_deck"].pop()
                self.process_event(game, event)
            
            self.production_phase(game)
            
            for p in game["players"]:
                p.apply_ascension_abilities()
            
            self.action_phase(game)
            
            # 每轮检查道路完成状态（修复）
            self.path_completion_phase(game)
            
            # 转职阶段（第5轮后）
            self.ascension_phase(game)
            
            # 检查提前胜利
            early_victor = self.check_early_victory(game)
            if early_victor:
                game["early_victory"] = True
                game["early_victor"] = early_victor.player_id
                game["early_victor_path"] = early_victor.path.value
                break
        
        results = []
        for p in game["players"]:
            score = p.get_final_score()
            path_complete, path_name, path_bonus = p.check_path_completion()
            
            results.append({
                "player_id": p.player_id,
                "path": p.path.value,
                "strategy": p.strategy.value,
                "ascended": p.has_ascended,
                "ascension_class": p.ascension_class.value if p.ascension_class else "",
                "ascension_round": p.ascension_round,
                "initial_rank": p.initial_rank,
                "score": round(score, 1),
                "merit": p.merit,
                "influence": p.influence,
                "wealth": p.wealth,
                "path_completed": path_name if path_complete else "",
                "path_bonus": path_bonus,
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        winner = results[0]
        
        return {
            "winner_path": winner["path"],
            "winner_strategy": winner["strategy"],
            "winner_ascended": winner["ascended"],
            "early_victory": game["early_victory"],
            "early_victor_path": game.get("early_victor_path", ""),
            "results": results,
        }

# ===================================================================
#                           全面测试器
# ===================================================================

class ComprehensiveTester:
    def __init__(self, num_players: int = 4):
        self.num_players = num_players
        self.simulator = GameSimulator(num_players)
        
        self.path_wins = defaultdict(int)
        self.path_games = defaultdict(int)
        self.strategy_wins = defaultdict(int)
        self.strategy_games = defaultdict(int)
        self.ascension_count = defaultdict(int)
        self.ascension_wins = defaultdict(int)
        self.early_victory_count = 0
        self.underdog_wins = 0
        self.underdog_ascensions = 0
        self.total_games = 0
    
    def run_test(self, num_games: int):
        all_paths = list(Path)[:self.num_players]
        path_combos = list(permutations(all_paths))
        
        games_per_combo = max(1, num_games // len(path_combos))
        
        print(f"  Running {len(path_combos)} path combos x {games_per_combo} games...")
        
        for paths in path_combos:
            for _ in range(games_per_combo):
                strategies = [random.choice(ALL_STRATEGIES) for _ in range(self.num_players)]
                self._run_and_record(list(paths), strategies)
    
    def _run_and_record(self, paths: List[Path], strategies: List[AIStrategy]):
        result = self.simulator.run_game(paths, strategies)
        self.total_games += 1
        
        winner_path = result["winner_path"]
        winner_strategy = result["winner_strategy"]
        
        self.path_wins[winner_path] += 1
        self.strategy_wins[winner_strategy] += 1
        
        for r in result["results"]:
            path = r["path"]
            strategy = r["strategy"]
            self.path_games[path] += 1
            self.strategy_games[strategy] += 1
            
            if r["ascended"]:
                self.ascension_count[path] += 1
                if r["path"] == winner_path:
                    self.ascension_wins[path] += 1
                
                if r["initial_rank"] > self.num_players * 0.5:
                    self.underdog_ascensions += 1
                    if r["path"] == winner_path:
                        self.underdog_wins += 1
        
        if result["early_victory"]:
            self.early_victory_count += 1
    
    def get_report(self) -> Dict:
        report = {
            "num_players": self.num_players,
            "total_games": self.total_games,
            "path_win_rates": {},
            "strategy_win_rates": {},
            "ascension_rates": {},
            "ascension_win_rates": {},
            "early_victory_rate": 0,
            "underdog_win_rate": 0,
            "balance_score": 0,
        }
        
        target_rate = 100 / self.num_players
        
        for path in self.path_games:
            games = self.path_games[path]
            wins = self.path_wins.get(path, 0)
            rate = wins / games * 100 if games > 0 else 0
            report["path_win_rates"][path] = round(rate, 2)
        
        for strategy in self.strategy_games:
            games = self.strategy_games[strategy]
            wins = self.strategy_wins.get(strategy, 0)
            rate = wins / games * 100 if games > 0 else 0
            report["strategy_win_rates"][strategy] = round(rate, 2)
        
        for path in self.path_games:
            games = self.path_games[path]
            ascensions = self.ascension_count.get(path, 0)
            rate = ascensions / games * 100 if games > 0 else 0
            report["ascension_rates"][path] = round(rate, 2)
        
        for path in self.ascension_count:
            ascensions = self.ascension_count[path]
            wins = self.ascension_wins.get(path, 0)
            rate = wins / ascensions * 100 if ascensions > 0 else 0
            report["ascension_win_rates"][path] = round(rate, 2)
        
        report["early_victory_rate"] = round(self.early_victory_count / self.total_games * 100, 2) if self.total_games > 0 else 0
        report["underdog_win_rate"] = round(self.underdog_wins / self.underdog_ascensions * 100, 2) if self.underdog_ascensions > 0 else 0
        
        if report["path_win_rates"]:
            deviations = [abs(rate - target_rate) for rate in report["path_win_rates"].values()]
            report["balance_score"] = round(sum(deviations) / len(deviations), 2)
        
        return report
    
    def print_report(self):
        report = self.get_report()
        target_rate = 100 / self.num_players
        
        print(f"\n{'='*70}")
        print(f"                    TEST REPORT - {self.num_players} PLAYERS (v7.1)")
        print(f"{'='*70}")
        print(f"Total games: {report['total_games']}")
        print(f"Target win rate: {target_rate:.1f}%")
        print(f"Balance score: {report['balance_score']:.2f} (lower is better, target <5)")
        
        print(f"\n  [Path Win Rates]")
        for path, rate in sorted(report["path_win_rates"].items(), key=lambda x: -x[1]):
            deviation = rate - target_rate
            status = "[OK]" if abs(deviation) <= 5 else "[!]" if abs(deviation) <= 10 else "[X]"
            print(f"    {path}: {rate}% ({deviation:+.1f}%) {status}")
        
        print(f"\n  [Strategy Win Rates]")
        for strategy, rate in sorted(report["strategy_win_rates"].items(), key=lambda x: -x[1]):
            print(f"    {strategy}: {rate}%")
        
        print(f"\n  [Ascension Rates] (转职率)")
        for path, rate in sorted(report["ascension_rates"].items(), key=lambda x: -x[1]):
            print(f"    {path}: {rate}%")
        
        print(f"\n  [Ascension Win Rates] (转职玩家胜率)")
        for path, rate in sorted(report["ascension_win_rates"].items(), key=lambda x: -x[1]):
            print(f"    {path}: {rate}%")
        
        print(f"\n  [Key Metrics]")
        print(f"    Early victory rate: {report['early_victory_rate']}%")
        print(f"    Underdog win rate: {report['underdog_win_rate']}% (弱者转职后胜率)")
        
        return report

# ===================================================================
#                           主程序
# ===================================================================

def main():
    print("=" * 70)
    print("       Path to Salvation v7.1 - Fixed Comprehensive Test")
    print("=" * 70)
    
    all_reports = {}
    
    for num_players in [4, 5, 6]:
        print(f"\n{'='*70}")
        print(f"Testing {num_players}-player game...")
        print(f"{'='*70}")
        
        tester = ComprehensiveTester(num_players)
        
        start = time.time()
        tester.run_test(10000)
        elapsed = time.time() - start
        
        print(f"  Time: {elapsed:.2f}s ({tester.total_games / elapsed:.1f} games/s)")
        
        report = tester.print_report()
        all_reports[f"{num_players}p"] = report
    
    with open("v7_fixed_test_results.json", "w", encoding="utf-8") as f:
        json.dump(all_reports, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*70}")
    print("Results saved to v7_fixed_test_results.json")
    print(f"{'='*70}")
    
    for key, report in all_reports.items():
        balance_score = report["balance_score"]
        if balance_score > 5:
            print(f"\n[WARNING] {key}: Balance score {balance_score} > 5, needs adjustment!")
        else:
            print(f"\n[OK] {key}: Balance score {balance_score} <= 5, acceptable!")
    
    return all_reports

if __name__ == "__main__":
    main()
