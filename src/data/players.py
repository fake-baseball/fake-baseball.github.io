import pandas as pd

from data.sources import PLAYERS_CSV, RETIRED_BATTERS_CSV, RETIRED_PITCHERS_CSV


def load_player_info():
    df = pd.read_csv(PLAYERS_CSV, index_col=('first_name', 'last_name'))
    df['spos'] = df['spos'].fillna('')
    return df


def _load_retirement_csv(path):
    df = pd.read_csv(path)[['First Name', 'Last Name', 'Age', 'Retirement Season']]
    df = df.fillna(0)
    df['Retirement Season'] = df['Retirement Season'].astype(int)
    return df


def load_retirements():
    return _load_retirement_csv(RETIRED_BATTERS_CSV), _load_retirement_csv(RETIRED_PITCHERS_CSV)
