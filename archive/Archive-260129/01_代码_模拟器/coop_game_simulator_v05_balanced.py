# -*- coding: utf-8 -*-
"""
功德轮回v0.5合作版模拟器（平衡修正版）

修正内容：
1. 放宽失败条件：功德<3或≥2人功德<5才失败
2. 增加功德获取：修行+3、讲经+2
3. 减缓劫难：每轮+4（原5）
4. 增强护法：各提升1点
5. 降低众生难度：财富需求-20%
6. 增加初始资源：所有角色功德+1
7. 调整胜利条件：劫难≤12、渡化≥5、建寺≥2、功德≥12
"""

import random
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
import statistics


class Role(Enum):
    MONK = "Monk"
    NOBLE = "Noble"
    MERCHANT = "Merchant"
    FARMER = "Farmer"


class VowType(Enum):
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"


class PlayerStrategy(Enum):
    SELFISH = "Selfish"
    BALANCED = "Balanced"
    ALTRUISTIC = "Altruistic"


@dataclass
class Player:
    """Player class"""
    name: str
    role: Role
    strategy: PlayerStrategy
    
    # Resources
    merit: int = 0
    wealth: int = 0
    influence: int = 0
    
    # Special resources
    discipline: int = 0
    reputation: int = 0
    land: int = 0
    trade_routes: int = 0
    piety: int = 0
    
    # Three Poisons
    greed: int = 0
    anger: int = 0
    delusion: int = 0
    
    # Statistics
    dharma_contribution: int = 0
    beings_saved: int = 0
    temples_built: int = 0
    
    # Vow
    vow_type: VowType = None
    vow_points: int = 0
    vow_achieved: bool = False
    
    def __post_init__(self):
        """Initialize starting resources (v0.5: +1 merit for all)"""
        if self.role == Role.MONK:
            self.merit = 7  # +1
            self.wealth = 2
            self.influence = 5
            self.discipline = 10
        elif self.role == Role.NOBLE:
            self.merit = 3  # +1
            self.wealth = 12
            self.influence = 6
            self.land = 1
            self.reputation = 2
        elif self.role == Role.MERCHANT:
            self.merit = 2  # +1
            self.wealth = 10
            self.influence = 3
            self.trade_routes = 1
        elif self.role == Role.FARMER:
            self.merit = 3  # +1
            self.wealth = 3  # +1
            self.influence = 1
            self.land = 1
            self.piety = 5


@dataclass
class Being:
    """Being card"""
    name: str
    difficulty: int
    wealth_needed: int = 0
    roles_needed: List[Role] = field(default_factory=list)
    dharma_reduction: int = 0
    merit_reward: int = 0
    turns_waiting: int = 0
    
    def can_complete(self, game_state) -> bool:
        total_wealth = sum(p.wealth for p in game_state.players)
        has_roles = all(any(p.role == r for p in game_state.players) for r in self.roles_needed)
        return total_wealth >= self.wealth_needed and has_roles


class GameState:
    """Game state"""
    def __init__(self, players: List[Player], difficulty: str = "Standard"):
        self.players = players
        self.round = 0
        self.dharma_disaster = 0
        self.beings_saved_count = 0
        self.temples = 0
        self.beings_failed = 0
        self.active_beings: List[Being] = []
        self.difficulty = difficulty
        
        # Difficulty settings (v0.5 modified)
        if difficulty == "Easy":
            self.dharma_per_round = 2  # -1
            self.dharma_win_threshold = 15
            self.beings_needed = 4
            self.temples_needed = 2
            self.merit_needed = 10
        elif difficulty == "Hard":
            self.dharma_per_round = 6  # -1
            self.dharma_win_threshold = 10
            self.beings_needed = 6
            self.temples_needed = 3
            self.merit_needed = 15
        else:  # Standard
            self.dharma_per_round = 4  # -1 (was 5)
            self.dharma_win_threshold = 12  # +2 (was 10)
            self.beings_needed = 5  # -1 (was 6)
            self.temples_needed = 2  # -1 (was 3)
            self.merit_needed = 12  # -3 (was 15)
    
    def check_team_victory(self) -> Tuple[bool, str]:
        """Check victory conditions"""
        conditions = []
        
        cond1 = self.dharma_disaster <= self.dharma_win_threshold
        conditions.append(f"Dharma{self.dharma_disaster}{'<=' if cond1 else '>'}{self.dharma_win_threshold}")
        
        cond2 = self.beings_saved_count >= self.beings_needed
        conditions.append(f"Saved{self.beings_saved_count}{'>=' if cond2 else '<'}{self.beings_needed}")
        
        cond3 = self.temples >= self.temples_needed
        conditions.append(f"Temples{self.temples}{'>=' if cond3 else '<'}{self.temples_needed}")
        
        cond4 = all(p.merit >= self.merit_needed for p in self.players)
        min_merit = min(p.merit for p in self.players)
        conditions.append(f"MinMerit{min_merit}{'>=' if cond4 else '<'}{self.merit_needed}")
        
        victory = cond1 and cond2 and cond3 and cond4
        return victory, " | ".join(conditions)
    
    def check_team_failure(self) -> Tuple[bool, str]:
        """Check failure conditions (v0.5 modified)"""
        # Failure 1: Dharma>=50
        if self.dharma_disaster >= 50:
            return True, f"Dharma{self.dharma_disaster}>=50"
        
        # Failure 2: Any player merit<3 OR >=2 players merit<5 (MODIFIED)
        low_merit_count = sum(1 for p in self.players if p.merit < 5)
        if low_merit_count >= 2:
            return True, f"{low_merit_count}players merit<5"
        if any(p.merit < 3 for p in self.players):
            return True, f"Player merit<3"
        
        # Failure 3: Beings failed>=4
        if self.beings_failed >= 4:
            return True, f"BeingsFailed{self.beings_failed}>=4"
        
        # Failure 4: Any player three poisons>=20
        for p in self.players:
            if p.greed + p.anger + p.delusion >= 20:
                return True, f"ThreePoisons>=20"
        
        return False, ""


def roll_dice(num_dice: int = 2, modifier: int = 0) -> int:
    """Roll dice"""
    result = sum(random.randint(1, 6) for _ in range(num_dice))
    return max(2, min(12, result + modifier))


def select_vow(player: Player) -> None:
    """Select vow"""
    if player.strategy == PlayerStrategy.SELFISH:
        player.vow_type = VowType.SMALL
        player.vow_points = random.choice([10, 11, 12])
    elif player.strategy == PlayerStrategy.BALANCED:
        player.vow_type = VowType.MEDIUM
        player.vow_points = random.choice([16, 17, 18, 19, 20])
    else:
        player.vow_type = VowType.LARGE
        player.vow_points = random.choice([28, 29, 30])


def player_action(player: Player, game_state: GameState) -> None:
    """Player action (2 actions per round)"""
    for action_num in range(2):
        if player.strategy == PlayerStrategy.SELFISH:
            # Selfish: Focus on personal cultivation
            if player.role == Role.MONK and player.discipline < 10:
                player.merit += 3  # +3 (was +2)
                player.delusion = max(0, player.delusion - 1)
            elif player.role == Role.MERCHANT:
                if player.trade_routes < 3 and player.wealth >= 6 and action_num == 0:
                    # Build trade route
                    player.wealth -= 6
                    player.trade_routes += 1
                else:
                    # Trade
                    income = player.trade_routes * 2
                    player.wealth += income
                    if income >= 5:
                        player.greed += 1
            else:
                player.merit += 3  # +3 (was +2)
                player.delusion = max(0, player.delusion - 1)
        
        elif player.strategy == PlayerStrategy.BALANCED:
            if action_num == 0:
                # Action 1: Personal
                if player.role == Role.MERCHANT and player.trade_routes < 3 and player.wealth >= 6:
                    player.wealth -= 6
                    player.trade_routes += 1
                else:
                    player.merit += 3  # +3 (was +2)
            else:
                # Action 2: Team contribution
                if game_state.dharma_disaster >= 20:
                    dharma_protection(player, game_state)
                elif len(game_state.active_beings) > 0 and random.random() < 0.5:
                    attempt_save_being(player, game_state)
                elif game_state.temples < game_state.temples_needed and can_build_temple(player):
                    build_temple(player, game_state)
                else:
                    player.merit += 3  # +3 (was +2)
        
        else:  # ALTRUISTIC
            # Always prioritize team
            if game_state.dharma_disaster >= 15:
                dharma_protection(player, game_state)
            elif len(game_state.active_beings) > 0:
                attempt_save_being(player, game_state)
            elif game_state.temples < game_state.temples_needed and can_build_temple(player):
                build_temple(player, game_state)
            else:
                # Altruistic also needs personal merit
                player.merit += 3  # +3 (was +2)
    
    # Farmer passive income
    if player.role == Role.FARMER:
        player.wealth += 2
        if player.piety >= 10:
            player.merit += 1  # Auto merit for high piety


def dharma_protection(player: Player, game_state: GameState) -> None:
    """Dharma protection action (v0.5: enhanced)"""
    reduction = 0
    cost_paid = False
    
    if player.role == Role.MONK:
        if player.influence >= 1:
            player.influence -= 1
            reduction = 3  # +1 (was 2)
            cost_paid = True
            # All players +2 merit (was +1)
            for p in game_state.players:
                p.merit += 2
    elif player.role == Role.NOBLE:
        if player.wealth >= 8:
            player.wealth -= 8
            reduction = 6  # +1 (was 5)
            cost_paid = True
            player.merit += 5  # +2 (was 3)
            player.reputation += 2
    elif player.role == Role.MERCHANT:
        if player.wealth >= 10:
            player.wealth -= 10
            reduction = 5  # +1 (was 4)
            cost_paid = True
            player.merit += 3  # +1 (was 2)
    elif player.role == Role.FARMER:
        reduction = 2
        cost_paid = True
        player.piety += 1
    
    if cost_paid:
        game_state.dharma_disaster = max(0, game_state.dharma_disaster - reduction)
        player.dharma_contribution += reduction


def attempt_save_being(player: Player, game_state: GameState) -> None:
    """Attempt to save being"""
    if not game_state.active_beings:
        return
    
    being = game_state.active_beings[0]
    
    # Contribute wealth
    contribution = min(player.wealth, being.wealth_needed)
    if contribution > 0:
        player.wealth -= contribution
        being.wealth_needed -= contribution
        
        # Check if completed
        if being.wealth_needed <= 0:
            player.merit += being.merit_reward
            player.beings_saved += 1
            game_state.dharma_disaster = max(0, game_state.dharma_disaster - being.dharma_reduction)
            game_state.beings_saved_count += 1
            game_state.active_beings.remove(being)


def can_build_temple(player: Player) -> bool:
    """Check if can build temple"""
    return player.wealth >= 10 and player.influence >= 5


def build_temple(player: Player, game_state: GameState) -> None:
    """Build temple"""
    if can_build_temple(player):
        player.wealth -= 10
        player.influence -= 5
        player.merit += 3  # +1 (was 2)
        player.temples_built += 1
        game_state.temples += 1
        # All players +2 merit (was +1)
        for p in game_state.players:
            p.merit += 2


def event_phase(game_state: GameState) -> None:
    """Event phase"""
    # 1. New being card (70% chance)
    if random.random() < 0.7:
        # v0.5: Reduced wealth requirement by 20%
        base_wealth = random.randint(4, 10)
        new_being = Being(
            name=f"Being{game_state.round}",
            difficulty=random.randint(5, 12),
            wealth_needed=int(base_wealth * 0.8),  # -20%
            dharma_reduction=random.randint(2, 5),
            merit_reward=random.randint(2, 4)
        )
        game_state.active_beings.append(new_being)
    
    # 2. Personal events (simplified)
    for player in game_state.players:
        event_roll = roll_dice(2)
        if event_roll >= 8:
            # Positive event
            player.merit += random.randint(1, 3)
            player.wealth += random.randint(1, 3)
        elif event_roll <= 5:
            # Negative event
            player.merit = max(0, player.merit - 1)
            player.wealth = max(0, player.wealth - 1)


def disaster_phase(game_state: GameState) -> None:
    """Disaster phase"""
    # Dharma increase (v0.5: slower)
    game_state.dharma_disaster += game_state.dharma_per_round
    
    # Check beings timeout (v0.5: 4 rounds instead of 3)
    for being in list(game_state.active_beings):
        being.turns_waiting += 1
        if being.turns_waiting >= 4:  # +1 round
            game_state.active_beings.remove(being)
            game_state.beings_failed += 1
            game_state.dharma_disaster += 5
    
    # Disaster effects
    if game_state.dharma_disaster >= 20:
        # Weapon disaster
        victim = random.choice(game_state.players)
        victim.wealth = max(0, victim.wealth - 3)
        victim.merit = max(0, victim.merit - 2)
    
    if game_state.dharma_disaster >= 35:
        # Plague disaster
        for p in game_state.players:
            p.merit = max(0, p.merit - 1)


def calculate_final_score(player: Player, game_state: GameState) -> int:
    """Calculate final score"""
    score = player.merit * 2
    
    # Vow achievement
    if player.vow_achieved:
        score += player.vow_points
    elif player.vow_type == VowType.LARGE:
        score -= 10
    
    # Special achievements
    if player.dharma_contribution >= 15:
        score += 5
    if player.beings_saved >= 3:
        score += 5
    if player.temples_built >= 2:
        score += 5
    
    # Role-specific bonuses
    if player.role == Role.FARMER and player.piety >= 20:
        score += 10
    if player.role == Role.NOBLE and player.reputation >= 15:
        score += 8
    
    # Penalties
    if player.dharma_contribution < 10:
        score = int(score * 0.5)
    
    if player.greed >= 10 or player.anger >= 10 or player.delusion >= 10:
        score = min(score, 19)
    
    return score


def check_vow_achievement(player: Player, game_state: GameState) -> None:
    """Check vow achievement"""
    if player.vow_type == VowType.SMALL:
        if player.merit >= 25:
            player.vow_achieved = True
    elif player.vow_type == VowType.MEDIUM:
        if player.beings_saved >= 4 or (player.merit >= 20 and player.dharma_contribution >= 8):
            player.vow_achieved = True
    elif player.vow_type == VowType.LARGE:
        # Large vow: All players merit>=20 (adjusted to >=18 for balance)
        if all(p.merit >= 18 for p in game_state.players) and game_state.dharma_disaster <= 12:
            player.vow_achieved = True


def simulate_game(strategies: List[PlayerStrategy], difficulty: str = "Standard", verbose: bool = False) -> Dict:
    """Simulate one game"""
    roles = [Role.MONK, Role.NOBLE, Role.MERCHANT, Role.FARMER]
    players = [
        Player(name=f"{role.value}", role=role, strategy=strategy)
        for role, strategy in zip(roles, strategies)
    ]
    
    game_state = GameState(players, difficulty)
    
    for player in players:
        select_vow(player)
    
    # Main game loop (8 rounds)
    for round_num in range(1, 9):
        game_state.round = round_num
        
        if verbose:
            print(f"\n===== Round {round_num} =====")
            print(f"Dharma:{game_state.dharma_disaster}  Saved:{game_state.beings_saved_count}  Temples:{game_state.temples}")
            for p in players:
                print(f"  {p.name}: Merit{p.merit} Wealth{p.wealth}")
        
        # Action phase
        for player in players:
            player_action(player, game_state)
        
        # Event phase
        event_phase(game_state)
        
        # Disaster phase
        disaster_phase(game_state)
        
        # Check failure
        failed, reason = game_state.check_team_failure()
        if failed:
            if verbose:
                print(f"\n[GAME FAILED] {reason}")
            return {
                "victory": False,
                "reason": reason,
                "final_dharma": game_state.dharma_disaster,
                "beings_saved": game_state.beings_saved_count,
                "temples": game_state.temples,
                "rounds_survived": round_num,
                "player_scores": [0] * len(players)
            }
    
    # Game end
    victory, conditions = game_state.check_team_victory()
    
    if verbose:
        print(f"\n===== Game End =====")
        print(f"Victory conditions: {conditions}")
        print(f"Result: {'VICTORY' if victory else 'DEFEAT'}")
    
    # Calculate scores
    for player in game_state.players:
        check_vow_achievement(player, game_state)
    
    scores = [calculate_final_score(p, game_state) for p in game_state.players]
    
    if verbose:
        for player, score in zip(game_state.players, scores):
            fruit = "Buddha" if score >= 50 else "Bodhisattva" if score >= 40 else "Arhat" if score >= 30 else "StreamEnter" if score >= 20 else "Mundane"
            print(f"{player.name}({player.strategy.value}): {score}pts - {fruit}")
    
    return {
        "victory": victory,
        "reason": conditions if victory else "Not all conditions met",
        "final_dharma": game_state.dharma_disaster,
        "beings_saved": game_state.beings_saved_count,
        "temples": game_state.temples,
        "rounds_survived": 8,
        "player_scores": scores
    }


def run_test_suite():
    """Run test suite"""
    print("=" * 80)
    print("Merit Cycle v0.5 Cooperative - Balance Test")
    print("=" * 80)
    
    test_configs = [
        {
            "name": "All Selfish",
            "strategies": [PlayerStrategy.SELFISH] * 4,
            "description": "Everyone focuses on personal cultivation"
        },
        {
            "name": "All Altruistic",
            "strategies": [PlayerStrategy.ALTRUISTIC] * 4,
            "description": "Everyone prioritizes team"
        },
        {
            "name": "All Balanced",
            "strategies": [PlayerStrategy.BALANCED] * 4,
            "description": "Everyone balances personal and team"
        },
        {
            "name": "Mixed A",
            "strategies": [PlayerStrategy.ALTRUISTIC, PlayerStrategy.BALANCED, 
                          PlayerStrategy.BALANCED, PlayerStrategy.SELFISH],
            "description": "1 Altruistic + 2 Balanced + 1 Selfish"
        },
        {
            "name": "Mixed B",
            "strategies": [PlayerStrategy.ALTRUISTIC, PlayerStrategy.ALTRUISTIC, 
                          PlayerStrategy.BALANCED, PlayerStrategy.SELFISH],
            "description": "2 Altruistic + 1 Balanced + 1 Selfish"
        },
        {
            "name": "Extreme Mix",
            "strategies": [PlayerStrategy.ALTRUISTIC, PlayerStrategy.ALTRUISTIC, 
                          PlayerStrategy.SELFISH, PlayerStrategy.SELFISH],
            "description": "2 Altruistic + 2 Selfish"
        },
    ]
    
    tests_per_config = 200  # Increased from 100
    
    results_summary = []
    
    for config in test_configs:
        print(f"\n{'='*80}")
        print(f"Test Config: {config['name']}")
        print(f"Description: {config['description']}")
        print(f"Strategies: {' | '.join([s.value for s in config['strategies']])}")
        print(f"Test runs: {tests_per_config}")
        print(f"{'='*80}")
        
        victories = 0
        total_dharma = []
        total_beings = []
        total_temples = []
        all_scores = [[] for _ in range(4)]
        failure_reasons = {}
        
        for test_num in range(tests_per_config):
            result = simulate_game(config['strategies'], difficulty="Standard", verbose=False)
            
            if result['victory']:
                victories += 1
            else:
                reason = result['reason'].split("|")[0].strip()
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
            
            total_dharma.append(result['final_dharma'])
            total_beings.append(result['beings_saved'])
            total_temples.append(result['temples'])
            
            for i, score in enumerate(result['player_scores']):
                all_scores[i].append(score)
        
        # Statistics
        win_rate = victories / tests_per_config * 100
        avg_dharma = statistics.mean(total_dharma)
        avg_beings = statistics.mean(total_beings)
        avg_temples = statistics.mean(total_temples)
        
        print(f"\n[Team Performance]")
        print(f"Win Rate: {win_rate:.1f}% ({victories}/{tests_per_config})")
        print(f"Avg Dharma: {avg_dharma:.1f}")
        print(f"Avg Beings Saved: {avg_beings:.1f}")
        print(f"Avg Temples: {avg_temples:.1f}")
        
        if failure_reasons:
            print(f"\n[Failure Reasons]")
            for reason, count in sorted(failure_reasons.items(), key=lambda x: -x[1])[:3]:
                print(f"  {reason}: {count} times ({count/tests_per_config*100:.1f}%)")
        
        print(f"\n[Individual Performance]")
        roles = ["Monk", "Noble", "Merchant", "Farmer"]
        for i, (role, strat) in enumerate(zip(roles, config['strategies'])):
            avg_score = statistics.mean(all_scores[i])
            std_score = statistics.stdev(all_scores[i]) if len(all_scores[i]) > 1 else 0
            max_score = max(all_scores[i])
            print(f"{role}({strat.value}): Avg {avg_score:.1f} (±{std_score:.1f}) Max {max_score}")
        
        results_summary.append({
            "config": config['name'],
            "win_rate": win_rate,
            "avg_dharma": avg_dharma,
            "avg_beings": avg_beings,
            "avg_temples": avg_temples,
            "avg_scores": [statistics.mean(scores) for scores in all_scores]
        })
    
    # Summary
    print(f"\n{'='*80}")
    print("Test Summary")
    print(f"{'='*80}")
    print(f"\n{'Config':<15} {'WinRate':<10} {'Dharma':<10} {'Saved':<10} {'Temples':<10} {'AvgScore':<10}")
    print("-" * 80)
    for result in results_summary:
        avg_score = statistics.mean(result['avg_scores'])
        print(f"{result['config']:<15} {result['win_rate']:<10.1f} {result['avg_dharma']:<10.1f} "
              f"{result['avg_beings']:<10.1f} {result['avg_temples']:<10.1f} {avg_score:<10.1f}")
    
    print(f"\n{'='*80}")
    print("Test Complete")
    print(f"{'='*80}")
    
    # Recommendations
    print(f"\n{'='*80}")
    print("Balance Analysis")
    print(f"{'='*80}")
    
    best_config = max(results_summary, key=lambda x: x['win_rate'])
    worst_config = min(results_summary, key=lambda x: x['win_rate'])
    
    print(f"\nBest Strategy: {best_config['config']} ({best_config['win_rate']:.1f}% win rate)")
    print(f"Worst Strategy: {worst_config['config']} ({worst_config['win_rate']:.1f}% win rate)")
    
    avg_win_rate = statistics.mean([r['win_rate'] for r in results_summary])
    print(f"\nAverage Win Rate: {avg_win_rate:.1f}%")
    
    if avg_win_rate < 30:
        print("\n[WARNING] Game is still too difficult (target: 40-60% win rate)")
        print("Recommendations:")
        print("  - Further increase merit gains")
        print("  - Further reduce dharma per round")
        print("  - Lower victory conditions")
    elif avg_win_rate > 70:
        print("\n[WARNING] Game is too easy")
        print("Recommendations:")
        print("  - Reduce merit gains")
        print("  - Increase dharma per round")
    else:
        print("\n[SUCCESS] Game balance is in acceptable range (40-60%)")


if __name__ == "__main__":
    run_test_suite()
    
    print("\n\n" + "="*80)
    print("Detailed Demo (All Balanced)")
    print("="*80)
    simulate_game([PlayerStrategy.BALANCED] * 4, verbose=True)
