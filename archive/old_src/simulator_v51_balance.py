# -*- coding: utf-8 -*-
"""
《功德轮回：众生百态》v5.1 综合平衡性模拟器

测试目标：
1. 资源经济紧张度 - 资源是否过多/过少？生存压力是否足够？
2. 职业平衡 - 胜率、得分分布、发愿达成率
3. 行动效用 - 每个行动的使用频率和价值
4. 事件卡影响 - 事件对游戏的影响程度
5. 决策点质量 - 每个决策的有效性
6. 新机制测试 - 福田、功德迴向、资源转换、绝境逆转等
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum
from collections import defaultdict
import json

# ============ 枚举定义 ============
class Role(Enum):
    FARMER = "农夫"
    MERCHANT = "商人"
    SCHOLAR = "学者"
    MONK = "僧侣"

class FaithState(Enum):
    SECULAR = "不皈依"
    SMALL_VEHICLE = "皈依"
    GREAT_VEHICLE = "大乘"

class Vow(Enum):
    # 简单发愿
    DILIGENT_MERIT = "勤劳致功德"  # 农夫简单
    WEALTH_DONATE = "资施功德"     # 商人简单
    TEACH_WISDOM = "传道授业"      # 学者简单
    ARHAT = "阿罗汉果"             # 僧侣简单
    # 困难发愿
    POOR_GIRL_LAMP = "贫女一灯"    # 农夫困难
    GREAT_MERCHANT = "大商人之心"  # 商人困难
    TEACHER_MODEL = "万世师表"     # 学者困难
    BODHISATTVA = "菩萨道"         # 僧侣困难

class ActionType(Enum):
    LABOR = "劳作"
    PRACTICE = "修行"
    DONATE = "布施"
    SAVE = "渡化"
    PROTECT = "护法"
    SKILL = "主动技能"

class EventType(Enum):
    DISASTER = "天灾"
    MISFORTUNE = "人祸"
    BLESSING = "功德"

# ============ 游戏配置 v5.1 ============
@dataclass
class GameConfig:
    """v5.1 规则参数"""
    # 胜利条件
    calamity_limit: int = 20        # 劫难上限
    calamity_win_threshold: int = 12  # 团队胜利劫难阈值
    save_target: int = 5            # 渡化目标
    max_rounds: int = 6
    
    # 初始资源 (资粮, 功德, 慧)
    init_farmer: Tuple[int, int, int] = (5, 2, 2)
    init_merchant: Tuple[int, int, int] = (9, 2, 1)
    init_scholar: Tuple[int, int, int] = (4, 2, 5)
    init_monk: Tuple[int, int, int] = (1, 5, 5)
    
    # 皈依效果
    secular_wealth_bonus: int = 4      # 不皈依+4资粮
    small_vehicle_merit_bonus: int = 1  # 皈依+1功德
    small_vehicle_hui_bonus: int = 1    # 皈依+1慧
    great_vehicle_wealth_cost: int = 2  # 大乘-2资粮（开局）
    great_vehicle_mid_cost: int = 3     # 大乘-3资粮（中途）
    great_vehicle_hui_bonus: int = 1    # 大乘+1慧
    
    # 行动基础值
    labor_base: int = 3
    labor_farmer_bonus: int = 1    # 农夫劳作+1
    labor_secular_bonus: int = 1   # 不皈依劳作+1
    practice_base: int = 2
    practice_scholar_bonus: int = 2  # 学者修行+2（共4慧）
    donate_cost: int = 2
    donate_merit_base: int = 2
    donate_merchant_bonus: int = 2   # 商人布施+2功德
    donate_faith_bonus: int = 1      # 皈依者布施+1功德
    donate_calamity_reduce: int = 1
    protect_cost: int = 2
    protect_merit: int = 1
    protect_calamity_reduce: int = 2
    
    # 渡化
    save_hui_threshold: int = 5      # 渡化所需慧
    save_cost_monk_reduce: int = 1   # 僧侣渡化-1成本
    save_cost_secular_reduce: int = 1  # 不皈依渡化-1成本
    
    # 发愿条件 (v4.7 平衡后)
    vow_diligent_merit: int = 24    # 勤劳致功德: 功德≥24
    vow_poor_girl_merit: int = 30   # 贫女一灯: 功德≥30 且 资粮≤5
    vow_poor_girl_wealth: int = 5
    vow_wealth_donate_count: int = 3  # 资施功德: 布施≥3次
    vow_great_merchant_merit: int = 18  # 大商人之心: 功德≥18 且 渡化≥2
    vow_great_merchant_save: int = 2
    vow_teach_hui: int = 18          # 传道授业: 慧≥18
    vow_teacher_merit: int = 12      # 万世师表: 功德≥12 且 慧≥18
    vow_teacher_hui: int = 18
    vow_arhat_hui: int = 14          # 阿罗汉果: 慧≥14
    vow_bodhisattva_merit: int = 15  # 菩萨道: 功德≥15 且 渡化≥3
    vow_bodhisattva_save: int = 3
    
    # 发愿奖惩
    vow_simple_reward: int = 12
    vow_simple_penalty: int = 4
    vow_hard_reward: int = 16
    vow_hard_penalty: int = 6
    
    # 每回合发愿奖励
    vow_farmer_merit_per_round: int = 1   # 农夫每回合+1功德
    vow_merchant_wealth_per_round: int = 1  # 商人每回合+1资粮
    vow_scholar_hui_per_round: int = 1    # 学者每回合+1慧
    vow_monk_hui_per_round: int = 1       # 僧侣简单每回合+1慧
    vow_monk_hard_merit_per_round: int = 1  # 僧侣困难每回合+1功德
    
    # 众生卡
    being_costs: List[int] = field(default_factory=lambda: [2, 2, 3, 3, 3, 4, 4, 5, 2, 4])
    being_merits: List[int] = field(default_factory=lambda: [2, 2, 3, 2, 1, 2, 4, 3, 3, 2])
    being_hui: List[int] = field(default_factory=lambda: [1, 1, 1, 2, 3, 2, 1, 3, 0, 2])
    futian_indices: List[int] = field(default_factory=lambda: [2, 4, 7])  # 孤儿、落魄书生、垂死老者
    
    # 劫难
    disaster_base_calamity: int = 4
    misfortune_base_calamity: int = 3
    timeout_penalty: int = 4  # 众生超时+4劫难
    
    # 生存消耗（偶数回合）
    survival_cost: int = 1
    
    # 事件权重
    disaster_weight: float = 0.33
    misfortune_weight: float = 0.17
    blessing_weight: float = 0.50

# ============ 玩家类 ============
@dataclass
class Player:
    role: Role
    faith: FaithState = FaithState.SECULAR
    wealth: int = 0
    merit: int = 0  # 功德
    hui: int = 0    # 慧
    vow: Optional[Vow] = None
    
    # 追踪统计
    donate_count: int = 0
    save_count: int = 0
    help_count: int = 0  # 布施+渡化+护法
    skill_uses: int = 2
    actions_taken: Dict[ActionType, int] = field(default_factory=lambda: defaultdict(int))
    
    # 资源来源追踪
    wealth_sources: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    merit_sources: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    hui_sources: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # 决策追踪
    decisions_made: List[str] = field(default_factory=list)
    
    def init_resources(self, config: GameConfig):
        if self.role == Role.FARMER:
            self.wealth, self.merit, self.hui = config.init_farmer
        elif self.role == Role.MERCHANT:
            self.wealth, self.merit, self.hui = config.init_merchant
        elif self.role == Role.SCHOLAR:
            self.wealth, self.merit, self.hui = config.init_scholar
        elif self.role == Role.MONK:
            self.wealth, self.merit, self.hui = config.init_monk
        self.wealth_sources["初始"] = self.wealth
        self.merit_sources["初始"] = self.merit
        self.hui_sources["初始"] = self.hui
    
    def apply_faith(self, faith: FaithState, config: GameConfig, is_start: bool = True):
        if faith == FaithState.SECULAR:
            if is_start:
                self.wealth += config.secular_wealth_bonus
                self.wealth_sources["不皈依"] += config.secular_wealth_bonus
        elif faith == FaithState.SMALL_VEHICLE:
            if is_start:
                self.merit += config.small_vehicle_merit_bonus
                self.hui += config.small_vehicle_hui_bonus
                self.merit_sources["皈依"] += config.small_vehicle_merit_bonus
                self.hui_sources["皈依"] += config.small_vehicle_hui_bonus
            else:
                self.merit += 1
                self.merit_sources["中途皈依"] += 1
        self.faith = faith
    
    def get_score(self, config: GameConfig) -> int:
        total = self.merit + self.hui
        if total < 10: base = 10
        elif total < 15: base = 15
        elif total < 20: base = 25
        elif total < 25: base = 35
        elif total < 30: base = 45
        elif total < 35: base = 55
        else: base = 65
        if self.merit < 5 or self.hui < 5:
            base = base // 2
        return base
    
    def check_vow(self, config: GameConfig) -> Tuple[int, int]:
        """返回 (奖励分, 惩罚分)"""
        if self.vow is None:
            return 0, 0
        
        achieved = False
        is_hard = False
        
        if self.vow == Vow.DILIGENT_MERIT:
            achieved = self.merit >= config.vow_diligent_merit
        elif self.vow == Vow.POOR_GIRL_LAMP:
            achieved = self.merit >= config.vow_poor_girl_merit and self.wealth <= config.vow_poor_girl_wealth
            is_hard = True
        elif self.vow == Vow.WEALTH_DONATE:
            achieved = self.donate_count >= config.vow_wealth_donate_count
        elif self.vow == Vow.GREAT_MERCHANT:
            achieved = self.merit >= config.vow_great_merchant_merit and self.save_count >= config.vow_great_merchant_save
            is_hard = True
        elif self.vow == Vow.TEACH_WISDOM:
            achieved = self.hui >= config.vow_teach_hui
        elif self.vow == Vow.TEACHER_MODEL:
            achieved = self.merit >= config.vow_teacher_merit and self.hui >= config.vow_teacher_hui
            is_hard = True
        elif self.vow == Vow.ARHAT:
            achieved = self.hui >= config.vow_arhat_hui
        elif self.vow == Vow.BODHISATTVA:
            achieved = self.merit >= config.vow_bodhisattva_merit and self.save_count >= config.vow_bodhisattva_save
            is_hard = True
        
        if achieved:
            return (config.vow_hard_reward if is_hard else config.vow_simple_reward), 0
        else:
            return 0, (config.vow_hard_penalty if is_hard else config.vow_simple_penalty)

# ============ 游戏状态 ============
@dataclass
class GameState:
    config: GameConfig
    players: List[Player]
    calamity: int = 0
    saved_count: int = 0
    current_round: int = 1
    beings_in_play: List[Tuple[int, int]] = field(default_factory=list)  # (being_index, delay_count)
    event_history: List[Tuple[int, EventType, str]] = field(default_factory=list)
    tension_log: List[Dict] = field(default_factory=list)  # 紧张度记录
    
    def is_team_win(self) -> bool:
        return self.calamity <= self.config.calamity_win_threshold and self.saved_count >= self.config.save_target
    
    def is_team_loss(self) -> bool:
        return self.calamity >= self.config.calamity_limit
    
    def log_tension(self, phase: str):
        """记录当前紧张度"""
        total_wealth = sum(p.wealth for p in self.players)
        avg_wealth = total_wealth / len(self.players)
        min_wealth = min(p.wealth for p in self.players)
        self.tension_log.append({
            "round": self.current_round,
            "phase": phase,
            "calamity": self.calamity,
            "saved": self.saved_count,
            "total_wealth": total_wealth,
            "avg_wealth": avg_wealth,
            "min_wealth": min_wealth,
            "calamity_margin": self.config.calamity_limit - self.calamity,
            "save_deficit": self.config.save_target - self.saved_count
        })

# ============ AI 决策 ============
class AIDecision:
    """AI决策引擎"""
    
    @staticmethod
    def choose_faith(player: Player, config: GameConfig) -> FaithState:
        """选择信仰状态"""
        # 僧侣默认皈依
        if player.role == Role.MONK:
            return FaithState.SMALL_VEHICLE
        
        # 其他职业：50%皈依，30%不皈依，20%大乘
        r = random.random()
        if r < 0.5:
            return FaithState.SMALL_VEHICLE
        elif r < 0.8:
            return FaithState.SECULAR
        else:
            return FaithState.GREAT_VEHICLE
    
    @staticmethod
    def choose_vow(player: Player, config: GameConfig) -> Vow:
        """选择发愿"""
        # 简单发愿概率更高（70%）
        if random.random() < 0.7:
            if player.role == Role.FARMER:
                return Vow.DILIGENT_MERIT
            elif player.role == Role.MERCHANT:
                return Vow.WEALTH_DONATE
            elif player.role == Role.SCHOLAR:
                return Vow.TEACH_WISDOM
            else:
                return Vow.ARHAT
        else:
            if player.role == Role.FARMER:
                return Vow.POOR_GIRL_LAMP
            elif player.role == Role.MERCHANT:
                return Vow.GREAT_MERCHANT
            elif player.role == Role.SCHOLAR:
                return Vow.TEACHER_MODEL
            else:
                return Vow.BODHISATTVA
    
    @staticmethod
    def choose_action(player: Player, state: GameState) -> ActionType:
        """选择行动"""
        config = state.config
        
        # 紧急情况：劫难过高
        if state.calamity >= config.calamity_limit - 4:
            if player.wealth >= config.protect_cost:
                return ActionType.PROTECT
            elif player.wealth >= config.donate_cost:
                return ActionType.DONATE
        
        # 渡化机会
        if player.hui >= config.save_hui_threshold and state.beings_in_play:
            best_being = AIDecision._find_affordable_being(player, state)
            if best_being is not None:
                # 有可负担的众生，考虑渡化
                if state.saved_count < config.save_target or random.random() < 0.6:
                    return ActionType.SAVE
        
        # 慧不够渡化，修行
        if player.hui < config.save_hui_threshold:
            return ActionType.PRACTICE
        
        # 资源决策
        if player.wealth < 4:
            return ActionType.LABOR
        
        # 功德导向
        if player.merit < 10:
            if player.wealth >= config.donate_cost:
                return ActionType.DONATE
        
        # 平衡策略
        actions = [ActionType.LABOR, ActionType.PRACTICE, ActionType.DONATE]
        weights = [0.3, 0.3, 0.4]
        
        # 根据职业调整
        if player.role == Role.FARMER:
            weights = [0.5, 0.2, 0.3]
        elif player.role == Role.MERCHANT:
            weights = [0.3, 0.1, 0.6]
        elif player.role == Role.SCHOLAR:
            weights = [0.2, 0.5, 0.3]
        elif player.role == Role.MONK:
            weights = [0.2, 0.4, 0.4]
        
        return random.choices(actions, weights=weights)[0]
    
    @staticmethod
    def _find_affordable_being(player: Player, state: GameState) -> Optional[int]:
        """找到可负担的众生"""
        config = state.config
        for being_idx, delay in state.beings_in_play:
            cost = config.being_costs[being_idx]
            # 调整成本
            if player.role == Role.MONK:
                cost -= config.save_cost_monk_reduce
            if player.faith == FaithState.SECULAR:
                cost -= config.save_cost_secular_reduce
            cost = max(0, cost)
            if player.wealth >= cost:
                return being_idx
        return None
    
    @staticmethod
    def choose_disaster_response(player: Player, state: GameState) -> str:
        """天灾抉择：A（牺牲）或 B（保守）"""
        # 资源充足时更倾向选A
        if player.wealth >= 4:
            return "A" if random.random() < 0.6 else "B"
        else:
            return "A" if random.random() < 0.3 else "B"

# ============ 游戏引擎 ============
class GameEngine:
    def __init__(self, config: GameConfig = None):
        self.config = config or GameConfig()
    
    def setup_game(self) -> GameState:
        """初始化游戏"""
        players = []
        for role in Role:
            player = Player(role=role)
            player.init_resources(self.config)
            player.faith = AIDecision.choose_faith(player, self.config)
            player.apply_faith(player.faith, self.config, is_start=True)
            player.vow = AIDecision.choose_vow(player, self.config)
            players.append(player)
        
        state = GameState(config=self.config, players=players)
        
        # 初始众生（2张）
        state.beings_in_play = [(0, 0), (1, 0)]
        
        return state
    
    def run_round(self, state: GameState) -> bool:
        """执行一回合，返回游戏是否继续"""
        round_num = state.current_round
        
        # 0. 发愿奖励
        self._phase_vow_reward(state)
        
        # 1. 集体事件
        self._phase_collective_event(state)
        if state.is_team_loss():
            return False
        
        # 2. 个人事件（奇数回合）
        if round_num % 2 == 1:
            self._phase_personal_event(state)
        
        # 3. 众生阶段
        self._phase_beings(state)
        if state.is_team_loss():
            return False
        
        # 4. 行动阶段
        self._phase_actions(state)
        if state.is_team_loss():
            return False
        
        state.log_tension("行动后")
        
        # 5. 结算阶段
        self._phase_settlement(state)
        if state.is_team_loss():
            return False
        
        state.current_round += 1
        return state.current_round <= self.config.max_rounds
    
    def _phase_vow_reward(self, state: GameState):
        """发愿每回合奖励"""
        for player in state.players:
            if player.vow in [Vow.DILIGENT_MERIT, Vow.POOR_GIRL_LAMP]:
                player.merit += self.config.vow_farmer_merit_per_round
                player.merit_sources["发愿每回合"] += self.config.vow_farmer_merit_per_round
            elif player.vow in [Vow.WEALTH_DONATE, Vow.GREAT_MERCHANT]:
                if player.vow == Vow.WEALTH_DONATE:
                    player.wealth += self.config.vow_merchant_wealth_per_round
                    player.wealth_sources["发愿每回合"] += self.config.vow_merchant_wealth_per_round
                else:
                    player.hui += 1  # 大商人之心每回合+1慧
                    player.hui_sources["发愿每回合"] += 1
            elif player.vow in [Vow.TEACH_WISDOM, Vow.TEACHER_MODEL]:
                player.hui += self.config.vow_scholar_hui_per_round
                player.hui_sources["发愿每回合"] += self.config.vow_scholar_hui_per_round
            elif player.vow == Vow.ARHAT:
                player.hui += self.config.vow_monk_hui_per_round
                player.hui_sources["发愿每回合"] += self.config.vow_monk_hui_per_round
            elif player.vow == Vow.BODHISATTVA:
                player.merit += self.config.vow_monk_hard_merit_per_round
                player.merit_sources["发愿每回合"] += self.config.vow_monk_hard_merit_per_round
    
    def _phase_collective_event(self, state: GameState):
        """集体事件"""
        # 随机事件类型
        r = random.random()
        if r < self.config.disaster_weight:
            event_type = EventType.DISASTER
        elif r < self.config.disaster_weight + self.config.misfortune_weight:
            event_type = EventType.MISFORTUNE
        else:
            event_type = EventType.BLESSING
        
        if event_type == EventType.DISASTER:
            self._handle_disaster(state)
        elif event_type == EventType.MISFORTUNE:
            self._handle_misfortune(state)
        else:
            self._handle_blessing(state)
        
        state.event_history.append((state.current_round, event_type, ""))
    
    def _handle_disaster(self, state: GameState):
        """处理天灾"""
        state.calamity += self.config.disaster_base_calamity
        
        # 玩家抉择
        choice_a_count = 0
        for player in state.players:
            choice = AIDecision.choose_disaster_response(player, state)
            player.decisions_made.append(f"R{state.current_round}天灾:{choice}")
            if choice == "A":
                choice_a_count += 1
                player.wealth -= 2
                player.merit += 1
                player.merit_sources["天灾抉择"] += 1
            else:
                player.wealth -= 1
        
        # 每多1人选A，劫难-1
        state.calamity -= choice_a_count
        
        # 全选B额外+2劫难
        if choice_a_count == 0:
            state.calamity += 2
    
    def _handle_misfortune(self, state: GameState):
        """处理人祸"""
        state.calamity += self.config.misfortune_base_calamity
        for player in state.players:
            player.wealth -= 1
    
    def _handle_blessing(self, state: GameState):
        """处理功德事件"""
        state.calamity -= 1
        for player in state.players:
            player.merit += 1
            player.merit_sources["功德事件"] += 1
            if player.faith != FaithState.SECULAR:
                player.merit += 1
                player.merit_sources["功德事件皈依加成"] += 1
    
    def _phase_personal_event(self, state: GameState):
        """个人事件（奇数回合）"""
        for player in state.players:
            # 简化：随机效果
            effect = random.choice(["gain", "choice", "dice"])
            if effect == "gain":
                player.merit += 1
                player.merit_sources["个人事件"] += 1
            elif effect == "choice":
                # 抉择：资源换功德
                if player.wealth >= 2 and random.random() < 0.5:
                    player.wealth -= 2
                    player.merit += 2
                    player.merit_sources["个人事件抉择"] += 2
            else:
                # 骰子
                roll = random.randint(1, 6)
                if roll >= 4:
                    player.hui += 1
                    player.hui_sources["个人事件骰子"] += 1
    
    def _phase_beings(self, state: GameState):
        """众生阶段"""
        # 滞留+1
        new_beings = []
        for being_idx, delay in state.beings_in_play:
            delay += 1
            if delay >= 2:
                # 超时惩罚
                state.calamity += self.config.timeout_penalty
            else:
                new_beings.append((being_idx, delay))
        state.beings_in_play = new_beings
        
        # 补充众生
        if len(state.beings_in_play) < 3:
            next_idx = (state.beings_in_play[-1][0] + 1) % 10 if state.beings_in_play else 2
            state.beings_in_play.append((next_idx, 0))
    
    def _phase_actions(self, state: GameState):
        """行动阶段"""
        for player in state.players:
            for _ in range(2):  # 每人2次行动
                action = AIDecision.choose_action(player, state)
                self._execute_action(player, action, state)
                player.actions_taken[action] += 1
    
    def _execute_action(self, player: Player, action: ActionType, state: GameState):
        """执行行动"""
        config = self.config
        
        if action == ActionType.LABOR:
            gain = config.labor_base
            if player.role == Role.FARMER:
                gain += config.labor_farmer_bonus
            if player.faith == FaithState.SECULAR:
                gain += config.labor_secular_bonus
            player.wealth += gain
            player.wealth_sources["劳作"] += gain
        
        elif action == ActionType.PRACTICE:
            gain = config.practice_base
            if player.role == Role.SCHOLAR:
                gain += config.practice_scholar_bonus
            player.hui += gain
            player.hui_sources["修行"] += gain
        
        elif action == ActionType.DONATE:
            if player.wealth >= config.donate_cost:
                player.wealth -= config.donate_cost
                gain = config.donate_merit_base
                if player.role == Role.MERCHANT:
                    gain += config.donate_merchant_bonus
                if player.faith != FaithState.SECULAR:
                    gain += config.donate_faith_bonus
                player.merit += gain
                player.merit_sources["布施"] += gain
                state.calamity -= config.donate_calamity_reduce
                player.donate_count += 1
                player.help_count += 1
        
        elif action == ActionType.SAVE:
            being = AIDecision._find_affordable_being(player, state)
            if being is not None and player.hui >= config.save_hui_threshold:
                # 计算成本
                cost = config.being_costs[being]
                if player.role == Role.MONK:
                    cost -= config.save_cost_monk_reduce
                if player.faith == FaithState.SECULAR:
                    cost -= config.save_cost_secular_reduce
                cost = max(0, cost)
                
                if player.wealth >= cost:
                    player.wealth -= cost
                    
                    # 奖励
                    merit_gain = config.being_merits[being]
                    hui_gain = config.being_hui[being]
                    
                    # 福田加成
                    if being in config.futian_indices:
                        merit_gain += 1
                        if player.faith != FaithState.SECULAR:
                            merit_gain += 1
                    
                    # 皈依加成
                    if player.faith != FaithState.SECULAR:
                        merit_gain += 1
                    
                    player.merit += merit_gain
                    player.hui += hui_gain
                    player.merit_sources["渡化"] += merit_gain
                    player.hui_sources["渡化"] += hui_gain
                    player.save_count += 1
                    player.help_count += 1
                    state.saved_count += 1
                    
                    # 移除众生
                    state.beings_in_play = [(b, d) for b, d in state.beings_in_play if b != being]
        
        elif action == ActionType.PROTECT:
            if player.wealth >= config.protect_cost:
                player.wealth -= config.protect_cost
                player.merit += config.protect_merit
                player.merit_sources["护法"] += config.protect_merit
                state.calamity -= config.protect_calamity_reduce
                player.help_count += 1
    
    def _phase_settlement(self, state: GameState):
        """结算阶段"""
        # 偶数回合生存消耗
        if state.current_round % 2 == 0:
            for player in state.players:
                if player.wealth >= self.config.survival_cost:
                    player.wealth -= self.config.survival_cost
                else:
                    player.wealth = 0
                    player.merit -= 1
        
        # 帮助奖励检查
        for player in state.players:
            if player.help_count >= 4 and not hasattr(player, '_help_bonus_given'):
                player.merit += 2
                player.merit_sources["帮助奖励"] += 2
                player._help_bonus_given = True
    
    def get_results(self, state: GameState) -> Dict:
        """获取游戏结果"""
        team_win = state.is_team_win()
        
        results = {
            "team_win": team_win,
            "final_calamity": state.calamity,
            "final_saved": state.saved_count,
            "rounds_played": state.current_round - 1,
            "players": []
        }
        
        for player in state.players:
            base_score = player.get_score(self.config) if team_win else 0
            vow_reward, vow_penalty = player.check_vow(self.config)
            final_score = base_score + vow_reward - vow_penalty if team_win else 0
            
            results["players"].append({
                "role": player.role.value,
                "faith": player.faith.value,
                "vow": player.vow.value if player.vow else None,
                "wealth": player.wealth,
                "merit": player.merit,
                "hui": player.hui,
                "base_score": base_score,
                "vow_reward": vow_reward,
                "vow_penalty": vow_penalty,
                "final_score": final_score,
                "vow_achieved": vow_reward > 0,
                "donate_count": player.donate_count,
                "save_count": player.save_count,
                "help_count": player.help_count,
                "actions": dict(player.actions_taken),
                "wealth_sources": dict(player.wealth_sources),
                "merit_sources": dict(player.merit_sources),
                "hui_sources": dict(player.hui_sources)
            })
        
        results["tension_log"] = state.tension_log
        
        return results

# ============ 模拟分析 ============
class BalanceAnalyzer:
    def __init__(self, num_simulations: int = 10000):
        self.num_simulations = num_simulations
        self.results = []
    
    def run_simulations(self, config: GameConfig = None):
        """运行模拟"""
        engine = GameEngine(config)
        
        for i in range(self.num_simulations):
            state = engine.setup_game()
            while engine.run_round(state):
                pass
            self.results.append(engine.get_results(state))
            
            if (i + 1) % 1000 == 0:
                print(f"完成 {i + 1}/{self.num_simulations} 局模拟...")
    
    def analyze(self) -> Dict:
        """分析结果"""
        analysis = {}
        
        # 1. 团队胜率
        team_wins = sum(1 for r in self.results if r["team_win"])
        analysis["team_win_rate"] = team_wins / len(self.results)
        
        # 2. 职业胜率（团队胜利时的个人第一名）
        role_wins = defaultdict(int)
        role_scores = defaultdict(list)
        role_vow_achieved = defaultdict(list)
        
        for result in self.results:
            if result["team_win"]:
                # 找出得分最高的玩家
                max_score = max(p["final_score"] for p in result["players"])
                for p in result["players"]:
                    role_scores[p["role"]].append(p["final_score"])
                    role_vow_achieved[p["role"]].append(1 if p["vow_achieved"] else 0)
                    if p["final_score"] == max_score:
                        role_wins[p["role"]] += 1
        
        analysis["role_win_rates"] = {role: wins / team_wins for role, wins in role_wins.items()} if team_wins > 0 else {}
        analysis["role_avg_scores"] = {role: sum(scores) / len(scores) for role, scores in role_scores.items()}
        analysis["role_vow_rates"] = {role: sum(achieved) / len(achieved) for role, achieved in role_vow_achieved.items()}
        
        # 3. 资源经济分析
        wealth_at_end = defaultdict(list)
        merit_at_end = defaultdict(list)
        hui_at_end = defaultdict(list)
        
        for result in self.results:
            for p in result["players"]:
                wealth_at_end[p["role"]].append(p["wealth"])
                merit_at_end[p["role"]].append(p["merit"])
                hui_at_end[p["role"]].append(p["hui"])
        
        analysis["resource_economy"] = {
            "avg_wealth_end": {role: sum(w) / len(w) for role, w in wealth_at_end.items()},
            "avg_merit_end": {role: sum(m) / len(m) for role, m in merit_at_end.items()},
            "avg_hui_end": {role: sum(h) / len(h) for role, h in hui_at_end.items()}
        }
        
        # 4. 行动使用分析
        action_counts = defaultdict(lambda: defaultdict(int))
        for result in self.results:
            for p in result["players"]:
                for action, count in p["actions"].items():
                    action_counts[p["role"]][action] += count
        
        analysis["action_usage"] = {
            role: {str(action): count / len(self.results) for action, count in actions.items()}
            for role, actions in action_counts.items()
        }
        
        # 5. 紧张度分析
        calamity_margins = []
        for result in self.results:
            if result["tension_log"]:
                final_log = result["tension_log"][-1]
                calamity_margins.append(final_log["calamity_margin"])
        
        analysis["tension"] = {
            "avg_calamity_margin": sum(calamity_margins) / len(calamity_margins) if calamity_margins else 0,
            "tight_games": sum(1 for m in calamity_margins if m <= 4) / len(calamity_margins) if calamity_margins else 0,
            "comfortable_games": sum(1 for m in calamity_margins if m >= 10) / len(calamity_margins) if calamity_margins else 0
        }
        
        # 6. 劫难来源分析
        analysis["calamity_stats"] = {
            "avg_final_calamity": sum(r["final_calamity"] for r in self.results) / len(self.results),
            "avg_saved": sum(r["final_saved"] for r in self.results) / len(self.results)
        }
        
        # 7. 发愿达成率详细
        vow_stats = defaultdict(lambda: {"achieved": 0, "total": 0})
        for result in self.results:
            for p in result["players"]:
                if p["vow"]:
                    vow_stats[p["vow"]]["total"] += 1
                    if p["vow_achieved"]:
                        vow_stats[p["vow"]]["achieved"] += 1
        
        analysis["vow_achievement_rates"] = {
            vow: stats["achieved"] / stats["total"] if stats["total"] > 0 else 0
            for vow, stats in vow_stats.items()
        }
        
        return analysis
    
    def generate_report(self, analysis: Dict) -> str:
        """生成分析报告"""
        report = []
        report.append("=" * 60)
        report.append("《功德轮回》v5.1 平衡性分析报告")
        report.append(f"模拟局数: {self.num_simulations}")
        report.append("=" * 60)
        
        # 团队胜率
        report.append(f"\n【团队胜率】: {analysis['team_win_rate']:.1%}")
        report.append(f"  - 理想范围: 50%-70%")
        if analysis['team_win_rate'] < 0.5:
            report.append("  ⚠️ 游戏过难，建议降低劫难压力或增加资源")
        elif analysis['team_win_rate'] > 0.7:
            report.append("  ⚠️ 游戏过易，建议增加劫难压力或减少资源")
        else:
            report.append("  ✅ 团队难度适中")
        
        # 职业胜率
        report.append("\n【职业个人胜率】(团队胜利时第一名概率):")
        for role, rate in sorted(analysis['role_win_rates'].items()):
            status = "✅" if 0.2 <= rate <= 0.35 else "⚠️"
            report.append(f"  {role}: {rate:.1%} {status}")
        
        # 职业平均得分
        report.append("\n【职业平均得分】:")
        for role, score in sorted(analysis['role_avg_scores'].items()):
            report.append(f"  {role}: {score:.1f}")
        
        # 发愿达成率
        report.append("\n【发愿达成率】:")
        for vow, rate in sorted(analysis['vow_achievement_rates'].items()):
            difficulty = "简单" if rate >= 0.7 else ("中等" if rate >= 0.4 else "困难")
            report.append(f"  {vow}: {rate:.1%} ({difficulty})")
        
        # 资源经济
        report.append("\n【资源经济】(游戏结束时平均值):")
        for resource, data in analysis['resource_economy'].items():
            report.append(f"  {resource}:")
            for role, value in sorted(data.items()):
                report.append(f"    {role}: {value:.1f}")
        
        # 紧张度
        report.append("\n【游戏紧张度】:")
        tension = analysis['tension']
        report.append(f"  平均劫难余量: {tension['avg_calamity_margin']:.1f}")
        report.append(f"  紧张局 (余量≤4): {tension['tight_games']:.1%}")
        report.append(f"  轻松局 (余量≥10): {tension['comfortable_games']:.1%}")
        
        if tension['comfortable_games'] > 0.5:
            report.append("  ⚠️ 游戏紧张度不足，玩家可能感觉无压力")
        elif tension['tight_games'] > 0.5:
            report.append("  ⚠️ 游戏过于紧张，玩家可能感到压力过大")
        else:
            report.append("  ✅ 紧张度适中")
        
        # 行动使用
        report.append("\n【行动使用频率】(每局平均次数):")
        for role in sorted(analysis['action_usage'].keys()):
            actions = analysis['action_usage'][role]
            report.append(f"  {role}:")
            for action in sorted(actions.keys(), key=str):
                count = actions[action]
                report.append(f"    {action}: {count:.1f}")
        
        # 劫难统计
        report.append("\n【劫难与渡化】:")
        report.append(f"  平均最终劫难: {analysis['calamity_stats']['avg_final_calamity']:.1f}")
        report.append(f"  平均渡化数: {analysis['calamity_stats']['avg_saved']:.1f}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)

# ============ 调整版配置 ============
def get_adjusted_config_v1() -> GameConfig:
    """平衡调整v1 - 轻度调整"""
    config = GameConfig()
    config.disaster_base_calamity = 5
    config.misfortune_base_calamity = 4
    config.timeout_penalty = 5
    config.disaster_weight = 0.40
    config.misfortune_weight = 0.20
    config.blessing_weight = 0.40
    config.donate_merit_base = 1
    config.donate_merchant_bonus = 1
    config.being_costs = [3, 3, 4, 4, 4, 5, 5, 6, 3, 5]
    config.survival_cost = 2
    config.vow_bodhisattva_merit = 12
    config.vow_bodhisattva_save = 2
    return config

def get_adjusted_config_v2() -> GameConfig:
    """平衡调整v2 - 中度调整（目标团队胜率60%）"""
    config = GameConfig()
    
    # 大幅增加劫难压力
    config.disaster_base_calamity = 6       # 4 -> 6
    config.misfortune_base_calamity = 5     # 3 -> 5
    config.timeout_penalty = 6              # 4 -> 6
    
    # 大幅增加灾难事件比例
    config.disaster_weight = 0.50           # 0.33 -> 0.50
    config.misfortune_weight = 0.25         # 0.17 -> 0.25
    config.blessing_weight = 0.25           # 0.50 -> 0.25
    
    # 减少功德来源
    config.donate_merit_base = 1
    config.donate_merchant_bonus = 1
    config.donate_faith_bonus = 0           # 皈依者布施不再额外+1
    
    # 减少发愿每回合奖励
    config.vow_farmer_merit_per_round = 0   # 农夫不再每回合+1功德
    
    # 增加渡化成本
    config.being_costs = [4, 4, 5, 5, 5, 6, 6, 7, 4, 6]  # 整体+2
    
    # 增加生存消耗
    config.survival_cost = 2
    
    # 调整发愿条件
    config.vow_diligent_merit = 16          # 降低
    config.vow_poor_girl_merit = 22
    config.vow_bodhisattva_merit = 10
    config.vow_bodhisattva_save = 2
    
    # 减少初始资源
    config.init_farmer = (4, 2, 2)          # 资粮-1
    config.init_merchant = (7, 2, 1)        # 资粮-2
    config.init_scholar = (3, 2, 4)         # 资粮-1，慧-1
    config.init_monk = (0, 4, 4)            # 功德-1，慧-1
    
    return config

def get_adjusted_config_v3() -> GameConfig:
    """平衡调整v3 - 激进调整（测试极端）"""
    config = get_adjusted_config_v2()
    config.disaster_base_calamity = 7
    config.misfortune_base_calamity = 6
    config.disaster_weight = 0.55
    config.misfortune_weight = 0.30
    config.blessing_weight = 0.15
    return config

def get_v52_final_config() -> GameConfig:
    """v5.2 最终平衡配置"""
    config = GameConfig()
    
    # 劫难压力增加
    config.disaster_base_calamity = 6
    config.misfortune_base_calamity = 5
    config.timeout_penalty = 5
    
    # 事件权重
    config.disaster_weight = 0.50
    config.misfortune_weight = 0.25
    config.blessing_weight = 0.25
    
    # 功德来源调整
    config.donate_merit_base = 1
    config.donate_merchant_bonus = 2
    config.donate_faith_bonus = 0  # 移除皈依加成
    config.vow_farmer_merit_per_round = 0  # 移除农夫每回合功德
    
    # 护法增强
    config.protect_merit = 2
    config.protect_calamity_reduce = 3
    
    # 学者削弱
    config.practice_scholar_bonus = 1  # 2 -> 1
    
    # 渡化成本
    config.being_costs = [3, 3, 4, 4, 4, 5, 5, 6, 3, 5]
    
    # 发愿条件
    config.vow_diligent_merit = 18
    config.vow_poor_girl_merit = 22
    config.vow_arhat_hui = 16
    config.vow_bodhisattva_merit = 8   # 进一步降低
    config.vow_bodhisattva_save = 1    # 进一步降低
    
    # 初始资源
    config.init_farmer = (4, 2, 2)
    config.init_merchant = (8, 2, 1)
    config.init_monk = (1, 6, 5)
    
    return config

def get_final_balanced_v1() -> GameConfig:
    """最终平衡版v1 - 目标65%胜率"""
    config = GameConfig()
    
    # 劫难伤害增加
    config.disaster_base_calamity = 6       # 4->6
    config.misfortune_base_calamity = 4     # 3->4
    config.timeout_penalty = 5
    
    # 事件权重
    config.disaster_weight = 0.45
    config.misfortune_weight = 0.20
    config.blessing_weight = 0.35
    
    # 功德调整
    config.donate_merit_base = 2            # 保持
    config.donate_merchant_bonus = 2        # 保持
    config.donate_faith_bonus = 1           # 保持
    config.vow_farmer_merit_per_round = 0   # 取消农夫每回合功德
    
    # 渡化成本
    config.being_costs = [3, 3, 4, 4, 4, 5, 5, 6, 3, 5]
    
    # 发愿
    config.vow_diligent_merit = 18
    config.vow_poor_girl_merit = 22
    config.vow_bodhisattva_merit = 12
    config.vow_bodhisattva_save = 2
    config.vow_arhat_hui = 12
    
    # 初始资源
    config.init_farmer = (4, 2, 2)
    config.init_monk = (1, 6, 5)
    
    return config

def get_final_balanced_v2() -> GameConfig:
    """最终平衡版v2 - 目标60%胜率"""
    config = get_final_balanced_v1()
    config.disaster_base_calamity = 6
    config.misfortune_base_calamity = 5     # 增加
    config.disaster_weight = 0.48
    config.misfortune_weight = 0.22
    config.blessing_weight = 0.30
    return config

def get_final_balanced_v3() -> GameConfig:
    """最终平衡版v3 - 目标55%胜率"""
    config = get_final_balanced_v2()
    config.disaster_base_calamity = 6
    config.misfortune_base_calamity = 5
    config.disaster_weight = 0.50
    config.misfortune_weight = 0.25
    config.blessing_weight = 0.25
    # 减少初始资源
    config.init_merchant = (8, 2, 1)        # 9->8
    return config

def get_test_config(disaster_weight: float) -> GameConfig:
    """测试不同灾难权重的配置"""
    config = GameConfig()
    
    # 劫难压力（保持固定）
    config.disaster_base_calamity = 5
    config.misfortune_base_calamity = 4
    config.timeout_penalty = 5
    
    # 可变事件权重
    config.disaster_weight = disaster_weight
    config.misfortune_weight = 0.20
    config.blessing_weight = 1.0 - disaster_weight - 0.20
    
    # 功德调整（固定）
    config.donate_merit_base = 1
    config.donate_merchant_bonus = 2
    config.donate_faith_bonus = 0
    config.vow_farmer_merit_per_round = 0
    
    # 渡化成本
    config.being_costs = [3, 3, 4, 4, 4, 5, 5, 6, 3, 5]
    
    # 发愿调整
    config.vow_diligent_merit = 16
    config.vow_poor_girl_merit = 20
    config.vow_bodhisattva_merit = 10
    config.vow_bodhisattva_save = 2
    config.vow_arhat_hui = 12
    
    # 初始资源
    config.init_farmer = (4, 2, 2)
    config.init_monk = (1, 6, 5)
    
    return config

def get_balanced_60_config() -> GameConfig:
    """目标团队胜率60%的平衡配置"""
    config = GameConfig()
    
    # 劫难压力
    config.disaster_base_calamity = 5
    config.misfortune_base_calamity = 4
    config.timeout_penalty = 5
    
    # 事件权重（增加灾难）
    config.disaster_weight = 0.48
    config.misfortune_weight = 0.22
    config.blessing_weight = 0.30
    
    # 功德调整
    config.donate_merit_base = 1
    config.donate_merchant_bonus = 2
    config.donate_faith_bonus = 0  # 移除皈依加成
    config.vow_farmer_merit_per_round = 0  # 移除农夫每回合功德
    
    # 渡化成本
    config.being_costs = [3, 3, 4, 4, 4, 5, 5, 6, 3, 5]
    
    # 发愿调整
    config.vow_diligent_merit = 16
    config.vow_poor_girl_merit = 20
    config.vow_bodhisattva_merit = 10
    config.vow_bodhisattva_save = 2
    config.vow_arhat_hui = 12
    
    # 初始资源
    config.init_farmer = (4, 2, 2)
    config.init_monk = (1, 6, 5)
    
    return config

def get_balanced_65_config() -> GameConfig:
    """目标团队胜率65%的平衡配置"""
    config = get_balanced_60_config()
    
    # 略微降低劫难
    config.disaster_base_calamity = 5
    config.misfortune_base_calamity = 4
    
    # 事件权重（略增功德事件）
    config.disaster_weight = 0.45
    config.misfortune_weight = 0.20
    config.blessing_weight = 0.35
    
    return config

def get_optimized_config() -> GameConfig:
    """优化版配置 - 目标团队胜率60%，职业平衡"""
    config = GameConfig()
    
    # === 劫难压力（介于v1和v2之间）===
    config.disaster_base_calamity = 5       # 原4，v2是6
    config.misfortune_base_calamity = 4     # 原3，v2是5
    config.timeout_penalty = 5              # 原4
    
    # 事件权重
    config.disaster_weight = 0.45           # 原0.33
    config.misfortune_weight = 0.22         # 原0.17
    config.blessing_weight = 0.33           # 原0.50
    
    # === 功德来源调整 ===
    config.donate_merit_base = 1            # 2 -> 1
    config.donate_merchant_bonus = 2        # 保持商人特色：总共3功德
    config.donate_faith_bonus = 1           # 皈依者+1
    
    # 发愿每回合：保留但减少农夫
    config.vow_farmer_merit_per_round = 0   # 取消农夫每回合+1功德（太强）
    
    # === 渡化成本调整（适中）===
    config.being_costs = [3, 3, 4, 4, 4, 5, 5, 6, 3, 5]  # 整体+1
    
    # === 生存消耗 ===
    config.survival_cost = 1                # 保持原值
    
    # === 发愿条件调整 ===
    # 农夫：取消每回合功德后，降低条件
    config.vow_diligent_merit = 18          # 24 -> 18（因为没有每回合+1了）
    config.vow_poor_girl_merit = 22         # 30 -> 22
    
    # 商人：保持
    config.vow_great_merchant_merit = 16    # 18 -> 16
    
    # 僧侣：增强（太弱）
    config.vow_arhat_hui = 12               # 14 -> 12
    config.vow_bodhisattva_merit = 12       # 15 -> 12
    config.vow_bodhisattva_save = 2         # 3 -> 2
    
    # 学者：略微降低（太强）
    config.vow_teach_hui = 16               # 18 -> 16
    config.vow_teacher_hui = 16             # 18 -> 16
    
    # === 初始资源调整 ===
    # 增强僧侣，削弱农夫
    config.init_farmer = (4, 2, 2)          # 资粮5 -> 4
    config.init_merchant = (9, 2, 1)        # 保持
    config.init_scholar = (4, 2, 5)         # 保持
    config.init_monk = (1, 6, 5)            # 功德5 -> 6
    
    return config

# ============ 主函数 ============
def main():
    print("Starting multi-config balance simulation...\n")
    
    configs = {
        "v52_final": get_v52_final_config(),
    }
    
    results = {}
    
    for name, config in configs.items():
        print(f"=== Testing {name} config ===")
        analyzer = BalanceAnalyzer(num_simulations=3000)
        analyzer.run_simulations(config)
        analysis = analyzer.analyze()
        report = analyzer.generate_report(analysis)
        
        with open(f"balance_report_{name}.txt", "w", encoding="utf-8") as f:
            f.write(report)
        
        results[name] = {
            "team_win_rate": analysis["team_win_rate"],
            "avg_calamity_margin": analysis["tension"]["avg_calamity_margin"],
            "tight_games": analysis["tension"]["tight_games"],
            "role_win_rates": analysis["role_win_rates"],
            "vow_rates": analysis["vow_achievement_rates"]
        }
        print(f"  Team Win Rate: {analysis['team_win_rate']:.1%}")
        print(f"  Avg Calamity Margin: {analysis['tension']['avg_calamity_margin']:.1f}")
        print(f"  Tight Games: {analysis['tension']['tight_games']:.1%}\n")
    
    # 保存汇总
    with open("balance_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n=== SUMMARY ===")
    print(f"{'Config':<15} {'Win Rate':>10} {'Margin':>10} {'Tight%':>10}")
    print("-" * 50)
    for name, data in results.items():
        print(f"{name:<15} {data['team_win_rate']:>10.1%} {data['avg_calamity_margin']:>10.1f} {data['tight_games']:>10.1%}")
    
    return results

if __name__ == "__main__":
    main()
