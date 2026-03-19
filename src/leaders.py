"""
Functions to query statistical leaders from batting.stats / pitching.stats.
Also computes season-best tables used for bolding on player pages.
"""
import pandas as pd

from constants import (
    BAT_SEASON_MIN_PA,   BAT_CAREER_MIN_PA,
    BR_SEASON_MIN_SBATT, BR_CAREER_MIN_SBATT,
    FLD_SEASON_MIN_GF,   FLD_CAREER_MIN_GF,
    PIT_SEASON_MIN_IP,   PIT_CAREER_MIN_IP,
    SEASON_RANGE,
)

from stats_meta import BATTING_STATS, BASERUNNING_STATS, FIELDING_STATS, PITCHING_STATS
from util import rank_column

SEASON_THRESHOLDS = {'PA': BAT_SEASON_MIN_PA, 'SBatt': BR_SEASON_MIN_SBATT, 'GF': FLD_SEASON_MIN_GF, 'IP_true': PIT_SEASON_MIN_IP}
CAREER_THRESHOLDS = {'PA': BAT_CAREER_MIN_PA, 'SBatt': BR_CAREER_MIN_SBATT, 'GF': FLD_CAREER_MIN_GF, 'IP_true': PIT_CAREER_MIN_IP}
_ALL_BAT_META = {**BATTING_STATS, **BASERUNNING_STATS, **FIELDING_STATS}


# ── Batting leaders ──────────────────────────────────────────────────────────

def get_batting_leaders(stat, season=None, worst=False, num=10, team=None, teams=None):
    import batting
    meta = _ALL_BAT_META[stat]
    ascending = meta['lowest'] ^ worst
    df = batting.stats[batting.stats[meta['qual_col']] >= SEASON_THRESHOLDS[meta['qual_col']]] if meta['qualified'] else batting.stats
    if season is None:
        df = df[df['stat_type'] == 'season']
    else:
        df = df[df['Season'] == season]
    if team is not None:
        df = df[df['Team'] == team]
    if teams is not None:
        df = df[df['Team'].isin(teams)]
    if ascending:
        df = df[df[stat] <= df[stat].nsmallest(num).max()]
        df = df.sort_values(stat, ascending=True)
    else:
        df = df[df[stat] >= df[stat].nlargest(num).min()]
        df = df.sort_values(stat, ascending=False)
    df.index = rank_column(df[stat])
    return df


def get_career_batting_leaders(stat, active=False, worst=False, num=10, team=None):
    import batting
    from data import players
    meta = _ALL_BAT_META[stat]
    ascending = meta['lowest'] ^ worst
    df = batting.stats[batting.stats[meta['qual_col']] >= CAREER_THRESHOLDS[meta['qual_col']]] if meta['qualified'] else batting.stats
    df = df[df['Season'] == 'Career']
    if active:
        df = df[df.set_index(['First Name', 'Last Name']).index.isin(players.player_info.index)]
    if team is not None:
        df = df[df['Team'] == team]
    if ascending:
        df = df[df[stat] <= df[stat].nsmallest(num).max()]
        df = df.sort_values(stat, ascending=True)
    else:
        df = df[df[stat] >= df[stat].nlargest(num).min()]
        df = df.sort_values(stat, ascending=False)
    df.index = rank_column(df[stat])
    return df


def get_leaders_by_season(stat, worst=False):
    dfs = []
    for season in SEASON_RANGE:
        df = get_batting_leaders(stat, season, worst=worst, num=1)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


# ── Pitching leaders ─────────────────────────────────────────────────────────

def get_pitching_leaders(stat, season=None, worst=False, num=10, team=None, teams=None):
    import pitching
    meta = PITCHING_STATS[stat]
    ascending = meta['lowest'] ^ worst
    df = pitching.stats[pitching.stats['IP_true'] >= PIT_SEASON_MIN_IP] if meta['qualified'] else pitching.stats
    if season is None:
        df = df[df['stat_type'] == 'season']
    else:
        df = df[df['Season'] == season]
    if team is not None:
        df = df[df['Team'] == team]
    if teams is not None:
        df = df[df['Team'].isin(teams)]
    if ascending:
        df = df[df[stat] <= df[stat].nsmallest(num).max()]
        df = df.sort_values(stat, ascending=True)
    else:
        df = df[df[stat] >= df[stat].nlargest(num).min()]
        df = df.sort_values(stat, ascending=False)
    df.index = rank_column(df[stat])
    return df


def get_career_pitching_leaders(stat, active=False, worst=False, num=10, team=None):
    import pitching
    from data import players
    meta = PITCHING_STATS[stat]
    ascending = meta['lowest'] ^ worst
    df = pitching.stats[pitching.stats['IP_true'] >= PIT_CAREER_MIN_IP] if meta['qualified'] else pitching.stats
    df = df[df['Season'] == 'Career']
    if active:
        df = df[df.set_index(['First Name', 'Last Name']).index.isin(players.player_info.index)]
    if team is not None:
        df = df[df['Team'] == team]
    if ascending:
        df = df[df[stat] <= df[stat].nsmallest(num).max()]
        df = df.sort_values(stat, ascending=True)
    else:
        df = df[df[stat] >= df[stat].nlargest(num).min()]
        df = df.sort_values(stat, ascending=False)
    df.index = rank_column(df[stat])
    return df


def get_pitching_leaders_by_season(stat, worst=False):
    dfs = []
    for season in SEASON_RANGE:
        df = get_pitching_leaders(stat, season, worst=worst, num=1)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


# ── Season bests (used for bolding on player pages) ──────────────────────────
# For each registered stat, batting_leaders/pitching_leaders holds the season-best
# value per season: max if lowest=False, min if lowest=True, filtered by the
# qualification threshold if qualified=True.

batting_leaders  = None
pitching_leaders = None


def compute_season_leaders():
    global batting_leaders, pitching_leaders
    import batting
    import pitching
    from stats_meta import BATTING_STATS, BASERUNNING_STATS, FIELDING_STATS, PITCHING_STATS

    bat_data = batting.stats[batting.stats['stat_type'] == 'season']
    pit_data = pitching.stats[pitching.stats['stat_type'] == 'season']

    batting_leaders  = _compute_leaders(bat_data, [BATTING_STATS, BASERUNNING_STATS, FIELDING_STATS])
    pitching_leaders = _compute_leaders(pit_data, [PITCHING_STATS])


def _compute_leaders(data, stat_dicts):
    cols = {}
    for stat_dict in stat_dicts:
        first_meta = next(iter(stat_dict.values()))
        qual_col   = first_meta['qual_col']
        threshold  = SEASON_THRESHOLDS[qual_col]
        qual_data  = data[data[qual_col] >= threshold]
        for stat, meta in stat_dict.items():
            if stat not in data.columns:
                continue
            source = qual_data if meta['qualified'] else data
            cols[stat] = source.groupby('Season')[stat].min() if meta['lowest'] else source.groupby('Season')[stat].max()
    return pd.DataFrame(cols)
