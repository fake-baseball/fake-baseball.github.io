"""
Functions to query statistical leaders from batting.stats / pitching.stats.
Also computes season-best tables used for bolding on player pages.
"""
import pandas as pd

import league as lg

from constants import (
    BAT_SEASON_MIN_PA,   BAT_CAREER_MIN_PA,
    BR_SEASON_MIN_SBATT, BR_CAREER_MIN_SBATT,
    FLD_SEASON_MIN_GF,   FLD_CAREER_MIN_GF,
    PIT_SEASON_MIN_IP,   PIT_CAREER_MIN_IP,
    SEASON_RANGE, CURRENT_SEASON,
)

from registry import REGISTRY
from util import rank_column

SEASON_THRESHOLDS = {'pa': BAT_SEASON_MIN_PA, 'sb_att': BR_SEASON_MIN_SBATT, 'gf': FLD_SEASON_MIN_GF, 'p_ip': PIT_SEASON_MIN_IP}
CAREER_THRESHOLDS = {'pa': BAT_CAREER_MIN_PA, 'sb_att': BR_CAREER_MIN_SBATT, 'gf': FLD_CAREER_MIN_GF, 'p_ip': PIT_CAREER_MIN_IP}
_BAT_CONTEXTS = {'batting', 'baserunning', 'fielding'}


def _qual_mask(df, qual_col):
    """Boolean mask for rows meeting the per-season pro-rated qualification threshold."""
    base = SEASON_THRESHOLDS[qual_col]
    thresholds = df['season'].map(lambda s: base * lg.season_scale.get(s, 1.0))
    return df[qual_col] >= thresholds


def _stats_df(stat):
    """Return the appropriate module-level stats DataFrame for a given stat key."""
    if REGISTRY[stat].get('context') == 'pitching':
        import pitching
        return pitching.stats
    import batting
    return batting.stats


# ── Leaders ──────────────────────────────────────────────────────────────────

def get_leaders(stat, season=None, worst=False, num=10, team=None, teams=None):
    meta = REGISTRY[stat]
    ascending = meta['lowest'] ^ worst
    qual_col = meta['qual_col']
    data = _stats_df(stat)
    df = data[_qual_mask(data, qual_col)] if meta['qualified'] else data
    if season is None:
        df = df[df['stat_type'] == 'season']
        df = df[df['season'] != CURRENT_SEASON]
    else:
        df = df[df['season'] == season]
    if team is not None:
        df = df[df['team'] == team]
    if teams is not None:
        df = df[df['team'].isin(teams)]
    if ascending:
        df = df[df[stat] <= df[stat].nsmallest(num).max()]
        df = df.sort_values(stat, ascending=True)
    else:
        df = df[df[stat] >= df[stat].nlargest(num).min()]
        df = df.sort_values(stat, ascending=False)
    df.index = rank_column(df[stat])
    return df


def get_career_leaders(stat, active=False, worst=False, num=10, team=None, teams=None):
    from data import players
    meta = REGISTRY[stat]
    ascending = meta['lowest'] ^ worst
    qual_col = meta['qual_col']
    data = _stats_df(stat)
    df = data[data[qual_col] >= CAREER_THRESHOLDS[qual_col]] if meta['qualified'] else data
    df = df[df['season'] == 'Career']
    if active:
        df = df[df['player_id'].isin(players.player_info.index[~players.player_info['is_retired']])]
    if team is not None:
        df = df[df['team'] == team]
    if teams is not None:
        # Filter by players whose most recent season was with one of the given teams
        season_data = data[data['stat_type'] == 'season']
        recent_team = (
            season_data.sort_values('season')
            .groupby('player_id')['team']
            .last()
        )
        eligible = recent_team[recent_team.isin(teams)].index
        df = df[df['player_id'].isin(eligible)]
    if ascending:
        df = df[df[stat] <= df[stat].nsmallest(num).max()]
        df = df.sort_values(stat, ascending=True)
    else:
        df = df[df[stat] >= df[stat].nlargest(num).min()]
        df = df.sort_values(stat, ascending=False)
    df.index = rank_column(df[stat])
    return df


def get_leaders_by_season(stat, worst=False, team=None, teams=None):
    dfs = []
    for season in SEASON_RANGE:
        df = get_leaders(stat, season, worst=worst, num=1, team=team, teams=teams)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


# ── Season bests (used for bolding on player pages) ──────────────────────────
# For each registered stat, batting_leaders/pitching_leaders holds the season-best
# value per season: max if lowest=False, min if lowest=True, filtered by the
# qualification threshold if qualified=True.
# _conf variants are dicts: conference_name -> same-structured DataFrame.

batting_leaders       = None
pitching_leaders      = None
batting_leaders_conf  = None
pitching_leaders_conf = None


def compute_season_leaders():
    global batting_leaders, pitching_leaders, batting_leaders_conf, pitching_leaders_conf
    import batting
    import pitching
    from data import teams as teams_data

    bat_meta = {k: v for k, v in REGISTRY.items() if v.get('context') in _BAT_CONTEXTS}
    pit_meta = {k: v for k, v in REGISTRY.items() if v.get('context') == 'pitching'}

    bat_data = batting.stats[batting.stats['stat_type'] == 'season']
    pit_data = pitching.stats[pitching.stats['stat_type'] == 'season']

    batting_leaders  = _compute_leaders(bat_data, [bat_meta])
    pitching_leaders = _compute_leaders(pit_data, [pit_meta])

    abbr_to_conf = teams_data.teams.set_index('team_id')['conference_name'].to_dict()
    confs        = teams_data.teams['conference_name'].dropna().unique()

    bat_c          = bat_data.copy()
    bat_c['_conf'] = bat_c['team'].map(abbr_to_conf)
    pit_c          = pit_data.copy()
    pit_c['_conf'] = pit_c['team'].map(abbr_to_conf)

    batting_leaders_conf  = {
        c: _compute_leaders(bat_c[bat_c['_conf'] == c], [bat_meta])
        for c in confs
    }
    pitching_leaders_conf = {
        c: _compute_leaders(pit_c[pit_c['_conf'] == c], [pit_meta])
        for c in confs
    }


def _compute_leaders(data, stat_dicts):
    cols = {}
    # Build per-qual_col filtered DataFrames (lazily, keyed by qual_col name)
    _qual_cache = {}
    def _get_qual(qual_col):
        if qual_col not in _qual_cache:
            if qual_col in data.columns:
                _qual_cache[qual_col] = data[_qual_mask(data, qual_col)]
            else:
                _qual_cache[qual_col] = data.iloc[0:0]  # empty
        return _qual_cache[qual_col]

    for stat_dict in stat_dicts:
        for stat, meta in stat_dict.items():
            if stat not in data.columns:
                continue
            qual_col = meta['qual_col']
            source = _get_qual(qual_col) if meta['qualified'] else data
            cols[stat] = source.groupby('season')[stat].min() if meta['lowest'] else source.groupby('season')[stat].max()
    return pd.DataFrame(cols)
