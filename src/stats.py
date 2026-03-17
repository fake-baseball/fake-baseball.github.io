"""
Compute all derived stats for batters and pitchers, then append career/team-total rows.
Requires league context from league.compute_league().
"""
import numpy as np
import pandas as pd

from util import fmt_ip

from constants import (
    scale_wOBA,
    runs_SB, runs_CS, runs_E, DEF_IMPACT,
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
    compute_ERA, compute_RA9, compute_WHIP,
    compute_BAA, compute_OBPA, compute_BABIP_pit,
    compute_WIN_pct,
    compute_K_per_9, compute_H_per_9, compute_HR_per_9, compute_BB_per_9,
    compute_K_per_BB,
    compute_HR_pct_pit, compute_K_pct_pit, compute_BB_pct_pit,
    compute_P_per_GP, compute_P_per_IP, compute_P_per_PA, compute_IP_per_GP,
    compute_SV_pct, compute_FIP_raw,
    compute_RAA_bat, compute_RAR_bat, compute_RAR_pit, compute_RAAlev, compute_RA9def,
)


# ── Batting ──────────────────────────────────────────────────────────────────

def compute_batting_stats(batters, lg):
    """
    batters - raw DataFrame from data.load_batters()
    lg      - league namespace from league.compute_league()
    Returns a new DataFrame with all derived columns plus career/team rows.
    """
    d = batters.copy()

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
    d = _append_batter_summary_rows(d)

    return d


def _append_batter_summary_rows(d):
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
    career = _recompute_batter_rates(career)
    career['wOBA'] = d.groupby(gp).apply(lambda g: _weighted(g, 'wOBA', 'PA'), include_groups=False).values
    career['OPS+'] = d.groupby(gp).apply(lambda g: _weighted(g, 'OPS+', 'PA'), include_groups=False).values
    career['wRC+'] = d.groupby(gp).apply(lambda g: _weighted(g, 'wRC+', 'PA'), include_groups=False).values

    team_totals = d.groupby(gt).sum(numeric_only=True).reset_index()
    season_counts = d.groupby(gt)['Season'].nunique().reset_index(name='Season')
    team_totals = team_totals.drop(columns=['Season']).merge(season_counts, on=gt)
    team_totals['Season'] = team_totals['Season'].apply(
        lambda n: f"{n} Szn" if n == 1 else f"{n} Szns")
    team_totals['Age']       = ''
    team_totals['PP']        = ''
    team_totals['2P']        = ''
    team_totals['stat_type'] = 'T'
    team_totals = _recompute_batter_rates(team_totals)
    team_totals['wOBA'] = d.groupby(gt).apply(lambda g: _weighted(g, 'wOBA', 'PA'), include_groups=False).values
    team_totals['OPS+'] = d.groupby(gt).apply(lambda g: _weighted(g, 'OPS+', 'PA'), include_groups=False).values
    team_totals['wRC+'] = d.groupby(gt).apply(lambda g: _weighted(g, 'wRC+', 'PA'), include_groups=False).values

    return pd.concat([d, career, team_totals], ignore_index=True)


def _recompute_batter_rates(df):
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


# ── Pitching ─────────────────────────────────────────────────────────────────

def compute_pitching_stats(pitchers, lg):
    """
    pitchers - raw DataFrame from data.load_pitchers()
    lg       - league namespace from league.compute_league()
    Returns a new DataFrame with all derived columns plus career/team rows.
    """
    d = pitchers.copy()

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
    d = _append_pitcher_summary_rows(d)

    return d


def _append_pitcher_summary_rows(d):
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
    career = _recompute_pitcher_rates(career)
    career['ERA-']   = d.groupby(gp).apply(lambda g: _weighted(g, 'ERA-',   'IP_true'), include_groups=False).values
    career['FIP']    = d.groupby(gp).apply(lambda g: _weighted(g, 'FIP',    'IP_true'), include_groups=False).values
    career['RA9def'] = d.groupby(gp).apply(lambda g: _weighted(g, 'RA9def', 'IP_true'), include_groups=False).values

    team_totals = d.groupby(gt).sum(numeric_only=True).reset_index()
    season_counts = d.groupby(gt)['Season'].nunique().reset_index(name='Season')
    team_totals = team_totals.drop(columns=['Season']).merge(season_counts, on=gt)
    team_totals['Season'] = team_totals['Season'].apply(
        lambda n: f"{n} Szn" if n == 1 else f"{n} Szns")
    team_totals['Age']       = ''
    team_totals['Role']      = ''
    team_totals['stat_type'] = 'T'
    team_totals = _recompute_pitcher_rates(team_totals)
    team_totals['ERA-']   = d.groupby(gt).apply(lambda g: _weighted(g, 'ERA-',   'IP_true'), include_groups=False).values
    team_totals['FIP']    = d.groupby(gt).apply(lambda g: _weighted(g, 'FIP',    'IP_true'), include_groups=False).values
    team_totals['RA9def'] = d.groupby(gt).apply(lambda g: _weighted(g, 'RA9def', 'IP_true'), include_groups=False).values

    return pd.concat([d, career, team_totals], ignore_index=True)


def _recompute_pitcher_rates(df):
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


# ── Helpers ──────────────────────────────────────────────────────────────────

def _weighted(df, stat, weight_col):
    w = df[weight_col].sum()
    return (df[stat] * df[weight_col]).sum() / w if w != 0 else 0.0
