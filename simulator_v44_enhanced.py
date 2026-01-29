# -*- coding: utf-8 -*-
"""
《功德轮回：众生百态》v4.4 增强版蒙特卡洛模拟器
- 详细统计每个机制的贡献
- 支持参数化调优
- 多轮迭代测试
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

# ============ 可调参数 ============
@dataclass
class GameConfig:
    """游戏参数配置"""
    # 胜利条件
    calamity_limit: int = 20
    calamity_win_threshold: int = 12
    save_target: int = 5
    max_rounds: int = 6
    
    # 初始资源 [财富, 福, 慧]
    init_farmer: Tuple[int, int, int] = (5, 2, 2)
    init_merchant: Tuple[int, int, int] = (8, 1, 1)
    init_scholar: Tuple[int, int, int] = (3, 1, 4)
    init_monk: Tuple[int, int, int] = (0, 3, 3)
    
    # 信仰收益
    secular_wealth_bonus: int = 4
    small_vehicle_fu_bonus: int = 1
    small_vehicle_hui_bonus: int = 1
    great_vehicle_wealth_cost: int = 2
    great_vehicle_hui_bonus: int = 1
    
    # 行动收益
    labor_base: int = 3
    labor_farmer_bonus: int = 1
    labor_secular_bonus: int = 1
    practice_base: int = 2
    practice_scholar_bonus: int = 1
    donate_cost: int = 2
    donate_fu_base: int = 2
    
    # 发愿条件
    vow_diligent_fu: int = 15
    vow_poor_girl_fu: int = 20
    vow_poor_girl_wealth: int = 5
    vow_wealth_merit_count: int = 3
    vow_great_merchant_fu: int = 18
    vow_great_merchant_save: int = 2
    vow_teach_hui: int = 18
    vow_teacher_fu: int = 15
    vow_teacher_hui: int = 22
    vow_arhat_hui: int = 22
    vow_bodhisattva_fu: int = 18
    vow_bodhisattva_save: int = 3
    
    # 发愿奖励/惩罚
    vow_simple_reward: int = 12
    vow_simple_penalty: int = 4
    vow_hard_reward: int = 16
    vow_hard_penalty: int = 6
    
    # 劫难
    disaster_calamity: int = 4
    misfortune_calamity: int = 2
    timeout_penalty: int = 4
    calamity_per_round: int = 1
    
    # 事件权重
    disaster_weight: float = 0.4
    misfortune_weight: float = 0.2
    blessing_weight: float = 0.4

@dataclass
class Player:
    role: Role
    faith: FaithState = FaithState.SECULAR
    wealth: int = 0
    fu: int = 0
    hui: int = 0
    vow: Optional[Vow] = None
    bodhisattva_vow: Optional[BodhisattvaVow] = None
    
    # 追踪
    donate_count: int = 0
    save_count: int = 0
    help_count: int = 0
    skill_uses: int = 2
    puxian_supply: int = 0
    guanyin_helped: set = field(default_factory=set)
    
    # 详细统计
    wealth_from_labor: int = 0
    wealth_from_events: int = 0
    fu_from_vow: int = 0
    fu_from_donate: int = 0
    fu_from_save: int = 0
    fu_from_events: int = 0
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
        if total < 10:
            base = 10
        elif total < 15:
            base = 15
        elif total < 20:
            base = 25
        elif total < 25:
            base = 35
        elif total < 30:
            base = 45
        elif total < 35:
            base = 55
        else:
            base = 65
        
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

@dataclass
class Being:
    name: str
    cost: int
    fu_reward: int
    hui_reward: int
    stay_rounds: int = 0

class GameSimulator:
    def __init__(self, config: GameConfig = None):
        self.config = config or GameConfig()
        self.beings_pool = self._create_beings()
        
    def _create_beings(self) -> List[Being]:
        return [
            Being("饥民", 2, 2, 1),
            Being("病者", 2, 2, 1),
            Being("孤儿", 3, 3, 1),
            Being("寡妇", 3, 2, 2),
            Being("落魄书生", 3, 1, 3),
            Being("迷途商贾", 4, 2, 2),
            Being("悔过恶人", 4, 4, 1),
            Being("垂死老者", 5, 3, 3),
            Being("被弃婴儿", 2, 3, 0),
            Being("绝望猎人", 4, 2, 2),
        ]
    
    def create_game(self) -> Dict:
        roles = list(Role)
        random.shuffle(roles)
        players = []
        
        for i, role in enumerate(roles[:4]):
            player = Player(role=role)
            player.init_resources(self.config)
            
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
            
            player.vow = self._choose_vow(role)
            
            if player.faith == FaithState.GREAT_VEHICLE:
                player.bodhisattva_vow = random.choice(list(BodhisattvaVow))
            
            players.append(player)
        
        beings_deck = [copy.copy(b) for b in self.beings_pool]
        random.shuffle(beings_deck)
        active_beings = [beings_deck.pop(), beings_deck.pop()]
        
        return {
            "players": players,
            "current_round": 1,
            "calamity": 0,
            "saved_count": 0,
            "active_beings": active_beings,
            "beings_deck": beings_deck,
            "events_log": [],
            "stats": {
                "disaster_count": 0,
                "misfortune_count": 0,
                "blessing_count": 0,
                "timeout_count": 0,
                "total_calamity_added": 0,
                "total_calamity_reduced": 0,
            }
        }
    
    def _choose_vow(self, role: Role) -> Vow:
        vow_map = {
            Role.FARMER: [Vow.DILIGENT_FORTUNE, Vow.POOR_GIRL_LAMP],
            Role.MERCHANT: [Vow.WEALTH_MERIT, Vow.GREAT_MERCHANT],
            Role.SCHOLAR: [Vow.TEACH_WISDOM, Vow.TEACHER_MODEL],
            Role.MONK: [Vow.ARHAT, Vow.BODHISATTVA],
        }
        return random.choices(vow_map[role], weights=[0.5, 0.5])[0]
    
    def vow_reward_phase(self, game: Dict):
        for p in game["players"]:
            if p.vow in [Vow.DILIGENT_FORTUNE, Vow.POOR_GIRL_LAMP]:
                p.fu += 1
                p.fu_from_vow += 1
            elif p.vow == Vow.WEALTH_MERIT:
                p.wealth += 1
            elif p.vow in [Vow.GREAT_MERCHANT, Vow.TEACH_WISDOM, Vow.TEACHER_MODEL, Vow.ARHAT]:
                p.hui += 1
                p.hui_from_vow += 1
            elif p.vow == Vow.BODHISATTVA:
                p.fu += 1
                p.fu_from_vow += 1
    
    def collective_event_phase(self, game: Dict):
        event_type = random.choices(
            ["disaster", "misfortune", "blessing"],
            weights=[self.config.disaster_weight, self.config.misfortune_weight, self.config.blessing_weight]
        )[0]
        
        if event_type == "disaster":
            self._disaster_event(game)
            game["stats"]["disaster_count"] += 1
        elif event_type == "misfortune":
            self._misfortune_event(game)
            game["stats"]["misfortune_count"] += 1
        else:
            self._blessing_event(game)
            game["stats"]["blessing_count"] += 1
    
    def _disaster_event(self, game: Dict):
        event_name = random.choice(["旱魃肆虐", "洪水滔天", "瘟疫流行", "蝗灾蔽日"])
        game["events_log"].append(f"R{game['current_round']}: {event_name}")
        
        choices = []
        for p in game["players"]:
            choice = self._decide_disaster_choice(p, game, event_name)
            choices.append(choice)
        
        a_count = choices.count("A")
        b_count = choices.count("B")
        
        calamity_add = self.config.disaster_calamity
        game["calamity"] += calamity_add
        game["stats"]["total_calamity_added"] += calamity_add
        
        if event_name == "旱魃肆虐":
            for i, p in enumerate(game["players"]):
                if choices[i] == "A":
                    p.wealth -= 3
                    if a_count >= 2:
                        p.fu += 1
                        p.fu_from_events += 1
                else:
                    p.wealth -= 1
            if a_count >= 2:
                game["calamity"] -= 1
                game["stats"]["total_calamity_reduced"] += 1
            if b_count >= 2:
                game["calamity"] += 1
                game["stats"]["total_calamity_added"] += 1
                
        elif event_name == "洪水滔天":
            for i, p in enumerate(game["players"]):
                if choices[i] == "A":
                    p.wealth -= 2
                    p.fu += 2
                    p.fu_from_events += 2
                else:
                    p.hui += 1
                    p.hui_from_events += 1
                    p.fu -= 1
                    
        elif event_name == "瘟疫流行":
            game["calamity"] += 1
            game["stats"]["total_calamity_added"] += 1
            for i, p in enumerate(game["players"]):
                if choices[i] == "A":
                    roll = random.randint(1, 6)
                    if roll <= 2:
                        p.fu -= 2
                    else:
                        p.fu += 2
                        p.hui += 1
                        p.fu_from_events += 2
                        p.hui_from_events += 1
                else:
                    p.hui += 2
                    p.hui_from_events += 2
                    p.fu -= 1
                    
        elif event_name == "蝗灾蔽日":
            for i, p in enumerate(game["players"]):
                if choices[i] == "A":
                    p.wealth -= 2
                    p.fu += a_count
                    p.fu_from_events += a_count
                else:
                    p.wealth += 2
                    p.wealth_from_events += 2
                    game["calamity"] += 1
                    game["stats"]["total_calamity_added"] += 1
            if a_count == len(game["players"]):
                game["calamity"] -= 2
                game["stats"]["total_calamity_reduced"] += 2
                for p in game["players"]:
                    p.hui += 1
                    p.hui_from_events += 1
    
    def _decide_disaster_choice(self, player: Player, game: Dict, event: str) -> str:
        calamity_critical = game["calamity"] >= 10
        
        if player.faith == FaithState.GREAT_VEHICLE:
            return "A" if random.random() > 0.3 else "B"
        
        if calamity_critical:
            return "A" if random.random() > 0.4 else "B"
        
        if player.wealth <= 3:
            return "B" if random.random() > 0.4 else "A"
        
        return random.choice(["A", "B"])
    
    def _misfortune_event(self, game: Dict):
        event_name = random.choice(["苛政如虎", "战火将至"])
        game["events_log"].append(f"R{game['current_round']}: {event_name}")
        
        calamity_add = self.config.misfortune_calamity
        game["calamity"] += calamity_add
        game["stats"]["total_calamity_added"] += calamity_add
        
        choices = []
        for p in game["players"]:
            choice = "A" if random.random() > 0.5 else "B"
            choices.append(choice)
        
        a_count = choices.count("A")
        
        if event_name == "苛政如虎":
            for i, p in enumerate(game["players"]):
                if choices[i] == "A":
                    if a_count >= 2:
                        p.wealth += 2
                        p.fu += 1
                        p.wealth_from_events += 2
                        p.fu_from_events += 1
                    else:
                        p.wealth -= 3
                else:
                    p.wealth -= 1
                    p.hui += 1
                    p.hui_from_events += 1
            if a_count >= 2:
                game["calamity"] -= 2
                game["stats"]["total_calamity_reduced"] += 2
    
    def _blessing_event(self, game: Dict):
        event_name = random.choice(["风调雨顺", "国泰民安", "浴佛盛会", "盂兰盆节", "高僧讲经", "舍利现世"])
        game["events_log"].append(f"R{game['current_round']}: {event_name}")
        
        if event_name == "风调雨顺":
            for p in game["players"]:
                p.wealth += 1
                p.wealth_from_events += 1
        elif event_name == "国泰民安":
            game["calamity"] -= 1
            game["stats"]["total_calamity_reduced"] += 1
        elif event_name == "浴佛盛会":
            for p in game["players"]:
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
        elif event_name == "舍利现世":
            for p in game["players"]:
                p.fu += 1
                p.fu_from_events += 1
    
    def beings_phase(self, game: Dict):
        for being in game["active_beings"]:
            being.stay_rounds += 1
        
        timeout_beings = [b for b in game["active_beings"] if b.stay_rounds >= 2]
        for b in timeout_beings:
            game["calamity"] += self.config.timeout_penalty
            game["stats"]["total_calamity_added"] += self.config.timeout_penalty
            game["stats"]["timeout_count"] += 1
            game["active_beings"].remove(b)
        
        if game["beings_deck"]:
            game["active_beings"].append(game["beings_deck"].pop())
    
    def action_phase(self, game: Dict):
        for p in game["players"]:
            actions_left = 2
            
            while actions_left > 0:
                action = self._decide_action(p, game)
                
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
                else:
                    break
                
                actions_left -= 1
    
    def _decide_action(self, player: Player, game: Dict) -> str:
        if game["calamity"] >= 15 and player.wealth >= 2:
            return "protect"
        
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
    
    def _can_afford_being(self, player: Player, being: Being) -> bool:
        cost = being.cost
        
        if player.role == Role.MERCHANT:
            cost += 1
        elif player.role == Role.SCHOLAR:
            cost -= 1
        elif player.role == Role.MONK:
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
            fu_gain += 1
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
            game["calamity"] -= 1
            game["stats"]["total_calamity_reduced"] += 1
        
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
        game["calamity"] -= 2
        game["stats"]["total_calamity_reduced"] += 2
        player.help_count += 1
    
    def settlement_phase(self, game: Dict):
        game["calamity"] += self.config.calamity_per_round
        game["stats"]["total_calamity_added"] += self.config.calamity_per_round
        
        if game["current_round"] % 2 == 0:
            for p in game["players"]:
                if p.wealth >= 1:
                    p.wealth -= 1
                else:
                    p.fu -= 1
        
        for p in game["players"]:
            if p.bodhisattva_vow == BodhisattvaVow.PUXIAN:
                if p.wealth >= 1:
                    p.wealth -= 1
                    p.puxian_supply += 1
    
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
            
            if round_num % 2 == 1:
                for p in game["players"]:
                    effect = random.choice(["fu+1", "hui+1", "wealth+1", "none"])
                    if effect == "fu+1":
                        p.fu += 1
                        p.fu_from_events += 1
                    elif effect == "hui+1":
                        p.hui += 1
                        p.hui_from_events += 1
                    elif effect == "wealth+1":
                        p.wealth += 1
                        p.wealth_from_events += 1
            
            self.beings_phase(game)
            self.action_phase(game)
            self.settlement_phase(game)
            
            ended, team_win = self.check_game_end(game)
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
                "bodhisattva_vow": p.bodhisattva_vow.value if p.bodhisattva_vow else None,
                "fu": p.fu,
                "hui": p.hui,
                "wealth": p.wealth,
                "base_score": base_score,
                "vow_bonus": vow_reward - vow_penalty,
                "bodhi_bonus": bodhi_reward - bodhi_penalty,
                "final_score": final_score,
                "save_count": p.save_count,
                "donate_count": p.donate_count,
                # 详细来源统计
                "wealth_from_labor": p.wealth_from_labor,
                "wealth_from_events": p.wealth_from_events,
                "fu_from_vow": p.fu_from_vow,
                "fu_from_donate": p.fu_from_donate,
                "fu_from_save": p.fu_from_save,
                "fu_from_events": p.fu_from_events,
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
            "events": game["events_log"],
            "stats": game["stats"]
        }
    
    def run_simulation(self, num_games: int = 1000) -> Dict:
        all_results = []
        
        team_wins = 0
        role_wins = defaultdict(int)
        faith_wins = defaultdict(int)
        vow_success = defaultdict(lambda: {"success": 0, "total": 0})
        role_scores = defaultdict(list)
        faith_scores = defaultdict(list)
        
        # 详细来源统计
        role_fu_sources = defaultdict(lambda: {"vow": 0, "donate": 0, "save": 0, "events": 0, "count": 0})
        role_hui_sources = defaultdict(lambda: {"practice": 0, "vow": 0, "events": 0, "count": 0})
        role_wealth_sources = defaultdict(lambda: {"labor": 0, "events": 0, "count": 0})
        
        # 发愿详细统计
        vow_final_values = defaultdict(list)
        
        # 事件统计
        total_stats = defaultdict(int)
        
        for i in range(num_games):
            result = self.run_game()
            all_results.append(result)
            
            if result["team_win"]:
                team_wins += 1
                if result["winner"]:
                    role_wins[result["winner"]] += 1
            
            for s, v in result["stats"].items():
                total_stats[s] += v
            
            for p in result["players"]:
                role_scores[p["role"]].append(p["final_score"])
                faith_scores[p["faith"]].append(p["final_score"])
                
                if result["team_win"]:
                    if p["role"] == result["winner"]:
                        faith_wins[p["faith"]] += 1
                
                if p["vow"]:
                    vow_success[p["vow"]]["total"] += 1
                    if p["vow_bonus"] > 0:
                        vow_success[p["vow"]]["success"] += 1
                    
                    # 记录发愿相关的最终值
                    if p["vow"] in ["勤劳致福", "贫女一灯"]:
                        vow_final_values[p["vow"]].append(p["fu"])
                    elif p["vow"] in ["传道授业", "万世师表", "阿罗汉果"]:
                        vow_final_values[p["vow"]].append(p["hui"])
                
                # 来源统计
                role_fu_sources[p["role"]]["vow"] += p["fu_from_vow"]
                role_fu_sources[p["role"]]["donate"] += p["fu_from_donate"]
                role_fu_sources[p["role"]]["save"] += p["fu_from_save"]
                role_fu_sources[p["role"]]["events"] += p["fu_from_events"]
                role_fu_sources[p["role"]]["count"] += 1
                
                role_hui_sources[p["role"]]["practice"] += p["hui_from_practice"]
                role_hui_sources[p["role"]]["vow"] += p["hui_from_vow"]
                role_hui_sources[p["role"]]["events"] += p["hui_from_events"]
                role_hui_sources[p["role"]]["count"] += 1
                
                role_wealth_sources[p["role"]]["labor"] += p["wealth_from_labor"]
                role_wealth_sources[p["role"]]["events"] += p["wealth_from_events"]
                role_wealth_sources[p["role"]]["count"] += 1
        
        # 计算平均来源
        for role in role_fu_sources:
            c = role_fu_sources[role]["count"]
            if c > 0:
                for k in ["vow", "donate", "save", "events"]:
                    role_fu_sources[role][k] /= c
        
        for role in role_hui_sources:
            c = role_hui_sources[role]["count"]
            if c > 0:
                for k in ["practice", "vow", "events"]:
                    role_hui_sources[role][k] /= c
        
        for role in role_wealth_sources:
            c = role_wealth_sources[role]["count"]
            if c > 0:
                for k in ["labor", "events"]:
                    role_wealth_sources[role][k] /= c
        
        analysis = {
            "version": "v4.4-enhanced",
            "total_games": num_games,
            "team_win_rate": team_wins / num_games * 100,
            "avg_calamity": sum(r["calamity"] for r in all_results) / num_games,
            "avg_saved": sum(r["saved_count"] for r in all_results) / num_games,
            
            "role_win_rates": {k: v / team_wins * 100 if team_wins > 0 else 0 
                              for k, v in role_wins.items()},
            "role_avg_scores": {k: sum(v) / len(v) if v else 0 
                               for k, v in role_scores.items()},
            
            "faith_win_rates": {k: v / team_wins * 100 if team_wins > 0 else 0 
                               for k, v in faith_wins.items()},
            "faith_avg_scores": {k: sum(v) / len(v) if v else 0 
                                for k, v in faith_scores.items()},
            
            "vow_success_rates": {k: v["success"] / v["total"] * 100 if v["total"] > 0 else 0 
                                  for k, v in vow_success.items()},
            "vow_avg_final_values": {k: sum(v) / len(v) if v else 0 
                                     for k, v in vow_final_values.items()},
            
            "role_fu_sources": dict(role_fu_sources),
            "role_hui_sources": dict(role_hui_sources),
            "role_wealth_sources": dict(role_wealth_sources),
            
            "event_stats": {k: v / num_games for k, v in total_stats.items()},
        }
        
        return analysis

def print_detailed_report(results: Dict, config: GameConfig):
    """打印详细分析报告"""
    print("=" * 70)
    print("《功德轮回》v4.4 平衡性详细分析报告")
    print("=" * 70)
    print()
    
    print(f"[基础数据] 模拟{results['total_games']}局")
    print("-" * 50)
    print(f"  团队胜率: {results['team_win_rate']:.1f}%")
    print(f"  平均劫难: {results['avg_calamity']:.1f}")
    print(f"  平均渡化: {results['avg_saved']:.1f}")
    print()
    
    print("[职业胜率与平均分]")
    print("-" * 50)
    for role in ["农夫", "商人", "学者", "僧侣"]:
        rate = results["role_win_rates"].get(role, 0)
        score = results["role_avg_scores"].get(role, 0)
        bar = "#" * int(rate / 2)
        print(f"  {role}: 胜率{rate:5.1f}% 平均分{score:5.1f} {bar}")
    print()
    
    print("[福来源分析] (每局平均)")
    print("-" * 50)
    print(f"  {'职业':<6} {'发愿':>6} {'布施':>6} {'渡化':>6} {'事件':>6} {'总计':>6}")
    for role in ["农夫", "商人", "学者", "僧侣"]:
        if role in results["role_fu_sources"]:
            s = results["role_fu_sources"][role]
            total = s["vow"] + s["donate"] + s["save"] + s["events"]
            print(f"  {role:<6} {s['vow']:>6.1f} {s['donate']:>6.1f} {s['save']:>6.1f} {s['events']:>6.1f} {total:>6.1f}")
    print()
    
    print("[慧来源分析] (每局平均)")
    print("-" * 50)
    print(f"  {'职业':<6} {'修行':>6} {'发愿':>6} {'事件':>6} {'总计':>6}")
    for role in ["农夫", "商人", "学者", "僧侣"]:
        if role in results["role_hui_sources"]:
            s = results["role_hui_sources"][role]
            total = s["practice"] + s["vow"] + s["events"]
            print(f"  {role:<6} {s['practice']:>6.1f} {s['vow']:>6.1f} {s['events']:>6.1f} {total:>6.1f}")
    print()
    
    print("[财富来源分析] (每局平均)")
    print("-" * 50)
    print(f"  {'职业':<6} {'劳作':>6} {'事件':>6}")
    for role in ["农夫", "商人", "学者", "僧侣"]:
        if role in results["role_wealth_sources"]:
            s = results["role_wealth_sources"][role]
            print(f"  {role:<6} {s['labor']:>6.1f} {s['events']:>6.1f}")
    print()
    
    print("[发愿达成率与平均值]")
    print("-" * 50)
    for vow, rate in sorted(results["vow_success_rates"].items(), key=lambda x: x[1], reverse=True):
        avg = results["vow_avg_final_values"].get(vow, "N/A")
        if isinstance(avg, float):
            print(f"  {vow:<12}: {rate:5.1f}% (平均值:{avg:.1f})")
        else:
            print(f"  {vow:<12}: {rate:5.1f}%")
    print()
    
    print("[事件统计] (每局平均)")
    print("-" * 50)
    for k, v in results["event_stats"].items():
        print(f"  {k}: {v:.2f}")
    print()
    
    print("[信仰状态分析]")
    print("-" * 50)
    for faith in ["不皈依", "小乘", "大乘"]:
        rate = results["faith_win_rates"].get(faith, 0)
        score = results["faith_avg_scores"].get(faith, 0)
        print(f"  {faith}: 胜率{rate:5.1f}% 平均分{score:5.1f}")

def run_balance_iteration(iteration: int, config: GameConfig) -> Dict:
    """运行一次平衡测试迭代"""
    print(f"\n{'='*70}")
    print(f"迭代 #{iteration}")
    print(f"{'='*70}")
    
    simulator = GameSimulator(config)
    results = simulator.run_simulation(num_games=1000)
    
    print_detailed_report(results, config)
    
    return results

def analyze_imbalance(results: Dict) -> List[str]:
    """分析不平衡原因"""
    issues = []
    
    # 检查职业胜率
    win_rates = results["role_win_rates"]
    if win_rates:
        max_rate = max(win_rates.values())
        min_rate = min(win_rates.values()) if min(win_rates.values()) > 0 else 1
        if max_rate / min_rate > 3:
            top_role = max(win_rates, key=win_rates.get)
            issues.append(f"职业不平衡: {top_role}胜率过高({max_rate:.1f}%)")
    
    # 检查发愿达成率
    vow_rates = results["vow_success_rates"]
    for vow, rate in vow_rates.items():
        if rate >= 95:
            issues.append(f"发愿过简单: {vow}达成率{rate:.1f}%")
        elif rate <= 15:
            issues.append(f"发愿过困难: {vow}达成率{rate:.1f}%")
    
    # 检查来源不平衡
    fu_sources = results["role_fu_sources"]
    for role, sources in fu_sources.items():
        if sources["vow"] > sources["donate"] + sources["save"]:
            issues.append(f"{role}福主要来自发愿({sources['vow']:.1f})，行动贡献低")
    
    return issues

def main():
    print("=" * 70)
    print("《功德轮回》v4.4 多轮平衡性测试")
    print("=" * 70)
    
    # 初始配置
    config = GameConfig()
    
    # 迭代1: 基础测试
    results1 = run_balance_iteration(1, config)
    issues1 = analyze_imbalance(results1)
    print("\n[发现的问题]")
    for issue in issues1:
        print(f"  - {issue}")
    
    # 迭代2: 调整农夫发愿条件
    print("\n[调整] 农夫发愿条件提高: 勤劳致福 福≥18, 贫女一灯 福≥25")
    config2 = GameConfig(
        vow_diligent_fu=18,  # 原15
        vow_poor_girl_fu=25,  # 原20
    )
    results2 = run_balance_iteration(2, config2)
    issues2 = analyze_imbalance(results2)
    print("\n[发现的问题]")
    for issue in issues2:
        print(f"  - {issue}")
    
    # 迭代3: 进一步调整
    print("\n[调整] 学者发愿条件降低: 万世师表 福≥12,慧≥18")
    config3 = GameConfig(
        vow_diligent_fu=18,
        vow_poor_girl_fu=25,
        vow_teacher_fu=12,  # 原15
        vow_teacher_hui=18,  # 原22
    )
    results3 = run_balance_iteration(3, config3)
    issues3 = analyze_imbalance(results3)
    print("\n[发现的问题]")
    for issue in issues3:
        print(f"  - {issue}")
    
    # 迭代4: 调整劳作收益
    print("\n[调整] 农夫劳作奖励降低: +0 (原+1)")
    config4 = GameConfig(
        vow_diligent_fu=18,
        vow_poor_girl_fu=25,
        vow_teacher_fu=12,
        vow_teacher_hui=18,
        labor_farmer_bonus=0,  # 原1
    )
    results4 = run_balance_iteration(4, config4)
    issues4 = analyze_imbalance(results4)
    print("\n[发现的问题]")
    for issue in issues4:
        print(f"  - {issue}")
    
    # 迭代5: 综合调整
    print("\n[调整] 综合平衡: 增加学者修行奖励, 调整僧侣发愿")
    config5 = GameConfig(
        vow_diligent_fu=18,
        vow_poor_girl_fu=25,
        vow_teacher_fu=12,
        vow_teacher_hui=18,
        labor_farmer_bonus=0,
        practice_scholar_bonus=2,  # 原1
        vow_arhat_hui=18,  # 原22
        vow_bodhisattva_fu=15,  # 原18
    )
    results5 = run_balance_iteration(5, config5)
    issues5 = analyze_imbalance(results5)
    print("\n[发现的问题]")
    for issue in issues5:
        print(f"  - {issue}")
    
    # 保存最终配置
    final_config = {
        "vow_diligent_fu": config5.vow_diligent_fu,
        "vow_poor_girl_fu": config5.vow_poor_girl_fu,
        "vow_teacher_fu": config5.vow_teacher_fu,
        "vow_teacher_hui": config5.vow_teacher_hui,
        "labor_farmer_bonus": config5.labor_farmer_bonus,
        "practice_scholar_bonus": config5.practice_scholar_bonus,
        "vow_arhat_hui": config5.vow_arhat_hui,
        "vow_bodhisattva_fu": config5.vow_bodhisattva_fu,
    }
    
    with open("balance_config_final.json", "w", encoding="utf-8") as f:
        json.dump(final_config, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 70)
    print("最终推荐配置已保存到 balance_config_final.json")
    print("=" * 70)
    
    # 保存详细结果
    all_results = {
        "iteration_1": results1,
        "iteration_2": results2,
        "iteration_3": results3,
        "iteration_4": results4,
        "iteration_5": results5,
    }
    
    with open("balance_iterations.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    
    print("详细迭代结果已保存到 balance_iterations.json")

if __name__ == "__main__":
    main()
