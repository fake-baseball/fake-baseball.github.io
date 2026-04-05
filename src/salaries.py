"""Salary model fitting: skills regression and WAR-based valuation."""
import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import PolynomialFeatures

from constants import LAST_COMPLETED_SEASON

RIDGE_ALPHAS = [0.01, 0.1, 1, 10, 100, 1000, 10000]
BAT_SKILLS   = ['power', 'contact', 'speed', 'fielding', 'arm']
PIT_SKILLS   = ['velocity', 'junk', 'accuracy']


def _r2(y, preds):
    ss_res = np.sum((y - preds) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0


def _build_war_map(stats_df, war_col='war'):
    """Return {(first, last): WAR} from last completed season rows."""
    s = stats_df[
        (stats_df['season'] == LAST_COMPLETED_SEASON) & (stats_df['stat_type'] == 'season')
    ]
    return {
        (row['first_name'], row['last_name']): float(row[war_col])
        for _, row in s.iterrows()
    }


def _fit_skills(pi_group, skills, war_map, cat_cols=None):
    """Fit Ridge salary ~ degree-2 interaction polynomial of skills + optional one-hot categoricals."""
    data = []
    for (first, last), row in pi_group.iterrows():
        try:
            sal = float(row['salary'])
        except (ValueError, TypeError):
            continue
        war = war_map.get((first, last))
        entry = {
            'first': first, 'last': last,
            'sal':   sal,
            'X':     [int(row[s]) for s in skills],
            'war':   war,
            'dol_per_war': sal / war if war and war > 0 else None,
        }
        if cat_cols:
            entry['cats'] = {col: row[col] for col in cat_cols}
        data.append(entry)
    if not data:
        return None, []
    X_raw = np.array([d['X'] for d in data], dtype=float)
    y = np.array([d['sal'] for d in data], dtype=float)
    poly = PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)
    X_poly = poly.fit_transform(X_raw)
    feat_names = list(poly.get_feature_names_out(skills))
    if cat_cols:
        for col in cat_cols:
            values = [d['cats'][col] for d in data]
            categories = sorted(set(values))
            for cat in categories:
                dummies = np.array([1.0 if v == cat else 0.0 for v in values])
                X_poly = np.column_stack([X_poly, dummies])
                feat_names.append(f"{col}={cat}")
    model = RidgeCV(alphas=RIDGE_ALPHAS, cv=5).fit(X_poly, np.log(y))
    log_resid = np.log(y) - model.predict(X_poly)
    smearing = np.mean(np.exp(log_resid))
    preds = smearing * np.exp(model.predict(X_poly))
    r2 = _r2(y, preds)
    for d, pred in zip(data, preds):
        d['pred_skills'] = pred
        d['diff_skills'] = d['sal'] - pred
    return (model, r2, len(data), feat_names, smearing), data


def _fit_war(data, war_key='proj_war'):
    """Fit log-linear Ridge: log(salary) ~ WAR."""
    valid = [d for d in data if d.get(war_key) is not None]
    if len(valid) < 2:
        return None
    X = np.array([[d[war_key]] for d in valid], dtype=float)
    y = np.array([d['sal'] for d in valid], dtype=float)
    model = RidgeCV(alphas=RIDGE_ALPHAS, cv=5).fit(X, np.log(y))
    log_resid = np.log(y) - model.predict(X)
    smearing = np.mean(np.exp(log_resid))
    preds = smearing * np.exp(model.predict(X))
    r2 = _r2(y, preds)
    for d, pred in zip(valid, preds):
        d['pred_war'] = pred
    return model, r2, len(valid), smearing


def _fit_war_combined(bat_rows, pit_rows):
    """Fit log-linear Ridge: log(salary) ~ proj_WAR + is_pitcher on all players combined."""
    valid = []
    for d in bat_rows:
        if d.get('proj_war') is not None:
            valid.append({'war': d['proj_war'], 'is_pit': 0.0, 'sal': d['sal']})
    for d in pit_rows:
        if d.get('proj_war') is not None:
            valid.append({'war': d['proj_war'], 'is_pit': 1.0, 'sal': d['sal']})
    if len(valid) < 3:
        return None
    X = np.array([[d['war'], d['is_pit']] for d in valid], dtype=float)
    y = np.array([d['sal'] for d in valid], dtype=float)
    model = RidgeCV(alphas=RIDGE_ALPHAS, cv=5).fit(X, np.log(y))
    log_resid = np.log(y) - model.predict(X)
    smearing = np.mean(np.exp(log_resid))
    preds = smearing * np.exp(model.predict(X))
    r2 = _r2(y, preds)
    return model, r2, len(valid), smearing


def _fit_war_linear(data, war_key='proj_war'):
    """Fit linear Ridge: salary ~ WAR (no log transform)."""
    valid = [d for d in data if d.get(war_key) is not None]
    if len(valid) < 2:
        return None
    X = np.array([[d[war_key]] for d in valid], dtype=float)
    y = np.array([d['sal'] for d in valid], dtype=float)
    model = RidgeCV(alphas=RIDGE_ALPHAS, cv=5).fit(X, y)
    preds = model.predict(X)
    r2 = _r2(y, preds)
    return model, r2, len(valid)


def compute_salary_models(pi, bat_stats, pit_stats, proj_rows, pit_proj_rows):
    """Run full salary model pipeline.

    Returns (bat_model_info, bat_rows, pit_model_info, pit_rows,
             bat_war_model_info, pit_war_model_info,
             combined_war_model_info, bat_war_linear_info, pit_war_linear_info).
    """
    bat_pi = pi[pi['ppos'] != 'P']
    pit_pi = pi[pi['ppos'] == 'P']

    bat_war_map = _build_war_map(bat_stats, war_col='war')
    pit_war_map = _build_war_map(pit_stats, war_col='p_war')

    bat_model_info, bat_rows = _fit_skills(bat_pi, BAT_SKILLS, bat_war_map)
    pit_model_info, pit_rows = _fit_skills(pit_pi, PIT_SKILLS, pit_war_map, cat_cols=['role'])

    bat_proj_war = {r['first'] + '\x00' + r['last']: r['war']   for r in proj_rows}
    pit_proj_war = {r['first'] + '\x00' + r['last']: r['p_war'] for r in pit_proj_rows}
    for d in bat_rows:
        d['proj_war'] = bat_proj_war.get(d['first'] + '\x00' + d['last'])
    for d in pit_rows:
        d['proj_war'] = pit_proj_war.get(d['first'] + '\x00' + d['last'])

    bat_war_model_info     = _fit_war(bat_rows, war_key='proj_war')
    pit_war_model_info     = _fit_war(pit_rows, war_key='proj_war')
    combined_war_model_info = _fit_war_combined(bat_rows, pit_rows)
    bat_war_linear_info    = _fit_war_linear(bat_rows, war_key='proj_war')
    pit_war_linear_info    = _fit_war_linear(pit_rows, war_key='proj_war')

    return (bat_model_info, bat_rows, pit_model_info, pit_rows,
            bat_war_model_info, pit_war_model_info,
            combined_war_model_info, bat_war_linear_info, pit_war_linear_info)
