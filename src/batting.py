"""
Compute derived batting stats from basic stats and league context.
Call compute() after data.stats.load_batting() and league.compute_league().
Results are stored in batting.stats.
"""
import numpy as np
import pandas as pd

import league as lg
from data import stats as raw
from util import weighted_avg

from constants import (
    scale_wOBA,
    runs_SB, runs_CS, runs_E,
    park_factors, num_games,
)
from formulas import (
    _div,
    compute_woba,
    compute_avg, compute_obp, compute_slg, compute_ops, compute_iso,
    compute_babip_bat,
    compute_hr_pct_bat, compute_k_pct_bat, compute_bb_pct_bat,
    compute_pa_per_gb, compute_pa_per_hr,
    compute_xbh_pct, compute_rs_pct, compute_rc_pct,
    compute_rs, compute_rb,
    compute_sb_pct, compute_sb_att_pct,
    compute_e_per_gf, compute_pb_per_gf,
    compute_b_raa, compute_b_rar,
)

# batting_stats is already renamed to final names in data/stats.py load_batting()


stats = None


def compute():
    global stats
    # batting_stats already has final column names from load_batting()
    d = raw.batting_stats.copy()

    compute_avg(d)
    compute_obp(d)
    compute_slg(d)
    compute_ops(d)
    compute_babip_bat(d)
    compute_woba(d)
    compute_iso(d)
    compute_hr_pct_bat(d)
    compute_k_pct_bat(d)
    compute_bb_pct_bat(d)
    compute_pa_per_gb(d)
    compute_pa_per_hr(d)
    compute_xbh_pct(d)
    compute_rs_pct(d)
    compute_rc_pct(d)
    compute_rs(d)
    compute_rb(d)
    compute_sb_pct(d)
    compute_sb_att_pct(d)
    compute_e_per_gf(d)
    compute_pb_per_gf(d)

    # Park factor
    pf = (1 + d['team'].map(park_factors)) / 2

    # Batting value (r_bat must come before wrc_plus)
    lg_woba = d['season'].map(lg.season_batting['woba'])
    d['r_bat'] = ((d['woba'] - lg_woba * pf) / scale_wOBA) * d['pa']

    # Baserunning
    lg_wsb = d['season'].map(lg.season_batting['lg_wsb'])
    d['r_br'] = (d['sb'] * runs_SB + d['cs'] * runs_CS
                 - lg_wsb * (d['b_1b'] + d['bb'] + d['hbp']))

    # Fielding
    avg_e  = d.set_index(['pos1', 'pos2']).index.map(lg.pos_fielding['e_per_gf'])
    avg_pb = d.set_index(['pos1', 'pos2']).index.map(lg.pos_fielding['pb_per_gf'])
    def_e  = (_div(d['e'],  d['gf']) - avg_e)  * runs_E * d['gb']
    def_pb = (_div(d['pb'], d['gf']) - avg_pb) * runs_E * d['gb']
    d['r_def'] = def_e + def_pb

    # Positional
    rpos      = d.set_index(['pos1', 'pos2']).index.map(lg.pos_adjustment['r_pos'])
    d['r_pos'] = rpos * d['gb'] / num_games

    d['r_corr'] = 0.0
    compute_b_raa(d)

    # Zero-sum correction: distribute the season RAA imbalance proportionally by PA
    season_raa = d.groupby('season')['raa'].sum()
    season_pa  = d.groupby('season')['pa'].sum()
    d['r_corr'] = d['season'].map(-season_raa / season_pa) * d['pa']
    compute_b_raa(d)

    rpw       = d['season'].map(lg.season_batting['r_per_w'])
    d['r_rep'] = d['pa'] * d['season'].map(lg.season_batting['rr_per_pa'])
    d['waa']  = d['raa'] / rpw
    compute_b_rar(d)
    d['war']  = d['rar'] / rpw

    # Park-adjusted rate stats (computed after r_bat so order is correct)
    lg_woba = d['season'].map(lg.season_batting['woba'])
    lg_obp  = d['season'].map(lg.season_batting['obp'])
    lg_slg  = d['season'].map(lg.season_batting['slg'])
    lg_wRC  = d['season'].map(lg.season_batting['wrc'])
    lg_rPA  = d['season'].map(lg.season_batting['r_per_pa'])
    lg_pa   = d['season'].map(lg.season_batting['pa'])

    d['ops_plus'] = 100 * ((d['obp'] / lg_obp) + (d['slg'] / lg_slg) - 1) / pf
    d['wrc']      = ((d['woba'] - lg_woba) / scale_wOBA + lg_rPA) * d['pa']
    d['wrc_plus'] = 100 * (d['r_bat'] / d['pa'] + lg_rPA) / (lg_wRC / lg_pa)

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
    compute_avg(df)
    compute_obp(df)
    compute_slg(df)
    compute_ops(df)
    compute_babip_bat(df)
    compute_iso(df)
    compute_hr_pct_bat(df)
    compute_k_pct_bat(df)
    compute_bb_pct_bat(df)
    compute_pa_per_gb(df)
    compute_pa_per_hr(df)
    compute_xbh_pct(df)
    compute_rs_pct(df)
    compute_rc_pct(df)
    compute_sb_pct(df)
    compute_sb_att_pct(df)
    compute_e_per_gf(df)
    compute_pb_per_gf(df)
    return df
