"""Compute batter projections using weighted recent-season component rates.

For each active player, for each of the 3 projection seasons:
  - If the player had qualified PA: use their actual stat/PA rate.
  - Otherwise: fill the missing PA using the model's predicted rate, then recompute.

The model is a linear regression fit on players who qualified in all 3 seasons.
"""
import numpy as np
from sklearn.linear_model import LinearRegression

import batting as bat_module
import league as lg
from data import players
from constants import (BAT_SEASON_MIN_PA, scale_wOBA, num_games,
                       PROJ_SEASONS, PROJ_WEIGHTS as WEIGHTS, PROJ_WEIGHT_TOTAL as WEIGHT_TOTAL,
                       total_WAR, batter_share, runs_SB, runs_CS)
from formulas import compute_TB, compute_AVG, compute_OBP, compute_SLG, compute_OPS, compute_wOBA
from util import fit_metrics
COMPONENTS   = ['BB', 'HBP', '1B', '2B', '3B', 'HR', 'K', 'SB', 'CS']
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
    active = set(players.player_info.index)

    df = bat_module.stats[
        (bat_module.stats['Season'].isin(PROJ_SEASONS)) &
        (bat_module.stats['stat_type'] == 'season')
    ].copy()
    df = df[df.apply(lambda r: (r['First Name'], r['Last Name']) in active, axis=1)]

    # ── Step 1: Fit regression on players qualified in all 3 seasons ─────────

    df_qual     = df[df['PA'] >= BAT_SEASON_MIN_PA].copy()
    full_counts = df_qual.groupby(['First Name', 'Last Name'])['Season'].nunique()
    full_names  = full_counts[full_counts == len(PROJ_SEASONS)].index
    df_train    = df_qual[df_qual.set_index(['First Name', 'Last Name']).index.isin(full_names)].copy()

    for comp in COMPONENTS:
        df_train[f'{comp}_rate'] = df_train[comp] / df_train['PA']

    train_rows = []
    for (first, last), group in df_train.groupby(['First Name', 'Last Name']):
        proj = {comp: sum(
            group.loc[group['Season'] == s, f'{comp}_rate'].iloc[0] * WEIGHTS[s]
            for s in PROJ_SEASONS
        ) / WEIGHT_TOTAL for comp in COMPONENTS}
        pi = players.player_info.loc[(first, last)]
        train_rows.append({
            'first': first, 'last': last,
            'power': int(pi['power']), 'contact': int(pi['contact']), 'speed': int(pi['speed']),
            **proj,
        })

    X_train = np.array([[r['power'], r['contact'], r['speed']] for r in train_rows], dtype=float)
    models  = {}
    metrics = []
    for comp in COMPONENTS:
        y     = np.array([r[comp] for r in train_rows], dtype=float)
        model = LinearRegression().fit(X_train, y)
        models[comp] = model
        fm = fit_metrics(y, model.predict(X_train))
        metrics.append({
            'stat':         comp,
            **fm,
            'coef_power':   model.coef_[0],
            'coef_contact': model.coef_[1],
            'coef_speed':   model.coef_[2],
            'intercept':    model.intercept_,
        })

    # ── Step 2: Project all active players ────────────────────────────────────

    rows = []
    for (first, last) in active:
        if players.player_info.loc[(first, last)]['ppos'] == 'P':
            continue
        pi       = players.player_info.loc[(first, last)]
        power    = int(pi['power'])
        contact  = int(pi['contact'])
        speed    = int(pi['speed'])
        fielding = int(pi['fielding'])
        arm      = int(pi['arm'])
        X_pred   = np.array([[power, contact, speed]], dtype=float)
        model_rates = {comp: models[comp].predict(X_pred)[0] for comp in COMPONENTS}

        season_pa = {}
        for s in PROJ_SEASONS:
            season_row     = df[(df['First Name'] == first) & (df['Last Name'] == last) & (df['Season'] == s)]
            season_pa[s]   = int(season_row.iloc[0]['PA']) if not season_row.empty else 0

        proj = {}
        for comp in COMPONENTS:
            weighted_sum = 0.0
            for s in PROJ_SEASONS:
                season_row  = df[(df['First Name'] == first) & (df['Last Name'] == last) & (df['Season'] == s)]
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
            'first':     first,
            'last':      last,
            'power':     power,
            'contact':   contact,
            'speed':     speed,
            'fielding':  fielding,
            'arm':       arm,
            'qualified': (first, last) in full_names,
            'team':      str(pi['team_name']) if 'team_name' in pi.index else '',
            **{f'pa_{s}': season_pa[s] for s in PROJ_SEASONS},
            **{f'x{comp}': model_rates[comp] for comp in COMPONENTS},
            **proj,
        })

    rows.sort(key=lambda r: (r['last'], r['first']))
    return rows, metrics


PA_FEATURES        = ['power', 'contact', 'speed', 'fielding', 'arm']
PA_FEATURES_SIMPLE = ['power', 'contact', 'speed']
PA_MAX             = 300


def fit_pa_model():
    """Fit PA ~ POW + CON + SPD + FLD + ARM for active position players using Season 20 data.

    Returns dict with keys: model, r2, rmse, coefs, intercept, n.
    """
    s20 = bat_module.stats[
        (bat_module.stats['Season'] == 20) &
        (bat_module.stats['stat_type'] == 'season') &
        (bat_module.stats['PA'] > 0)
    ].copy()

    pi = players.player_info.reset_index()
    pi = pi[pi['ppos'] != 'P'][['first_name', 'last_name'] + PA_FEATURES]
    merged = s20.merge(pi, left_on=['First Name', 'Last Name'],
                           right_on=['first_name', 'last_name'])

    X = merged[PA_FEATURES].values.astype(float)
    y = merged['PA'].values.astype(float)

    model = LinearRegression().fit(X, y)
    fm    = fit_metrics(y, model.predict(X))
    return {
        'model':     model,
        **fm,
        'coefs':     dict(zip(PA_FEATURES, model.coef_)),
        'intercept': model.intercept_,
        'n':         len(merged),
    }


def fit_pa_model_simple():
    """Fit PA ~ (POW + CON + SPD) / 3 for active position players using Season 20 data.

    Returns dict with keys: model, r2, rmse, slope, intercept, n.
    """
    s20 = bat_module.stats[
        (bat_module.stats['Season'] == 20) &
        (bat_module.stats['stat_type'] == 'season') &
        (bat_module.stats['PA'] > 0)
    ].copy()

    pi = players.player_info.reset_index()
    pi = pi[pi['ppos'] != 'P'][['first_name', 'last_name'] + PA_FEATURES_SIMPLE]
    merged = s20.merge(pi, left_on=['First Name', 'Last Name'],
                           right_on=['first_name', 'last_name'])
    merged['skill_score'] = merged[PA_FEATURES_SIMPLE].mean(axis=1)

    X = merged[['skill_score']].values.astype(float)
    y = merged['PA'].values.astype(float)

    model = LinearRegression().fit(X, y)
    fm    = fit_metrics(y, model.predict(X))
    return {
        'model':     model,
        **fm,
        'slope':     model.coef_[0],
        'intercept': model.intercept_,
        'n':         len(merged),
    }


_cache = None


def compute_all():
    """Full projection computation: blended rates + PA model + derived stats.

    Returns list of enriched row dicts (sorted by last/first).
    Also returns metrics from compute() as second element of tuple.
    Results are cached after first call.
    """
    global _cache
    if _cache is not None:
        return _cache

    rows, metrics = compute()
    pa_model        = fit_pa_model()
    pa_model_simple = fit_pa_model_simple()
    pa_reg          = pa_model['model']
    pa_reg_simple   = pa_model_simple['model']

    for row in rows:
        X        = [[row[f] for f in PA_FEATURES]]
        X_simple = [[(row['power'] + row['contact'] + row['speed']) / 3]]
        row['proj_pa']        = min(PA_MAX, max(0, int(round(pa_reg.predict(X)[0]))))
        row['proj_pa_simple'] = min(PA_MAX, max(0, int(round(pa_reg_simple.predict(X_simple)[0]))))

        d = {
            'BB': row['BB'], 'HBP': row['HBP'],
            '1B': row['1B'], '2B': row['2B'], '3B': row['3B'], 'HR': row['HR'],
            'H':  row['1B'] + row['2B'] + row['3B'] + row['HR'],
            'AB': max(0.0, 1.0 - row['BB'] - row['HBP']),
            'SF': 0.0,
        }
        compute_TB(d); compute_AVG(d); compute_OBP(d); compute_SLG(d)
        compute_OPS(d); compute_wOBA(d)
        row['xAVG']  = d['AVG']
        row['xOBP']  = d['OBP']
        row['xSLG']  = d['SLG']
        row['xOPS']  = d['OPS']
        row['xwOBA'] = d['wOBA']
        row['xHR']   = int(round(row['proj_pa'] * row['HR']))
        row['xK']    = int(round(row['proj_pa'] * row['K']))
        row['xSB']   = int(round(row['proj_pa'] * row['SB']))
        row['xCS']   = int(round(row['proj_pa'] * row['CS']))
        bip_rate     = 1.0 - row['BB'] - row['HBP'] - row['K'] - row['HR']
        row['xBABIP'] = (row['1B'] + row['2B'] + row['3B']) / bip_rate if bip_rate > 0 else 0.0

    # League context: 5/4/3 weighted average across seasons 18-20
    def _lg_avg(col):
        return sum(WEIGHTS[s] * lg.season_batting.loc[s, col] for s in PROJ_SEASONS) / WEIGHT_TOTAL

    lg_wOBA_20 = _lg_avg('wOBA')
    rpw_20     = _lg_avg('R/W')
    lg_rPA_20  = _lg_avg('R/PA')
    lg_wrcpa   = _lg_avg('wRC') / _lg_avg('PA')  # used as wRC/PA in wRC+ formula
    lg_pa_20   = _lg_avg('PA')
    lg_rrpa_20 = _lg_avg('RR/PA')
    lg_wSB     = _lg_avg('lg_wSB')
    lg_obp_20  = _lg_avg('OBP')
    lg_slg_20  = _lg_avg('SLG')

    s20 = bat_module.stats[
        (bat_module.stats['Season'] == 20) &
        (bat_module.stats['stat_type'] == 'season') &
        (bat_module.stats['PA'] > 0) &
        (bat_module.stats['GB'] > 0)
    ]
    pa_per_gb = (s20['PA'] / s20['GB']).mean()

    for row in rows:
        first, last = row['first'], row['last']
        pi = players.player_info.loc[(first, last)]
        pp = pi['ppos']
        sp = pi['spos']
        xRbat = ((row['xwOBA'] - lg_wOBA_20) / scale_wOBA) * row['proj_pa']
        xGB   = row['proj_pa'] / pa_per_gb if pa_per_gb > 0 else 0.0
        row['xGB'] = max(0, min(num_games, int(round(xGB))))
        row['xOPS+'] = 100 * ((row['xOBP'] / lg_obp_20) + (row['xSLG'] / lg_slg_20) - 1) if lg_obp_20 > 0 and lg_slg_20 > 0 else 100.0
        try:
            rpos_per_g = lg.pos_adjustment.loc[(pp, sp), 'Rpos']
        except KeyError:
            rpos_per_g = 0.0
        xRpos = rpos_per_g * xGB / num_games
        xRbr  = (row['SB'] * runs_SB + row['CS'] * runs_CS
                 - lg_wSB * (row['1B'] + row['BB'] + row['HBP'])) * row['proj_pa']
        row['xRbr']   = xRbr
        row['_xRAA']  = xRbat + xRbr + xRpos
        row['_xRrep'] = row['proj_pa'] * lg_rrpa_20
        if row['proj_pa'] > 0 and lg_wrcpa > 0:
            row['xwRC+'] = 100 * (xRbat / row['proj_pa'] + lg_rPA_20) / lg_wrcpa
        else:
            row['xwRC+'] = 0.0

    # Rcorr: target correct total WAR using only rostered players to set the rate
    rostered       = [r for r in rows if r['team'] != 'FREE AGENT']
    total_xRAA     = sum(r['_xRAA'] for r in rostered)
    total_xRrep    = sum(r['_xRrep'] for r in rostered)
    total_xPA      = sum(r['proj_pa'] for r in rostered)
    target_xRAA    = total_WAR * batter_share * rpw_20 - total_xRrep
    corr_rate      = (target_xRAA - total_xRAA) / total_xPA if total_xPA > 0 else 0.0
    for row in rows:
        xRcorr      = corr_rate * row['proj_pa']
        xRAR        = row['_xRAA'] + xRcorr + row['_xRrep']
        row['xWAR'] = xRAR / rpw_20 if rpw_20 > 0 else 0.0

    # ── Fit OLS: RBI/PA ~ 1B_rate + 2B_rate + 3B_rate + HR_rate + (BB+HBP)_rate
    # BB and HBP are combined: both put the batter on base with no contact and
    # almost never directly drive in a run, so they share a single coefficient.
    RBI_FEATURES = ['1B', '2B', '3B', 'HR', 'BB_HBP']
    df_all = bat_module.stats[
        (bat_module.stats['stat_type'] == 'season') &
        (bat_module.stats['PA'] >= BAT_SEASON_MIN_PA)
    ].copy()
    df_all['BB_HBP'] = df_all['BB'] + df_all['HBP']
    for feat in RBI_FEATURES:
        df_all[f'{feat}_rate'] = df_all[feat] / df_all['PA']
    X_rbi     = df_all[[f'{feat}_rate' for feat in RBI_FEATURES]].values.astype(float)
    y_rbi     = (df_all['RBI'] / df_all['PA']).values.astype(float)
    rbi_model = LinearRegression().fit(X_rbi, y_rbi)
    rbi_fm    = fit_metrics(y_rbi, rbi_model.predict(X_rbi))
    rbi_metric = {
        **rbi_fm,
        'coefs': dict(zip(RBI_FEATURES, rbi_model.coef_)),
        'intercept': rbi_model.intercept_,
        'model': rbi_model,
    }

    # ── Projected R via blended RC% × projected non-HR OB events ─────────────
    df_proj = bat_module.stats[
        (bat_module.stats['Season'].isin(PROJ_SEASONS)) &
        (bat_module.stats['stat_type'] == 'season')
    ]
    lg_rc_pct = {}   # RC% = (R - HR) / (H - HR + BB + HBP)
    for s in PROJ_SEASONS:
        s_df            = df_proj[df_proj['Season'] == s]
        total_non_hr_ob = (s_df['H'] - s_df['HR'] + s_df['BB'] + s_df['HBP']).sum()
        lg_rc_pct[s]    = (s_df['R'] - s_df['HR']).sum() / total_non_hr_ob if total_non_hr_ob > 0 else 0.0

    for row in rows:
        first, last = row['first'], row['last']
        rc_total = 0.0
        for s in PROJ_SEASONS:
            sr = df_proj[
                (df_proj['First Name'] == first) &
                (df_proj['Last Name']  == last) &
                (df_proj['Season']     == s)
            ]
            pa_s = float(sr.iloc[0]['PA']) if not sr.empty else 0.0
            if pa_s > 0:
                non_hr_ob_s = (float(sr.iloc[0]['H'])  - float(sr.iloc[0]['HR'])
                               + float(sr.iloc[0]['BB']) + float(sr.iloc[0]['HBP']))
                rc_pct_s    = ((float(sr.iloc[0]['R']) - float(sr.iloc[0]['HR']))
                               / non_hr_ob_s if non_hr_ob_s > 0 else lg_rc_pct[s])
            else:
                rc_pct_s = lg_rc_pct[s]
            rc_total += WEIGHTS[s] * rc_pct_s

        blended_rc_pct = rc_total / WEIGHT_TOTAL
        proj_non_hr_ob = row['proj_pa'] * (
            row['1B'] + row['2B'] + row['3B'] + row['BB'] + row['HBP']
        )
        row['xR'] = int(round(row['xHR'] + proj_non_hr_ob * blended_rc_pct))

        # xRBI: OLS on blended per-PA component rates (BB+HBP combined)
        X_pred        = [[row['1B'], row['2B'], row['3B'], row['HR'], row['BB'] + row['HBP']]]
        rbi_rate_pred = max(0.0, rbi_model.predict(X_pred)[0])
        row['xRBI']   = int(round(row['proj_pa'] * rbi_rate_pred))

    _cache = (rows, metrics, pa_model, pa_model_simple, rbi_metric)
    return _cache
