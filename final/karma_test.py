# -*- coding: utf-8 -*-
"""
共业倍率机制测试：好人有好报，坏人有恶报？

测试策略：
- 利他型（好人）：集体事件80%选A（牺牲），积极帮助团队
- 自私型（坏人）：集体事件80%选B（保全），搭便车
- 中庸型（普通人）：50%选A，50%选B
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from collections import defaultdict

# ============== 配置 ==============

@dataclass
class TestConfig:
    """测试配置"""
    # 初始资源 (资粮, 功德, 慧)
    init_resources: Tuple[int, int, int] = (5, 3, 4)  # 平均值
    
    # 行动效果
    labor_gain: int = 4
    practice_gain: int = 3
    donate_cost: int = 2
    donate_merit: int = 2
    donate_calamity: int = 1
    save_cost: int = 4
    save_merit: int = 3
    protect_cost: int = 2
    protect_merit: int = 3
    protect_calamity: int = 2  # 降低护法效果
    
    # 集体事件（增加压力）
    event_calamity: int = 8  # 6→8 增加劫难压力
    sacrifice_cost: int = 2  # 选A的资源代价
    sacrifice_merit: int = 2  # 1→2 选A的功德奖励
    sacrifice_calamity_reduce: int = 2  # 1→2 每人选A减少的劫难（更重要）
    
    # 共业倍率
    karma_multiplier_levels: list = field(default_factory=lambda: [
        (4, 1.5),   # 劫难0-4: ×1.5
        (8, 1.2),   # 劫难5-8: ×1.2
        (12, 1.0),  # 劫难9-12: ×1.0
    ])
    
    # 牺牲加成
    sacrifice_bonus_threshold: int = 10  # 劫难≥10时选A额外+2功德
    sacrifice_bonus_merit: int = 2
    
    # 胜利条件
    max_calamity: int = 20
    win_calamity: int = 12
    total_rounds: int = 6

# ============== 玩家类型 ==============

class PlayerType:
    ALTRUIST = "利他型（好人）"  # 80%选A
    SELFISH = "自私型（坏人）"   # 80%选B
    NEUTRAL = "中庸型（普通人）" # 50%选A

@dataclass
class Player:
    name: str
    player_type: str
    wealth: int = 0
    merit: int = 0
    hui: int = 0
    sacrifice_count: int = 0  # 选A次数
    selfish_count: int = 0    # 选B次数

# ============== 游戏模拟 ==============

class KarmaTestEngine:
    def __init__(self, config: TestConfig):
        self.config = config
    
    def get_karma_multiplier(self, calamity: int) -> float:
        """获取共业倍率"""
        for threshold, multiplier in self.config.karma_multiplier_levels:
            if calamity <= threshold:
                return multiplier
        return 1.0
    
    def player_choose_sacrifice(self, player: Player, calamity: int) -> bool:
        """玩家选择是否牺牲（选A）"""
        if player.player_type == PlayerType.ALTRUIST:
            return random.random() < 0.8  # 80%选A
        elif player.player_type == PlayerType.SELFISH:
            return random.random() < 0.2  # 20%选A（80%选B）
        else:
            return random.random() < 0.5  # 50%选A
    
    def run_game(self, player_types: List[str]) -> Dict:
        """运行一局游戏"""
        config = self.config
        
        # 初始化玩家
        players = []
        for i, ptype in enumerate(player_types):
            p = Player(
                name=f"玩家{i+1}",
                player_type=ptype,
                wealth=config.init_resources[0],
                merit=config.init_resources[1],
                hui=config.init_resources[2]
            )
            players.append(p)
        
        calamity = 0
        
        # 游戏循环
        for round_num in range(1, config.total_rounds + 1):
            # 集体事件
            calamity += config.event_calamity
            
            sacrifice_count = 0
            for p in players:
                if self.player_choose_sacrifice(p, calamity):
                    # 选A：牺牲
                    p.wealth -= config.sacrifice_cost
                    p.merit += config.sacrifice_merit
                    p.sacrifice_count += 1
                    sacrifice_count += 1
                    
                    # 牺牲加成：劫难≥10时额外功德
                    if calamity >= config.sacrifice_bonus_threshold:
                        p.merit += config.sacrifice_bonus_merit
                else:
                    # 选B：保全
                    p.selfish_count += 1
            
            # 选A的人降低劫难
            calamity -= sacrifice_count * config.sacrifice_calamity_reduce
            calamity = max(0, calamity)
            
            # 检查立即失败
            if calamity >= config.max_calamity:
                break
            
            # 行动阶段（简化：每人2次行动，随机选择）
            for p in players:
                for _ in range(2):
                    if p.wealth < 2:
                        # 资源不足，劳作
                        p.wealth += config.labor_gain
                    elif random.random() < 0.3:
                        # 30%布施
                        p.wealth -= config.donate_cost
                        p.merit += config.donate_merit
                        calamity -= config.donate_calamity
                    elif random.random() < 0.3:
                        # 30%护法
                        p.wealth -= config.protect_cost
                        p.merit += config.protect_merit
                        calamity -= config.protect_calamity
                    else:
                        # 40%修行或劳作
                        if random.random() < 0.5:
                            p.hui += config.practice_gain
                        else:
                            p.wealth += config.labor_gain
            
            calamity = max(0, calamity)
        
        # 计算结果
        team_win = calamity <= config.win_calamity
        karma_multiplier = self.get_karma_multiplier(calamity) if team_win else 0
        
        result = {
            "team_win": team_win,
            "final_calamity": calamity,
            "karma_multiplier": karma_multiplier,
            "players": []
        }
        
        for p in players:
            # 基础分 = 功德 + 慧
            base_score = p.merit + p.hui
            
            # 最终分 = 基础分 × 共业倍率
            final_score = int(base_score * karma_multiplier) if team_win else 0
            
            result["players"].append({
                "name": p.name,
                "type": p.player_type,
                "merit": p.merit,
                "hui": p.hui,
                "base_score": base_score,
                "final_score": final_score,
                "sacrifice_count": p.sacrifice_count,
                "selfish_count": p.selfish_count,
            })
        
        return result

# ============== 测试场景 ==============

def run_scenario(name: str, player_types: List[str], num_games: int = 5000):
    """运行测试场景"""
    config = TestConfig()
    engine = KarmaTestEngine(config)
    
    # 统计
    stats = {
        "wins": 0,
        "by_type": defaultdict(lambda: {
            "count": 0,
            "total_base": 0,
            "total_final": 0,
            "rank_1": 0,
            "rank_4": 0,
            "sacrifice": 0,
            "selfish": 0,
        })
    }
    
    for _ in range(num_games):
        result = engine.run_game(player_types)
        
        if result["team_win"]:
            stats["wins"] += 1
        
        # 按最终分排名
        players = result["players"]
        players_sorted = sorted(players, key=lambda x: -x["final_score"])
        
        for rank, p in enumerate(players_sorted):
            ptype = p["type"]
            stats["by_type"][ptype]["count"] += 1
            stats["by_type"][ptype]["total_base"] += p["base_score"]
            stats["by_type"][ptype]["total_final"] += p["final_score"]
            stats["by_type"][ptype]["sacrifice"] += p["sacrifice_count"]
            stats["by_type"][ptype]["selfish"] += p["selfish_count"]
            
            if rank == 0:
                stats["by_type"][ptype]["rank_1"] += 1
            if rank == len(players) - 1:
                stats["by_type"][ptype]["rank_4"] += 1
    
    # 输出结果
    print(f"\n{'='*60}")
    print(f"场景：{name}")
    print(f"模拟局数：{num_games}")
    print(f"团队胜率：{stats['wins']/num_games*100:.1f}%")
    print(f"{'='*60}")
    print(f"{'类型':<20} | {'平均基础分':>10} | {'平均最终分':>10} | {'第1名率':>8} | {'选A次数':>8}")
    print(f"{'-'*60}")
    
    for ptype in player_types:
        if ptype in stats["by_type"]:
            s = stats["by_type"][ptype]
            cnt = s["count"]
            if cnt > 0:
                avg_base = s["total_base"] / cnt
                avg_final = s["total_final"] / cnt
                rank1_rate = s["rank_1"] / cnt * 100
                avg_sacrifice = s["sacrifice"] / cnt
                print(f"{ptype:<20} | {avg_base:>10.1f} | {avg_final:>10.1f} | {rank1_rate:>7.1f}% | {avg_sacrifice:>8.1f}")
    
    return stats

def main():
    print("="*60)
    print("《功德轮回》共业倍率机制测试")
    print("验证：好人有好报，坏人有恶报？")
    print("="*60)
    
    # 场景1：1个好人 vs 3个坏人
    print("\n" + "="*60)
    print("【场景1】1个好人 vs 3个坏人")
    print("测试：孤独的好人能否战胜自私的群体？")
    run_scenario(
        "1好人 vs 3坏人",
        [PlayerType.ALTRUIST, PlayerType.SELFISH, PlayerType.SELFISH, PlayerType.SELFISH],
        5000
    )
    
    # 场景2：1个坏人 vs 3个好人
    print("\n" + "="*60)
    print("【场景2】1个坏人 vs 3个好人")
    print("测试：搭便车的坏人能否占便宜？")
    run_scenario(
        "1坏人 vs 3好人",
        [PlayerType.SELFISH, PlayerType.ALTRUIST, PlayerType.ALTRUIST, PlayerType.ALTRUIST],
        5000
    )
    
    # 场景3：2好人 vs 2坏人
    print("\n" + "="*60)
    print("【场景3】2个好人 vs 2个坏人")
    print("测试：势均力敌时谁会赢？")
    run_scenario(
        "2好人 vs 2坏人",
        [PlayerType.ALTRUIST, PlayerType.ALTRUIST, PlayerType.SELFISH, PlayerType.SELFISH],
        5000
    )
    
    # 场景4：全是好人
    print("\n" + "="*60)
    print("【场景4】全是好人")
    print("测试：理想社会的表现")
    run_scenario(
        "4好人",
        [PlayerType.ALTRUIST, PlayerType.ALTRUIST, PlayerType.ALTRUIST, PlayerType.ALTRUIST],
        5000
    )
    
    # 场景5：全是坏人
    print("\n" + "="*60)
    print("【场景5】全是坏人")
    print("测试：自私社会的结局")
    run_scenario(
        "4坏人",
        [PlayerType.SELFISH, PlayerType.SELFISH, PlayerType.SELFISH, PlayerType.SELFISH],
        5000
    )
    
    # 总结
    print("\n" + "="*60)
    print("【结论分析】")
    print("="*60)
    print("""
关键观察点：
1. 1好人vs3坏人：好人能否靠高倍率弥补？
2. 1坏人vs3好人：坏人能否搭便车成功？
3. 2vs2：势均力敌时的博弈结果
4. 全好人：团队胜率和得分倍率
5. 全坏人：团队是否能赢？

如果机制设计正确，应该看到：
- 好人在团队成功时得分更高（因为帮助降低劫难→高倍率）
- 坏人在团队勉强成功时得分较低（低倍率惩罚搭便车）
- 全坏人团队很难成功（没人愿意牺牲→劫难爆表）
""")

if __name__ == "__main__":
    main()
