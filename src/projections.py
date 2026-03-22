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
from data import teams as teams_data
from constants import (BAT_SEASON_MIN_PA, scale_wOBA, num_games,
                       PROJ_SEASONS, PROJ_WEIGHTS as WEIGHTS, PROJ_WEIGHT_TOTAL as WEIGHT_TOTAL,
                       total_WAR, batter_share, runs_SB, runs_CS, park_factors)
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
    active = set(players.player_info.index)

    df = bat_module.stats[
        (bat_module.stats['Season'].isin(PROJ_SEASONS)) &
        (bat_module.stats['stat_type'] == 'season')
    ].copy()
    df = df[df.apply(lambda r: (r['First Name'], r['Last Name']) in active, axis=1)]

    # ── Step 1: Fit regression on players qualified in all 3 seasons ─────────

    df_qual     = df[df['pa'] >= BAT_SEASON_MIN_PA].copy()
    full_counts = df_qual.groupby(['First Name', 'Last Name'])['Season'].nunique()
    full_names  = full_counts[full_counts == len(PROJ_SEASONS)].index
    df_train    = df_qual[df_qual.set_index(['First Name', 'Last Name']).index.isin(full_names)].copy()

    for comp in COMPONENTS:
        df_train[f'{comp}_rate'] = df_train[comp] / df_train['pa']

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
    for comp in COMPONENTS:
        y            = np.array([r[comp] for r in train_rows], dtype=float)
        models[comp] = LinearRegression().fit(X_train, y)

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
            season_pa[s]   = int(season_row.iloc[0]['pa']) if not season_row.empty else 0

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
            'team':      str(pi['team_name']) if 'team_name' in pi.index else '',
            **{f'pa_{s}': season_pa[s] for s in PROJ_SEASONS},
            **{f'x{comp}': model_rates[comp] for comp in COMPONENTS},
            **proj,
        })

    rows.sort(key=lambda r: (r['last'], r['first']))
    return rows


PA_FEATURES = ['power', 'contact', 'speed', 'fielding', 'arm']
PA_MAX             = 300


def fit_pa_model():
    """Fit PA ~ POW + CON + SPD + FLD + ARM for active position players using Season 20 data.

    Returns dict with keys: model, r2, rmse, coefs, intercept, n.
    """
    s20 = bat_module.stats[
        (bat_module.stats['Season'] == 20) &
        (bat_module.stats['stat_type'] == 'season') &
        (bat_module.stats['pa'] > 0)
    ].copy()

    pi = players.player_info.reset_index()
    pi = pi[pi['ppos'] != 'P'][['first_name', 'last_name'] + PA_FEATURES]
    merged = s20.merge(pi, left_on=['First Name', 'Last Name'],
                           right_on=['first_name', 'last_name'])

    X = merged[PA_FEATURES].values.astype(float)
    y = merged['pa'].values.astype(float)

    return LinearRegression().fit(X, y)


_cache = None


def compute_all():
    """Full projection computation: blended rates + PA model + derived stats.

    Returns list of enriched row dicts (sorted by last/first).
    Results are cached after first call.
    """
    global _cache
    if _cache is not None:
        return _cache

    rows   = compute()
    pa_reg = fit_pa_model()

    for row in rows:
        row['proj_pa'] = min(PA_MAX, max(0, int(round(pa_reg.predict([[row[f] for f in PA_FEATURES]])[0]))))

        # Use final batting column names in temp dict for formula functions
        d = {
            'bb': row['bb'], 'hbp': row['hbp'],
            'b_1b': row['b_1b'], 'b_2b': row['b_2b'], 'b_3b': row['b_3b'], 'hr': row['hr'],
            'h':  row['b_1b'] + row['b_2b'] + row['b_3b'] + row['hr'],
            'ab': max(0.0, 1.0 - row['bb'] - row['hbp']),
            'sf': 0.0,
        }
        compute_tb(d); compute_avg(d); compute_obp(d); compute_slg(d)
        compute_ops(d); compute_woba(d)
        row['xAVG']  = d['avg']
        row['xOBP']  = d['obp']
        row['xSLG']  = d['slg']
        row['xOPS']  = d['ops']
        row['xwOBA'] = d['woba']
        row['xHR']   = int(round(row['proj_pa'] * row['hr']))
        row['xK']    = int(round(row['proj_pa'] * row['k']))
        row['xSB']   = int(round(row['proj_pa'] * row['sb']))
        row['xCS']   = int(round(row['proj_pa'] * row['cs']))
        bip_rate     = 1.0 - row['bb'] - row['hbp'] - row['k'] - row['hr']
        row['xBABIP'] = (row['b_1b'] + row['b_2b'] + row['b_3b']) / bip_rate if bip_rate > 0 else 0.0

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
        (bat_module.stats['pa'] > 0) &
        (bat_module.stats['gb'] > 0)
    ]
    pa_per_gb = (s20['pa'] / s20['gb']).mean()

    abbr_map = teams_data.teams.set_index('team_name')['abbr'] if teams_data.teams is not None else {}

    for row in rows:
        first, last = row['first'], row['last']
        pi = players.player_info.loc[(first, last)]
        pp = pi['ppos']
        sp = pi['spos']
        team_abbr = abbr_map.get(row['team'], '')
        pf    = (1 + park_factors.get(team_abbr, 1.0)) / 2
        xRbat = ((row['xwOBA'] - lg_wOBA_20 * pf) / scale_wOBA) * row['proj_pa']
        xGB   = row['proj_pa'] / pa_per_gb if pa_per_gb > 0 else 0.0
        row['xGB'] = max(0, min(num_games, int(round(xGB))))
        row['xOPS+'] = 100 * ((row['xOBP'] / lg_obp_20) + (row['xSLG'] / lg_slg_20) - 1) / pf if lg_obp_20 > 0 and lg_slg_20 > 0 else 100.0
        try:
            rpos_per_g = lg.pos_adjustment.loc[(pp, sp), 'r_pos']
        except KeyError:
            rpos_per_g = 0.0
        xRpos = rpos_per_g * xGB / num_games
        xRbr  = (row['sb'] * runs_SB + row['cs'] * runs_CS
                 - lg_wSB * (row['b_1b'] + row['bb'] + row['hbp'])) * row['proj_pa']
        row['xRbat']  = xRbat
        row['xRpos']  = xRpos
        row['xRbr']   = xRbr
        row['_xRAA']  = xRbat + xRbr + xRpos
        row['_xRrep'] = row['proj_pa'] * lg_rrpa_20
        if row['proj_pa'] > 0 and lg_wrcpa > 0:
            row['xwRC+'] = 100 * (xRbat / row['proj_pa'] + lg_rPA_20) / lg_wrcpa
            row['xwRC']  = (xRbat + lg_rPA_20 * row['proj_pa'])
        else:
            row['xwRC+'] = 0.0
            row['xwRC']  = 0.0

    # Rcorr: target correct total WAR using only rostered players to set the rate
    rostered       = [r for r in rows if r['team'] != 'FREE AGENT']
    total_xRAA     = sum(r['_xRAA'] for r in rostered)
    total_xRrep    = sum(r['_xRrep'] for r in rostered)
    total_xPA      = sum(r['proj_pa'] for r in rostered)
    target_xRAA    = total_WAR * batter_share * rpw_20 - total_xRrep
    corr_rate      = (target_xRAA - total_xRAA) / total_xPA if total_xPA > 0 else 0.0
    for row in rows:
        xRcorr        = corr_rate * row['proj_pa']
        xRAA          = row['_xRAA'] + xRcorr
        xRAR          = xRAA + row['_xRrep']
        row['xRcorr'] = xRcorr
        row['xRrep']  = row['_xRrep']
        row['xRAA']   = xRAA
        row['xRAR']   = xRAR
        row['xWAA']   = xRAA / rpw_20 if rpw_20 > 0 else 0.0
        row['xWAR']   = xRAR / rpw_20 if rpw_20 > 0 else 0.0

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
        (bat_module.stats['Season'].isin(PROJ_SEASONS)) &
        (bat_module.stats['stat_type'] == 'season')
    ]
    lg_rc_pct_total = 0.0
    for s in PROJ_SEASONS:
        s_df            = df_proj[df_proj['Season'] == s]
        total_non_hr_ob = (s_df['h'] - s_df['hr'] + s_df['bb'] + s_df['hbp']).sum()
        lg_rc_pct_s     = (s_df['r'] - s_df['hr']).sum() / total_non_hr_ob if total_non_hr_ob > 0 else 0.0
        lg_rc_pct_total += WEIGHTS[s] * lg_rc_pct_s
    lg_rc_pct = lg_rc_pct_total / WEIGHT_TOTAL

    for row in rows:
        proj_non_hr_ob = row['proj_pa'] * (
            row['b_1b'] + row['b_2b'] + row['b_3b'] + row['bb'] + row['hbp']
        )
        row['xR'] = int(round(row['xHR'] + proj_non_hr_ob * lg_rc_pct))

        # xRBI: OLS on blended per-PA component rates (BB+HBP combined)
        X_pred        = [[row['b_1b'], row['b_2b'], row['b_3b'], row['hr'], row['bb'] + row['hbp']]]
        rbi_rate_pred = max(0.0, rbi_model.predict(X_pred)[0])
        row['xRBI']   = int(round(row['proj_pa'] * rbi_rate_pred))

    _cache = rows
    return _cache
