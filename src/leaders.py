"""
Functions to query statistical leaders from data_batters / data_pitchers.
Also computes the season-max tables used for bolding on player pages.
"""
import pandas as pd

from constants import (
    BAT_SEASON_MIN_PA,   BAT_CAREER_MIN_PA,
    BR_SEASON_MIN_SBATT, BR_CAREER_MIN_SBATT,
    FLD_SEASON_MIN_GF,   FLD_CAREER_MIN_GF,
    PIT_SEASON_MIN_IP,   PIT_CAREER_MIN_IP,
    SEASON_RANGE,
)

_SEASON_THRESHOLDS = {'PA': BAT_SEASON_MIN_PA, 'SBatt': BR_SEASON_MIN_SBATT, 'GF': FLD_SEASON_MIN_GF}
_CAREER_THRESHOLDS = {'PA': BAT_CAREER_MIN_PA, 'SBatt': BR_CAREER_MIN_SBATT, 'GF': FLD_CAREER_MIN_GF}


# ── Batting leaders ──────────────────────────────────────────────────────────

def get_batting_leaders(data_batters, stat, season=None, qualified=False, qual_col='PA', lowest=False, num=10, team=None):
    df = data_batters[data_batters[qual_col] >= _SEASON_THRESHOLDS[qual_col]] if qualified else data_batters
    if season is None:
        df = df[df['stat_type'] == 'S']
    else:
        df = df[df['Season'] == season]
    if team is not None:
        df = df[df['Team'] == team]
    if lowest:
        df = df[df[stat] <= df[stat].nsmallest(num).max()]
        df = df.sort_values(stat, ascending=True)
    else:
        df = df[df[stat] >= df[stat].nlargest(num).min()]
        df = df.sort_values(stat, ascending=False)
    return df


def get_career_batting_leaders(data_batters, player_info, stat, qualified=False, qual_col='PA', active=False, lowest=False, num=10, team=None):
    df = data_batters[data_batters[qual_col] >= _CAREER_THRESHOLDS[qual_col]] if qualified else data_batters
    df = df[df['Season'] == 'Career']
    if active:
        df = df[df.set_index(['First Name', 'Last Name']).index.isin(player_info.index)]
    if team is not None:
        df = df[df['Team'] == team]
    if lowest:
        df = df[df[stat] <= df[stat].nsmallest(num).max()]
        df = df.sort_values(stat, ascending=True)
    else:
        df = df[df[stat] >= df[stat].nlargest(num).min()]
        df = df.sort_values(stat, ascending=False)
    return df


def get_leaders_by_season(data_batters, stat, qualified=False, qual_col='PA', lowest=False):
    dfs = []
    for season in SEASON_RANGE:
        df = get_batting_leaders(data_batters, stat, season, qualified=qualified, qual_col=qual_col, lowest=lowest, num=1)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


# ── Pitching leaders ─────────────────────────────────────────────────────────

def get_pitching_leaders(data_pitchers, stat, season=None, qualified=False, lowest=False, num=10, team=None):
    df = data_pitchers[data_pitchers['IP_true'] >= PIT_SEASON_MIN_IP] if qualified else data_pitchers
    if season is None:
        df = df[df['stat_type'] == 'S']
    else:
        df = df[df['Season'] == season]
    if team is not None:
        df = df[df['Team'] == team]
    if lowest:
        df = df[df[stat] <= df[stat].nsmallest(num).max()]
        df = df.sort_values(stat, ascending=True)
    else:
        df = df[df[stat] >= df[stat].nlargest(num).min()]
        df = df.sort_values(stat, ascending=False)
    return df


def get_career_pitching_leaders(data_pitchers, player_info, stat, qualified=False, active=False, lowest=False, num=10, team=None):
    df = data_pitchers[data_pitchers['IP_true'] >= PIT_CAREER_MIN_IP] if qualified else data_pitchers
    df = df[df['Season'] == 'Career']
    if active:
        df = df[df.set_index(['First Name', 'Last Name']).index.isin(player_info.index)]
    if team is not None:
        df = df[df['Team'] == team]
    if lowest:
        df = df[df[stat] <= df[stat].nsmallest(num).max()]
        df = df.sort_values(stat, ascending=True)
    else:
        df = df[df[stat] >= df[stat].nlargest(num).min()]
        df = df.sort_values(stat, ascending=False)
    return df


def get_pitching_leaders_by_season(data_pitchers, stat, qualified=False, lowest=False):
    dfs = []
    for season in SEASON_RANGE:
        df = get_pitching_leaders(data_pitchers, stat, season, qualified=qualified, lowest=lowest, num=1)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


# ── Season-max tables (used for bolding on player pages) ────────────────────

# Columns for which we track the season leader (used to bold individual season rows).
# Hardcoded for now; could eventually be driven by a field in stats_meta.
BAT_COLUMNS      = ['GB', 'WAR', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'RBI',
                     'SB', 'CS', 'BB', 'K', 'TB', 'SH', 'SF']
BAT_QUAL_COLUMNS = ['AVG', 'OBP', 'SLG', 'OPS', 'OPS+']

PIT_COLUMNS          = ['WAR', 'W', 'GP', 'GS', 'CG', 'SHO', 'SV', 'K', 'IP_true']
PIT_QUAL_COLUMNS     = ['WIN%']
PIT_QUAL_LOW_COLUMNS = ['ERA', 'ERA-', 'FIP', 'WHIP']


def compute_season_maxes(data_batters):
    """Returns (max_batters, max_qual_batters) used for bolding on batter pages."""
    season_data = data_batters[data_batters['stat_type'] == 'S']
    max_batters = season_data.groupby('Season')[BAT_COLUMNS].max()
    max_qual_batters = (
        season_data[season_data['PA'] >= BAT_SEASON_MIN_PA]
        .groupby('Season')[BAT_QUAL_COLUMNS].max()
    )
    return max_batters, max_qual_batters


def compute_season_maxes_pitchers(data_pitchers):
    """Returns (max_pitchers, max_qual_pitchers, min_qual_pitchers) for bolding on pitcher pages."""
    season_data = data_pitchers[data_pitchers['stat_type'] == 'S']
    qual = season_data[season_data['IP_true'] >= PIT_SEASON_MIN_IP]
    max_pitchers      = season_data.groupby('Season')[PIT_COLUMNS].max()
    max_qual_pitchers = qual.groupby('Season')[PIT_QUAL_COLUMNS].max()
    min_qual_pitchers = qual.groupby('Season')[PIT_QUAL_LOW_COLUMNS].min()
    return max_pitchers, max_qual_pitchers, min_qual_pitchers
