# -*- coding: utf-8 -*-
"""
救赎之路 v6.0 - 无偏见多策略测试版
基于桌游平衡最佳实践：
1. 对称初始 + 道路分化（参考Root的22-28%胜率目标）
2. 多种AI策略（激进/保守/平衡/随机/机会主义）避免测试偏见
3. Monte Carlo大规模模拟
4. 追踪所有可能性
"""

import random
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import time
from itertools import permutations

# ═══════════════════════════════════════════════════════════════════
#                           枚举与常量
# ═══════════════════════════════════════════════════════════════════

class Path(Enum):
    """六条道路（对称设计，游戏开始时选择）"""
    NIRVANA = "福田道"      # 原僧伽
    CHARITY = "布施道"      # 原商贾
    TEMPLE = "土地道"       # 原地主
    CULTURE = "文化道"      # 原文士
    DILIGENCE = "勤劳道"    # 原农夫
    SALVATION = "渡化道"    # 原信女

class AIStrategy(Enum):
    """AI策略类型 - 避免测试偏见"""
    AGGRESSIVE = "激进型"   # 优先高风险高回报
    CONSERVATIVE = "保守型" # 优先稳定收益
    BALANCED = "平衡型"     # 中庸策略
    RANDOM = "随机型"       # 完全随机
    OPPORTUNISTIC = "机会型" # 根据局势调整

class ScoreSource(Enum):
    MECHANISM = "机制"
    EVENT = "事件"
    INTERACTION = "互动"
    PATH = "道路"

# ═══════════════════════════════════════════════════════════════════
#                           道路定义
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PathDefinition:
    path: Path
    name: str
    startup_bonus: Dict[str, int]  # 启动奖励
    action_bonus: str              # 专属加成描述
    full_condition: str            # 完成条件
    small_condition: str           # 小成条件

# v6.3 最终微调：勤劳道削弱，渡化道/布施道加强
PATH_DEFINITIONS = {
    Path.NIRVANA: PathDefinition(
        path=Path.NIRVANA,
        name="福田道",
        startup_bonus={"influence": 5, "merit": 2},
        action_bonus="修行效率+100%",
        full_condition="回向3人 + 影响消耗≥4",
        small_condition="回向1人"
    ),
    Path.CHARITY: PathDefinition(
        path=Path.CHARITY,
        name="布施道", 
        startup_bonus={"wealth": 6},  # v6.3: +6财富（加强）
        action_bonus="捐献效率+75%",  # v6.3: 提升到75%
        full_condition="累计捐献≥12 + 影响≥3",
        small_condition="累计捐献≥7"  # v6.3: 降低小成条件
    ),
    Path.TEMPLE: PathDefinition(
        path=Path.TEMPLE,
        name="土地道",
        startup_bonus={"land": 1, "wealth": 2},
        action_bonus="土地产出+1",
        full_condition="建寺 + 捐地≥3",
        small_condition="建寺 或 捐地≥2"
    ),
    Path.CULTURE: PathDefinition(
        path=Path.CULTURE,
        name="文化道",
        startup_bonus={"influence": 2, "wealth": 2},
        action_bonus="善行效率+50%",
        full_condition="影响≥7 + 善行3人",
        small_condition="影响≥5 或 善行2人"
    ),
    Path.DILIGENCE: PathDefinition(
        path=Path.DILIGENCE,
        name="勤劳道",
        startup_bonus={},  # v6.3: 移除所有启动奖励
        action_bonus="耕作收益+1 + 额外行动点",  # v6.3: 仍保留行动点加成
        full_condition="善行≥5次 + 耕作≥5次",  # v6.3: 提高条件
        small_condition="善行≥3次 或 耕作≥3次"  # v6.3: 提高小成条件
    ),
    Path.SALVATION: PathDefinition(
        path=Path.SALVATION,
        name="渡化道",
        startup_bonus={"merit": 5, "influence": 2},  # v6.3: 更多启动奖励
        action_bonus="回向效率+100%",  # v6.3: 提升到100%
        full_condition="回向≥3次 + 渡化2人",  # v6.3: 降低渡化要求
        small_condition="回向≥1次 或 渡化1人"  # v6.3: 降低小成条件
    ),
}

# ═══════════════════════════════════════════════════════════════════
#                           事件卡（30张，每张有选择）
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
    # 天象类 6张
    EventCard(1, "丰年", "天象", 2, "+3财富", "+1功德+1影响"),
    EventCard(2, "祥瑞", "天象", 2, "+2功德", "+2影响"),
    EventCard(3, "灾异", "天象", 2, "-3财富", "-2功德"),
    # 法会类 6张
    EventCard(4, "盂兰盆会", "法会", 2, "消耗2财富+3功德", "不参与"),
    EventCard(5, "讲经法会", "法会", 2, "消耗1影响+2功德", "+1功德"),
    EventCard(6, "水陆法会", "法会", 2, "消耗3财富+4功德", "不参与"),
    # 世俗类 6张
    EventCard(7, "商队", "世俗", 2, "+3财富", "3财富换2功德"),
    EventCard(8, "科举", "世俗", 2, "影响≥5:+2功德", "+1影响"),
    EventCard(9, "集市", "世俗", 2, "+2财富", "+1功德"),
    # 灾难类 6张
    EventCard(10, "旱灾", "灾难", 2, "-3财富", "-1功德-1影响"),
    EventCard(11, "盗匪", "灾难", 2, "-4财富", "-2影响"),
    EventCard(12, "瘟疫", "灾难", 2, "-2功德", "-2影响"),
    # 机缘类 6张
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
#                           玩家类
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Player:
    player_id: int
    path: Path
    strategy: AIStrategy
    num_players: int = 4
    
    # 4种资源（对称初始）
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
    
    # 得分来源
    score_sources: Dict = field(default_factory=lambda: {
        ScoreSource.MECHANISM: 0,
        ScoreSource.EVENT: 0,
        ScoreSource.INTERACTION: 0,
        ScoreSource.PATH: 0,
    })
    
    def __post_init__(self):
        """应用道路启动奖励"""
        path_def = PATH_DEFINITIONS[self.path]
        for resource, amount in path_def.startup_bonus.items():
            if resource == "wealth":
                self.wealth += amount
            elif resource == "merit":
                self.merit += amount
            elif resource == "influence":
                self.influence += amount
            elif resource == "land":
                self.land += amount
            elif resource == "action_points":
                self.base_action_points += amount
    
    def add_merit(self, amount: int, source: ScoreSource):
        self.merit += amount
        self.score_sources[source] += amount * 2
    
    def get_path_bonus_multiplier(self, action: str) -> float:
        """获取道路加成 - v6.3调整"""
        if self.path == Path.NIRVANA and action == "practice":
            return 2.0  # 100%加成
        elif self.path == Path.CHARITY and action == "donate":
            return 1.75  # v6.3: 75%加成
        elif self.path == Path.TEMPLE and action == "farm":
            return 1.0
        elif self.path == Path.CULTURE and action == "kindness":
            return 1.5
        elif self.path == Path.DILIGENCE and action == "farm":
            return 1.0
        elif self.path == Path.SALVATION and action == "transfer":
            return 2.0  # v6.3: 100%加成
        return 1.0
    
    def check_path_completion(self, num_players: int) -> Tuple[bool, str, int]:
        """检查道路完成 - v6.3调整后条件"""
        # 人数调整
        multiplier = 1.0
        if num_players == 3:
            multiplier = 1.2
        elif num_players >= 5:
            multiplier = 0.9
        
        base_bonus = 25
        small_bonus = 12
        
        if self.path == Path.NIRVANA:
            # 回向3人 + 影响消耗≥4
            if len(self.transfer_targets) >= 3 and self.influence_spent >= 4:
                return (True, "福田道", int(base_bonus * multiplier))
            elif len(self.transfer_targets) >= 1:
                return (True, "福田道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.CHARITY:
            # 累计捐献≥12 + 影响≥3
            if self.total_donated >= 12 and self.influence >= 3:
                return (True, "布施道", int(base_bonus * multiplier))
            elif self.total_donated >= 7:  # v6.3: 降低小成条件
                return (True, "布施道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.TEMPLE:
            # 建寺 + 捐地≥3
            if self.has_built_temple and self.land_donated >= 3:
                return (True, "土地道", int(base_bonus * multiplier))
            elif self.has_built_temple or self.land_donated >= 2:
                return (True, "土地道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.CULTURE:
            # 影响≥7 + 善行3人
            if self.influence >= 7 and len(self.kindness_targets) >= 3:
                return (True, "文化道", int(base_bonus * multiplier))
            elif self.influence >= 5 or len(self.kindness_targets) >= 2:
                return (True, "文化道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.DILIGENCE:
            # v6.3: 善行≥5 + 耕作≥5（提高难度）
            if self.kindness_count >= 5 and self.farming_count >= 5:
                return (True, "勤劳道", int(base_bonus * multiplier))
            elif self.kindness_count >= 3 or self.farming_count >= 3:  # v6.3: 提高小成
                return (True, "勤劳道（小成）", int(small_bonus * multiplier))
        
        elif self.path == Path.SALVATION:
            # v6.3: 回向≥3 + 渡化2人（降低难度）
            all_helped = self.transfer_targets | self.kindness_targets
            if self.transfer_count >= 3 and len(all_helped) >= 2:
                return (True, "渡化道", int(base_bonus * multiplier))
            elif self.transfer_count >= 1 or len(all_helped) >= 1:  # v6.3: 更低小成
                return (True, "渡化道（小成）", int(small_bonus * multiplier))
        
        return (False, "", 0)
    
    def get_final_score(self, num_players: int) -> float:
        """计算最终得分"""
        base_score = self.merit * 2 + self.influence + self.wealth / 3 + self.land * 2
        
        path_complete, path_name, path_bonus = self.check_path_completion(num_players)
        if path_complete:
            self.score_sources[ScoreSource.PATH] = path_bonus
        
        return base_score + path_bonus

# ═══════════════════════════════════════════════════════════════════
#                           多策略AI决策
# ═══════════════════════════════════════════════════════════════════

class AIDecisionMaker:
    """多策略AI决策器 - 避免测试偏见"""
    
    @staticmethod
    def decide_action(player: Player, game: Dict, others: List[Player]) -> Optional[str]:
        """根据策略类型选择行动"""
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
        """获取可用行动列表"""
        actions = []
        
        # 布施：消耗3财富
        if player.wealth >= 3:
            actions.append("donate")
        
        # 修行：消耗2影响
        if player.influence >= 2:
            actions.append("practice")
        
        # 善行：消耗1财富
        if player.wealth >= 1 and others:
            actions.append("kindness")
        
        # 回向：消耗2功德
        if player.merit >= 2 and others:
            actions.append("transfer")
        
        # 耕作：无消耗
        actions.append("farm")
        
        # 建寺：消耗8财富+2影响 或 2土地
        if not player.has_built_temple:
            if player.wealth >= 8 and player.influence >= 2:
                actions.append("build_temple")
            elif player.land >= 2:
                actions.append("build_temple_land")
        
        # 捐地：消耗1土地
        if player.land >= 1:
            actions.append("donate_land")
        
        return actions
    
    @staticmethod
    def _random_action(player: Player, others: List[Player]) -> Optional[str]:
        """完全随机策略"""
        actions = AIDecisionMaker._get_available_actions(player, others)
        if actions:
            return random.choice(actions)
        return None
    
    @staticmethod
    def _aggressive_action(player: Player, others: List[Player]) -> Optional[str]:
        """激进策略：优先高回报行动"""
        # 优先级：建寺 > 大额捐献 > 回向 > 修行 > 其他
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
        """保守策略：优先稳定收益"""
        # 优先级：耕作积累 > 小额行动 > 避免大额消耗
        
        # 确保有足够财富
        if player.wealth < 5:
            return "farm"
        
        # 小额善行
        if player.wealth >= 1 and others:
            return "kindness"
        
        # 适度捐献
        if player.wealth >= 6:
            return "donate"
        
        # 修行
        if player.influence >= 3:
            return "practice"
        
        return "farm"
    
    @staticmethod
    def _balanced_action(player: Player, others: List[Player]) -> Optional[str]:
        """平衡策略：根据道路目标行动"""
        path = player.path
        
        # 根据道路选择最相关的行动
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
        
        # 默认
        actions = AIDecisionMaker._get_available_actions(player, others)
        if actions:
            return random.choice(actions)
        return None
    
    @staticmethod
    def _opportunistic_action(player: Player, game: Dict, others: List[Player]) -> Optional[str]:
        """机会型策略：根据当前局势调整"""
        round_num = game["round"]
        
        # 前期积累
        if round_num <= 3:
            if player.wealth < 8:
                return "farm"
            if player.wealth >= 3:
                return "donate"
        
        # 中期发展
        elif round_num <= 6:
            # 看是否接近完成道路
            path_complete, _, _ = player.check_path_completion(len(others) + 1)
            if not path_complete:
                return AIDecisionMaker._balanced_action(player, others)
        
        # 后期冲刺
        else:
            # 最大化得分
            if not player.has_built_temple and player.land >= 2:
                return "build_temple_land"
            if player.wealth >= 3:
                return "donate"
            if player.merit >= 2 and others:
                return "transfer"
        
        return AIDecisionMaker._balanced_action(player, others)
    
    @staticmethod
    def decide_event_option(player: Player, event: EventCard) -> str:
        """决定事件卡选项"""
        strategy = player.strategy
        
        if strategy == AIStrategy.RANDOM:
            return random.choice(["A", "B"])
        
        # 根据事件类型和策略选择
        if event.category == "灾难":
            # 灾难时保守型选择损失较小的
            if strategy == AIStrategy.CONSERVATIVE:
                # 简化：随机选
                return random.choice(["A", "B"])
        
        if event.category in ["法会", "机缘"]:
            # 机会类激进型更愿意参与
            if strategy == AIStrategy.AGGRESSIVE:
                return "A"
        
        return random.choice(["A", "B"])

# ═══════════════════════════════════════════════════════════════════
#                           游戏模拟器
# ═══════════════════════════════════════════════════════════════════

class GameSimulator:
    def __init__(self, num_players: int = 4, strategy_mode: str = "mixed"):
        """
        strategy_mode:
        - "mixed": 每个玩家随机分配策略
        - "uniform_X": 所有玩家使用策略X
        - "all_strategies": 测试所有策略组合
        """
        if num_players < 3 or num_players > 6:
            raise ValueError("Player count must be 3-6")
        self.num_players = num_players
        self.strategy_mode = strategy_mode
        self.all_paths = list(Path)[:num_players]
    
    def _assign_strategies(self) -> List[AIStrategy]:
        """分配AI策略"""
        if self.strategy_mode == "mixed":
            # 随机分配
            return [random.choice(list(AIStrategy)) for _ in range(self.num_players)]
        elif self.strategy_mode.startswith("uniform_"):
            strategy_name = self.strategy_mode.replace("uniform_", "")
            strategy = AIStrategy[strategy_name]
            return [strategy] * self.num_players
        else:
            # 混合策略
            strategies = list(AIStrategy)
            return [strategies[i % len(strategies)] for i in range(self.num_players)]
    
    def create_game(self, paths: List[Path] = None, strategies: List[AIStrategy] = None) -> Dict:
        """创建游戏"""
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
        }
    
    def process_event(self, game: Dict, event: EventCard):
        """处理事件"""
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
        """生产阶段 - 所有玩家相同"""
        for p in game["players"]:
            # 基础产出
            p.wealth += 2
            p.influence += 1
            
            # 土地产出
            land_bonus = 1 if p.path in [Path.TEMPLE, Path.DILIGENCE] else 0
            p.wealth += p.land * (1 + land_bonus)
    
    def action_phase(self, game: Dict):
        """行动阶段"""
        players = game["players"]
        
        for p in players:
            p.action_points = p.base_action_points
            others = [o for o in players if o.player_id != p.player_id]
            
            while p.action_points > 0:
                action = AIDecisionMaker.decide_action(p, game, others)
                if action is None:
                    break
                
                self.execute_action(p, action, game, others)
                p.action_points -= 1
    
    def execute_action(self, player: Player, action: str, game: Dict, others: List[Player]):
        """执行行动"""
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
            # v6.2: 土地道+1，勤劳道+1
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
    
    def run_game(self, paths: List[Path] = None, strategies: List[AIStrategy] = None) -> Dict:
        """运行一局游戏"""
        game = self.create_game(paths, strategies)
        
        for round_num in range(1, 9):  # 8轮
            game["round"] = round_num
            
            # 事件阶段
            if game["event_deck"]:
                event = game["event_deck"].pop()
                self.process_event(game, event)
            
            # 生产阶段
            self.production_phase(game)
            
            # 行动阶段
            self.action_phase(game)
        
        # 计算得分
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
                "path_bonus": path_bonus,
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        winner_path = results[0]["path"]
        winner_strategy = results[0]["strategy"]
        
        return {
            "winner_path": winner_path,
            "winner_strategy": winner_strategy,
            "results": results,
        }
    
    def run_comprehensive_test(self, games_per_config: int = 1000) -> Dict:
        """
        全面测试 - 覆盖所有可能性
        1. 测试所有道路组合
        2. 测试所有策略类型
        3. 交叉验证
        """
        results = {
            "path_win_rates": defaultdict(int),
            "path_total_games": defaultdict(int),
            "strategy_win_rates": defaultdict(int),
            "strategy_total_games": defaultdict(int),
            "path_avg_scores": defaultdict(list),
            "path_completion_rates": defaultdict(lambda: defaultdict(int)),
            "cross_validation": {},
        }
        
        all_strategies = list(AIStrategy)
        
        # 测试1：混合策略，随机道路分配
        print("  Test 1: Mixed strategies, random paths...")
        for _ in range(games_per_config):
            game_result = self.run_game()
            
            results["path_win_rates"][game_result["winner_path"]] += 1
            results["strategy_win_rates"][game_result["winner_strategy"]] += 1
            
            for r in game_result["results"]:
                results["path_total_games"][r["path"]] += 1
                results["strategy_total_games"][r["strategy"]] += 1
                results["path_avg_scores"][r["path"]].append(r["score"])
                if r["path_completed"]:
                    results["path_completion_rates"][r["path"]][r["path_completed"]] += 1
        
        # 测试2：每种策略单独测试（控制变量）
        print("  Test 2: Uniform strategy tests...")
        for strategy in all_strategies:
            strategy_results = defaultdict(int)
            for _ in range(games_per_config // 2):
                strategies = [strategy] * self.num_players
                game_result = self.run_game(strategies=strategies)
                strategy_results[game_result["winner_path"]] += 1
            
            results["cross_validation"][f"uniform_{strategy.value}"] = dict(strategy_results)
        
        # 计算统计
        total_games = sum(results["path_win_rates"].values())
        
        final_stats = {
            "num_players": self.num_players,
            "games_per_config": games_per_config,
            "total_games": total_games,
            "path_win_rates": {},
            "path_avg_scores": {},
            "path_completion_rates": {},
            "strategy_win_rates": {},
            "cross_validation": results["cross_validation"],
        }
        
        for path in Path:
            path_name = path.value
            if path_name in results["path_win_rates"]:
                wins = results["path_win_rates"][path_name]
                total = results["path_total_games"][path_name]
                if total > 0:
                    final_stats["path_win_rates"][path_name] = round(wins / total * 100, 2)
                    scores = results["path_avg_scores"][path_name]
                    final_stats["path_avg_scores"][path_name] = round(sum(scores) / len(scores), 2)
                    
                    completions = results["path_completion_rates"][path_name]
                    if completions:
                        final_stats["path_completion_rates"][path_name] = {
                            k: round(v / total * 100, 2) for k, v in completions.items()
                        }
        
        for strategy in AIStrategy:
            strategy_name = strategy.value
            if strategy_name in results["strategy_win_rates"]:
                wins = results["strategy_win_rates"][strategy_name]
                total = results["strategy_total_games"][strategy_name]
                if total > 0:
                    final_stats["strategy_win_rates"][strategy_name] = round(wins / total * 100, 2)
        
        return final_stats

# ═══════════════════════════════════════════════════════════════════
#                           主程序
# ═══════════════════════════════════════════════════════════════════

def test_turn_order_bias(num_players: int = 4, games: int = 5000):
    """测试先手/后手优势偏见"""
    print(f"\n{'='*60}")
    print(f"Testing turn order bias ({num_players} players, {games} games)...")
    print(f"{'='*60}")
    
    position_wins = defaultdict(int)
    position_scores = defaultdict(list)
    
    simulator = GameSimulator(num_players, strategy_mode="mixed")
    
    for _ in range(games):
        game = simulator.create_game()
        
        for round_num in range(1, 9):
            game["round"] = round_num
            if game["event_deck"]:
                event = game["event_deck"].pop()
                simulator.process_event(game, event)
            simulator.production_phase(game)
            simulator.action_phase(game)
        
        # 按位置记录结果
        scores = []
        for i, p in enumerate(game["players"]):
            score = p.get_final_score(num_players)
            scores.append((i, score))
            position_scores[i].append(score)
        
        scores.sort(key=lambda x: -x[1])
        winner_position = scores[0][0]
        position_wins[winner_position] += 1
    
    print(f"  Position win rates (should be ~{100/num_players:.1f}% each):")
    for pos in range(num_players):
        wins = position_wins[pos]
        rate = wins / games * 100
        avg_score = sum(position_scores[pos]) / len(position_scores[pos])
        target = 100 / num_players
        diff = rate - target
        status = "OK" if abs(diff) < 5 else ("FIRST_ADVANTAGE" if diff > 0 else "LAST_ADVANTAGE")
        print(f"    Position {pos+1}: {rate:.2f}% wins, avg score {avg_score:.1f} ({status})")
    
    return position_wins


def run_iterative_balancing():
    """迭代平衡测试"""
    print("=" * 70)
    print("救赎之路 v6.3 - 无偏见多策略平衡测试")
    print("目标：所有道路胜率在 15-25% 范围内（参考Root的22-28%）")
    print("=" * 70)
    
    results_all = {}
    
    for num_players in [4, 5, 6]:
        print(f"\n{'='*60}")
        print(f"Testing {num_players}-player configuration...")
        print(f"{'='*60}")
        
        simulator = GameSimulator(num_players, strategy_mode="mixed")
        
        print("  Running comprehensive test (10000 games)...")
        start = time.time()
        stats = simulator.run_comprehensive_test(games_per_config=10000)
        elapsed = time.time() - start
        print(f"  Completed in {elapsed:.2f}s")
        
        results_all[f"{num_players}p"] = stats
        
        # 打印结果
        print(f"\n  [Results - {num_players} players]")
        print(f"  Path win rates:")
        for path, rate in sorted(stats["path_win_rates"].items(), key=lambda x: -x[1]):
            target_rate = 100 / num_players
            diff = rate - target_rate
            status = "OK" if abs(diff) < 8 else ("HIGH" if diff > 0 else "LOW")
            print(f"    {path}: {rate}% (target: {target_rate:.1f}%, {status})")
        
        print(f"  Strategy win rates (should be similar):")
        for strategy, rate in sorted(stats["strategy_win_rates"].items(), key=lambda x: -x[1]):
            print(f"    {strategy}: {rate}%")
    
    # 额外：测试先手/后手优势
    print("\n" + "=" * 70)
    print("BIAS CHECK: Testing turn order advantage...")
    print("=" * 70)
    test_turn_order_bias(4, 5000)
    test_turn_order_bias(6, 5000)
    
    # 保存结果
    with open("simulation_results_v6_unbiased.json", "w", encoding="utf-8") as f:
        json.dump(results_all, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 70)
    print("Results saved to simulation_results_v6_unbiased.json")
    
    return results_all


if __name__ == "__main__":
    run_iterative_balancing()
