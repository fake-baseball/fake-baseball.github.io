"""Core utilities shared by non-page modules (batting, pitching, leaders)."""
import numpy as np

from data.data_utils import convert_name  # re-exported for backward compat


def rank_column(series, ascending=False):
    """Return a list of 1-based ranks with standard competition ranking (1,1,3,...) for ties."""
    ranks = []
    prev_val = None
    prev_rank = 0
    for i, val in enumerate(series, 1):
        if val != prev_val:
            prev_rank = i
            prev_val = val
        ranks.append(prev_rank)
    return ranks


def fmt_ip(v):
    """Format a decimal IP value into base-3 baseball notation (e.g. 6.667 -> '6.2')."""
    try:
        if np.isnan(v):
            return '-'
    except (TypeError, ValueError):
        pass
    whole  = int(v)
    thirds = int((v - whole) * 3 + 0.5)
    return f"{whole}.{thirds}"


def weighted_avg(df, stat, weight_col):
    """Weighted average of stat by weight_col; returns 0 if total weight is zero."""
    w = df[weight_col].sum()
    return (df[stat] * df[weight_col]).sum() / w if w != 0 else 0.0


def append_summary_rows(d, player_keys, recompute_fn, weighted_avg_specs, extra_meta=None):
    """Build career and team-total summary rows and append to d.

    player_keys        - list of player identity columns (e.g. ['player_id'])
    recompute_fn       - callable(df) that recomputes rate stats in-place and returns df
    weighted_avg_specs - list of (col, weight_col) pairs for weighted averages
    extra_meta         - optional dict of extra fields to set on career and team rows
    """
    import pandas as pd
    gp = player_keys
    gt = player_keys + ['team']

    career = d.groupby(gp).sum(numeric_only=True).reset_index()
    career['season']    = np.nan
    career['age']       = ''
    career['stat_type'] = 'career'
    if 'team' in career.columns:
        career['team'] = np.nan
    if extra_meta:
        for k, v in extra_meta.items():
            career[k] = v
    career = recompute_fn(career)
    for col, weight_col in weighted_avg_specs:
        career[col] = d.groupby(gp).apply(
            lambda g, c=col, w=weight_col: weighted_avg(g, c, w), include_groups=False
        ).values

    team_totals = d.groupby(gt).sum(numeric_only=True).reset_index()
    team_totals['season']    = np.nan
    team_totals['age']       = ''
    team_totals['stat_type'] = 'team'
    if extra_meta:
        for k, v in extra_meta.items():
            team_totals[k] = v
    team_totals = recompute_fn(team_totals)
    for col, weight_col in weighted_avg_specs:
        team_totals[col] = d.groupby(gt).apply(
            lambda g, c=col, w=weight_col: weighted_avg(g, c, w), include_groups=False
        ).values

    return pd.concat([d, career, team_totals], ignore_index=True)
