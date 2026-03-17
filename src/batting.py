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
    compute_wOBA,
    compute_AVG, compute_OBP, compute_SLG, compute_OPS, compute_ISO,
    compute_BABIP_bat,
    compute_HR_pct_bat, compute_K_pct_bat, compute_BB_pct_bat,
    compute_PA_per_GB, compute_PA_per_HR,
    compute_XBH_pct, compute_RS_pct, compute_RC_pct,
    compute_RS, compute_RB,
    compute_SB_pct, compute_SbAtt_pct,
    compute_E_per_GF, compute_PB_per_GF,
    compute_RAA_bat, compute_RAR_bat,
)


stats = None


def compute():
    global stats
    d = raw.batting_stats.copy()

    compute_AVG(d)
    compute_OBP(d)
    compute_SLG(d)
    compute_OPS(d)
    compute_BABIP_bat(d)
    compute_wOBA(d)
    compute_ISO(d)
    compute_HR_pct_bat(d)
    compute_K_pct_bat(d)
    compute_BB_pct_bat(d)
    compute_PA_per_GB(d)
    compute_PA_per_HR(d)
    compute_XBH_pct(d)
    compute_RS_pct(d)
    compute_RC_pct(d)
    compute_RS(d)
    compute_RB(d)
    compute_SB_pct(d)
    compute_SbAtt_pct(d)
    compute_E_per_GF(d)
    compute_PB_per_GF(d)

    # Park factor
    pf = (1 + d['Team'].map(park_factors)) / 2

    # Batting value (Rbat must come before wRC+)
    lg_wOBA = d['Season'].map(lg.season_batting['wOBA'])
    d['Rbat'] = ((d['wOBA'] - lg_wOBA * pf) / scale_wOBA) * d['PA']

    # Baserunning
    lg_wsb = d['Season'].map(lg.season_batting['lg_wSB'])
    d['Rbr'] = (d['SB'] * runs_SB + d['CS'] * runs_CS
                - lg_wsb * (d['1B'] + d['BB'] + d['HBP']))

    # Fielding
    avg_e  = d.set_index(['PP', '2P']).index.map(lg.pos_fielding['E/GF'])
    avg_pb = d.set_index(['PP', '2P']).index.map(lg.pos_fielding['PB/GF'])
    def_e  = (_div(d['E'],  d['GF']) - avg_e)  * runs_E * d['GB']
    def_pb = (_div(d['PB'], d['GF']) - avg_pb) * runs_E * d['GB']
    d['Rdef'] = def_e + def_pb

    # Positional
    rpos      = d.set_index(['PP', '2P']).index.map(lg.pos_adjustment['Rpos'])
    d['Rpos'] = rpos * d['GB'] / num_games

    d['Rcorr'] = 0.0
    compute_RAA_bat(d)

    # Zero-sum correction: distribute the season RAA imbalance proportionally by PA
    season_raa = d.groupby('Season')['RAA'].sum()
    season_pa  = d.groupby('Season')['PA'].sum()
    d['Rcorr'] = d['Season'].map(-season_raa / season_pa) * d['PA']
    compute_RAA_bat(d)

    rpw       = d['Season'].map(lg.season_batting['R/W'])
    d['Rrep'] = d['PA'] * d['Season'].map(lg.season_batting['RR/PA'])
    d['WAA']  = d['RAA'] / rpw
    compute_RAR_bat(d)
    d['WAR']  = d['RAR'] / rpw

    # Park-adjusted rate stats (computed after Rbat so order is correct)
    lg_wOBA = d['Season'].map(lg.season_batting['wOBA'])
    lg_obp  = d['Season'].map(lg.season_batting['OBP'])
    lg_slg  = d['Season'].map(lg.season_batting['SLG'])
    lg_wRC  = d['Season'].map(lg.season_batting['wRC'])
    lg_rPA  = d['Season'].map(lg.season_batting['R/PA'])
    lg_pa   = d['Season'].map(lg.season_batting['PA'])

    d['OPS+'] = 100 * ((d['OBP'] / lg_obp) + (d['SLG'] / lg_slg) - 1) / pf
    d['wRC']  = ((d['wOBA'] - lg_wOBA) / scale_wOBA + lg_rPA) * d['PA']
    d['wRC+'] = 100 * (d['Rbat'] / d['PA'] + lg_rPA) / (lg_wRC / lg_pa)

    d['stat_type'] = 'S'
    stats = _append_summary_rows(d)


def _append_summary_rows(d):
    gp = ['First Name', 'Last Name']
    gt = ['First Name', 'Last Name', 'Team']

    career = d.groupby(gp).sum(numeric_only=True).reset_index()
    career['Season']    = 'Career'
    career['Age']       = ''
    career['PP']        = ''
    career['2P']        = ''
    career['stat_type'] = 'C'
    team_counts = d.groupby(gp)['Team'].nunique().reset_index(name='Team')
    career = career.merge(team_counts, on=gp)
    career['Team'] = career['Team'].astype(str) + 'TM'
    career = _recompute_rates(career)
    career['wOBA'] = d.groupby(gp).apply(lambda g: weighted_avg(g, 'wOBA', 'PA'), include_groups=False).values
    career['OPS+'] = d.groupby(gp).apply(lambda g: weighted_avg(g, 'OPS+', 'PA'), include_groups=False).values
    career['wRC+'] = d.groupby(gp).apply(lambda g: weighted_avg(g, 'wRC+', 'PA'), include_groups=False).values

    team_totals = d.groupby(gt).sum(numeric_only=True).reset_index()
    season_counts = d.groupby(gt)['Season'].nunique().reset_index(name='Season')
    team_totals = team_totals.drop(columns=['Season']).merge(season_counts, on=gt)
    team_totals['Season'] = team_totals['Season'].apply(
        lambda n: f"{n} Szn" if n == 1 else f"{n} Szns")
    team_totals['Age']       = ''
    team_totals['PP']        = ''
    team_totals['2P']        = ''
    team_totals['stat_type'] = 'T'
    team_totals = _recompute_rates(team_totals)
    team_totals['wOBA'] = d.groupby(gt).apply(lambda g: weighted_avg(g, 'wOBA', 'PA'), include_groups=False).values
    team_totals['OPS+'] = d.groupby(gt).apply(lambda g: weighted_avg(g, 'OPS+', 'PA'), include_groups=False).values
    team_totals['wRC+'] = d.groupby(gt).apply(lambda g: weighted_avg(g, 'wRC+', 'PA'), include_groups=False).values

    return pd.concat([d, career, team_totals], ignore_index=True)


def _recompute_rates(df):
    compute_AVG(df)
    compute_OBP(df)
    compute_SLG(df)
    compute_OPS(df)
    compute_BABIP_bat(df)
    compute_ISO(df)
    compute_HR_pct_bat(df)
    compute_K_pct_bat(df)
    compute_BB_pct_bat(df)
    compute_PA_per_GB(df)
    compute_PA_per_HR(df)
    compute_XBH_pct(df)
    compute_RS_pct(df)
    compute_RC_pct(df)
    compute_SB_pct(df)
    compute_SbAtt_pct(df)
    compute_E_per_GF(df)
    compute_PB_per_GF(df)
    return df
