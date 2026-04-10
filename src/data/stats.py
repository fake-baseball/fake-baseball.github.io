"""Raw CSV data for batting and pitching (pre-derived stats)."""
import numpy as np
import pandas as pd

from formulas import compute_tb, compute_xbh, compute_bip_bat, compute_gf, compute_sb_att
from formulas import compute_p_bip, compute_p_gr
from data.sources import BATTERS_CSV, PITCHERS_CSV, TEAMS_CSV, season21_latest, season21_all, read_s21
from constants import weight_BB, weight_HBP, weight_1B, weight_2B, weight_3B, weight_HR

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

_s21_cache = {}  # path -> DataFrame, shared across all stream_rows calls


def _read_s21_cached(path):
    if path not in _s21_cache:
        _s21_cache[path] = read_s21(path)
    return _s21_cache[path]


def load_batting():
    global batting_stats
    data = pd.read_csv(BATTERS_CSV)
    data = data[[
        'Season', 'First Name', 'Last Name', 'Team', 'Age', 'PP', '2P',
        'GB', 'GP', 'PA', 'AB', 'H', 'HR', 'R', '1B', '2B', '3B', 'RBI',
        'SB', 'CS', 'BB', 'K', 'SH', 'SF', 'HBP', 'E', 'PB',
    ]]
    data['2P'] = data['2P'].fillna(value="")
    data = data.rename(columns={
        'First Name': 'first_name', 'Last Name': 'last_name',
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
    raw = read_s21(path)
    if raw.empty:
        return None

    abbr = _name_to_abbr()
    d = pd.DataFrame()
    d['season']     = raw['seasonNum']
    d['first_name'] = raw['firstName']
    d['last_name']  = raw['lastName']
    d['team']       = raw['mostRecentTeam'].map(abbr)
    d['age']        = raw['age']
    d['pos1']       = raw['primaryPosition'].map(_POS_MAP)
    d['pos2']    = raw['secondaryPosition'].fillna(0).astype(int).map(_SPOS_MAP).fillna('')
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
        'First Name': 'first_name', 'Last Name': 'last_name',
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
    raw = read_s21(path)
    if raw.empty:
        return None

    # Convert outs pitched to decimal innings
    outs = raw['outsPitched']
    p_ip = outs // 3 + (outs % 3) / 10

    d = pd.DataFrame()
    d['season']     = raw['seasonNum']
    d['first_name'] = raw['firstName']
    d['last_name']  = raw['lastName']
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


def batting_stream_rows(first, last):
    """Return stream-by-stream season 21 batting rows for one player.

    Each element is a dict with counting stat diffs and cumulative rate stats.
    Streams are numbered sequentially from 1 regardless of which file index
    the player first appears in.
    Returns an empty list if the player has no season 21 batting data.
    """
    files = season21_all('batting')
    if not files:
        return []

    _MAP = {
        'gamesBatting': 'gb',
        'atBats': 'ab', 'runs': 'r', 'hits': 'h',
        'doubles': 'b_2b', 'triples': 'b_3b', 'homeruns': 'hr',
        'rbi': 'rbi', 'stolenBases': 'sb', 'caughtStealing': 'cs',
        'baseOnBalls': 'bb', 'strikeOuts': 'k',
        'hitByPitch': 'hbp', 'sacrificeHits': 'sh', 'sacrificeFlies': 'sf',
        'errors': 'e', 'passedBalls': 'pb',
    }

    def _int(snap, col):
        v = snap[col]
        return int(v) if not pd.isna(v) else 0

    snapshots = []
    for path in files:
        raw = _read_s21_cached(path)
        mask = (raw['firstName'] == first) & (raw['lastName'] == last)
        snapshots.append(raw[mask].iloc[0] if mask.any() else None)

    if all(s is None for s in snapshots):
        return []

    import os
    rows = []
    prev = None
    for path, snap in zip(files, snapshots):
        if snap is None:
            prev = None
            continue
        file_num = int(os.path.basename(path).rsplit('_', 1)[1].split('.')[0])
        row = {'stream': file_num}
        for raw_col, key in _MAP.items():
            curr = _int(snap, raw_col)
            pv   = _int(prev, raw_col) if prev is not None else 0
            row[key] = curr - pv
        row['pa'] = row['ab'] + row['bb'] + row['hbp'] + row['sh'] + row['sf']
        row['tb'] = row['h'] + row['b_2b'] + 2 * row['b_3b'] + 3 * row['hr']
        # Cumulative rate stats
        h   = _int(snap, 'hits')
        ab  = _int(snap, 'atBats')
        bb  = _int(snap, 'baseOnBalls')
        hbp = _int(snap, 'hitByPitch')
        sf  = _int(snap, 'sacrificeFlies')
        k   = _int(snap, 'strikeOuts')
        d2  = _int(snap, 'doubles')
        d3  = _int(snap, 'triples')
        xhr = _int(snap, 'homeruns')
        s1  = h - d2 - d3 - xhr
        tb_cum = s1 + 2*d2 + 3*d3 + 4*xhr
        row['avg'] = h / ab if ab > 0 else 0.0
        obp_d = ab + bb + hbp + sf
        row['obp'] = (h + bb + hbp) / obp_d if obp_d > 0 else 0.0
        row['slg'] = tb_cum / ab if ab > 0 else 0.0
        row['ops'] = row['obp'] + row['slg']
        bip = ab - k - xhr + sf
        row['babip'] = (h - xhr) / bip if bip > 0 else 0.0
        woba_d = ab + bb + hbp + sf
        row['woba'] = (weight_BB*bb + weight_HBP*hbp + weight_1B*s1 + weight_2B*d2 + weight_3B*d3 + weight_HR*xhr) / woba_d if woba_d > 0 else 0.0
        prev = snap
        rows.append(row)

    return rows


def pitching_stream_rows(first, last):
    """Return stream-by-stream season 21 pitching rows for one player.

    Each element is a dict with counting stat diffs and cumulative rate stats.
    Streams are numbered sequentially from 1 regardless of which file index
    the player first appears in.
    Returns an empty list if the player has no season 21 pitching data.
    """
    files = season21_all('pitching')
    if not files:
        return []

    _MAP = {
        'wins': 'p_w', 'losses': 'p_l', 'games': 'p_gp', 'gamesStarted': 'p_gs',
        'completeGames': 'p_cg', 'shutouts': 'p_sho', 'saves': 'p_sv',
        'hits': 'p_h', 'earnedRuns': 'p_er', 'homeRuns': 'p_hr',
        'baseOnBalls': 'p_bb', 'strikeOuts': 'p_k',
        'battersHitByPitch': 'p_hbp', 'totalPitches': 'p_tp',
        'battersFaced': 'p_bf', 'runsAllowed': 'p_ra', 'wildPitches': 'p_wp',
    }

    def _int(snap, col):
        v = snap[col]
        return int(v) if not pd.isna(v) else 0

    snapshots = []
    for path in files:
        raw = _read_s21_cached(path)
        mask = (raw['firstName'] == first) & (raw['lastName'] == last)
        snapshots.append(raw[mask].iloc[0] if mask.any() else None)

    if all(s is None for s in snapshots):
        return []

    import os
    rows = []
    prev = None
    for path, snap in zip(files, snapshots):
        if snap is None:
            prev = None
            continue
        file_num = int(os.path.basename(path).rsplit('_', 1)[1].split('.')[0])
        row = {'stream': file_num}
        for raw_col, key in _MAP.items():
            curr = _int(snap, raw_col)
            pv   = _int(prev, raw_col) if prev is not None else 0
            row[key] = curr - pv
        # IP: diff outs converted to display notation
        curr_outs = _int(snap, 'outsPitched')
        prev_outs = _int(prev, 'outsPitched') if prev is not None else 0
        diff_outs = curr_outs - prev_outs
        row['p_ip'] = diff_outs / 3.0
        # Cumulative rate stats
        ip_true  = _int(snap, 'outsPitched') / 3.0
        er_cum   = _int(snap, 'earnedRuns')
        bb_cum   = _int(snap, 'baseOnBalls')
        h_cum    = _int(snap, 'hits')
        k_cum    = _int(snap, 'strikeOuts')
        hr_cum   = _int(snap, 'homeRuns')
        hbp_cum  = _int(snap, 'battersHitByPitch')
        bf_cum   = _int(snap, 'battersFaced')
        w_cum    = _int(snap, 'wins')
        l_cum    = _int(snap, 'losses')
        row['p_era']     = (er_cum * 9.0) / ip_true if ip_true > 0 else 0.0
        row['p_whip']    = (bb_cum + h_cum) / ip_true if ip_true > 0 else 0.0
        row['p_win_pct'] = w_cum / (w_cum + l_cum) if (w_cum + l_cum) > 0 else np.nan
        p_bip = bf_cum - bb_cum - k_cum - hr_cum - hbp_cum
        row['p_babip'] = (h_cum - hr_cum) / p_bip if p_bip > 0 else 0.0
        if ip_true > 0:
            import league as lg
            from constants import CURRENT_SEASON
            cfip_index = lg.season_pitching.index
            cfip_season = CURRENT_SEASON if CURRENT_SEASON in cfip_index else cfip_index.max()
            cfip = lg.season_pitching.loc[cfip_season, 'p_cfip']
            row['p_fip'] = (13*hr_cum + 3*(bb_cum + hbp_cum) - 2*k_cum) / ip_true + cfip
        else:
            row['p_fip'] = np.nan
        prev = snap
        rows.append(row)

    return rows
