"""Compute batter projections using weighted recent-season component rates.

For each active player, for each of the 3 projection seasons:
  - If the player had qualified PA: use their actual stat/PA rate.
  - Otherwise: fill the missing PA using the model's predicted rate, then recompute.

The model is a linear regression fit on players who qualified in all 3 seasons.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

import batting as bat_module
import league as lg
from data import players
from data import teams as teams_data
from constants import (BAT_SEASON_MIN_PA, scale_wOBA, num_games,
                       PROJ_SEASONS, PROJ_WEIGHTS as WEIGHTS, PROJ_WEIGHT_TOTAL as WEIGHT_TOTAL,
                       total_WAR, batter_share, runs_SB, runs_CS, park_factors,
                       CURRENT_SEASON, LAST_COMPLETED_SEASON)
from formulas import compute_tb, compute_avg, compute_obp, compute_slg, compute_ops, compute_woba

# Component names as they appear in batting.stats (final column names)
# These are per-PA rate components
COMPONENTS   = ['bb', 'hbp', 'b_1b', 'b_2b', 'b_3b', 'hr', 'k', 'sb', 'cs']
SKILLS       = ['power', 'contact', 'speed', 'fielding', 'arm']

def compute():
    """Return (rows, metrics) for all active players.

    rows: list of dicts sorted by last/first name.
          Keys: first, last, power, contact, speed,
                {comp} (blended projected rate) for each COMPONENT,
                x{comp} (model predicted rate) for each COMPONENT.
    metrics: list of dicts (one per component) with r2, rmse, and coefficients.
             Computed on the training set (players qualified in all 3 seasons).
    """
    active = set(players.player_info.index[~players.player_info['is_retired']])

    df = bat_module.stats[
        (bat_module.stats['season'].isin(PROJ_SEASONS)) &
        (bat_module.stats['stat_type'] == 'season')
    ].copy()
    df = df[df['player_id'].isin(active)]

    # ── Step 1: Fit regression on players qualified in all 3 seasons ─────────

    df_qual     = df[df['pa'] >= BAT_SEASON_MIN_PA].copy()
    full_counts = df_qual.groupby('player_id')['season'].nunique()
    full_names  = full_counts[full_counts == len(PROJ_SEASONS)].index
    df_train    = df_qual[df_qual['player_id'].isin(full_names)].copy()

    for comp in COMPONENTS:
        df_train[f'{comp}_rate'] = df_train[comp] / df_train['pa']

    train_rows = []
    for pid, group in df_train.groupby('player_id'):
        proj = {comp: sum(
            group.loc[group['season'] == s, f'{comp}_rate'].iloc[0] * WEIGHTS[s]
            for s in PROJ_SEASONS
        ) / WEIGHT_TOTAL for comp in COMPONENTS}
        try:
            pi = players.player_info_proj.loc[pid]
        except KeyError:
            pi = players.player_info.loc[pid]
        train_rows.append({
            'player_id': pid,
            'power': int(pi['power']), 'contact': int(pi['contact']), 'speed': int(pi['speed']),
            **proj,
        })

    X_train = np.array([[r['power'], r['contact'], r['speed']] for r in train_rows], dtype=float)
    models  = {}
    for comp in COMPONENTS:
        y            = np.array([r[comp] for r in train_rows], dtype=float)
        models[comp] = LinearRegression().fit(X_train, y)

    # ── Step 2: Project all active players ────────────────────────────────────

    rows = []
    for pid in active:
        if players.player_info.loc[pid]['pos1'] == 'P':
            continue
        try:
            pi = players.player_info_proj.loc[pid]
        except KeyError:
            pi = players.player_info.loc[pid]
        first, last = pi['first_name'], pi['last_name']
        power    = int(pi['power'])
        contact  = int(pi['contact'])
        speed    = int(pi['speed'])
        fielding = int(pi['fielding'])
        arm      = int(pi['arm'])
        X_pred   = np.array([[power, contact, speed]], dtype=float)
        model_rates = {comp: models[comp].predict(X_pred)[0] for comp in COMPONENTS}

        season_pa = {}
        for s in PROJ_SEASONS:
            season_row     = df[(df['player_id'] == pid) & (df['season'] == s)]
            season_pa[s]   = int(season_row.iloc[0]['pa']) if not season_row.empty else 0

        proj = {}
        for comp in COMPONENTS:
            weighted_sum = 0.0
            for s in PROJ_SEASONS:
                season_row  = df[(df['player_id'] == pid) & (df['season'] == s)]
                actual_pa   = season_pa[s]
                actual_stat = float(season_row.iloc[0][comp]) if not season_row.empty else 0.0

                if actual_pa >= BAT_SEASON_MIN_PA:
                    rate = actual_stat / actual_pa
                else:
                    missing_pa = BAT_SEASON_MIN_PA - actual_pa
                    rate = (actual_stat + model_rates[comp] * missing_pa) / BAT_SEASON_MIN_PA

                weighted_sum += rate * WEIGHTS[s]
            proj[comp] = max(0.0, weighted_sum / WEIGHT_TOTAL)

        rows.append({
            'player_id': pid,
            'power':     power,
            'contact':   contact,
            'speed':     speed,
            'fielding':  fielding,
            'arm':       arm,
            'team':      str(pi['team_name']) if 'team_name' in pi.index else '',
            **{f'pa_{s}': season_pa[s] for s in PROJ_SEASONS},
            **{f'x{comp}': model_rates[comp] for comp in COMPONENTS},
            **{f'{comp}_rate': v for comp, v in proj.items()},
        })

    rows.sort(key=lambda r: r['player_id'])
    return rows


PA_FEATURES = ['power', 'contact', 'speed', 'fielding', 'arm']
PA_MAX             = 300


def fit_pa_model():
    """Fit PA ~ POW + CON + SPD + FLD + ARM for active position players using last completed season data.

    Returns dict with keys: model, r2, rmse, coefs, intercept, n.
    """
    s20 = bat_module.stats[
        (bat_module.stats['season'] == LAST_COMPLETED_SEASON) &
        (bat_module.stats['stat_type'] == 'season') &
        (bat_module.stats['pa'] > 0)
    ].copy()

    pi = players.player_info_proj.reset_index()
    pi = pi[pi['pos1'] != 'P'][['player_id'] + PA_FEATURES]
    merged = s20.merge(pi, on='player_id')

    X = merged[PA_FEATURES].values.astype(float)
    y = merged['pa'].values.astype(float)

    return LinearRegression().fit(X, y)


rows = None


def compute_all():
    """Full projection computation: blended rates + PA model + derived stats.

    Sets and returns bat_projections.rows (list of enriched row dicts, sorted by last/first).
    """
    global rows

    rows   = compute()
    pa_reg = fit_pa_model()

    for row in rows:
        row['proj_pa'] = min(PA_MAX, max(0, int(round(pa_reg.predict([[row[f] for f in PA_FEATURES]])[0]))))

        # Use final batting column names in temp dict for formula functions
        d = {
            'bb': row['bb_rate'], 'hbp': row['hbp_rate'],
            'b_1b': row['b_1b_rate'], 'b_2b': row['b_2b_rate'], 'b_3b': row['b_3b_rate'], 'hr': row['hr_rate'],
            'h':  row['b_1b_rate'] + row['b_2b_rate'] + row['b_3b_rate'] + row['hr_rate'],
            'ab': max(0.0, 1.0 - row['bb_rate'] - row['hbp_rate']),
            'sf': 0.0,
        }
        compute_tb(d); compute_avg(d); compute_obp(d); compute_slg(d)
        compute_ops(d); compute_woba(d)
        row['avg']  = d['avg']
        row['obp']  = d['obp']
        row['slg']  = d['slg']
        row['ops']  = d['ops']
        row['woba'] = d['woba']
        row['hr']   = int(round(row['proj_pa'] * row['hr_rate']))
        row['k']    = int(round(row['proj_pa'] * row['k_rate']))
        row['sb']   = int(round(row['proj_pa'] * row['sb_rate']))
        row['cs']   = int(round(row['proj_pa'] * row['cs_rate']))
        bip_rate    = 1.0 - row['bb_rate'] - row['hbp_rate'] - row['k_rate'] - row['hr_rate']
        row['babip'] = (row['b_1b_rate'] + row['b_2b_rate'] + row['b_3b_rate']) / bip_rate if bip_rate > 0 else 0.0

    # League context: 5/4/3 weighted average across seasons 18-20
    def _lg_avg(col):
        return sum(WEIGHTS[s] * lg.season_batting.loc[s, col] for s in PROJ_SEASONS) / WEIGHT_TOTAL

    lg_wOBA_20 = _lg_avg('woba')
    rpw_20     = _lg_avg('r_per_w')
    lg_rPA_20  = _lg_avg('r_per_pa')
    lg_wrcpa   = _lg_avg('wrc') / _lg_avg('pa')  # used as wRC/PA in wRC+ formula
    lg_pa_20   = _lg_avg('pa')
    lg_rrpa_20 = _lg_avg('rr_per_pa')
    lg_wSB     = _lg_avg('lg_wsb')
    lg_obp_20  = _lg_avg('obp')
    lg_slg_20  = _lg_avg('slg')

    s20 = bat_module.stats[
        (bat_module.stats['season'] == LAST_COMPLETED_SEASON) &
        (bat_module.stats['stat_type'] == 'season') &
        (bat_module.stats['pa'] > 0) &
        (bat_module.stats['gb'] > 0)
    ]
    pa_per_gb = (s20['pa'] / s20['gb']).mean()

    abbr_map = teams_data.teams.set_index('team_name')['abbr']

    for row in rows:
        pi = players.player_info.loc[row['player_id']]
        pp = pi['pos1']
        sp = pi['pos2']
        team_abbr = abbr_map.get(row['team'], '')
        pf     = (1 + park_factors.get(team_abbr, 1.0)) / 2
        r_bat  = ((row['woba'] - lg_wOBA_20 * pf) / scale_wOBA) * row['proj_pa']
        xGB    = row['proj_pa'] / pa_per_gb if pa_per_gb > 0 else 0.0
        row['gb'] = max(0, min(num_games, int(round(xGB))))
        row['ops_plus'] = 100 * ((row['obp'] / lg_obp_20) + (row['slg'] / lg_slg_20) - 1) / pf if lg_obp_20 > 0 and lg_slg_20 > 0 else 100.0
        try:
            rpos_per_g = lg.pos_adjustment.loc[(pp, sp), 'r_pos']
        except KeyError:
            rpos_per_g = 0.0
        r_pos = rpos_per_g * row['gb'] / num_games
        r_br  = (row['sb_rate'] * runs_SB + row['cs_rate'] * runs_CS
                 - lg_wSB * (row['b_1b_rate'] + row['bb_rate'] + row['hbp_rate'])) * row['proj_pa']
        row['r_bat']  = r_bat
        row['r_pos']  = r_pos
        row['r_br']   = r_br
        row['_raa']   = r_bat + r_br + r_pos
        row['_rrep']  = row['proj_pa'] * lg_rrpa_20
        if row['proj_pa'] > 0 and lg_wrcpa > 0:
            row['wrc_plus'] = 100 * (r_bat / row['proj_pa'] + lg_rPA_20) / lg_wrcpa
            row['wrc']      = r_bat + lg_rPA_20 * row['proj_pa']
        else:
            row['wrc_plus'] = 0.0
            row['wrc']      = 0.0

    # Rcorr: target correct total WAR using only rostered players to set the rate
    rostered    = [r for r in rows if r['team'] != 'FREE AGENT']
    total_raa   = sum(r['_raa']  for r in rostered)
    total_rrep  = sum(r['_rrep'] for r in rostered)
    total_pa    = sum(r['proj_pa'] for r in rostered)
    target_raa  = total_WAR * batter_share * rpw_20 - total_rrep
    corr_rate   = (target_raa - total_raa) / total_pa if total_pa > 0 else 0.0
    for row in rows:
        r_corr      = corr_rate * row['proj_pa']
        raa         = row['_raa'] + r_corr
        rar         = raa + row['_rrep']
        row['r_corr'] = r_corr
        row['r_rep']  = row['_rrep']
        row['raa']    = raa
        row['rar']    = rar
        row['waa']    = raa / rpw_20 if rpw_20 > 0 else 0.0
        row['war']    = rar / rpw_20 if rpw_20 > 0 else 0.0

    # ── Fit OLS: RBI/PA ~ 1B_rate + 2B_rate + 3B_rate + HR_rate + (BB+HBP)_rate
    # BB and HBP are combined: both put the batter on base with no contact and
    # almost never directly drive in a run, so they share a single coefficient.
    RBI_FEATURES = ['b_1b', 'b_2b', 'b_3b', 'hr', 'BB_HBP']
    df_all = bat_module.stats[
        (bat_module.stats['stat_type'] == 'season') &
        (bat_module.stats['pa'] >= BAT_SEASON_MIN_PA)
    ].copy()
    df_all['BB_HBP'] = df_all['bb'] + df_all['hbp']
    for feat in RBI_FEATURES:
        df_all[f'{feat}_rate'] = df_all[feat] / df_all['pa']
    X_rbi     = df_all[[f'{feat}_rate' for feat in RBI_FEATURES]].values.astype(float)
    y_rbi     = (df_all['rbi'] / df_all['pa']).values.astype(float)
    rbi_model = LinearRegression().fit(X_rbi, y_rbi)

    # ── Projected R via league-average RC% x projected non-HR OB events ───────
    # RC% = (R - HR) / (H - HR + BB + HBP): context-driven, not a player skill,
    # so we use the weighted league average rather than individual player history.
    df_proj = bat_module.stats[
        (bat_module.stats['season'].isin(PROJ_SEASONS)) &
        (bat_module.stats['stat_type'] == 'season')
    ]
    lg_rc_pct_total = 0.0
    for s in PROJ_SEASONS:
        s_df            = df_proj[df_proj['season'] == s]
        total_non_hr_ob = (s_df['h'] - s_df['hr'] + s_df['bb'] + s_df['hbp']).sum()
        lg_rc_pct_s     = (s_df['r'] - s_df['hr']).sum() / total_non_hr_ob if total_non_hr_ob > 0 else 0.0
        lg_rc_pct_total += WEIGHTS[s] * lg_rc_pct_s
    lg_rc_pct = lg_rc_pct_total / WEIGHT_TOTAL

    for row in rows:
        proj_non_hr_ob = row['proj_pa'] * (
            row['b_1b_rate'] + row['b_2b_rate'] + row['b_3b_rate'] + row['bb_rate'] + row['hbp_rate']
        )
        row['r'] = int(round(row['hr'] + proj_non_hr_ob * lg_rc_pct))

        # rbi: OLS on blended per-PA component rates (BB+HBP combined)
        X_pred        = [[row['b_1b_rate'], row['b_2b_rate'], row['b_3b_rate'], row['hr_rate'], row['bb_rate'] + row['hbp_rate']]]
        rbi_rate_pred = max(0.0, rbi_model.predict(X_pred)[0])
        row['rbi']    = int(round(row['proj_pa'] * rbi_rate_pred))

    return rows
