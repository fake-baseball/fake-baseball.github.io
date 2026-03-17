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
    compute_ERA, compute_RA9, compute_WHIP,
    compute_BAA, compute_OBPA, compute_BABIP_pit,
    compute_WIN_pct,
    compute_K_per_9, compute_H_per_9, compute_HR_per_9, compute_BB_per_9,
    compute_K_per_BB,
    compute_HR_pct_pit, compute_K_pct_pit, compute_BB_pct_pit,
    compute_P_per_GP, compute_P_per_IP, compute_P_per_PA, compute_IP_per_GP,
    compute_SV_pct, compute_FIP_raw,
    compute_RAR_pit, compute_RAAlev, compute_RA9def,
)


stats = None


def compute():
    global stats
    d = raw.pitching_stats.copy()

    compute_ERA(d)
    d['ERA-'] = 100 * d['ERA'] / d['Season'].map(lg.season_pitching['ERA'])
    compute_RA9(d)
    compute_WHIP(d)
    compute_FIP_raw(d)
    d['FIP'] += d['Season'].map(lg.season_pitching['cFIP'])
    compute_BAA(d)
    compute_OBPA(d)
    compute_BABIP_pit(d)
    compute_WIN_pct(d)
    compute_K_per_9(d)
    compute_H_per_9(d)
    compute_HR_per_9(d)
    compute_BB_per_9(d)
    compute_K_per_BB(d)
    compute_HR_pct_pit(d)
    compute_K_pct_pit(d)
    compute_BB_pct_pit(d)
    compute_P_per_GP(d)
    compute_P_per_IP(d)
    compute_P_per_PA(d)
    compute_IP_per_GP(d)
    compute_SV_pct(d)

    # Defense-adjusted RA9
    bip        = d['BF'] - d['BB'] - d['HBP'] - d['K'] - d['HR']
    babip_diff = d.apply(
        lambda row: lg.team_defense.loc[(row['Season'], row['Team']), 'BABIP_diff'], axis=1)
    rh         = d['Season'].map(lg.season_pitching['R/H'])
    d['Rdef']  = -bip * babip_diff * rh * DEF_IMPACT
    compute_RA9def(d)

    # WAR
    pf       = (1 + d['Team'].map(park_factors)) / 2
    ra9_comp = d.apply(
        lambda row: lg.role_pitching.loc[(row['Season'], row['Role'] == 'SP'), 'RA9'], axis=1)

    base_raa = (ra9_comp * pf - d['RA9def']) / 9 * d['IP_true']

    # Zero-sum correction: distribute the season RAA imbalance proportionally by IP
    d['Rcorr'] = 0.0
    d['RAA']   = base_raa
    season_raa = d.groupby('Season')['RAA'].sum()
    season_ip  = d.groupby('Season')['IP_true'].sum()
    d['Rcorr'] = d['Season'].map(-season_raa / season_ip) * d['IP_true']
    d['RAA']   = base_raa + d['Rcorr']

    d['Rlev']   = d.apply(
        lambda row: (
            row['SV']               * lg.role_leverage.loc[(row['Season'], row['Role']), 'R_sv'] +
            (row['GR'] - row['SV']) * lg.role_leverage.loc[(row['Season'], row['Role']), 'R_no_SV']
        ), axis=1)
    compute_RAAlev(d)

    rpw      = d['Season'].map(lg.season_batting['R/W'])
    d['WAA'] = d['RAAlev'] / rpw

    wrep     = d['IP_true'] * d.apply(
        lambda row: lg.role_innings.loc[
            (row['Season'], 'RP' if row['Role'] == 'CL' else row['Role']), 'RW/IP'
        ], axis=1)
    d['Rrep'] = rpw * wrep
    compute_RAR_pit(d)
    d['WAR']  = d['RAR'] / rpw

    d['stat_type'] = 'S'
    stats = _append_summary_rows(d)


def _append_summary_rows(d):
    gp = ['First Name', 'Last Name']
    gt = ['First Name', 'Last Name', 'Team']

    career = d.groupby(gp).sum(numeric_only=True).reset_index()
    career['Season']    = 'Career'
    career['Age']       = ''
    career['Role']      = ''
    career['stat_type'] = 'C'
    team_counts = d.groupby(gp)['Team'].nunique().reset_index(name='Team')
    career = career.merge(team_counts, on=gp)
    career['Team'] = career['Team'].astype(str) + 'TM'
    career = _recompute_rates(career)
    career['ERA-']   = d.groupby(gp).apply(lambda g: weighted_avg(g, 'ERA-',   'IP_true'), include_groups=False).values
    career['FIP']    = d.groupby(gp).apply(lambda g: weighted_avg(g, 'FIP',    'IP_true'), include_groups=False).values
    career['RA9def'] = d.groupby(gp).apply(lambda g: weighted_avg(g, 'RA9def', 'IP_true'), include_groups=False).values

    team_totals = d.groupby(gt).sum(numeric_only=True).reset_index()
    season_counts = d.groupby(gt)['Season'].nunique().reset_index(name='Season')
    team_totals = team_totals.drop(columns=['Season']).merge(season_counts, on=gt)
    team_totals['Season'] = team_totals['Season'].apply(
        lambda n: f"{n} Szn" if n == 1 else f"{n} Szns")
    team_totals['Age']       = ''
    team_totals['Role']      = ''
    team_totals['stat_type'] = 'T'
    team_totals = _recompute_rates(team_totals)
    team_totals['ERA-']   = d.groupby(gt).apply(lambda g: weighted_avg(g, 'ERA-',   'IP_true'), include_groups=False).values
    team_totals['FIP']    = d.groupby(gt).apply(lambda g: weighted_avg(g, 'FIP',    'IP_true'), include_groups=False).values
    team_totals['RA9def'] = d.groupby(gt).apply(lambda g: weighted_avg(g, 'RA9def', 'IP_true'), include_groups=False).values

    return pd.concat([d, career, team_totals], ignore_index=True)


def _recompute_rates(df):
    df['IP'] = df['IP_true'].map(fmt_ip)

    compute_ERA(df)
    compute_RA9(df)
    compute_WHIP(df)
    compute_BAA(df)
    compute_OBPA(df)
    compute_BABIP_pit(df)
    compute_WIN_pct(df)
    compute_K_per_9(df)
    compute_H_per_9(df)
    compute_HR_per_9(df)
    compute_BB_per_9(df)
    compute_K_per_BB(df)
    compute_K_pct_pit(df)
    compute_BB_pct_pit(df)
    compute_P_per_GP(df)
    compute_P_per_IP(df)
    compute_P_per_PA(df)
    compute_IP_per_GP(df)
    compute_SV_pct(df)
    return df
