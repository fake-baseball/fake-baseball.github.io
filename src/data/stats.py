"""Raw CSV data for batting and pitching (pre-derived stats)."""
import numpy as np
import pandas as pd

from formulas import compute_TB, compute_XBH, compute_BIP_bat, compute_GF, compute_SBatt
from formulas import compute_BIP_pit, compute_GR
from data.sources import BATTERS_CSV, PITCHERS_CSV


batting_stats  = None
pitching_stats = None


def load_batting():
    global batting_stats
    data = pd.read_csv(BATTERS_CSV)
    data = data[[
        'Season', 'First Name', 'Last Name', 'Team', 'Age', 'PP', '2P',
        'GB', 'GP', 'PA', 'AB', 'H', 'HR', 'R', '1B', '2B', '3B', 'RBI',
        'SB', 'CS', 'BB', 'K', 'SH', 'SF', 'HBP', 'E', 'PB',
    ]]
    data['2P'] = data['2P'].fillna(value="None")
    compute_TB(data)
    compute_XBH(data)
    compute_BIP_bat(data)
    compute_GF(data)
    compute_SBatt(data)
    batting_stats = data


def load_pitching():
    global pitching_stats
    data = pd.read_csv(PITCHERS_CSV)
    data = data[[
        'Season', 'First Name', 'Last Name', 'Team', 'Age', 'Role',
        'W', 'L', 'GP', 'GS', 'IP', 'CG', 'SHO', 'SV',
        'K', 'BB', 'H', 'ER', 'HR', 'HBP', 'TP', 'BF', 'RA', 'WP',
    ]]
    ip = data['IP']
    data['IP_true'] = np.floor(ip) + (ip - np.floor(ip)) * (10/3)
    data['IP'] = data['IP'].apply(lambda x: f"{x:.1f}")
    compute_BIP_pit(data)
    compute_GR(data)
    pitching_stats = data
