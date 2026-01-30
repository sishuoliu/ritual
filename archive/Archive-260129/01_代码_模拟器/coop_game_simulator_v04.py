# -*- coding: utf-8 -*-
"""
功德轮回v0.4合作版模拟器
"""

import random
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
import statistics


class Role(Enum):
    MONK = "僧侣"
    NOBLE = "贵族"
    MERCHANT = "商人"
    FARMER = "农夫"


class VowType(Enum):
    SMALL = "小愿"
    MEDIUM = "中愿"
    LARGE = "大愿"


class PlayerStrategy(Enum):
    SELFISH = "自利型"  # 优先个人修行
    BALANCED = "平衡型"  # 平衡个人和团队
    ALTRUISTIC = "利他型"  # 优先团队


@dataclass
class Player:
    """玩家类"""
    name: str
    role: Role
    strategy: PlayerStrategy
    
    # 资源
    merit: int = 0  # 功德
    wealth: int = 0
    influence: int = 0
    
    # 特殊资源
    discipline: int = 0  # 戒律（僧侣）
    reputation: int = 0  # 声望（贵族）
    land: int = 0  # 土地
    trade_routes: int = 0  # 商路（商人）
    piety: int = 0  # 虔诚（农夫）
    
    # 三毒
    greed: int = 0  # 贪
    anger: int = 0  # 嗔
    delusion: int = 0  # 痴
    
    # 统计
    dharma_contribution: int = 0  # 护法贡献
    beings_saved: int = 0  # 渡化众生数
    temples_built: int = 0  # 建寺数
    
    # 发愿
    vow_type: VowType = None
    vow_points: int = 0
    vow_achieved: bool = False
    
    def __post_init__(self):
        """初始化角色起始资源"""
        if self.role == Role.MONK:
            self.merit = 6
            self.wealth = 2
            self.influence = 5
            self.discipline = 10
        elif self.role == Role.NOBLE:
            self.merit = 2
            self.wealth = 12
            self.influence = 6
            self.land = 1
            self.reputation = 2
        elif self.role == Role.MERCHANT:
            self.merit = 1
            self.wealth = 10
            self.influence = 3
            self.trade_routes = 1
        elif self.role == Role.FARMER:
            self.merit = 2
            self.wealth = 2
            self.influence = 1
            self.land = 1
            self.piety = 5


@dataclass
class Being:
    """众生卡"""
    name: str
    difficulty: int  # 苦难值
    wealth_needed: int = 0
    roles_needed: List[Role] = field(default_factory=list)
    dharma_reduction: int = 0  # 完成后降低劫难
    merit_reward: int = 0  # 完成后功德奖励
    turns_waiting: int = 0  # 等待轮数
    
    def can_complete(self, game_state) -> bool:
        """检查是否可以完成渡化"""
        # 简化判定：检查是否有足够财富和所需角色
        total_wealth = sum(p.wealth for p in game_state.players)
        has_roles = all(any(p.role == r for p in game_state.players) for r in self.roles_needed)
        return total_wealth >= self.wealth_needed and has_roles


class GameState:
    """游戏状态"""
    def __init__(self, players: List[Player], difficulty: str = "标准"):
        self.players = players
        self.round = 0
        self.dharma_disaster = 0  # 劫难指数
        self.beings_saved_count = 0  # 渡化众生计数
        self.temples = 0  # 建寺数
        self.beings_failed = 0  # 渡化失败数
        self.active_beings: List[Being] = []  # 当前场上的众生卡
        self.difficulty = difficulty
        
        # 难度设置
        if difficulty == "简单":
            self.dharma_per_round = 3
            self.dharma_win_threshold = 15
        elif difficulty == "困难":
            self.dharma_per_round = 7
            self.dharma_win_threshold = 10
        else:  # 标准
            self.dharma_per_round = 5
            self.dharma_win_threshold = 10
    
    def check_team_victory(self) -> Tuple[bool, str]:
        """检查团队胜利条件"""
        conditions = []
        
        # 条件1：劫难≤10
        cond1 = self.dharma_disaster <= self.dharma_win_threshold
        conditions.append(f"劫难{self.dharma_disaster}{'≤' if cond1 else '>'}{self.dharma_win_threshold}")
        
        # 条件2：渡化众生≥6
        cond2 = self.beings_saved_count >= 6
        conditions.append(f"渡化{self.beings_saved_count}{'≥' if cond2 else '<'}6")
        
        # 条件3：建寺≥3
        cond3 = self.temples >= 3
        conditions.append(f"建寺{self.temples}{'≥' if cond3 else '<'}3")
        
        # 条件4：所有玩家功德≥15
        cond4 = all(p.merit >= 15 for p in self.players)
        min_merit = min(p.merit for p in self.players)
        conditions.append(f"最低功德{min_merit}{'≥' if cond4 else '<'}15")
        
        victory = cond1 and cond2 and cond3 and cond4
        return victory, " | ".join(conditions)
    
    def check_team_failure(self) -> Tuple[bool, str]:
        """检查团队失败条件"""
        # 失败1：劫难≥50
        if self.dharma_disaster >= 50:
            return True, f"劫难{self.dharma_disaster}≥50，世界毁灭"
        
        # 失败2：任意玩家功德<5
        for p in self.players:
            if p.merit < 5:
                return True, f"{p.name}功德{p.merit}<5，有人堕入恶道"
        
        # 失败3：渡化失败≥4
        if self.beings_failed >= 4:
            return True, f"渡化失败{self.beings_failed}≥4，失去慈悲心"
        
        # 失败4：任意玩家三毒≥20
        for p in self.players:
            if p.greed + p.anger + p.delusion >= 20:
                return True, f"{p.name}三毒{p.greed+p.anger+p.delusion}≥20，堕入魔道"
        
        return False, ""


def roll_dice(num_dice: int = 2, modifier: int = 0) -> int:
    """掷骰子"""
    result = sum(random.randint(1, 6) for _ in range(num_dice))
    return max(2, min(12, result + modifier))


def select_vow(player: Player) -> None:
    """选择发愿"""
    if player.strategy == PlayerStrategy.SELFISH:
        # 自利型选择小愿
        player.vow_type = VowType.SMALL
        player.vow_points = random.choice([10, 11, 12])
    elif player.strategy == PlayerStrategy.BALANCED:
        # 平衡型选择中愿
        player.vow_type = VowType.MEDIUM
        player.vow_points = random.choice([16, 17, 18, 19, 20])
    else:  # ALTRUISTIC
        # 利他型选择大愿
        player.vow_type = VowType.LARGE
        player.vow_points = random.choice([28, 29, 30])


def player_action(player: Player, game_state: GameState) -> None:
    """玩家行动（每轮2个行动）"""
    for action_num in range(2):
        # 根据策略选择行动
        if player.strategy == PlayerStrategy.SELFISH:
            # 自利型：优先个人修行
            if player.role == Role.MONK and player.discipline < 10:
                # 修行
                player.merit += 2
                player.delusion = max(0, player.delusion - 1)
            elif player.role == Role.MERCHANT:
                # 贸易
                income = player.trade_routes * 2
                player.wealth += income
                if income >= 5:
                    player.greed += 1
            else:
                # 修行
                player.merit += 2
                player.delusion = max(0, player.delusion - 1)
        
        elif player.strategy == PlayerStrategy.BALANCED:
            # 平衡型：50%个人，50%团队
            if action_num == 0:
                # 第1个行动：个人修行
                if player.role == Role.MERCHANT and player.trade_routes < 3:
                    # 开辟商路
                    if player.wealth >= 6:
                        player.wealth -= 6
                        player.trade_routes += 1
                else:
                    player.merit += 2
            else:
                # 第2个行动：团队贡献
                if game_state.dharma_disaster >= 30:
                    # 护法
                    dharma_protection(player, game_state)
                elif len(game_state.active_beings) > 0:
                    # 尝试渡化众生
                    attempt_save_being(player, game_state)
                else:
                    player.merit += 2
        
        else:  # ALTRUISTIC
            # 利他型：优先团队
            if game_state.dharma_disaster >= 25:
                # 护法
                dharma_protection(player, game_state)
            elif len(game_state.active_beings) > 0:
                # 尝试渡化众生
                attempt_save_being(player, game_state)
            elif game_state.temples < 3 and can_build_temple(player):
                # 建寺
                build_temple(player, game_state)
            else:
                # 修行
                player.merit += 2


def dharma_protection(player: Player, game_state: GameState) -> None:
    """护法行动（降低劫难）"""
    reduction = 0
    cost_paid = False
    
    if player.role == Role.MONK:
        # 僧侣讲经
        if player.influence >= 1:
            player.influence -= 1
            reduction = 2
            cost_paid = True
            # 所有玩家+1功德
            for p in game_state.players:
                p.merit += 1
    elif player.role == Role.NOBLE:
        # 贵族赈灾
        if player.wealth >= 8:
            player.wealth -= 8
            reduction = 5
            cost_paid = True
            player.merit += 3
            player.reputation += 2
    elif player.role == Role.MERCHANT:
        # 商人捐资
        if player.wealth >= 10:
            player.wealth -= 10
            reduction = 4
            cost_paid = True
            player.merit += 2
    elif player.role == Role.FARMER:
        # 农夫祈福
        reduction = 2
        cost_paid = True
        player.piety += 1
    
    if cost_paid:
        game_state.dharma_disaster = max(0, game_state.dharma_disaster - reduction)
        player.dharma_contribution += reduction


def attempt_save_being(player: Player, game_state: GameState) -> None:
    """尝试渡化众生"""
    if not game_state.active_beings:
        return
    
    # 选择第一个众生尝试渡化
    being = game_state.active_beings[0]
    
    # 简化判定：贡献财富
    if player.wealth >= being.wealth_needed:
        # 完成渡化
        player.wealth -= being.wealth_needed
        player.merit += being.merit_reward
        player.beings_saved += 1
        game_state.dharma_disaster = max(0, game_state.dharma_disaster - being.dharma_reduction)
        game_state.beings_saved_count += 1
        game_state.active_beings.remove(being)


def can_build_temple(player: Player) -> bool:
    """检查是否可以建寺"""
    return player.wealth >= 10 and player.influence >= 5


def build_temple(player: Player, game_state: GameState) -> None:
    """建寺"""
    if can_build_temple(player):
        player.wealth -= 10
        player.influence -= 5
        player.merit += 2
        player.temples_built += 1
        game_state.temples += 1
        # 所有人+1功德
        for p in game_state.players:
            p.merit += 1


def event_phase(game_state: GameState) -> None:
    """事件阶段"""
    # 1. 翻开2张众生卡
    if random.random() < 0.7:  # 70%概率出现众生卡
        new_being = Being(
            name=f"众生{game_state.round}",
            difficulty=random.randint(5, 12),
            wealth_needed=random.randint(4, 10),
            dharma_reduction=random.randint(2, 5),
            merit_reward=random.randint(2, 4)
        )
        game_state.active_beings.append(new_being)
    
    # 2. 专属事件（简化）
    for player in game_state.players:
        # 随机事件，50%正面50%负面
        event_roll = roll_dice(2)
        if event_roll >= 8:
            # 正面事件
            player.merit += random.randint(1, 3)
            player.wealth += random.randint(0, 2)
        elif event_roll <= 5:
            # 负面事件
            player.merit -= 1
            player.merit = max(0, player.merit)


def disaster_phase(game_state: GameState) -> None:
    """劫难阶段"""
    # 劫难递增
    game_state.dharma_disaster += game_state.dharma_per_round
    
    # 检查众生卡超时
    for being in list(game_state.active_beings):
        being.turns_waiting += 1
        if being.turns_waiting >= 3:
            # 渡化失败
            game_state.active_beings.remove(being)
            game_state.beings_failed += 1
            game_state.dharma_disaster += 5
    
    # 灾难效果
    if game_state.dharma_disaster >= 20:
        # 刀兵劫
        victim = random.choice(game_state.players)
        victim.wealth = max(0, victim.wealth - 3)
        victim.merit = max(0, victim.merit - 2)
    
    if game_state.dharma_disaster >= 35:
        # 瘟疫劫
        for p in game_state.players:
            p.merit = max(0, p.merit - 1)


def calculate_final_score(player: Player, game_state: GameState) -> int:
    """计算个人最终分数"""
    score = player.merit * 2
    
    # 发愿达成
    if player.vow_achieved:
        score += player.vow_points
    elif player.vow_type == VowType.LARGE:
        score -= 10  # 大愿失败惩罚
    
    # 特殊成就
    if player.dharma_contribution >= 15:
        score += 5
    if player.beings_saved >= 3:
        score += 5
    if player.temples_built >= 2:
        score += 5
    
    # 虔诚/声望奖励
    if player.role == Role.FARMER and player.piety >= 20:
        score += 10
    if player.role == Role.NOBLE and player.reputation >= 15:
        score += 8
    
    # 惩罚
    if player.dharma_contribution < 10:
        score = int(score * 0.5)  # 团队拖累
    
    if player.greed >= 10 or player.anger >= 10 or player.delusion >= 10:
        # 三毒过重，最多只能得凡夫
        score = min(score, 19)
    
    return score


def check_vow_achievement(player: Player, game_state: GameState) -> None:
    """检查发愿是否达成"""
    if player.vow_type == VowType.SMALL:
        # 小愿：功德≥25（简化）
        if player.merit >= 25:
            player.vow_achieved = True
    elif player.vow_type == VowType.MEDIUM:
        # 中愿：渡化众生≥4或功德≥20
        if player.beings_saved >= 4 or player.merit >= 20:
            player.vow_achieved = True
    elif player.vow_type == VowType.LARGE:
        # 大愿：所有玩家功德≥20
        if all(p.merit >= 20 for p in game_state.players):
            player.vow_achieved = True


def simulate_game(strategies: List[PlayerStrategy], difficulty: str = "标准", verbose: bool = False) -> Dict:
    """模拟一局游戏"""
    # 创建玩家
    roles = [Role.MONK, Role.NOBLE, Role.MERCHANT, Role.FARMER]
    players = [
        Player(name=f"{role.value}", role=role, strategy=strategy)
        for role, strategy in zip(roles, strategies)
    ]
    
    # 初始化游戏状态
    game_state = GameState(players, difficulty)
    
    # 选择发愿
    for player in players:
        select_vow(player)
    
    # 游戏主循环（8轮）
    for round_num in range(1, 9):
        game_state.round = round_num
        
        if verbose:
            print(f"\n===== 第{round_num}轮 =====")
            print(f"劫难：{game_state.dharma_disaster}  渡化：{game_state.beings_saved_count}  建寺：{game_state.temples}")
        
        # 阶段1：协商（简化，AI自动决策）
        # 阶段2：行动阶段
        for player in players:
            player_action(player, game_state)
        
        # 阶段3：事件阶段
        event_phase(game_state)
        
        # 阶段4：劫难阶段
        disaster_phase(game_state)
        
        # 检查失败条件
        failed, reason = game_state.check_team_failure()
        if failed:
            if verbose:
                print(f"\n【游戏失败】{reason}")
            return {
                "victory": False,
                "reason": reason,
                "final_dharma": game_state.dharma_disaster,
                "beings_saved": game_state.beings_saved_count,
                "temples": game_state.temples,
                "rounds_survived": round_num,
                "player_scores": [0] * len(players)
            }
    
    # 游戏结束，检查胜利条件
    victory, conditions = game_state.check_team_victory()
    
    if verbose:
        print(f"\n===== 游戏结束 =====")
        print(f"胜利条件：{conditions}")
        print(f"结果：{'胜利' if victory else '失败'}")
    
    # 计算个人分数
    for player in game_state.players:
        check_vow_achievement(player, game_state)
    
    scores = [calculate_final_score(p, game_state) for p in game_state.players]
    
    if verbose:
        for player, score in zip(game_state.players, scores):
            fruit = "佛果" if score >= 50 else "菩萨" if score >= 40 else "阿罗汉" if score >= 30 else "初果" if score >= 20 else "凡夫"
            print(f"{player.name}({player.strategy.value})：{score}分 - {fruit}")
    
    return {
        "victory": victory,
        "reason": conditions if victory else "未满足全部胜利条件",
        "final_dharma": game_state.dharma_disaster,
        "beings_saved": game_state.beings_saved_count,
        "temples": game_state.temples,
        "rounds_survived": 8,
        "player_scores": scores
    }


def run_test_suite():
    """运行测试套件"""
    print("=" * 80)
    print("功德轮回v0.4合作版 - 平衡性测试")
    print("=" * 80)
    
    # 测试方案
    test_configs = [
        {
            "name": "全自利型",
            "strategies": [PlayerStrategy.SELFISH] * 4,
            "description": "所有人只顾自己修行"
        },
        {
            "name": "全利他型",
            "strategies": [PlayerStrategy.ALTRUISTIC] * 4,
            "description": "所有人优先团队"
        },
        {
            "name": "全平衡型",
            "strategies": [PlayerStrategy.BALANCED] * 4,
            "description": "所有人平衡个人和团队"
        },
        {
            "name": "混合型A",
            "strategies": [PlayerStrategy.ALTRUISTIC, PlayerStrategy.BALANCED, 
                          PlayerStrategy.BALANCED, PlayerStrategy.SELFISH],
            "description": "1利他+2平衡+1自利"
        },
        {
            "name": "混合型B",
            "strategies": [PlayerStrategy.ALTRUISTIC, PlayerStrategy.ALTRUISTIC, 
                          PlayerStrategy.BALANCED, PlayerStrategy.SELFISH],
            "description": "2利他+1平衡+1自利"
        },
        {
            "name": "极端混合",
            "strategies": [PlayerStrategy.ALTRUISTIC, PlayerStrategy.ALTRUISTIC, 
                          PlayerStrategy.SELFISH, PlayerStrategy.SELFISH],
            "description": "2利他+2自利"
        },
    ]
    
    # 每种配置测试次数
    tests_per_config = 100
    
    results_summary = []
    
    for config in test_configs:
        print(f"\n{'='*80}")
        print(f"测试配置：{config['name']}")
        print(f"说明：{config['description']}")
        print(f"策略：{' | '.join([s.value for s in config['strategies']])}")
        print(f"测试次数：{tests_per_config}")
        print(f"{'='*80}")
        
        victories = 0
        total_dharma = []
        total_beings = []
        total_temples = []
        all_scores = [[] for _ in range(4)]
        failure_reasons = {}
        
        for test_num in range(tests_per_config):
            result = simulate_game(config['strategies'], difficulty="标准", verbose=False)
            
            if result['victory']:
                victories += 1
            else:
                reason = result['reason'].split("|")[0].strip()  # 取第一个失败原因
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
            
            total_dharma.append(result['final_dharma'])
            total_beings.append(result['beings_saved'])
            total_temples.append(result['temples'])
            
            for i, score in enumerate(result['player_scores']):
                all_scores[i].append(score)
        
        # 统计结果
        win_rate = victories / tests_per_config * 100
        avg_dharma = statistics.mean(total_dharma)
        avg_beings = statistics.mean(total_beings)
        avg_temples = statistics.mean(total_temples)
        
        print(f"\n【团队表现】")
        print(f"胜率：{win_rate:.1f}% ({victories}/{tests_per_config})")
        print(f"平均劫难：{avg_dharma:.1f}")
        print(f"平均渡化：{avg_beings:.1f}")
        print(f"平均建寺：{avg_temples:.1f}")
        
        if failure_reasons:
            print(f"\n【失败原因分布】")
            for reason, count in sorted(failure_reasons.items(), key=lambda x: -x[1])[:3]:
                print(f"  {reason}：{count}次 ({count/tests_per_config*100:.1f}%)")
        
        print(f"\n【个人表现】")
        roles = ["僧侣", "贵族", "商人", "农夫"]
        for i, (role, strat) in enumerate(zip(roles, config['strategies'])):
            avg_score = statistics.mean(all_scores[i])
            std_score = statistics.stdev(all_scores[i]) if len(all_scores[i]) > 1 else 0
            print(f"{role}({strat.value})：平均{avg_score:.1f}分 (±{std_score:.1f})")
        
        results_summary.append({
            "config": config['name'],
            "win_rate": win_rate,
            "avg_dharma": avg_dharma,
            "avg_beings": avg_beings,
            "avg_temples": avg_temples,
            "avg_scores": [statistics.mean(scores) for scores in all_scores]
        })
    
    # 总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}")
    print(f"\n{'配置':<12} {'胜率':<8} {'劫难':<8} {'渡化':<8} {'建寺':<8} {'平均分':<8}")
    print("-" * 80)
    for result in results_summary:
        avg_score = statistics.mean(result['avg_scores'])
        print(f"{result['config']:<12} {result['win_rate']:<8.1f} {result['avg_dharma']:<8.1f} "
              f"{result['avg_beings']:<8.1f} {result['avg_temples']:<8.1f} {avg_score:<8.1f}")
    
    print(f"\n{'='*80}")
    print("测试完成")
    print(f"{'='*80}")


if __name__ == "__main__":
    # 运行测试
    run_test_suite()
    
    # 运行一局详细演示
    print("\n\n" + "="*80)
    print("详细演示（全平衡型）")
    print("="*80)
    simulate_game([PlayerStrategy.BALANCED] * 4, verbose=True)
