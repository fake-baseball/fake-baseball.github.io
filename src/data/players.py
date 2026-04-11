import pandas as pd

from data.sources import PLAYERS_CSV, RETIRED_BATTERS_CSV, RETIRED_PITCHERS_CSV
from data.sources import season21_latest, season21_earliest, read_s21
from data.stats import _ROLE_MAP, player_names
from data.data_utils import convert_name


player_info      = None  # all players (active + retired), indexed by player_id
player_info_proj = None  # pre-season skills snapshot (earliest players file, for projections)


def load_player_info():
    global player_info, player_info_proj
    active       = _load_players21(season21_latest('players'))
    retired      = _load_retirements()
    # Retired players not already in active (edge case: re-signed) get appended.
    new_pids    = retired.index.difference(active.index)
    player_info = pd.concat([active, retired.loc[new_pids]])

    # Players that appear in stats CSVs but have no roster or retirement record
    # (data gaps): add minimal retired rows with NaN age/retirement_season.
    known = set(player_info.index)
    orphans = [pid for pid in player_names if pid not in known]
    if orphans:
        rows = []
        for pid in orphans:
            first, last = player_names[pid]
            rows.append({'first_name': first, 'last_name': last,
                         'is_retired': True, 'retirement_season': pd.NA, 'age': pd.NA})
        orphan_df = pd.DataFrame(rows, index=pd.Index(orphans, name='player_id'))
        player_info = pd.concat([player_info, orphan_df])
    player_info_proj = _load_players21(season21_earliest('players'))


def _load_players21(path):
    """Load a season21 players CSV; returns DataFrame indexed by player_id with is_retired=False."""
    raw = read_s21(path)

    df = pd.DataFrame()
    df['id']                = raw['id']
    df['jersey']            = raw['jersey']
    df['first_name']        = raw['firstName']
    df['last_name']         = raw['lastName']
    df['age']               = raw['age']
    df['team_name']         = raw['teamName']
    df['pos1']              = raw['primaryPosition'].map(
                                  {1:'P',2:'C',3:'1B',4:'2B',5:'3B',6:'SS',7:'LF',8:'CF',9:'RF'})
    df['pos2']              = raw['secondaryPosition'].fillna(0).astype(int).map(
                                  {0:'',2:'C',3:'1B',4:'2B',5:'3B',6:'SS',7:'LF',8:'CF',9:'RF',
                                   10:'IF',11:'OF',12:'1B/OF',13:'IF/OF'}).fillna('')
    df['role']              = raw['pitcherRole'].map(_ROLE_MAP).replace('', pd.NA).fillna('')
    df['throws']            = raw['throws'].map({0:'L', 1:'R'})
    df['bats']              = raw['bats'].map({0:'L', 1:'R', 2:'S'})
    df['power']             = raw['power']
    df['contact']           = raw['contact']
    df['speed']             = raw['speed']
    df['fielding']          = raw['fielding']
    df['arm']               = raw['arm']
    df['velocity']          = raw['velocity']
    df['junk']              = raw['junk']
    df['accuracy']          = raw['accuracy']
    _pitch_cols = [c for c in raw.columns if c.startswith('has_')]
    df['arsenal']           = raw[_pitch_cols].apply(
        lambda row: ', '.join(c[4:].upper() for c in _pitch_cols if row[c]), axis=1)
    df['salary']            = raw['salary'] / 1_000_000
    df['is_retired']        = False
    df['retirement_season'] = pd.NA

    df['player_id'] = df.apply(lambda r: convert_name(r['first_name'], r['last_name']), axis=1)
    df = df.set_index('player_id')
    df['pos2'] = df['pos2'].fillna('')
    return df


def _load_retirements():
    """Load both retirement CSVs; returns unified DataFrame indexed by player_id with is_retired=True."""
    bat = _load_retirement_csv(RETIRED_BATTERS_CSV)
    pit = _load_retirement_csv(RETIRED_PITCHERS_CSV)
    return pd.concat([bat, pit], ignore_index=True).set_index('player_id')


def _load_retirement_csv(path):
    df = pd.read_csv(path)[['First Name', 'Last Name', 'Age', 'Retirement Season']]
    df = df.rename(columns={
        'First Name':       'first_name',
        'Last Name':        'last_name',
        'Age':              'age',
        'Retirement Season':'retirement_season',
    })
    df['retirement_season'] = df['retirement_season'].fillna(0).astype(int)
    df['is_retired']        = True
    df['player_id']         = df.apply(lambda r: convert_name(r['first_name'], r['last_name']), axis=1)
    return df
