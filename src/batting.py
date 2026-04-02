"""
Compute derived batting stats from basic stats and league context.
Call compute() after data.stats.load_batting() and league.compute_league().
Results are stored in batting.stats.
"""
import pandas as pd

from data import stats as raw
from util import weighted_avg

import formulas as f

stats = None

def compute():
    global stats
    # batting_stats already has final column names from load_batting()
    d = raw.batting_stats.copy()

    f.compute_avg(d)
    f.compute_obp(d)
    f.compute_slg(d)
    f.compute_ops(d)
    f.compute_babip_bat(d)
    f.compute_woba(d)
    f.compute_iso(d)
    f.compute_hr_pct_bat(d)
    f.compute_k_pct_bat(d)
    f.compute_bb_pct_bat(d)
    f.compute_pa_per_gb(d)
    f.compute_pa_per_hr(d)
    f.compute_xbh_pct(d)
    f.compute_rs_pct(d)
    f.compute_rc_pct(d)
    f.compute_rs(d)
    f.compute_rb(d)
    f.compute_sb_pct(d)
    f.compute_sb_att_pct(d)
    f.compute_e_per_gf(d)
    f.compute_pb_per_gf(d)

    # Batting value (r_bat must come before wrc_plus)
    f.compute_r_bat(d)
    f.compute_r_br(d)
    f.compute_r_def(d)
    f.compute_r_pos(d)

    d['r_corr'] = 0.0
    f.compute_b_raa(d)

    # Zero-sum correction: distribute the season RAA imbalance proportionally by PA
    season_raa = d.groupby('season')['raa'].sum()
    season_pa  = d.groupby('season')['pa'].sum()
    d['r_corr'] = d['season'].map(-season_raa / season_pa) * d['pa']
    f.compute_b_raa(d)

    f.compute_r_rep(d)
    f.compute_b_rar(d)
    f.compute_b_waa(d)
    f.compute_b_war(d)

    # Park-adjusted rate stats (computed after r_bat so order is correct)
    f.compute_ops_plus(d)
    f.compute_wrc(d)
    f.compute_wrc_plus(d)

    d['stat_type'] = 'season'
    stats = _append_summary_rows(d)


def _append_summary_rows(d):
    gp = ['First Name', 'Last Name']
    gt = ['First Name', 'Last Name', 'team']

    career = d.groupby(gp).sum(numeric_only=True).reset_index()
    career['season']    = 'Career'
    career['age']       = ''
    career['pos1']      = ''
    career['pos2']      = ''
    career['stat_type'] = 'career'
    team_counts = d.groupby(gp)['team'].nunique().reset_index(name='team')
    career = career.merge(team_counts, on=gp)
    career['team'] = career['team'].astype(str) + 'TM'
    career = _recompute_rates(career)
    career['woba']     = d.groupby(gp).apply(lambda g: weighted_avg(g, 'woba',     'pa'), include_groups=False).values
    career['ops_plus'] = d.groupby(gp).apply(lambda g: weighted_avg(g, 'ops_plus', 'pa'), include_groups=False).values
    career['wrc_plus'] = d.groupby(gp).apply(lambda g: weighted_avg(g, 'wrc_plus', 'pa'), include_groups=False).values

    team_totals = d.groupby(gt).sum(numeric_only=True).reset_index()
    season_counts = d.groupby(gt)['season'].nunique().reset_index(name='season')
    team_totals = team_totals.drop(columns=['season']).merge(season_counts, on=gt)
    team_totals['season'] = team_totals['season'].apply(
        lambda n: f"{n} Szn" if n == 1 else f"{n} Szns")
    team_totals['age']       = ''
    team_totals['pos1']      = ''
    team_totals['pos2']      = ''
    team_totals['stat_type'] = 'team'
    team_totals = _recompute_rates(team_totals)
    team_totals['woba']     = d.groupby(gt).apply(lambda g: weighted_avg(g, 'woba',     'pa'), include_groups=False).values
    team_totals['ops_plus'] = d.groupby(gt).apply(lambda g: weighted_avg(g, 'ops_plus', 'pa'), include_groups=False).values
    team_totals['wrc_plus'] = d.groupby(gt).apply(lambda g: weighted_avg(g, 'wrc_plus', 'pa'), include_groups=False).values

    return pd.concat([d, career, team_totals], ignore_index=True)


def _recompute_rates(df):
    # DataFrame already has final column names - just call formula functions directly
    f.compute_avg(df)
    f.compute_obp(df)
    f.compute_slg(df)
    f.compute_ops(df)
    f.compute_babip_bat(df)
    f.compute_iso(df)
    f.compute_hr_pct_bat(df)
    f.compute_k_pct_bat(df)
    f.compute_bb_pct_bat(df)
    f.compute_pa_per_gb(df)
    f.compute_pa_per_hr(df)
    f.compute_xbh_pct(df)
    f.compute_rs_pct(df)
    f.compute_rc_pct(df)
    f.compute_sb_pct(df)
    f.compute_sb_att_pct(df)
    f.compute_e_per_gf(df)
    f.compute_pb_per_gf(df)
    return df
