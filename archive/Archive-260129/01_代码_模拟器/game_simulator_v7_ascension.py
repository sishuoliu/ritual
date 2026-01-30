# -*- coding: utf-8 -*-
"""
救赎之路 v7.0 - 转职系统测试版
基于v6.3，增加转职机制：
1. 小成后可转职
2. 转职成本动态调整（帮助弱者）
3. 转职后提前胜利条件
4. 游戏延长到10轮
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

class Path(Enum):
    NIRVANA = "福田道"
    CHARITY = "布施道"
    TEMPLE = "土地道"
    CULTURE = "文化道"
    DILIGENCE = "勤劳道"
    SALVATION = "渡化道"

class AscensionClass(Enum):
    """转职职业"""
    ARHAT = "罗汉"           # 福田道
    MAHADANAPATI = "大檀越"  # 布施道
    TEMPLE_MASTER = "舍宅主" # 土地道
    MANJUSRI = "文殊化身"    # 文化道
    WANDERING_MONK = "行脚僧" # 勤劳道
    BODHISATTVA = "菩萨"     # 渡化道

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

PLAYER_CONFIG = {
    3: [Path.NIRVANA, Path.CHARITY, Path.CULTURE],
    4: [Path.NIRVANA, Path.CHARITY, Path.TEMPLE, Path.CULTURE],
    5: [Path.NIRVANA, Path.CHARITY, Path.TEMPLE, Path.CULTURE, Path.DILIGENCE],
    6: [Path.NIRVANA, Path.CHARITY, Path.TEMPLE, Path.CULTURE, Path.DILIGENCE, Path.SALVATION],
}

# ═══════════════════════════════════════════════════════════════════
#                           事件卡（30张）
# ═══════════════════════════════════════════════════════════════════

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
    EventCard(8, "科举", "世俗", 2, "影响≥5:+2功德", "+1影响"),
    EventCard(9, "集市", "世俗", 2, "+2财富", "+1功德"),
    EventCard(10, "旱灾", "灾难", 2, "-3财富", "-1功德-1影响"),
    EventCard(11, "盗匪", "灾难", 2, "-4财富", "-2影响"),
    EventCard(12, "瘟疫", "灾难", 2, "-2功德", "-2影响"),
    EventCard(13, "高僧", "机缘", 2, "+3功德", "+2功德+1影响"),
    EventCard(14, "顿悟", "机缘", 2, "+2功德+1影响", "+3影响"),
    EventCard(15, "福报", "机缘", 2, "+2财富+1功德", "+1功德+2影响"),
]

def build_event_deck() -> List[EventCard]:
    deck = []
    for card in EVENT_CARDS:
        for _ in range(card.copies):
            deck.append(card)
    random.shuffle(deck)
    return deck

# ═══════════════════════════════════════════════════════════════════
#                           玩家类（v7.0转职版）
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Player:
    player_id: int
    path: Path
    strategy: AIStrategy
    num_players: int = 4
    
    # 4种资源
    wealth: int = 6
    merit: int = 2
    influence: int = 3
    land: int = 1
    
    base_action_points: int = 2
    action_points: int = 2
    
    # 行动追踪
    total_donated: int = 0
    influence_spent: int = 0
    kindness_count: int = 0
    kindness_targets: Set = field(default_factory=set)
    transfer_count: int = 0
    transfer_targets: Set = field(default_factory=set)
    farming_count: int = 0
    land_donated: int = 0
    has_built_temple: bool = False
    
    # 转职相关
    has_ascended: bool = False
    ascension_class: Optional[AscensionClass] = None
    small_path_completed: bool = False
    
    # 得分来源
    score_sources: Dict = field(default_factory=lambda: {
        ScoreSource.MECHANISM: 0,
        ScoreSource.EVENT: 0,
        ScoreSource.INTERACTION: 0,
        ScoreSource.PATH: 0,
        ScoreSource.ASCENSION: 0,
    })
    
    def __post_init__(self):
        """应用道路启动奖励"""
        if self.path == Path.NIRVANA:
            self.influence += 5
            self.merit += 2
        elif self.path == Path.CHARITY:
            self.wealth += 6
        elif self.path == Path.TEMPLE:
            self.land += 1
            self.wealth += 2
        elif self.path == Path.CULTURE:
            self.influence += 2
            self.wealth += 2
        elif self.path == Path.DILIGENCE:
            self.base_action_points = 3
            self.action_points = 3
        elif self.path == Path.SALVATION:
            self.merit += 5
            self.influence += 2
    
    def get_current_score(self) -> float:
        """计算当前得分（用于排名）"""
        base_score = self.merit * 2 + self.influence + self.wealth / 3 + self.land * 2
        path_complete, _, path_bonus = self.check_path_completion()
        if path_complete:
            base_score += path_bonus
        return base_score
    
    def get_rank(self, players: List['Player']) -> int:
        """获取当前排名（1=最高，4=最低）"""
        scores = [(p.get_current_score(), p.player_id) for p in players]
        scores.sort(reverse=True)
        for idx, (score, pid) in enumerate(scores):
            if pid == self.player_id:
                return idx + 1
        return len(players)
    
    def get_ascension_cost(self, players: List['Player']) -> Tuple[int, int, int]:
        """计算转职成本（动态调整）"""
        base_merit = 5
        base_influence = 3
        base_wealth = 3
        
        rank = self.get_rank(players)
        total_players = len(players)
        
        # 排名调整
        if rank <= total_players * 0.25:  # 前25%
            merit_cost = base_merit + 2
        elif rank >= total_players * 0.5:  # 后50%
            merit_cost = base_merit - 2
        else:
            merit_cost = base_merit
        
        return (max(1, merit_cost), base_influence, base_wealth)
    
    def can_ascend(self, players: List['Player'], round_num: int) -> bool:
        """检查是否可以转职"""
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
    
    def ascend(self, players: List['Player']):
        """执行转职"""
        merit_cost, inf_cost, wealth_cost = self.get_ascension_cost(players)
        
        self.merit -= merit_cost
        self.influence -= inf_cost
        self.wealth -= wealth_cost
        
        self.has_ascended = True
        
        # 根据道路分配转职职业
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
        """检查提前胜利条件"""
        if not self.has_ascended:
            return False
        
        rank = self.get_rank(players)
        
        if self.ascension_class == AscensionClass.ARHAT:
            # 回向5人 + 功德≥(15-排名×2)
            merit_req = max(5, 15 - (rank - 1) * 2)
            return len(self.transfer_targets) >= 5 and self.merit >= merit_req
        
        elif self.ascension_class == AscensionClass.MAHADANAPATI:
            # 累计捐献≥25 + 财富≤(2+排名)
            wealth_max = 2 + rank
            return self.total_donated >= 25 and self.wealth <= wealth_max
        
        elif self.ascension_class == AscensionClass.TEMPLE_MASTER:
            # 建寺 + 捐地≥5 + 土地≤排名
            return (self.has_built_temple and 
                    self.land_donated >= 5 and 
                    self.land <= rank)
        
        elif self.ascension_class == AscensionClass.MANJUSRI:
            # 影响≥(12-排名×2) + 善行5人
            inf_req = max(4, 12 - (rank - 1) * 2)
            return self.influence >= inf_req and len(self.kindness_targets) >= 5
        
        elif self.ascension_class == AscensionClass.WANDERING_MONK:
            # 善行≥8 + 耕作≥8 + 财富≥(10-排名×2)
            wealth_req = max(2, 10 - (rank - 1) * 2)
            return (self.kindness_count >= 8 and 
                    self.farming_count >= 8 and 
                    self.wealth >= wealth_req)
        
        elif self.ascension_class == AscensionClass.BODHISATTVA:
            # 回向≥5 + 渡化4人 + 功德≥(12-排名×2)
            merit_req = max(4, 12 - (rank - 1) * 2)
            all_helped = self.transfer_targets | self.kindness_targets
            return (self.transfer_count >= 5 and 
                    len(all_helped) >= 4 and 
                    self.merit >= merit_req)
        
        return False
    
    def get_ascension_bonus_multiplier(self, action: str) -> float:
        """获取转职后的能力加成"""
        if not self.has_ascended:
            return 1.0
        
        if self.ascension_class == AscensionClass.ARHAT:
            if action == "practice":
                return 0.5  # 消耗-1影响（2→1）
            elif action == "transfer":
                return 1.0  # 额外+1影响在execute中处理
        
        elif self.ascension_class == AscensionClass.MAHADANAPATI:
            if action == "donate":
                return 1.5  # 效率+50%
        
        elif self.ascension_class == AscensionClass.TEMPLE_MASTER:
            if action == "donate_land":
                return 1.5  # 效率+50%
        
        elif self.ascension_class == AscensionClass.MANJUSRI:
            if action == "kindness":
                return 1.5  # 效率+50%
        
        elif self.ascension_class == AscensionClass.WANDERING_MONK:
            if action == "farm":
                return 1.0  # 收益+1在execute中处理
        
        elif self.ascension_class == AscensionClass.BODHISATTVA:
            if action == "transfer":
                return 2.0  # 效率+100%
        
        return 1.0
    
    def check_path_completion(self) -> Tuple[bool, str, int]:
        """检查道路完成"""
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
            if self.kindness_count >= 5 and self.farming_count >= 5:
                return (True, "勤劳道", int(base_bonus * multiplier))
            elif self.kindness_count >= 3 or self.farming_count >= 3:
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
        """计算最终得分"""
        base_score = self.merit * 2 + self.influence + self.wealth / 3 + self.land * 2
        
        path_complete, path_name, path_bonus = self.check_path_completion()
        if path_complete:
            self.score_sources[ScoreSource.PATH] = path_bonus
        
        return base_score + path_bonus
    
    def apply_ascension_abilities(self):
        """应用转职后的自动能力（每轮）"""
        if not self.has_ascended:
            return
        
        if self.ascension_class == AscensionClass.ARHAT:
            # 功德回向：每轮+1功德
            self.add_merit(1, ScoreSource.ASCENSION)
        
        elif self.ascension_class == AscensionClass.MAHADANAPATI:
            # 无尽藏：每轮+2财富
            self.wealth += 2
        
        elif self.ascension_class == AscensionClass.TEMPLE_MASTER:
            # 土地供养：每块土地额外+1财富（在production中处理）
            # 寺院经济：建寺后每轮+1功德
            if self.has_built_temple:
                self.add_merit(1, ScoreSource.ASCENSION)
        
        elif self.ascension_class == AscensionClass.MANJUSRI:
            # 声名远播：影响≥8时每轮+1功德
            if self.influence >= 8:
                self.add_merit(1, ScoreSource.ASCENSION)
        
        elif self.ascension_class == AscensionClass.WANDERING_MONK:
            # 行脚修行：每轮额外+1行动点（在action_phase中处理）
            pass
        
        elif self.ascension_class == AscensionClass.BODHISATTVA:
            # 无自动能力
            pass
    
    def add_merit(self, amount: int, source: ScoreSource):
        self.merit += amount
        self.score_sources[source] += amount * 2

# ═══════════════════════════════════════════════════════════════════
#                           多策略AI决策
# ═══════════════════════════════════════════════════════════════════

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
        # 如果转职了，优先达成提前胜利条件
        if player.has_ascended:
            return AIDecisionMaker._pursue_early_victory(player, others)
        
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
        # 如果转职了，优先达成提前胜利条件
        if player.has_ascended:
            return AIDecisionMaker._pursue_early_victory(player, others)
        
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
            if player.kindness_count < 5 and player.wealth >= 1 and others:
                return "kindness"
            if player.farming_count < 5:
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
                return AIDecisionMaker._pursue_early_victory(player, others)
            return AIDecisionMaker._balanced_action(player, others, game)
        else:
            if player.has_ascended:
                return AIDecisionMaker._pursue_early_victory(player, others)
            if not player.has_built_temple and player.land >= 2:
                return "build_temple_land"
            if player.wealth >= 3:
                return "donate"
            if player.merit >= 2 and others:
                return "transfer"
        
        return AIDecisionMaker._balanced_action(player, others, game)
    
    @staticmethod
    def _pursue_early_victory(player: Player, others: List[Player]) -> Optional[str]:
        """转职后追求提前胜利"""
        if player.ascension_class == AscensionClass.ARHAT:
            # 需要回向5人
            if len(player.transfer_targets) < 5 and player.merit >= 2 and others:
                return "transfer"
            if player.influence >= 2:
                return "practice"
        
        elif player.ascension_class == AscensionClass.MAHADANAPATI:
            # 需要累计捐献≥25
            if player.total_donated < 25 and player.wealth >= 3:
                return "donate"
            return "farm"
        
        elif player.ascension_class == AscensionClass.TEMPLE_MASTER:
            # 需要捐地≥5
            if player.land_donated < 5 and player.land >= 1:
                return "donate_land"
            return "farm"
        
        elif player.ascension_class == AscensionClass.MANJUSRI:
            # 需要善行5人
            if len(player.kindness_targets) < 5 and player.wealth >= 1 and others:
                return "kindness"
            if player.influence < 8:
                if player.influence >= 2:
                    return "practice"
        
        elif player.ascension_class == AscensionClass.WANDERING_MONK:
            # 需要善行≥8 + 耕作≥8
            if player.kindness_count < 8 and player.wealth >= 1 and others:
                return "kindness"
            if player.farming_count < 8:
                return "farm"
        
        elif player.ascension_class == AscensionClass.BODHISATTVA:
            # 需要回向≥5 + 渡化4人
            if player.transfer_count < 5 and player.merit >= 2 and others:
                return "transfer"
            all_helped = player.transfer_targets | player.kindness_targets
            if len(all_helped) < 4 and player.wealth >= 1 and others:
                return "kindness"
        
        return None
    
    @staticmethod
    def decide_ascension(player: Player, players: List[Player], round_num: int) -> bool:
        """决定是否转职"""
        if not player.can_ascend(players, round_num):
            return False
        
        strategy = player.strategy
        
        if strategy == AIStrategy.RANDOM:
            return random.random() < 0.5
        
        # 计算转职成本
        merit_cost, inf_cost, wealth_cost = player.get_ascension_cost(players)
        rank = player.get_rank(players)
        total_players = len(players)
        
        # 激进型：更容易转职
        if strategy == AIStrategy.AGGRESSIVE:
            if rank >= total_players * 0.5:  # 弱者
                return True
            elif player.merit >= merit_cost + 2:  # 资源充足
                return True
            return False
        
        # 保守型：更谨慎
        if strategy == AIStrategy.CONSERVATIVE:
            if rank >= total_players * 0.5 and player.merit >= merit_cost + 3:
                return True
            return False
        
        # 平衡型：根据情况
        if strategy == AIStrategy.BALANCED:
            if rank >= total_players * 0.5:  # 弱者更容易转职
                return True
            elif player.merit >= merit_cost + 2:
                return random.random() < 0.6
            return False
        
        # 机会型：根据轮数
        if strategy == AIStrategy.OPPORTUNISTIC:
            if round_num >= 7:  # 后期更容易转职
                return True
            elif rank >= total_players * 0.5:
                return True
            return False
        
        return False
    
    @staticmethod
    def decide_event_option(player: Player, event: EventCard) -> str:
        return random.choice(["A", "B"])

# ═══════════════════════════════════════════════════════════════════
#                           游戏模拟器
# ═══════════════════════════════════════════════════════════════════

class GameSimulator:
    def __init__(self, num_players: int = 4, strategy_mode: str = "mixed"):
        if num_players < 3 or num_players > 6:
            raise ValueError("Player count must be 3-6")
        self.num_players = num_players
        self.strategy_mode = strategy_mode
        self.all_paths = PLAYER_CONFIG[num_players]
    
    def _assign_strategies(self) -> List[AIStrategy]:
        if self.strategy_mode == "mixed":
            return [random.choice(list(AIStrategy)) for _ in range(self.num_players)]
        else:
            strategies = list(AIStrategy)
            return [strategies[i % len(strategies)] for i in range(self.num_players)]
    
    def create_game(self, paths: List[Path] = None, strategies: List[AIStrategy] = None) -> Dict:
        if paths is None:
            paths = random.sample(self.all_paths, self.num_players)
        if strategies is None:
            strategies = self._assign_strategies()
        
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
            "temple_fund": 0,
            "early_victory": False,
            "early_victor": None,
        }
    
    def process_event(self, game: Dict, event: EventCard):
        """处理事件（与v6相同）"""
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
        """生产阶段"""
        for p in game["players"]:
            # 基础产出
            p.wealth += 2
            p.influence += 1
            
            # 土地产出
            land_bonus = 1 if p.path in [Path.TEMPLE, Path.DILIGENCE] else 0
            p.wealth += p.land * (1 + land_bonus)
            
            # 转职后能力：土地供养
            if p.has_ascended and p.ascension_class == AscensionClass.TEMPLE_MASTER:
                p.wealth += p.land  # 额外+1财富/土地
    
    def action_phase(self, game: Dict):
        """行动阶段"""
        players = game["players"]
        
        for p in players:
            # 计算行动点
            p.action_points = p.base_action_points
            if p.has_ascended and p.ascension_class == AscensionClass.WANDERING_MONK:
                p.action_points += 1  # 行脚修行：额外+1行动点
            
            others = [o for o in players if o.player_id != p.player_id]
            
            while p.action_points > 0:
                action = AIDecisionMaker.decide_action(p, game, others)
                if action is None:
                    break
                
                self.execute_action(p, action, game, others)
                p.action_points -= 1
    
    def execute_action(self, player: Player, action: str, game: Dict, others: List[Player]):
        """执行行动（包含转职后能力）"""
        multiplier = player.get_ascension_bonus_multiplier(action)
        
        if action == "donate":
            if player.wealth >= 3:
                player.wealth -= 3
                player.total_donated += 3
                merit_gain = int(1 * multiplier)
                player.add_merit(merit_gain, ScoreSource.MECHANISM)
                
                # 大檀越：福田增长
                if player.has_ascended and player.ascension_class == AscensionClass.MAHADANAPATI:
                    if others:
                        target = random.choice(others)
                        target.add_merit(1, ScoreSource.INTERACTION)
        
        elif action == "practice":
            cost = 2
            if player.has_ascended and player.ascension_class == AscensionClass.ARHAT:
                cost = 1  # 法身显现：消耗-1影响
            
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
                
                # 文殊化身：文化传播
                if player.has_ascended and player.ascension_class == AscensionClass.MANJUSRI:
                    player.influence += 1
                
                # 行脚僧：化缘得法
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
                
                # 罗汉：无我布施（额外+1影响）
                if player.has_ascended and player.ascension_class == AscensionClass.ARHAT:
                    player.influence += 1
                else:
                    player.influence += 1  # 普通回向也+1影响
                
                # 菩萨：普度众生（额外+1影响）
                if player.has_ascended and player.ascension_class == AscensionClass.BODHISATTVA:
                    player.influence += 1
                
                # 菩萨：功德回向（帮助他人自己也得功德）
                if player.has_ascended and player.ascension_class == AscensionClass.BODHISATTVA:
                    player.add_merit(1, ScoreSource.ASCENSION)
        
        elif action == "farm":
            base_gain = 2
            if player.path in [Path.TEMPLE, Path.DILIGENCE]:
                base_gain += 1
            if player.has_ascended and player.ascension_class == AscensionClass.WANDERING_MONK:
                base_gain += 1  # 日行千里：收益+1
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
                    merit_gain = 4  # 舍宅为寺：效率+50%
                player.add_merit(merit_gain, ScoreSource.MECHANISM)
    
    def ascension_phase(self, game: Dict):
        """转职阶段（第5轮后）"""
        if game["round"] < 5:
            return
        
        players = game["players"]
        for p in players:
            if p.can_ascend(players, game["round"]):
                if AIDecisionMaker.decide_ascension(p, players, game["round"]):
                    p.ascend(players)
    
    def check_early_victory(self, game: Dict) -> Optional[Player]:
        """检查提前胜利"""
        players = game["players"]
        for p in players:
            if p.check_early_victory(players):
                return p
        return None
    
    def run_game(self, paths: List[Path] = None, strategies: List[AIStrategy] = None) -> Dict:
        """运行一局游戏（10轮）"""
        game = self.create_game(paths, strategies)
        
        for round_num in range(1, 11):  # 10轮
            game["round"] = round_num
            
            # 事件阶段
            if game["event_deck"]:
                event = game["event_deck"].pop()
                self.process_event(game, event)
            
            # 生产阶段
            self.production_phase(game)
            
            # 转职后自动能力
            for p in game["players"]:
                p.apply_ascension_abilities()
            
            # 行动阶段
            self.action_phase(game)
            
            # 转职阶段（第5轮后）
            self.ascension_phase(game)
            
            # 检查提前胜利
            early_victor = self.check_early_victory(game)
            if early_victor:
                game["early_victory"] = True
                game["early_victor"] = early_victor.player_id
                break
        
        # 计算得分
        results = []
        for p in game["players"]:
            score = p.get_final_score()
            path_complete, path_name, path_bonus = p.check_path_completion()
            
            results.append({
                "path": p.path.value,
                "strategy": p.strategy.value,
                "ascended": p.has_ascended,
                "ascension_class": p.ascension_class.value if p.ascension_class else "",
                "score": round(score, 1),
                "merit": p.merit,
                "influence": p.influence,
                "wealth": p.wealth,
                "path_completed": path_name if path_complete else "",
                "path_bonus": path_bonus,
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        winner_path = results[0]["path"]
        winner_ascended = results[0]["ascended"]
        
        return {
            "winner_path": winner_path,
            "winner_ascended": winner_ascended,
            "early_victory": game["early_victory"],
            "early_victor": game["early_victor"],
            "results": results,
        }
    
    def run_batch(self, num_games: int) -> Dict:
        """批量运行游戏"""
        wins = defaultdict(int)
        ascension_stats = defaultdict(int)
        early_victory_count = 0
        path_win_rates = defaultdict(int)
        path_total_games = defaultdict(int)
        ascension_win_rates = defaultdict(int)
        ascension_total_games = defaultdict(int)
        
        for _ in range(num_games):
            result = self.run_game()
            wins[result["winner_path"]] += 1
            path_total_games[result["winner_path"]] += 1
            
            if result["early_victory"]:
                early_victory_count += 1
            
            for r in result["results"]:
                path = r["path"]
                if r["ascended"]:
                    ascension_stats[path] += 1
                    ascension_total_games[path] += 1
                    if r["path"] == result["winner_path"]:
                        ascension_win_rates[path] += 1
        
        stats = {
            "num_games": num_games,
            "num_players": self.num_players,
            "path_win_rates": {},
            "ascension_rates": {},
            "ascension_win_rates": {},
            "early_victory_rate": round(early_victory_count / num_games * 100, 2),
        }
        
        for path in [p.value for p in self.all_paths]:
            if path in wins:
                stats["path_win_rates"][path] = round(wins[path] / num_games * 100, 2)
            if path in ascension_stats:
                stats["ascension_rates"][path] = round(ascension_stats[path] / path_total_games[path] * 100, 2)
            if path in ascension_win_rates:
                stats["ascension_win_rates"][path] = round(ascension_win_rates[path] / ascension_total_games[path] * 100, 2) if ascension_total_games[path] > 0 else 0
        
        return stats

# ═══════════════════════════════════════════════════════════════════
#                           主程序
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("救赎之路 v7.0 - 转职系统测试")
    print("=" * 70)
    
    results_all = {}
    
    for num_players in [4, 5, 6]:
        print(f"\n{'='*60}")
        print(f"Testing {num_players}-player game (v7.0 Ascension)...")
        print(f"{'='*60}")
        
        simulator = GameSimulator(num_players, strategy_mode="mixed")
        
        for batch_size in [100, 1000, 10000]:
            print(f"  Running {batch_size} games...", end=" ")
            start = time.time()
            stats = simulator.run_batch(batch_size)
            elapsed = time.time() - start
            print(f"Done in {elapsed:.2f}s")
            
            key = f"{num_players}p_{batch_size}"
            results_all[key] = stats
        
        stats = results_all[f"{num_players}p_10000"]
        print(f"\n  [10000 games summary - v7.0]")
        print(f"  Path win rates:")
        for path, rate in sorted(stats["path_win_rates"].items(), key=lambda x: -x[1]):
            target = 100 / num_players
            print(f"    {path}: {rate}% (target: {target:.1f}%)")
        print(f"  Ascension rates:")
        for path, rate in sorted(stats["ascension_rates"].items(), key=lambda x: -x[1]):
            print(f"    {path}: {rate}%")
        print(f"  Early victory rate: {stats['early_victory_rate']}%")
        print(f"  Ascension win rates (转职玩家胜率):")
        for path, rate in sorted(stats["ascension_win_rates"].items(), key=lambda x: -x[1]):
            print(f"    {path}: {rate}%")
    
    with open("simulation_results_v7_ascension.json", "w", encoding="utf-8") as f:
        json.dump(results_all, f, ensure_ascii=False, indent=2)
    
    print("\n\nResults saved to simulation_results_v7_ascension.json")
    return results_all


if __name__ == "__main__":
    main()
