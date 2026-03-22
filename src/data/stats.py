"""Raw CSV data for batting and pitching (pre-derived stats)."""
import numpy as np
import pandas as pd

from formulas import compute_tb, compute_xbh, compute_bip_bat, compute_gf, compute_sb_att
from formulas import compute_p_bip, compute_p_gr
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
    # Rename to final column names before calling formula functions
    data = data.rename(columns={
        'PP': 'pos1', '2P': 'pos2',
        'Team': 'team', 'Age': 'age', 'Season': 'season',
        'GP': 'b_gp', 'GB': 'gb', 'PA': 'pa', 'AB': 'ab', 'H': 'h',
        '1B': 'b_1b', '2B': 'b_2b', '3B': 'b_3b',
        'HR': 'hr', 'R': 'r', 'RBI': 'rbi', 'BB': 'bb', 'K': 'k',
        'SH': 'sh', 'SF': 'sf', 'HBP': 'hbp', 'E': 'e', 'PB': 'pb',
        'SB': 'sb', 'CS': 'cs',
    })
    compute_tb(data)
    compute_xbh(data)
    compute_bip_bat(data)
    compute_gf(data)
    compute_sb_att(data)
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
    data['p_ip'] = np.floor(ip) + (ip - np.floor(ip)) * (10/3)
    data = data.drop(columns=['IP'])
    data = data.rename(columns={
        'Team': 'team', 'Age': 'age', 'Season': 'season', 'Role': 'role',
        'W': 'p_w', 'L': 'p_l', 'GP': 'p_gp', 'GS': 'p_gs',
        'CG': 'p_cg', 'SHO': 'p_sho', 'SV': 'p_sv',
        'K': 'p_k', 'BB': 'p_bb', 'H': 'p_h', 'ER': 'p_er',
        'HR': 'p_hr', 'HBP': 'p_hbp', 'TP': 'p_tp', 'BF': 'p_bf',
        'RA': 'p_ra', 'WP': 'p_wp',
    })
    compute_p_bip(data)
    compute_p_gr(data)
    pitching_stats = data
