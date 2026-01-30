# -*- coding: utf-8 -*-
"""
《功德轮回》v5.3 全面平衡模拟器
包含所有机制：皈依时机、大乘舍离、菩萨行愿能力、行持约束等
"""

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import json

# ============== 枚举定义 ==============

class Role(Enum):
    FARMER = "农夫"
    MERCHANT = "商人"
    SCHOLAR = "学者"
    MONK = "僧侣"

class FaithState(Enum):
    SECULAR = "不皈依"
    REFUGE = "皈依"
    MAHAYANA = "大乘"

class SacrificeType(Enum):
    WEALTH = "舍资施众"      # 资-4, 布施额外劫难-1
    MERIT = "舍功德迴向"     # 功德-3, 渡化额外功德+1
    WISDOM = "舍慧度众"      # 慧-3, 帮助行动额外慧+1

class BodhisattvaVow(Enum):
    KSITIGARBHA = "地藏愿"   # 代受业报, 劫难≤8得+20
    AVALOKITESVARA = "观音愿" # 闻声救苦, 帮助≥5得+14
    SAMANTABHADRA = "普贤愿"  # 广修供养, 布施≥4且渡化≥6得+16
    MANJUSRI = "文殊愿"       # 智慧加持, 协助渡化≥2得+14

class Vow(Enum):
    # 农夫
    DILIGENT = "勤劳致功德"      # 简单, 功德≥18
    POOR_GIRL = "贫女一灯"       # 困难, 功德≥22且资≤5
    # 商人
    CHARITY = "资施功德"         # 简单, 布施≥3
    GREAT_MERCHANT = "大商人之心" # 困难, 功德≥18且渡化≥2
    # 学者
    TEACHING = "传道授业"        # 简单, 慧≥18
    MASTER = "万世师表"          # 困难, 功德≥12且慧≥18
    # 僧侣
    ARHAT = "阿罗汉果"           # 简单, 慧≥16
    BODHISATTVA = "菩萨道"       # 困难, 功德≥8且渡化≥1

class ActionType(Enum):
    LABOR = "劳作"
    PRACTICE = "修行"
    DONATE = "布施"
    SAVE = "渡化"
    PROTECT = "护法"

class EventType(Enum):
    DISASTER = "天灾"
    MISFORTUNE = "人祸"
    BLESSING = "功德"

# ============== 配置 ==============

@dataclass
class GameConfig:
    """游戏配置参数"""
    # 初始资源 (资粮, 功德, 慧)
    init_farmer: Tuple[int, int, int] = (4, 2, 2)
    init_merchant: Tuple[int, int, int] = (8, 2, 1)
    init_scholar: Tuple[int, int, int] = (4, 2, 5)
    init_monk: Tuple[int, int, int] = (1, 6, 5)
    
    # 不皈依奖励 (v5.5增强)
    secular_init_wealth: int = 5  # 4→5
    secular_labor_bonus: int = 1
    secular_save_cost_reduce: int = 1
    secular_practice_bonus: int = 1  # v5.5新增：不皈依修行+1慧
    
    # 皈依时机效果 (功德, 慧)
    refuge_round1: Tuple[int, int] = (1, 2)
    refuge_round23: Tuple[int, int] = (2, 1)
    refuge_round45: Tuple[int, int] = (3, 0)
    refuge_round6: Tuple[int, int] = (4, -1)
    
    # 皈依持续效果
    refuge_merit_per_round: int = 1
    refuge_futian_bonus: int = 1
    
    # 大乘舍离代价
    sacrifice_wealth: int = 4
    sacrifice_merit: int = 3
    sacrifice_wisdom: int = 3
    
    # 大乘舍离永久加成 (v5.3调整)
    sacrifice_wealth_donate_calamity: int = 1
    sacrifice_merit_save_merit: int = 1
    sacrifice_wisdom_help_hui: int = 0  # 1→0 舍慧太强，改为每2次帮助+1慧
    
    # 劫难调整 v5.6: 增加压力让护法有意义
    disaster_base_calamity_adj: int = 6  # 5→6 恢复压力
    misfortune_base_calamity_adj: int = 5  # 4→5 恢复压力
    
    # 行动效果
    labor_base: int = 3
    labor_farmer_bonus: int = 1
    practice_base: int = 2
    practice_scholar_bonus: int = 1
    donate_cost: int = 2
    donate_merit: int = 1
    donate_calamity: int = 1
    donate_merchant_bonus: int = 2
    protect_cost: int = 2
    protect_merit: int = 3  # v5.5: 2→3 (增强吸引力)
    protect_calamity: int = 3
    protect_crisis_bonus: int = 1  # v5.5: 劫难>=8时额外功德
    protect_crisis_threshold: int = 8  # v5.5: 10→8 (更易触发)
    protect_team_save_bonus: int = 1  # v5.6新增: 护法后本回合队友渡化+1功德
    
    # 渡化
    save_hui_requirement: int = 5
    merchant_economic_save_multiplier: int = 2  # v5.4: 商人经济渡化成本倍数
    save_monk_cost_reduce: int = 1
    
    # 众生成本
    being_costs: List[int] = field(default_factory=lambda: [3, 3, 4, 4, 4, 5, 5, 6, 3, 5])
    being_merit_rewards: List[int] = field(default_factory=lambda: [2, 2, 3, 2, 1, 2, 4, 3, 3, 2])
    being_hui_rewards: List[int] = field(default_factory=lambda: [1, 1, 1, 2, 3, 2, 1, 3, 0, 2])
    being_is_futian: List[bool] = field(default_factory=lambda: [False, False, True, False, True, False, False, True, False, False])
    
    # 事件权重
    disaster_weight: float = 0.50
    misfortune_weight: float = 0.25
    blessing_weight: float = 0.25
    
    # 劫难值 (基础版)
    disaster_base_calamity: int = 6
    misfortune_base_calamity: int = 5
    timeout_penalty: int = 5
    
    # 人间炼狱模式 (可选开启)
    hell_mode: bool = False
    hell_disaster_calamity: int = 9   # 人间炼狱事件劫难 (FINAL)
    hell_disaster_weight: float = 0.62  # 灾难权重 (FINAL)
    hell_protect_bonus: int = 1      # 护法令额外减劫难
    
    # 发愿条件 (v5.3 final)
    # 目标：简单愿~70%，困难愿~40%，菩萨愿~10%
    
    # === 简单发愿 (目标70%) ===
    vow_diligent_merit: int = 15      # 勤劳致功德 62.8%→略加难
    vow_charity_donate: int = 7       # 资施功德 91.2%→加难 5→7
    vow_teaching_hui: int = 19        # 传道授业 92.0%→加难 16→19
    vow_arhat_hui: int = 13           # 阿罗汉果 70.8%→合适
    
    # === 困难发愿 (目标40%) ===
    vow_poor_girl_merit: int = 16     # 贫女一灯 24.6%→放宽 18→16
    vow_poor_girl_wealth: int = 10    # 放宽 8→10
    vow_great_merchant_merit: int = 32  # 大商人之心 68.7%→加难 28→32
    vow_great_merchant_save: int = 0
    vow_master_merit: int = 14        # 万世师表 55.6%→加难 12→14
    vow_master_hui: int = 19          # 18→19
    vow_bodhisattva_merit: int = 22   # 菩萨道 70.8%→加难 20→22
    vow_bodhisattva_save: int = 3     # 2→3
    
    # === 菩萨愿条件 (v5.5 final) ===
    # 目标达成率：15-25%（困难但可达成，有成就感）
    bvow_ksitigarbha_calamity: int = 4   # 地藏愿：劫难≤4 且 主动承受≥2
    bvow_ksitigarbha_absorb: int = 2     # 需真正承受
    bvow_avalokitesvara_help: int = 7    # 观音愿：帮助≥7
    bvow_samantabhadra_donate: int = 6   # 普贤愿：布施≥6
    bvow_samantabhadra_save: int = 6     # 团队渡化≥6
    bvow_manjusri_assist: int = 3        # 文殊愿：协助渡化≥3
    
    # 发愿分数 (成功分, 失败分)
    vow_scores: dict = field(default_factory=lambda: {
        # 简单发愿：中等奖励，中等惩罚
        "勤劳致功德": (10, -4),
        "资施功德": (10, -4),
        "传道授业": (10, -4),
        "阿罗汉果": (10, -4),
        # 困难发愿：高奖励，中等惩罚
        "贫女一灯": (18, -6),
        "大商人之心": (18, -6),
        "万世师表": (16, -6),
        "菩萨道": (16, -6),
    })
    # 菩萨愿分数：极高奖励，低惩罚（鼓励挑战）
    bvow_scores: dict = field(default_factory=lambda: {
        "地藏愿": (25, -4),        # 最难，最高奖励
        "观音愿": (22, -4),
        "普贤愿": (22, -4),
        "文殊愿": (22, -4),
    })
    
    # 胜利条件
    max_calamity: int = 20
    win_calamity: int = 12
    win_save: int = 5
    total_rounds: int = 6

# ============== 玩家状态 ==============

@dataclass
class Player:
    role: Role
    wealth: int = 0
    merit: int = 0
    hui: int = 0
    faith: FaithState = FaithState.SECULAR
    refuge_round: int = 0  # 皈依的回合
    sacrifice: Optional[SacrificeType] = None
    vow: Optional[Vow] = None
    bodhisattva_vow: Optional[BodhisattvaVow] = None
    
    # 行动统计
    labor_count: int = 0
    practice_count: int = 0
    donate_count: int = 0
    save_count: int = 0
    protect_count: int = 0
    help_count: int = 0  # 布施+渡化+护法（每回合重置）
    
    # 职业特性使用统计
    farmer_share_used: int = 0      # 农夫分享收成次数
    merchant_first_save: bool = False  # 商人首次渡化+2资
    merchant_feast_used: int = 0    # 商人宴请次数
    scholar_redraw_used: bool = False  # 学者重抽事件
    scholar_skill_used: int = 0     # v5.4: 学者讲学传道使用次数
    monk_merit_substitute: int = 0  # 僧侣功德代资次数
    
    # v5.4新增统计
    ksitigarbha_absorb_count: int = 0  # 地藏愿主动承受次数
    hero_marks: int = 0                # 英雄标记数量
    
    # 其他统计
    assist_save_count: int = 0
    helped_players: set = field(default_factory=set)
    rounds_without_help: int = 0
    mahayana_penalty: int = 0

# ============== 游戏状态 ==============

@dataclass
class GameState:
    config: GameConfig
    players: List[Player]
    calamity: int = 0
    total_saves: int = 0
    current_round: int = 1
    beings_in_play: List[int] = field(default_factory=list)  # 众生卡索引
    being_timers: List[int] = field(default_factory=list)    # 众生计时器
    protect_blessing_active: bool = False  # v5.6: 护法祝福激活（本回合队友渡化+1功德）

# ============== AI决策 ==============

class AIDecision:
    """简化的AI决策逻辑"""
    
    @staticmethod
    def choose_faith(player: Player, state: GameState) -> Tuple[FaithState, Optional[int], Optional[SacrificeType]]:
        """选择信仰路线: (信仰状态, 皈依回合, 舍离类型)"""
        role = player.role
        round_num = state.current_round
        
        # 僧侣固定皈依
        if role == Role.MONK:
            # 50%概率发大乘
            if random.random() < 0.5:
                sacrifice = random.choice(list(SacrificeType))
                return (FaithState.MAHAYANA, 1, sacrifice)
            return (FaithState.REFUGE, 1, None)
        
        # 其他职业按策略选择
        r = random.random()
        if r < 0.3:  # 30% 不皈依
            return (FaithState.SECULAR, 0, None)
        elif r < 0.7:  # 40% 皈依
            refuge_round = random.choice([1, 1, 2, 3])  # 偏向早皈依
            return (FaithState.REFUGE, refuge_round, None)
        else:  # 30% 大乘
            refuge_round = 1
            sacrifice = random.choice(list(SacrificeType))
            return (FaithState.MAHAYANA, refuge_round, sacrifice)
    
    @staticmethod
    def choose_vow(player: Player) -> Vow:
        """选择发愿"""
        role = player.role
        vows = {
            Role.FARMER: [Vow.DILIGENT, Vow.POOR_GIRL],
            Role.MERCHANT: [Vow.CHARITY, Vow.GREAT_MERCHANT],
            Role.SCHOLAR: [Vow.TEACHING, Vow.MASTER],
            Role.MONK: [Vow.ARHAT, Vow.BODHISATTVA],
        }
        # 70%选简单，30%选困难
        if random.random() < 0.7:
            return vows[role][0]
        return vows[role][1]
    
    @staticmethod
    def choose_bodhisattva_vow(player: Player) -> BodhisattvaVow:
        """选择菩萨愿"""
        return random.choice(list(BodhisattvaVow))
    
    @staticmethod
    def choose_action(player: Player, state: GameState, actions_left: int) -> ActionType:
        """选择行动 - 职业差异化决策"""
        config = state.config
        role = player.role
        
        # 大乘玩家必须每回合帮助
        if player.faith == FaithState.MAHAYANA and player.help_count == 0 and actions_left == 1:
            if player.wealth >= config.donate_cost:
                return ActionType.DONATE
            elif player.hui >= config.save_hui_requirement and state.beings_in_play:
                return ActionType.SAVE
            elif player.wealth >= config.protect_cost:
                return ActionType.PROTECT
        
        urgency = state.calamity / config.max_calamity
        
        # ============ 职业特化行为 ============
        
        # 农夫：偏好劳作积累资粮，后期爆发渡化
        if role == Role.FARMER:
            if state.current_round <= 3:
                # 前期积累
                if random.random() < 0.6:
                    return ActionType.LABOR
            else:
                # 后期渡化
                if state.beings_in_play and player.hui >= config.save_hui_requirement:
                    cost = config.being_costs[state.beings_in_play[0]]
                    if player.wealth >= cost and random.random() < 0.5:
                        return ActionType.SAVE
        
        # 商人：偏好布施积累功德，v5.5增加经济渡化倾向
        elif role == Role.MERCHANT:
            # v5.5: 商人经济渡化 - 用双倍资粮代替慧
            if state.beings_in_play and player.wealth >= 8:  # 资粮充足时尝试经济渡化
                being_idx = state.beings_in_play[0]
                double_cost = config.being_costs[being_idx] * 2  # 双倍成本
                if player.wealth >= double_cost and random.random() < 0.3:
                    return ActionType.SAVE  # 模拟经济渡化
            
            if player.wealth >= config.donate_cost:
                if random.random() < 0.5:  # 商人更爱布施
                    return ActionType.DONATE
            if player.wealth < 4:  # 资粮不足时劳作
                if random.random() < 0.6:
                    return ActionType.LABOR
        
        # 学者：偏好修行积累慧
        elif role == Role.SCHOLAR:
            if player.hui < 15:  # 慧不够时优先修行
                if random.random() < 0.5:
                    return ActionType.PRACTICE
            # 慧够了可以渡化
            if state.beings_in_play and player.hui >= config.save_hui_requirement:
                cost = config.being_costs[state.beings_in_play[0]] - 1  # 学者成本-1
                if player.wealth >= cost and random.random() < 0.4:
                    return ActionType.SAVE
        
        # 僧侣：偏好渡化（成本-1，可用功德代资）
        elif role == Role.MONK:
            if state.beings_in_play and player.hui >= config.save_hui_requirement:
                being_idx = state.beings_in_play[0]
                cost = config.being_costs[being_idx] - config.save_monk_cost_reduce
                # 可以用功德代替部分资粮
                effective_wealth = player.wealth + min(2, player.merit)
                if effective_wealth >= cost and random.random() < 0.6:
                    return ActionType.SAVE
            # 僧侣资粮少，需要劳作补充
            if player.wealth < 2:
                if random.random() < 0.5:
                    return ActionType.LABOR
        
        # ============ 通用逻辑 ============
        
        # v5.6: 护法决策 - 人间炼狱模式更积极
        if player.wealth >= config.protect_cost:
            if config.hell_mode:
                # 人间炼狱模式：大幅提高护法概率
                protect_prob = 0.35 + urgency * 0.5  # 基础35%，高劫难时85%
                if urgency > 0.25:  # 劫难>3时就开始护法
                    if random.random() < protect_prob:
                        return ActionType.PROTECT
            elif urgency > 0.35:
                # 基础版：劫难较高时护法
                protect_prob = 0.25 + urgency * 0.4
                if random.random() < protect_prob:
                    return ActionType.PROTECT
        
        # 有众生且能渡化
        if state.beings_in_play and player.hui >= config.save_hui_requirement:
            cost = config.being_costs[state.beings_in_play[0]]
            if role == Role.MONK:
                cost -= config.save_monk_cost_reduce
            if player.faith == FaithState.SECULAR:
                cost -= config.secular_save_cost_reduce
            if player.wealth >= cost:
                if random.random() < 0.3:
                    return ActionType.SAVE
        
        # 布施
        if player.wealth >= config.donate_cost:
            if random.random() < 0.25:
                return ActionType.DONATE
        
        # 修行
        if random.random() < 0.3:
            return ActionType.PRACTICE
        
        # 默认劳作
        return ActionType.LABOR

# ============== 游戏引擎 ==============

class GameEngine:
    def __init__(self, config: GameConfig):
        self.config = config
        self.stats = defaultdict(lambda: defaultdict(int))
    
    def init_players(self) -> List[Player]:
        """初始化玩家"""
        roles = list(Role)
        players = []
        
        init_resources = {
            Role.FARMER: self.config.init_farmer,
            Role.MERCHANT: self.config.init_merchant,
            Role.SCHOLAR: self.config.init_scholar,
            Role.MONK: self.config.init_monk,
        }
        
        for role in roles:
            w, m, h = init_resources[role]
            player = Player(role=role, wealth=w, merit=m, hui=h)
            players.append(player)
        
        return players
    
    def apply_faith_choice(self, player: Player, state: GameState):
        """应用信仰选择"""
        faith, refuge_round, sacrifice = AIDecision.choose_faith(player, state)
        player.faith = faith
        player.refuge_round = refuge_round if refuge_round else 0
        player.sacrifice = sacrifice
        
        # 不皈依开局奖励
        if faith == FaithState.SECULAR:
            player.wealth += self.config.secular_init_wealth
        
        # 皈依开局奖励（第1回合皈依）
        elif refuge_round == 1:
            m, h = self.config.refuge_round1
            player.merit += m
            player.hui += h
            
            # 大乘舍离
            if faith == FaithState.MAHAYANA and sacrifice:
                if sacrifice == SacrificeType.WEALTH:
                    player.wealth -= self.config.sacrifice_wealth
                elif sacrifice == SacrificeType.MERIT:
                    player.merit -= self.config.sacrifice_merit
                elif sacrifice == SacrificeType.WISDOM:
                    player.hui -= self.config.sacrifice_wisdom
                
                # 确保不为负
                player.wealth = max(0, player.wealth)
                player.merit = max(0, player.merit)
                player.hui = max(0, player.hui)
    
    def check_mid_game_refuge(self, player: Player, state: GameState):
        """检查中途皈依"""
        if player.faith != FaithState.SECULAR:
            return
        if player.refuge_round == 0:
            return
        if state.current_round != player.refuge_round:
            return
        
        # 应用皈依效果
        round_num = state.current_round
        if round_num == 1:
            m, h = self.config.refuge_round1
        elif round_num <= 3:
            m, h = self.config.refuge_round23
        elif round_num <= 5:
            m, h = self.config.refuge_round45
        else:
            m, h = self.config.refuge_round6
        
        player.merit += m
        player.hui += h
        player.faith = FaithState.REFUGE
        
        # 失去不皈依效果（已经获得的资粮保留）
    
    def execute_action(self, player: Player, action: ActionType, state: GameState):
        """执行行动"""
        config = self.config
        
        if action == ActionType.LABOR:
            gain = config.labor_base
            if player.role == Role.FARMER:
                gain += config.labor_farmer_bonus
            if player.faith == FaithState.SECULAR:
                gain += config.secular_labor_bonus
            player.wealth += gain
            player.labor_count += 1
        
        elif action == ActionType.PRACTICE:
            gain = config.practice_base
            if player.role == Role.SCHOLAR:
                gain += config.practice_scholar_bonus
            # v5.5: 不皈依修行加成
            if player.faith == FaithState.SECULAR:
                gain += config.secular_practice_bonus
            player.hui += gain
            player.practice_count += 1
        
        elif action == ActionType.DONATE:
            if player.wealth >= config.donate_cost:
                player.wealth -= config.donate_cost
                merit_gain = config.donate_merit
                if player.role == Role.MERCHANT:
                    merit_gain += config.donate_merchant_bonus
                player.merit += merit_gain
                state.calamity -= config.donate_calamity
                
                # 大乘舍资加成
                if player.sacrifice == SacrificeType.WEALTH:
                    state.calamity -= config.sacrifice_wealth_donate_calamity
                
                player.donate_count += 1
                player.help_count += 1
        
        elif action == ActionType.SAVE:
            if state.beings_in_play and player.hui >= config.save_hui_requirement:
                being_idx = state.beings_in_play[0]
                cost = config.being_costs[being_idx]
                
                if player.role == Role.MONK:
                    cost -= config.save_monk_cost_reduce
                if player.faith == FaithState.SECULAR:
                    cost -= config.secular_save_cost_reduce
                
                cost = max(1, cost)
                
                # 僧侣可用功德代资（最多2点）
                merit_substitute = 0
                actual_wealth_cost = cost
                if player.role == Role.MONK and player.wealth < cost:
                    merit_substitute = min(2, cost - player.wealth, player.merit)
                    actual_wealth_cost = cost - merit_substitute
                
                if player.wealth >= actual_wealth_cost:
                    player.wealth -= actual_wealth_cost
                    if merit_substitute > 0:
                        player.merit -= merit_substitute
                        player.monk_merit_substitute += merit_substitute
                    
                    merit_gain = config.being_merit_rewards[being_idx]
                    hui_gain = config.being_hui_rewards[being_idx]
                    
                    # 福田加成
                    if config.being_is_futian[being_idx] and player.faith in [FaithState.REFUGE, FaithState.MAHAYANA]:
                        merit_gain += config.refuge_futian_bonus
                    
                    # 大乘舍功德加成
                    if player.sacrifice == SacrificeType.MERIT:
                        merit_gain += config.sacrifice_merit_save_merit
                    
                    # v5.6: 护法祝福加成
                    if state.protect_blessing_active:
                        merit_gain += config.protect_team_save_bonus
                    
                    # 商人首次渡化+2资
                    if player.role == Role.MERCHANT and not player.merchant_first_save:
                        player.wealth += 2
                        player.merchant_first_save = True
                    
                    player.merit += merit_gain
                    player.hui += hui_gain
                    player.save_count += 1
                    player.help_count += 1
                    state.total_saves += 1
                    
                    # 移除众生
                    state.beings_in_play.pop(0)
                    state.being_timers.pop(0)
        
        elif action == ActionType.PROTECT:
            if player.wealth >= config.protect_cost:
                player.wealth -= config.protect_cost
                merit_gain = config.protect_merit
                # v5.5: 危机加成
                if state.calamity >= config.protect_crisis_threshold:
                    merit_gain += config.protect_crisis_bonus
                player.merit += merit_gain
                state.calamity -= config.protect_calamity
                player.protect_count += 1
                player.help_count += 1
                # v5.6新增: 护法祝福 - 本回合队友渡化+1功德
                state.protect_blessing_active = True
        
        # 大乘舍慧加成
        if player.sacrifice == SacrificeType.WISDOM and action in [ActionType.DONATE, ActionType.SAVE, ActionType.PROTECT]:
            player.hui += config.sacrifice_wisdom_help_hui
        
        state.calamity = max(0, state.calamity)
    
    def process_collective_event(self, state: GameState):
        """处理集体事件"""
        r = random.random()
        
        # 人间炼狱模式使用更高的灾难权重
        disaster_weight = self.config.hell_disaster_weight if self.config.hell_mode else self.config.disaster_weight
        misfortune_weight = self.config.misfortune_weight * (0.5 if self.config.hell_mode else 1.0)
        
        if r < disaster_weight:
            # 人间炼狱模式使用更高劫难
            if self.config.hell_mode:
                base = self.config.hell_disaster_calamity
                # 护法令：本回合护法次数减劫难（激励护法）
                # 注意：这里简化为随机模拟护法效果
            else:
                base = getattr(self.config, 'disaster_base_calamity_adj', self.config.disaster_base_calamity)
            state.calamity += base
            # 简化：假设玩家合作降低一些（人间炼狱模式合作效果减半）
            coop_rate = 0.3 if self.config.hell_mode else 0.5
            coop = sum(1 for p in state.players if random.random() < coop_rate)
            state.calamity -= coop
        elif r < disaster_weight + misfortune_weight:
            if self.config.hell_mode:
                base = self.config.hell_disaster_calamity - 3  # 人祸略低
            else:
                base = getattr(self.config, 'misfortune_base_calamity_adj', self.config.misfortune_base_calamity)
            state.calamity += base
        else:
            # 功德事件（人间炼狱模式较少出现）
            for p in state.players:
                p.merit += 1
                if p.faith in [FaithState.REFUGE, FaithState.MAHAYANA]:
                    p.merit += 1  # 皈依者额外效果
        
        state.calamity = max(0, state.calamity)
    
    def process_beings_phase(self, state: GameState):
        """众生阶段"""
        # 计时器+1
        for i in range(len(state.being_timers)):
            state.being_timers[i] += 1
        
        # 检查超时
        to_remove = []
        for i, timer in enumerate(state.being_timers):
            if timer >= 2:
                state.calamity += self.config.timeout_penalty
                to_remove.append(i)
        
        for i in reversed(to_remove):
            state.beings_in_play.pop(i)
            state.being_timers.pop(i)
        
        # 补充众生
        while len(state.beings_in_play) < 2:
            new_being = random.randint(0, len(self.config.being_costs) - 1)
            state.beings_in_play.append(new_being)
            state.being_timers.append(0)
    
    def process_round_end(self, state: GameState):
        """回合结束处理"""
        # 皈依者每回合+1功德
        for p in state.players:
            if p.faith in [FaithState.REFUGE, FaithState.MAHAYANA]:
                p.merit += self.config.refuge_merit_per_round
        
        # 大乘行持检查
        for p in state.players:
            if p.faith == FaithState.MAHAYANA:
                if p.help_count == 0:
                    p.merit -= 1
                    p.mahayana_penalty += 1
                p.help_count = 0  # 重置
        
        # 偶数回合消耗
        if state.current_round % 2 == 0:
            for p in state.players:
                # 不皈依者仅4、6回合消耗
                if p.faith == FaithState.SECULAR and state.current_round == 2:
                    continue
                if p.wealth > 0:
                    p.wealth -= 1
                else:
                    p.merit -= 1
        
        # v5.6: 重置护法祝福
        state.protect_blessing_active = False
    
    def check_vow(self, player: Player, state: GameState) -> bool:
        """检查发愿是否达成"""
        vow = player.vow
        config = self.config
        
        if vow == Vow.DILIGENT:
            return player.merit >= config.vow_diligent_merit
        elif vow == Vow.POOR_GIRL:
            return player.merit >= config.vow_poor_girl_merit and player.wealth <= config.vow_poor_girl_wealth
        elif vow == Vow.CHARITY:
            return player.donate_count >= config.vow_charity_donate
        elif vow == Vow.GREAT_MERCHANT:
            return player.merit >= config.vow_great_merchant_merit and player.save_count >= config.vow_great_merchant_save
        elif vow == Vow.TEACHING:
            # v5.4: 需使用过主动技能
            return player.hui >= config.vow_teaching_hui and player.scholar_skill_used >= 1
        elif vow == Vow.MASTER:
            return player.merit >= config.vow_master_merit and player.hui >= config.vow_master_hui
        elif vow == Vow.ARHAT:
            return player.hui >= config.vow_arhat_hui
        elif vow == Vow.BODHISATTVA:
            return player.merit >= config.vow_bodhisattva_merit and player.save_count >= config.vow_bodhisattva_save
        return False
    
    def check_bodhisattva_vow(self, player: Player, state: GameState) -> bool:
        """检查菩萨愿是否达成"""
        bvow = player.bodhisattva_vow
        config = self.config
        
        if bvow == BodhisattvaVow.KSITIGARBHA:
            # v5.4: 需劫难≤4 且 主动承受≥2次
            return (state.calamity <= config.bvow_ksitigarbha_calamity and 
                    player.ksitigarbha_absorb_count >= config.bvow_ksitigarbha_absorb)
        elif bvow == BodhisattvaVow.AVALOKITESVARA:
            # v5.4: 帮助≥9次
            total_help = player.donate_count + player.save_count + player.protect_count
            return total_help >= config.bvow_avalokitesvara_help
        elif bvow == BodhisattvaVow.SAMANTABHADRA:
            return player.donate_count >= config.bvow_samantabhadra_donate and state.total_saves >= config.bvow_samantabhadra_save
        elif bvow == BodhisattvaVow.MANJUSRI:
            # 文殊愿：渡化≥3次 且 帮助≥6次（智慧度众）
            total_help = player.donate_count + player.save_count + player.protect_count
            return player.save_count >= config.bvow_manjusri_assist and total_help >= 6
        return False
    
    def run_game(self) -> Dict:
        """运行一局游戏"""
        players = self.init_players()
        state = GameState(config=self.config, players=players)
        
        # 初始众生
        state.beings_in_play = [0, 1]
        state.being_timers = [0, 0]
        
        # 选择信仰和发愿
        for p in players:
            self.apply_faith_choice(p, state)
            p.vow = AIDecision.choose_vow(p)
            if p.faith == FaithState.MAHAYANA:
                p.bodhisattva_vow = AIDecision.choose_bodhisattva_vow(p)
        
        # 游戏循环
        for round_num in range(1, self.config.total_rounds + 1):
            state.current_round = round_num
            
            # 检查中途皈依
            for p in players:
                self.check_mid_game_refuge(p, state)
            
            # 重置每回合帮助计数
            for p in players:
                p.help_count = 0
            
            # 集体事件
            self.process_collective_event(state)
            
            # 众生阶段
            self.process_beings_phase(state)
            
            # 检查立即失败
            if state.calamity >= self.config.max_calamity:
                break
            
            # 行动阶段（每人2行动）
            for p in players:
                # v5.4: 模拟学者使用主动技能
                if p.role == Role.SCHOLAR and p.scholar_skill_used < 2 and random.random() < 0.3:
                    p.scholar_skill_used += 1
                
                # v5.4: 模拟地藏愿主动承受
                if p.bodhisattva_vow == BodhisattvaVow.KSITIGARBHA and random.random() < 0.25:
                    p.ksitigarbha_absorb_count += 1
                
                for action_num in range(2):
                    action = AIDecision.choose_action(p, state, 2 - action_num)
                    self.execute_action(p, action, state)
            
            # 回合结束
            self.process_round_end(state)
            
            # 检查立即失败
            if state.calamity >= self.config.max_calamity:
                break
        
        # 计算结果
        team_win = state.calamity <= self.config.win_calamity and state.total_saves >= self.config.win_save
        
        result = {
            "team_win": team_win,
            "final_calamity": state.calamity,
            "total_saves": state.total_saves,
            "players": []
        }
        
        for p in players:
            vow_achieved = self.check_vow(p, state) if p.vow else False
            bvow_achieved = self.check_bodhisattva_vow(p, state) if p.bodhisattva_vow else False
            
            player_result = {
                "role": p.role.value,
                "faith": p.faith.value,
                "sacrifice": p.sacrifice.value if p.sacrifice else None,
                "wealth": p.wealth,
                "merit": p.merit,
                "hui": p.hui,
                "vow": p.vow.value if p.vow else None,
                "vow_achieved": vow_achieved,
                "bodhisattva_vow": p.bodhisattva_vow.value if p.bodhisattva_vow else None,
                "bvow_achieved": bvow_achieved,
                # 行动统计
                "labor_count": p.labor_count,
                "practice_count": p.practice_count,
                "donate_count": p.donate_count,
                "save_count": p.save_count,
                "protect_count": p.protect_count,
                # 职业特性
                "merchant_first_save": p.merchant_first_save,
                "monk_merit_substitute": p.monk_merit_substitute,
                "mahayana_penalty": p.mahayana_penalty,
            }
            result["players"].append(player_result)
        
        return result

# ============== 统计分析器 ==============

class BalanceAnalyzer:
    def __init__(self, config: GameConfig, num_simulations: int = 5000):
        self.config = config
        self.num_simulations = num_simulations
        self.results = []
    
    def run_simulations(self):
        """运行模拟"""
        engine = GameEngine(self.config)
        for i in range(self.num_simulations):
            if (i + 1) % 1000 == 0:
                print(f"  模拟进度: {i+1}/{self.num_simulations}")
            result = engine.run_game()
            self.results.append(result)
    
    def analyze(self) -> Dict:
        """分析结果"""
        stats = {
            "total_games": len(self.results),
            "team_wins": 0,
            "team_win_rate": 0,
            "avg_calamity": 0,
            "avg_saves": 0,
            
            # 按职业统计（含行动模式）
            "by_role": defaultdict(lambda: {
                "count": 0,
                "avg_merit": 0,
                "avg_hui": 0,
                "avg_wealth": 0,
                "vow_achieved": 0,
                "avg_labor": 0,
                "avg_practice": 0,
                "avg_donate": 0,
                "avg_save": 0,
                "avg_protect": 0,
            }),
            
            # 按信仰统计
            "by_faith": defaultdict(lambda: {
                "count": 0,
                "avg_merit": 0,
                "avg_hui": 0,
                "vow_achieved": 0,
            }),
            
            # 按舍离类型统计
            "by_sacrifice": defaultdict(lambda: {
                "count": 0,
                "avg_merit": 0,
                "vow_achieved": 0,
                "bvow_achieved": 0,
            }),
            
            # 按发愿统计
            "by_vow": defaultdict(lambda: {
                "count": 0,
                "achieved": 0,
                "rate": 0,
            }),
            
            # 按菩萨愿统计
            "by_bvow": defaultdict(lambda: {
                "count": 0,
                "achieved": 0,
                "rate": 0,
            }),
            
            # 行动统计
            "action_stats": {
                "avg_donate": 0,
                "avg_save": 0,
                "avg_protect": 0,
            },
            
            # 大乘行持惩罚
            "mahayana_penalty_rate": 0,
        }
        
        total_calamity = 0
        total_saves = 0
        total_donate = 0
        total_save_actions = 0
        total_protect = 0
        total_mahayana = 0
        total_mahayana_penalty = 0
        
        for result in self.results:
            if result["team_win"]:
                stats["team_wins"] += 1
            total_calamity += result["final_calamity"]
            total_saves += result["total_saves"]
            
            for p in result["players"]:
                role = p["role"]
                faith = p["faith"]
                sacrifice = p["sacrifice"]
                vow = p["vow"]
                bvow = p["bodhisattva_vow"]
                
                # 职业统计（含行动模式）
                stats["by_role"][role]["count"] += 1
                stats["by_role"][role]["avg_merit"] += p["merit"]
                stats["by_role"][role]["avg_hui"] += p["hui"]
                stats["by_role"][role]["avg_wealth"] += p["wealth"]
                stats["by_role"][role]["avg_labor"] += p["labor_count"]
                stats["by_role"][role]["avg_practice"] += p["practice_count"]
                stats["by_role"][role]["avg_donate"] += p["donate_count"]
                stats["by_role"][role]["avg_save"] += p["save_count"]
                stats["by_role"][role]["avg_protect"] += p["protect_count"]
                if p["vow_achieved"]:
                    stats["by_role"][role]["vow_achieved"] += 1
                
                # 信仰统计
                stats["by_faith"][faith]["count"] += 1
                stats["by_faith"][faith]["avg_merit"] += p["merit"]
                stats["by_faith"][faith]["avg_hui"] += p["hui"]
                if p["vow_achieved"]:
                    stats["by_faith"][faith]["vow_achieved"] += 1
                
                # 舍离统计
                if sacrifice:
                    stats["by_sacrifice"][sacrifice]["count"] += 1
                    stats["by_sacrifice"][sacrifice]["avg_merit"] += p["merit"]
                    if p["vow_achieved"]:
                        stats["by_sacrifice"][sacrifice]["vow_achieved"] += 1
                    if p["bvow_achieved"]:
                        stats["by_sacrifice"][sacrifice]["bvow_achieved"] += 1
                
                # 发愿统计
                if vow:
                    stats["by_vow"][vow]["count"] += 1
                    if p["vow_achieved"]:
                        stats["by_vow"][vow]["achieved"] += 1
                
                # 菩萨愿统计
                if bvow:
                    stats["by_bvow"][bvow]["count"] += 1
                    if p["bvow_achieved"]:
                        stats["by_bvow"][bvow]["achieved"] += 1
                
                # 行动统计
                total_donate += p["donate_count"]
                total_save_actions += p["save_count"]
                total_protect += p["protect_count"]
                
                # 大乘惩罚
                if faith == "大乘":
                    total_mahayana += 1
                    total_mahayana_penalty += p["mahayana_penalty"]
        
        # 计算平均值
        n = len(self.results)
        stats["team_win_rate"] = stats["team_wins"] / n
        stats["avg_calamity"] = total_calamity / n
        stats["avg_saves"] = total_saves / n
        
        for role in stats["by_role"]:
            cnt = stats["by_role"][role]["count"]
            if cnt > 0:
                stats["by_role"][role]["avg_merit"] /= cnt
                stats["by_role"][role]["avg_hui"] /= cnt
                stats["by_role"][role]["avg_wealth"] /= cnt
                stats["by_role"][role]["avg_labor"] /= cnt
                stats["by_role"][role]["avg_practice"] /= cnt
                stats["by_role"][role]["avg_donate"] /= cnt
                stats["by_role"][role]["avg_save"] /= cnt
                stats["by_role"][role]["avg_protect"] /= cnt
                stats["by_role"][role]["vow_rate"] = stats["by_role"][role]["vow_achieved"] / cnt
        
        for faith in stats["by_faith"]:
            cnt = stats["by_faith"][faith]["count"]
            if cnt > 0:
                stats["by_faith"][faith]["avg_merit"] /= cnt
                stats["by_faith"][faith]["avg_hui"] /= cnt
                stats["by_faith"][faith]["vow_rate"] = stats["by_faith"][faith]["vow_achieved"] / cnt
        
        for sacrifice in stats["by_sacrifice"]:
            cnt = stats["by_sacrifice"][sacrifice]["count"]
            if cnt > 0:
                stats["by_sacrifice"][sacrifice]["avg_merit"] /= cnt
                stats["by_sacrifice"][sacrifice]["vow_rate"] = stats["by_sacrifice"][sacrifice]["vow_achieved"] / cnt
                stats["by_sacrifice"][sacrifice]["bvow_rate"] = stats["by_sacrifice"][sacrifice]["bvow_achieved"] / cnt
        
        for vow in stats["by_vow"]:
            cnt = stats["by_vow"][vow]["count"]
            if cnt > 0:
                stats["by_vow"][vow]["rate"] = stats["by_vow"][vow]["achieved"] / cnt
        
        for bvow in stats["by_bvow"]:
            cnt = stats["by_bvow"][bvow]["count"]
            if cnt > 0:
                stats["by_bvow"][bvow]["rate"] = stats["by_bvow"][bvow]["achieved"] / cnt
        
        player_count = n * 4
        stats["action_stats"]["avg_donate"] = total_donate / player_count
        stats["action_stats"]["avg_save"] = total_save_actions / player_count
        stats["action_stats"]["avg_protect"] = total_protect / player_count
        
        if total_mahayana > 0:
            stats["mahayana_penalty_rate"] = total_mahayana_penalty / total_mahayana
        
        return stats
    
    def generate_report(self, stats: Dict) -> str:
        """生成报告"""
        lines = []
        lines.append("=" * 70)
        lines.append("《功德轮回》v5.3 全面平衡分析报告")
        lines.append(f"模拟局数: {stats['total_games']}")
        lines.append("=" * 70)
        lines.append("")
        
        # 团队胜率
        lines.append(f"【团队胜率】: {stats['team_win_rate']*100:.1f}%")
        lines.append(f"  平均劫难: {stats['avg_calamity']:.1f}")
        lines.append(f"  平均渡化: {stats['avg_saves']:.1f}")
        lines.append("")
        
        # 职业统计
        lines.append("【职业统计】")
        for role in ["农夫", "商人", "学者", "僧侣"]:
            if role in stats["by_role"]:
                r = stats["by_role"][role]
                lines.append(f"  {role}: 功德={r['avg_merit']:.1f} 慧={r['avg_hui']:.1f} 资={r['avg_wealth']:.1f} 发愿达成={r.get('vow_rate', 0)*100:.1f}%")
        lines.append("")
        
        # 职业行动模式
        lines.append("【职业行动模式（每人每局）】")
        lines.append("  职业    | 劳作 | 修行 | 布施 | 渡化 | 护法 | 特色行动")
        lines.append("  --------|------|------|------|------|------|----------")
        role_specialties = {
            "农夫": "劳作积累",
            "商人": "布施为主",
            "学者": "修行优先",
            "僧侣": "渡化专精",
        }
        for role in ["农夫", "商人", "学者", "僧侣"]:
            if role in stats["by_role"]:
                r = stats["by_role"][role]
                specialty = role_specialties.get(role, "")
                lines.append(f"  {role}    | {r['avg_labor']:.1f}  | {r['avg_practice']:.1f}  | {r['avg_donate']:.1f}  | {r['avg_save']:.1f}  | {r['avg_protect']:.1f}  | {specialty}")
        lines.append("")
        
        # 信仰统计
        lines.append("【信仰路线统计】")
        for faith in ["不皈依", "皈依", "大乘"]:
            if faith in stats["by_faith"]:
                f = stats["by_faith"][faith]
                lines.append(f"  {faith}: 人数={f['count']} 功德={f['avg_merit']:.1f} 慧={f['avg_hui']:.1f} 发愿达成={f.get('vow_rate', 0)*100:.1f}%")
        lines.append("")
        
        # 舍离类型统计
        lines.append("【大乘舍离类型统计】")
        for sacrifice in ["舍资施众", "舍功德迴向", "舍慧度众"]:
            if sacrifice in stats["by_sacrifice"]:
                s = stats["by_sacrifice"][sacrifice]
                lines.append(f"  {sacrifice}: 人数={s['count']} 功德={s['avg_merit']:.1f} 职愿达成={s.get('vow_rate', 0)*100:.1f}% 菩萨愿达成={s.get('bvow_rate', 0)*100:.1f}%")
        lines.append("")
        
        # 发愿统计
        lines.append("【职业发愿达成率】")
        for vow in stats["by_vow"]:
            v = stats["by_vow"][vow]
            lines.append(f"  {vow}: {v['achieved']}/{v['count']} = {v['rate']*100:.1f}%")
        lines.append("")
        
        # 菩萨愿统计
        lines.append("【菩萨愿达成率】")
        for bvow in stats["by_bvow"]:
            b = stats["by_bvow"][bvow]
            lines.append(f"  {bvow}: {b['achieved']}/{b['count']} = {b['rate']*100:.1f}%")
        lines.append("")
        
        # 行动统计
        lines.append("【行动使用频率（每人每局）】")
        lines.append(f"  布施: {stats['action_stats']['avg_donate']:.2f}")
        lines.append(f"  渡化: {stats['action_stats']['avg_save']:.2f}")
        lines.append(f"  护法: {stats['action_stats']['avg_protect']:.2f}")
        lines.append("")
        
        # 大乘惩罚
        lines.append(f"【大乘行持惩罚率】: {stats['mahayana_penalty_rate']:.2f} 次/人")
        lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)

# ============== 主程序 ==============

def main():
    print("《功德轮回》v5.6 全面平衡模拟器")
    print("=" * 50)
    
    # 转换defaultdict为普通dict
    def convert_dict(d):
        if isinstance(d, defaultdict):
            d = dict(d)
        if isinstance(d, dict):
            return {k: convert_dict(v) for k, v in d.items()}
        return d
    
    # ============ 基础版模拟 ============
    print("\n【基础版模拟】")
    config = GameConfig()
    analyzer = BalanceAnalyzer(config, num_simulations=5000)
    
    print("开始模拟...")
    analyzer.run_simulations()
    
    print("分析数据...")
    stats = analyzer.analyze()
    
    report = analyzer.generate_report(stats)
    print(report)
    
    with open("balance_report_v53.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    with open("balance_stats_v53.json", "w", encoding="utf-8") as f:
        json.dump(convert_dict(stats), f, ensure_ascii=False, indent=2)
    
    # ============ 人间炼狱版模拟 ============
    print("\n" + "=" * 50)
    print("【人间炼狱版模拟】")
    print("=" * 50)
    
    hell_config = GameConfig(hell_mode=True)
    hell_analyzer = BalanceAnalyzer(hell_config, num_simulations=5000)
    
    print("开始模拟...")
    hell_analyzer.run_simulations()
    
    print("分析数据...")
    hell_stats = hell_analyzer.analyze()
    
    hell_report = hell_analyzer.generate_report(hell_stats)
    hell_report = hell_report.replace("v5.3", "v5.6 人间炼狱版")
    print(hell_report)
    
    with open("balance_report_hell.txt", "w", encoding="utf-8") as f:
        f.write(hell_report)
    
    with open("balance_stats_hell.json", "w", encoding="utf-8") as f:
        json.dump(convert_dict(hell_stats), f, ensure_ascii=False, indent=2)
    
    print("\n报告已保存:")
    print("  基础版: balance_report_v53.txt")
    print("  人间炼狱版: balance_report_hell.txt")

if __name__ == "__main__":
    main()
