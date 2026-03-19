"""Generate the Projections page (docs/projections.html)."""
from pathlib import Path

from dominate.tags import *

import projections as proj_module
from data import players
from data import teams as teams_data
from util import make_doc, player_link, fmt_round
from stats_meta import BATTING_STATS

_SKILL_LABELS = {'power': 'POW', 'contact': 'CON', 'speed': 'SPD', 'fielding': 'FLD', 'arm': 'ARM'}


def _proj_table(rows, show_model=False, show_proj_pa=False, show_season_pa=True, show_counts=False):
    with table(border=0):
        with thead():
            with tr():
                th('Player')
                for skill in proj_module.SKILLS:
                    th(_SKILL_LABELS[skill])
                if show_season_pa:
                    for s in proj_module.PROJ_SEASONS:
                        th(f'S{s} PA')
                if show_proj_pa:
                    th('xPA3')
                    th('xPA5')
                if not show_counts:
                    for comp in proj_module.COMPONENTS:
                        th(f'{comp}/PA')
                if show_model:
                    for comp in proj_module.COMPONENTS:
                        th(f'x{comp}/PA')
                if show_counts:
                    th('xPA5')
                    for comp in proj_module.COMPONENTS:
                        th(f'x{comp}')
                    for stat in ['xAVG', 'xOBP', 'xSLG', 'xOPS', 'xwRC+', 'xwOBA']:
                        th(stat)
                    th('xWAR')
        with tbody():
            for row in rows:
                first, last = row['first'], row['last']
                with tr():
                    td(player_link(first, last, prefix='players/'))
                    for skill in proj_module.SKILLS:
                        td(row[skill])
                    if show_season_pa:
                        for s in proj_module.PROJ_SEASONS:
                            td(row[f'pa_{s}'])
                    if show_proj_pa:
                        td(row['proj_pa_simple'])
                        td(row['proj_pa'])
                    if not show_counts:
                        for comp in proj_module.COMPONENTS:
                            td(f"{row[comp]:.3f}")
                    if show_model:
                        for comp in proj_module.COMPONENTS:
                            td(f"{row[f'x{comp}']:.3f}")
                    if show_counts:
                        td(row['proj_pa'])
                        for comp in proj_module.COMPONENTS:
                            td(int(round(row['proj_pa'] * row[comp])))
                        for stat, key in [('xAVG', 'xAVG'), ('xOBP', 'xOBP'), ('xSLG', 'xSLG'), ('xOPS', 'xOPS'), ('xwRC+', 'xwRC+'), ('xwOBA', 'xwOBA')]:
                            m = BATTING_STATS[stat.lstrip('x')]
                            td(fmt_round(row[key], m['decimal_places'], m['leading_zero'], m['percentage']))
                        td(fmt_round(row['xWAR'], 1, True, False))


def _team_summary_table(team_rows):
    """Render one row per team: summed xPA/xHR/xWAR, PA-weighted xAVG/xOPS/xwRC+."""
    m_avg = BATTING_STATS['AVG']
    m_ops = BATTING_STATS['OPS']
    with table(border=0):
        with thead():
            with tr():
                for col in ['Team', 'xPA', 'xAVG', 'xHR', 'xOPS', 'xwRC+', 'xWAR']:
                    th(col)
        with tbody():
            for tname, trows in team_rows:
                total_pa  = sum(r['proj_pa'] for r in trows)
                total_hr  = sum(r['xHR']     for r in trows)
                total_war = sum(r['xWAR']    for r in trows)
                if total_pa > 0:
                    w_avg  = sum(r['xAVG']  * r['proj_pa'] for r in trows) / total_pa
                    w_ops  = sum(r['xOPS']  * r['proj_pa'] for r in trows) / total_pa
                    w_wrc  = sum(r['xwRC+'] * r['proj_pa'] for r in trows) / total_pa
                else:
                    w_avg = w_ops = w_wrc = 0.0
                with tr():
                    td(tname)
                    td(total_pa)
                    td(fmt_round(w_avg,  m_avg['decimal_places'], m_avg['leading_zero'], False))
                    td(total_hr)
                    td(fmt_round(w_ops,  m_ops['decimal_places'], m_ops['leading_zero'], False))
                    td(int(round(w_wrc)))
                    td(fmt_round(total_war, 1, True, False))


def generate_projections():
    rows, metrics, pa_model, pa_model_simple = proj_module.compute_all()

    qualified = [r for r in rows if     r['qualified']]
    others    = [r for r in rows if not r['qualified']]

    # Build team -> proj rows mapping (position players only, already filtered)
    pi = players.player_info.reset_index()
    player_team = {(row['first_name'], row['last_name']): row['team_name']
                   for _, row in pi.iterrows()}
    team_proj = {}
    for r in rows:
        tname = player_team.get((r['first'], r['last']))
        if tname and tname != 'FREE AGENT':
            team_proj.setdefault(tname, []).append(r)
    # Sort teams by xWAR descending
    team_rows_sorted = sorted(team_proj.items(),
                              key=lambda kv: sum(r['xWAR'] for r in kv[1]),
                              reverse=True)

    doc = make_doc("Projections", css='style.css')
    with doc:
        h1("Projections")
        p(f"Rates weighted {proj_module.WEIGHTS[20]}/{proj_module.WEIGHTS[19]}/{proj_module.WEIGHTS[18]} "
          f"(most recent to oldest). "
          f"Missing PA filled using skill-based model predictions.")

        h2("Team Projections")
        _team_summary_table(team_rows_sorted)

        h2(f"Qualified ({len(qualified)})")
        p(f"Players with qualified PA in all of seasons "
          f"{', '.join(str(s) for s in proj_module.PROJ_SEASONS)}.")
        _proj_table(qualified, show_model=True)

        h2(f"All Players ({len(rows)})")
        _proj_table(rows, show_season_pa=False, show_proj_pa=False, show_model=False, show_counts=True)

        h2("PA Model (PA ~ POW + CON + SPD + FLD + ARM)")
        p(f"Fit on {pa_model['n']} active position players using Season 20 data.")
        with table(border=0):
            with thead():
                with tr():
                    for col in ['R2', 'RMSE'] + [f'{f.upper()} coef' for f in proj_module.PA_FEATURES] + ['Intercept']:
                        th(col)
            with tbody():
                with tr():
                    td(f"{pa_model['r2']:.4f}")
                    td(f"{pa_model['rmse']:.2f}")
                    for f in proj_module.PA_FEATURES:
                        td(f"{pa_model['coefs'][f]:.4f}")
                    td(f"{pa_model['intercept']:.2f}")

        h2("Component Rate Model Fit")
        with table(border=0):
            with thead():
                with tr():
                    for col in ['Stat', 'R2', 'RMSE', 'POW coef', 'CON coef', 'SPD coef', 'Intercept']:
                        th(col)
            with tbody():
                for m in metrics:
                    with tr():
                        td(f"{m['stat']}/PA")
                        td(f"{m['r2']:.3f}")
                        td(f"{m['rmse']:.4f}")
                        td(f"{m['coef_power']:.6f}")
                        td(f"{m['coef_contact']:.6f}")
                        td(f"{m['coef_speed']:.6f}")
                        td(f"{m['intercept']:.4f}")

    Path("docs/projections.html").write_text(str(doc))
