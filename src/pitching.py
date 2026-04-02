"""
Compute derived pitching stats from basic stats and league context.
Call compute() after data.stats.load_pitching() and league.compute_league().
Results are stored in pitching.stats.
"""
import numpy as np
import pandas as pd

import league as lg
from data import stats as raw
from util import fmt_ip, weighted_avg

from constants import (
    runs_E, DEF_IMPACT,
    park_factors,
)
from formulas import (
    _div,
    compute_p_era, compute_p_ra9, compute_p_whip,
    compute_p_baa, compute_p_obpa, compute_p_babip,
    compute_p_win_pct,
    compute_p_k_per_9, compute_p_h_per_9, compute_p_hr_per_9, compute_p_bb_per_9,
    compute_p_k_per_bb,
    compute_p_hr_pct, compute_p_k_pct, compute_p_bb_pct,
    compute_p_p_per_gp, compute_p_p_per_ip, compute_p_p_per_pa, compute_p_ip_per_gp,
    compute_p_sv_pct, compute_p_cyp, compute_fip_raw,
    compute_p_rar, compute_p_raa_lev, compute_p_ra9_def,
)

stats = None


def compute():
    global stats
    d = raw.pitching_stats.copy()
    # Columns are already renamed to final names by load_pitching() in data/stats.py

    compute_p_era(d)
    d['p_era_minus'] = 100 * d['p_era'] / d['season'].map(lg.season_pitching['p_era'])
    compute_p_ra9(d)
    compute_p_whip(d)
    compute_fip_raw(d)
    d['p_fip'] += d['season'].map(lg.season_pitching['p_cfip'])
    compute_p_baa(d)
    compute_p_obpa(d)
    compute_p_babip(d)
    compute_p_win_pct(d)
    compute_p_k_per_9(d)
    compute_p_h_per_9(d)
    compute_p_hr_per_9(d)
    compute_p_bb_per_9(d)
    compute_p_k_per_bb(d)
    compute_p_hr_pct(d)
    compute_p_k_pct(d)
    compute_p_bb_pct(d)
    compute_p_p_per_gp(d)
    compute_p_p_per_ip(d)
    compute_p_p_per_pa(d)
    compute_p_ip_per_gp(d)
    compute_p_sv_pct(d)

    # Defense-adjusted RA9
    bip        = d['p_bf'] - d['p_bb'] - d['p_hbp'] - d['p_k'] - d['p_hr']
    babip_diff = d.apply(
        lambda row: lg.team_defense.loc[(row['season'], row['team']), 'p_babip_diff']
        if pd.notna(row['team']) else 0.0, axis=1)
    rh         = d['season'].map(lg.season_pitching['r_per_h'])
    d['p_r_def']  = -bip * babip_diff * rh * DEF_IMPACT
    compute_p_ra9_def(d)

    # WAR
    pf       = (1 + d['team'].map(park_factors).fillna(0)) / 2
    ra9_comp = d.apply(
        lambda row: lg.role_pitching.loc[(row['season'], row['role'] == 'SP'), 'p_ra9'], axis=1)

    base_raa = (ra9_comp * pf - d['p_ra9_def']) / 9 * d['p_ip']

    # Zero-sum correction: distribute the season RAA imbalance proportionally by IP
    d['p_r_corr'] = 0.0
    d['p_raa']    = base_raa
    season_raa = d.groupby('season')['p_raa'].sum()
    season_ip  = d.groupby('season')['p_ip'].sum()
    d['p_r_corr'] = d['season'].map(-season_raa / season_ip) * d['p_ip']
    d['p_raa']    = base_raa + d['p_r_corr']

    d['p_r_lev']   = d.apply(
        lambda row: (
            row['p_sv']               * lg.role_leverage.loc[(row['season'], row['role']), 'r_sv'] +
            (row['p_gr'] - row['p_sv']) * lg.role_leverage.loc[(row['season'], row['role']), 'r_no_sv']
        ), axis=1)
    compute_p_raa_lev(d)

    rpw       = d['season'].map(lg.season_batting['r_per_w'])
    d['p_waa'] = d['p_raa_lev'] / rpw

    wrep       = d['p_ip'] * d.apply(
        lambda row: lg.role_innings.loc[
            (row['season'], 'RP' if row['role'] == 'CL' else row['role']), 'rw_per_ip'
        ], axis=1)
    d['p_r_rep'] = rpw * wrep
    compute_p_rar(d)
    d['p_war']  = d['p_rar'] / rpw

    # Victory Bonus: 1 if pitcher's team won their division that season
    from data import teams as teams_data
    div_winners = set()
    if teams_data.standings is not None and teams_data.teams is not None:
        abbr_map = teams_data.teams.set_index('team_name')['abbr'].to_dict()
        for _, row in teams_data.standings[teams_data.standings['GB'] == 0].iterrows():
            abbr = abbr_map.get(row['teamName'])
            if abbr:
                div_winners.add((row['Season'], abbr))
    d['p_vb'] = d.apply(lambda row: 1 if (row['season'], row['team']) in div_winners else 0, axis=1)
    compute_p_cyp(d)

    d['stat_type'] = 'season'
    stats = _append_summary_rows(d)


def _append_summary_rows(d):
    gp = ['First Name', 'Last Name']
    gt = ['First Name', 'Last Name', 'team']

    career = d.groupby(gp).sum(numeric_only=True).reset_index()
    career['season']    = 'Career'
    career['age']       = ''
    career['role']      = ''
    career['stat_type'] = 'career'
    team_counts = d.groupby(gp)['team'].nunique().reset_index(name='team')
    career = career.merge(team_counts, on=gp)
    career['team'] = career['team'].astype(str) + 'TM'
    career = _recompute_rates(career)
    career['p_era_minus'] = d.groupby(gp).apply(lambda g: weighted_avg(g, 'p_era_minus', 'p_ip'), include_groups=False).values
    career['p_fip']       = d.groupby(gp).apply(lambda g: weighted_avg(g, 'p_fip',       'p_ip'), include_groups=False).values
    career['p_ra9_def']   = d.groupby(gp).apply(lambda g: weighted_avg(g, 'p_ra9_def',   'p_ip'), include_groups=False).values

    team_totals = d.groupby(gt).sum(numeric_only=True).reset_index()
    season_counts = d.groupby(gt)['season'].nunique().reset_index(name='season')
    team_totals = team_totals.drop(columns=['season']).merge(season_counts, on=gt)
    team_totals['season'] = team_totals['season'].apply(
        lambda n: f"{n} Szn" if n == 1 else f"{n} Szns")
    team_totals['age']       = ''
    team_totals['role']      = ''
    team_totals['stat_type'] = 'team'
    team_totals = _recompute_rates(team_totals)
    team_totals['p_era_minus'] = d.groupby(gt).apply(lambda g: weighted_avg(g, 'p_era_minus', 'p_ip'), include_groups=False).values
    team_totals['p_fip']       = d.groupby(gt).apply(lambda g: weighted_avg(g, 'p_fip',       'p_ip'), include_groups=False).values
    team_totals['p_ra9_def']   = d.groupby(gt).apply(lambda g: weighted_avg(g, 'p_ra9_def',   'p_ip'), include_groups=False).values

    return pd.concat([d, career, team_totals], ignore_index=True)


def _recompute_rates(df):
    # DataFrame already has final column names - just call formula functions directly
    compute_p_era(df)
    compute_p_ra9(df)
    compute_p_whip(df)
    compute_p_baa(df)
    compute_p_obpa(df)
    compute_p_babip(df)
    compute_p_win_pct(df)
    compute_p_k_per_9(df)
    compute_p_h_per_9(df)
    compute_p_hr_per_9(df)
    compute_p_bb_per_9(df)
    compute_p_k_per_bb(df)
    compute_p_k_pct(df)
    compute_p_bb_pct(df)
    compute_p_p_per_gp(df)
    compute_p_p_per_ip(df)
    compute_p_p_per_pa(df)
    compute_p_ip_per_gp(df)
    compute_p_sv_pct(df)
    return df
