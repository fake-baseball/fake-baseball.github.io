import pandas as pd

from data.sources import PLAYERS_CSV, RETIRED_BATTERS_CSV, RETIRED_PITCHERS_CSV
from data.sources import season21_latest, season21_earliest, read_s21
from data.stats import _ROLE_MAP


player_info      = None  # current active roster (most recent players file)
player_info_proj = None  # pre-season skills snapshot (earliest players file, for projections)
retired_batters  = None
retired_pitchers = None


def load_player_info():
    global player_info, player_info_proj
    player_info      = _load_players21(season21_latest('players'))
    player_info_proj = _load_players21(season21_earliest('players'))


def _load_players21(path):
    """Load a season21 players CSV into the player_info format."""
    raw = read_s21(path)

    df = pd.DataFrame()
    df['id']         = raw['id']
    df['jersey']     = raw['jersey']
    df['first_name'] = raw['firstName']
    df['last_name']  = raw['lastName']
    df['age']        = raw['age']
    df['team_name']  = raw['teamName']
    df['ppos']       = raw['primaryPosition'].map(
                           {1:'P',2:'C',3:'1B',4:'2B',5:'3B',6:'SS',7:'LF',8:'CF',9:'RF'})
    df['spos']       = raw['secondaryPosition'].fillna(0).astype(int).map(
                           {0:'',2:'C',3:'1B',4:'2B',5:'3B',6:'SS',7:'LF',8:'CF',9:'RF',
                            10:'IF',11:'OF',12:'1B/OF',13:'IF/OF'}).fillna('')
    df['role']       = raw['pitcherRole'].map(_ROLE_MAP).replace('', pd.NA).fillna('')
    df['throws']     = raw['throws'].map({0:'L', 1:'R'})
    df['bats']       = raw['bats'].map({0:'L', 1:'R', 2:'S'})
    df['power']      = raw['power']
    df['contact']    = raw['contact']
    df['speed']      = raw['speed']
    df['fielding']   = raw['fielding']
    df['arm']        = raw['arm']
    df['velocity']   = raw['velocity']
    df['junk']       = raw['junk']
    df['accuracy']   = raw['accuracy']
    _pitch_cols = [c for c in raw.columns if c.startswith('has_')]
    df['pitchTypes'] = raw[_pitch_cols].apply(
        lambda row: ', '.join(c[4:].upper() for c in _pitch_cols if row[c]), axis=1)
    df['salary']     = raw['salary'].apply(lambda v: f'${v/1_000_000:.1f}m')

    df = df.set_index(['first_name', 'last_name'])
    df['spos'] = df['spos'].fillna('')
    return df


def load_retirements():
    global retired_batters, retired_pitchers
    retired_batters  = _load_retirement_csv(RETIRED_BATTERS_CSV)
    retired_pitchers = _load_retirement_csv(RETIRED_PITCHERS_CSV)


def _load_retirement_csv(path):
    df = pd.read_csv(path)[['First Name', 'Last Name', 'Age', 'Retirement Season']]
    df = df.rename(columns={'Age': 'age'})
    df = df.fillna(0)
    df['Retirement Season'] = df['Retirement Season'].astype(int)
    return df
