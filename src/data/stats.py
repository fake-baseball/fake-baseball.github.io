"""Raw CSV data for batting and pitching (pre-derived stats)."""
import numpy as np
import pandas as pd

from formulas import compute_tb, compute_xbh, compute_bip_bat, compute_gf, compute_sb_att
from formulas import compute_p_bip, compute_p_gr
from data.sources import BATTERS_CSV, PITCHERS_CSV, TEAMS_CSV, season21_latest

# Integer position codes used in season21 files
_POS_MAP  = {1:'P', 2:'C', 3:'1B', 4:'2B', 5:'3B', 6:'SS', 7:'LF', 8:'CF', 9:'RF'}
_SPOS_MAP = {
    0:'',   2:'C',     3:'1B',    4:'2B',    5:'3B',   6:'SS',
    7:'LF', 8:'CF',    9:'RF',   10:'IF',   11:'OF',  12:'1B/OF', 13:'IF/OF',
}
_ROLE_MAP = {0:'', 1:'SP', 2:'SP/RP', 3:'RP', 4:'CL'}


def _name_to_abbr():
    """Return {team_name: abbr} from teams.csv."""
    teams = pd.read_csv(TEAMS_CSV, usecols=['team_name', 'abbr'])
    return dict(zip(teams['team_name'], teams['abbr']))

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
    data = data.rename(columns={
        'PP': 'pos1', '2P': 'pos2',
        'Team': 'team', 'Age': 'age', 'Season': 'season',
        'GP': 'b_gp', 'GB': 'gb', 'PA': 'pa', 'AB': 'ab', 'H': 'h',
        '1B': 'b_1b', '2B': 'b_2b', '3B': 'b_3b',
        'HR': 'hr', 'R': 'r', 'RBI': 'rbi', 'BB': 'bb', 'K': 'k',
        'SH': 'sh', 'SF': 'sf', 'HBP': 'hbp', 'E': 'e', 'PB': 'pb',
        'SB': 'sb', 'CS': 'cs',
    })

    s21 = _load_season21_batting()
    if s21 is not None:
        data = pd.concat([data, s21], ignore_index=True)

    compute_tb(data)
    compute_xbh(data)
    compute_bip_bat(data)
    compute_gf(data)
    compute_sb_att(data)
    batting_stats = data


def _load_season21_batting():
    path = season21_latest('batting')
    if path is None:
        return None
    raw = pd.read_csv(path)
    if raw.empty:
        return None

    abbr = _name_to_abbr()
    d = pd.DataFrame()
    d['season']  = raw['seasonNum']
    d['First Name'] = raw['firstName']
    d['Last Name']  = raw['lastName']
    d['team']    = raw['mostRecentTeam'].map(abbr)
    d['age']     = raw['age']
    d['pos1']    = raw['primaryPosition'].map(_POS_MAP)
    d['pos2']    = raw['secondaryPosition'].fillna(0).astype(int).map(_SPOS_MAP).fillna('None')
    d['gb']      = raw['gamesBatting']
    d['b_gp']    = raw['gamesPlayed']
    d['ab']      = raw['atBats']
    d['r']       = raw['runs']
    d['h']       = raw['hits']
    d['b_2b']    = raw['doubles']
    d['b_3b']    = raw['triples']
    d['hr']      = raw['homeruns']
    d['rbi']     = raw['rbi']
    d['sb']      = raw['stolenBases']
    d['cs']      = raw['caughtStealing']
    d['bb']      = raw['baseOnBalls']
    d['k']       = raw['strikeOuts']
    d['hbp']     = raw['hitByPitch']
    d['sh']      = raw['sacrificeHits']
    d['sf']      = raw['sacrificeFlies']
    d['e']       = raw['errors']
    d['pb']      = raw['passedBalls']
    # Derived raw stats
    d['pa']      = d['ab'] + d['bb'] + d['hbp'] + d['sh'] + d['sf']
    d['b_1b']    = d['h'] - d['b_2b'] - d['b_3b'] - d['hr']
    return d


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

    s21 = _load_season21_pitching()
    if s21 is not None:
        data = pd.concat([data, s21], ignore_index=True)

    compute_p_bip(data)
    compute_p_gr(data)
    pitching_stats = data


def _load_season21_pitching():
    path = season21_latest('pitching')
    if path is None:
        return None
    raw = pd.read_csv(path)
    if raw.empty:
        return None

    # Convert outs pitched to decimal innings
    outs = raw['outsPitched']
    p_ip = outs // 3 + (outs % 3) / 10

    d = pd.DataFrame()
    d['season'] = raw['seasonNum']
    d['First Name'] = raw['firstName']
    d['Last Name']  = raw['lastName']
    abbr = _name_to_abbr()
    d['team']   = raw['mostRecentTeam'].map(abbr)
    d['age']    = raw['age']
    d['role']   = raw['pitcherRole'].map(_ROLE_MAP)
    d['p_w']    = raw['wins']
    d['p_l']    = raw['losses']
    d['p_gp']   = raw['games']
    d['p_gs']   = raw['gamesStarted']
    d['p_cg']   = raw['completeGames']
    d['p_sho']  = raw['shutouts']
    d['p_sv']   = raw['saves']
    d['p_ip']   = np.floor(p_ip) + (p_ip - np.floor(p_ip)) * (10/3)
    d['p_k']    = raw['strikeOuts']
    d['p_bb']   = raw['baseOnBalls']
    d['p_h']    = raw['hits']
    d['p_er']   = raw['earnedRuns']
    d['p_hr']   = raw['homeRuns']
    d['p_hbp']  = raw['battersHitByPitch']
    d['p_tp']   = raw['totalPitches']
    d['p_bf']   = raw['battersFaced']
    d['p_ra']   = raw['runsAllowed']
    d['p_wp']   = raw['wildPitches']
    return d
