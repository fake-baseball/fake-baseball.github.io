"""Compute pitcher projections using weighted recent-season component rates.

For each active pitcher, for each of the 3 projection seasons:
  - If the pitcher had qualified IP: use their actual stat/BF rate.
  - Otherwise: fill the missing BF using the model's predicted rate, then recompute.

The component model is a linear regression fit on pitchers who qualified in all 3 seasons.
The RA9 model is a linear regression fit on all individual qualified pitcher-seasons.
"""
import numpy as np
from sklearn.linear_model import LinearRegression

import pitching as pit_module
import league as lg
from data import players
from constants import (PIT_SEASON_MIN_IP,
                       PROJ_SEASONS, PROJ_WEIGHTS as WEIGHTS, PROJ_WEIGHT_TOTAL as WEIGHT_TOTAL,
                       total_WAR, batter_share)

# Component names as they appear in pitching.stats (final column names after rename)
COMPONENTS   = ['p_k', 'p_bb', 'p_hbp', 'p_hr', 'p_h']   # per-BF rates
SKILLS          = ['velocity', 'junk', 'accuracy']
IP_FEATURES     = ['velocity', 'junk', 'accuracy']
IP_MAX          = {'SP': 120, 'SP/RP': 80, 'RP': 80, 'CL': 60}
FULL_SEASON_APP  = {'SP': 20, 'RP': 40, 'CL': 40}
APP_COL          = {'SP': 'p_gs', 'RP': 'p_gr', 'CL': 'p_gr'}
SPRP_FIXED_IP    = 65.0   # SP/RP gets a fixed projection; role is deployment-driven


def compute():
    """Return (rows, comp_metrics, ra9_metric) for all active pitchers.

    rows: list of dicts sorted by last/first name.
          Keys: first, last, velocity, junk, accuracy, role, qualified,
                ip_{s} for each season,
                x{comp} (model predicted rate) for each COMPONENT,
                {comp} (blended projected rate) for each COMPONENT.
    comp_metrics: list of dicts (one per component) with r2, rmse, coef_velocity,
                  coef_junk, coef_accuracy, intercept.
    ra9_metric: dict with r2, rmse, coefs (dict by component name), intercept,
                model, lg_bf_per_ip.
    """
    active = set(players.player_info.index)

    df = pit_module.stats[
        (pit_module.stats['season'].isin(PROJ_SEASONS)) &
        (pit_module.stats['stat_type'] == 'season')
    ].copy()
    df = df[df.apply(lambda r: (r['First Name'], r['Last Name']) in active, axis=1)]

    # Filter to pitchers (ppos == 'P')
    pit_keys = {k for k in active if players.player_info.loc[k]['ppos'] == 'P'}
    df = df[df.apply(lambda r: (r['First Name'], r['Last Name']) in pit_keys, axis=1)]

    # Compute lg_bf_per_ip from this filtered data
    valid_bf_ip = df[(df['p_bf'] > 0) & (df['p_ip'] > 0)]
    lg_bf_per_ip = (valid_bf_ip['p_bf'] / valid_bf_ip['p_ip']).mean()

    # Add component rate columns
    for comp in COMPONENTS:
        df[f'{comp}_rate'] = df[comp] / df['p_bf']

    # ── Step 1: Fit component regression on pitchers qualified in all 3 seasons ──

    df_qual    = df[df['p_ip'] >= PIT_SEASON_MIN_IP].copy()
    full_counts = df_qual.groupby(['First Name', 'Last Name'])['season'].nunique()
    full_names  = full_counts[full_counts == len(PROJ_SEASONS)].index
    df_train   = df_qual[df_qual.set_index(['First Name', 'Last Name']).index.isin(full_names)].copy()

    train_rows = []
    for (first, last), group in df_train.groupby(['First Name', 'Last Name']):
        blended = {comp: sum(
            group.loc[group['season'] == s, f'{comp}_rate'].iloc[0] * WEIGHTS[s]
            for s in PROJ_SEASONS
        ) / WEIGHT_TOTAL for comp in COMPONENTS}
        pi = players.player_info.loc[(first, last)]
        train_rows.append({
            'first': first, 'last': last,
            'velocity': int(pi['velocity']), 'junk': int(pi['junk']), 'accuracy': int(pi['accuracy']),
            **blended,
        })

    X_train     = np.array([[r['velocity'], r['junk'], r['accuracy']] for r in train_rows], dtype=float)
    comp_models = {}
    for comp in COMPONENTS:
        y                 = np.array([r[comp] for r in train_rows], dtype=float)
        comp_models[comp] = LinearRegression().fit(X_train, y)

    # ── Step 2: Fit RA9 regression on all individual qualified pitcher-seasons ──

    df_ra9 = df_qual.copy()
    X_ra9  = df_ra9[[f'{comp}_rate' for comp in COMPONENTS]].values.astype(float)
    y_ra9  = df_ra9['p_ra9'].values.astype(float)

    ra9_model  = LinearRegression().fit(X_ra9, y_ra9)
    ra9_metric = {
        'model':        ra9_model,
        'lg_bf_per_ip': lg_bf_per_ip,
    }

    # ── Step 3: Project all active pitchers ───────────────────────────────────

    rows = []
    for (first, last) in pit_keys:
        pi       = players.player_info.loc[(first, last)]
        velocity = int(pi['velocity'])
        junk     = int(pi['junk'])
        accuracy = int(pi['accuracy'])
        role     = str(pi['role']) if 'role' in pi.index else 'RP'
        X_pred   = np.array([[velocity, junk, accuracy]], dtype=float)
        model_rates = {comp: comp_models[comp].predict(X_pred)[0] for comp in COMPONENTS}

        season_ip  = {}
        season_app = {}   # p_gs for SP, p_gr for relievers
        app_col    = 'p_gs' if role == 'SP' else 'p_gr'
        for s in PROJ_SEASONS:
            season_row    = df[(df['First Name'] == first) & (df['Last Name'] == last) & (df['season'] == s)]
            season_ip[s]  = float(season_row.iloc[0]['p_ip']) if not season_row.empty else 0.0
            season_app[s] = float(season_row.iloc[0][app_col])  if not season_row.empty else 0.0

        proj = {}
        for comp in COMPONENTS:
            weighted_sum = 0.0
            for s in PROJ_SEASONS:
                season_row  = df[(df['First Name'] == first) & (df['Last Name'] == last) & (df['season'] == s)]
                actual_ip   = season_ip[s]
                actual_bf   = float(season_row.iloc[0]['p_bf']) if not season_row.empty else 0.0
                actual_stat = float(season_row.iloc[0][comp]) if not season_row.empty else 0.0

                if actual_ip >= PIT_SEASON_MIN_IP:
                    rate = actual_stat / actual_bf if actual_bf > 0 else model_rates[comp]
                else:
                    min_bf      = PIT_SEASON_MIN_IP * lg_bf_per_ip
                    missing_bf  = min_bf - actual_bf
                    filled_bf   = actual_bf + missing_bf
                    rate = (actual_stat + model_rates[comp] * missing_bf) / filled_bf if filled_bf > 0 else model_rates[comp]

                weighted_sum += rate * WEIGHTS[s]
            proj[comp] = max(0.0, weighted_sum / WEIGHT_TOTAL)

        rows.append({
            'first':     first,
            'last':      last,
            'velocity':  velocity,
            'junk':      junk,
            'accuracy':  accuracy,
            'role':      role,
            'team':      str(pi['team_name']) if 'team_name' in pi.index else '',
            **{f'ip_{s}':  season_ip[s]  for s in PROJ_SEASONS},
            **{f'app_{s}': season_app[s] for s in PROJ_SEASONS},
            **{f'x{comp}': model_rates[comp] for comp in COMPONENTS},
            **proj,
        })

    rows.sort(key=lambda r: (r['last'], r['first']))
    return rows, ra9_metric


def fit_ip_model():
    """Fit IP/appearance ~ VEL + JNK + ACC for each role group using Season 20 data.

    Role groups: 'SP' (uses p_gs), 'SP/RP' (uses p_gp), 'reliever' (RP+CL, uses p_gr).
    Returns dict keyed by role group, each value a dict: model, r2, rmse, coefs, intercept, n.
    """
    s20 = pit_module.stats[
        (pit_module.stats['season'] == 20) &
        (pit_module.stats['stat_type'] == 'season') &
        (pit_module.stats['p_ip'] > 0)
    ].copy()

    pi = players.player_info.reset_index()
    pi = pi[pi['ppos'] == 'P'][['first_name', 'last_name'] + IP_FEATURES]
    merged = s20.merge(pi, left_on=['First Name', 'Last Name'],
                           right_on=['first_name', 'last_name'])

    results = {}
    for group, roles, app_col in [
        ('SP',       ['SP'],       'p_gs'),
        ('reliever', ['RP', 'CL'], 'p_gr'),
    ]:
        sub = merged[merged['role'].isin(roles) & (merged[app_col] > 0)].copy()
        sub['ip_per_app'] = sub['p_ip'] / sub[app_col]
        X = sub[IP_FEATURES].values.astype(float)
        y = sub['ip_per_app'].values.astype(float)
        results[group] = LinearRegression().fit(X, y)
    return results


_cache = None


def compute_all():
    """Full projection computation: blended rates + IP model + derived stats.

    Returns list of enriched row dicts. Results are cached after first call.
    """
    global _cache
    if _cache is not None:
        return _cache

    rows, ra9_metric = compute()
    ip_models        = fit_ip_model()

    # League context: 5/4/3 weighted averages across PROJ_SEASONS
    rpw = sum(WEIGHTS[s] * lg.season_batting.loc[s, 'r_per_w'] for s in PROJ_SEASONS) / WEIGHT_TOTAL

    lg_ra9_sp = sum(
        WEIGHTS[s] * lg.role_pitching.loc[(s, True), 'p_ra9'] for s in PROJ_SEASONS
    ) / WEIGHT_TOTAL
    lg_ra9_rp = sum(
        WEIGHTS[s] * lg.role_pitching.loc[(s, False), 'p_ra9'] for s in PROJ_SEASONS
    ) / WEIGHT_TOTAL

    # RW/IP by role (SP, SP/RP, RP); CL maps to RP
    lg_rw_ip = {}
    for role_key in ['SP', 'SP/RP', 'RP']:
        lg_rw_ip[role_key] = sum(
            WEIGHTS[s] * lg.role_innings.loc[(s, role_key), 'rw_per_ip'] for s in PROJ_SEASONS
        ) / WEIGHT_TOTAL
    lg_rw_ip['CL'] = lg_rw_ip['RP']

    cFIP     = sum(WEIGHTS[s] * lg.season_pitching.loc[s, 'p_cfip'] for s in PROJ_SEASONS) / WEIGHT_TOTAL
    lg_era   = sum(WEIGHTS[s] * lg.season_pitching.loc[s, 'p_era']  for s in PROJ_SEASONS) / WEIGHT_TOTAL
    lg_er_ra = sum(
        WEIGHTS[s] * (lg.season_pitching.loc[s, 'p_er'] / lg.season_pitching.loc[s, 'p_ra']
                      if lg.season_pitching.loc[s, 'p_ra'] > 0 else 1.0)
        for s in PROJ_SEASONS
    ) / WEIGHT_TOTAL

    lg_bf_per_ip = ra9_metric['lg_bf_per_ip']
    ra9_mdl      = ra9_metric['model']

    def _role_group(role):
        return 'SP' if role == 'SP' else 'reliever'

    for row in rows:
        role = row['role']
        if role == 'SP/RP':
            row['proj_ip'] = SPRP_FIXED_IP
        else:
            rg             = _role_group(role)
            X_ip           = [[row['velocity'], row['junk'], row['accuracy']]]
            model_ip_per_app = ip_models[rg].predict(X_ip)[0]
            apps           = FULL_SEASON_APP.get(role, 40)
            ip_cap         = IP_MAX.get(role, 80)

            # Blend actual IP/app (5/4/3) with model for missing seasons
            weighted_sum = 0.0
            for s in PROJ_SEASONS:
                actual_app = row[f'app_{s}']
                actual_ip  = row[f'ip_{s}']
                if actual_app > 0:
                    ip_per_app_s = actual_ip / actual_app
                else:
                    ip_per_app_s = model_ip_per_app
                weighted_sum += ip_per_app_s * WEIGHTS[s]
            blended_ip_per_app = weighted_sum / WEIGHT_TOTAL

            row['proj_ip'] = min(ip_cap, max(0.0, blended_ip_per_app * apps))

        # Projected counting stats (rounded to int for display)
        K_rate   = row['p_k']
        BB_rate  = row['p_bb']
        HBP_rate = row['p_hbp']
        HR_rate  = row['p_hr']
        H_rate   = row['p_h']

        out_rate = 1.0 - H_rate - BB_rate - HBP_rate
        proj_bf_per_ip = 3.0 / out_rate if out_rate > 0 else lg_bf_per_ip
        xBF = row['proj_ip'] * proj_bf_per_ip

        row['xK']   = int(round(xBF * K_rate))
        row['xBB']  = int(round(xBF * BB_rate))
        row['xHBP'] = int(round(xBF * HBP_rate))
        row['xHR']  = int(round(xBF * HR_rate))
        row['xH']   = int(round(xBF * H_rate))

        # xRA9 from RA9 model using blended rates; floor at 0
        X_ra9   = [[K_rate, BB_rate, HBP_rate, HR_rate, H_rate]]
        raw_ra9 = ra9_mdl.predict(X_ra9)[0]
        row['xRA9']  = max(0.0, raw_ra9)
        row['xERA']  = row['xRA9'] * lg_er_ra
        row['xER']   = int(round(row['xERA'] * row['proj_ip'] / 9.0)) if row['proj_ip'] > 0 else 0
        row['xERA-'] = 100 * row['xERA'] / lg_era if lg_era > 0 else 100.0

        # xFIP using exact float counts (not rounded)
        if row['proj_ip'] > 0:
            xK_f   = xBF * K_rate
            xBB_f  = xBF * BB_rate
            xHBP_f = xBF * HBP_rate
            xHR_f  = xBF * HR_rate
            row['xFIP'] = (13 * xHR_f + 3 * (xBB_f + xHBP_f) - 2 * xK_f) / row['proj_ip'] + cFIP
        else:
            row['xFIP'] = 0.0

        row['xWHIP'] = (BB_rate + H_rate) * proj_bf_per_ip
        row['xK%']   = K_rate
        row['xBB%']  = BB_rate
        bip_rate     = 1.0 - K_rate - BB_rate - HBP_rate - HR_rate
        row['xBABIP'] = (H_rate - HR_rate) / bip_rate if bip_rate > 0 else 0.0

        # xRAA (pre-correction) and xRlev
        is_starter    = (role == 'SP')
        lg_ra9_role   = lg_ra9_sp if is_starter else lg_ra9_rp
        rw_ip_role    = lg_rw_ip.get(role, lg_rw_ip['RP'])
        row['_xRAA']  = (lg_ra9_role - row['xRA9']) / 9 * row['proj_ip']
        row['_xRrep'] = row['proj_ip'] * rw_ip_role * rpw

        row['_rw_ip_role'] = rw_ip_role

    # Rcorr: target correct total WAR using only rostered players to set the rate
    rostered       = [r for r in rows if r['team'] != 'FREE AGENT']
    total_xRAA     = sum(r['_xRAA'] for r in rostered)
    total_xRrep    = sum(r['_xRrep'] for r in rostered)
    total_xIP      = sum(r['proj_ip'] for r in rostered)
    target_xRAA    = total_WAR * (1 - batter_share) * rpw - total_xRrep
    corr_rate      = (target_xRAA - total_xRAA) / total_xIP if total_xIP > 0 else 0.0
    for row in rows:
        xRcorr        = corr_rate * row['proj_ip']
        row['_xRcorr'] = xRcorr
        row['_xRAA_corr'] = row['_xRAA'] + xRcorr   # RAA before Rlev

    # ── W, L, SV models fit on all historical seasons ─────────────────────────
    # W/L individual history has near-zero year-over-year reproducibility (r~0.07-0.16).
    # xRA9 is a far better predictor. Models:
    #   SP  W/GS  ~ xRA9  (R2=0.33)
    #   SP  L/GS  ~ xRA9  (R2=0.27)
    #   RP  L/GR  ~ xRA9  (R2=0.12)
    #   RP  W/GR  -> league average (R2=0.04, negligible spread)
    #   CL  SV/GR ~ xRA9  (r=-0.46)
    #   RP  SV/GR -> league average (role-dependent, not skill)
    df_all = pit_module.stats[pit_module.stats['stat_type'] == 'season'].copy()

    sp_hist = df_all[(df_all['role'] == 'SP') & (df_all['p_gs'] >= 5)].copy()
    sp_hist['W_rate'] = sp_hist['p_w'] / sp_hist['p_gs']
    sp_hist['L_rate'] = sp_hist['p_l'] / sp_hist['p_gs']
    sp_w_model = LinearRegression().fit(sp_hist[['p_ra9']].values, sp_hist['W_rate'].values)
    sp_l_model = LinearRegression().fit(sp_hist[['p_ra9']].values, sp_hist['L_rate'].values)

    rp_hist = df_all[(df_all['role'].isin(['RP', 'CL', 'SP/RP'])) & (df_all['p_gr'] >= 10)].copy()
    rp_hist['L_rate'] = rp_hist['p_l'] / rp_hist['p_gr']
    rp_l_model = LinearRegression().fit(rp_hist[['p_ra9']].values, rp_hist['L_rate'].values)

    cl_hist = df_all[(df_all['role'] == 'CL') & (df_all['p_gr'] >= 10)].copy()
    cl_hist['SV_rate'] = cl_hist['p_sv'] / cl_hist['p_gr']
    cl_sv_model = LinearRegression().fit(cl_hist[['p_ra9']].values, cl_hist['SV_rate'].values)

    # League averages for the flat cases (RP W/GR, RP SV/GR)
    rp_all = df_all[df_all['role'].isin(['RP', 'CL', 'SP/RP'])]
    lg_rp_w_rate  = rp_all['p_w'].sum() / rp_all['p_gr'].sum() if rp_all['p_gr'].sum() > 0 else 0.0
    lg_rp_sv_rate = (df_all[df_all['role'].isin(['RP', 'SP/RP'])]['p_sv'].sum() /
                     df_all[df_all['role'].isin(['RP', 'SP/RP'])]['p_gr'].sum()
                     if df_all[df_all['role'].isin(['RP', 'SP/RP'])]['p_gr'].sum() > 0 else 0.0)

    for row in rows:
        role = row['role']
        apps = FULL_SEASON_APP.get(role, 40)
        xra9 = [[row['xRA9']]]

        if role == 'SP':
            xW  = max(0.0, sp_w_model.predict(xra9)[0]) * apps
            xL  = max(0.0, sp_l_model.predict(xra9)[0]) * apps
            xSV = 0
        else:
            xW  = lg_rp_w_rate * apps
            xL  = max(0.0, rp_l_model.predict(xra9)[0]) * apps
            if role == 'CL':
                xSV = max(0.0, cl_sv_model.predict(xra9)[0]) * apps
            else:
                xSV = lg_rp_sv_rate * apps

        row['xW']  = int(round(xW))
        row['xL']  = int(round(xL))
        row['xSV'] = int(round(xSV))
        row['xGS'] = apps if role == 'SP' else 0
        row['xGP'] = apps

    # ── Final pass: Rlev and all exposed WAR components ───────────────────────
    # Precompute blended R_sv / R_no_SV by role group
    lev_rates = {}
    for lev_role in ('SP', 'RP', 'SP/RP'):
        r_sv_total = r_no_sv_total = 0.0
        for s in PROJ_SEASONS:
            try:
                lev = lg.role_leverage.loc[(s, lev_role)]
                r_sv_total    += WEIGHTS[s] * lev['r_sv']
                r_no_sv_total += WEIGHTS[s] * lev['r_no_sv']
            except KeyError:
                pass
        lev_rates[lev_role] = (r_sv_total / WEIGHT_TOTAL, r_no_sv_total / WEIGHT_TOTAL)
    lev_rates['CL'] = lev_rates['RP']

    for row in rows:
        role       = row['role']
        is_starter = (role == 'SP')
        r_sv, r_no_sv = lev_rates.get(role, lev_rates['RP'])
        xSV_f = row['xSV']
        xGR_f = row['xGP'] if not is_starter else 0
        xRlev    = xSV_f * r_sv + (xGR_f - xSV_f) * r_no_sv
        xRAA     = row['_xRAA_corr']
        xRAAlev  = xRAA + xRlev
        xRrep    = row['_xRrep']
        xRAR     = xRAAlev + xRrep

        # BAA and OBPA from projected rates
        H_rate   = row['p_h']
        BB_rate  = row['p_bb']
        HBP_rate = row['p_hbp']
        HR_rate  = row['p_hr']
        out_rate = 1.0 - H_rate - BB_rate - HBP_rate
        bf_per_ip = 3.0 / out_rate if out_rate > 0 else 4.0
        xBF      = row['proj_ip'] * bf_per_ip
        xBAA     = (H_rate * xBF) / (xBF - BB_rate * xBF - HBP_rate * xBF) if (xBF * (1 - BB_rate - HBP_rate)) > 0 else 0.0
        xOBPA    = H_rate + BB_rate + HBP_rate

        row['xRlev']   = xRlev
        row['xRcorr']  = row['_xRcorr']
        row['xRdef']   = 0.0
        row['xRrep']   = xRrep
        row['xRAA']    = xRAA
        row['xRAAlev'] = xRAAlev
        row['xWAA']    = xRAAlev / rpw if rpw > 0 else 0.0
        row['xRAR']    = xRAR
        row['xWAR']    = xRAR / rpw if rpw > 0 else 0.0
        row['xBAA']    = xBAA
        row['xOBPA']   = xOBPA

    _cache = rows
    return _cache
