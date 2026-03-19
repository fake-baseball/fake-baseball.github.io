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
from constants import BAT_SEASON_MIN_PA, scale_wOBA, num_games
from formulas import compute_TB, compute_AVG, compute_OBP, compute_SLG, compute_OPS, compute_wOBA

PROJ_SEASONS = [18, 19, 20]
WEIGHTS      = {18: 3, 19: 4, 20: 5}
WEIGHT_TOTAL = sum(WEIGHTS.values())
COMPONENTS   = ['BB', 'HBP', '1B', '2B', '3B', 'HR']
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
        preds     = model.predict(X_train)
        residuals = y - preds
        rmse      = np.sqrt(np.mean(residuals ** 2))
        ss_res    = np.sum(residuals ** 2)
        ss_tot    = np.sum((y - y.mean()) ** 2)
        metrics.append({
            'stat':         comp,
            'r2':           1 - ss_res / ss_tot if ss_tot > 0 else 0.0,
            'rmse':         rmse,
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

    model     = LinearRegression().fit(X, y)
    preds     = model.predict(X)
    residuals = y - preds
    rmse      = np.sqrt(np.mean(residuals ** 2))
    ss_res    = np.sum(residuals ** 2)
    ss_tot    = np.sum((y - y.mean()) ** 2)

    return {
        'model':     model,
        'r2':        1 - ss_res / ss_tot,
        'rmse':      rmse,
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

    model     = LinearRegression().fit(X, y)
    preds     = model.predict(X)
    residuals = y - preds
    rmse      = np.sqrt(np.mean(residuals ** 2))
    ss_res    = np.sum(residuals ** 2)
    ss_tot    = np.sum((y - y.mean()) ** 2)

    return {
        'model':     model,
        'r2':        1 - ss_res / ss_tot,
        'rmse':      rmse,
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

    # League context: 5/4/3 weighted average across seasons 18-20
    _lw = {18: 3, 19: 4, 20: 5}
    _lt = sum(_lw.values())
    def _lg_avg(col):
        return sum(_lw[s] * lg.season_batting.loc[s, col] for s in PROJ_SEASONS) / _lt

    lg_wOBA_20 = _lg_avg('wOBA')
    rpw_20     = _lg_avg('R/W')
    lg_rPA_20  = _lg_avg('R/PA')
    lg_wrcpa   = _lg_avg('wRC') / _lg_avg('PA')  # used as wRC/PA in wRC+ formula
    lg_pa_20   = _lg_avg('PA')
    lg_rrpa_20 = _lg_avg('RR/PA')

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
        try:
            rpos_per_g = lg.pos_adjustment.loc[(pp, sp), 'Rpos']
        except KeyError:
            rpos_per_g = 0.0
        xRpos = rpos_per_g * xGB / num_games
        xRrep = row['proj_pa'] * lg_rrpa_20
        xRAA  = xRbat + xRpos
        xRAR  = xRAA + xRrep
        row['xWAR'] = xRAR / rpw_20 if rpw_20 > 0 else 0.0
        if row['proj_pa'] > 0 and lg_wrcpa > 0:
            row['xwRC+'] = 100 * (xRbat / row['proj_pa'] + lg_rPA_20) / lg_wrcpa
        else:
            row['xwRC+'] = 0.0

    _cache = (rows, metrics, pa_model, pa_model_simple)
    return _cache
