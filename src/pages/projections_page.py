"""Generate the Projections page (docs/projections.html)."""
from pathlib import Path

from dominate.tags import *

import projections as proj_module
import pit_projections as pit_proj_module
from data import players
from data import teams as teams_data
from util import make_doc, player_link, fmt_round
from stats_meta import BATTING_STATS

_SKILL_LABELS     = {'power': 'POW', 'contact': 'CON', 'speed': 'SPD', 'fielding': 'FLD', 'arm': 'ARM'}
_PIT_SKILL_LABELS = {'velocity': 'VEL', 'junk': 'JNK', 'accuracy': 'ACC'}


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


def _pit_qual_table(pit_rows):
    """Table for qualified pitchers: skills, season IP, blended rates, model rates."""
    with table(border=0):
        with thead():
            with tr():
                th('Player')
                for skill in pit_proj_module.SKILLS:
                    th(_PIT_SKILL_LABELS[skill])
                for s in pit_proj_module.PROJ_SEASONS:
                    th(f'S{s} IP')
                for comp in pit_proj_module.COMPONENTS:
                    th(f'{comp}/BF')
                for comp in pit_proj_module.COMPONENTS:
                    th(f'x{comp}/BF')
        with tbody():
            for row in pit_rows:
                first, last = row['first'], row['last']
                with tr():
                    td(player_link(first, last, prefix='players/'))
                    for skill in pit_proj_module.SKILLS:
                        td(row[skill])
                    for s in pit_proj_module.PROJ_SEASONS:
                        td(f"{row[f'ip_{s}']:.1f}")
                    for comp in pit_proj_module.COMPONENTS:
                        td(f"{row[comp]:.3f}")
                    for comp in pit_proj_module.COMPONENTS:
                        td(f"{row[f'x{comp}']:.3f}")


def _pit_all_table(pit_rows):
    """Table for all pitchers: skills, role, projected counting/rate stats, xWAR."""
    with table(border=0):
        with thead():
            with tr():
                for col in ['Player', 'VEL', 'JNK', 'ACC', 'Role', 'xIP',
                            'xK', 'xBB', 'xHR', 'xH',
                            'xRA9', 'xFIP', 'xWHIP', 'xK/9', 'xBB/9', 'xHR/9', 'xWAR']:
                    th(col)
        with tbody():
            for row in pit_rows:
                first, last = row['first'], row['last']
                with tr():
                    td(player_link(first, last, prefix='players/'))
                    td(row['velocity'])
                    td(row['junk'])
                    td(row['accuracy'])
                    td(row['role'])
                    td(f"{row['proj_ip']:.1f}")
                    td(row['xK'])
                    td(row['xBB'])
                    td(row['xHR'])
                    td(row['xH'])
                    td(f"{row['xRA9']:.2f}")
                    td(f"{row['xFIP']:.2f}")
                    td(f"{row['xWHIP']:.2f}")
                    td(f"{row['xK9']:.1f}")
                    td(f"{row['xBB9']:.1f}")
                    td(f"{row['xHR9']:.1f}")
                    td(f"{row['xWAR']:.1f}")


def _pit_team_summary_table(team_rows):
    """Render one row per team: summed xIP/xWAR, IP-weighted rate stats."""
    with table(border=0):
        with thead():
            with tr():
                for col in ['Team', 'xIP', 'xRA9', 'xFIP', 'xWHIP', 'xK/9', 'xWAR']:
                    th(col)
        with tbody():
            for tname, trows in team_rows:
                total_ip  = sum(r['proj_ip'] for r in trows)
                total_war = sum(r['xWAR']    for r in trows)
                if total_ip > 0:
                    w_ra9  = sum(r['xRA9']  * r['proj_ip'] for r in trows) / total_ip
                    w_fip  = sum(r['xFIP']  * r['proj_ip'] for r in trows) / total_ip
                    w_whip = sum(r['xWHIP'] * r['proj_ip'] for r in trows) / total_ip
                    w_k9   = sum(r['xK9']   * r['proj_ip'] for r in trows) / total_ip
                else:
                    w_ra9 = w_fip = w_whip = w_k9 = 0.0
                with tr():
                    td(tname)
                    td(f"{total_ip:.1f}")
                    td(f"{w_ra9:.2f}")
                    td(f"{w_fip:.2f}")
                    td(f"{w_whip:.2f}")
                    td(f"{w_k9:.1f}")
                    td(f"{total_war:.1f}")


from constants import replacement_level
_GAMES       = 80
_REPL_WINS   = replacement_level * _GAMES


def generate_projections():
    rows, metrics, pa_model, pa_model_simple = proj_module.compute_all()
    pit_rows, comp_metrics, ra9_metric, ip_models = pit_proj_module.compute_all()

    qualified = [r for r in rows if     r['qualified']]
    others    = [r for r in rows if not r['qualified']]

    # Build player -> team lookup
    pi = players.player_info.reset_index()
    player_team = {(row['first_name'], row['last_name']): row['team_name']
                   for _, row in pi.iterrows()}

    # team -> bat/pit rows
    team_proj     = {}
    pit_team_proj = {}
    for r in rows:
        tname = player_team.get((r['first'], r['last']))
        if tname and tname != 'FREE AGENT':
            team_proj.setdefault(tname, []).append(r)
    for r in pit_rows:
        tname = player_team.get((r['first'], r['last']))
        if tname and tname != 'FREE AGENT':
            pit_team_proj.setdefault(tname, []).append(r)

    # Build combined team summary with division info
    team_info = teams_data.teams.set_index('team_name')
    all_teams = sorted(set(list(team_proj.keys()) + list(pit_team_proj.keys())))
    team_summary = []
    for tname in all_teams:
        bat_war = sum(r['xWAR'] for r in team_proj.get(tname, []))
        pit_war = sum(r['xWAR'] for r in pit_team_proj.get(tname, []))
        tot_war = bat_war + pit_war
        wins    = min(_GAMES, max(0, round(_REPL_WINS + tot_war)))
        div     = team_info.loc[tname, 'division_name'] if tname in team_info.index else ''
        team_summary.append({
            'team': tname, 'division': div,
            'bat_war': bat_war, 'pit_war': pit_war, 'tot_war': tot_war,
            'wins': wins, 'losses': _GAMES - wins,
        })

    # Sort by division name, then total WAR descending
    team_summary.sort(key=lambda t: (t['division'], -t['tot_war']))

    # Also sort the per-section tables by xWAR for their own sections
    team_rows_sorted     = sorted(team_proj.items(),
                                  key=lambda kv: sum(r['xWAR'] for r in kv[1]),
                                  reverse=True)
    pit_team_rows_sorted = sorted(pit_team_proj.items(),
                                  key=lambda kv: sum(r['xWAR'] for r in kv[1]),
                                  reverse=True)

    pit_qualified = [r for r in pit_rows if r['qualified']]

    doc = make_doc("Projections", css='style.css')
    with doc:
        h1("Projections")
        p(f"Rates weighted {proj_module.WEIGHTS[20]}/{proj_module.WEIGHTS[19]}/{proj_module.WEIGHTS[18]} "
          f"(most recent to oldest). "
          f"Missing PA filled using skill-based model predictions.")

        h2("Team Projections")
        with table(border=0):
            with thead():
                with tr():
                    for col in ['Team', 'Division', 'xBAT WAR', 'xPIT WAR', 'xWAR', 'W', 'L']:
                        th(col)
            with tbody():
                for t in team_summary:
                    with tr():
                        td(t['team'])
                        td(t['division'])
                        td(fmt_round(t['bat_war'], 1, True, False))
                        td(fmt_round(t['pit_war'], 1, True, False))
                        td(fmt_round(t['tot_war'], 1, True, False))
                        td(t['wins'])
                        td(t['losses'])

        h2(f"Qualified ({len(qualified)})")
        p(f"Players with qualified PA in all of seasons "
          f"{', '.join(str(s) for s in proj_module.PROJ_SEASONS)}.")
        _proj_table(qualified, show_model=True)

        h2(f"All Players ({len(rows)})")
        _proj_table(sorted(rows, key=lambda r: r['xWAR'], reverse=True), show_season_pa=False, show_proj_pa=False, show_model=False, show_counts=True)

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

        # ── Pitcher Projections ───────────────────────────────────────────────

        h2(f"Pitcher Projections (Qualified)")
        p(f"Pitchers with qualified IP in all of seasons "
          f"{', '.join(str(s) for s in pit_proj_module.PROJ_SEASONS)}.")
        _pit_qual_table(pit_qualified)

        h2(f"All Pitchers ({len(pit_rows)})")
        _pit_all_table(sorted(pit_rows, key=lambda r: r['xWAR'], reverse=True))

        h2("Pitcher Team Projections")
        _pit_team_summary_table(pit_team_rows_sorted)

        h2("Pitcher IP/Appearance Model (IP/app ~ VEL + JNK + ACC)")
        p(f"SP: predicted IP/GS x {pit_proj_module.FULL_SEASON_APP['SP']} GS. "
          f"RP/CL: predicted IP/GR x {pit_proj_module.FULL_SEASON_APP['RP']} GR. "
          f"SP/RP: fixed at {pit_proj_module.SPRP_FIXED_IP:.0f} IP (deployment-driven role). "
          "Fit on Season 20 data.")
        with table(border=0):
            with thead():
                with tr():
                    for col in ['Role Group', 'N', 'R2', 'RMSE', 'VEL coef', 'JNK coef', 'ACC coef', 'Intercept']:
                        th(col)
            with tbody():
                for grp_name in ['SP', 'reliever']:
                    m = ip_models[grp_name]
                    with tr():
                        td(grp_name)
                        td(m['n'])
                        td(f"{m['r2']:.4f}")
                        td(f"{m['rmse']:.3f}")
                        td(f"{m['coefs']['velocity']:.4f}")
                        td(f"{m['coefs']['junk']:.4f}")
                        td(f"{m['coefs']['accuracy']:.4f}")
                        td(f"{m['intercept']:.3f}")

        h2("Pitcher Component Rate Model Fit")
        with table(border=0):
            with thead():
                with tr():
                    for col in ['Stat', 'R2', 'RMSE', 'VEL coef', 'JNK coef', 'ACC coef', 'Intercept']:
                        th(col)
            with tbody():
                for m in comp_metrics:
                    with tr():
                        td(f"{m['stat']}/BF")
                        td(f"{m['r2']:.3f}")
                        td(f"{m['rmse']:.4f}")
                        td(f"{m['coef_velocity']:.6f}")
                        td(f"{m['coef_junk']:.6f}")
                        td(f"{m['coef_accuracy']:.6f}")
                        td(f"{m['intercept']:.4f}")

        h2("Pitcher RA9 Model Fit (RA9 ~ component rates)")
        with table(border=0):
            with thead():
                with tr():
                    for col in ['R2', 'RMSE',
                                'K coef', 'BB coef', 'HBP coef', 'HR coef', 'H coef',
                                'Intercept']:
                        th(col)
            with tbody():
                with tr():
                    td(f"{ra9_metric['r2']:.4f}")
                    td(f"{ra9_metric['rmse']:.4f}")
                    for comp in pit_proj_module.COMPONENTS:
                        td(f"{ra9_metric['coefs'][comp]:.4f}")
                    td(f"{ra9_metric['intercept']:.4f}")

    Path("docs/projections.html").write_text(str(doc))
