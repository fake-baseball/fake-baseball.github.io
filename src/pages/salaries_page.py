"""Generate the Salaries page (docs/salaries.html)."""
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import PolynomialFeatures
from dominate.tags import *

RIDGE_ALPHAS = [0.01, 0.1, 1, 10, 100, 1000, 10000]

from constants import CURRENT_SEASON, LAST_COMPLETED_SEASON
from util import make_doc, convert_name
from data import players
from data import teams as teams_data
import batting as bat_module
import pitching as pit_module

BAT_SKILLS  = ['power', 'contact', 'speed', 'fielding', 'arm']
PIT_SKILLS  = ['velocity', 'junk', 'accuracy']
BAT_LABELS  = {'power': 'POW', 'contact': 'CON', 'speed': 'SPD', 'fielding': 'FLD', 'arm': 'ARM'}
PIT_LABELS  = {'velocity': 'VEL', 'junk': 'JNK', 'accuracy': 'ACC'}


def _parse_salary(val):
    """Parse '$1.3m' -> 1.3 (millions)."""
    s = str(val).strip().lower().lstrip('$').rstrip('m')
    return float(s)


def _fmt_sal(millions):
    return f"${millions:.1f}m"


def _r2(y, preds):
    ss_res = np.sum((y - preds) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0


def _fit_skills(pi_group, skills, war_map, cat_cols=None):
    """Fit Ridge salary ~ degree-2 interaction polynomial of skills + optional one-hot categoricals."""
    data = []
    for (first, last), row in pi_group.iterrows():
        try:
            sal = _parse_salary(row['salary'])
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
    """Fit log-linear Ridge: log(salary) ~ WAR. Predictions back-transformed with exp()."""
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


def _coef_table(model_info, skills, labels):
    model, r2, n, feat_names, smearing = model_info
    p(f"R\u00b2 = {r2:.3f}, n = {n}, alpha = {model.alpha_:.1f} (log-linear model)")
    with table(border=0):
        with thead():
            with tr():
                th('Feature')
                th('Coefficient ($m)')
        with tbody():
            with tr():
                td('Intercept')
                td(f"{model.intercept_:+.4f}")
            for fname, coef in zip(feat_names, model.coef_):
                # Replace raw skill names with short labels in interaction terms
                display = fname
                for skill, label in labels.items():
                    display = display.replace(skill, label)
                with tr():
                    td(display)
                    td(f"{coef:+.6f}")


def _war_coef_table(war_model_info):
    model, r2, n, smearing = war_model_info
    p(f"R\u00b2 = {r2:.3f}, n = {n} (all players with projections, log-linear model)")
    with table(border=0):
        with thead():
            with tr():
                th('Feature')
                th('Coefficient ($m)')
        with tbody():
            with tr():
                td('Intercept')
                td(f"{model.intercept_:+.3f}")
            with tr():
                td('WAR')
                td(f"{model.coef_[0]:+.3f}")


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


def _combined_war_coef_table(model_info):
    model, r2, n, smearing = model_info
    p(f"R\u00b2 = {r2:.3f}, n = {n} (all players with projected WAR > 0, log-linear model)")
    p(f"is_pitcher coefficient: {model.coef_[1]:+.3f} "
      f"(multiplicative factor: {np.exp(model.coef_[1]):.3f}x)")
    with table(border=0):
        with thead():
            with tr():
                th('Feature')
                th('Coefficient (log-space)')
        with tbody():
            with tr():
                td('Intercept')
                td(f"{model.intercept_:+.4f}")
            with tr():
                td('WAR')
                td(f"{model.coef_[0]:+.4f}")
            with tr():
                td('is_pitcher')
                td(f"{model.coef_[1]:+.4f}")


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


def _combined_war_conversion_table(model_info, bat_linear_info, pit_linear_info):
    model, r2, n, smearing = model_info
    war_values = [w / 2 for w in range(-4, 11)]  # -2.0 to 5.0 step 0.5
    a = model.intercept_
    b_war = model.coef_[0]
    b_pit = model.coef_[1]
    bat_lin = bat_linear_info[0] if bat_linear_info else None
    pit_lin = pit_linear_info[0] if pit_linear_info else None
    with table(border=0):
        with thead():
            with tr():
                th('WAR')
                th('Pos (log)')
                th('Pit (log)')
                th('Pos (linear)')
                th('Pit (linear)')
        with tbody():
            for w in war_values:
                pred_bat_log = smearing * np.exp(a + b_war * w)
                pred_pit_log = smearing * np.exp(a + b_war * w + b_pit)
                pred_bat_lin = _fmt_sal(bat_lin.intercept_ + bat_lin.coef_[0] * w) if bat_lin else '-'
                pred_pit_lin = _fmt_sal(pit_lin.intercept_ + pit_lin.coef_[0] * w) if pit_lin else '-'
                with tr():
                    td(f"{w:+.1f}")
                    td(_fmt_sal(pred_bat_log))
                    td(_fmt_sal(pred_pit_log))
                    td(pred_bat_lin)
                    td(pred_pit_lin)


def _team_salary_table(abbr_map, bat_rows, pit_rows, bat_war_model_info, pit_war_model_info):
    pi = players.player_info

    # Actual salaries per team
    totals = {}  # team_name -> {'bat': float, 'pit': float}
    for (first, last), row in pi.iterrows():
        try:
            sal = _parse_salary(row['salary'])
        except (ValueError, TypeError):
            continue
        team = row['team_name']
        if team == 'FREE AGENT':
            continue
        if team not in totals:
            totals[team] = {'bat': 0.0, 'pit': 0.0,
                            'bat_xwar': 0.0, 'bat_pred': 0.0,
                            'pit_xwar': 0.0, 'pit_pred': 0.0}
        if row['ppos'] == 'P':
            totals[team]['pit'] += sal
        else:
            totals[team]['bat'] += sal

    # Accumulate projected WAR and model-predicted salary per team
    def _accumulate(rows, war_model_info, sal_key, xwar_key, pred_key):
        if not war_model_info:
            return
        m        = war_model_info[0]
        smearing = war_model_info[3]
        for d in rows:
            team = pi.loc[(d['first'], d['last']), 'team_name'] if (d['first'], d['last']) in pi.index else None
            if not team or team == 'FREE AGENT' or team not in totals:
                continue
            xwar = d.get('proj_war')
            if xwar is not None:
                totals[team][xwar_key] += xwar
                totals[team][pred_key] += smearing * np.exp(m.intercept_ + m.coef_[0] * xwar)

    _accumulate(bat_rows, bat_war_model_info, 'bat', 'bat_xwar', 'bat_pred')
    _accumulate(pit_rows, pit_war_model_info, 'pit', 'pit_xwar', 'pit_pred')

    league = {k: sum(v[k] for v in totals.values())
              for k in ('bat', 'pit', 'bat_xwar', 'bat_pred', 'pit_xwar', 'pit_pred')}

    # Compute all diff values to normalize color scale
    def _raw_diff(pred, actual):
        return pred - actual if pred > 0.0 else None

    all_diffs = []
    for v in totals.values():
        for pred_k, sal_k in (('bat_pred', 'bat'), ('pit_pred', 'pit')):
            d = _raw_diff(v[pred_k], v[sal_k])
            if d is not None:
                all_diffs.append(abs(d))
    max_mag = max(all_diffs) if all_diffs else 1.0

    def _diff_td(pred, actual, bold=False):
        diff = _raw_diff(pred, actual)
        if diff is None:
            td(b('-') if bold else '-')
            return
        intensity = min(abs(diff) / max_mag, 1.0)
        if diff >= 0:
            r = int(255 * (1 - intensity * 0.6))
            g = 255
            c = int(255 * (1 - intensity * 0.6))
        else:
            r = 255
            g = int(255 * (1 - intensity * 0.6))
            c = int(255 * (1 - intensity * 0.6))
        style = f"background-color: rgb({r},{g},{c})"
        text = _fmt_diff(diff)
        td(b(text) if bold else text, style=style)

    league_total_val = league['bat'] + league['pit']
    league_pct = league['bat'] / league_total_val * 100 if league_total_val > 0 else 0.0

    with table(border=0):
        with thead():
            with tr():
                th('Team')
                th('Pos$')
                th('Pos xWAR')
                th('Pos Diff')
                th('Pit$')
                th('Pit xWAR')
                th('Pit Diff')
                th('Total')
                th('Pos%')
        with tbody():
            for team_name, v in sorted(totals.items(), key=lambda x: x[0]):
                abbr = abbr_map[team_name]
                total = v['bat'] + v['pit']
                pct = v['bat'] / total * 100 if total > 0 else 0.0
                with tr():
                    td(abbr)
                    td(_fmt_sal(v['bat']))
                    td(f"{v['bat_xwar']:.1f}")
                    _diff_td(v['bat_pred'], v['bat'])
                    td(_fmt_sal(v['pit']))
                    td(f"{v['pit_xwar']:.1f}")
                    _diff_td(v['pit_pred'], v['pit'])
                    td(_fmt_sal(total))
                    td(f"{pct:.1f}%")
            with tr():
                td(b('Total'))
                td(b(_fmt_sal(league['bat'])))
                td(b(f"{league['bat_xwar']:.1f}"))
                _diff_td(league['bat_pred'], league['bat'], bold=True)
                td(b(_fmt_sal(league['pit'])))
                td(b(f"{league['pit_xwar']:.1f}"))
                _diff_td(league['pit_pred'], league['pit'], bold=True)
                td(b(_fmt_sal(league_total_val)))
                td(b(f"{league_pct:.1f}%"))


def _war_conversion_table(war_model_info):
    model, r2, n, smearing = war_model_info
    war_values = [w / 2 for w in range(-4, 11)]  # -2.0 to 5.0 step 0.5
    with table(border=0):
        with thead():
            with tr():
                th('WAR')
                th('Pred Salary')
        with tbody():
            for w in war_values:
                pred = smearing * np.exp(model.intercept_ + model.coef_[0] * w)
                with tr():
                    td(f"{w:+.1f}")
                    td(_fmt_sal(pred))


def _fmt_diff(diff):
    return f"{'+' if diff >= 0 else ''}{diff:.1f}m"


def _player_table(rows, skills, labels, abbr_map, war_model_info, war_linear_info=None):
    skill_headers = [labels[s] for s in skills]
    war_model    = war_model_info[0] if war_model_info else None
    war_smearing = war_model_info[3] if war_model_info else 1.0
    lin_model    = war_linear_info[0] if war_linear_info else None
    with table(border=0):
        with thead():
            with tr():
                for col in (['Player', 'Team'] + skill_headers +
                            ['Pred (Skills)', 'Pred (WAR)', 'Pred (Proj WAR)', 'Pred (Proj WAR, Lin)',
                             'Salary', 'Diff (Skills)', 'Diff (Proj WAR)', 'Diff (Proj WAR, Lin)']):
                    th(col)
        with tbody():
            for d in rows:
                first, last = d['first'], d['last']
                if war_model and d.get('war') is not None and d['war'] > 0:
                    pred_war_str = _fmt_sal(war_smearing * np.exp(war_model.intercept_ + war_model.coef_[0] * d['war']))
                else:
                    pred_war_str = '-'
                diff_skills = _fmt_diff(d['pred_skills'] - d['sal'])
                if war_model and d.get('proj_war') is not None:
                    pred_proj = war_smearing * np.exp(war_model.intercept_ + war_model.coef_[0] * d['proj_war'])
                    pred_proj_str = _fmt_sal(pred_proj)
                    diff_proj = _fmt_diff(pred_proj - d['sal'])
                else:
                    pred_proj_str = '-'
                    diff_proj = '-'
                if lin_model and d.get('proj_war') is not None:
                    pred_proj_lin = lin_model.intercept_ + lin_model.coef_[0] * d['proj_war']
                    pred_proj_lin_str = _fmt_sal(pred_proj_lin)
                    diff_proj_lin = _fmt_diff(pred_proj_lin - d['sal'])
                else:
                    pred_proj_lin_str = '-'
                    diff_proj_lin = '-'
                with tr():
                    td(a(f"{first} {last}", href=f"players/{convert_name(first, last)}.html"))
                    team = players.player_info.loc[(first, last), 'team_name']
                    td(abbr_map.get(team, team))
                    for val in d['X']:
                        td(val)
                    td(_fmt_sal(d['pred_skills']))
                    td(pred_war_str)
                    td(pred_proj_str)
                    td(pred_proj_lin_str)
                    td(_fmt_sal(d['sal']))
                    td(diff_skills)
                    td(diff_proj)
                    td(diff_proj_lin)


def _build_war_map(stats_df, war_col='WAR'):
    """Return {(first, last): WAR} from current season rows."""
    s20 = stats_df[
        (stats_df['season'] == LAST_COMPLETED_SEASON) & (stats_df['stat_type'] == 'season')
    ]
    return {
        (row['First Name'], row['Last Name']): float(row[war_col])
        for _, row in s20.iterrows()
    }


def _methodology_section():
    h2("Methodology")

    h3("Overview")
    p("This page uses statistical models to assess salary efficiency in two independent ways: "
      "how well a player's salary reflects their skills, and how well it reflects their projected "
      "on-field value (WAR). Contracts in this league are assigned based on skills, so the skills "
      "model is the primary market-efficiency benchmark. The WAR models add a performance-based "
      "lens that rewards realized and projected production regardless of raw skill ratings.")

    h3("Skills Model")
    p("A log-linear Ridge regression is fit separately for position players and pitchers:")
    with ul():
        li("Position players: five skills (POW, CON, SPD, FLD, ARM) expanded to 15 features "
           "via degree-2 interaction terms (e.g. POW x CON). This captures synergies between "
           "skills -- a player who excels in two dimensions may command a larger premium than "
           "the sum of each skill individually.")
        li("Pitchers: three skills (VEL, JNK, ACC) expanded to 6 features via degree-2 "
           "interaction terms, plus four role dummy variables (SP, SP/RP, RP, CL) added as "
           "linear features. Role captures the structural salary difference between starters "
           "and relievers independent of raw stuff.")
        li("The target variable is log(salary) rather than salary itself. This reflects the "
           "multiplicative nature of the market: each skill point multiplies salary by a "
           "constant factor rather than adding a fixed dollar amount. Stars command "
           "disproportionately higher salaries than the linear relationship would suggest.")
        li("Ridge regression with regularization strength (alpha) chosen by 5-fold "
           "cross-validation from the grid [0.01, 0.1, 1, 10, 100, 1000, 10000]. Ridge "
           "shrinks large coefficients toward zero, reducing overfitting on the interaction terms.")
        li("Predictions are back-transformed from log-space using exp(), then multiplied by "
           "Duan's smearing factor -- the mean of exp(residuals) from the training fit. This "
           "corrects a systematic downward bias that arises when exponentiating a log-space "
           "prediction: exp(E[log y]) is the median, not the mean, of a skewed distribution.")

    h3("WAR Models (Separate)")
    p("Two separate log-linear Ridge models are fit -- one for position players, one for pitchers "
      "-- each regressing log(salary) on projected WAR:")
    with ul():
        li("Projected WAR (xWAR from the Marcel-style projection system) is used as the "
           f"predictor rather than Season {LAST_COMPLETED_SEASON} actual WAR. Contracts are forward-looking bets on "
           "future performance, so the projected distribution better matches the salary-setting "
           "context than realized outcomes.")
        li("Only players with projected WAR > 0 are included in the fit. Replacement-level "
           "and below players are excluded because their salaries are set by roster minimums "
           "rather than market forces, which would distort the slope estimate.")
        li("The log-linear form captures the superstar premium: each additional WAR multiplies "
           "predicted salary by e^b rather than adding a fixed amount. A 5-WAR player is worth "
           "exponentially more than a 1-WAR player, reflecting both the scarcity of elite "
           "performance and the convex value of wins near playoff thresholds.")
        li("Duan's smearing correction is applied on back-transformation, as in the skills model.")
        li(f"Pred (WAR) in the player table applies the fitted model to the player's Season {LAST_COMPLETED_SEASON} "
           "actual WAR -- a backward-looking view. Pred (Proj WAR) applies the same model to "
           "their projected WAR -- a forward-looking view.")

    h3("Combined WAR Model")
    p("A single model is fit on all players (batters and pitchers combined) with log(salary) "
      "regressed on projected WAR and an is_pitcher indicator variable. The coefficient on "
      "is_pitcher answers the question: controlling for WAR, are pitchers paid more or less "
      "than position players? The coefficient is reported in log-space; its exponential gives "
      "the multiplicative salary factor for pitchers relative to position players at the same WAR. "
      "A value below 1.0 means pitchers are underpaid per WAR; above 1.0 means they are overpaid. "
      "The real-world benchmark for the position player WAR share is 13/21 (~61.9%), matching the "
      "conventional wisdom that position players account for roughly 62% of team WAR.")

    h3("Team Salary Allocation")
    p("The team table aggregates actual salaries and projected WAR by team and position group. "
      "The Diff columns compare the sum of WAR-model predicted salaries (for players with "
      "positive projected WAR) against actual salaries for that group. A positive diff means "
      "the team is underpaying relative to what their projected production is worth at market "
      "rates; a negative diff means they are overpaying. Color intensity scales to the largest "
      "absolute diff in the table. Players without projections (rookies, free agents) are "
      "excluded from the diff calculation but included in the actual salary totals.")

    h3("Reading the Player Tables")
    with ul():
        li("Pred (Skills): the salary the skills model says this player should earn, given "
           "their skill ratings. Positive Diff (Skills) means the player is underpaid relative "
           "to what the market model implies for their skills; negative means overpaid.")
        li(f"Pred (WAR): the salary implied by the player's Season {LAST_COMPLETED_SEASON} actual WAR. This is a "
           "backward-looking measure -- useful for evaluating whether last season's performance "
           "was fairly compensated.")
        li("Pred (Proj WAR): the salary implied by the player's projected WAR. This is the "
           "most forward-looking and actionable measure -- it flags players whose contracts "
           "look like good or bad value going into the coming season.")
        li("Diff (Proj WAR): positive = the player is projected to outperform their contract "
           "(buy low candidate); negative = they are projected to underperform it (potential "
           "salary trap). Because the WAR model was fit on projected WAR directly, the "
           "league-wide sum of diffs should be near zero after the smearing correction.")
        li("The WAR conversion tables translate hypothetical WAR values to predicted salary "
           "under each model, giving an intuitive sense of the implied market rate at each "
           "performance level.")


def generate_salaries():
    import projections as proj_module
    import pit_projections as pit_proj_module

    pi       = players.player_info
    bat_pi   = pi[pi['ppos'] != 'P']
    pit_pi   = pi[pi['ppos'] == 'P']
    abbr_map = teams_data.teams.set_index('team_name')['abbr'].to_dict() if teams_data.teams is not None else {}

    bat_war_map = _build_war_map(bat_module.stats, war_col='war')
    pit_war_map = _build_war_map(pit_module.stats, war_col='p_war')

    bat_model_info, bat_rows = _fit_skills(bat_pi, BAT_SKILLS, bat_war_map)
    pit_model_info, pit_rows = _fit_skills(pit_pi, PIT_SKILLS, pit_war_map, cat_cols=['role'])

    # Attach projected WAR to each row
    bat_proj_war = {r['first'] + '\x00' + r['last']: r['xWAR'] for r in proj_module.compute_all()}
    pit_proj_war = {r['first'] + '\x00' + r['last']: r['xWAR'] for r in pit_proj_module.compute_all()}
    for d in bat_rows:
        d['proj_war'] = bat_proj_war.get(d['first'] + '\x00' + d['last'])
    for d in pit_rows:
        d['proj_war'] = pit_proj_war.get(d['first'] + '\x00' + d['last'])

    # Fit WAR model on projected WAR -> salary (forward-looking, matches how contracts are set)
    bat_war_model_info = _fit_war(bat_rows, war_key='proj_war')
    pit_war_model_info = _fit_war(pit_rows, war_key='proj_war')
    combined_war_model_info = _fit_war_combined(bat_rows, pit_rows)
    bat_war_linear_info = _fit_war_linear(bat_rows, war_key='proj_war')
    pit_war_linear_info = _fit_war_linear(pit_rows, war_key='proj_war')

    bat_rows.sort(key=lambda d: -d['sal'])
    pit_rows.sort(key=lambda d: -d['sal'])

    doc = make_doc("Salaries", css='style.css')
    with doc:
        h1("Salaries")

        h2("Model Coefficients")

        h3("Position Players — Skills Model")
        if bat_model_info:
            _coef_table(bat_model_info, BAT_SKILLS, BAT_LABELS)

        h3("Position Players — WAR Model")
        if bat_war_model_info:
            _war_coef_table(bat_war_model_info)
            _war_conversion_table(bat_war_model_info)

        h3("Pitchers — Skills Model")
        if pit_model_info:
            _coef_table(pit_model_info, PIT_SKILLS, PIT_LABELS)

        h3("Pitchers — WAR Model")
        if pit_war_model_info:
            _war_coef_table(pit_war_model_info)
            _war_conversion_table(pit_war_model_info)

        h3("Combined WAR Model (Pos Players vs Pitchers)")
        if combined_war_model_info:
            _combined_war_coef_table(combined_war_model_info)
            _combined_war_conversion_table(combined_war_model_info, bat_war_linear_info, pit_war_linear_info)

        h2("Team Salary Allocation")
        _team_salary_table(abbr_map, bat_rows, pit_rows, bat_war_model_info, pit_war_model_info)

        h2("Position Players")
        if bat_rows:
            _player_table(bat_rows, BAT_SKILLS, BAT_LABELS, abbr_map, bat_war_model_info, bat_war_linear_info)

        h2("Pitchers")
        if pit_rows:
            _player_table(pit_rows, PIT_SKILLS, PIT_LABELS, abbr_map, pit_war_model_info, pit_war_linear_info)

        _methodology_section()

    Path("docs/salaries.html").write_text(str(doc))
