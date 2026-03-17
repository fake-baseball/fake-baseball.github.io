import pandas as pd

from data.sources import PLAYERS_CSV, RETIRED_BATTERS_CSV, RETIRED_PITCHERS_CSV


player_info      = None
retired_batters  = None
retired_pitchers = None


def load_player_info():
    global player_info
    df = pd.read_csv(PLAYERS_CSV, index_col=('first_name', 'last_name'))
    df['spos'] = df['spos'].fillna('')
    player_info = df


def load_retirements():
    global retired_batters, retired_pitchers
    retired_batters  = _load_retirement_csv(RETIRED_BATTERS_CSV)
    retired_pitchers = _load_retirement_csv(RETIRED_PITCHERS_CSV)


def _load_retirement_csv(path):
    df = pd.read_csv(path)[['First Name', 'Last Name', 'Age', 'Retirement Season']]
    df = df.fillna(0)
    df['Retirement Season'] = df['Retirement Season'].astype(int)
    return df
