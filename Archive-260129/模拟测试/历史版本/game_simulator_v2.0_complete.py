"""
《功德轮回：众生百态》v2.0 完整版模拟器

版本说明：
- v2.0: 完整重构版
  - 角色重定位：官员→学者
  - 双事件卡系统：共享事件 + 专属事件
  - 发愿系统：每职业3张发愿
  - 骰子系统：2d6判定
  - 道的选择：修行传统
  - 生存消耗：每2回合-1财富

作者：AI助手
日期：2026年1月28日
"""

import random
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

# ===== 骰子系统 =====
def roll_2d6() -> int:
    """掷2d6"""
    return random.randint(1, 6) + random.randint(1, 6)

def dice_result(roll: int) -> str:
    """判定2d6结果"""
    if roll <= 4:
        return "CRIT_FAIL"  # 大失败
    elif roll <= 7:
        return "FAIL"       # 失败
    elif roll <= 9:
        return "SUCCESS"    # 成功
    else:
        return "CRIT_SUCCESS"  # 大成功

# ===== 角色系统 =====
class RoleType(Enum):
    FARMER = "农夫"      # 慢积累，稳定
    MERCHANT = "商人"    # 高财富，低慧
    SCHOLAR = "学者"     # 高智慧，清贫
    MONK = "僧侣"        # 需供养

class Tradition(Enum):
    """修行传统（道的选择）"""
    LAYMAN = "居士道"    # 平衡，无强制
    SRAVAKA = "声闻道"   # 重慧，自度
    BODHISATTVA = "菩萨道"  # 重福，度人

# 角色初始值 v2.0.1
ROLE_INIT = {
    RoleType.FARMER: {"wealth": 4, "fu": 1, "hui": 1, "desc": "勤劳积累"},
    RoleType.MERCHANT: {"wealth": 6, "fu": 1, "hui": 1, "desc": "财富多善结缘"},
    RoleType.SCHOLAR: {"wealth": 2, "fu": 1, "hui": 4, "desc": "智慧高清贫"},
    RoleType.MONK: {"wealth": 0, "fu": 2, "hui": 2, "desc": "需供养无自主财富"},
}

# ===== 发愿系统 =====
VOWS = {
    RoleType.FARMER: [
        {"name": "虔诚信徒", "level": "小愿", "cost": 3, "condition": "hui>=18", "reward": 10, "penalty": 0},
        {"name": "贫女一灯", "level": "中愿", "cost": 5, "condition": "fu>=22 and wealth<=3", "reward": 18, "penalty": -5},
        {"name": "饥饿渡生", "level": "大愿", "cost": 8, "condition": "save_count>=5", "reward": 26, "penalty": -10},
    ],
    RoleType.MERCHANT: [
        {"name": "富甲天下", "level": "小愿", "cost": 3, "condition": "wealth>=10", "reward": 12, "penalty": 0},
        {"name": "功德商人", "level": "中愿", "cost": 5, "condition": "fu>=18 and donate_count>=3", "reward": 20, "penalty": -5},
        {"name": "布施长者", "level": "大愿", "cost": 8, "condition": "save_count>=3 and fu>=20", "reward": 28, "penalty": -10},
    ],
    RoleType.SCHOLAR: [
        {"name": "学富五车", "level": "小愿", "cost": 3, "condition": "hui>=18", "reward": 14, "penalty": 0},
        {"name": "传道授业", "level": "中愿", "cost": 5, "condition": "teach_count>=3 and fu>=15", "reward": 20, "penalty": -5},
        {"name": "万世师表", "level": "大愿", "cost": 8, "condition": "hui>=22 and fu>=18", "reward": 28, "penalty": -10},
    ],
    RoleType.MONK: [
        {"name": "阿罗汉果", "level": "小愿", "cost": 3, "condition": "hui>=25", "reward": 14, "penalty": 0},
        {"name": "菩萨道", "level": "中愿", "cost": 5, "condition": "save_count>=4 and fu>=20", "reward": 22, "penalty": -5},
        {"name": "地藏宏愿", "level": "大愿", "cost": 8, "condition": "fu>=30 and team_fu_min>=15", "reward": 32, "penalty": -12},
    ],
}

# ===== 众生卡 =====
@dataclass
class SentientBeing:
    name: str
    cost: int
    fu_reward: int
    hui_reward: int
    turns_in_area: int = 0
    special: str = ""

SENTIENT_BEINGS = [
    SentientBeing("饥民", 2, 2, 1, 0, ""),
    SentientBeing("病者", 2, 2, 1, 0, ""),
    SentientBeing("孤儿", 3, 3, 1, 0, ""),
    SentientBeing("寡妇", 3, 2, 2, 0, ""),
    SentientBeing("落魄书生", 3, 1, 3, 0, "学者渡化+1慧"),
    SentientBeing("迷途商贾", 4, 2, 2, 0, "商人渡化+2财"),
    SentientBeing("悔过恶人", 4, 4, 1, 0, ""),
    SentientBeing("垂死老者", 5, 3, 3, 0, ""),
    SentientBeing("绝望工匠", 4, 2, 2, 0, ""),
    SentientBeing("沉沦官吏", 5, 2, 4, 0, "需说法"),
    SentientBeing("迷信村民", 3, 2, 2, 0, ""),
    SentientBeing("问道青年", 4, 2, 3, 0, ""),
]

# ===== 事件卡系统 =====
# 共享事件（每轮抽1张）
SHARED_EVENTS = [
    {"name": "旱灾", "type": "disaster", "effect": {"calamity": 2}},
    {"name": "洪水", "type": "disaster", "effect": {"calamity": 2}},
    {"name": "瘟疫", "type": "disaster", "effect": {"calamity": 2, "wealth_all": -1}},
    {"name": "战乱", "type": "disaster", "effect": {"calamity": 3}},
    {"name": "饥荒", "type": "disaster", "effect": {"calamity": 2}},
    {"name": "丰收", "type": "opportunity", "effect": {"wealth_all": 2}},
    {"name": "法会", "type": "opportunity", "effect": {"fu_all": 1, "hui_all": 1}},
    {"name": "高僧开示", "type": "opportunity", "effect": {"hui_all": 2}},
    {"name": "国泰民安", "type": "opportunity", "effect": {"calamity": -2}},
    {"name": "浴佛节", "type": "festival", "effect": {"fu_all": 1, "free_save": True}},
    {"name": "盂兰盆节", "type": "festival", "effect": {"fu_all": 2}},
    {"name": "施主到来", "type": "opportunity", "effect": {"wealth_all": 2}},
]

# 专属事件（每人每轮抽1张）
ROLE_EVENTS = {
    RoleType.FARMER: [
        {"name": "丰收年", "dice": True, "success": {"wealth": 4}, "fail": {"wealth": 1}},
        {"name": "蝗灾", "dice": True, "success": {"wealth": -1}, "fail": {"wealth": -3}},
        {"name": "村中长者求助", "choice": True, "help": {"fu": 2, "wealth": -2}, "ignore": {}},
        {"name": "发现灵芝", "dice": True, "success": {"hui": 2, "wealth": 2}, "fail": {}},
        {"name": "农忙", "effect": {"wealth": 2}},
        {"name": "邻里互助", "effect": {"fu": 1}},
        {"name": "土地祭祀", "dice": True, "success": {"fu": 2}, "fail": {"fu": -1}},
        {"name": "遇僧求施", "choice": True, "help": {"fu": 3, "wealth": -1}, "ignore": {}},
    ],
    RoleType.MERCHANT: [
        {"name": "商路畅通", "dice": True, "success": {"wealth": 6}, "fail": {"wealth": 2}},
        {"name": "遭遇劫匪", "dice": True, "success": {"wealth": -1}, "fail": {"wealth": -4}},
        {"name": "贫民求借", "choice": True, "help": {"fu": 3, "wealth": -3}, "ignore": {}},
        {"name": "发现商机", "dice": True, "success": {"wealth": 5}, "fail": {"wealth": -1}},
        {"name": "账房结算", "effect": {"wealth": 3}},
        {"name": "客商宴请", "effect": {"wealth": 1, "fu": -1}},
        {"name": "寺院募捐", "choice": True, "help": {"fu": 4, "wealth": -4}, "ignore": {}},
        {"name": "异乡迷路", "dice": True, "success": {}, "fail": {"wealth": -2}},
    ],
    RoleType.SCHOLAR: [
        {"name": "著书立说", "dice": True, "success": {"hui": 4}, "fail": {"hui": 1}},
        {"name": "学生求教", "effect": {"hui": 1, "fu": 1}},
        {"name": "辩论失败", "dice": True, "success": {}, "fail": {"hui": -2}},
        {"name": "受邀讲学", "dice": True, "success": {"hui": 2, "wealth": 2}, "fail": {"hui": 1}},
        {"name": "抄经修行", "effect": {"hui": 2}},
        {"name": "论道高僧", "dice": True, "success": {"hui": 3, "fu": 1}, "fail": {}},
        {"name": "贫困求助", "choice": True, "help": {"fu": 2, "wealth": -2}, "ignore": {}},
        {"name": "闭门读书", "effect": {"hui": 2, "wealth": -1}},
    ],
    RoleType.MONK: [
        {"name": "托钵化缘", "dice": True, "success": {"wealth": 3, "fu": 1}, "fail": {"wealth": 1}},
        {"name": "魔障考验", "dice": True, "success": {"hui": 3}, "fail": {"hui": -2, "fu": -1}},
        {"name": "信众供养", "effect": {"wealth": 2, "fu": 1}},
        {"name": "讲经说法", "dice": True, "success": {"fu": 3, "hui": 1}, "fail": {"fu": 1}},
        {"name": "闭关禅修", "effect": {"hui": 3, "wealth": -1}},
        {"name": "法事邀请", "choice": True, "ceremony": {"wealth": 4, "fu": -2, "hui": -1}, "decline": {"fu": 1}},
        {"name": "渡化机缘", "dice": True, "success": {"fu": 4}, "fail": {"fu": 1}},
        {"name": "破戒试探", "dice": True, "success": {"hui": 2}, "fail": {"fu": -3, "hui": -2}},
    ],
}

# ===== 行动类型 =====
class ActionType(Enum):
    LABOR = "劳作"
    PRACTICE = "修行"
    DONATE = "布施"
    SAVE = "渡化"
    PROTECT = "护法"
    SUPPORT_MONK = "供养"
    TEACH = "讲学"  # 学者专属
    ALMS = "托钵"   # 僧侣专属
    CEREMONY = "法事"  # 僧侣专属

# ===== 玩家状态 =====
@dataclass
class Player:
    role: RoleType
    tradition: Tradition
    wealth: int
    fu: int
    hui: int
    vow: Optional[Dict] = None
    
    # 统计数据
    save_count: int = 0
    donate_count: int = 0
    teach_count: int = 0
    protect_count: int = 0
    labor_count: int = 0
    starve_count: int = 0
    help_streak: int = 0
    max_streak: int = 0
    helped_this_turn: bool = False
    
    # 福慧来源统计
    fu_from_save: int = 0
    fu_from_donate: int = 0
    fu_from_protect: int = 0
    fu_from_event: int = 0
    fu_from_vow: int = 0
    hui_from_practice: int = 0
    hui_from_save: int = 0
    hui_from_event: int = 0

# ===== 游戏状态 =====
@dataclass
class GameState:
    players: List[Player]
    calamity: int = 0
    sentient_area: List[SentientBeing] = field(default_factory=list)
    saved_count: int = 0
    current_round: int = 0
    max_rounds: int = 6
    shared_event_deck: List[Dict] = field(default_factory=list)
    role_event_decks: Dict[RoleType, List[Dict]] = field(default_factory=dict)
    being_deck: List[SentientBeing] = field(default_factory=list)
    event_modifiers: Dict = field(default_factory=dict)
    save_required: int = 6
    
    def __post_init__(self):
        if not self.shared_event_deck:
            self.shared_event_deck = [e.copy() for e in SHARED_EVENTS]
            random.shuffle(self.shared_event_deck)
        
        if not self.role_event_decks:
            for role in RoleType:
                self.role_event_decks[role] = [e.copy() for e in ROLE_EVENTS[role]]
                random.shuffle(self.role_event_decks[role])
        
        if not self.being_deck:
            self.being_deck = [SentientBeing(b.name, b.cost, b.fu_reward, b.hui_reward, 0, b.special)
                              for b in SENTIENT_BEINGS]
            random.shuffle(self.being_deck)

# ===== 策略枚举 =====
class Strategy(Enum):
    BALANCED = "平衡型"
    SELFISH = "自私型"
    ALTRUISTIC = "利他型"
    SMART = "智能型"

# ===== 游戏模拟器 =====
class GameSimulator:
    def __init__(self, num_players: int = 4, strategies: List[Strategy] = None):
        self.num_players = num_players
        self.strategies = strategies or [Strategy.SMART] * num_players
        self.state = None
    
    def initialize_game(self):
        roles = list(RoleType)[:self.num_players]
        traditions = [Tradition.LAYMAN, Tradition.SRAVAKA, Tradition.BODHISATTVA, Tradition.LAYMAN]
        players = []
        for i, role in enumerate(roles):
            init = ROLE_INIT[role]
            tradition = traditions[i % len(traditions)]
            player = Player(role, tradition, init["wealth"], init["fu"], init["hui"])
            # 分配发愿（随机选一个）
            vows = VOWS[role]
            player.vow = random.choice(vows)
            players.append(player)
        self.state = GameState(players=players)
    
    def _get_monk_idx(self) -> Optional[int]:
        for i, p in enumerate(self.state.players):
            if p.role == RoleType.MONK:
                return i
        return None
    
    # ===== 事件阶段 =====
    def run_shared_event(self):
        """共享事件（每轮1张）"""
        if not self.state.shared_event_deck:
            return
        event = self.state.shared_event_deck.pop(0)
        effect = event.get("effect", {})
        
        if "calamity" in effect:
            self.state.calamity = max(0, self.state.calamity + effect["calamity"])
        if "wealth_all" in effect:
            for p in self.state.players:
                p.wealth = max(0, p.wealth + effect["wealth_all"])
        if "fu_all" in effect:
            for p in self.state.players:
                p.fu += effect["fu_all"]
                p.fu_from_event += effect["fu_all"]
        if "hui_all" in effect:
            for p in self.state.players:
                p.hui += effect["hui_all"]
                p.hui_from_event += effect["hui_all"]
        if "free_save" in effect:
            self.state.event_modifiers["free_save"] = True
    
    def run_role_event(self, player: Player, player_idx: int, strategy: Strategy):
        """专属事件（每人每轮1张）"""
        role = player.role
        deck = self.state.role_event_decks.get(role, [])
        if not deck:
            return
        
        event = deck.pop(0)
        
        # 纯效果事件
        if "effect" in event:
            self._apply_event_effect(player, event["effect"])
            return
        
        # 骰子判定事件
        if event.get("dice"):
            roll = roll_2d6()
            result = dice_result(roll)
            if result in ["SUCCESS", "CRIT_SUCCESS"]:
                self._apply_event_effect(player, event.get("success", {}))
            else:
                self._apply_event_effect(player, event.get("fail", {}))
            return
        
        # 选择事件
        if event.get("choice"):
            # 智能选择：根据策略决定
            if strategy == Strategy.ALTRUISTIC:
                # 利他型总是帮助
                if "help" in event:
                    self._apply_event_effect(player, event["help"])
                    player.helped_this_turn = True
                elif "ceremony" in event:
                    self._apply_event_effect(player, event.get("decline", {}))
            elif strategy == Strategy.SELFISH:
                # 自私型不帮助
                if "ignore" in event:
                    self._apply_event_effect(player, event["ignore"])
                elif "ceremony" in event:
                    self._apply_event_effect(player, event["ceremony"])
            else:
                # 智能/平衡型：根据资源情况决定
                if "help" in event:
                    help_eff = event["help"]
                    cost = abs(help_eff.get("wealth", 0))
                    if player.wealth >= cost + 2:
                        self._apply_event_effect(player, help_eff)
                        player.helped_this_turn = True
                    else:
                        self._apply_event_effect(player, event.get("ignore", {}))
                elif "ceremony" in event:
                    # 僧侣法事选择：财富紧张才做法事
                    if player.wealth < 2:
                        self._apply_event_effect(player, event["ceremony"])
                    else:
                        self._apply_event_effect(player, event.get("decline", {}))
    
    def _apply_event_effect(self, player: Player, effect: Dict):
        """应用事件效果"""
        if "wealth" in effect:
            player.wealth = max(0, player.wealth + effect["wealth"])
        if "fu" in effect:
            player.fu += effect["fu"]
            if effect["fu"] > 0:
                player.fu_from_event += effect["fu"]
        if "hui" in effect:
            player.hui += effect["hui"]
            if effect["hui"] > 0:
                player.hui_from_event += effect["hui"]
    
    # ===== 行动评估 =====
    def _evaluate_action_score(self, player: Player, action: ActionType, player_idx: int) -> float:
        """评估行动预期收益"""
        role = player.role
        fu, hui, wealth = player.fu, player.hui, player.wealth
        remaining = self.state.max_rounds - self.state.current_round
        saves_needed = self.state.save_required - self.state.saved_count
        calamity = self.state.calamity
        tradition = player.tradition
        
        # 福慧平衡需求
        fu_need = max(0, hui - fu) * 0.5
        hui_need = max(0, fu - hui) * 0.5
        
        # 传统修正
        if tradition == Tradition.SRAVAKA:
            hui_need += 1  # 声闻道偏重慧
        elif tradition == Tradition.BODHISATTVA:
            fu_need += 1  # 菩萨道偏重福
        
        # 紧急度
        calamity_urgency = max(0, (calamity - 8) / 12) * 2
        save_urgency = max(0, (saves_needed - remaining) / 3) * 2
        
        score = 0
        
        if action == ActionType.LABOR:
            if role == RoleType.MONK:
                return -10  # 僧侣不能劳作
            score = 3 * 0.3  # 财富基础价值
            if wealth < 4:
                score += 3
            if wealth < 2:
                score += 4
        
        elif action == ActionType.PRACTICE:
            base_hui = 2
            if role == RoleType.SCHOLAR:
                base_hui = 3  # 学者修行加成
            score = base_hui + hui_need
        
        elif action == ActionType.DONATE:
            if wealth < 3:
                return -5
            fu_gain = 2
            if role == RoleType.MERCHANT:
                fu_gain = 4  # 商人布施+2福
            score = fu_gain + fu_need + calamity_urgency
        
        elif action == ActionType.PROTECT:
            if wealth < 2:
                return -5
            score = 2 + fu_need + calamity_urgency * 2
        
        elif action == ActionType.SAVE:
            affordable = [b for b in self.state.sentient_area if wealth >= b.cost]
            if not affordable:
                return -5
            best = max(affordable, key=lambda b: (b.fu_reward + b.hui_reward) / b.cost)
            save_bonus = max(0, 3 - player.save_count)
            fu_gain = best.fu_reward + save_bonus
            hui_gain = best.hui_reward
            score = fu_gain + hui_gain + save_urgency * 3
            # 紧急众生优先
            urgent = [b for b in affordable if b.turns_in_area >= 1]
            if urgent:
                score += 5
        
        elif action == ActionType.TEACH:
            if role != RoleType.SCHOLAR:
                return -10
            score = 2 + fu_need + hui_need  # 讲学+1福+1慧
        
        elif action == ActionType.ALMS:
            if role != RoleType.MONK:
                return -10
            # 托钵期望值（骰子）：成功+3财+1福，失败+1财
            score = 2 * 0.3 + 0.5 + fu_need
        
        elif action == ActionType.CEREMONY:
            if role != RoleType.MONK:
                return -10
            # 法事：+4财-2福-1慧（不推荐）
            score = 4 * 0.3 - 2 - fu_need - 1 - hui_need
            if wealth < 1:
                score += 5  # 财富极度紧张时考虑
        
        elif action == ActionType.SUPPORT_MONK:
            monk_idx = self._get_monk_idx()
            if monk_idx is None or monk_idx == player_idx:
                return -10
            if wealth < 2:
                return -5
            monk = self.state.players[monk_idx]
            score = 2 + fu_need
            if monk.wealth < 2:
                score += 3  # 僧侣需要钱
        
        return score
    
    def _choose_action(self, player: Player, strategy: Strategy, player_idx: int) -> ActionType:
        """选择行动"""
        if strategy == Strategy.SELFISH:
            if player.role == RoleType.MONK:
                return ActionType.CEREMONY
            return ActionType.PRACTICE
        
        role = player.role
        if role == RoleType.MONK:
            actions = [ActionType.ALMS, ActionType.CEREMONY, ActionType.SAVE, ActionType.PROTECT, ActionType.PRACTICE]
        elif role == RoleType.SCHOLAR:
            actions = [ActionType.LABOR, ActionType.PRACTICE, ActionType.TEACH, ActionType.DONATE, ActionType.SAVE, ActionType.PROTECT, ActionType.SUPPORT_MONK]
        else:
            actions = [ActionType.LABOR, ActionType.PRACTICE, ActionType.DONATE, ActionType.SAVE, ActionType.PROTECT, ActionType.SUPPORT_MONK]
        
        scores = [(a, self._evaluate_action_score(player, a, player_idx) + random.gauss(0, 1)) for a in actions]
        best = max(scores, key=lambda x: x[1])[0]
        return best
    
    # ===== 执行行动 =====
    def _execute_action(self, player: Player, action: ActionType, player_idx: int):
        role = player.role
        
        if action == ActionType.LABOR:
            if role == RoleType.MONK:
                player.wealth += 1
                player.fu = max(0, player.fu - 1)
            else:
                player.wealth += 3
            player.labor_count += 1
        
        elif action == ActionType.PRACTICE:
            # v2.0.1: 降低修行收益，骰子只影响是否成功
            base = 2
            if role == RoleType.SCHOLAR:
                base = 3
            elif role == RoleType.MONK:
                base = 2  # 僧侣修行和普通人一样
            roll = roll_2d6()
            result = dice_result(roll)
            if result == "CRIT_SUCCESS":
                gain = base + 1
            elif result in ["SUCCESS", "FAIL"]:
                gain = base
            else:  # CRIT_FAIL
                gain = max(1, base - 1)
            player.hui += gain
            player.hui_from_practice += gain
        
        elif action == ActionType.DONATE:
            if player.wealth >= 3:
                player.wealth -= 3
                fu_gain = 2
                hui_gain = 1
                if role == RoleType.MERCHANT:
                    fu_gain = 4
                    hui_gain = 2  # 商人布施也获得更多慧（结缘中悟道）
                player.fu += fu_gain
                player.fu_from_donate += fu_gain
                player.hui += hui_gain
                player.hui_from_event += hui_gain
                self.state.calamity = max(0, self.state.calamity - 1)
                player.donate_count += 1
                player.helped_this_turn = True
        
        elif action == ActionType.PROTECT:
            if player.wealth >= 2:
                player.wealth -= 2
                player.fu += 2
                player.fu_from_protect += 2
                player.hui += 1
                self.state.calamity = max(0, self.state.calamity - 2)
                player.protect_count += 1
                player.helped_this_turn = True
        
        elif action == ActionType.SAVE:
            affordable = [b for b in self.state.sentient_area if player.wealth >= b.cost]
            if affordable:
                being = max(affordable, key=lambda b: (b.fu_reward + b.hui_reward) / b.cost)
                cost = being.cost
                if self.state.event_modifiers.get("free_save") and player.save_count == 0:
                    cost = 0
                    self.state.event_modifiers["free_save"] = False
                
                if player.wealth >= cost:
                    player.wealth -= cost
                    # v2.0.1: 更激进的递减（防止农夫独大）
                    save_bonus = max(0, 2 - player.save_count)
                    fu_gain = being.fu_reward + save_bonus
                    hui_gain = being.hui_reward
                    
                    # 角色加成
                    if role == RoleType.SCHOLAR and "学者" in being.special:
                        hui_gain += 1
                    if role == RoleType.MERCHANT and "商人" in being.special:
                        player.wealth += 2
                    
                    player.fu += fu_gain
                    player.hui += hui_gain
                    player.fu_from_save += fu_gain
                    player.hui_from_save += hui_gain
                    player.save_count += 1
                    self.state.saved_count += 1
                    self.state.sentient_area.remove(being)
                    player.helped_this_turn = True
        
        elif action == ActionType.TEACH:
            # v2.0.1: 学者讲学：自己+2福+1慧，他人+1福+1慧
            player.hui += 1
            player.hui_from_practice += 1
            player.fu += 2
            player.fu_from_event += 2
            others = [p for i, p in enumerate(self.state.players) if i != player_idx]
            if others:
                target = min(others, key=lambda p: p.fu)
                target.fu += 1
                target.hui += 1
            player.teach_count += 1
            player.helped_this_turn = True  # 讲学算帮助
        
        elif action == ActionType.ALMS:
            # 托钵：骰子判定
            roll = roll_2d6()
            result = dice_result(roll)
            if result in ["SUCCESS", "CRIT_SUCCESS"]:
                player.wealth += 3
                player.fu += 1
                player.fu_from_event += 1
            else:
                player.wealth += 1
            player.hui += 1
            player.hui_from_practice += 1
        
        elif action == ActionType.CEREMONY:
            # 法事：+4财-2福-1慧
            player.wealth += 4
            player.fu = max(0, player.fu - 2)
            player.hui = max(0, player.hui - 1)
        
        elif action == ActionType.SUPPORT_MONK:
            monk_idx = self._get_monk_idx()
            if monk_idx is not None and player.wealth >= 2:
                player.wealth -= 2
                monk = self.state.players[monk_idx]
                monk.wealth += 2
                monk.fu += 1
                player.fu += 2
                player.fu_from_donate += 2
                player.helped_this_turn = True
    
    # ===== 众生阶段 =====
    def run_sentient_phase(self):
        # 超时检查
        for being in self.state.sentient_area[:]:
            being.turns_in_area += 1
            if being.turns_in_area >= 2:
                self.state.calamity += 3
                self.state.sentient_area.remove(being)
        
        # 添加新众生
        if self.state.being_deck:
            new = self.state.being_deck.pop(0)
            self.state.sentient_area.append(new)
    
    # ===== 持续帮助 =====
    def _update_help_streak(self):
        for player in self.state.players:
            if player.helped_this_turn:
                player.help_streak += 1
                player.max_streak = max(player.max_streak, player.help_streak)
                if player.help_streak >= 3 and player.help_streak <= 4:
                    fu_bonus = 1
                    hui_bonus = 1
                    if player.role == RoleType.FARMER:
                        fu_bonus = 2  # 农夫持续帮助加成
                    player.fu += fu_bonus
                    player.hui += hui_bonus
                    player.fu_from_event += fu_bonus
                    player.hui_from_event += hui_bonus
            else:
                player.help_streak = 0
    
    # ===== 生存消耗 =====
    def _apply_survival_cost(self):
        if self.state.current_round % 2 == 0:
            for player in self.state.players:
                player.wealth -= 1
                if player.wealth < 0:
                    player.wealth = 0
                    player.fu = max(0, player.fu - 1)
                    player.hui = max(0, player.hui - 1)
                    player.starve_count += 1
    
    # ===== 发愿检查 =====
    def _check_vow(self, player: Player) -> int:
        """检查发愿是否达成，返回加分"""
        if not player.vow:
            return 0
        
        vow = player.vow
        condition = vow["condition"]
        
        # 构建评估上下文
        ctx = {
            "fu": player.fu,
            "hui": player.hui,
            "wealth": player.wealth,
            "save_count": player.save_count,
            "donate_count": player.donate_count,
            "teach_count": player.teach_count,
            "team_fu_min": min(p.fu for p in self.state.players),
        }
        
        try:
            if eval(condition, {"__builtins__": {}}, ctx):
                return vow["reward"]
            else:
                return vow["penalty"]
        except:
            return 0
    
    # ===== 结算阶段 =====
    def run_settlement_phase(self):
        self._update_help_streak()
        self._apply_survival_cost()
        
        for player in self.state.players:
            player.helped_this_turn = False
        
        self.state.event_modifiers = {}
    
    # ===== 计算得分 =====
    def calculate_score(self, player: Player) -> float:
        fu, hui = player.fu, player.hui
        base = math.sqrt(max(1, fu * hui)) * 3
        
        # 道的加分
        tradition_bonus = 0
        if player.tradition == Tradition.LAYMAN:
            if fu >= 12 and hui >= 12:
                tradition_bonus = 14
        elif player.tradition == Tradition.SRAVAKA:
            if hui >= 18 and fu >= 8:
                tradition_bonus = 15
        elif player.tradition == Tradition.BODHISATTVA:
            if fu >= 18 and hui >= 8:
                tradition_bonus = 16
        
        # 发愿加分
        vow_bonus = self._check_vow(player)
        
        return base + tradition_bonus + vow_bonus
    
    # ===== 运行游戏 =====
    def run_game(self) -> Tuple[bool, List[Dict]]:
        self.initialize_game()
        
        for round_num in range(1, self.state.max_rounds + 1):
            self.state.current_round = round_num
            
            # 共享事件
            self.run_shared_event()
            
            # 众生阶段
            self.run_sentient_phase()
            
            # 每人专属事件 + 行动
            for i, player in enumerate(self.state.players):
                strategy = self.strategies[i]
                
                # 专属事件
                self.run_role_event(player, i, strategy)
                
                # 2个行动
                for _ in range(2):
                    action = self._choose_action(player, strategy, i)
                    self._execute_action(player, action, i)
            
            # 结算
            self.run_settlement_phase()
            
            # 检查失败
            if self.state.calamity >= 20:
                break
        
        # 团队胜利检查
        team_win = (self.state.calamity <= 12 and self.state.saved_count >= self.state.save_required)
        
        # 计算个人得分
        results = []
        for i, player in enumerate(self.state.players):
            score = self.calculate_score(player) if team_win else 0
            results.append({
                "role": player.role,
                "tradition": player.tradition,
                "fu": player.fu,
                "hui": player.hui,
                "wealth": player.wealth,
                "score": score,
                "save_count": player.save_count,
                "donate_count": player.donate_count,
                "starve_count": player.starve_count,
                "max_streak": player.max_streak,
                "fu_from_save": player.fu_from_save,
                "fu_from_donate": player.fu_from_donate,
                "fu_from_event": player.fu_from_event,
                "hui_from_practice": player.hui_from_practice,
                "hui_from_event": player.hui_from_event,
                "vow_success": self._check_vow(player) > 0,
            })
        
        return team_win, results

# ===== 蒙特卡洛测试器 =====
class MonteCarloTester:
    def __init__(self, num_simulations: int = 500):
        self.num_simulations = num_simulations
    
    def run_full_test(self):
        print("=" * 80)
        print("《功德轮回》v2.0.3 完整版测试")
        print(f"模拟次数: {self.num_simulations}局")
        print("=" * 80)
        
        print("\n【v2.0 核心机制】")
        print("• 4角色：农夫/商人/学者/僧侣")
        print("• 双事件卡：共享事件+专属事件（每人每轮抽1张）")
        print("• 发愿系统：每职业3选1")
        print("• 骰子系统：2d6判定")
        print("• 道的选择：居士/声闻/菩萨")
        
        # 统计
        role_stats = {role: {"wins": 0, "scores": [], "fu": [], "hui": [], "wealth": [],
                             "save": [], "starve": [], "vow_success": 0,
                             "fu_save": [], "fu_donate": [], "fu_event": [],
                             "hui_practice": [], "hui_event": []}
                     for role in RoleType}
        team_wins = 0
        
        for _ in range(self.num_simulations):
            strategies = [Strategy.SMART] * 4
            sim = GameSimulator(4, strategies)
            team_win, results = sim.run_game()
            
            if team_win:
                team_wins += 1
                # 找出胜者
                winner_idx = max(range(len(results)), key=lambda i: results[i]["score"])
                for i, r in enumerate(results):
                    role = r["role"]
                    role_stats[role]["scores"].append(r["score"])
                    role_stats[role]["fu"].append(r["fu"])
                    role_stats[role]["hui"].append(r["hui"])
                    role_stats[role]["wealth"].append(r["wealth"])
                    role_stats[role]["save"].append(r["save_count"])
                    role_stats[role]["starve"].append(r["starve_count"])
                    role_stats[role]["fu_save"].append(r["fu_from_save"])
                    role_stats[role]["fu_donate"].append(r["fu_from_donate"])
                    role_stats[role]["fu_event"].append(r["fu_from_event"])
                    role_stats[role]["hui_practice"].append(r["hui_from_practice"])
                    role_stats[role]["hui_event"].append(r["hui_from_event"])
                    if r["vow_success"]:
                        role_stats[role]["vow_success"] += 1
                    if i == winner_idx:
                        role_stats[role]["wins"] += 1
        
        # 输出结果
        team_rate = team_wins / self.num_simulations * 100
        print(f"\n【智能型策略】团队胜率: {team_rate:.1f}%\n")
        
        win_rates = []
        for role in RoleType:
            stats = role_stats[role]
            if not stats["scores"]:
                continue
            
            win_rate = stats["wins"] / team_wins * 100 if team_wins else 0
            win_rates.append((role, win_rate))
            avg_score = sum(stats["scores"]) / len(stats["scores"])
            avg_fu = sum(stats["fu"]) / len(stats["fu"])
            avg_hui = sum(stats["hui"]) / len(stats["hui"])
            avg_wealth = sum(stats["wealth"]) / len(stats["wealth"])
            avg_save = sum(stats["save"]) / len(stats["save"])
            avg_starve = sum(stats["starve"]) / len(stats["starve"])
            vow_rate = stats["vow_success"] / team_wins * 100 if team_wins else 0
            
            print(f"  {role.value}: 胜率={win_rate:.1f}%")
            print(f"    福={avg_fu:.1f}, 慧={avg_hui:.1f}, 分={avg_score:.1f}")
            print(f"    财富={avg_wealth:.1f}, 渡化={avg_save:.1f}, 饥饿={avg_starve:.1f}")
            print(f"    发愿成功率={vow_rate:.1f}%")
            print()
        
        # 福来源分析
        print("=" * 80)
        print("福来源分析（平均值）")
        print("=" * 80)
        print(f"{'角色':<8} {'渡化':<8} {'布施':<8} {'事件':<8}")
        for role in RoleType:
            stats = role_stats[role]
            if not stats["fu_save"]:
                continue
            fs = sum(stats["fu_save"]) / len(stats["fu_save"])
            fd = sum(stats["fu_donate"]) / len(stats["fu_donate"])
            fe = sum(stats["fu_event"]) / len(stats["fu_event"])
            print(f"{role.value:<8} {fs:<8.1f} {fd:<8.1f} {fe:<8.1f}")
        
        print()
        print("=" * 80)
        print("慧来源分析（平均值）")
        print("=" * 80)
        print(f"{'角色':<8} {'修行':<8} {'事件':<8}")
        for role in RoleType:
            stats = role_stats[role]
            if not stats["hui_practice"]:
                continue
            hp = sum(stats["hui_practice"]) / len(stats["hui_practice"])
            he = sum(stats["hui_event"]) / len(stats["hui_event"])
            print(f"{role.value:<8} {hp:<8.1f} {he:<8.1f}")
        
        # 平衡性评价
        print()
        print("=" * 80)
        if win_rates:
            max_rate = max(w[1] for w in win_rates)
            min_rate = min(w[1] for w in win_rates)
            gap = max_rate - min_rate
            
            if gap < 15:
                rating = "★★★★★ 非常平衡"
            elif gap < 25:
                rating = "★★★★☆ 比较平衡"
            elif gap < 35:
                rating = "★★★☆☆ 一般"
            else:
                rating = "★★☆☆☆ 需调整"
            
            print(f"胜率差距: {gap:.1f}%")
            print(f"评价: {rating}")
            
            best = max(win_rates, key=lambda x: x[1])
            worst = min(win_rates, key=lambda x: x[1])
            print(f"\n最强角色: {best[0].value} ({best[1]:.1f}%)")
            print(f"最弱角色: {worst[0].value} ({worst[1]:.1f}%)")

if __name__ == "__main__":
    tester = MonteCarloTester(num_simulations=500)
    tester.run_full_test()
