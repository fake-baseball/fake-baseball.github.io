import numpy as np
import pandas as pd

from formulas import compute_TB, compute_XBH, compute_BIP_bat, compute_GF, compute_SBatt
from data.sources import BATTERS_CSV


def load_batters():
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
    return data
