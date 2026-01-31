# -*- coding: utf-8 -*-
"""
《功德轮回》核心版 v1.0 平衡模拟器
去掉扩展包（皈依/大乘/菩萨愿/英雄时刻）的纯净核心版本
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

class Vow(Enum):
    # 农夫
    DILIGENT = "勤劳致功德"      # 简单, 功德≥16
    POOR_GIRL = "贫女一灯"       # 困难, 功德≥14且资≤12
    # 商人
    CHARITY = "资施功德"         # 简单, 布施≥6
    GREAT_MERCHANT = "大商人之心" # 困难, 功德≥26
    # 学者
    TEACHING = "传道授业"        # 简单, 慧≥18
    MASTER = "万世师表"          # 困难, 功德≥12且慧≥18
    # 僧侣
    ARHAT = "阿罗汉果"           # 简单, 慧≥12
    BODHISATTVA = "菩萨道"       # 困难, 功德≥20且渡化≥2

class ActionType(Enum):
    LABOR = "劳作"
    PRACTICE = "修行"
    DONATE = "布施"
    SAVE = "渡化"
    PROTECT = "护法"

# ============== 配置 ==============

@dataclass
class CoreConfig:
    """核心版游戏配置"""
    # 初始资源 (资粮, 功德, 慧) v1.1调整
    init_farmer: Tuple[int, int, int] = (5, 2, 3)
    init_merchant: Tuple[int, int, int] = (8, 2, 1)
    init_scholar: Tuple[int, int, int] = (4, 2, 5)
    init_monk: Tuple[int, int, int] = (2, 6, 6)  # v1.1: 增强僧侣（资1→2, 功德5→6, 慧5→6）
    
    # 行动效果
    labor_base: int = 3
    labor_farmer_bonus: int = 2  # 农夫+5
    practice_base: int = 2
    practice_scholar_bonus: int = 1  # 学者+3
    donate_cost: int = 2
    donate_merit: int = 1
    donate_calamity: int = 1
    donate_merchant_bonus: int = 2  # 商人布施+3功德
    protect_cost: int = 2
    protect_merit: int = 3
    protect_calamity: int = 3
    protect_monk_bonus: int = 2  # v1.1: 僧侣护法+5功德（1→2）
    
    # 渡化
    save_hui_requirement: int = 4  # 平均众生慧需求
    save_cost: int = 3  # 平均众生资粮成本
    save_merit: int = 3  # 平均众生功德奖励
    save_monk_cost_reduce: int = 1  # 僧侣成本-1
    
    # 集体事件
    disaster_calamity: int = 6
    sacrifice_cost: int = 2
    sacrifice_merit: int = 1
    sacrifice_calamity_reduce: int = 1
    sacrifice_bonus_threshold: int = 10  # 劫难≥10时选A额外+2功德
    sacrifice_bonus_merit: int = 2
    
    # 共业倍率
    karma_multiplier_levels: list = field(default_factory=lambda: [
        (4, 1.5),   # 劫难0-4: ×1.5
        (8, 1.2),   # 劫难5-8: ×1.2
        (12, 1.0),  # 劫难9-12: ×1.0
    ])
    
    # 发愿条件
    vow_diligent_merit: int = 16
    vow_poor_girl_merit: int = 14
    vow_poor_girl_wealth: int = 12
    vow_charity_donate: int = 6
    vow_great_merchant_merit: int = 26
    vow_teaching_hui: int = 18
    vow_master_merit: int = 12
    vow_master_hui: int = 18
    vow_arhat_hui: int = 10  # v1.1: 降低（12→10）让僧侣更容易达成
    vow_bodhisattva_merit: int = 20
    vow_bodhisattva_save: int = 2
    
    # 发愿分数
    vow_scores: dict = field(default_factory=lambda: {
        "勤劳致功德": (12, 0),
        "资施功德": (12, 0),
        "传道授业": (10, 0),
        "阿罗汉果": (14, 0),   # v1.1: 10→14 增强僧侣
        "贫女一灯": (18, 0),
        "大商人之心": (20, 0),
        "万世师表": (16, 0),
        "菩萨道": (20, 0),     # v1.1: 16→20 增强僧侣
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
    vow: Optional[Vow] = None
    
    # 行动统计
    labor_count: int = 0
    practice_count: int = 0
    donate_count: int = 0
    save_count: int = 0
    protect_count: int = 0
    sacrifice_count: int = 0  # 选A次数

# ============== 游戏状态 ==============

@dataclass
class GameState:
    config: CoreConfig
    players: List[Player]
    calamity: int = 0
    total_saves: int = 0
    current_round: int = 1

# ============== AI决策 ==============

class AIDecision:
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
    def choose_sacrifice(player: Player, calamity: int) -> bool:
        """选择是否牺牲（选A）"""
        # 基础概率50%
        prob = 0.5
        # 劫难高时更倾向选A
        if calamity >= 10:
            prob = 0.7
        elif calamity >= 15:
            prob = 0.85
        # 资源不足时倾向选B
        if player.wealth < 3:
            prob -= 0.2
        return random.random() < prob
    
    @staticmethod
    def choose_action(player: Player, state: GameState, actions_left: int) -> ActionType:
        """选择行动"""
        config = state.config
        role = player.role
        urgency = state.calamity / config.max_calamity
        
        # 职业特化行为
        if role == Role.FARMER:
            if state.current_round <= 3 and random.random() < 0.6:
                return ActionType.LABOR
            if player.hui >= config.save_hui_requirement and random.random() < 0.4:
                return ActionType.SAVE
        
        elif role == Role.MERCHANT:
            if player.wealth >= config.donate_cost and random.random() < 0.5:
                return ActionType.DONATE
            if player.wealth < 4 and random.random() < 0.6:
                return ActionType.LABOR
        
        elif role == Role.SCHOLAR:
            if player.hui < 15 and random.random() < 0.5:
                return ActionType.PRACTICE
            if player.hui >= config.save_hui_requirement and random.random() < 0.4:
                return ActionType.SAVE
        
        elif role == Role.MONK:
            if player.hui >= config.save_hui_requirement and random.random() < 0.5:
                return ActionType.SAVE
            if urgency > 0.4 and player.wealth >= config.protect_cost and random.random() < 0.4:
                return ActionType.PROTECT
            if player.wealth < 2 and random.random() < 0.5:
                return ActionType.LABOR
        
        # 通用逻辑
        if urgency > 0.4 and player.wealth >= config.protect_cost and random.random() < 0.3:
            return ActionType.PROTECT
        if player.wealth >= config.donate_cost and random.random() < 0.25:
            return ActionType.DONATE
        if random.random() < 0.3:
            return ActionType.PRACTICE
        
        return ActionType.LABOR

# ============== 游戏引擎 ==============

class CoreGameEngine:
    def __init__(self, config: CoreConfig):
        self.config = config
    
    def init_players(self) -> List[Player]:
        """初始化玩家"""
        init_resources = {
            Role.FARMER: self.config.init_farmer,
            Role.MERCHANT: self.config.init_merchant,
            Role.SCHOLAR: self.config.init_scholar,
            Role.MONK: self.config.init_monk,
        }
        
        players = []
        for role in Role:
            w, m, h = init_resources[role]
            player = Player(role=role, wealth=w, merit=m, hui=h)
            player.vow = AIDecision.choose_vow(player)
            players.append(player)
        
        return players
    
    def get_karma_multiplier(self, calamity: int) -> float:
        """获取共业倍率"""
        for threshold, multiplier in self.config.karma_multiplier_levels:
            if calamity <= threshold:
                return multiplier
        return 1.0
    
    def execute_action(self, player: Player, action: ActionType, state: GameState):
        """执行行动"""
        config = self.config
        
        if action == ActionType.LABOR:
            gain = config.labor_base
            if player.role == Role.FARMER:
                gain += config.labor_farmer_bonus
            player.wealth += gain
            player.labor_count += 1
        
        elif action == ActionType.PRACTICE:
            gain = config.practice_base
            if player.role == Role.SCHOLAR:
                gain += config.practice_scholar_bonus
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
                player.donate_count += 1
        
        elif action == ActionType.SAVE:
            if player.hui >= config.save_hui_requirement:
                cost = config.save_cost
                if player.role == Role.MONK:
                    cost -= config.save_monk_cost_reduce
                cost = max(1, cost)
                
                if player.wealth >= cost:
                    player.wealth -= cost
                    player.merit += config.save_merit
                    player.save_count += 1
                    state.total_saves += 1
        
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
    
    def process_collective_event(self, state: GameState):
        """处理集体事件"""
        config = self.config
        state.calamity += config.disaster_calamity
        
        # 玩家选择
        for p in state.players:
            if AIDecision.choose_sacrifice(p, state.calamity):
                # 选A：牺牲
                p.wealth -= config.sacrifice_cost
                p.wealth = max(0, p.wealth)
                p.merit += config.sacrifice_merit
                p.sacrifice_count += 1
                state.calamity -= config.sacrifice_calamity_reduce
                
                # 牺牲加成
                if state.calamity >= config.sacrifice_bonus_threshold:
                    p.merit += config.sacrifice_bonus_merit
        
        state.calamity = max(0, state.calamity)
    
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
            return player.merit >= config.vow_great_merchant_merit
        elif vow == Vow.TEACHING:
            return player.hui >= config.vow_teaching_hui
        elif vow == Vow.MASTER:
            return player.merit >= config.vow_master_merit and player.hui >= config.vow_master_hui
        elif vow == Vow.ARHAT:
            return player.hui >= config.vow_arhat_hui
        elif vow == Vow.BODHISATTVA:
            return player.merit >= config.vow_bodhisattva_merit and player.save_count >= config.vow_bodhisattva_save
        return False
    
    def calculate_score(self, player: Player, team_win: bool, vow_achieved: bool, calamity: int) -> int:
        """计算个人得分"""
        if not team_win:
            return 0
        
        config = self.config
        
        # 基础分 = 功德 + 慧
        base_score = player.merit + player.hui
        
        # 发愿奖励
        vow_score = 0
        if player.vow:
            vow_name = player.vow.value
            if vow_name in config.vow_scores:
                success_score, fail_score = config.vow_scores[vow_name]
                vow_score = success_score if vow_achieved else fail_score
        
        # 共业倍率
        karma_multiplier = self.get_karma_multiplier(calamity)
        
        # 最终分
        raw_score = base_score + vow_score
        final_score = int(raw_score * karma_multiplier)
        return max(0, final_score)
    
    def run_game(self) -> Dict:
        """运行一局游戏"""
        players = self.init_players()
        state = GameState(config=self.config, players=players)
        
        # 游戏循环
        for round_num in range(1, self.config.total_rounds + 1):
            state.current_round = round_num
            
            # 集体事件
            self.process_collective_event(state)
            
            # 检查立即失败
            if state.calamity >= self.config.max_calamity:
                break
            
            # 行动阶段
            for p in players:
                for _ in range(2):
                    action = AIDecision.choose_action(p, state, 2)
                    self.execute_action(p, action, state)
            
            # 回合结束：偶数回合消耗
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
            vow_achieved = self.check_vow(p, state) if p.vow else False
            personal_score = self.calculate_score(p, team_win, vow_achieved, state.calamity)
            
            result["players"].append({
                "role": p.role.value,
                "wealth": p.wealth,
                "merit": p.merit,
                "hui": p.hui,
                "vow": p.vow.value if p.vow else None,
                "vow_achieved": vow_achieved,
                "personal_score": personal_score,
                "labor_count": p.labor_count,
                "practice_count": p.practice_count,
                "donate_count": p.donate_count,
                "save_count": p.save_count,
                "protect_count": p.protect_count,
                "sacrifice_count": p.sacrifice_count,
            })
        
        # 排名
        if team_win:
            scores = [(i, result["players"][i]["personal_score"]) for i in range(4)]
            scores.sort(key=lambda x: -x[1])
            for rank, (idx, score) in enumerate(scores):
                result["players"][idx]["rank"] = rank + 1
        else:
            for p in result["players"]:
                p["rank"] = 0
        
        return result

# ============== 统计分析 ==============

class CoreBalanceAnalyzer:
    def __init__(self, config: CoreConfig, num_simulations: int = 5000):
        self.config = config
        self.num_simulations = num_simulations
        self.results = []
    
    def run_simulations(self):
        engine = CoreGameEngine(self.config)
        for i in range(self.num_simulations):
            if (i + 1) % 1000 == 0:
                print(f"  模拟进度: {i+1}/{self.num_simulations}")
            result = engine.run_game()
            self.results.append(result)
    
    def analyze(self) -> Dict:
        stats = {
            "total_games": len(self.results),
            "team_wins": 0,
            "avg_calamity": 0,
            "avg_saves": 0,
            "by_role": defaultdict(lambda: {
                "count": 0,
                "avg_merit": 0,
                "avg_hui": 0,
                "avg_score": 0,
                "vow_achieved": 0,
                "rank_1": 0,
                "rank_4": 0,
                "scores": [],
            }),
            "by_vow": defaultdict(lambda: {
                "count": 0,
                "achieved": 0,
            }),
        }
        
        total_calamity = 0
        total_saves = 0
        
        for result in self.results:
            if result["team_win"]:
                stats["team_wins"] += 1
            total_calamity += result["final_calamity"]
            total_saves += result["total_saves"]
            
            for p in result["players"]:
                role = p["role"]
                vow = p["vow"]
                
                stats["by_role"][role]["count"] += 1
                stats["by_role"][role]["avg_merit"] += p["merit"]
                stats["by_role"][role]["avg_hui"] += p["hui"]
                stats["by_role"][role]["avg_score"] += p["personal_score"]
                stats["by_role"][role]["scores"].append(p["personal_score"])
                
                if p["vow_achieved"]:
                    stats["by_role"][role]["vow_achieved"] += 1
                
                rank = p.get("rank", 0)
                if rank == 1:
                    stats["by_role"][role]["rank_1"] += 1
                elif rank == 4:
                    stats["by_role"][role]["rank_4"] += 1
                
                if vow:
                    stats["by_vow"][vow]["count"] += 1
                    if p["vow_achieved"]:
                        stats["by_vow"][vow]["achieved"] += 1
        
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
                stats["by_role"][role]["avg_score"] /= cnt
                stats["by_role"][role]["vow_rate"] = stats["by_role"][role]["vow_achieved"] / cnt
                stats["by_role"][role]["rank_1_rate"] = stats["by_role"][role]["rank_1"] / cnt
                stats["by_role"][role]["rank_4_rate"] = stats["by_role"][role]["rank_4"] / cnt
                
                scores = stats["by_role"][role]["scores"]
                avg = stats["by_role"][role]["avg_score"]
                variance = sum((s - avg) ** 2 for s in scores) / len(scores)
                stats["by_role"][role]["score_std"] = variance ** 0.5
                del stats["by_role"][role]["scores"]
        
        for vow in stats["by_vow"]:
            cnt = stats["by_vow"][vow]["count"]
            if cnt > 0:
                stats["by_vow"][vow]["rate"] = stats["by_vow"][vow]["achieved"] / cnt
        
        return stats
    
    def generate_report(self, stats: Dict) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("《功德轮回》核心版 v1.0 平衡分析报告")
        lines.append(f"模拟局数: {stats['total_games']}")
        lines.append("=" * 60)
        lines.append("")
        
        lines.append(f"【团队胜率】: {stats['team_win_rate']*100:.1f}%")
        lines.append(f"  平均劫难: {stats['avg_calamity']:.1f}")
        lines.append(f"  平均渡化: {stats['avg_saves']:.1f}")
        lines.append("")
        
        lines.append("【职业得分与排名】")
        lines.append("  职业    | 平均分 | 标准差 | 第1名率 | 第4名率 | 发愿达成")
        lines.append("  --------|--------|--------|---------|---------|----------")
        for role in ["农夫", "商人", "学者", "僧侣"]:
            if role in stats["by_role"]:
                r = stats["by_role"][role]
                lines.append(f"  {role}    | {r['avg_score']:6.1f} | {r.get('score_std', 0):6.1f} | {r['rank_1_rate']*100:6.1f}% | {r['rank_4_rate']*100:6.1f}% | {r['vow_rate']*100:.1f}%")
        lines.append("")
        
        lines.append("【职业资源统计】")
        for role in ["农夫", "商人", "学者", "僧侣"]:
            if role in stats["by_role"]:
                r = stats["by_role"][role]
                lines.append(f"  {role}: 功德={r['avg_merit']:.1f} 慧={r['avg_hui']:.1f}")
        lines.append("")
        
        lines.append("【发愿达成率】")
        for vow in stats["by_vow"]:
            v = stats["by_vow"][vow]
            lines.append(f"  {vow}: {v['achieved']}/{v['count']} = {v['rate']*100:.1f}%")
        lines.append("")
        
        # 平衡评估
        lines.append("【平衡性评估】")
        roles_data = [(role, stats["by_role"][role]) for role in ["农夫", "商人", "学者", "僧侣"]]
        avg_ranks = [1*r["rank_1_rate"] + 2*(1-r["rank_1_rate"]-r["rank_4_rate"])*0.5 + 2*(1-r["rank_1_rate"]-r["rank_4_rate"])*0.5 + 4*r["rank_4_rate"] for _, r in roles_data]
        
        max_score = max(r["avg_score"] for _, r in roles_data)
        min_score = min(r["avg_score"] for _, r in roles_data)
        score_diff = max_score - min_score
        
        if score_diff < 5:
            balance = "优秀"
        elif score_diff < 10:
            balance = "良好"
        elif score_diff < 15:
            balance = "一般"
        else:
            balance = "需调整"
        
        lines.append(f"  得分差距: {score_diff:.1f} ({balance})")
        lines.append("")
        
        lines.append("=" * 60)
        return "\n".join(lines)

# ============== 主程序 ==============

def main():
    print("《功德轮回》核心版 v1.0 平衡模拟器")
    print("=" * 50)
    
    config = CoreConfig()
    analyzer = CoreBalanceAnalyzer(config, num_simulations=5000)
    
    print("\n开始模拟...")
    analyzer.run_simulations()
    
    print("分析数据...")
    stats = analyzer.analyze()
    
    report = analyzer.generate_report(stats)
    print(report)
    
    # 保存报告
    with open("core_balance_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    # 转换defaultdict为普通dict
    def convert_dict(d):
        if isinstance(d, defaultdict):
            d = dict(d)
        if isinstance(d, dict):
            return {k: convert_dict(v) for k, v in d.items()}
        return d
    
    with open("core_balance_stats.json", "w", encoding="utf-8") as f:
        json.dump(convert_dict(stats), f, ensure_ascii=False, indent=2)
    
    print("\n报告已保存: core_balance_report.txt")

if __name__ == "__main__":
    main()
