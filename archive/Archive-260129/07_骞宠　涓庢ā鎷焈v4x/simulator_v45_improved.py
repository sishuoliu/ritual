# -*- coding: utf-8 -*-
"""
《功德轮回：众生百态》v4.5 改进版蒙特卡洛模拟器

改进内容：
1. AI策略多样化 - 根据发愿目标调整决策
2. 天灾抉择博弈 - 实现囚徒困境逻辑
3. 个人事件卡 - 实现主要事件类型效果
4. 主动技能 - 完整实现四职业技能
5. 参数回调 - 修正过激调整
6. 团队难度 - 增加劫难压力
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import json
from collections import defaultdict
import copy

class Role(Enum):
    FARMER = "农夫"
    MERCHANT = "商人"
    SCHOLAR = "学者"
    MONK = "僧侣"

class FaithState(Enum):
    SECULAR = "不皈依"
    SMALL_VEHICLE = "小乘"
    GREAT_VEHICLE = "大乘"

class Vow(Enum):
    DILIGENT_FORTUNE = "勤劳致福"
    POOR_GIRL_LAMP = "贫女一灯"
    WEALTH_MERIT = "财施功德"
    GREAT_MERCHANT = "大商人之心"
    TEACH_WISDOM = "传道授业"
    TEACHER_MODEL = "万世师表"
    ARHAT = "阿罗汉果"
    BODHISATTVA = "菩萨道"

class BodhisattvaVow(Enum):
    DIZANG = "地藏愿"
    GUANYIN = "观音愿"
    PUXIAN = "普贤愿"
    WENSHU = "文殊愿"

class AIStrategy(Enum):
    """AI策略类型"""
    VOW_FOCUSED = "发愿导向"  # 优先完成发愿条件
    TEAM_FOCUSED = "团队导向"  # 优先帮助团队
    BALANCED = "平衡型"       # 均衡发展

# ============ 配置 - 根据批判调整 ============
@dataclass
class GameConfig:
    """游戏参数配置 - v4.5修正版"""
    calamity_limit: int = 20
    calamity_win_threshold: int = 12
    save_target: int = 5
    max_rounds: int = 6
    
    # 初始资源 - 保守调整
    init_farmer: Tuple[int, int, int] = (5, 2, 2)    # 恢复原值
    init_merchant: Tuple[int, int, int] = (8, 1, 1)
    init_scholar: Tuple[int, int, int] = (3, 2, 4)   # 福+1，慧保持4
    init_monk: Tuple[int, int, int] = (0, 4, 3)      # 福+1，财保持0（主题一致）
    
    # 信仰收益
    secular_wealth_bonus: int = 4
    small_vehicle_fu_bonus: int = 1
    small_vehicle_hui_bonus: int = 1
    great_vehicle_wealth_cost: int = 2
    great_vehicle_hui_bonus: int = 1
    
    # 行动收益 - 恢复职业特色
    labor_base: int = 3
    labor_farmer_bonus: int = 1   # 恢复农夫劳作+1
    labor_secular_bonus: int = 1
    practice_base: int = 2
    practice_scholar_bonus: int = 1  # 学者修行+1（恢复）
    donate_cost: int = 2
    donate_fu_base: int = 2
    donate_merchant_bonus: int = 1  # 商人布施+1（恢复）
    
    # 发愿条件 - 温和调整
    vow_diligent_fu: int = 17      # 原15，略提高
    vow_poor_girl_fu: int = 22     # 原20→28过激，改为22
    vow_poor_girl_wealth: int = 5
    vow_wealth_merit_count: int = 3
    vow_great_merchant_fu: int = 16  # 原18，略降低
    vow_great_merchant_save: int = 2
    vow_teach_hui: int = 16        # 原18，略降低
    vow_teacher_fu: int = 12
    vow_teacher_hui: int = 18      # 原22，降低
    vow_arhat_hui: int = 18        # 原22，降低
    vow_bodhisattva_fu: int = 16   # 原18，略降低
    vow_bodhisattva_save: int = 3
    
    # 奖惩
    vow_simple_reward: int = 12
    vow_simple_penalty: int = 4
    vow_hard_reward: int = 16
    vow_hard_penalty: int = 6
    
    # 劫难 - 增加压力
    disaster_calamity: int = 4
    misfortune_calamity: int = 3   # 原2，增加
    timeout_penalty: int = 4
    calamity_per_round: int = 1
    
    # 事件权重 - 增加灾难概率
    disaster_weight: float = 0.45  # 原0.4
    misfortune_weight: float = 0.25  # 原0.2
    blessing_weight: float = 0.30  # 原0.4，减少

@dataclass
class Player:
    role: Role
    faith: FaithState = FaithState.SECULAR
    wealth: int = 0
    fu: int = 0
    hui: int = 0
    vow: Optional[Vow] = None
    bodhisattva_vow: Optional[BodhisattvaVow] = None
    strategy: AIStrategy = AIStrategy.BALANCED
    
    # 追踪
    donate_count: int = 0
    save_count: int = 0
    help_count: int = 0
    skill_uses: int = 2  # 主动技能剩余次数
    puxian_supply: int = 0
    guanyin_helped: set = field(default_factory=set)
    
    # 统计
    wealth_from_labor: int = 0
    fu_from_vow: int = 0
    fu_from_donate: int = 0
    fu_from_save: int = 0
    fu_from_events: int = 0
    fu_from_skill: int = 0
    hui_from_practice: int = 0
    hui_from_vow: int = 0
    hui_from_events: int = 0
    
    def init_resources(self, config: GameConfig):
        if self.role == Role.FARMER:
            self.wealth, self.fu, self.hui = config.init_farmer
        elif self.role == Role.MERCHANT:
            self.wealth, self.fu, self.hui = config.init_merchant
        elif self.role == Role.SCHOLAR:
            self.wealth, self.fu, self.hui = config.init_scholar
        elif self.role == Role.MONK:
            self.wealth, self.fu, self.hui = config.init_monk
    
    def apply_faith(self, faith: FaithState, config: GameConfig, is_start: bool = True):
        if faith == FaithState.SECULAR:
            if is_start:
                self.wealth += config.secular_wealth_bonus
        elif faith == FaithState.SMALL_VEHICLE:
            if is_start:
                self.fu += config.small_vehicle_fu_bonus
                self.hui += config.small_vehicle_hui_bonus
            else:
                self.fu += 1
        self.faith = faith
    
    def apply_great_vehicle(self, config: GameConfig, is_start: bool = True):
        if is_start:
            self.wealth -= config.great_vehicle_wealth_cost
            self.hui += config.great_vehicle_hui_bonus
        else:
            self.wealth -= 3
        self.faith = FaithState.GREAT_VEHICLE
    
    def get_score(self) -> int:
        total = self.fu + self.hui
        if total < 10: base = 10
        elif total < 15: base = 15
        elif total < 20: base = 25
        elif total < 25: base = 35
        elif total < 30: base = 45
        elif total < 35: base = 55
        else: base = 65
        if self.fu < 5 or self.hui < 5:
            base = base // 2
        return base
    
    def check_vow(self, config: GameConfig) -> Tuple[int, int]:
        reward, penalty = 0, 0
        
        if self.vow == Vow.DILIGENT_FORTUNE:
            if self.fu >= config.vow_diligent_fu:
                reward += config.vow_simple_reward
            else:
                penalty += config.vow_simple_penalty
        elif self.vow == Vow.POOR_GIRL_LAMP:
            if self.fu >= config.vow_poor_girl_fu and self.wealth <= config.vow_poor_girl_wealth:
                reward += config.vow_hard_reward + 2
            else:
                penalty += config.vow_hard_penalty
        elif self.vow == Vow.WEALTH_MERIT:
            if self.donate_count >= config.vow_wealth_merit_count:
                reward += config.vow_simple_reward
            else:
                penalty += config.vow_simple_penalty
        elif self.vow == Vow.GREAT_MERCHANT:
            if self.fu >= config.vow_great_merchant_fu and self.save_count >= config.vow_great_merchant_save:
                reward += config.vow_hard_reward
            else:
                penalty += config.vow_hard_penalty
        elif self.vow == Vow.TEACH_WISDOM:
            if self.hui >= config.vow_teach_hui:
                reward += config.vow_simple_reward
            else:
                penalty += config.vow_simple_penalty
        elif self.vow == Vow.TEACHER_MODEL:
            if self.fu >= config.vow_teacher_fu and self.hui >= config.vow_teacher_hui:
                reward += config.vow_hard_reward
            else:
                penalty += config.vow_hard_penalty
        elif self.vow == Vow.ARHAT:
            if self.hui >= config.vow_arhat_hui:
                reward += config.vow_simple_reward
            else:
                penalty += config.vow_simple_penalty
        elif self.vow == Vow.BODHISATTVA:
            if self.fu >= config.vow_bodhisattva_fu and self.save_count >= config.vow_bodhisattva_save:
                reward += config.vow_hard_reward + 2
            else:
                penalty += config.vow_hard_penalty + 2
        
        return reward, penalty
    
    def needs_fu(self, config: GameConfig) -> bool:
        """检查是否需要福来完成发愿"""
        if self.vow == Vow.DILIGENT_FORTUNE:
            return self.fu < config.vow_diligent_fu
        elif self.vow == Vow.POOR_GIRL_LAMP:
            return self.fu < config.vow_poor_girl_fu
        elif self.vow == Vow.GREAT_MERCHANT:
            return self.fu < config.vow_great_merchant_fu
        elif self.vow == Vow.TEACHER_MODEL:
            return self.fu < config.vow_teacher_fu
        elif self.vow == Vow.BODHISATTVA:
            return self.fu < config.vow_bodhisattva_fu
        return False
    
    def needs_hui(self, config: GameConfig) -> bool:
        """检查是否需要慧来完成发愿"""
        if self.vow == Vow.TEACH_WISDOM:
            return self.hui < config.vow_teach_hui
        elif self.vow == Vow.TEACHER_MODEL:
            return self.hui < config.vow_teacher_hui
        elif self.vow == Vow.ARHAT:
            return self.hui < config.vow_arhat_hui
        return False
    
    def needs_donate(self, config: GameConfig) -> bool:
        """检查是否需要布施来完成发愿"""
        if self.vow == Vow.WEALTH_MERIT:
            return self.donate_count < config.vow_wealth_merit_count
        return False
    
    def needs_save(self, config: GameConfig) -> bool:
        """检查是否需要渡化来完成发愿"""
        if self.vow == Vow.GREAT_MERCHANT:
            return self.save_count < config.vow_great_merchant_save
        elif self.vow == Vow.BODHISATTVA:
            return self.save_count < config.vow_bodhisattva_save
        return False

@dataclass
class Being:
    name: str
    cost: int
    fu_reward: int
    hui_reward: int
    stay_rounds: int = 0

# ============ 个人事件卡 ============
class PersonalEvent:
    """个人事件卡"""
    def __init__(self, name: str, event_type: str, exclusive_role: Optional[Role] = None):
        self.name = name
        self.event_type = event_type  # "story", "choice", "dice", "interaction"
        self.exclusive_role = exclusive_role

PERSONAL_EVENTS = [
    # 经典故事类
    PersonalEvent("贫女一灯", "story"),
    PersonalEvent("割肉喂鹰", "story"),
    PersonalEvent("舍身饲虎", "story"),
    PersonalEvent("目连救母", "story"),
    # 职业专属
    PersonalEvent("丰年收成", "exclusive", Role.FARMER),
    PersonalEvent("歉收之年", "exclusive", Role.FARMER),
    PersonalEvent("大宗交易", "exclusive", Role.MERCHANT),
    PersonalEvent("海上风暴", "exclusive", Role.MERCHANT),
    PersonalEvent("弟子求教", "exclusive", Role.SCHOLAR),
    PersonalEvent("焚书之劫", "exclusive", Role.SCHOLAR),
    PersonalEvent("皇帝供养", "exclusive", Role.MONK),
    PersonalEvent("破戒边缘", "exclusive", Role.MONK),
    # 抉择类
    PersonalEvent("一念之间", "choice"),
    PersonalEvent("神秘访客", "choice"),
    PersonalEvent("拾金不昧", "choice"),
    # 骰子机遇类
    PersonalEvent("发现伏藏", "dice"),
    PersonalEvent("遇见高人", "dice"),
    PersonalEvent("命运之轮", "dice"),
    # 互动类
    PersonalEvent("求助他人", "interaction"),
    PersonalEvent("共修因缘", "interaction"),
]

class GameSimulator:
    def __init__(self, config: GameConfig = None):
        self.config = config or GameConfig()
        self.beings_pool = self._create_beings()
        self.events_pool = PERSONAL_EVENTS.copy()
        
    def _create_beings(self) -> List[Being]:
        return [
            Being("饥民", 2, 2, 1), Being("病者", 2, 2, 1),
            Being("孤儿", 3, 3, 1), Being("寡妇", 3, 2, 2),
            Being("落魄书生", 3, 1, 3), Being("迷途商贾", 4, 2, 2),
            Being("悔过恶人", 4, 4, 1), Being("垂死老者", 5, 3, 3),
            Being("被弃婴儿", 2, 3, 0), Being("绝望猎人", 4, 2, 2),
        ]
    
    def create_game(self) -> Dict:
        roles = list(Role)
        random.shuffle(roles)
        players = []
        
        for role in roles[:4]:
            player = Player(role=role)
            player.init_resources(self.config)
            
            # 根据角色选择合适的信仰状态
            if role == Role.MONK:
                # 僧侣固定皈依
                faith_choice = random.choices(
                    [FaithState.SMALL_VEHICLE, FaithState.GREAT_VEHICLE],
                    weights=[0.6, 0.4]
                )[0]
            else:
                faith_choice = random.choices(
                    [FaithState.SECULAR, FaithState.SMALL_VEHICLE, FaithState.GREAT_VEHICLE],
                    weights=[0.3, 0.4, 0.3]
                )[0]
            
            if faith_choice == FaithState.SECULAR:
                player.apply_faith(FaithState.SECULAR, self.config, is_start=True)
            elif faith_choice == FaithState.SMALL_VEHICLE:
                player.apply_faith(FaithState.SMALL_VEHICLE, self.config, is_start=True)
            else:
                player.apply_faith(FaithState.SMALL_VEHICLE, self.config, is_start=True)
                player.apply_great_vehicle(self.config, is_start=True)
            
            # 智能选择发愿
            player.vow = self._choose_vow_smart(role, player.faith)
            
            # 选择AI策略
            player.strategy = random.choice(list(AIStrategy))
            
            if player.faith == FaithState.GREAT_VEHICLE:
                player.bodhisattva_vow = random.choice(list(BodhisattvaVow))
            
            players.append(player)
        
        beings_deck = [copy.copy(b) for b in self.beings_pool]
        random.shuffle(beings_deck)
        
        events_deck = self.events_pool.copy()
        random.shuffle(events_deck)
        
        return {
            "players": players,
            "current_round": 1,
            "calamity": 0,
            "saved_count": 0,
            "active_beings": [beings_deck.pop(), beings_deck.pop()],
            "beings_deck": beings_deck,
            "events_deck": events_deck,
            "events_log": [],
            "stats": defaultdict(int)
        }
    
    def _choose_vow_smart(self, role: Role, faith: FaithState) -> Vow:
        """智能选择发愿 - 根据信仰状态调整"""
        vow_map = {
            Role.FARMER: [Vow.DILIGENT_FORTUNE, Vow.POOR_GIRL_LAMP],
            Role.MERCHANT: [Vow.WEALTH_MERIT, Vow.GREAT_MERCHANT],
            Role.SCHOLAR: [Vow.TEACH_WISDOM, Vow.TEACHER_MODEL],
            Role.MONK: [Vow.ARHAT, Vow.BODHISATTVA],
        }
        
        # 大乘玩家更倾向困难发愿（高风险高回报）
        if faith == FaithState.GREAT_VEHICLE:
            weights = [0.3, 0.7]  # 更倾向困难
        elif faith == FaithState.SMALL_VEHICLE:
            weights = [0.5, 0.5]  # 平衡
        else:
            weights = [0.7, 0.3]  # 倾向简单
        
        return random.choices(vow_map[role], weights=weights)[0]
    
    def vow_reward_phase(self, game: Dict):
        """发愿奖励阶段"""
        for p in game["players"]:
            if p.vow in [Vow.DILIGENT_FORTUNE, Vow.POOR_GIRL_LAMP, Vow.BODHISATTVA]:
                p.fu += 1
                p.fu_from_vow += 1
            elif p.vow == Vow.WEALTH_MERIT:
                p.wealth += 1
            elif p.vow in [Vow.GREAT_MERCHANT, Vow.TEACH_WISDOM, Vow.TEACHER_MODEL, Vow.ARHAT]:
                p.hui += 1
                p.hui_from_vow += 1
    
    def collective_event_phase(self, game: Dict):
        """集体事件阶段 - 实现囚徒困境"""
        event_type = random.choices(
            ["disaster", "misfortune", "blessing"],
            weights=[self.config.disaster_weight, self.config.misfortune_weight, self.config.blessing_weight]
        )[0]
        
        if event_type == "disaster":
            self._disaster_event_with_dilemma(game)
            game["stats"]["disaster_count"] += 1
        elif event_type == "misfortune":
            self._misfortune_event(game)
            game["stats"]["misfortune_count"] += 1
        else:
            self._blessing_event(game)
            game["stats"]["blessing_count"] += 1
    
    def _disaster_event_with_dilemma(self, game: Dict):
        """天灾抉择 - 实现囚徒困境博弈"""
        event_name = random.choice(["旱魃肆虐", "洪水滔天", "瘟疫流行", "蝗灾蔽日"])
        game["events_log"].append(f"R{game['current_round']}: {event_name}")
        
        # 每个玩家根据策略和状态决定
        choices = []
        for p in game["players"]:
            choice = self._decide_dilemma_choice(p, game)
            choices.append(choice)
        
        a_count = choices.count("A")
        b_count = choices.count("B")
        
        # 基础劫难增加
        base_calamity = self.config.disaster_calamity
        
        # 囚徒困境核心逻辑
        if a_count == 4:
            # 全员合作：劫难最小化，全员小奖励
            game["calamity"] += base_calamity - 2
            for p in game["players"]:
                p.fu += 1
                p.fu_from_events += 1
                p.wealth -= 1
        elif a_count == 0:
            # 全员背叛：劫难爆炸
            game["calamity"] += base_calamity + 3
            for p in game["players"]:
                p.hui += 1
                p.hui_from_events += 1
        else:
            # 混合情况：合作者牺牲，背叛者获利
            game["calamity"] += base_calamity + b_count - a_count
            for i, p in enumerate(game["players"]):
                if choices[i] == "A":
                    # 合作者：牺牲财富，获得福
                    p.wealth -= 2
                    p.fu += 2 if a_count >= 2 else 1
                    p.fu_from_events += 2 if a_count >= 2 else 1
                else:
                    # 背叛者：保全财富，但少获福
                    p.wealth -= 1
                    if b_count >= 3:  # 背叛者太多，惩罚
                        p.fu -= 1
    
    def _decide_dilemma_choice(self, player: Player, game: Dict) -> str:
        """决定囚徒困境选择 - 基于策略、信仰、状态"""
        
        # 基础合作倾向
        coop_prob = 0.5
        
        # 策略影响
        if player.strategy == AIStrategy.TEAM_FOCUSED:
            coop_prob += 0.2
        elif player.strategy == AIStrategy.VOW_FOCUSED:
            # 发愿导向者：需要福则合作
            if player.needs_fu(self.config):
                coop_prob += 0.15
            else:
                coop_prob -= 0.1
        
        # 信仰影响
        if player.faith == FaithState.GREAT_VEHICLE:
            coop_prob += 0.25  # 大乘行者更倾向利他
        elif player.faith == FaithState.SMALL_VEHICLE:
            coop_prob += 0.1
        elif player.faith == FaithState.SECULAR:
            coop_prob -= 0.1  # 不皈依者更务实
        
        # 劫难状态影响
        if game["calamity"] >= 12:
            coop_prob += 0.2  # 危机时刻更团结
        elif game["calamity"] <= 5:
            coop_prob -= 0.1  # 安全时更自利
        
        # 财富状态影响
        if player.wealth <= 2:
            coop_prob -= 0.15  # 穷困时保守
        elif player.wealth >= 8:
            coop_prob += 0.1  # 富裕时慷慨
        
        # 回合影响
        if game["current_round"] >= 5:
            coop_prob += 0.1  # 后期更合作
        
        coop_prob = max(0.1, min(0.9, coop_prob))  # 限制在10%-90%
        
        return "A" if random.random() < coop_prob else "B"
    
    def _misfortune_event(self, game: Dict):
        """人祸事件"""
        event_name = random.choice(["苛政如虎", "战火将至", "盗匪横行"])
        game["events_log"].append(f"R{game['current_round']}: {event_name}")
        game["calamity"] += self.config.misfortune_calamity
        
        # 随机影响
        for p in game["players"]:
            if random.random() > 0.5:
                p.wealth -= 1
    
    def _blessing_event(self, game: Dict):
        """福报事件"""
        event_name = random.choice(["风调雨顺", "国泰民安", "浴佛盛会", "盂兰盆节", "高僧讲经", "舍利现世"])
        game["events_log"].append(f"R{game['current_round']}: {event_name}")
        
        if event_name == "风调雨顺":
            for p in game["players"]:
                p.wealth += 1
        elif event_name == "国泰民安":
            game["calamity"] = max(0, game["calamity"] - 1)
        elif event_name == "浴佛盛会":
            for p in game["players"]:
                p.fu += 1
                p.fu_from_events += 1
                if p.faith != FaithState.SECULAR:
                    p.fu += 1
                    p.fu_from_events += 1
        elif event_name == "盂兰盆节":
            for p in game["players"]:
                p.fu += 1
                p.fu_from_events += 1
        elif event_name == "高僧讲经":
            for p in game["players"]:
                p.hui += 1
                p.hui_from_events += 1
                if p.faith != FaithState.SECULAR:
                    p.hui += 1
                    p.hui_from_events += 1
        elif event_name == "舍利现世":
            game["calamity"] = max(0, game["calamity"] - 1)
            for p in game["players"]:
                p.fu += 1
                p.fu_from_events += 1
    
    def personal_event_phase(self, game: Dict):
        """个人事件阶段 - 实现事件效果"""
        if not game["events_deck"]:
            return
        
        for p in game["players"]:
            if not game["events_deck"]:
                break
            
            event = game["events_deck"].pop()
            self._execute_personal_event(p, event, game)
    
    def _execute_personal_event(self, player: Player, event: PersonalEvent, game: Dict):
        """执行个人事件"""
        
        if event.event_type == "story":
            # 经典故事类：通常有福或慧奖励
            if event.name == "贫女一灯":
                if player.wealth >= 2:
                    player.wealth -= 2
                    player.fu += 3
                    player.fu_from_events += 3
                else:
                    player.fu += 1
                    player.fu_from_events += 1
            elif event.name == "割肉喂鹰":
                player.fu += 2
                player.fu_from_events += 2
                player.wealth -= 1
            elif event.name in ["舍身饲虎", "目连救母"]:
                player.fu += 2
                player.fu_from_events += 2
        
        elif event.event_type == "exclusive":
            # 职业专属事件
            is_exclusive = (event.exclusive_role == player.role)
            
            if event.name == "丰年收成":
                player.wealth += 3 if is_exclusive else 1
            elif event.name == "歉收之年":
                player.wealth -= 2 if is_exclusive else 1
                player.fu += 1
                player.fu_from_events += 1
            elif event.name == "大宗交易":
                if is_exclusive:
                    player.wealth += 4
                else:
                    player.wealth += 1
            elif event.name == "海上风暴":
                if is_exclusive:
                    if random.random() > 0.5:
                        player.wealth += 3
                    else:
                        player.wealth -= 2
                else:
                    player.wealth -= 1
            elif event.name == "弟子求教":
                if is_exclusive:
                    player.hui += 2
                    player.fu += 1
                    player.hui_from_events += 2
                    player.fu_from_events += 1
                else:
                    player.hui += 1
                    player.hui_from_events += 1
            elif event.name == "焚书之劫":
                if is_exclusive:
                    player.hui -= 1
                    player.fu += 2
                    player.fu_from_events += 2
                else:
                    player.hui -= 1
            elif event.name == "皇帝供养":
                if is_exclusive:
                    player.wealth += 3
                    player.fu += 2
                    player.fu_from_events += 2
                else:
                    player.fu += 1
                    player.fu_from_events += 1
            elif event.name == "破戒边缘":
                if is_exclusive:
                    # 抉择：保戒（失财）或破戒（失福）
                    if player.wealth >= 2:
                        player.wealth -= 2
                        player.fu += 1
                        player.fu_from_events += 1
                    else:
                        player.fu -= 2
        
        elif event.event_type == "choice":
            # 抉择类：玩家选择
            if event.name == "一念之间":
                # 选择：得慧失福 或 得福失慧
                if player.needs_hui(self.config):
                    player.hui += 2
                    player.fu -= 1
                    player.hui_from_events += 2
                else:
                    player.fu += 2
                    player.hui -= 1
                    player.fu_from_events += 2
            elif event.name == "神秘访客":
                # 选择：接待（花财富得福）或拒绝（无效果）
                if player.wealth >= 2:
                    player.wealth -= 2
                    player.fu += 3
                    player.fu_from_events += 3
            elif event.name == "拾金不昧":
                # 选择：归还（+2福）或私吞（+3财富,-1福）
                if player.needs_fu(self.config) or player.faith != FaithState.SECULAR:
                    player.fu += 2
                    player.fu_from_events += 2
                else:
                    player.wealth += 3
                    player.fu -= 1
        
        elif event.event_type == "dice":
            # 骰子机遇类
            roll = random.randint(1, 6)
            if event.name == "发现伏藏":
                if roll >= 5:
                    player.hui += 3
                    player.fu += 2
                    player.hui_from_events += 3
                    player.fu_from_events += 2
                elif roll >= 3:
                    player.hui += 1
                    player.hui_from_events += 1
                # 1-2无效果
            elif event.name == "遇见高人":
                if roll >= 4:
                    player.hui += 2
                    player.hui_from_events += 2
                else:
                    player.fu += 1
                    player.fu_from_events += 1
            elif event.name == "命运之轮":
                if roll >= 5:
                    player.fu += 2
                    player.hui += 2
                    player.fu_from_events += 2
                    player.hui_from_events += 2
                elif roll <= 2:
                    player.wealth -= 1
                    player.fu -= 1
        
        elif event.event_type == "interaction":
            # 互动类：涉及其他玩家
            others = [p for p in game["players"] if p != player]
            if event.name == "求助他人":
                # 随机获得帮助或被拒绝
                if others and random.random() > 0.3:
                    helper = random.choice(others)
                    if helper.wealth >= 1:
                        helper.wealth -= 1
                        player.wealth += 1
                        helper.fu += 1
                        helper.fu_from_events += 1
            elif event.name == "共修因缘":
                # 与他人共同获益
                if others:
                    partner = random.choice(others)
                    player.hui += 1
                    partner.hui += 1
                    player.hui_from_events += 1
                    partner.hui_from_events += 1
    
    def beings_phase(self, game: Dict):
        """众生阶段"""
        for being in game["active_beings"]:
            being.stay_rounds += 1
        
        timeout_beings = [b for b in game["active_beings"] if b.stay_rounds >= 2]
        for b in timeout_beings:
            game["calamity"] += self.config.timeout_penalty
            game["stats"]["timeout_count"] += 1
            game["active_beings"].remove(b)
        
        if game["beings_deck"]:
            game["active_beings"].append(game["beings_deck"].pop())
    
    def action_phase(self, game: Dict):
        """行动阶段 - 含主动技能"""
        for p in game["players"]:
            actions_left = 2
            
            while actions_left > 0:
                action = self._decide_action_smart(p, game, actions_left)
                
                if action == "labor":
                    self._do_labor(p)
                elif action == "practice":
                    self._do_practice(p)
                elif action == "donate":
                    self._do_donate(p, game)
                elif action == "save":
                    self._do_save(p, game)
                elif action == "protect":
                    self._do_protect(p, game)
                elif action == "skill":
                    self._do_skill(p, game)
                else:
                    break
                
                actions_left -= 1
    
    def _decide_action_smart(self, player: Player, game: Dict, actions_left: int) -> str:
        """智能决策行动 - 基于策略和发愿目标"""
        
        # 紧急情况：劫难过高
        if game["calamity"] >= 15 and player.wealth >= 2:
            return "protect"
        
        # 发愿导向策略
        if player.strategy == AIStrategy.VOW_FOCUSED:
            # 需要布施次数
            if player.needs_donate(self.config) and player.wealth >= 2:
                return "donate"
            # 需要渡化次数
            if player.needs_save(self.config) and player.hui >= 5 and game["active_beings"]:
                affordable = [b for b in game["active_beings"] if self._can_afford_being(player, b)]
                if affordable:
                    return "save"
            # 需要慧
            if player.needs_hui(self.config):
                return "practice"
            # 需要福（通过布施或渡化）
            if player.needs_fu(self.config):
                if player.wealth >= 2:
                    return "donate"
                elif player.hui >= 5 and game["active_beings"]:
                    affordable = [b for b in game["active_beings"] if self._can_afford_being(player, b)]
                    if affordable:
                        return "save"
        
        # 团队导向策略
        elif player.strategy == AIStrategy.TEAM_FOCUSED:
            # 优先渡化和护法
            if game["calamity"] >= 10 and player.wealth >= 2:
                return "protect"
            if player.hui >= 5 and game["active_beings"]:
                affordable = [b for b in game["active_beings"] if self._can_afford_being(player, b)]
                if affordable:
                    return "save"
            if player.wealth >= 2:
                return "donate"
        
        # 考虑使用主动技能
        if player.skill_uses > 0 and actions_left == 2 and random.random() > 0.6:
            if self._can_use_skill(player, game):
                return "skill"
        
        # 默认逻辑
        if player.hui >= 5 and game["active_beings"]:
            affordable = [b for b in game["active_beings"] if self._can_afford_being(player, b)]
            if affordable:
                return "save"
        
        if player.hui < 5:
            return "practice"
        
        if player.wealth >= 2 and random.random() > 0.4:
            return "donate"
        
        if player.wealth < 4:
            return "labor"
        
        return "practice"
    
    def _can_use_skill(self, player: Player, game: Dict) -> bool:
        """检查是否可以使用主动技能"""
        if player.skill_uses <= 0:
            return False
        
        if player.role == Role.FARMER:
            return player.wealth >= 2
        elif player.role == Role.MERCHANT:
            return player.wealth >= 3
        elif player.role == Role.SCHOLAR:
            return True
        elif player.role == Role.MONK:
            return player.fu >= 1
        return False
    
    def _do_skill(self, player: Player, game: Dict):
        """执行主动技能"""
        if player.skill_uses <= 0:
            return
        
        others = [p for p in game["players"] if p != player]
        if not others:
            return
        
        if player.role == Role.FARMER:
            # 分享收成：给他人2财富，双方各+1福
            if player.wealth >= 2:
                target = min(others, key=lambda x: x.wealth)  # 给最穷的
                player.wealth -= 2
                target.wealth += 2
                player.fu += 1
                target.fu += 1
                player.fu_from_skill += 1
                player.skill_uses -= 1
        
        elif player.role == Role.MERCHANT:
            # 慷慨宴请：-3财富，全体+1福，劫难-1
            if player.wealth >= 3:
                player.wealth -= 3
                for p in game["players"]:
                    p.fu += 1
                    if p == player:
                        p.fu_from_skill += 1
                    else:
                        p.fu_from_events += 1
                game["calamity"] = max(0, game["calamity"] - 1)
                player.skill_uses -= 1
        
        elif player.role == Role.SCHOLAR:
            # 讲学传道：2名玩家各+1慧，自己+1福
            targets = random.sample(others, min(2, len(others)))
            for t in targets:
                t.hui += 1
                t.hui_from_events += 1
            player.fu += 1
            player.fu_from_skill += 1
            player.skill_uses -= 1
        
        elif player.role == Role.MONK:
            # 加持祈福：转移自己的福给他人
            if player.fu >= 1:
                target = min(others, key=lambda x: x.fu)  # 给福最低的
                transfer = min(2, player.fu - 1)  # 保留至少1福
                if transfer > 0:
                    player.fu -= transfer
                    target.fu += transfer + 1  # 额外+1（祝福效果）
                    target.fu_from_events += transfer + 1
                    player.skill_uses -= 1
    
    def _can_afford_being(self, player: Player, being: Being) -> bool:
        cost = being.cost
        if player.role == Role.MERCHANT:
            cost += 1
        elif player.role in [Role.SCHOLAR, Role.MONK]:
            cost -= 1
        if player.faith == FaithState.SECULAR:
            cost -= 1
        cost = max(1, cost)
        
        if player.role == Role.MONK:
            return player.wealth + min(2, player.fu) >= cost
        return player.wealth >= cost
    
    def _do_labor(self, player: Player):
        gain = self.config.labor_base
        if player.role == Role.FARMER:
            gain += self.config.labor_farmer_bonus
        if player.faith == FaithState.SECULAR:
            gain += self.config.labor_secular_bonus
        player.wealth += gain
        player.wealth_from_labor += gain
    
    def _do_practice(self, player: Player):
        gain = self.config.practice_base
        if player.role == Role.SCHOLAR:
            gain += self.config.practice_scholar_bonus
        if player.bodhisattva_vow == BodhisattvaVow.WENSHU:
            gain -= 1
        player.hui += gain
        player.hui_from_practice += gain
    
    def _do_donate(self, player: Player, game: Dict):
        if player.wealth < self.config.donate_cost:
            return
        
        player.wealth -= self.config.donate_cost
        fu_gain = self.config.donate_fu_base
        
        if player.role == Role.MERCHANT:
            fu_gain += self.config.donate_merchant_bonus
        if player.faith != FaithState.SECULAR:
            fu_gain += 1
        if game["calamity"] >= 15:
            fu_gain += 1
        
        if player.bodhisattva_vow == BodhisattvaVow.GUANYIN:
            others = [p for p in game["players"] if p != player]
            if others:
                poorest = min(others, key=lambda x: x.wealth)
                poorest.wealth += 2
                player.guanyin_helped.add(id(poorest))
        else:
            game["calamity"] = max(0, game["calamity"] - 1)
        
        player.fu += fu_gain
        player.fu_from_donate += fu_gain
        player.donate_count += 1
        player.help_count += 1
    
    def _do_save(self, player: Player, game: Dict):
        if player.hui < 5 or not game["active_beings"]:
            return
        
        affordable = [b for b in game["active_beings"] if self._can_afford_being(player, b)]
        if not affordable:
            return
        
        being = min(affordable, key=lambda x: x.cost)
        cost = being.cost
        
        if player.role == Role.MERCHANT:
            cost += 1
        elif player.role == Role.SCHOLAR:
            cost -= 1
            player.hui -= 1
        elif player.role == Role.MONK:
            cost -= 1
        
        if player.faith == FaithState.SECULAR:
            cost -= 1
        cost = max(1, cost)
        
        if player.role == Role.MONK and player.wealth < cost:
            fu_used = min(2, cost - player.wealth)
            player.fu -= fu_used
            player.wealth -= (cost - fu_used)
        else:
            player.wealth -= cost
        
        player.fu += being.fu_reward
        player.hui += being.hui_reward
        player.fu_from_save += being.fu_reward
        
        if player.faith != FaithState.SECULAR:
            player.fu += 1
            player.fu_from_save += 1
        
        if player.role == Role.MERCHANT and player.save_count == 0:
            player.wealth += 2
        
        game["active_beings"].remove(being)
        game["saved_count"] += 1
        player.save_count += 1
        player.help_count += 1
    
    def _do_protect(self, player: Player, game: Dict):
        if player.wealth < 2:
            return
        player.wealth -= 2
        player.fu += 1
        game["calamity"] = max(0, game["calamity"] - 2)
        player.help_count += 1
    
    def settlement_phase(self, game: Dict):
        """结算阶段"""
        game["calamity"] += self.config.calamity_per_round
        
        if game["current_round"] % 2 == 0:
            for p in game["players"]:
                if p.wealth >= 1:
                    p.wealth -= 1
                else:
                    p.fu -= 1
        
        for p in game["players"]:
            if p.bodhisattva_vow == BodhisattvaVow.PUXIAN and p.wealth >= 1:
                p.wealth -= 1
                p.puxian_supply += 1
        
        for p in game["players"]:
            if p.help_count >= 4:
                p.fu += 2
                p.help_count = 0
    
    def check_game_end(self, game: Dict) -> Tuple[bool, bool]:
        if game["calamity"] >= self.config.calamity_limit:
            return True, False
        if game["current_round"] >= self.config.max_rounds:
            team_win = (game["calamity"] <= self.config.calamity_win_threshold and 
                       game["saved_count"] >= self.config.save_target)
            return True, team_win
        return False, False
    
    def run_game(self) -> Dict:
        game = self.create_game()
        
        for round_num in range(1, self.config.max_rounds + 1):
            game["current_round"] = round_num
            
            self.vow_reward_phase(game)
            self.collective_event_phase(game)
            
            # 个人事件阶段（仅奇数回合）
            if round_num % 2 == 1:
                self.personal_event_phase(game)
            
            self.beings_phase(game)
            self.action_phase(game)
            self.settlement_phase(game)
            
            ended, _ = self.check_game_end(game)
            if ended:
                break
        
        _, team_win = self.check_game_end(game)
        
        results = []
        for p in game["players"]:
            base_score = p.get_score()
            vow_reward, vow_penalty = p.check_vow(self.config)
            
            bodhi_reward, bodhi_penalty = 0, 0
            if p.bodhisattva_vow:
                if p.bodhisattva_vow == BodhisattvaVow.DIZANG:
                    base_score -= 10
                    if team_win:
                        bodhi_reward += 15
                elif p.bodhisattva_vow == BodhisattvaVow.GUANYIN:
                    if len(p.guanyin_helped) >= 3:
                        bodhi_reward += 12
                    else:
                        bodhi_penalty += 4
                elif p.bodhisattva_vow == BodhisattvaVow.PUXIAN:
                    if p.puxian_supply >= 5:
                        bodhi_reward += 10
                    else:
                        bodhi_penalty += 6
                elif p.bodhisattva_vow == BodhisattvaVow.WENSHU:
                    high_hui = sum(1 for op in game["players"] if op != p and op.hui >= 15)
                    if high_hui >= 2:
                        bodhi_reward += 14
                    else:
                        bodhi_penalty += 5
            
            final_score = base_score + vow_reward - vow_penalty + bodhi_reward - bodhi_penalty
            if not team_win:
                final_score = 0
            
            results.append({
                "role": p.role.value,
                "faith": p.faith.value,
                "vow": p.vow.value if p.vow else None,
                "strategy": p.strategy.value,
                "fu": p.fu, "hui": p.hui, "wealth": p.wealth,
                "base_score": base_score,
                "vow_bonus": vow_reward - vow_penalty,
                "final_score": final_score,
                "save_count": p.save_count,
                "donate_count": p.donate_count,
                "fu_from_vow": p.fu_from_vow,
                "fu_from_donate": p.fu_from_donate,
                "fu_from_save": p.fu_from_save,
                "fu_from_events": p.fu_from_events,
                "fu_from_skill": p.fu_from_skill,
                "hui_from_practice": p.hui_from_practice,
                "hui_from_vow": p.hui_from_vow,
                "hui_from_events": p.hui_from_events,
            })
        
        winner = max(results, key=lambda x: x["final_score"]) if team_win else None
        
        return {
            "team_win": team_win,
            "calamity": game["calamity"],
            "saved_count": game["saved_count"],
            "players": results,
            "winner": winner["role"] if winner else None,
            "stats": dict(game["stats"])
        }
    
    def run_simulation(self, num_games: int = 2000) -> Dict:
        team_wins = 0
        calamity_failures = 0
        save_failures = 0
        
        role_wins = defaultdict(int)
        role_scores = defaultdict(list)
        faith_wins = defaultdict(int)
        strategy_wins = defaultdict(int)
        vow_success = defaultdict(lambda: {"success": 0, "total": 0})
        
        role_fu_sources = defaultdict(lambda: defaultdict(float))
        role_hui_sources = defaultdict(lambda: defaultdict(float))
        role_counts = defaultdict(int)
        
        combo_wins = defaultdict(int)
        combo_total = defaultdict(int)
        
        total_stats = defaultdict(int)
        
        for _ in range(num_games):
            result = self.run_game()
            
            if result["team_win"]:
                team_wins += 1
                if result["winner"]:
                    role_wins[result["winner"]] += 1
            else:
                if result["calamity"] >= 20:
                    calamity_failures += 1
                else:
                    save_failures += 1
            
            for k, v in result["stats"].items():
                total_stats[k] += v
            
            for p in result["players"]:
                role_scores[p["role"]].append(p["final_score"])
                role_counts[p["role"]] += 1
                
                role_fu_sources[p["role"]]["vow"] += p["fu_from_vow"]
                role_fu_sources[p["role"]]["donate"] += p["fu_from_donate"]
                role_fu_sources[p["role"]]["save"] += p["fu_from_save"]
                role_fu_sources[p["role"]]["events"] += p["fu_from_events"]
                role_fu_sources[p["role"]]["skill"] += p["fu_from_skill"]
                
                role_hui_sources[p["role"]]["practice"] += p["hui_from_practice"]
                role_hui_sources[p["role"]]["vow"] += p["hui_from_vow"]
                role_hui_sources[p["role"]]["events"] += p["hui_from_events"]
                
                if result["team_win"] and p["role"] == result["winner"]:
                    faith_wins[p["faith"]] += 1
                    strategy_wins[p["strategy"]] += 1
                
                if p["vow"]:
                    vow_success[p["vow"]]["total"] += 1
                    if p["vow_bonus"] > 0:
                        vow_success[p["vow"]]["success"] += 1
                
                combo = f"{p['role']}+{p['faith']}"
                combo_total[combo] += 1
                if result["team_win"] and p["role"] == result["winner"]:
                    combo_wins[combo] += 1
        
        for role in role_fu_sources:
            c = role_counts[role]
            for k in role_fu_sources[role]:
                role_fu_sources[role][k] /= c
        
        for role in role_hui_sources:
            c = role_counts[role]
            for k in role_hui_sources[role]:
                role_hui_sources[role][k] /= c
        
        return {
            "total_games": num_games,
            "team_win_rate": team_wins / num_games * 100,
            "calamity_failure_rate": calamity_failures / num_games * 100,
            "save_failure_rate": save_failures / num_games * 100,
            "role_win_rates": {k: v / team_wins * 100 if team_wins > 0 else 0 for k, v in role_wins.items()},
            "role_avg_scores": {k: sum(v) / len(v) if v else 0 for k, v in role_scores.items()},
            "faith_win_rates": {k: v / team_wins * 100 if team_wins > 0 else 0 for k, v in faith_wins.items()},
            "strategy_win_rates": {k: v / team_wins * 100 if team_wins > 0 else 0 for k, v in strategy_wins.items()},
            "vow_success_rates": {k: v["success"] / v["total"] * 100 if v["total"] > 0 else 0 for k, v in vow_success.items()},
            "role_fu_sources": {k: dict(v) for k, v in role_fu_sources.items()},
            "role_hui_sources": {k: dict(v) for k, v in role_hui_sources.items()},
            "combo_win_rates": {k: combo_wins[k] / combo_total[k] * 100 if combo_total[k] > 0 else 0 for k in combo_total},
            "event_stats": {k: v / num_games for k, v in total_stats.items()},
        }

def print_report(name: str, results: Dict):
    print(f"\n{'='*65}")
    print(f"配置: {name}")
    print(f"{'='*65}")
    print(f"团队胜率: {results['team_win_rate']:.1f}%")
    print(f"  劫难爆表失败: {results['calamity_failure_rate']:.1f}%")
    print(f"  渡化不足失败: {results['save_failure_rate']:.1f}%")
    print()
    
    print("职业胜率:")
    for role in ["农夫", "商人", "学者", "僧侣"]:
        rate = results["role_win_rates"].get(role, 0)
        score = results["role_avg_scores"].get(role, 0)
        bar = "#" * int(rate / 2)
        print(f"  {role}: {rate:5.1f}% (平均{score:.1f}) {bar}")
    
    print("\n信仰胜率:")
    for faith in ["不皈依", "小乘", "大乘"]:
        rate = results["faith_win_rates"].get(faith, 0)
        print(f"  {faith}: {rate:5.1f}%")
    
    print("\nAI策略胜率:")
    for strat in ["发愿导向", "团队导向", "平衡型"]:
        rate = results["strategy_win_rates"].get(strat, 0)
        print(f"  {strat}: {rate:5.1f}%")
    
    print("\n发愿达成率:")
    for vow, rate in sorted(results["vow_success_rates"].items(), key=lambda x: x[1], reverse=True):
        bar = "#" * int(rate / 5)
        print(f"  {vow}: {rate:5.1f}% {bar}")
    
    print("\n福来源 (每局平均):")
    print(f"  {'职业':<6} {'发愿':>5} {'布施':>5} {'渡化':>5} {'事件':>5} {'技能':>5} {'总计':>5}")
    for role in ["农夫", "商人", "学者", "僧侣"]:
        if role in results["role_fu_sources"]:
            s = results["role_fu_sources"][role]
            total = sum(s.values())
            print(f"  {role:<6} {s.get('vow',0):>5.1f} {s.get('donate',0):>5.1f} {s.get('save',0):>5.1f} {s.get('events',0):>5.1f} {s.get('skill',0):>5.1f} {total:>5.1f}")
    
    print("\n事件统计 (每局平均):")
    for k, v in results.get("event_stats", {}).items():
        print(f"  {k}: {v:.2f}")

def run_iteration(name: str, config: GameConfig, num_games: int = 2000) -> Dict:
    sim = GameSimulator(config)
    results = sim.run_simulation(num_games)
    print_report(name, results)
    return results

def main():
    print("=" * 65)
    print("《功德轮回》v4.5 改进版平衡测试")
    print("=" * 65)
    print("\n改进内容:")
    print("  1. AI策略多样化（发愿导向/团队导向/平衡型）")
    print("  2. 天灾抉择博弈（囚徒困境逻辑）")
    print("  3. 个人事件完整实现（20种事件）")
    print("  4. 主动技能完整实现（4职业技能）")
    print("  5. 温和参数调整（避免矫枉过正）")
    
    # 基线测试
    config_base = GameConfig()
    results_base = run_iteration("v4.5基线", config_base, 3000)
    
    # 分析不平衡
    win_rates = results_base["role_win_rates"]
    max_role = max(win_rates, key=win_rates.get)
    min_role = min(win_rates, key=lambda x: win_rates[x] if win_rates[x] > 0 else 999)
    imbalance = win_rates[max_role] - win_rates.get(min_role, 0)
    
    print(f"\n[分析] 最强职业: {max_role}({win_rates[max_role]:.1f}%), 最弱职业: {min_role}({win_rates.get(min_role,0):.1f}%)")
    print(f"[分析] 胜率差距: {imbalance:.1f}%")
    
    # 根据结果进行调整
    if imbalance > 15:
        print("\n[调整] 胜率差距过大，进行针对性调整...")
        
        # 动态调整
        config_adj = GameConfig()
        
        if max_role == "农夫":
            config_adj.vow_diligent_fu = 18
            print("  - 农夫发愿条件提高")
        elif max_role == "商人":
            config_adj.donate_merchant_bonus = 0
            print("  - 商人布施奖励降低")
        
        if min_role == "学者":
            config_adj.practice_scholar_bonus = 2
            config_adj.vow_teach_hui = 15
            print("  - 学者修行奖励提高，发愿条件降低")
        elif min_role == "僧侣":
            config_adj.init_monk = (1, 4, 3)
            config_adj.vow_arhat_hui = 16
            print("  - 僧侣初始资源提高，发愿条件降低")
        
        results_adj = run_iteration("v4.5调整版", config_adj, 3000)
    
    # 团队胜率调整
    if results_base["team_win_rate"] > 85:
        print("\n[调整] 团队胜率过高，增加难度...")
        config_hard = GameConfig(
            disaster_calamity=5,
            misfortune_calamity=4,
            disaster_weight=0.5,
            blessing_weight=0.25
        )
        results_hard = run_iteration("v4.5困难版", config_hard, 3000)
    elif results_base["team_win_rate"] < 60:
        print("\n[调整] 团队胜率过低，降低难度...")
        config_easy = GameConfig(
            disaster_calamity=3,
            misfortune_calamity=2,
            disaster_weight=0.35,
            blessing_weight=0.45
        )
        results_easy = run_iteration("v4.5简单版", config_easy, 3000)
    
    # 保存结果
    with open("balance_v45_improved.json", "w", encoding="utf-8") as f:
        json.dump({
            "base": results_base,
        }, f, ensure_ascii=False, indent=2, default=str)
    
    print("\n" + "=" * 65)
    print("测试完成，结果已保存到 balance_v45_improved.json")
    print("=" * 65)

if __name__ == "__main__":
    main()
