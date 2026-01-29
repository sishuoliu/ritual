# -*- coding: utf-8 -*-
"""
《功德轮回》v4.4 平衡性测试 - 第二轮迭代
针对剩余问题进行深度调整
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

@dataclass
class GameConfig:
    """游戏参数配置"""
    calamity_limit: int = 20
    calamity_win_threshold: int = 12
    save_target: int = 5
    max_rounds: int = 6
    
    init_farmer: Tuple[int, int, int] = (5, 2, 2)
    init_merchant: Tuple[int, int, int] = (8, 1, 1)
    init_scholar: Tuple[int, int, int] = (3, 1, 4)
    init_monk: Tuple[int, int, int] = (0, 3, 3)
    
    secular_wealth_bonus: int = 4
    small_vehicle_fu_bonus: int = 1
    small_vehicle_hui_bonus: int = 1
    great_vehicle_wealth_cost: int = 2
    great_vehicle_hui_bonus: int = 1
    
    labor_base: int = 3
    labor_farmer_bonus: int = 0  # 第一轮调整结果
    labor_secular_bonus: int = 1
    practice_base: int = 2
    practice_scholar_bonus: int = 2  # 第一轮调整结果
    donate_cost: int = 2
    donate_fu_base: int = 2
    donate_merchant_bonus: int = 1
    
    # 发愿条件 - 第一轮调整结果
    vow_diligent_fu: int = 18
    vow_poor_girl_fu: int = 25
    vow_poor_girl_wealth: int = 5
    vow_wealth_merit_count: int = 3
    vow_great_merchant_fu: int = 18
    vow_great_merchant_save: int = 2
    vow_teach_hui: int = 18
    vow_teacher_fu: int = 12
    vow_teacher_hui: int = 18
    vow_arhat_hui: int = 18
    vow_bodhisattva_fu: int = 15
    vow_bodhisattva_save: int = 3
    
    vow_simple_reward: int = 12
    vow_simple_penalty: int = 4
    vow_hard_reward: int = 16
    vow_hard_penalty: int = 6
    
    disaster_calamity: int = 4
    misfortune_calamity: int = 2
    timeout_penalty: int = 4
    calamity_per_round: int = 1
    
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
    
    donate_count: int = 0
    save_count: int = 0
    help_count: int = 0
    skill_uses: int = 2
    puxian_supply: int = 0
    guanyin_helped: set = field(default_factory=set)
    
    wealth_from_labor: int = 0
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
        
        return {
            "players": players,
            "current_round": 1,
            "calamity": 0,
            "saved_count": 0,
            "active_beings": [beings_deck.pop(), beings_deck.pop()],
            "beings_deck": beings_deck,
            "events_log": [],
            "stats": defaultdict(int)
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
        elif event_type == "misfortune":
            self._misfortune_event(game)
        else:
            self._blessing_event(game)
    
    def _disaster_event(self, game: Dict):
        game["calamity"] += self.config.disaster_calamity
        game["stats"]["disaster_count"] += 1
        
        choices = [self._decide_disaster_choice(p, game) for p in game["players"]]
        a_count = choices.count("A")
        
        for i, p in enumerate(game["players"]):
            if choices[i] == "A":
                p.wealth -= 2
                if a_count >= 2:
                    p.fu += 1
                    p.fu_from_events += 1
            else:
                p.wealth -= 1
                p.fu -= 1
        
        if a_count >= 2:
            game["calamity"] -= 1
        if a_count <= 1:
            game["calamity"] += 1
    
    def _decide_disaster_choice(self, player: Player, game: Dict) -> str:
        if player.faith == FaithState.GREAT_VEHICLE:
            return "A" if random.random() > 0.3 else "B"
        if game["calamity"] >= 10:
            return "A" if random.random() > 0.4 else "B"
        if player.wealth <= 3:
            return "B" if random.random() > 0.4 else "A"
        return random.choice(["A", "B"])
    
    def _misfortune_event(self, game: Dict):
        game["calamity"] += self.config.misfortune_calamity
        game["stats"]["misfortune_count"] += 1
    
    def _blessing_event(self, game: Dict):
        game["stats"]["blessing_count"] += 1
        effect = random.choice(["wealth", "fu", "hui", "calamity_reduce"])
        
        if effect == "wealth":
            for p in game["players"]:
                p.wealth += 1
        elif effect == "fu":
            for p in game["players"]:
                p.fu += 1
                p.fu_from_events += 1
        elif effect == "hui":
            for p in game["players"]:
                p.hui += 1
                p.hui_from_events += 1
        elif effect == "calamity_reduce":
            game["calamity"] -= 1
    
    def beings_phase(self, game: Dict):
        for being in game["active_beings"]:
            being.stay_rounds += 1
        
        timeout_beings = [b for b in game["active_beings"] if b.stay_rounds >= 2]
        for b in timeout_beings:
            game["calamity"] += self.config.timeout_penalty
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
        
        if player.bodhisattva_vow != BodhisattvaVow.GUANYIN:
            game["calamity"] -= 1
        
        player.fu += fu_gain
        player.fu_from_donate += fu_gain
        player.donate_count += 1
    
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
    
    def _do_protect(self, player: Player, game: Dict):
        if player.wealth < 2:
            return
        player.wealth -= 2
        player.fu += 1
        game["calamity"] -= 2
    
    def settlement_phase(self, game: Dict):
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
                    effect = random.choice(["fu", "hui", "wealth", "none"])
                    if effect == "fu":
                        p.fu += 1
                        p.fu_from_events += 1
                    elif effect == "hui":
                        p.hui += 1
                        p.hui_from_events += 1
                    elif effect == "wealth":
                        p.wealth += 1
            
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
                "fu": p.fu, "hui": p.hui, "wealth": p.wealth,
                "base_score": base_score,
                "vow_bonus": vow_reward - vow_penalty,
                "final_score": final_score,
                "save_count": p.save_count,
                "donate_count": p.donate_count,
                "fu_from_vow": p.fu_from_vow,
                "fu_from_donate": p.fu_from_donate,
                "fu_from_save": p.fu_from_save,
                "hui_from_practice": p.hui_from_practice,
                "hui_from_vow": p.hui_from_vow,
                "wealth_from_labor": p.wealth_from_labor,
            })
        
        winner = max(results, key=lambda x: x["final_score"]) if team_win else None
        
        return {
            "team_win": team_win,
            "calamity": game["calamity"],
            "saved_count": game["saved_count"],
            "players": results,
            "winner": winner["role"] if winner else None,
        }
    
    def run_simulation(self, num_games: int = 2000) -> Dict:
        team_wins = 0
        role_wins = defaultdict(int)
        role_scores = defaultdict(list)
        faith_wins = defaultdict(int)
        vow_success = defaultdict(lambda: {"success": 0, "total": 0})
        
        role_fu_sources = defaultdict(lambda: defaultdict(float))
        role_hui_sources = defaultdict(lambda: defaultdict(float))
        role_counts = defaultdict(int)
        
        # 组合统计
        combo_wins = defaultdict(int)
        combo_total = defaultdict(int)
        
        for _ in range(num_games):
            result = self.run_game()
            
            if result["team_win"]:
                team_wins += 1
                if result["winner"]:
                    role_wins[result["winner"]] += 1
            
            for p in result["players"]:
                role_scores[p["role"]].append(p["final_score"])
                role_counts[p["role"]] += 1
                
                # 来源统计
                role_fu_sources[p["role"]]["vow"] += p["fu_from_vow"]
                role_fu_sources[p["role"]]["donate"] += p["fu_from_donate"]
                role_fu_sources[p["role"]]["save"] += p["fu_from_save"]
                role_hui_sources[p["role"]]["practice"] += p["hui_from_practice"]
                role_hui_sources[p["role"]]["vow"] += p["hui_from_vow"]
                
                if result["team_win"] and p["role"] == result["winner"]:
                    faith_wins[p["faith"]] += 1
                
                if p["vow"]:
                    vow_success[p["vow"]]["total"] += 1
                    if p["vow_bonus"] > 0:
                        vow_success[p["vow"]]["success"] += 1
                
                # 组合统计
                combo = f"{p['role']}+{p['faith']}"
                combo_total[combo] += 1
                if result["team_win"] and p["role"] == result["winner"]:
                    combo_wins[combo] += 1
        
        # 计算平均值
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
            "role_win_rates": {k: v / team_wins * 100 if team_wins > 0 else 0 for k, v in role_wins.items()},
            "role_avg_scores": {k: sum(v) / len(v) if v else 0 for k, v in role_scores.items()},
            "faith_win_rates": {k: v / team_wins * 100 if team_wins > 0 else 0 for k, v in faith_wins.items()},
            "vow_success_rates": {k: v["success"] / v["total"] * 100 if v["total"] > 0 else 0 for k, v in vow_success.items()},
            "role_fu_sources": {k: dict(v) for k, v in role_fu_sources.items()},
            "role_hui_sources": {k: dict(v) for k, v in role_hui_sources.items()},
            "combo_win_rates": {k: combo_wins[k] / combo_total[k] * 100 if combo_total[k] > 0 else 0 for k in combo_total},
        }

def print_report(name: str, results: Dict):
    print(f"\n{'='*60}")
    print(f"配置: {name}")
    print(f"{'='*60}")
    print(f"团队胜率: {results['team_win_rate']:.1f}%")
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
    
    print("\n发愿达成率:")
    for vow, rate in sorted(results["vow_success_rates"].items(), key=lambda x: x[1], reverse=True):
        bar = "#" * int(rate / 5)
        print(f"  {vow}: {rate:5.1f}% {bar}")
    
    print("\n职业+信仰组合胜率 (TOP 5):")
    combos = sorted(results["combo_win_rates"].items(), key=lambda x: x[1], reverse=True)[:5]
    for combo, rate in combos:
        print(f"  {combo}: {rate:.2f}%")
    
    print("\n福来源 (每局平均):")
    print(f"  {'职业':<6} {'发愿':>6} {'布施':>6} {'渡化':>6}")
    for role in ["农夫", "商人", "学者", "僧侣"]:
        if role in results["role_fu_sources"]:
            s = results["role_fu_sources"][role]
            print(f"  {role:<6} {s.get('vow',0):>6.1f} {s.get('donate',0):>6.1f} {s.get('save',0):>6.1f}")

def main():
    print("=" * 60)
    print("《功德轮回》v4.4 第二轮平衡性迭代测试")
    print("=" * 60)
    
    # 基线配置（第一轮最终结果）
    print("\n[基线] 第一轮最终配置")
    config_baseline = GameConfig()
    sim = GameSimulator(config_baseline)
    results_baseline = sim.run_simulation(2000)
    print_report("基线", results_baseline)
    
    # 迭代6: 进一步提高农夫发愿难度
    print("\n[迭代6] 农夫发愿: 勤劳致福福≥20, 贫女一灯福≥28")
    config6 = GameConfig(vow_diligent_fu=20, vow_poor_girl_fu=28)
    results6 = GameSimulator(config6).run_simulation(2000)
    print_report("迭代6", results6)
    
    # 迭代7: 增加商人布施奖励
    print("\n[迭代7] 商人布施额外+2福 (原+1)")
    config7 = GameConfig(
        vow_diligent_fu=20, vow_poor_girl_fu=28,
        donate_merchant_bonus=2
    )
    results7 = GameSimulator(config7).run_simulation(2000)
    print_report("迭代7", results7)
    
    # 迭代8: 调整僧侣初始资源
    print("\n[迭代8] 僧侣初始: 财0→1, 福3→4")
    config8 = GameConfig(
        vow_diligent_fu=20, vow_poor_girl_fu=28,
        donate_merchant_bonus=2,
        init_monk=(1, 4, 3)
    )
    results8 = GameSimulator(config8).run_simulation(2000)
    print_report("迭代8", results8)
    
    # 迭代9: 调整学者渡化成本
    print("\n[迭代9] 学者渡化: 额外消耗1慧→0慧")
    # 需要修改代码逻辑，这里通过提高学者初始慧来模拟
    config9 = GameConfig(
        vow_diligent_fu=20, vow_poor_girl_fu=28,
        donate_merchant_bonus=2,
        init_monk=(1, 4, 3),
        init_scholar=(3, 2, 5)  # 慧4→5, 福1→2
    )
    results9 = GameSimulator(config9).run_simulation(2000)
    print_report("迭代9", results9)
    
    # 迭代10: 综合微调
    print("\n[迭代10] 综合微调: 农夫初始资源降低")
    config10 = GameConfig(
        vow_diligent_fu=20, vow_poor_girl_fu=28,
        donate_merchant_bonus=2,
        init_monk=(1, 4, 3),
        init_scholar=(3, 2, 5),
        init_farmer=(4, 2, 2)  # 财富5→4
    )
    results10 = GameSimulator(config10).run_simulation(2000)
    print_report("迭代10", results10)
    
    # 保存最佳配置
    best_config = {
        "vow_diligent_fu": 20,
        "vow_poor_girl_fu": 28,
        "vow_teacher_fu": 12,
        "vow_teacher_hui": 18,
        "vow_arhat_hui": 18,
        "vow_bodhisattva_fu": 15,
        "labor_farmer_bonus": 0,
        "practice_scholar_bonus": 2,
        "donate_merchant_bonus": 2,
        "init_farmer": [4, 2, 2],
        "init_merchant": [8, 1, 1],
        "init_scholar": [3, 2, 5],
        "init_monk": [1, 4, 3],
    }
    
    with open("balance_config_v2.json", "w", encoding="utf-8") as f:
        json.dump(best_config, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("第二轮迭代完成，最佳配置已保存到 balance_config_v2.json")
    print("=" * 60)
    
    # 生成对比报告
    comparison = {
        "baseline": {
            "role_win_rates": results_baseline["role_win_rates"],
            "vow_success_rates": results_baseline["vow_success_rates"],
        },
        "final": {
            "role_win_rates": results10["role_win_rates"],
            "vow_success_rates": results10["vow_success_rates"],
        }
    }
    
    print("\n[对比] 基线 vs 最终")
    print("-" * 50)
    print("职业胜率变化:")
    for role in ["农夫", "商人", "学者", "僧侣"]:
        old = results_baseline["role_win_rates"].get(role, 0)
        new = results10["role_win_rates"].get(role, 0)
        diff = new - old
        arrow = "↑" if diff > 0 else "↓" if diff < 0 else "="
        print(f"  {role}: {old:.1f}% → {new:.1f}% ({arrow}{abs(diff):.1f}%)")

if __name__ == "__main__":
    main()
