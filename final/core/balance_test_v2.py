# -*- coding: utf-8 -*-
"""
《功德轮回》核心版 v1.1 平衡测试器
目标：
- 全好人(利他)：团队胜率 ~80%
- 全坏人(自私)：团队胜率 <30%
- 好人有好报，坏人有恶报
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import json

# ============== 枚举定义 ==============

class Role(Enum):
    FARMER = "农夫"
    MERCHANT = "商人"
    SCHOLAR = "学者"
    MONK = "僧侣"

class PlayerType(Enum):
    ALTRUIST = "利他者"    # 好人：优先团队
    SELFISH = "自私者"     # 坏人：优先自己
    NEUTRAL = "中立者"     # 平衡策略

class ActionType(Enum):
    LABOR = "劳作"
    PRACTICE = "修行"
    DONATE = "布施"
    SAVE = "渡化"
    PROTECT = "护法"

# ============== 配置 ==============

@dataclass
class BalanceConfig:
    """游戏平衡配置 - 可调整参数"""
    
    # 初始资源 (资粮, 功德, 慧)
    init_farmer: Tuple[int, int, int] = (5, 2, 3)
    init_merchant: Tuple[int, int, int] = (8, 2, 1)
    init_scholar: Tuple[int, int, int] = (4, 2, 5)
    init_monk: Tuple[int, int, int] = (2, 6, 6)
    
    # === 关键平衡参数 ===
    
    # 集体事件 - 每回合基础劫难增加
    event_base_calamity: int = 4  # 基础劫难增加
    event_b_extra_calamity: int = 2  # 选B额外增加（总计 base + 人数*extra）
    
    # 选A牺牲
    sacrifice_cost: int = 2       # 选A消耗资粮
    sacrifice_merit: int = 1      # 选A获得功德
    sacrifice_calamity: int = 1   # 选A减少劫难
    
    # 牺牲加成
    sacrifice_crisis_threshold: int = 10  # 劫难≥此值时选A额外奖励
    sacrifice_crisis_merit: int = 2       # 危急时选A额外功德
    sacrifice_poor_merit: int = 3         # 资源不足仍选A额外功德
    sacrifice_all_a_merit: int = 1        # 全员选A每人额外功德
    
    # 众生超时
    being_timeout_rounds: int = 3   # 众生滞留多少回合超时
    being_timeout_calamity: int = 5 # 超时增加劫难
    
    # 基础行动
    labor_base: int = 3
    labor_farmer_bonus: int = 2
    practice_base: int = 2
    practice_scholar_bonus: int = 1
    donate_cost: int = 2
    donate_merit: int = 1
    donate_calamity: int = 1
    donate_merchant_bonus: int = 2
    protect_cost: int = 2
    protect_merit: int = 3
    protect_calamity: int = 3
    protect_monk_bonus: int = 2
    
    # 渡化
    save_hui_requirement: int = 4
    save_cost: int = 2
    save_merit: int = 3
    save_monk_cost_reduce: int = 1
    
    # 共业倍率
    karma_multiplier_levels: list = field(default_factory=lambda: [
        (4, 1.5),   # 劫难0-4: ×1.5
        (8, 1.2),   # 劫难5-8: ×1.2
        (12, 1.0),  # 劫难9-12: ×1.0
    ])
    
    # 胜利条件
    max_calamity: int = 20
    win_calamity: int = 12
    win_save: int = 5
    total_rounds: int = 6

# ============== 玩家状态 ==============

@dataclass
class Player:
    role: Role
    player_type: PlayerType
    wealth: int = 0
    merit: int = 0
    hui: int = 0
    
    # 统计
    sacrifice_count: int = 0
    donate_count: int = 0
    save_count: int = 0
    protect_count: int = 0

# ============== 游戏状态 ==============

@dataclass
class GameState:
    config: BalanceConfig
    players: List[Player]
    calamity: int = 0
    total_saves: int = 0
    current_round: int = 1
    beings_in_play: int = 5  # 场上众生数
    being_rounds: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])  # 每个众生滞留回合

# ============== AI决策 ==============

class AIDecision:
    @staticmethod
    def choose_sacrifice(player: Player, calamity: int, config: BalanceConfig) -> bool:
        """决定是否选A(牺牲)"""
        ptype = player.player_type
        
        if ptype == PlayerType.ALTRUIST:
            # 好人：高概率选A，危急时更高
            if calamity >= 15:
                return random.random() < 0.95
            elif calamity >= 10:
                return random.random() < 0.85
            else:
                return random.random() < 0.70
        
        elif ptype == PlayerType.SELFISH:
            # 坏人：低概率选A，除非快失败了
            if calamity >= 18:
                return random.random() < 0.50  # 快死了才帮忙
            elif calamity >= 15:
                return random.random() < 0.25
            else:
                return random.random() < 0.10
        
        else:  # NEUTRAL
            # 中立：根据情况决定
            if calamity >= 15:
                return random.random() < 0.70
            elif calamity >= 10:
                return random.random() < 0.50
            else:
                return random.random() < 0.35
    
    @staticmethod
    def choose_action(player: Player, state: GameState) -> ActionType:
        """选择行动"""
        config = state.config
        ptype = player.player_type
        urgency = state.calamity / config.max_calamity
        need_saves = state.total_saves < config.win_save
        
        # 好人：优先团队行动
        if ptype == PlayerType.ALTRUIST:
            # 高危时优先护法/布施
            if urgency > 0.5 and player.wealth >= config.protect_cost:
                if random.random() < 0.5:
                    return ActionType.PROTECT
            if urgency > 0.4 and player.wealth >= config.donate_cost:
                if random.random() < 0.4:
                    return ActionType.DONATE
            # 需要渡化时渡化
            if need_saves and player.hui >= config.save_hui_requirement:
                if player.wealth >= (config.save_cost - (1 if player.role == Role.MONK else 0)):
                    if random.random() < 0.5:
                        return ActionType.SAVE
        
        # 坏人：优先个人积累
        elif ptype == PlayerType.SELFISH:
            # 只在极端危急时才帮忙
            if urgency > 0.8 and player.wealth >= config.protect_cost:
                if random.random() < 0.3:
                    return ActionType.PROTECT
            # 大部分时间积累资源
            if player.role == Role.FARMER or player.wealth < 5:
                return ActionType.LABOR
            if player.role == Role.SCHOLAR:
                return ActionType.PRACTICE
        
        # 职业特化
        if player.role == Role.FARMER:
            if random.random() < 0.5:
                return ActionType.LABOR
        elif player.role == Role.MERCHANT:
            if player.wealth >= config.donate_cost and random.random() < 0.4:
                return ActionType.DONATE
            if player.wealth < 5:
                return ActionType.LABOR
        elif player.role == Role.SCHOLAR:
            if player.hui < 15 and random.random() < 0.4:
                return ActionType.PRACTICE
        elif player.role == Role.MONK:
            if need_saves and player.hui >= config.save_hui_requirement:
                cost = config.save_cost - config.save_monk_cost_reduce
                if player.wealth >= cost and random.random() < 0.5:
                    return ActionType.SAVE
            if urgency > 0.3 and player.wealth >= config.protect_cost:
                if random.random() < 0.4:
                    return ActionType.PROTECT
        
        # 默认
        if random.random() < 0.4:
            return ActionType.PRACTICE
        return ActionType.LABOR

# ============== 游戏引擎 ==============

class GameEngine:
    def __init__(self, config: BalanceConfig):
        self.config = config
    
    def init_players(self, player_types: List[PlayerType]) -> List[Player]:
        """初始化玩家"""
        init_resources = {
            Role.FARMER: self.config.init_farmer,
            Role.MERCHANT: self.config.init_merchant,
            Role.SCHOLAR: self.config.init_scholar,
            Role.MONK: self.config.init_monk,
        }
        
        players = []
        roles = list(Role)
        for i, ptype in enumerate(player_types):
            role = roles[i % len(roles)]
            w, m, h = init_resources[role]
            player = Player(role=role, player_type=ptype, wealth=w, merit=m, hui=h)
            players.append(player)
        
        return players
    
    def get_karma_multiplier(self, calamity: int) -> float:
        """获取共业倍率"""
        for threshold, multiplier in self.config.karma_multiplier_levels:
            if calamity <= threshold:
                return multiplier
        return 1.0
    
    def process_collective_event(self, state: GameState):
        """处理集体事件"""
        config = self.config
        
        # 基础劫难增加
        base_increase = config.event_base_calamity
        
        # 统计选A的人数
        a_count = 0
        for p in state.players:
            if AIDecision.choose_sacrifice(p, state.calamity, config):
                a_count += 1
                # 选A效果
                cost = min(p.wealth, config.sacrifice_cost)
                p.wealth -= cost
                p.merit += config.sacrifice_merit
                p.sacrifice_count += 1
                state.calamity -= config.sacrifice_calamity
                
                # 牺牲加成
                if state.calamity >= config.sacrifice_crisis_threshold:
                    p.merit += config.sacrifice_crisis_merit
                if cost < config.sacrifice_cost:  # 资源不足仍选A
                    p.merit += config.sacrifice_poor_merit
        
        # 全员选A加成
        if a_count == len(state.players):
            for p in state.players:
                p.merit += config.sacrifice_all_a_merit
        
        # 选B的人数造成额外劫难
        b_count = len(state.players) - a_count
        state.calamity += base_increase + b_count * config.event_b_extra_calamity
        state.calamity = max(0, state.calamity)
    
    def process_beings(self, state: GameState):
        """处理众生阶段"""
        config = self.config
        
        # 所有众生滞留+1
        for i in range(state.beings_in_play):
            if i < len(state.being_rounds):
                state.being_rounds[i] += 1
                # 超时检查
                if state.being_rounds[i] >= config.being_timeout_rounds:
                    state.calamity += config.being_timeout_calamity
                    state.being_rounds[i] = 0  # 重置
    
    def execute_action(self, player: Player, action: ActionType, state: GameState):
        """执行行动"""
        config = self.config
        
        if action == ActionType.LABOR:
            gain = config.labor_base
            if player.role == Role.FARMER:
                gain += config.labor_farmer_bonus
            player.wealth += gain
        
        elif action == ActionType.PRACTICE:
            gain = config.practice_base
            if player.role == Role.SCHOLAR:
                gain += config.practice_scholar_bonus
            player.hui += gain
        
        elif action == ActionType.DONATE:
            if player.wealth >= config.donate_cost:
                player.wealth -= config.donate_cost
                merit_gain = config.donate_merit
                if player.role == Role.MERCHANT:
                    merit_gain += config.donate_merchant_bonus
                player.merit += merit_gain
                state.calamity -= config.donate_calamity
                player.donate_count += 1
        
        elif action == ActionType.SAVE:
            if player.hui >= config.save_hui_requirement and state.beings_in_play > 0:
                cost = config.save_cost
                if player.role == Role.MONK:
                    cost -= config.save_monk_cost_reduce
                cost = max(1, cost)
                
                if player.wealth >= cost:
                    player.wealth -= cost
                    player.merit += config.save_merit
                    player.save_count += 1
                    state.total_saves += 1
                    state.beings_in_play -= 1
        
        elif action == ActionType.PROTECT:
            if player.wealth >= config.protect_cost:
                player.wealth -= config.protect_cost
                merit_gain = config.protect_merit
                if player.role == Role.MONK:
                    merit_gain += config.protect_monk_bonus
                player.merit += merit_gain
                state.calamity -= config.protect_calamity
                player.protect_count += 1
        
        state.calamity = max(0, state.calamity)
    
    def calculate_score(self, player: Player, team_win: bool, calamity: int) -> Tuple[int, int]:
        """计算得分，返回(原始分, 最终分)"""
        if not team_win:
            return (0, 0)
        
        raw_score = player.merit + player.hui
        karma_multiplier = self.get_karma_multiplier(calamity)
        final_score = int(raw_score * karma_multiplier)
        return (raw_score, final_score)
    
    def run_game(self, player_types: List[PlayerType]) -> Dict:
        """运行一局游戏"""
        players = self.init_players(player_types)
        state = GameState(config=self.config, players=players)
        
        # 游戏循环
        for round_num in range(1, self.config.total_rounds + 1):
            state.current_round = round_num
            
            # 1. 集体事件
            self.process_collective_event(state)
            
            # 检查立即失败
            if state.calamity >= self.config.max_calamity:
                break
            
            # 2. 众生阶段
            self.process_beings(state)
            
            if state.calamity >= self.config.max_calamity:
                break
            
            # 3. 行动阶段（每人2次）
            for p in players:
                for _ in range(2):
                    action = AIDecision.choose_action(p, state)
                    self.execute_action(p, action, state)
            
            # 4. 回合结束：偶数回合消耗
            if round_num % 2 == 0:
                for p in players:
                    if p.wealth > 0:
                        p.wealth -= 1
            
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
            raw_score, final_score = self.calculate_score(p, team_win, state.calamity)
            result["players"].append({
                "role": p.role.value,
                "type": p.player_type.value,
                "wealth": p.wealth,
                "merit": p.merit,
                "hui": p.hui,
                "raw_score": raw_score,
                "final_score": final_score,
                "sacrifice_count": p.sacrifice_count,
                "donate_count": p.donate_count,
                "save_count": p.save_count,
                "protect_count": p.protect_count,
            })
        
        # 排名
        if team_win:
            scores = [(i, result["players"][i]["final_score"]) for i in range(len(players))]
            scores.sort(key=lambda x: -x[1])
            for rank, (idx, score) in enumerate(scores):
                result["players"][idx]["rank"] = rank + 1
        else:
            for p in result["players"]:
                p["rank"] = 0
        
        return result

# ============== 测试场景 ==============

def run_scenario(config: BalanceConfig, player_types: List[PlayerType], 
                 num_games: int = 2000, label: str = "") -> Dict:
    """运行测试场景"""
    engine = GameEngine(config)
    
    wins = 0
    total_calamity = 0
    total_saves = 0
    
    type_stats = defaultdict(lambda: {
        "count": 0, "wins": 0, "total_raw": 0, "total_final": 0,
        "first_place": 0, "last_place": 0
    })
    
    for _ in range(num_games):
        result = engine.run_game(player_types)
        
        if result["team_win"]:
            wins += 1
        total_calamity += result["final_calamity"]
        total_saves += result["total_saves"]
        
        for p in result["players"]:
            ptype = p["type"]
            type_stats[ptype]["count"] += 1
            if result["team_win"]:
                type_stats[ptype]["wins"] += 1
            type_stats[ptype]["total_raw"] += p["raw_score"]
            type_stats[ptype]["total_final"] += p["final_score"]
            
            if result["team_win"]:
                if p["rank"] == 1:
                    type_stats[ptype]["first_place"] += 1
                if p["rank"] == len(result["players"]):
                    type_stats[ptype]["last_place"] += 1
    
    # 计算统计
    stats = {
        "label": label,
        "num_games": num_games,
        "team_win_rate": wins / num_games,
        "avg_calamity": total_calamity / num_games,
        "avg_saves": total_saves / num_games,
        "by_type": {}
    }
    
    for ptype, data in type_stats.items():
        cnt = data["count"]
        win_cnt = data["wins"]
        stats["by_type"][ptype] = {
            "count": cnt,
            "avg_raw_score": data["total_raw"] / cnt if cnt else 0,
            "avg_final_score": data["total_final"] / cnt if cnt else 0,
            "first_place_rate": data["first_place"] / win_cnt if win_cnt else 0,
            "last_place_rate": data["last_place"] / win_cnt if win_cnt else 0,
        }
    
    return stats

def print_scenario(stats: Dict):
    """打印场景结果"""
    print(f"\n{'='*60}")
    print(f"场景: {stats['label']}")
    print(f"{'='*60}")
    print(f"团队胜率: {stats['team_win_rate']*100:.1f}%")
    print(f"平均劫难: {stats['avg_calamity']:.1f}")
    print(f"平均渡化: {stats['avg_saves']:.1f}")
    
    if stats["by_type"]:
        print(f"\n玩家类型统计:")
        print(f"  {'类型':<8} | {'平均原始分':>10} | {'平均最终分':>10} | {'第1名率':>8} | {'最后名率':>8}")
        print(f"  {'-'*8}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+-{'-'*8}")
        for ptype, data in stats["by_type"].items():
            print(f"  {ptype:<8} | {data['avg_raw_score']:>10.1f} | {data['avg_final_score']:>10.1f} | {data['first_place_rate']*100:>7.1f}% | {data['last_place_rate']*100:>7.1f}%")

def run_all_tests(config: BalanceConfig, num_games: int = 2000):
    """运行所有测试场景"""
    print("\n" + "="*70)
    print("《功德轮回》核心版 v1.1 平衡测试")
    print("="*70)
    
    scenarios = [
        ([PlayerType.ALTRUIST] * 4, "全好人(4利他者)"),
        ([PlayerType.SELFISH] * 4, "全坏人(4自私者)"),
        ([PlayerType.NEUTRAL] * 4, "全中立(4中立者)"),
        ([PlayerType.ALTRUIST, PlayerType.ALTRUIST, PlayerType.ALTRUIST, PlayerType.SELFISH], "3好1坏"),
        ([PlayerType.ALTRUIST, PlayerType.ALTRUIST, PlayerType.SELFISH, PlayerType.SELFISH], "2好2坏"),
        ([PlayerType.ALTRUIST, PlayerType.SELFISH, PlayerType.SELFISH, PlayerType.SELFISH], "1好3坏"),
    ]
    
    results = []
    for types, label in scenarios:
        stats = run_scenario(config, types, num_games, label)
        print_scenario(stats)
        results.append(stats)
    
    # 总结
    print("\n" + "="*70)
    print("平衡性总结")
    print("="*70)
    
    all_good = results[0]["team_win_rate"]
    all_bad = results[1]["team_win_rate"]
    
    print(f"全好人胜率: {all_good*100:.1f}% (目标: 75-85%)")
    print(f"全坏人胜率: {all_bad*100:.1f}% (目标: <30%)")
    
    # 检查好人有好报
    if len(results) >= 5:
        mixed_stats = results[4]  # 2好2坏
        if "利他者" in mixed_stats["by_type"] and "自私者" in mixed_stats["by_type"]:
            good_score = mixed_stats["by_type"]["利他者"]["avg_final_score"]
            bad_score = mixed_stats["by_type"]["自私者"]["avg_final_score"]
            print(f"\n2好2坏场景:")
            print(f"  好人平均分: {good_score:.1f}")
            print(f"  坏人平均分: {bad_score:.1f}")
            if good_score > bad_score:
                print(f"  [OK] 好人有好报！(+{good_score - bad_score:.1f}分)")
            else:
                print(f"  [!!] 需要调整：坏人得分更高")
    
    return results

# ============== 主程序 ==============

def main():
    # 可调整的配置 - v6.0平衡参数（迭代2）
    config = BalanceConfig(
        # === 调整这些参数来达到目标胜率 ===
        # 目标：全好人~80%，全坏人<30%
        event_base_calamity=4,      # 每回合基础劫难（调高）
        event_b_extra_calamity=2,   # 选B每人额外劫难
        sacrifice_cost=2,
        sacrifice_merit=2,          # 选A功德奖励
        sacrifice_calamity=2,       # 选A劫难减免
        sacrifice_crisis_merit=4,   # 危急时选A额外功德（增加，让好人更有优势）
        sacrifice_poor_merit=5,     # 资源不足选A额外功德（增加）
        sacrifice_all_a_merit=2,    # 全员选A每人功德
        being_timeout_rounds=3,
        being_timeout_calamity=5,   # 超时劫难（恢复）
    )
    
    results = run_all_tests(config, num_games=3000)
    
    # 检查是否达标
    all_good = results[0]["team_win_rate"]
    all_bad = results[1]["team_win_rate"]
    
    print("\n" + "="*70)
    if 0.75 <= all_good <= 0.85 and all_bad < 0.30:
        print("✓ 平衡达标！")
    else:
        print("需要继续调整参数...")
        if all_good > 0.85:
            print("  - 全好人胜率太高，增加 event_base_calamity 或 being_timeout_calamity")
        elif all_good < 0.75:
            print("  - 全好人胜率太低，减少 event_base_calamity")
        if all_bad >= 0.30:
            print("  - 全坏人胜率太高，增加 event_b_extra_calamity")

if __name__ == "__main__":
    main()
