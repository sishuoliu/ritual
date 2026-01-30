# -*- coding: utf-8 -*-
"""
《救赎之路》v2.9 骰子系统版
新增四种骰子机制增加随机性和趣味性

骰子系统：
1. 业力骰 - 每轮开始，决定运势
2. 因缘骰 - 玩家互动时，决定缘分深浅
3. 修行骰 - 功德行动时，决定成效
4. 无常骰 - 生命阶段，可能触发顿悟
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from enum import Enum
import json
import time

class Role(Enum):
    MERCHANT = "富商"
    LANDLORD = "地主"
    OFFICIAL = "官员"
    FARMER = "农民"
    WIDOW = "寡妇"
    MONK = "僧侣"

class DiceResult(Enum):
    """骰子结果枚举"""
    # 业力骰结果
    KARMA_ADVERSE = "逆境"      # 1-2
    KARMA_NORMAL = "平常"       # 3-4  
    KARMA_FAVORABLE = "顺缘"    # 5-6
    
    # 修行骰结果
    PRACTICE_FAIL = "修行受阻"      # 1
    PRACTICE_NORMAL = "修行平常"    # 2-4
    PRACTICE_SUCCESS = "修行精进"   # 5
    PRACTICE_ENLIGHTEN = "大彻大悟" # 6
    
    # 因缘骰结果
    FATE_SHALLOW = "缘浅"       # 1-2
    FATE_NORMAL = "普通因缘"    # 3-4
    FATE_DEEP = "深厚因缘"      # 5-6
    
    # 无常骰结果
    IMPERM_NOTHING = "无事"        # 1-3
    IMPERM_AWAKENING = "顿悟"      # 4-5
    IMPERM_EPIPHANY = "大顿悟"     # 6

def roll_d6() -> int:
    """掷一个六面骰"""
    return random.randint(1, 6)

def roll_karma_dice() -> Tuple[int, DiceResult]:
    """业力骰：决定本轮运势"""
    result = roll_d6()
    if result <= 2:
        return result, DiceResult.KARMA_ADVERSE
    elif result <= 4:
        return result, DiceResult.KARMA_NORMAL
    else:
        return result, DiceResult.KARMA_FAVORABLE

def roll_practice_dice() -> Tuple[int, DiceResult]:
    """修行骰：决定修行成效"""
    result = roll_d6()
    if result == 1:
        return result, DiceResult.PRACTICE_FAIL
    elif result <= 4:
        return result, DiceResult.PRACTICE_NORMAL
    elif result == 5:
        return result, DiceResult.PRACTICE_SUCCESS
    else:  # 6
        return result, DiceResult.PRACTICE_ENLIGHTEN

def roll_fate_dice() -> Tuple[int, DiceResult]:
    """因缘骰：决定与他人互动效果"""
    result = roll_d6()
    if result <= 2:
        return result, DiceResult.FATE_SHALLOW
    elif result <= 4:
        return result, DiceResult.FATE_NORMAL
    else:
        return result, DiceResult.FATE_DEEP

def roll_impermanence_dice() -> Tuple[int, DiceResult]:
    """无常骰：可能触发顿悟"""
    result = roll_d6()
    if result <= 3:
        return result, DiceResult.IMPERM_NOTHING
    elif result <= 5:
        return result, DiceResult.IMPERM_AWAKENING
    else:  # 6
        return result, DiceResult.IMPERM_EPIPHANY

@dataclass
class Player:
    role: Role
    grain: int = 0
    coins: int = 0
    land: int = 0
    merit: int = 0
    reputation: int = 0
    dharma_power: int = 0
    grant_points: int = 0
    life: int = 10
    action_points: int = 2
    awakening_tokens: int = 0
    retreat_mode: bool = False
    
    # 本轮业力状态
    karma_state: DiceResult = None
    
    # 专属状态
    bodhisattva_mode: bool = False
    liberation_turn: int = 0
    salvation_points: int = 0
    beings_saved: int = 0
    saved_players: Set = field(default_factory=set)
    
    charity_mode: bool = False
    total_donated: int = 0
    
    temple_built: bool = False
    land_donated: int = 0
    legacy_points: int = 0
    
    retired: bool = False
    petitions: int = 0
    court_visits: int = 0
    
    labor_points: int = 0
    daily_good_deeds: int = 0
    harvest_shared: int = 0
    
    # 骰子统计
    dice_stats: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.role == Role.MERCHANT:
            self.grain, self.coins, self.land = 2, 10, 0
        elif self.role == Role.LANDLORD:
            self.grain, self.coins, self.land = 3, 2, 3
        elif self.role == Role.OFFICIAL:
            self.grain, self.coins, self.land = 2, 4, 1
            self.reputation = 0
        elif self.role == Role.FARMER:
            self.grain, self.coins, self.land = 5, 2, 0
            self.action_points = 3
        elif self.role == Role.WIDOW:
            self.grain, self.coins, self.land, self.merit = 2, 3, 0, 4
        elif self.role == Role.MONK:
            self.dharma_power = 8
        
        self.dice_stats = {
            "karma_favorable": 0,
            "karma_adverse": 0,
            "practice_enlighten": 0,
            "fate_deep": 0,
            "imperm_epiphany": 0
        }
    
    def get_action_cost_modifier(self) -> int:
        """根据业力状态返回行动消耗修正"""
        if self.karma_state == DiceResult.KARMA_ADVERSE:
            return 1  # 逆境：行动消耗+1（相当于少1行动点）
        elif self.karma_state == DiceResult.KARMA_FAVORABLE:
            return -1  # 顺缘：行动消耗-1（相当于多1行动点）
        return 0
    
    def get_total_resources(self) -> int:
        return self.grain + self.coins + self.land * 5
    
    def check_path_completion(self) -> tuple:
        if self.role == Role.WIDOW:
            if self.bodhisattva_mode and self.beings_saved >= 4:
                return (True, "菩萨道", 38)
            elif self.bodhisattva_mode and self.beings_saved >= 2:
                return (True, "菩萨道（小成）", 22)
            return (False, "", 0)
            
        elif self.role == Role.MONK:
            if self.dharma_power <= 3 and self.grant_points >= 12:
                return (True, "涅槃道", 52)
            return (False, "", 0)
            
        elif self.role == Role.MERCHANT:
            if self.total_donated >= 15 and self.coins <= 5:
                return (True, "善财道", 55)
            elif self.total_donated >= 10:
                return (True, "善财道（小成）", 32)
            return (False, "", 0)
            
        elif self.role == Role.LANDLORD:
            # v2.9: 地主舍宅道加分提高
            if self.land_donated >= 3 and self.temple_built:
                return (True, "舍宅道", 58)
            elif self.land_donated >= 2 or self.temple_built:
                return (True, "舍宅道（小成）", 30)
            return (False, "", 0)
            
        elif self.role == Role.OFFICIAL:
            if self.retired and self.petitions >= 5:
                return (True, "清官道", 52)
            elif self.retired or self.petitions >= 4:
                return (True, "清官道（小成）", 35)
            return (False, "", 0)
            
        elif self.role == Role.FARMER:
            if self.daily_good_deeds >= 5 and self.harvest_shared >= 3:
                return (True, "勤劳道", 48)
            elif self.daily_good_deeds >= 3 or self.harvest_shared >= 2:
                return (True, "勤劳道（小成）", 26)
            return (False, "", 0)
        
        return (False, "", 0)
    
    def get_final_score(self) -> float:
        if self.role == Role.MONK:
            base_score = self.grant_points * 3 + self.merit
        else:
            resource_bonus = self.get_total_resources() // 4
            base_score = self.merit * 2 + self.reputation + resource_bonus
        
        path_complete, path_name, path_bonus = self.check_path_completion()
        if path_complete:
            base_score += path_bonus
        
        if self.role == Role.FARMER:
            base_score += self.labor_points * 2
        elif self.role == Role.WIDOW and self.bodhisattva_mode:
            base_score += self.salvation_points * 2 + self.beings_saved * 6
        elif self.role == Role.MERCHANT:
            base_score += int(self.total_donated * 1.2)
        elif self.role == Role.LANDLORD:
            base_score += self.legacy_points * 2 + self.land_donated * 6
        elif self.role == Role.OFFICIAL:
            base_score += self.petitions * 5
        
        # 骰子加分：大彻大悟次数
        base_score += self.dice_stats.get("practice_enlighten", 0) * 3
        
        return base_score

class GameSimulator:
    def __init__(self):
        self.dice_log = []  # 记录骰子事件
        
    def create_game(self):
        roles = list(Role)
        random.shuffle(roles)
        players = [Player(role=role) for role in roles[:6]]
        return {"players": players, "current_round": 1}
    
    def karma_phase(self, game):
        """业力阶段：每位玩家掷业力骰"""
        for p in game["players"]:
            roll, result = roll_karma_dice()
            p.karma_state = result
            
            if result == DiceResult.KARMA_FAVORABLE:
                p.dice_stats["karma_favorable"] += 1
            elif result == DiceResult.KARMA_ADVERSE:
                p.dice_stats["karma_adverse"] += 1
    
    def production_phase(self, game):
        for p in game["players"]:
            if p.role == Role.LANDLORD:
                p.grain += p.land
                p.legacy_points += max(1, p.land // 2)
            elif p.role == Role.FARMER:
                p.grain += 2
                p.labor_points += 1
            elif p.role == Role.WIDOW:
                if not p.bodhisattva_mode:
                    p.merit += 2
                else:
                    p.merit += 1
            elif p.role == Role.MONK:
                if not p.retreat_mode:
                    p.dharma_power = min(10, p.dharma_power + 1)
                else:
                    p.grant_points += 3
            elif p.role == Role.MERCHANT:
                p.coins += 2
    
    def event_phase(self, game):
        event_type = random.randint(1, 6)
        
        if event_type == 1:
            for p in game["players"]:
                if p.role == Role.OFFICIAL:
                    p.reputation += 2
                    p.court_visits += 1
                p.merit += 1
                
        elif event_type == 2:
            for p in game["players"]:
                p.grain = max(0, p.grain - 2)
            for p in game["players"]:
                if p.role == Role.OFFICIAL and p.reputation >= 1:
                    if random.random() > 0.4:
                        p.reputation = max(0, p.reputation - 1)
                        p.petitions += 1
                        p.merit += 3
                        for f in game["players"]:
                            if f.role in [Role.FARMER, Role.WIDOW]:
                                f.grain += 1
                                
        elif event_type == 3:
            participants = 0
            for p in game["players"]:
                if p.role == Role.MONK:
                    continue
                if p.coins >= 2 and random.random() > 0.3:
                    p.coins -= 2
                    p.merit += 1
                    participants += 1
                    if p.role == Role.MERCHANT:
                        p.total_donated += 2
                elif p.role == Role.WIDOW:
                    p.merit += 1
                    participants += 1
            for p in game["players"]:
                if p.role == Role.MONK:
                    p.grant_points += participants
                    
        elif event_type == 4:
            valid_targets = [p for p in game["players"] if p.life > 1]
            if valid_targets:
                target = random.choice(valid_targets)
                target.life -= 1
                target.awakening_tokens += 1
                
        elif event_type == 5:
            for p in game["players"]:
                if p.role == Role.FARMER:
                    p.grain += 3
                elif p.role == Role.LANDLORD:
                    p.grain += p.land
                    
        else:
            for p in game["players"]:
                if p.role == Role.MERCHANT:
                    p.coins += 3
    
    def action_phase(self, game):
        for p in game["players"]:
            # 基础行动点
            base_ap = 3 if p.role == Role.FARMER else 2
            
            # 业力修正
            karma_mod = -p.get_action_cost_modifier()  # 顺缘+1AP，逆境-1AP
            ap = max(1, base_ap + karma_mod)  # 最少1行动点
            
            # 菩萨状态额外行动点
            if p.role == Role.WIDOW and p.bodhisattva_mode:
                ap += 2
            
            self.check_state_transitions(p, game)
            
            while ap > 0:
                action = self.decide_action(p, game, ap)
                ap = self.execute_action(p, game, action, ap)
    
    def impermanence_phase(self, game):
        """无常阶段：生命减少，可能触发顿悟"""
        for p in game["players"]:
            p.life -= 1
            
            # 掷无常骰
            roll, result = roll_impermanence_dice()
            
            if result == DiceResult.IMPERM_AWAKENING:
                p.awakening_tokens += 1
            elif result == DiceResult.IMPERM_EPIPHANY:
                p.awakening_tokens += 2
                p.merit += 2
                p.dice_stats["imperm_epiphany"] += 1
    
    def check_state_transitions(self, p, game):
        if p.role == Role.WIDOW and not p.bodhisattva_mode:
            if (p.merit >= 8 and p.reputation == 0 and 
                p.get_total_resources() <= 10):
                p.bodhisattva_mode = True
                p.liberation_turn = game["current_round"]
        
        if p.role == Role.MONK and game["current_round"] >= 5:
            if p.dharma_power <= 6 and p.grant_points >= 5:
                p.retreat_mode = True
        
        if p.role == Role.OFFICIAL and game["current_round"] >= 7:
            if not p.retired and p.reputation >= 3 and p.petitions >= 3:
                if random.random() > 0.4:
                    p.retired = True
                    p.merit += p.reputation * 2
                    p.reputation = 0
        
        if p.role == Role.MERCHANT and not p.charity_mode:
            if p.total_donated >= 6:
                p.charity_mode = True
    
    def execute_action(self, p, game, action, ap) -> int:
        if action == "none":
            return 0
        
        elif action == "donate":
            if p.coins >= 3:
                # 修行骰：捐献时掷骰
                roll, result = roll_practice_dice()
                
                p.coins -= 3
                base_merit = 1
                
                if result == DiceResult.PRACTICE_ENLIGHTEN:
                    base_merit = 3  # 大彻大悟：三倍功德
                    p.dice_stats["practice_enlighten"] += 1
                elif result == DiceResult.PRACTICE_SUCCESS:
                    base_merit = 2  # 修行精进：双倍功德
                elif result == DiceResult.PRACTICE_FAIL:
                    base_merit = 0  # 修行受阻：无功德
                
                p.merit += base_merit
                
                if p.role == Role.WIDOW and not p.bodhisattva_mode:
                    p.merit += 1
                if p.role == Role.MERCHANT:
                    p.total_donated += 3
                p.reputation += 1
                for mp in game["players"]:
                    if mp.role == Role.MONK:
                        mp.dharma_power = min(10, mp.dharma_power + 1)
            return ap - 1
            
        elif action == "donate_anonymous":
            if p.coins >= 4:
                roll, result = roll_practice_dice()
                
                p.coins -= 4
                base_merit = 2
                
                if result == DiceResult.PRACTICE_ENLIGHTEN:
                    base_merit = 5
                    p.dice_stats["practice_enlighten"] += 1
                elif result == DiceResult.PRACTICE_SUCCESS:
                    base_merit = 3
                elif result == DiceResult.PRACTICE_FAIL:
                    base_merit = 1
                
                p.merit += base_merit
                
                if p.role == Role.WIDOW and not p.bodhisattva_mode:
                    p.merit += 1
                if p.role == Role.MERCHANT:
                    p.total_donated += 4
                for mp in game["players"]:
                    if mp.role == Role.MONK:
                        mp.dharma_power = min(10, mp.dharma_power + 1)
            return ap - 1
            
        elif action == "trade":
            if p.grain >= 3:
                p.grain -= 3
                p.coins += 4 if p.role == Role.MERCHANT else 2
            return ap
            
        elif action == "buy_land":
            cost = 4 if p.role == Role.LANDLORD else 6
            if p.coins >= cost and p.land < 5:
                p.coins -= cost
                p.land += 1
            return ap - 1
        
        elif action == "save_being":
            # 因缘骰：渡众生时掷骰
            roll, result = roll_fate_dice()
            
            targets = [t for t in game["players"] 
                      if t != p and t.role != Role.MONK and t.merit < 25]
            if targets:
                target = min(targets, key=lambda x: x.merit)
                
                if result == DiceResult.FATE_DEEP:
                    merit_given = 6  # 深厚因缘：给予更多
                    p.dice_stats["fate_deep"] += 1
                elif result == DiceResult.FATE_SHALLOW:
                    merit_given = 2  # 缘浅：给予较少
                else:
                    merit_given = 4  # 普通
                
                target.merit += merit_given
                p.salvation_points += merit_given
                
                if id(target) not in p.saved_players:
                    p.saved_players.add(id(target))
                    p.beings_saved += 1
            return ap - 1
        
        elif action == "grant":
            if p.dharma_power >= 2:
                # 修行骰：授法时掷骰
                roll, result = roll_practice_dice()
                
                targets = [t for t in game["players"] if t != p]
                if targets:
                    target = random.choice(targets)
                    
                    if result == DiceResult.PRACTICE_ENLIGHTEN:
                        grant = min(6, p.dharma_power)  # 大彻大悟：更多授法
                        p.dice_stats["practice_enlighten"] += 1
                    elif result == DiceResult.PRACTICE_SUCCESS:
                        grant = min(5, p.dharma_power)
                    elif result == DiceResult.PRACTICE_FAIL:
                        grant = min(2, p.dharma_power)  # 受阻：较少
                    else:
                        grant = min(4, p.dharma_power)
                    
                    p.dharma_power -= grant
                    target.merit += grant
                    p.grant_points += grant
            return ap - 1
        
        elif action == "grand_charity":
            if p.coins >= 5:
                roll, result = roll_practice_dice()
                
                donation = min(p.coins - 2, 8)
                p.coins -= donation
                p.total_donated += donation
                
                if result == DiceResult.PRACTICE_ENLIGHTEN:
                    p.merit += donation  # 全额功德
                    p.dice_stats["practice_enlighten"] += 1
                elif result == DiceResult.PRACTICE_SUCCESS:
                    p.merit += donation * 3 // 4
                else:
                    p.merit += donation // 2
                
                for other in game["players"]:
                    if other != p and other.role != Role.MONK:
                        other.coins += 1
            return ap - 1
        
        elif action == "donate_land":
            if p.land >= 1:
                roll, result = roll_practice_dice()
                
                p.land -= 1
                p.land_donated += 1
                
                if result == DiceResult.PRACTICE_ENLIGHTEN:
                    p.merit += 6
                    p.dice_stats["practice_enlighten"] += 1
                elif result == DiceResult.PRACTICE_SUCCESS:
                    p.merit += 5
                else:
                    p.merit += 4
                
                if p.land_donated >= 2 and not p.temple_built:
                    p.temple_built = True
                    p.merit += 6
            return ap - 1
            
        elif action == "build_temple":
            if p.land >= 2 and not p.temple_built:
                roll, result = roll_practice_dice()
                
                p.land -= 2
                p.land_donated += 2
                p.temple_built = True
                
                if result == DiceResult.PRACTICE_ENLIGHTEN:
                    p.merit += 18
                    p.dice_stats["practice_enlighten"] += 1
                elif result == DiceResult.PRACTICE_SUCCESS:
                    p.merit += 15
                else:
                    p.merit += 12
            return ap - 1
        
        elif action == "go_to_court":
            p.reputation += 1
            p.court_visits += 1
            return ap - 1
            
        elif action == "petition":
            if p.reputation >= 1:
                # 因缘骰：为民请命
                roll, result = roll_fate_dice()
                
                p.reputation = max(0, p.reputation - 1)
                p.petitions += 1
                
                if result == DiceResult.FATE_DEEP:
                    p.merit += 5  # 深厚因缘：更多功德
                    p.dice_stats["fate_deep"] += 1
                elif result == DiceResult.FATE_SHALLOW:
                    p.merit += 2
                else:
                    p.merit += 3
                
                targets = [t for t in game["players"] 
                          if t != p and t.role not in [Role.MONK, Role.OFFICIAL]]
                if targets:
                    target = min(targets, key=lambda x: x.merit)
                    target.merit += 2
            return ap - 1
            
        elif action == "retire":
            if not p.retired and p.reputation >= 2:
                p.merit += p.reputation * 2
                p.retired = True
                p.reputation = 0
            return ap - 1
        
        elif action == "daily_good":
            if p.grain >= 1:
                roll, result = roll_practice_dice()
                
                p.grain -= 1
                
                if result == DiceResult.PRACTICE_ENLIGHTEN:
                    p.merit += 4
                    p.dice_stats["practice_enlighten"] += 1
                elif result == DiceResult.PRACTICE_SUCCESS:
                    p.merit += 3
                else:
                    p.merit += 2
                
                p.daily_good_deeds += 1
            return ap - 1
            
        elif action == "share_harvest":
            if p.grain >= 3:
                roll, result = roll_fate_dice()
                
                p.grain -= 2
                targets = [t for t in game["players"] 
                          if t != p and t.role != Role.MONK]
                if targets:
                    target = min(targets, key=lambda x: x.grain)
                    
                    if result == DiceResult.FATE_DEEP:
                        target.grain += 3
                        p.merit += 3
                        p.dice_stats["fate_deep"] += 1
                    elif result == DiceResult.FATE_SHALLOW:
                        target.grain += 1
                        p.merit += 1
                    else:
                        target.grain += 2
                        p.merit += 2
                    
                    p.harvest_shared += 1
            return ap - 1
        
        elif action == "use_awakening":
            if p.awakening_tokens > 0:
                p.awakening_tokens -= 1
                p.merit += 4
            return ap - 1
        
        return ap - 1
    
    def decide_action(self, player, game, remaining_ap) -> str:
        actions = []
        p = player
        round_num = game["current_round"]
        
        if p.role == Role.WIDOW:
            if p.bodhisattva_mode:
                targets = [t for t in game["players"] 
                          if t != p and t.role != Role.MONK and t.merit < 25]
                if targets:
                    actions.append(("save_being", 0.9))
            else:
                if p.coins >= 4:
                    actions.append(("donate_anonymous", 0.6))
                elif p.coins >= 3:
                    actions.append(("donate", 0.5))
        
        elif p.role == Role.MONK:
            if p.dharma_power >= 3:
                actions.append(("grant", 0.85))
            elif p.dharma_power >= 2:
                actions.append(("grant", 0.7))
        
        elif p.role == Role.MERCHANT:
            if p.charity_mode and p.coins >= 5:
                actions.append(("grand_charity", 0.8))
            if p.coins >= 4:
                actions.append(("donate_anonymous", 0.6))
            if p.coins >= 3:
                actions.append(("donate", 0.5))
            if p.grain >= 3:
                actions.append(("trade", 0.65))
        
        elif p.role == Role.LANDLORD:
            if p.land >= 2 and not p.temple_built and round_num >= 3:
                actions.append(("build_temple", 0.7))
            if p.land >= 1 and round_num >= 4:
                actions.append(("donate_land", 0.6))
            if p.coins >= 4 and p.land < 4 and round_num <= 5:
                actions.append(("buy_land", 0.5))
            if p.coins >= 3:
                actions.append(("donate", 0.3))
        
        elif p.role == Role.OFFICIAL:
            if p.reputation <= 1 and not p.retired:
                actions.append(("go_to_court", 0.75))
            if p.reputation >= 2 and not p.retired:
                actions.append(("petition", 0.7))
            if p.reputation >= 4 and round_num >= 6 and not p.retired:
                actions.append(("retire", 0.6))
            if p.coins >= 4:
                actions.append(("donate_anonymous", 0.35))
        
        elif p.role == Role.FARMER:
            if p.grain >= 5:
                actions.append(("share_harvest", 0.75))
            if p.grain >= 2:
                actions.append(("daily_good", 0.7))
            if p.grain >= 3:
                actions.append(("trade", 0.35))
            if p.coins >= 3:
                actions.append(("donate", 0.25))
        
        if p.awakening_tokens > 0:
            actions.append(("use_awakening", 0.9))
        
        if not actions:
            return "none"
        
        actions.sort(key=lambda x: x[1], reverse=True)
        
        for action, priority in actions:
            if random.random() < priority:
                return action
        
        return actions[0][0] if actions else "none"
    
    def run_game(self) -> Dict:
        game = self.create_game()
        
        for round_num in range(1, 11):
            game["current_round"] = round_num
            self.karma_phase(game)        # 新增：业力阶段
            self.production_phase(game)
            self.event_phase(game)
            self.action_phase(game)
            self.impermanence_phase(game)  # 改进：无常阶段包含骰子
        
        results = []
        for p in game["players"]:
            path_complete, path_name, path_bonus = p.check_path_completion()
            score = p.get_final_score()
            
            results.append({
                "role": p.role.value,
                "merit": p.merit,
                "reputation": p.reputation,
                "final_score": score,
                "path_complete": path_complete,
                "path_name": path_name,
                "dice_stats": p.dice_stats.copy()
            })
        
        sorted_results = sorted(results, key=lambda x: x["final_score"], reverse=True)
        winner = sorted_results[0]
        
        win_type = winner["path_name"] if winner["path_complete"] else "standard"
        
        return {"winner": winner["role"], "win_type": win_type, "scores": results}
    
    def run_batch(self, num_games: int) -> Dict:
        role_wins = {role.value: 0 for role in Role}
        role_scores = {role.value: [] for role in Role}
        path_wins = {}
        
        # 骰子统计
        total_enlighten = 0
        total_epiphany = 0
        total_fate_deep = 0
        
        for _ in range(num_games):
            result = self.run_game()
            role_wins[result["winner"]] += 1
            
            win_type = result["win_type"]
            path_wins[win_type] = path_wins.get(win_type, 0) + 1
            
            for p in result["scores"]:
                role_scores[p["role"]].append(p["final_score"])
                total_enlighten += p["dice_stats"].get("practice_enlighten", 0)
                total_epiphany += p["dice_stats"].get("imperm_epiphany", 0)
                total_fate_deep += p["dice_stats"].get("fate_deep", 0)
        
        return {
            "total_games": num_games,
            "role_win_rates": {k: v/num_games*100 for k, v in role_wins.items()},
            "role_avg_scores": {k: sum(v)/len(v) if v else 0 for k, v in role_scores.items()},
            "role_score_std": {k: (sum((x - sum(v)/len(v))**2 for x in v)/len(v))**0.5 if v else 0 
                              for k, v in role_scores.items()},
            "win_types": {k: v/num_games*100 for k, v in path_wins.items()},
            "dice_stats": {
                "avg_enlighten_per_game": total_enlighten / num_games,
                "avg_epiphany_per_game": total_epiphany / num_games,
                "avg_fate_deep_per_game": total_fate_deep / num_games
            }
        }

def main():
    simulator = GameSimulator()
    
    test_sizes = [100, 1000, 10000]
    all_results = {}
    
    for size in test_sizes:
        print(f"Running {size} games simulation...")
        start = time.time()
        results = simulator.run_batch(size)
        elapsed = time.time() - start
        results["elapsed_seconds"] = round(elapsed, 2)
        all_results[size] = results
        print(f"  Completed in {elapsed:.2f} seconds")
    
    with open("batch_simulation_results_v29_dice.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*70)
    print("BATCH SIMULATION RESULTS - Path to Salvation v2.9")
    print("(With Dice System)")
    print("="*70)
    
    for size in test_sizes:
        r = all_results[size]
        print(f"\n{'='*70}")
        print(f"  {size} GAMES ({r['elapsed_seconds']}s)")
        print(f"{'='*70}")
        
        print("\n[Win Rates]")
        for role, rate in sorted(r["role_win_rates"].items(), key=lambda x: x[1], reverse=True):
            bar = "#" * int(rate / 2)
            print(f"  {role}: {rate:6.2f}% {bar}")
        
        print("\n[Average Scores]")
        for role in sorted(r["role_avg_scores"].keys(), key=lambda x: r["role_avg_scores"][x], reverse=True):
            avg = r["role_avg_scores"][role]
            std = r["role_score_std"][role]
            print(f"  {role}: {avg:6.1f} (+/- {std:.1f})")
        
        print(f"\n[Victory Types]")
        for vtype, rate in sorted(r["win_types"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {vtype}: {rate:5.2f}%")
        
        print(f"\n[Dice Events (per game avg)]")
        ds = r["dice_stats"]
        print(f"  Enlightenment (6 on Practice): {ds['avg_enlighten_per_game']:.2f}")
        print(f"  Great Epiphany (6 on Imperm):  {ds['avg_epiphany_per_game']:.2f}")
        print(f"  Deep Fate (5-6 on Fate):       {ds['avg_fate_deep_per_game']:.2f}")
    
    print("\n" + "="*70)
    print("Results saved to batch_simulation_results_v29_dice.json")
    
    return all_results

if __name__ == "__main__":
    main()
