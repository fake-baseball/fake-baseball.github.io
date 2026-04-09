"""
Precompute per-player, per-season stat rankings for fast lookup on player pages.
Call compute() after batting.compute() and pitching.compute().

Module-level state:
    batting  - {(season, col): sorted np.array} for batting/baserunning/fielding rank cols
    pitching - {(season, col): sorted np.array} for pitching rank cols

Public helpers:
    BAT_RANK_COLS  - batting stats used in player ranking tables (mirrors team_ranks)
    PIT_RANK_COLS  - pitching stats used in player ranking tables (mirrors team_ranks)
    player_rank(val, season, col, data) -> rank string e.g. '1st', 'T-3rd', or '--'
"""
import numpy as np

from registry import REGISTRY
from leaders import SEASON_THRESHOLDS
from team_ranks import BAT_RANK_COLS, PIT_RANK_COLS, ordinal

import league as lg

batting  = None   # {(season, col): sorted np.array}
pitching = None   # {(season, col): sorted np.array}


def compute():
    global batting, pitching
    import batting as bat_module
    import pitching as pit_module

    bat_seasons = bat_module.stats[bat_module.stats['stat_type'] == 'season']
    pit_seasons = pit_module.stats[pit_module.stats['stat_type'] == 'season']

    batting  = _build(bat_seasons, BAT_RANK_COLS)
    pitching = _build(pit_seasons, PIT_RANK_COLS)


def _build(season_df, cols):
    """Return {(season, col): sorted np.array} for each season and col."""
    out = {}
    for season, grp in season_df.groupby('season'):
        for col in cols:
            if col not in grp.columns:
                continue
            meta     = REGISTRY.get(col, {})
            qual_col = meta.get('qual_col', 'pa')
            if meta.get('qualified', False) and qual_col in grp.columns:
                scale     = lg.season_scale.get(season, 1.0)
                threshold = SEASON_THRESHOLDS.get(qual_col, 0) * scale
                pool = grp[grp[qual_col] >= threshold]
            else:
                pool = grp
            vals = pool[col].dropna().values
            if vals.size:
                out[(season, col)] = np.sort(vals)
    return out


def player_rank(val, season, col, data):
    """Return a rank string for val within the precomputed sorted array.

    val    - raw numeric value for this player/season/col
    season - season number
    col    - stat column name
    data   - batting or pitching dict from this module

    Returns '--' if the value is missing or the season/col has no data.
    Returns e.g. '1st', 'T-3rd'.
    """
    import math
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return '--'
    arr = data.get((season, col))
    if arr is None or arr.size == 0:
        return '--'

    lowest = REGISTRY.get(col, {}).get('lowest', False)
    fval   = float(val)

    if lowest:
        # rank = number of values strictly less than val, + 1
        rank_val = int(np.searchsorted(arr, fval, side='left')) + 1
        tied     = int(np.searchsorted(arr, fval, side='right')) - int(np.searchsorted(arr, fval, side='left')) > 1
    else:
        # rank = number of values strictly greater than val, + 1
        rank_val = int(arr.size - np.searchsorted(arr, fval, side='right')) + 1
        tied     = int(np.searchsorted(arr, fval, side='right')) - int(np.searchsorted(arr, fval, side='left')) > 1

    return ('T-' if tied else '') + ordinal(rank_val)
