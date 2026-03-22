"""Raw CSV data for batting and pitching (pre-derived stats)."""
import numpy as np
import pandas as pd

from formulas import compute_tb, compute_xbh, compute_bip_bat, compute_gf, compute_sb_att
from formulas import compute_bip_pit_raw, compute_gr_raw
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
    data['IP_true'] = np.floor(ip) + (ip - np.floor(ip)) * (10/3)
    # Drop the formatted string IP column; IP_true is the canonical innings value
    data = data.drop(columns=['IP'])
    compute_bip_pit_raw(data)
    compute_gr_raw(data)
    # Rename to final column names
    _CSV_PIT_RENAMES = {
        'W': 'p_w', 'L': 'p_l', 'GP': 'p_gp', 'GS': 'p_gs', 'GR': 'p_gr',
        'IP_true': 'p_ip', 'CG': 'p_cg', 'SHO': 'p_sho', 'SV': 'p_sv',
        'K': 'p_k', 'BB': 'p_bb', 'H': 'p_h', 'ER': 'p_er',
        'HR': 'p_hr', 'HBP': 'p_hbp', 'TP': 'p_tp', 'BF': 'p_bf',
        'RA': 'p_ra', 'WP': 'p_wp', 'BIP': 'p_bip',
    }
    data = data.rename(columns=_CSV_PIT_RENAMES)
    pitching_stats = data
