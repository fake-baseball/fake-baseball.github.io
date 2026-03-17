import numpy as np
import pandas as pd

from formulas import compute_BIP_pit, compute_GR
from data.sources import PITCHERS_CSV


def load_pitchers():
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
    return data
