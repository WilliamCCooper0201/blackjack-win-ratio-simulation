#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STA 4222 Final Project: Estimating Early-Variance Anomalies in Blackjack
Systematic Sampling + Bootstrap Variance Estimation
Simulation uses card removal (without replacement) and simple player strategy.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ==========================================
# 1. BLACKJACK SIMULATION ENGINE (WITHOUT REPLACEMENT)
# ==========================================

class Shoe:
    """Shoe of multiple decks, draws without replacement, reshuffles when low."""
    def __init__(self, num_decks=6):
        self.num_decks = num_decks
        self.reshuffle_threshold = 10   # reshuffle when fewer than 10 cards remain
        self._build_shoe()
        self.shuffle()

    def _build_shoe(self):
        # 52‑card deck: 2‑9, 10, J, Q, K (all 10), Ace (11)
        deck_values = [2,3,4,5,6,7,8,9,10,10,10,10,11] * 4
        self.cards = deck_values * self.num_decks

    def shuffle(self):
        np.random.shuffle(self.cards)

    def draw(self):
        if len(self.cards) < self.reshuffle_threshold:
            self._build_shoe()
            self.shuffle()
        return self.cards.pop()

def hand_value(hand):
    """Compute total hand value, converting Ace from 11 to 1 if needed."""
    total = sum(hand)
    aces = hand.count(11)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total

def player_decision(player_hand, dealer_upcard):
    """
    Simple but realistic basic strategy:
    - Stand on 17 or more.
    - Hit on 16 or less.
    (Soft hands are handled automatically by hand_value.)
    """
    total = hand_value(player_hand)
    return 'S' if total >= 17 else 'H'

def play_one_round(shoe):
    """
    Plays one round (player vs dealer). Returns:
        1 if player wins,
        0 if player loses,
        None if push (ignored in cumulative ratio).
    No splits, no doubles – keeps it simple and clean.
    """
    # Initial deal
    player_hand = [shoe.draw(), shoe.draw()]
    dealer_hand = [shoe.draw(), shoe.draw()]
    dealer_upcard = dealer_hand[0]

    # Check for natural blackjacks
    player_bj = (hand_value(player_hand) == 21 and len(player_hand) == 2)
    dealer_bj = (hand_value(dealer_hand) == 21 and len(dealer_hand) == 2)

    if player_bj and dealer_bj:
        return None
    if player_bj:
        return 1
    if dealer_bj:
        return 0

    # Player's turn
    while True:
        action = player_decision(player_hand, dealer_upcard)
        if action == 'S':
            break
        player_hand.append(shoe.draw())
        if hand_value(player_hand) > 21:
            return 0   # player bust

    # Dealer's turn (stands on 17+)
    while hand_value(dealer_hand) < 17:
        dealer_hand.append(shoe.draw())
    dealer_total = hand_value(dealer_hand)
    player_total = hand_value(player_hand)

    if dealer_total > 21:
        return 1
    if player_total > dealer_total:
        return 1
    if player_total < dealer_total:
        return 0
    return None   # push

def simulate_player_session(desired_decisive_rounds=500, num_decks=6):
    """
    Simulates one player until they have `desired_decisive_rounds` non‑push rounds.
    Returns:
        - cumulative_ratios : list of win ratios at each decisive round
        - final_win_rate    : final win ratio (overall proportion of wins)
    """
    shoe = Shoe(num_decks)
    wins = 0
    decisive = 0
    cumulative_ratios = []

    while decisive < desired_decisive_rounds:
        result = play_one_round(shoe)
        if result is None:
            continue
        if result == 1:
            wins += 1
        decisive += 1
        cumulative_ratios.append(wins / decisive)

    return cumulative_ratios, cumulative_ratios[-1]

# ==========================================
# 2. GENERATE THE POPULATION (1000 PLAYERS)
# ==========================================
np.random.seed(42)
N_PLAYERS = 1000
ROUNDS_PER_PLAYER = 500

print("Simulating 1,000 players, each with 500 decisive rounds...")
print("(This may take 30–60 seconds depending on your machine.)")

player_records = []
final_rates = []

for pid in range(N_PLAYERS):
    ratios, final_rate = simulate_player_session(ROUNDS_PER_PLAYER)
    final_rates.append(final_rate)
    max_ratio = max(ratios)
    peak_round = ratios.index(max_ratio) + 1   # 1‑based round number
    player_records.append({
        'Player_ID': pid + 1,
        'Peak_Round': peak_round,
        'Max_Win_Ratio': max_ratio
    })

df_pop = pd.DataFrame(player_records)
true_global_win_rate = np.mean(final_rates)

# ==========================================
# 3. POPULATION PARAMETERS
# ==========================================
true_mean_peak = df_pop['Peak_Round'].mean()
true_mean_max = df_pop['Max_Win_Ratio'].mean()

print("\n=== TRUE POPULATION PARAMETERS (N = 1,000) ===")
print(f"Global win rate (average final ratio): {true_global_win_rate:.4f}")
print(f"Mean peak round: {true_mean_peak:.2f}")
print(f"Mean max win ratio: {true_mean_max:.4f}")
print("===============================================\n")

# ==========================================
# 4. SYSTEMATIC SAMPLING (1-in-k)
# ==========================================
n_sample = 100
k = N_PLAYERS // n_sample   # = 10
random_start = np.random.randint(0, k)
sample_indices = list(range(random_start, N_PLAYERS, k))
df_sample = df_pop.iloc[sample_indices].copy()

sample_mean_peak = df_sample['Peak_Round'].mean()
sample_mean_max = df_sample['Max_Win_Ratio'].mean()

print("=== SYSTEMATIC SAMPLE ESTIMATES (n = 100) ===")
print(f"Sample mean peak round: {sample_mean_peak:.2f}")
print(f"Sample mean max win ratio: {sample_mean_max:.4f}")
print("==============================================\n")

# ==========================================
# 5. BOOTSTRAP VARIANCE ESTIMATION (Post‑data)
# ==========================================
B = 1000
boot_peak = []
boot_max = []

for _ in range(B):
    resample = df_sample.sample(n=n_sample, replace=True)
    boot_peak.append(resample['Peak_Round'].mean())
    boot_max.append(resample['Max_Win_Ratio'].mean())

se_peak = np.std(boot_peak, ddof=1)
se_max = np.std(boot_max, ddof=1)

z = 1.96
ci_peak = (sample_mean_peak - z * se_peak, sample_mean_peak + z * se_peak)
ci_max = (sample_mean_max - z * se_max, sample_mean_max + z * se_max)

print("=== BOOTSTRAP 95% CONFIDENCE INTERVALS ===")
print(f"Peak round: ({ci_peak[0]:.2f}, {ci_peak[1]:.2f})   SE = {se_peak:.2f}")
print(f"Max win ratio: ({ci_max[0]:.4f}, {ci_max[1]:.4f})   SE = {se_max:.4f}")
print("============================================\n")

# Check if intervals capture the true population means
peak_captured = ci_peak[0] <= true_mean_peak <= ci_peak[1]
max_captured = ci_max[0] <= true_mean_max <= ci_max[1]
print(f"CI captures true mean peak round? {peak_captured}")
print(f"CI captures true mean max win ratio? {max_captured}\n")

# ==========================================
# 6. VISUALIZATIONS (as required)
# ==========================================
plt.style.use('ggplot')

# Figure 1: Scatterplot – Peak Round vs Max Win Ratio
plt.figure(figsize=(10, 6))
plt.scatter(df_pop['Peak_Round'], df_pop['Max_Win_Ratio'],
            alpha=0.5, color='royalblue', edgecolors='w', s=40)
plt.axhline(true_global_win_rate, color='red', linestyle='--', linewidth=2,
            label=f'True global win rate = {true_global_win_rate:.4f}')
plt.title('Figure 1: Maximum Win Ratio vs. Peak Round\n(1,000 simulated players, real blackjack rules)')
plt.xlabel('Peak Round (1‑based)')
plt.ylabel('Maximum Cumulative Win Ratio')
plt.legend()
plt.tight_layout()
plt.savefig('scatter_peak_vs_max.png', dpi=150)
plt.show()

# Figure 2: Histogram of Peak Round
plt.figure(figsize=(10, 6))
plt.hist(df_pop['Peak_Round'], bins=50, color='darkorange', edgecolor='black', alpha=0.7)
plt.axvline(true_mean_peak, color='black', linestyle='dashed', linewidth=2,
            label=f'True mean peak round = {true_mean_peak:.1f}')
plt.title('Figure 2: Distribution of Peak Rounds across Players')
plt.xlabel('Peak Round')
plt.ylabel('Number of Players')
plt.legend()
plt.tight_layout()
plt.savefig('hist_peak_round.png', dpi=150)
plt.show()

print("Plots saved as 'scatter_peak_vs_max.png' and 'hist_peak_round.png'")
print("\n--- Simulation complete ---")
