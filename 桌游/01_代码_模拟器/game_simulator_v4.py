# -*- coding: utf-8 -*-
"""
救赎之路 v4.0 模拟器
- 支持3-7人可变人数
- 48张事件卡系统
- 详细的胜利来源追踪（机制/事件/骰子/互动/道路）
- 三种骰子系统
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
    SANGHA = "僧伽"      # 僧侣
    PATRON = "护法"      # 富商
    LANDOWNER = "田主"   # 地主
    SCHOLAR = "士人"     # 文人
    PEASANT = "农人"     # 农民
    UPASIKA = "虔信女"   # 居士
    EMPEROR = "皇帝"     # 帝王

# 人数与角色配置
PLAYER_CONFIG = {
    3: [Role.SANGHA, Role.PATRON, Role.PEASANT],
    4: [Role.SANGHA, Role.PATRON, Role.PEASANT, Role.LANDOWNER],
    5: [Role.SANGHA, Role.PATRON, Role.PEASANT, Role.LANDOWNER, Role.UPASIKA],
    6: [Role.SANGHA, Role.PATRON, Role.PEASANT, Role.LANDOWNER, Role.UPASIKA, Role.SCHOLAR],
    7: [Role.SANGHA, Role.PATRON, Role.PEASANT, Role.LANDOWNER, Role.UPASIKA, Role.SCHOLAR, Role.EMPEROR],
}

class DiceResult(Enum):
    # 业力骰
    KARMA_ADVERSE = "逆境"
    KARMA_NORMAL = "平常"
    KARMA_FAVORABLE = "顺缘"
    # 修行骰
    PRACTICE_BLOCKED = "受阻"
    PRACTICE_NORMAL = "正常"
    PRACTICE_DILIGENT = "精进"
    PRACTICE_ENLIGHTENED = "大彻大悟"
    # 因缘骰
    FATE_SHALLOW = "缘浅"
    FATE_NORMAL = "普通"
    FATE_DEEP = "深缘"

class EventCategory(Enum):
    CELESTIAL = "天象类"
    DHARMA = "法会类"
    SECULAR = "世俗类"
    DISASTER = "灾难类"
    OPPORTUNITY = "机缘类"
    IMPERIAL = "皇恩类"

class ScoreSource(Enum):
    MECHANISM = "机制"
    EVENT = "事件"
    DICE = "骰子"
    INTERACTION = "互动"
    PATH = "道路"

# ═══════════════════════════════════════════════════════════════════
#                           事件卡定义
# ═══════════════════════════════════════════════════════════════════

@dataclass
class EventCard:
    id: int
    name: str
    category: EventCategory
    description: str
    copies: int  # 这种卡有几张

# 48张事件卡定义
EVENT_CARDS = [
    # 天象类 - 8张
    EventCard(1, "瑞雪兆丰年", EventCategory.CELESTIAL, "所有玩家+2粮", 2),
    EventCard(2, "五谷丰登", EventCategory.CELESTIAL, "田主+土地数×2粮，农人+3粮", 2),
    EventCard(3, "月蚀示警", EventCategory.CELESTIAL, "所有玩家-1功德（掷4+免除）", 1),
    EventCard(4, "祥云呈瑞", EventCategory.CELESTIAL, "僧伽+2法力，所有玩家+1功德", 2),
    EventCard(5, "彗星过境", EventCategory.CELESTIAL, "所有行动消耗+1，皇帝-2龙气", 1),
    
    # 法会类 - 8张
    EventCard(6, "盂兰盆会", EventCategory.DHARMA, "可捐2钱获3功德，虔信女额外+2功德", 2),
    EventCard(7, "水陆法会", EventCategory.DHARMA, "僧伽主持，参与者+4功德", 1),
    EventCard(8, "开光大典", EventCategory.DHARMA, "建寺者额外+5功德", 2),
    EventCard(9, "传戒法会", EventCategory.DHARMA, "僧伽收徒，被收者功德行动+1", 1),
    EventCard(10, "经书抄写", EventCategory.DHARMA, "消耗1钱+1行动点获+2功德", 2),
    
    # 世俗类 - 10张
    EventCard(11, "商队到来", EventCategory.SECULAR, "护法+3钱，可用2粮换3钱", 2),
    EventCard(12, "茶马互市", EventCategory.SECULAR, "任意两位可交换资源，双方+1功德", 1),
    EventCard(13, "新科进士", EventCategory.SECULAR, "士人+2声望+1文名", 2),
    EventCard(14, "丰收集市", EventCategory.SECULAR, "3粮换4钱", 2),
    EventCard(15, "庙会", EventCategory.SECULAR, "可购买护身符，1钱免下次负面事件", 1),
    EventCard(16, "香客云集", EventCategory.SECULAR, "僧伽+2法力，护法捐钱效率提升", 2),
    
    # 灾难类 - 8张
    EventCard(17, "大旱", EventCategory.DISASTER, "所有玩家-3粮", 2),
    EventCard(18, "蝗灾", EventCategory.DISASTER, "所有-2粮，农人-4粮", 1),
    EventCard(19, "瘟疫", EventCategory.DISASTER, "掷骰决定效果", 1),
    EventCard(20, "盗匪", EventCategory.DISASTER, "钱最多者-3钱，田主-1地", 2),
    EventCard(21, "火灾", EventCategory.DISASTER, "随机一人失去一半资源", 1),
    EventCard(22, "洪水", EventCategory.DISASTER, "所有-2粮-1钱，田主-1地", 1),
    
    # 机缘类 - 8张
    EventCard(23, "得遇高僧", EventCategory.OPPORTUNITY, "选择一人+3功德", 2),
    EventCard(24, "古经出土", EventCategory.OPPORTUNITY, "僧伽+3法力，士人+2文名+2功德", 1),
    EventCard(25, "贵人相助", EventCategory.OPPORTUNITY, "功德最低者+3功德", 2),
    EventCard(26, "顿悟时刻", EventCategory.OPPORTUNITY, "获得觉醒状态，本轮功德翻倍", 1),
    EventCard(27, "菩萨示现", EventCategory.OPPORTUNITY, "虔信女进入菩萨状态或所有+2功德", 1),
    EventCard(28, "福报现前", EventCategory.OPPORTUNITY, "功德最高者可转化3功德为资源", 1),
    
    # 皇恩类 - 6张
    EventCard(29, "圣驾亲临", EventCategory.IMPERIAL, "皇帝钦赐匾额", 2),
    EventCard(30, "恩科取士", EventCategory.IMPERIAL, "士人+3声望", 1),
    EventCard(31, "赈灾诏令", EventCategory.IMPERIAL, "皇帝消耗2龙气，所有+2粮+1钱", 1),
    EventCard(32, "敕建寺院", EventCategory.IMPERIAL, "皇帝免费建寺", 1),
    EventCard(33, "法难预兆", EventCategory.IMPERIAL, "皇帝选择护法或不护", 1),
]

def build_event_deck() -> List[EventCard]:
    """根据copies数量构建完整的事件牌组"""
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
    
    # 通用资源
    coins: int = 0
    grain: int = 0
    land: int = 0
    merit: int = 0
    life: int = 10
    action_points: int = 2
    
    # 专属资源
    dharma_power: int = 0       # 法力（僧伽）
    grant_points: int = 0       # 授德点（僧伽）
    total_donated: int = 0      # 累计捐献（护法）
    inheritance_points: int = 0 # 传承点（田主）
    land_donated: int = 0       # 捐地数（田主）
    has_built_temple: bool = False
    literary_fame: int = 0      # 文名（士人）
    prestige: int = 0           # 声望（士人/皇帝）
    inscriptions: int = 0       # 撰碑数（士人）
    diligence_points: int = 0   # 勤劳点（农人）
    good_deeds: int = 0         # 日行一善次数（农人）
    shared_harvest: int = 0     # 分享收成次数（农人）
    salvation_points: int = 0   # 渡化点（虔信女）
    beings_saved: int = 0       # 渡化人数（虔信女）
    bodhisattva_mode: bool = False
    dragon_qi: int = 0          # 龙气（皇帝）
    imperial_grants: int = 0    # 钦赐次数（皇帝）
    
    # 状态
    retreat_mode: bool = False  # 闭关状态
    karma_state: DiceResult = DiceResult.KARMA_NORMAL
    awakened: bool = False      # 觉醒状态
    has_amulet: bool = False    # 护身符
    disciple_of: int = -1       # 师父ID
    
    # 得分来源追踪
    score_sources: Dict = field(default_factory=lambda: {
        ScoreSource.MECHANISM: 0,
        ScoreSource.EVENT: 0,
        ScoreSource.DICE: 0,
        ScoreSource.INTERACTION: 0,
        ScoreSource.PATH: 0,
    })
    
    # 骰子统计
    dice_stats: Dict = field(default_factory=lambda: {
        "karma_favorable": 0,
        "karma_adverse": 0,
        "practice_enlightened": 0,
        "fate_deep": 0,
    })
    
    def __post_init__(self):
        """根据角色设置初始资源"""
        if self.role == Role.SANGHA:
            self.dharma_power = 6
            self.merit = 2
            self.action_points = 2
        elif self.role == Role.PATRON:
            self.coins = 10
            self.grain = 2
            self.action_points = 2
        elif self.role == Role.LANDOWNER:
            self.land = 3
            self.coins = 2
            self.grain = 3
            self.action_points = 2
        elif self.role == Role.SCHOLAR:
            self.coins = 3
            self.grain = 2
            self.literary_fame = 2
            self.prestige = 2
            self.action_points = 2
        elif self.role == Role.PEASANT:
            self.grain = 5
            self.coins = 2
            self.action_points = 3
        elif self.role == Role.UPASIKA:
            self.coins = 3
            self.grain = 2
            self.merit = 4
            self.action_points = 2
        elif self.role == Role.EMPEROR:
            self.coins = 6
            self.grain = 4
            self.land = 2
            self.dragon_qi = 3
            self.prestige = 4
            self.action_points = 2
    
    def add_merit(self, amount: int, source: ScoreSource):
        """添加功德并记录来源"""
        if self.awakened:
            amount *= 2
        self.merit += amount
        self.score_sources[source] += amount * 2  # 功德×2计入得分
    
    def check_path_completion(self) -> Tuple[bool, str, int]:
        """检查是否完成专属道路"""
        if self.role == Role.SANGHA:
            if self.dharma_power <= 2 and self.grant_points >= 12:
                return (True, "涅槃道", 40)
            elif self.grant_points >= 8:
                return (True, "涅槃道（小成）", 20)
        
        elif self.role == Role.PATRON:
            if self.total_donated >= 18 and self.coins <= 3:
                return (True, "善财道", 45)
            elif self.total_donated >= 12:
                return (True, "善财道（小成）", 22)
        
        elif self.role == Role.LANDOWNER:
            if self.land_donated >= 3 and self.has_built_temple:
                return (True, "舍宅道", 50)
            elif self.land_donated >= 2:
                return (True, "舍宅道（小成）", 25)
        
        elif self.role == Role.SCHOLAR:
            if self.prestige >= 6 and self.inscriptions >= 3:
                return (True, "清名道", 40)
            elif self.inscriptions >= 2:
                return (True, "清名道（小成）", 20)
        
        elif self.role == Role.PEASANT:
            if self.good_deeds >= 5 and self.shared_harvest >= 3:
                return (True, "勤劳道", 45)
            elif self.good_deeds >= 3:
                return (True, "勤劳道（小成）", 22)
        
        elif self.role == Role.UPASIKA:
            if self.bodhisattva_mode and self.beings_saved >= 3:
                return (True, "菩萨道", 45)
            elif self.bodhisattva_mode:
                return (True, "菩萨道（小成）", 22)
        
        elif self.role == Role.EMPEROR:
            if self.dragon_qi >= 10 and self.imperial_grants >= 3:
                return (True, "天命道", 50)
            elif self.imperial_grants >= 2:
                return (True, "天命道（小成）", 25)
        
        return (False, "", 0)
    
    def get_final_score(self) -> float:
        """计算最终得分"""
        # 基础分
        base_score = self.merit * 2
        resources = self.coins + self.grain + self.land * 2
        base_score += resources / 4
        
        # 角色加分
        role_bonus = 0
        if self.role == Role.SANGHA:
            role_bonus = self.grant_points * 2
        elif self.role == Role.PATRON:
            role_bonus = self.total_donated
        elif self.role == Role.LANDOWNER:
            role_bonus = self.inheritance_points * 2 + self.land_donated * 4
        elif self.role == Role.SCHOLAR:
            role_bonus = self.prestige * 2 + self.literary_fame * 3
        elif self.role == Role.PEASANT:
            role_bonus = self.diligence_points * 2
        elif self.role == Role.UPASIKA:
            role_bonus = self.salvation_points * 3 + self.beings_saved * 5
        elif self.role == Role.EMPEROR:
            role_bonus = self.dragon_qi * 2 + self.prestige * 2
        
        self.score_sources[ScoreSource.MECHANISM] += role_bonus
        
        # 道路加分
        path_complete, path_name, path_bonus = self.check_path_completion()
        if path_complete:
            self.score_sources[ScoreSource.PATH] = path_bonus
        
        total = base_score + role_bonus + path_bonus
        return total
    
    def get_score_breakdown(self) -> Dict:
        """获取得分来源明细"""
        return {
            source.value: points 
            for source, points in self.score_sources.items()
        }

# ═══════════════════════════════════════════════════════════════════
#                           骰子系统
# ═══════════════════════════════════════════════════════════════════

def roll_d6() -> int:
    return random.randint(1, 6)

def roll_karma_dice() -> Tuple[int, DiceResult]:
    """业力骰"""
    roll = roll_d6()
    if roll <= 2:
        return roll, DiceResult.KARMA_ADVERSE
    elif roll <= 4:
        return roll, DiceResult.KARMA_NORMAL
    else:
        return roll, DiceResult.KARMA_FAVORABLE

def roll_practice_dice() -> Tuple[int, DiceResult]:
    """修行骰"""
    roll = roll_d6()
    if roll == 1:
        return roll, DiceResult.PRACTICE_BLOCKED
    elif roll <= 4:
        return roll, DiceResult.PRACTICE_NORMAL
    elif roll == 5:
        return roll, DiceResult.PRACTICE_DILIGENT
    else:
        return roll, DiceResult.PRACTICE_ENLIGHTENED

def roll_fate_dice() -> Tuple[int, DiceResult]:
    """因缘骰"""
    roll = roll_d6()
    if roll <= 2:
        return roll, DiceResult.FATE_SHALLOW
    elif roll <= 4:
        return roll, DiceResult.FATE_NORMAL
    else:
        return roll, DiceResult.FATE_DEEP

# ═══════════════════════════════════════════════════════════════════
#                           游戏模拟器
# ═══════════════════════════════════════════════════════════════════

class GameSimulator:
    def __init__(self, num_players: int = 7):
        if num_players < 3 or num_players > 7:
            raise ValueError("Player count must be 3-7")
        self.num_players = num_players
        self.roles = PLAYER_CONFIG[num_players]
        
    def create_game(self) -> Dict:
        """创建新游戏"""
        players = []
        for i, role in enumerate(self.roles):
            players.append(Player(role=role, player_id=i))
        
        return {
            "players": players,
            "round": 1,
            "event_deck": build_event_deck(),
            "current_event": None,
            "round_bonus_action_cost": 0,  # 彗星过境等效果
            "has_emperor": Role.EMPEROR in self.roles,
            "temple_built_this_round": False,
            "round_events": [],
        }
    
    def find_sangha(self, game: Dict) -> Optional[Player]:
        """找到僧伽玩家"""
        for p in game["players"]:
            if p.role == Role.SANGHA:
                return p
        return None
    
    # ─────────────────────────────────────────────────────────────
    #                        事件处理
    # ─────────────────────────────────────────────────────────────
    
    def process_event(self, game: Dict, event: EventCard):
        """处理事件卡效果"""
        players = game["players"]
        sangha = self.find_sangha(game)
        
        # 皇恩类事件：无皇帝时跳过
        if event.category == EventCategory.IMPERIAL and not game["has_emperor"]:
            return
        
        # 天象类
        if event.id == 1:  # 瑞雪兆丰年
            for p in players:
                p.grain += 2
        
        elif event.id == 2:  # 五谷丰登
            for p in players:
                if p.role == Role.LANDOWNER:
                    p.grain += p.land * 2
                elif p.role == Role.PEASANT:
                    p.grain += 3
        
        elif event.id == 3:  # 月蚀示警
            for p in players:
                roll = roll_d6()
                if roll < 4 and p.merit > 0:
                    if not p.has_amulet:
                        p.merit = max(0, p.merit - 1)
                    else:
                        p.has_amulet = False
        
        elif event.id == 4:  # 祥云呈瑞
            if sangha:
                sangha.dharma_power += 2
            for p in players:
                p.add_merit(1, ScoreSource.EVENT)
        
        elif event.id == 5:  # 彗星过境
            game["round_bonus_action_cost"] = 1
            for p in players:
                if p.role == Role.EMPEROR:
                    p.dragon_qi = max(0, p.dragon_qi - 2)
        
        # 法会类
        elif event.id == 6:  # 盂兰盆会
            for p in players:
                if p.coins >= 2:
                    p.coins -= 2
                    p.add_merit(3, ScoreSource.EVENT)
                    if p.role == Role.UPASIKA:
                        p.add_merit(2, ScoreSource.EVENT)
                    if sangha:
                        sangha.dharma_power += 1
        
        elif event.id == 7:  # 水陆法会
            if sangha and sangha.dharma_power >= 3:
                sangha.dharma_power -= 3
                sangha.grant_points += 3
                for p in players:
                    if p.coins >= 3:
                        p.coins -= 3
                        p.add_merit(4, ScoreSource.EVENT)
        
        elif event.id == 8:  # 开光大典
            if game["temple_built_this_round"]:
                for p in players:
                    if p.has_built_temple:
                        p.add_merit(5, ScoreSource.EVENT)
                        if sangha:
                            sangha.grant_points += 2
        
        elif event.id == 9:  # 传戒法会
            if sangha:
                # 随机选择一个非僧伽玩家作为徒弟
                others = [p for p in players if p.role != Role.SANGHA]
                if others:
                    disciple = random.choice(others)
                    disciple.disciple_of = sangha.player_id
                    sangha.grant_points += 1
        
        elif event.id == 10:  # 经书抄写
            for p in players:
                if p.coins >= 1 and p.action_points >= 1:
                    p.coins -= 1
                    p.action_points -= 1
                    p.add_merit(2, ScoreSource.EVENT)
                    if p.role == Role.SCHOLAR:
                        p.literary_fame += 1
        
        # 世俗类
        elif event.id == 11:  # 商队到来
            for p in players:
                if p.role == Role.PATRON:
                    p.coins += 3
                if p.grain >= 2:
                    p.grain -= 2
                    p.coins += 3
        
        elif event.id == 12:  # 茶马互市
            # 简化：功德最低和最高者交换部分资源
            if len(players) >= 2:
                sorted_p = sorted(players, key=lambda x: x.merit)
                low, high = sorted_p[0], sorted_p[-1]
                if low != high:
                    # 交换一些粮食
                    exchange = min(2, low.grain, high.grain)
                    low.add_merit(1, ScoreSource.INTERACTION)
                    high.add_merit(1, ScoreSource.INTERACTION)
        
        elif event.id == 13:  # 新科进士
            for p in players:
                if p.role == Role.SCHOLAR:
                    p.prestige += 2
                    p.literary_fame += 1
                    p.inscriptions += 1  # 免费撰碑
        
        elif event.id == 14:  # 丰收集市
            for p in players:
                if p.grain >= 3:
                    p.grain -= 3
                    p.coins += 4
        
        elif event.id == 15:  # 庙会
            for p in players:
                if p.coins >= 1 and not p.has_amulet:
                    p.coins -= 1
                    p.has_amulet = True
        
        elif event.id == 16:  # 香客云集
            if sangha:
                sangha.dharma_power += 2
            # 护法捐钱效率本轮提升（简化处理）
            for p in players:
                if p.role == Role.PATRON:
                    p.add_merit(1, ScoreSource.EVENT)
        
        # 灾难类
        elif event.id == 17:  # 大旱
            for p in players:
                if not p.has_amulet:
                    p.grain = max(0, p.grain - 3)
                else:
                    p.has_amulet = False
        
        elif event.id == 18:  # 蝗灾
            for p in players:
                if not p.has_amulet:
                    loss = 4 if p.role == Role.PEASANT else 2
                    p.grain = max(0, p.grain - loss)
                else:
                    p.has_amulet = False
        
        elif event.id == 19:  # 瘟疫
            for p in players:
                if p.has_amulet:
                    p.has_amulet = False
                    continue
                roll = roll_d6()
                if roll <= 2:
                    p.merit = max(0, p.merit - 2)
                elif roll >= 5:
                    p.add_merit(1, ScoreSource.EVENT)
        
        elif event.id == 20:  # 盗匪
            richest = max(players, key=lambda x: x.coins)
            if not richest.has_amulet:
                richest.coins = max(0, richest.coins - 3)
            else:
                richest.has_amulet = False
            for p in players:
                if p.role == Role.LANDOWNER and p.land > 0:
                    if not p.has_amulet:
                        p.land -= 1
                    else:
                        p.has_amulet = False
        
        elif event.id == 21:  # 火灾
            victim = random.choice(players)
            if not victim.has_amulet:
                victim.coins //= 2
                victim.grain //= 2
            else:
                victim.has_amulet = False
            # 僧伽可保护
            if sangha and sangha.dharma_power >= 2:
                sangha.dharma_power -= 2
                victim.coins *= 2
                victim.grain *= 2
        
        elif event.id == 22:  # 洪水
            for p in players:
                if p.has_amulet:
                    p.has_amulet = False
                    continue
                p.grain = max(0, p.grain - 2)
                p.coins = max(0, p.coins - 1)
                if p.role == Role.LANDOWNER and p.land > 0:
                    p.land -= 1
            # 农人救灾
            for p in players:
                if p.role == Role.PEASANT and p.action_points >= 2:
                    p.action_points -= 2
                    p.add_merit(3, ScoreSource.EVENT)
        
        # 机缘类
        elif event.id == 23:  # 得遇高僧
            if sangha:
                # 选择功德最低的玩家
                target = min(players, key=lambda x: x.merit)
                target.add_merit(3, ScoreSource.EVENT)
                sangha.grant_points += 1
                # 修行骰
                roll, result = roll_practice_dice()
                if result == DiceResult.PRACTICE_ENLIGHTENED:
                    target.add_merit(5, ScoreSource.DICE)
                    target.dice_stats["practice_enlightened"] += 1
        
        elif event.id == 24:  # 古经出土
            if sangha:
                sangha.dharma_power += 3
            for p in players:
                if p.role == Role.SCHOLAR:
                    p.literary_fame += 2
                    p.add_merit(2, ScoreSource.EVENT)
        
        elif event.id == 25:  # 贵人相助
            lowest = min(players, key=lambda x: x.merit)
            lowest.add_merit(3, ScoreSource.EVENT)
            # 护法可额外帮助
            for p in players:
                if p.role == Role.PATRON and p.coins >= 3:
                    p.coins -= 3
                    lowest.add_merit(2, ScoreSource.INTERACTION)
                    p.add_merit(1, ScoreSource.INTERACTION)
        
        elif event.id == 26:  # 顿悟时刻
            # 当前玩家觉醒
            current = random.choice(players)
            current.awakened = True
        
        elif event.id == 27:  # 菩萨示现
            has_upasika = False
            for p in players:
                if p.role == Role.UPASIKA:
                    p.bodhisattva_mode = True
                    has_upasika = True
            if not has_upasika:
                for p in players:
                    p.add_merit(2, ScoreSource.EVENT)
        
        elif event.id == 28:  # 福报现前
            highest = max(players, key=lambda x: x.merit)
            if highest.merit >= 3:
                highest.merit -= 3
                highest.coins += 3
                highest.grain += 2
        
        # 皇恩类
        elif event.id == 29:  # 圣驾亲临
            emperor = None
            for p in players:
                if p.role == Role.EMPEROR:
                    emperor = p
                    break
            if emperor:
                # 选择功德最高的非皇帝玩家
                others = [p for p in players if p.role != Role.EMPEROR]
                if others:
                    target = max(others, key=lambda x: x.merit)
                    target.add_merit(4, ScoreSource.EVENT)
                    emperor.dragon_qi += 2
                    emperor.prestige += 1
                    emperor.imperial_grants += 1
        
        elif event.id == 30:  # 恩科取士
            for p in players:
                if p.role == Role.SCHOLAR:
                    p.prestige += 3
                    p.add_merit(2, ScoreSource.EVENT)
        
        elif event.id == 31:  # 赈灾诏令
            emperor = None
            for p in players:
                if p.role == Role.EMPEROR:
                    emperor = p
            if emperor and emperor.dragon_qi >= 2:
                emperor.dragon_qi -= 2
                for p in players:
                    p.grain += 2
                    p.coins += 1
                emperor.add_merit(3, ScoreSource.EVENT)
        
        elif event.id == 32:  # 敕建寺院
            emperor = None
            for p in players:
                if p.role == Role.EMPEROR:
                    emperor = p
            if emperor:
                emperor.has_built_temple = True
                emperor.add_merit(5, ScoreSource.EVENT)
                emperor.dragon_qi += 2
                game["temple_built_this_round"] = True
                if sangha:
                    sangha.grant_points += 3
        
        elif event.id == 33:  # 法难预兆
            emperor = None
            for p in players:
                if p.role == Role.EMPEROR:
                    emperor = p
            if emperor:
                # AI决策：保护概率50%
                if random.random() < 0.5:
                    emperor.dragon_qi = max(0, emperor.dragon_qi - 2)
                else:
                    if sangha:
                        sangha.dharma_power = max(0, sangha.dharma_power - 3)
                    emperor.prestige = max(0, emperor.prestige - 1)
    
    # ─────────────────────────────────────────────────────────────
    #                        生产阶段
    # ─────────────────────────────────────────────────────────────
    
    def production_phase(self, game: Dict):
        """生产阶段"""
        for p in game["players"]:
            if p.role == Role.SANGHA:
                if p.retreat_mode:
                    p.grant_points += 2
                else:
                    p.dharma_power += 1
            
            elif p.role == Role.PATRON:
                p.coins += 2
            
            elif p.role == Role.LANDOWNER:
                p.grain += p.land
            
            elif p.role == Role.SCHOLAR:
                if game["round"] % 2 == 0:
                    p.literary_fame += 1
            
            elif p.role == Role.PEASANT:
                p.grain += 2
                p.diligence_points += 1
            
            elif p.role == Role.UPASIKA:
                p.add_merit(1, ScoreSource.MECHANISM)
            
            elif p.role == Role.EMPEROR:
                if game["round"] % 3 == 0:
                    p.dragon_qi += 1
    
    # ─────────────────────────────────────────────────────────────
    #                        行动阶段
    # ─────────────────────────────────────────────────────────────
    
    def action_phase(self, game: Dict):
        """行动阶段"""
        sangha = self.find_sangha(game)
        
        for p in game["players"]:
            # 计算行动点
            base_ap = 3 if p.role == Role.PEASANT else 2
            karma_mod = 0
            if p.karma_state == DiceResult.KARMA_FAVORABLE:
                karma_mod = 1
            elif p.karma_state == DiceResult.KARMA_ADVERSE:
                karma_mod = -1
            
            ap = max(1, base_ap + karma_mod)
            p.action_points = ap
            
            # 执行行动
            while p.action_points > 0:
                action_cost = 1 + game["round_bonus_action_cost"]
                if p.action_points < action_cost:
                    break
                
                action = self.decide_action(p, game)
                if action is None:
                    break
                
                self.execute_action(p, action, game, sangha)
                p.action_points -= action_cost
    
    def decide_action(self, player: Player, game: Dict) -> Optional[str]:
        """AI决策选择行动"""
        role = player.role
        
        # 根据角色选择最优行动
        if role == Role.SANGHA:
            if player.dharma_power >= 3:
                return "grant_dharma"
            elif player.dharma_power >= 2:
                return "chant"
            return None
        
        elif role == Role.PATRON:
            if player.coins >= 10:
                return "build_temple"
            elif player.coins >= 5:
                return "big_donation"
            elif player.coins >= 3:
                return "donate"
            return None
        
        elif role == Role.LANDOWNER:
            if player.land >= 2 and not player.has_built_temple:
                return "donate_land_temple"
            elif player.land >= 1 and random.random() < 0.3:
                return "donate_land"
            elif player.coins >= 4:
                return "buy_land"
            elif player.coins >= 3:
                return "donate"
            return None
        
        elif role == Role.SCHOLAR:
            if player.literary_fame >= 1:
                return "inscribe"
            elif player.coins >= 3:
                return "donate"
            return "compose"
        
        elif role == Role.PEASANT:
            if player.grain >= 2:
                return "share_harvest"
            elif player.grain >= 1:
                return "good_deed"
            return None
        
        elif role == Role.UPASIKA:
            if player.bodhisattva_mode and player.merit >= 4:
                return "save_beings"
            elif player.merit >= 2:
                return "transfer_merit"
            elif player.coins >= 3:
                return "donate"
            return None
        
        elif role == Role.EMPEROR:
            if player.coins >= 2:
                return "imperial_grant"
            elif player.dragon_qi >= 1:
                return "pray_decree"
            return None
        
        return None
    
    def execute_action(self, player: Player, action: str, game: Dict, sangha: Optional[Player]):
        """执行行动"""
        
        if action == "donate":
            if player.coins >= 3:
                player.coins -= 3
                player.total_donated += 3
                roll, result = roll_practice_dice()
                merit_gain = 1
                if result == DiceResult.PRACTICE_DILIGENT:
                    merit_gain = 2
                elif result == DiceResult.PRACTICE_ENLIGHTENED:
                    merit_gain = 3
                    player.dice_stats["practice_enlightened"] += 1
                elif result == DiceResult.PRACTICE_BLOCKED:
                    merit_gain = 1
                
                # 徒弟加成
                if player.disciple_of >= 0:
                    merit_gain += 1
                
                player.add_merit(merit_gain, ScoreSource.MECHANISM)
                if sangha:
                    sangha.dharma_power += 1
        
        elif action == "grant_dharma":
            if player.role == Role.SANGHA and player.dharma_power >= 3:
                amount = min(3, player.dharma_power)
                player.dharma_power -= amount
                player.grant_points += amount
                # 随机选择目标
                others = [p for p in game["players"] if p.role != Role.SANGHA]
                if others:
                    target = random.choice(others)
                    target.add_merit(amount, ScoreSource.INTERACTION)
                    player.score_sources[ScoreSource.INTERACTION] += amount
        
        elif action == "chant":
            if player.role == Role.SANGHA and player.dharma_power >= 2:
                player.dharma_power -= 2
                player.grant_points += 1
                others = [p for p in game["players"] if p.role != Role.SANGHA]
                if others:
                    target = random.choice(others)
                    target.add_merit(2, ScoreSource.INTERACTION)
        
        elif action == "big_donation":
            if player.role == Role.PATRON and player.coins >= 5:
                amount = min(player.coins, 9)
                player.coins -= amount
                player.total_donated += amount
                merit = (amount // 3) * 2
                player.add_merit(merit, ScoreSource.MECHANISM)
                if sangha:
                    sangha.dharma_power += 2
        
        elif action == "build_temple":
            if player.coins >= 10:
                player.coins -= 10
                player.total_donated += 10
                player.has_built_temple = True
                game["temple_built_this_round"] = True
                roll, result = roll_practice_dice()
                merit = 8
                if result == DiceResult.PRACTICE_ENLIGHTENED:
                    merit = 12
                    player.dice_stats["practice_enlightened"] += 1
                player.add_merit(merit, ScoreSource.MECHANISM)
        
        elif action == "buy_land":
            if player.coins >= 4:
                player.coins -= 4
                player.land += 1
        
        elif action == "donate_land":
            if player.land >= 1:
                player.land -= 1
                player.land_donated += 1
                player.add_merit(5, ScoreSource.MECHANISM)
        
        elif action == "donate_land_temple":
            if player.land >= 2:
                player.land -= 2
                player.land_donated += 2
                player.has_built_temple = True
                game["temple_built_this_round"] = True
                player.add_merit(15, ScoreSource.MECHANISM)
        
        elif action == "inscribe":
            if player.literary_fame >= 1:
                player.literary_fame -= 1
                player.prestige += 2
                player.inscriptions += 1
                player.add_merit(1, ScoreSource.MECHANISM)
                if sangha:
                    sangha.grant_points += 1
        
        elif action == "compose":
            player.literary_fame += 1
            player.add_merit(1, ScoreSource.MECHANISM)
        
        elif action == "good_deed":
            if player.grain >= 1:
                player.grain -= 1
                player.good_deeds += 1
                player.add_merit(2, ScoreSource.MECHANISM)
        
        elif action == "share_harvest":
            if player.grain >= 2:
                player.grain -= 2
                player.shared_harvest += 1
                # 分享给他人
                others = [p for p in game["players"] if p.player_id != player.player_id]
                if others:
                    target = random.choice(others)
                    target.grain += 2
                    roll, result = roll_fate_dice()
                    if result == DiceResult.FATE_DEEP:
                        player.add_merit(2, ScoreSource.DICE)
                        target.add_merit(1, ScoreSource.DICE)
                        player.dice_stats["fate_deep"] += 1
                    else:
                        player.add_merit(1, ScoreSource.INTERACTION)
                        target.add_merit(1, ScoreSource.INTERACTION)
        
        elif action == "transfer_merit":
            if player.merit >= 2:
                player.merit -= 2
                player.salvation_points += 3
        
        elif action == "save_beings":
            if player.bodhisattva_mode and player.merit >= 4:
                player.merit -= 4
                others = [p for p in game["players"] if p.player_id != player.player_id]
                if others:
                    target = random.choice(others)
                    target.add_merit(4, ScoreSource.INTERACTION)
                    player.salvation_points += 4
                    player.beings_saved += 1
        
        elif action == "imperial_grant":
            if player.coins >= 2:
                player.coins -= 2
                player.imperial_grants += 1
                player.dragon_qi += 2
                player.prestige += 1
                others = [p for p in game["players"] if p.role != Role.EMPEROR]
                if others:
                    target = random.choice(others)
                    target.add_merit(3, ScoreSource.INTERACTION)
        
        elif action == "pray_decree":
            if player.dragon_qi >= 1 and sangha:
                player.dragon_qi -= 1
                player.dragon_qi += 2
                sangha.dharma_power -= 1
                sangha.grant_points += 2
    
    # ─────────────────────────────────────────────────────────────
    #                        运行游戏
    # ─────────────────────────────────────────────────────────────
    
    def run_game(self) -> Dict:
        """运行一局完整游戏"""
        game = self.create_game()
        
        for round_num in range(1, 11):
            game["round"] = round_num
            game["round_bonus_action_cost"] = 0
            game["temple_built_this_round"] = False
            
            # 天机阶段
            if game["event_deck"]:
                event = game["event_deck"].pop()
                game["current_event"] = event
                game["round_events"].append(event.name)
                
                # 业力骰
                for p in game["players"]:
                    roll, result = roll_karma_dice()
                    p.karma_state = result
                    if result == DiceResult.KARMA_FAVORABLE:
                        p.dice_stats["karma_favorable"] += 1
                    elif result == DiceResult.KARMA_ADVERSE:
                        p.dice_stats["karma_adverse"] += 1
                
                # 处理事件
                self.process_event(game, event)
            
            # 生产阶段
            self.production_phase(game)
            
            # 行动阶段
            self.action_phase(game)
            
            # 轮回阶段
            for p in game["players"]:
                p.life -= 1
                p.awakened = False  # 觉醒状态每轮重置
        
        # 计算最终得分
        results = []
        for p in game["players"]:
            final_score = p.get_final_score()
            path_complete, path_name, path_bonus = p.check_path_completion()
            
            results.append({
                "role": p.role.value,
                "score": round(final_score, 1),
                "merit": p.merit,
                "path_completed": path_name if path_complete else "",
                "path_bonus": path_bonus if path_complete else 0,
                "score_breakdown": p.get_score_breakdown(),
                "dice_stats": p.dice_stats.copy(),
            })
        
        # 确定胜者
        results.sort(key=lambda x: x["score"], reverse=True)
        winner = results[0]["role"]
        
        return {
            "winner": winner,
            "results": results,
            "events": game["round_events"],
            "num_players": self.num_players,
        }
    
    def run_batch(self, num_games: int) -> Dict:
        """批量运行游戏"""
        wins = defaultdict(int)
        total_scores = defaultdict(list)
        path_completions = defaultdict(int)
        source_totals = defaultdict(lambda: defaultdict(float))
        event_counts = defaultdict(int)
        
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
            
            for event in result["events"]:
                event_counts[event] += 1
        
        # 计算统计
        stats = {
            "num_games": num_games,
            "num_players": self.num_players,
            "roles_used": [r.value for r in self.roles],
            "win_rates": {},
            "avg_scores": {},
            "path_completion_rates": {},
            "score_source_breakdown": {},
            "event_frequency": dict(event_counts),
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
                total = sum(sources.values())
                if total > 0:
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
    
    # 测试不同人数
    for num_players in [3, 4, 5, 6, 7]:
        print(f"\n{'='*60}")
        print(f"Testing {num_players}-player game...")
        print(f"{'='*60}")
        
        simulator = GameSimulator(num_players)
        
        # 运行100, 1000, 10000局
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
        print(f"\n  [10000 games summary]")
        print(f"  Roles: {', '.join(stats['roles_used'])}")
        print(f"  Win rates:")
        for role, rate in sorted(stats["win_rates"].items(), key=lambda x: -x[1]):
            print(f"    {role}: {rate}%")
        print(f"  Avg scores:")
        for role, score in sorted(stats["avg_scores"].items(), key=lambda x: -x[1]):
            print(f"    {role}: {score}")
    
    # 保存结果
    with open("simulation_results_v4.json", "w", encoding="utf-8") as f:
        json.dump(results_all, f, ensure_ascii=False, indent=2)
    
    print("\n\nResults saved to simulation_results_v4.json")
    return results_all


if __name__ == "__main__":
    main()
