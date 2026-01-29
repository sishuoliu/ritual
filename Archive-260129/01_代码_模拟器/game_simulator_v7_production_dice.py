# -*- coding: utf-8 -*-
"""
救赎之路 v7.0 - 生产骰子系统测试版
基于v6.3无偏见版本，新增生产阶段骰子系统

测试设计原则：
1. 对照组 vs 实验组（无骰子 vs 有骰子）
2. 多策略AI避免测试偏见
3. 大规模Monte Carlo模拟（每配置10000局）
4. 交叉验证：混合策略 + 单一策略
5. 骰子影响量化分析
"""

import random
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import time
from statistics import mean, stdev
import math

# ═══════════════════════════════════════════════════════════════════
#                           枚举与常量
# ═══════════════════════════════════════════════════════════════════

class Path(Enum):
    """六条道路"""
    NIRVANA = "福田道"
    CHARITY = "布施道"
    TEMPLE = "土地道"
    CULTURE = "文化道"
    DILIGENCE = "勤劳道"
    SALVATION = "渡化道"

class AIStrategy(Enum):
    """AI策略类型 - 避免测试偏见"""
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
    DICE = "骰子"  # 新增：骰子来源

class DiceResult(Enum):
    """生产骰子结果"""
    NORMAL = "平常"      # 1-2: 标准生产
    SMALL_FORTUNE = "小福"  # 3-4: +1财富
    GREAT_FORTUNE = "大福"  # 5-6: +1财富 +1影响

# ═══════════════════════════════════════════════════════════════════
#                           道路定义（与v6.3一致）
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PathDefinition:
    path: Path
    name: str
    startup_bonus: Dict[str, int]
    action_bonus: str
    full_condition: str
    small_condition: str

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
        startup_bonus={"wealth": 6},
        action_bonus="捐献效率+75%",
        full_condition="累计捐献≥12 + 影响≥3",
        small_condition="累计捐献≥7"
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
        startup_bonus={},
        action_bonus="耕作收益+1 + 额外行动点",
        full_condition="善行≥5次 + 耕作≥5次",
        small_condition="善行≥3次 或 耕作≥3次"
    ),
    Path.SALVATION: PathDefinition(
        path=Path.SALVATION,
        name="渡化道",
        startup_bonus={"merit": 5, "influence": 2},
        action_bonus="回向效率+100%",
        full_condition="回向≥3次 + 渡化2人",
        small_condition="回向≥1次 或 渡化1人"
    ),
}

# ═══════════════════════════════════════════════════════════════════
#                           事件卡
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
    
    # 骰子统计
    dice_wealth_bonus: int = 0
    dice_influence_bonus: int = 0
    dice_results: List = field(default_factory=list)
    
    # 得分来源
    score_sources: Dict = field(default_factory=lambda: {
        ScoreSource.MECHANISM: 0,
        ScoreSource.EVENT: 0,
        ScoreSource.INTERACTION: 0,
        ScoreSource.PATH: 0,
        ScoreSource.DICE: 0,
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
        """获取道路加成 - v7.1: 所有加成统一为翻倍（无小数）"""
        if self.path == Path.NIRVANA and action == "practice":
            return 2.0  # 福田道：修行翻倍
        elif self.path == Path.CHARITY and action == "donate":
            return 2.0  # 布施道：布施翻倍（原1.75→2.0）
        elif self.path == Path.TEMPLE and action == "farm":
            return 1.0
        elif self.path == Path.CULTURE and action == "kindness":
            return 2.0  # 文化道：善行翻倍（原1.5→2.0）
        elif self.path == Path.DILIGENCE and action == "farm":
            return 1.0
        elif self.path == Path.SALVATION and action == "transfer":
            return 2.0  # 渡化道：回向翻倍
        return 1.0
    
    def check_path_completion(self, num_players: int) -> Tuple[bool, str, int]:
        """检查道路完成"""
        multiplier = 1.0
        if num_players == 3:
            multiplier = 1.2
        elif num_players >= 5:
            multiplier = 0.9
        
        base_bonus = 25
        small_bonus = 12
        
        if self.path == Path.NIRVANA:
            if len(self.transfer_targets) >= 3 and self.influence_spent >= 4:
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
        """计算最终得分"""
        base_score = self.merit * 2 + self.influence + self.wealth / 3 + self.land * 2
        
        path_complete, path_name, path_bonus = self.check_path_completion(num_players)
        if path_complete:
            self.score_sources[ScoreSource.PATH] = path_bonus
        
        return base_score + path_bonus

# ═══════════════════════════════════════════════════════════════════
#                           AI决策器
# ═══════════════════════════════════════════════════════════════════

class AIDecisionMaker:
    """多策略AI决策器"""
    
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
        if actions:
            return random.choice(actions)
        return None
    
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
        
        actions = AIDecisionMaker._get_available_actions(player, others)
        if actions:
            return random.choice(actions)
        return None
    
    @staticmethod
    def _opportunistic_action(player: Player, game: Dict, others: List[Player]) -> Optional[str]:
        round_num = game["round"]
        
        if round_num <= 3:
            if player.wealth < 8:
                return "farm"
            if player.wealth >= 3:
                return "donate"
        elif round_num <= 6:
            path_complete, _, _ = player.check_path_completion(len(others) + 1)
            if not path_complete:
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
        strategy = player.strategy
        
        if strategy == AIStrategy.RANDOM:
            return random.choice(["A", "B"])
        
        if event.category == "灾难":
            if strategy == AIStrategy.CONSERVATIVE:
                return random.choice(["A", "B"])
        
        if event.category in ["法会", "机缘"]:
            if strategy == AIStrategy.AGGRESSIVE:
                return "A"
        
        return random.choice(["A", "B"])

# ═══════════════════════════════════════════════════════════════════
#                           游戏模拟器
# ═══════════════════════════════════════════════════════════════════

class GameSimulator:
    def __init__(self, num_players: int = 4, use_dice: bool = False, 
                 dice_config: Dict = None):
        """
        初始化模拟器
        
        Args:
            num_players: 玩家数量 (3-6)
            use_dice: 是否使用生产骰子
            dice_config: 骰子配置 {
                "small_fortune_wealth": 1,    # 小福额外财富
                "great_fortune_wealth": 1,    # 大福额外财富
                "great_fortune_influence": 1  # 大福额外影响
            }
        """
        if num_players < 3 or num_players > 6:
            raise ValueError("Player count must be 3-6")
        
        self.num_players = num_players
        self.use_dice = use_dice
        self.dice_config = dice_config or {
            "small_fortune_wealth": 1,
            "great_fortune_wealth": 1,
            "great_fortune_influence": 1
        }
        self.all_paths = list(Path)[:num_players]
        
        # 统计数据
        self.dice_stats = defaultdict(int)
    
    def _assign_strategies(self) -> List[AIStrategy]:
        """随机分配策略"""
        return [random.choice(list(AIStrategy)) for _ in range(self.num_players)]
    
    def _roll_production_dice(self) -> Tuple[DiceResult, int, int]:
        """
        掷生产骰子
        
        Returns:
            (结果类型, 额外财富, 额外影响)
        """
        roll = random.randint(1, 6)
        
        if roll <= 2:
            return (DiceResult.NORMAL, 0, 0)
        elif roll <= 4:
            return (DiceResult.SMALL_FORTUNE, 
                    self.dice_config["small_fortune_wealth"], 0)
        else:
            return (DiceResult.GREAT_FORTUNE, 
                    self.dice_config["great_fortune_wealth"],
                    self.dice_config["great_fortune_influence"])
    
    def create_game(self, paths: List[Path] = None, 
                    strategies: List[AIStrategy] = None) -> Dict:
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
        """生产阶段 - 带骰子系统"""
        for p in game["players"]:
            # 基础产出
            p.wealth += 2
            p.influence += 1
            
            # 土地产出
            land_bonus = 1 if p.path in [Path.TEMPLE, Path.DILIGENCE] else 0
            p.wealth += p.land * (1 + land_bonus)
            
            # 骰子加成
            if self.use_dice:
                dice_result, extra_wealth, extra_influence = self._roll_production_dice()
                p.dice_results.append(dice_result)
                p.dice_wealth_bonus += extra_wealth
                p.dice_influence_bonus += extra_influence
                p.wealth += extra_wealth
                p.influence += extra_influence
                
                # 统计
                self.dice_stats[dice_result.value] += 1
                
                # 记录骰子得分来源
                score_from_dice = extra_influence + extra_wealth / 3
                p.score_sources[ScoreSource.DICE] += score_from_dice
    
    def action_phase(self, game: Dict):
        """行动阶段"""
        players = game["players"]
        
        for p in players:
            # 勤劳道有3个行动点
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
    
    def execute_action(self, player: Player, action: str, game: Dict, 
                       others: List[Player]):
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
    
    def run_game(self, paths: List[Path] = None, 
                 strategies: List[AIStrategy] = None) -> Dict:
        """运行一局游戏"""
        game = self.create_game(paths, strategies)
        
        for round_num in range(1, 9):
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
                "dice_wealth_bonus": p.dice_wealth_bonus,
                "dice_influence_bonus": p.dice_influence_bonus,
                "dice_score_contribution": round(p.score_sources.get(ScoreSource.DICE, 0), 2),
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        winner_path = results[0]["path"]
        winner_strategy = results[0]["strategy"]
        
        return {
            "winner_path": winner_path,
            "winner_strategy": winner_strategy,
            "results": results,
        }


# ═══════════════════════════════════════════════════════════════════
#                           测试框架
# ═══════════════════════════════════════════════════════════════════

def run_ab_test(num_players: int = 4, games_per_config: int = 10000,
                dice_config: Dict = None) -> Dict:
    """
    A/B测试：对照组(无骰子) vs 实验组(有骰子)
    
    返回对比结果
    """
    print(f"\n{'='*70}")
    print(f"A/B TEST: {num_players} players, {games_per_config} games each")
    print(f"{'='*70}")
    
    results = {
        "control": {},  # 无骰子
        "experiment": {},  # 有骰子
        "comparison": {},  # 对比分析
    }
    
    # ========== 对照组：无骰子 ==========
    print("\n[CONTROL GROUP] Running baseline (no dice)...")
    start = time.time()
    
    control_sim = GameSimulator(num_players, use_dice=False)
    control_stats = run_comprehensive_test(control_sim, games_per_config)
    
    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.2f}s")
    results["control"] = control_stats
    
    # ========== 实验组：有骰子 ==========
    print("\n[EXPERIMENT GROUP] Running with production dice...")
    start = time.time()
    
    experiment_sim = GameSimulator(num_players, use_dice=True, 
                                   dice_config=dice_config)
    experiment_stats = run_comprehensive_test(experiment_sim, games_per_config)
    
    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.2f}s")
    results["experiment"] = experiment_stats
    
    # ========== 对比分析 ==========
    print("\n[COMPARISON ANALYSIS]")
    
    comparison = {
        "win_rate_changes": {},
        "score_variance_change": {},
        "dice_impact": {},
    }
    
    # 胜率变化
    for path in Path:
        path_name = path.value
        control_rate = control_stats["path_win_rates"].get(path_name, 0)
        experiment_rate = experiment_stats["path_win_rates"].get(path_name, 0)
        change = experiment_rate - control_rate
        comparison["win_rate_changes"][path_name] = {
            "control": control_rate,
            "experiment": experiment_rate,
            "change": round(change, 2),
            "status": "OK" if abs(change) < 3 else ("UP" if change > 0 else "DOWN")
        }
    
    # 得分方差变化
    for path in Path:
        path_name = path.value
        control_scores = control_stats.get("path_score_details", {}).get(path_name, {})
        experiment_scores = experiment_stats.get("path_score_details", {}).get(path_name, {})
        
        control_std = control_scores.get("std", 0)
        experiment_std = experiment_scores.get("std", 0)
        
        comparison["score_variance_change"][path_name] = {
            "control_std": control_std,
            "experiment_std": experiment_std,
            "change": round(experiment_std - control_std, 2)
        }
    
    # 骰子影响
    if "dice_stats" in experiment_stats:
        comparison["dice_impact"] = experiment_stats["dice_stats"]
    
    results["comparison"] = comparison
    
    # 打印对比结果
    print("\n  Win Rate Changes (Experiment - Control):")
    target_rate = 100 / num_players
    all_balanced = True
    for path_name, data in comparison["win_rate_changes"].items():
        change_str = f"+{data['change']}" if data['change'] >= 0 else str(data['change'])
        status = "✓" if abs(data['experiment'] - target_rate) < 8 else "✗"
        if status == "✗":
            all_balanced = False
        print(f"    {path_name}: {data['control']:.1f}% → {data['experiment']:.1f}% ({change_str}%) {status}")
    
    print(f"\n  Score Standard Deviation Changes:")
    for path_name, data in comparison["score_variance_change"].items():
        change_str = f"+{data['change']:.2f}" if data['change'] >= 0 else f"{data['change']:.2f}"
        print(f"    {path_name}: {data['control_std']:.2f} → {data['experiment_std']:.2f} ({change_str})")
    
    results["is_balanced"] = all_balanced
    
    return results


def run_comprehensive_test(simulator: GameSimulator, 
                           games_per_config: int = 10000) -> Dict:
    """
    全面测试
    """
    results = {
        "path_win_rates": defaultdict(int),
        "path_total_games": defaultdict(int),
        "strategy_win_rates": defaultdict(int),
        "strategy_total_games": defaultdict(int),
        "path_scores": defaultdict(list),
        "path_completion_rates": defaultdict(lambda: defaultdict(int)),
    }
    
    all_strategies = list(AIStrategy)
    
    # 测试1：混合策略
    for _ in range(games_per_config):
        game_result = simulator.run_game()
        
        results["path_win_rates"][game_result["winner_path"]] += 1
        results["strategy_win_rates"][game_result["winner_strategy"]] += 1
        
        for r in game_result["results"]:
            results["path_total_games"][r["path"]] += 1
            results["strategy_total_games"][r["strategy"]] += 1
            results["path_scores"][r["path"]].append(r["score"])
            if r["path_completed"]:
                results["path_completion_rates"][r["path"]][r["path_completed"]] += 1
    
    # 测试2：单一策略控制变量
    cross_validation = {}
    for strategy in all_strategies:
        strategy_results = defaultdict(int)
        for _ in range(games_per_config // 5):
            strategies = [strategy] * simulator.num_players
            game_result = simulator.run_game(strategies=strategies)
            strategy_results[game_result["winner_path"]] += 1
        cross_validation[f"uniform_{strategy.value}"] = dict(strategy_results)
    
    # 计算统计
    final_stats = {
        "num_players": simulator.num_players,
        "games_per_config": games_per_config,
        "use_dice": simulator.use_dice,
        "path_win_rates": {},
        "path_avg_scores": {},
        "path_score_details": {},
        "path_completion_rates": {},
        "strategy_win_rates": {},
        "cross_validation": cross_validation,
    }
    
    for path in Path:
        path_name = path.value
        if path_name in results["path_win_rates"]:
            wins = results["path_win_rates"][path_name]
            total = results["path_total_games"][path_name]
            if total > 0:
                final_stats["path_win_rates"][path_name] = round(wins / total * 100, 2)
                scores = results["path_scores"][path_name]
                avg_score = mean(scores)
                score_std = stdev(scores) if len(scores) > 1 else 0
                final_stats["path_avg_scores"][path_name] = round(avg_score, 2)
                final_stats["path_score_details"][path_name] = {
                    "avg": round(avg_score, 2),
                    "std": round(score_std, 2),
                    "min": round(min(scores), 2),
                    "max": round(max(scores), 2),
                }
                
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
    
    # 骰子统计
    if simulator.use_dice:
        total_dice_rolls = sum(simulator.dice_stats.values())
        if total_dice_rolls > 0:
            final_stats["dice_stats"] = {
                result: {
                    "count": count,
                    "rate": round(count / total_dice_rolls * 100, 2)
                }
                for result, count in simulator.dice_stats.items()
            }
    
    return final_stats


def test_dice_configurations(num_players: int = 4, 
                             games_per_config: int = 5000) -> Dict:
    """
    测试不同的骰子配置，找到最佳参数
    """
    print(f"\n{'='*70}")
    print(f"DICE CONFIGURATION OPTIMIZATION")
    print(f"{'='*70}")
    
    configs = [
        # 配置名称, 小福额外财富, 大福额外财富, 大福额外影响
        ("v1_baseline", 1, 1, 1),
        ("v2_more_wealth", 2, 2, 1),
        ("v3_more_influence", 1, 1, 2),
        ("v4_balanced", 1, 2, 1),
        ("v5_minimal", 1, 1, 0),
    ]
    
    results = {}
    
    for config_name, sw, gw, gi in configs:
        print(f"\n  Testing {config_name}: small_fortune=+{sw}W, great_fortune=+{gw}W+{gi}I")
        
        dice_config = {
            "small_fortune_wealth": sw,
            "great_fortune_wealth": gw,
            "great_fortune_influence": gi
        }
        
        sim = GameSimulator(num_players, use_dice=True, dice_config=dice_config)
        stats = run_comprehensive_test(sim, games_per_config)
        
        # 计算平衡性评分
        target_rate = 100 / num_players
        balance_score = 0
        for path_name, rate in stats["path_win_rates"].items():
            deviation = abs(rate - target_rate)
            balance_score += deviation
        
        results[config_name] = {
            "config": dice_config,
            "win_rates": stats["path_win_rates"],
            "balance_score": round(balance_score, 2),  # 越低越好
        }
        
        print(f"    Balance score: {balance_score:.2f} (lower is better)")
    
    # 找到最佳配置
    best_config = min(results.items(), key=lambda x: x[1]["balance_score"])
    print(f"\n  BEST CONFIG: {best_config[0]} (score: {best_config[1]['balance_score']:.2f})")
    
    return results


def run_final_test(games_per_config: int = 10000) -> Dict:
    """
    最终测试：使用最佳配置进行完整A/B测试
    """
    print("\n" + "="*70)
    print("《救赎之路》v7.0 生产骰子系统测试")
    print("目标：所有道路胜率在 15-25% 范围内")
    print("="*70)
    
    all_results = {}
    
    # 测试4人、5人、6人配置
    for num_players in [4, 5, 6]:
        print(f"\n{'='*60}")
        print(f"Testing {num_players}-player configuration")
        print(f"{'='*60}")
        
        result = run_ab_test(num_players, games_per_config)
        all_results[f"{num_players}p"] = result
    
    return all_results


def generate_report(results: Dict) -> str:
    """
    生成测试报告
    """
    report = []
    report.append("="*70)
    report.append("《救赎之路》v7.0 生产骰子系统测试报告")
    report.append(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*70)
    
    for config_name, config_results in results.items():
        report.append(f"\n{'='*60}")
        report.append(f"配置: {config_name}")
        report.append(f"{'='*60}")
        
        # 对照组结果
        control = config_results.get("control", {})
        experiment = config_results.get("experiment", {})
        comparison = config_results.get("comparison", {})
        
        report.append("\n▌胜率对比")
        report.append("━"*50)
        report.append(f"{'道路':<12} {'无骰子':>10} {'有骰子':>10} {'变化':>10} {'状态':>8}")
        report.append("-"*50)
        
        target_rate = 100 / int(config_name[0])
        
        for path_name, data in comparison.get("win_rate_changes", {}).items():
            change = data["change"]
            change_str = f"+{change:.1f}" if change >= 0 else f"{change:.1f}"
            exp_rate = data["experiment"]
            status = "✓ OK" if abs(exp_rate - target_rate) < 8 else "✗ BIAS"
            report.append(f"{path_name:<12} {data['control']:>10.1f}% {exp_rate:>10.1f}% {change_str:>10}% {status:>8}")
        
        report.append("\n▌得分方差变化")
        report.append("━"*50)
        report.append(f"{'道路':<12} {'无骰子σ':>12} {'有骰子σ':>12} {'变化':>10}")
        report.append("-"*50)
        
        for path_name, data in comparison.get("score_variance_change", {}).items():
            change = data["change"]
            change_str = f"+{change:.2f}" if change >= 0 else f"{change:.2f}"
            report.append(f"{path_name:<12} {data['control_std']:>12.2f} {data['experiment_std']:>12.2f} {change_str:>10}")
        
        # 骰子统计
        if experiment.get("dice_stats"):
            report.append("\n▌骰子统计")
            report.append("━"*50)
            for result, stats in experiment["dice_stats"].items():
                report.append(f"  {result}: {stats['count']} 次 ({stats['rate']:.1f}%)")
        
        # 平衡性评估
        report.append("\n▌平衡性评估")
        report.append("━"*50)
        is_balanced = config_results.get("is_balanced", False)
        if is_balanced:
            report.append("  ✓ 所有道路胜率在合理范围内")
        else:
            report.append("  ✗ 存在胜率偏差，需要调整")
    
    report.append("\n" + "="*70)
    report.append("报告结束")
    report.append("="*70)
    
    return "\n".join(report)


# ═══════════════════════════════════════════════════════════════════
#                           主程序
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Starting production dice system test...")
    print("This will take several minutes...\n")
    
    # 运行最终测试
    results = run_final_test(games_per_config=10000)
    
    # 生成报告
    report = generate_report(results)
    print("\n" + report)
    
    # 保存结果
    with open("dice_test_results_v7.json", "w", encoding="utf-8") as f:
        # 转换defaultdict为普通dict以便JSON序列化
        def convert_to_serializable(obj):
            if isinstance(obj, defaultdict):
                return dict(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(i) for i in obj]
            return obj
        
        json.dump(convert_to_serializable(results), f, ensure_ascii=False, indent=2)
    
    # 保存报告
    with open("dice_test_report_v7.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\nResults saved to dice_test_results_v7.json")
    print("Report saved to dice_test_report_v7.txt")
