# -*- coding: utf-8 -*-
"""
《功德轮回：众生百态》v4.4 蒙特卡洛模拟器
用于平衡性测试
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import json
from collections import defaultdict

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
    # 农夫发愿
    DILIGENT_FORTUNE = "勤劳致福"  # 简单：福≥15
    POOR_GIRL_LAMP = "贫女一灯"    # 困难：福≥20且财富≤5
    # 商人发愿
    WEALTH_MERIT = "财施功德"      # 简单：布施≥3次
    GREAT_MERCHANT = "大商人之心"  # 困难：福≥18且渡化≥2
    # 学者发愿
    TEACH_WISDOM = "传道授业"      # 简单：慧≥18
    TEACHER_MODEL = "万世师表"     # 困难：福≥15且慧≥22
    # 僧侣发愿
    ARHAT = "阿罗汉果"            # 简单：慧≥22
    BODHISATTVA = "菩萨道"        # 困难：福≥18且渡化≥3

class BodhisattvaVow(Enum):
    DIZANG = "地藏愿"   # 自损换团队收益
    GUANYIN = "观音愿"  # 布施改为帮助队友
    PUXIAN = "普贤愿"   # 每回合供养
    WENSHU = "文殊愿"   # 修行减1慧但可分给他人

@dataclass
class Player:
    role: Role
    faith: FaithState = FaithState.SECULAR
    wealth: int = 0
    fu: int = 0  # 福
    hui: int = 0  # 慧
    vow: Optional[Vow] = None
    bodhisattva_vow: Optional[BodhisattvaVow] = None
    
    # 追踪
    donate_count: int = 0
    save_count: int = 0  # 渡化次数
    help_count: int = 0  # 帮助行动次数
    skill_uses: int = 2  # 主动技能剩余次数
    puxian_supply: int = 0  # 普贤供养累计
    guanyin_helped: set = field(default_factory=set)  # 观音帮助过的玩家
    
    def __post_init__(self):
        # 设置初始资源
        if self.role == Role.FARMER:
            self.wealth, self.fu, self.hui = 5, 2, 2
        elif self.role == Role.MERCHANT:
            self.wealth, self.fu, self.hui = 8, 1, 1
        elif self.role == Role.SCHOLAR:
            self.wealth, self.fu, self.hui = 3, 1, 4
        elif self.role == Role.MONK:
            self.wealth, self.fu, self.hui = 0, 3, 3
    
    def apply_faith(self, faith: FaithState, is_start: bool = True):
        """应用信仰状态"""
        if faith == FaithState.SECULAR:
            if is_start:
                self.wealth += 4
        elif faith == FaithState.SMALL_VEHICLE:
            if is_start:
                self.fu += 1
                self.hui += 1
            else:
                self.fu += 1  # 中途皈依只加福
        
        self.faith = faith
    
    def apply_great_vehicle(self, is_start: bool = True):
        """发大乘心"""
        if is_start:
            self.wealth -= 2
            self.hui += 1
        else:
            self.wealth -= 3
        self.faith = FaithState.GREAT_VEHICLE
    
    def get_score(self) -> int:
        """计算基础分"""
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
        
        # 平衡惩罚
        if self.fu < 5 or self.hui < 5:
            base = base // 2
        
        return base
    
    def check_vow(self) -> Tuple[int, int]:
        """检查发愿达成，返回(奖励分, 惩罚分)"""
        reward, penalty = 0, 0
        
        if self.vow == Vow.DILIGENT_FORTUNE:
            if self.fu >= 15:
                reward += 12
            else:
                penalty += 4
        elif self.vow == Vow.POOR_GIRL_LAMP:
            if self.fu >= 20 and self.wealth <= 5:
                reward += 18
            else:
                penalty += 6
        elif self.vow == Vow.WEALTH_MERIT:
            if self.donate_count >= 3:
                reward += 12
            else:
                penalty += 4
        elif self.vow == Vow.GREAT_MERCHANT:
            if self.fu >= 18 and self.save_count >= 2:
                reward += 16
            else:
                penalty += 6
        elif self.vow == Vow.TEACH_WISDOM:
            if self.hui >= 18:
                reward += 12
            else:
                penalty += 4
        elif self.vow == Vow.TEACHER_MODEL:
            if self.fu >= 15 and self.hui >= 22:
                reward += 16
            else:
                penalty += 6
        elif self.vow == Vow.ARHAT:
            if self.hui >= 22:
                reward += 12
            else:
                penalty += 4
        elif self.vow == Vow.BODHISATTVA:
            if self.fu >= 18 and self.save_count >= 3:
                reward += 18
            else:
                penalty += 8
        
        return reward, penalty
    
    def check_bodhisattva_vow(self, team_win: bool, other_players: List['Player']) -> Tuple[int, int]:
        """检查菩萨愿达成"""
        reward, penalty = 0, 0
        
        if self.bodhisattva_vow == BodhisattvaVow.DIZANG:
            if team_win:
                reward += 15  # 净收益+5（因为持续效果-10）
            # 持续效果-10已在外部计算
        elif self.bodhisattva_vow == BodhisattvaVow.GUANYIN:
            if len(self.guanyin_helped) >= 3:
                reward += 12
            else:
                penalty += 4
        elif self.bodhisattva_vow == BodhisattvaVow.PUXIAN:
            if self.puxian_supply >= 5:
                reward += 10
            else:
                penalty += 6
        elif self.bodhisattva_vow == BodhisattvaVow.WENSHU:
            # 检查其他玩家慧≥15的数量
            high_hui_count = sum(1 for p in other_players if p.hui >= 15)
            if high_hui_count >= 2:
                reward += 14
            else:
                penalty += 5
        
        return reward, penalty

@dataclass
class Being:
    """众生卡"""
    name: str
    cost: int
    fu_reward: int
    hui_reward: int
    stay_rounds: int = 0

class GameSimulator:
    def __init__(self, num_players: int = 4):
        self.num_players = num_players
        self.beings_pool = self._create_beings()
        
    def _create_beings(self) -> List[Being]:
        """创建众生牌堆"""
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
        """创建游戏"""
        roles = list(Role)
        random.shuffle(roles)
        players = []
        
        for i, role in enumerate(roles[:self.num_players]):
            player = Player(role=role)
            
            # 随机选择信仰状态
            faith_choice = random.choices(
                [FaithState.SECULAR, FaithState.SMALL_VEHICLE, FaithState.GREAT_VEHICLE],
                weights=[0.3, 0.4, 0.3]  # 可调整权重
            )[0]
            
            if faith_choice == FaithState.SECULAR:
                player.apply_faith(FaithState.SECULAR, is_start=True)
            elif faith_choice == FaithState.SMALL_VEHICLE:
                player.apply_faith(FaithState.SMALL_VEHICLE, is_start=True)
            else:
                player.apply_faith(FaithState.SMALL_VEHICLE, is_start=True)
                player.apply_great_vehicle(is_start=True)
            
            # 选择发愿
            player.vow = self._choose_vow(role)
            
            # 大乘选择菩萨愿
            if player.faith == FaithState.GREAT_VEHICLE:
                player.bodhisattva_vow = random.choice(list(BodhisattvaVow))
            
            players.append(player)
        
        # 初始化众生区域
        beings_deck = self.beings_pool.copy()
        random.shuffle(beings_deck)
        active_beings = [beings_deck.pop(), beings_deck.pop()]  # 初始2张
        
        return {
            "players": players,
            "current_round": 1,
            "calamity": 0,
            "saved_count": 0,
            "active_beings": active_beings,
            "beings_deck": beings_deck,
            "events_log": []
        }
    
    def _choose_vow(self, role: Role) -> Vow:
        """根据角色选择发愿"""
        vow_map = {
            Role.FARMER: [Vow.DILIGENT_FORTUNE, Vow.POOR_GIRL_LAMP],
            Role.MERCHANT: [Vow.WEALTH_MERIT, Vow.GREAT_MERCHANT],
            Role.SCHOLAR: [Vow.TEACH_WISDOM, Vow.TEACHER_MODEL],
            Role.MONK: [Vow.ARHAT, Vow.BODHISATTVA],
        }
        # 50%选简单，50%选困难（更均衡的测试）
        return random.choices(vow_map[role], weights=[0.5, 0.5])[0]
    
    def vow_reward_phase(self, game: Dict):
        """发愿奖励阶段（回合开始）"""
        for p in game["players"]:
            if p.vow in [Vow.DILIGENT_FORTUNE, Vow.POOR_GIRL_LAMP]:
                p.fu += 1
            elif p.vow == Vow.WEALTH_MERIT:
                p.wealth += 1
            elif p.vow in [Vow.GREAT_MERCHANT, Vow.TEACH_WISDOM, Vow.TEACHER_MODEL, Vow.ARHAT]:
                p.hui += 1
            elif p.vow == Vow.BODHISATTVA:
                p.fu += 1
    
    def collective_event_phase(self, game: Dict):
        """集体事件阶段"""
        # 调整权重：增加灾难概率，减少福报
        event_type = random.choices(
            ["disaster", "misfortune", "blessing"],
            weights=[0.4, 0.2, 0.4]  # 原来0.33, 0.17, 0.5
        )[0]
        
        if event_type == "disaster":
            self._disaster_event(game)
        elif event_type == "misfortune":
            self._misfortune_event(game)
        else:
            self._blessing_event(game)
    
    def _disaster_event(self, game: Dict):
        """天灾事件（囚徒困境）"""
        event_name = random.choice(["旱魃肆虐", "洪水滔天", "瘟疫流行", "蝗灾蔽日"])
        game["events_log"].append(f"R{game['current_round']}: {event_name}")
        
        # 每个玩家独立选择A或B
        choices = []
        for p in game["players"]:
            # AI决策：基于当前状态选择
            choice = self._decide_disaster_choice(p, game, event_name)
            choices.append(choice)
        
        a_count = choices.count("A")
        b_count = choices.count("B")
        
        # 基础效果 - 增加劫难
        game["calamity"] += 4  # 进一步增加
        
        # 根据事件类型和选择执行效果
        if event_name == "旱魃肆虐":
            for i, p in enumerate(game["players"]):
                if choices[i] == "A":
                    p.wealth -= 3
                    if a_count >= 2:
                        p.fu += 1
                else:
                    p.wealth -= 1
            if a_count >= 2:
                game["calamity"] -= 1
            if b_count >= 2:
                game["calamity"] += 1
                
        elif event_name == "洪水滔天":
            for i, p in enumerate(game["players"]):
                if choices[i] == "A":
                    p.wealth -= 2
                    p.fu += 2
                else:
                    p.hui += 1
                    p.fu -= 1
                    
        elif event_name == "瘟疫流行":
            game["calamity"] += 1  # 额外+1
            for i, p in enumerate(game["players"]):
                if choices[i] == "A":
                    roll = random.randint(1, 6)
                    if roll <= 2:
                        p.fu -= 2
                    else:
                        p.fu += 2
                        p.hui += 1
                else:
                    p.hui += 2
                    p.fu -= 1
                    
        elif event_name == "蝗灾蔽日":
            for i, p in enumerate(game["players"]):
                if choices[i] == "A":
                    p.wealth -= 2
                    p.fu += a_count  # 每个选A的人都获得福
                else:
                    p.wealth += 2
                    game["calamity"] += 1
            if a_count == len(game["players"]):
                game["calamity"] -= 2
                for p in game["players"]:
                    p.hui += 1
    
    def _decide_disaster_choice(self, player: Player, game: Dict, event: str) -> str:
        """AI决策天灾选择"""
        # 简单策略：根据当前劫难和资源情况决定
        calamity_critical = game["calamity"] >= 10
        wealth_low = player.wealth <= 3
        fu_high = player.fu >= 10
        
        # 大乘玩家倾向选A（利他）
        if player.faith == FaithState.GREAT_VEHICLE:
            return "A" if random.random() > 0.3 else "B"
        
        # 劫难高时更多人选A
        if calamity_critical:
            return "A" if random.random() > 0.4 else "B"
        
        # 财富低时可能选B保守
        if wealth_low:
            return "B" if random.random() > 0.4 else "A"
        
        # 默认随机
        return random.choice(["A", "B"])
    
    def _misfortune_event(self, game: Dict):
        """人祸事件"""
        event_name = random.choice(["苛政如虎", "战火将至"])
        game["events_log"].append(f"R{game['current_round']}: {event_name}")
        game["calamity"] += 2  # 原来+1
        
        # 类似处理...
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
                    else:
                        p.wealth -= 3
                else:
                    p.wealth -= 1
                    p.hui += 1
            if a_count >= 2:
                game["calamity"] -= 2
    
    def _blessing_event(self, game: Dict):
        """福报事件 - 减少劫难减少量"""
        event_name = random.choice(["风调雨顺", "国泰民安", "浴佛盛会", "盂兰盆节", "高僧讲经", "舍利现世"])
        game["events_log"].append(f"R{game['current_round']}: {event_name}")
        
        if event_name == "风调雨顺":
            for p in game["players"]:
                p.wealth += 1  # 原来+2
            # 不减劫难了
        elif event_name == "国泰民安":
            game["calamity"] -= 1  # 原来-2
        elif event_name == "浴佛盛会":
            for p in game["players"]:
                p.fu += 1
                # 移除皈依者额外+1
        elif event_name == "盂兰盆节":
            for p in game["players"]:
                p.fu += 1
                # 移除慧+1
        elif event_name == "高僧讲经":
            for p in game["players"]:
                p.hui += 1
                # 移除皈依者额外+1
        elif event_name == "舍利现世":
            # 不减劫难了
            for p in game["players"]:
                p.fu += 1
    
    def beings_phase(self, game: Dict):
        """众生阶段"""
        # 滞留标记+1
        for being in game["active_beings"]:
            being.stay_rounds += 1
        
        # 超时惩罚 - 增加惩罚
        timeout_beings = [b for b in game["active_beings"] if b.stay_rounds >= 2]
        for b in timeout_beings:
            game["calamity"] += 4  # 原来+3
            game["active_beings"].remove(b)
        
        # 补充众生
        if game["beings_deck"]:
            game["active_beings"].append(game["beings_deck"].pop())
    
    def action_phase(self, game: Dict):
        """行动阶段"""
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
                elif action == "skill":
                    self._do_skill(p, game)
                else:
                    break
                
                actions_left -= 1
    
    def _decide_action(self, player: Player, game: Dict) -> str:
        """AI决策行动"""
        # 优先级策略
        
        # 1. 劫难太高，优先护法
        if game["calamity"] >= 15 and player.wealth >= 2:
            return "protect"
        
        # 2. 有众生可渡化
        if player.hui >= 5 and game["active_beings"]:
            affordable = [b for b in game["active_beings"] 
                         if self._can_afford_being(player, b)]
            if affordable:
                return "save"
        
        # 3. 慧不够，修行
        if player.hui < 5:
            return "practice"
        
        # 4. 财富够，布施
        if player.wealth >= 2 and random.random() > 0.4:
            return "donate"
        
        # 5. 缺钱劳作
        if player.wealth < 4:
            return "labor"
        
        # 6. 使用主动技能
        if player.skill_uses > 0 and random.random() > 0.7:
            return "skill"
        
        # 默认修行
        return "practice"
    
    def _can_afford_being(self, player: Player, being: Being) -> bool:
        """检查是否能支付众生成本"""
        cost = being.cost
        
        # 角色成本调整
        if player.role == Role.MERCHANT:
            cost += 1
        elif player.role == Role.SCHOLAR:
            cost -= 1
        elif player.role == Role.MONK:
            cost -= 1
        
        # 不皈依者成本-1
        if player.faith == FaithState.SECULAR:
            cost -= 1
        
        cost = max(1, cost)
        
        # 僧侣可用福代财
        if player.role == Role.MONK:
            return player.wealth + min(2, player.fu) >= cost
        
        return player.wealth >= cost
    
    def _do_labor(self, player: Player):
        """劳作"""
        gain = 3
        if player.role == Role.FARMER:
            gain += 1  # 农夫4
        if player.faith == FaithState.SECULAR:
            gain += 1  # 不皈依者额外+1
        player.wealth += gain
        
        # 农夫被动：每回合第一次劳作不受负面事件影响（简化为概率收益）
        # 这里不额外实现
    
    def _do_practice(self, player: Player):
        """修行"""
        gain = 2
        if player.role == Role.SCHOLAR:
            gain += 1
        
        # 文殊愿：修行-1但可分给他人（简化处理）
        if player.bodhisattva_vow == BodhisattvaVow.WENSHU:
            gain -= 1
        
        player.hui += gain
    
    def _do_donate(self, player: Player, game: Dict):
        """布施"""
        if player.wealth < 2:
            return
        
        player.wealth -= 2
        fu_gain = 2
        
        if player.role == Role.MERCHANT:
            fu_gain += 1
        if player.faith != FaithState.SECULAR:
            fu_gain += 1
        if game["calamity"] >= 15:
            fu_gain += 1
        
        # 观音愿：布施改为帮助队友
        if player.bodhisattva_vow == BodhisattvaVow.GUANYIN:
            # 给最穷的队友财富
            others = [p for p in game["players"] if p != player]
            if others:
                poorest = min(others, key=lambda x: x.wealth)
                poorest.wealth += 2
                player.guanyin_helped.add(id(poorest))
        else:
            game["calamity"] -= 1
        
        player.fu += fu_gain
        player.donate_count += 1
        player.help_count += 1
    
    def _do_save(self, player: Player, game: Dict):
        """渡化"""
        if player.hui < 5 or not game["active_beings"]:
            return
        
        # 选择成本最低的众生
        affordable = [b for b in game["active_beings"] 
                     if self._can_afford_being(player, b)]
        if not affordable:
            return
        
        being = min(affordable, key=lambda x: x.cost)
        cost = being.cost
        
        # 成本调整
        if player.role == Role.MERCHANT:
            cost += 1
        elif player.role == Role.SCHOLAR:
            cost -= 1
            player.hui -= 1  # 学者额外消耗1慧
        elif player.role == Role.MONK:
            cost -= 1
        
        if player.faith == FaithState.SECULAR:
            cost -= 1
        
        cost = max(1, cost)
        
        # 僧侣可用福代财
        if player.role == Role.MONK and player.wealth < cost:
            fu_used = min(2, cost - player.wealth)
            player.fu -= fu_used
            player.wealth -= (cost - fu_used)
        else:
            player.wealth -= cost
        
        # 获得奖励
        player.fu += being.fu_reward
        player.hui += being.hui_reward
        
        if player.faith != FaithState.SECULAR:
            player.fu += 1
        
        # 商人首次渡化返财
        if player.role == Role.MERCHANT and player.save_count == 0:
            player.wealth += 2
        
        game["active_beings"].remove(being)
        game["saved_count"] += 1
        player.save_count += 1
        player.help_count += 1
    
    def _do_protect(self, player: Player, game: Dict):
        """护法"""
        if player.wealth < 2:
            return
        
        player.wealth -= 2
        player.fu += 1
        game["calamity"] -= 2
        player.help_count += 1
    
    def _do_skill(self, player: Player, game: Dict):
        """使用主动技能"""
        if player.skill_uses <= 0:
            return
        
        others = [p for p in game["players"] if p != player]
        if not others:
            return
        
        if player.role == Role.FARMER:
            # 分享收成
            if player.wealth >= 2:
                target = random.choice(others)
                player.wealth -= 2
                target.wealth += 2
                player.fu += 1
                target.fu += 1
                player.skill_uses -= 1
        elif player.role == Role.MERCHANT:
            # 慷慨宴请
            if player.wealth >= 3:
                player.wealth -= 3
                for p in game["players"]:
                    p.fu += 1
                game["calamity"] -= 1
                player.skill_uses -= 1
        elif player.role == Role.SCHOLAR:
            # 讲学传道
            targets = random.sample(others, min(2, len(others)))
            for t in targets:
                t.hui += 1
            player.fu += 1
            player.skill_uses -= 1
        elif player.role == Role.MONK:
            # 加持祈福
            target = random.choice(others)
            # 简化：直接给资源
            target.fu += 2
            player.fu -= 1
            player.skill_uses -= 1
    
    def settlement_phase(self, game: Dict):
        """结算阶段"""
        # 每回合劫难自动+1（时间压力）
        game["calamity"] += 1
        
        # 偶数回合生存消耗
        if game["current_round"] % 2 == 0:
            for p in game["players"]:
                if p.wealth >= 1:
                    p.wealth -= 1
                else:
                    p.fu -= 1
        
        # 普贤愿供养
        for p in game["players"]:
            if p.bodhisattva_vow == BodhisattvaVow.PUXIAN:
                if p.wealth >= 1:
                    p.wealth -= 1
                    p.puxian_supply += 1
        
        # 帮助奖励
        for p in game["players"]:
            if p.help_count >= 4:
                p.fu += 2
                p.help_count = 0  # 重置，避免重复触发
    
    def check_game_end(self, game: Dict) -> Tuple[bool, bool]:
        """检查游戏结束，返回(是否结束, 是否团队胜利)"""
        # 劫难爆表
        if game["calamity"] >= 20:
            return True, False
        
        # 6回合结束
        if game["current_round"] >= 6:
            # 劫难可以为负数（好事），只要≤12就算胜利
            team_win = game["calamity"] <= 12 and game["saved_count"] >= 5
            return True, team_win
        
        return False, False
    
    def run_game(self) -> Dict:
        """运行一局游戏"""
        game = self.create_game()
        
        for round_num in range(1, 7):
            game["current_round"] = round_num
            
            # 0. 发愿奖励
            self.vow_reward_phase(game)
            
            # 1. 集体事件
            self.collective_event_phase(game)
            
            # 2. 个人事件（奇数回合，简化处理）
            if round_num % 2 == 1:
                for p in game["players"]:
                    # 随机小效果
                    effect = random.choice(["fu+1", "hui+1", "wealth+1", "none"])
                    if effect == "fu+1":
                        p.fu += 1
                    elif effect == "hui+1":
                        p.hui += 1
                    elif effect == "wealth+1":
                        p.wealth += 1
            
            # 3. 众生阶段
            self.beings_phase(game)
            
            # 4. 行动阶段
            self.action_phase(game)
            
            # 5. 结算阶段
            self.settlement_phase(game)
            
            # 检查游戏结束
            ended, team_win = self.check_game_end(game)
            if ended:
                break
        
        # 最终检查
        _, team_win = self.check_game_end(game)
        
        # 计算得分
        results = []
        for p in game["players"]:
            base_score = p.get_score()
            vow_reward, vow_penalty = p.check_vow()
            
            # 菩萨愿
            bodhi_reward, bodhi_penalty = 0, 0
            if p.bodhisattva_vow:
                other_players = [op for op in game["players"] if op != p]
                bodhi_reward, bodhi_penalty = p.check_bodhisattva_vow(team_win, other_players)
                
                # 地藏愿持续效果
                if p.bodhisattva_vow == BodhisattvaVow.DIZANG:
                    base_score -= 10
            
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
            })
        
        winner = max(results, key=lambda x: x["final_score"]) if team_win else None
        
        return {
            "team_win": team_win,
            "calamity": game["calamity"],
            "saved_count": game["saved_count"],
            "players": results,
            "winner": winner["role"] if winner else None,
            "events": game["events_log"]
        }
    
    def run_simulation(self, num_games: int = 1000) -> Dict:
        """运行蒙特卡洛模拟"""
        all_results = []
        
        # 统计
        team_wins = 0
        role_wins = defaultdict(int)
        faith_wins = defaultdict(int)
        vow_success = defaultdict(lambda: {"success": 0, "total": 0})
        role_scores = defaultdict(list)
        faith_scores = defaultdict(list)
        
        for i in range(num_games):
            result = self.run_game()
            all_results.append(result)
            
            if result["team_win"]:
                team_wins += 1
                if result["winner"]:
                    role_wins[result["winner"]] += 1
            
            for p in result["players"]:
                role_scores[p["role"]].append(p["final_score"])
                faith_scores[p["faith"]].append(p["final_score"])
                
                if result["team_win"]:
                    if p["role"] == result["winner"]:
                        faith_wins[p["faith"]] += 1
                
                # 发愿统计
                if p["vow"]:
                    vow_success[p["vow"]]["total"] += 1
                    if p["vow_bonus"] > 0:
                        vow_success[p["vow"]]["success"] += 1
        
        # 分析结果
        analysis = {
            "version": "v4.4",
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
        }
        
        return analysis

def main():
    print("=" * 60)
    print("《功德轮回：众生百态》v4.4 蒙特卡洛模拟")
    print("=" * 60)
    print()
    
    simulator = GameSimulator(num_players=4)
    
    # 先运行单局测试
    print("[单局测试]")
    test_result = simulator.run_game()
    print(f"  团队胜利: {test_result['team_win']}")
    print(f"  劫难: {test_result['calamity']}")
    print(f"  渡化: {test_result['saved_count']}")
    print(f"  条件检查: 劫难<=12={test_result['calamity'] <= 12}, 渡化>=5={test_result['saved_count'] >= 5}")
    print()
    
    print("运行 1000 局模拟...")
    results = simulator.run_simulation(num_games=1000)
    
    print()
    print(f"[团队胜率] {results['team_win_rate']:.1f}%")
    print(f"[平均劫难] {results['avg_calamity']:.1f}")
    print(f"[平均渡化] {results['avg_saved']:.1f}")
    print()
    
    print("[职业胜率] (团队胜利后个人排名第一)")
    print("-" * 40)
    for role, rate in sorted(results["role_win_rates"].items(), 
                             key=lambda x: x[1], reverse=True):
        bar = "#" * int(rate / 2)
        print(f"  {role}: {rate:5.1f}% {bar}")
    
    print()
    print("[职业平均分]")
    print("-" * 40)
    for role, score in sorted(results["role_avg_scores"].items(), 
                              key=lambda x: x[1], reverse=True):
        print(f"  {role}: {score:.1f}")
    
    print()
    print("[信仰状态胜率]")
    print("-" * 40)
    for faith, rate in sorted(results["faith_win_rates"].items(), 
                              key=lambda x: x[1], reverse=True):
        bar = "#" * int(rate / 2)
        print(f"  {faith}: {rate:5.1f}% {bar}")
    
    print()
    print("[信仰状态平均分]")
    print("-" * 40)
    for faith, score in sorted(results["faith_avg_scores"].items(), 
                               key=lambda x: x[1], reverse=True):
        print(f"  {faith}: {score:.1f}")
    
    print()
    print("[发愿达成率]")
    print("-" * 40)
    for vow, rate in sorted(results["vow_success_rates"].items(), 
                            key=lambda x: x[1], reverse=True):
        bar = "#" * int(rate / 5)
        print(f"  {vow}: {rate:5.1f}% {bar}")
    
    # 保存结果
    with open("simulation_results_v44.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print()
    print("结果已保存到 simulation_results_v44.json")
    
    return results

if __name__ == "__main__":
    main()
