"""Generate the Projections page (docs/projections.html)."""
from pathlib import Path

from dominate.tags import *
from dominate.util import raw

import projections as proj_module
import pit_projections as pit_proj_module
import batting as bat_module
import pitching as pit_module
from data import players
from data import teams as teams_data
import pandas as pd

from util import make_doc, player_link, fmt_round, render_table
from registry import REGISTRY

_SKILL_LABELS     = {'power': 'POW', 'contact': 'CON', 'speed': 'SPD', 'fielding': 'FLD', 'arm': 'ARM'}
_PIT_SKILL_LABELS = {'velocity': 'VEL', 'junk': 'JNK', 'accuracy': 'ACC'}


def _f(stat, val):
    m = REGISTRY[stat]
    return fmt_round(val, m['decimal_places'], m['leading_zero'], m['percentage'])


def _team_td(abbr):
    with td():
        if abbr is None:
            em('FA')
        else:
            raw(abbr)


def _proj_table(rows):
    records = []
    for row in rows:
        records.append({
            'First Name': row['first'], 'Last Name': row['last'], 'Player': '',
            'Team':    row['_team_abbr'] or 'FA',
            'power':   row['power'],   'contact': row['contact'],
            'speed':   row['speed'],   'fielding': row['fielding'], 'arm': row['arm'],
            'gb':  row['xGB'],  'pa':  row['proj_pa'],
            'hr':  row['xHR'], 'r':   row['xR'], 'rbi': row['xRBI'], 'sb': row['xSB'],
            'avg': row['xAVG'], 'obp': row['xOBP'], 'slg': row['xSLG'],
            'ops': row['xOPS'], 'wrc_plus': row['xwRC+'], 'war': row['xWAR'],
        })
    render_table(pd.DataFrame(records), prefix='players/')


def _team_summary_table(team_rows):
    """Render one row per team: summed xPA/xHR/xWAR, PA-weighted xAVG/xOPS/xwRC+."""
    with table(border=0):
        with thead():
            with tr():
                for col in ['Team', 'PA', 'AVG', 'HR', 'OPS', 'wRC+', 'WAR']:  # display headers only
                    th(col)
        with tbody():
            for tname, trows in team_rows:
                total_pa  = sum(r['proj_pa'] for r in trows)
                total_hr  = sum(r['xHR']     for r in trows)
                total_war = sum(r['xWAR']    for r in trows)
                if total_pa > 0:
                    w_avg  = sum(r['xAVG']  * r['proj_pa'] for r in trows) / total_pa
                    w_ops  = sum(r['xOPS']  * r['proj_pa'] for r in trows) / total_pa
                    w_wrc  = sum(r['xwRC+']  * r['proj_pa'] for r in trows) / total_pa
                else:
                    w_avg = w_ops = w_wrc = 0.0
                with tr():
                    td(tname)
                    td(total_pa)
                    td(_f('avg',  w_avg))
                    td(total_hr)
                    td(_f('ops',  w_ops))
                    td(_f('wrc_plus', w_wrc))
                    td(_f('war',  total_war))




def _pit_all_table(pit_rows):
    records = []
    for row in pit_rows:
        records.append({
            'First Name': row['first'], 'Last Name': row['last'], 'Player': '',
            'Team':     row['_team_abbr'] or 'FA',
            'velocity': row['velocity'], 'junk': row['junk'], 'accuracy': row['accuracy'],
            'Role':     row['role'],
            'p_ip':  row['proj_ip'],
            'p_gp': row['xGP'], 'p_w': row['xW'], 'p_l': row['xL'], 'p_sv': row['xSV'],
            'p_k': row['xK'], 'p_bb': row['xBB'], 'p_hr': row['xHR'],
            'p_era': row['xERA'], 'p_era_minus': row['xERA-'], 'p_fip': row['xFIP'],
            'p_whip': row['xWHIP'], 'p_k_pct': row['xK%'], 'p_bb_pct': row['xBB%'],
            'p_war': row['xWAR'],
        })
    render_table(pd.DataFrame(records), prefix='players/')


def _pit_team_summary_table(team_rows):
    """Render one row per team: summed xIP/xWAR, IP-weighted rate stats."""
    def _f(stat, val):
        m = REGISTRY[stat]
        return fmt_round(val, m['decimal_places'], m['leading_zero'], False)
    with table(border=0):
        with thead():
            with tr():
                for col in ['Team', 'xIP', 'xRA9', 'xERA', 'xFIP', 'xK%', 'xBB%', 'xWAR']:
                    th(col)
        with tbody():
            for tname, trows in team_rows:
                total_ip  = sum(r['proj_ip'] for r in trows)
                total_war = sum(r['xWAR']    for r in trows)
                if total_ip > 0:
                    w_ra9   = sum(r['xRA9']  * r['proj_ip'] for r in trows) / total_ip
                    w_era   = sum(r['xERA']  * r['proj_ip'] for r in trows) / total_ip
                    w_fip   = sum(r['xFIP']  * r['proj_ip'] for r in trows) / total_ip
                    w_kpct  = sum(r['xK%']   * r['proj_ip'] for r in trows) / total_ip
                    w_bbpct = sum(r['xBB%']  * r['proj_ip'] for r in trows) / total_ip
                else:
                    w_ra9 = w_era = w_fip = w_kpct = w_bbpct = 0.0
                with tr():
                    td(tname)
                    td(f"{total_ip:.1f}")
                    td(_f('p_ra9',  w_ra9))
                    td(_f('p_era',  w_era))
                    td(_f('p_fip',  w_fip))
                    td(_f('p_k_pct',  w_kpct))
                    td(_f('p_bb_pct', w_bbpct))
                    td(_f('p_war',    total_war))


def _war_delta_table(deltas):
    """Render a table of (first, last, s20_war, xwar, delta) rows."""
    m = REGISTRY['war']
    def _fw(v):
        return fmt_round(v, m['decimal_places'], m['leading_zero'], False)
    with table(border=0):
        with thead():
            with tr():
                for col in ['Player', 'S20 WAR', 'xWAR', 'Delta']:
                    th(col)
        with tbody():
            for first, last, s20_war, xwar, delta in deltas:
                with tr():
                    td(player_link(first, last, prefix='players/'))
                    td(_fw(s20_war))
                    td(_fw(xwar))
                    sign = '+' if delta >= 0 else ''
                    td(f"{sign}{_fw(delta)}")


from constants import replacement_level


def _rookie_war_list(bat_rookies, pit_rookies, ppos_map, n=10):
    """Render a combined numbered list of top n rookies (batters + pitchers) by xWAR."""
    combined = [('bat', r) for r in bat_rookies] + [('pit', r) for r in pit_rookies]
    combined.sort(key=lambda x: x[1]['xWAR'], reverse=True)
    p(f"Stat of the day: my projected top {n} rookie position players and pitchers by WAR:")
    with ol():
        for kind, r in combined[:n]:
            abbr = r['_team_abbr'] or 'FA'
            war  = _f('war', r['xWAR'])
            if kind == 'bat':
                pos  = ppos_map.get((r['first'], r['last']), '')
                line = (f"{_f('avg', r['xAVG'])} AVG, {r['xHR']} HR, "
                        f"{_f('ops', r['xOPS'])} OPS, {war} WAR")
            else:
                pos  = r['role']
                ip   = f"{r['proj_ip']:.1f}"
                if r['role'] == 'SP':
                    line = (f"{r['xW']}-{r['xL']}, {ip} IP, "
                            f"{_f('p_era', r['xERA'])} ERA, {r['xK']} K, {war} WAR")
                else:
                    line = (f"{ip} IP, {_f('p_era', r['xERA'])} ERA, "
                            f"{r['xK']} K, {r['xSV']} SV, {war} WAR")
            li(f"{r['first']} {r['last']} ({pos}, {abbr}): {line}")
_GAMES       = 80
_REPL_WINS   = replacement_level * _GAMES


def generate_projections():
    rows = proj_module.compute_all()
    pit_rows = pit_proj_module.compute_all()

    # Build player -> team lookup and team name -> abbreviation map
    pi = players.player_info.reset_index()
    player_team = {(row['first_name'], row['last_name']): row['team_name']
                   for _, row in pi.iterrows()}
    abbr_map = teams_data.teams.set_index('team_name')['abbr'] if teams_data.teams is not None else {}
    ppos_map = {(row['first_name'], row['last_name']): row['ppos'] for _, row in pi.iterrows()}
    for r in rows + pit_rows:
        r['_team_abbr'] = abbr_map.get(r['team'], r['team']) if r['team'] != 'FREE AGENT' else None

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

        # ── Rookies ───────────────────────────────────────────────────────────
        rookies     = [r for r in rows    if sum(r[f'pa_{s}'] for s in proj_module.PROJ_SEASONS)     == 0]
        pit_rookies = [r for r in pit_rows if sum(r[f'ip_{s}'] for s in pit_proj_module.PROJ_SEASONS) == 0]

        h2("Rookies")
        _rookie_war_list(rookies, pit_rookies, ppos_map)

        # ── Batting ───────────────────────────────────────────────────────────
        h2("Batting")

        h3(f"All Players ({len(rows)})")
        _proj_table(sorted(rows, key=lambda r: r['xWAR'], reverse=True))

        h3(f"Rookies ({len(rookies)})")
        _proj_table(sorted(rookies, key=lambda r: r['xWAR'], reverse=True))

        h3("Team Projections")
        _team_summary_table(team_rows_sorted)

        # WAR delta: xWAR vs Season 20 WAR
        bat_s20 = bat_module.stats[
            (bat_module.stats['Season'] == 20) & (bat_module.stats['stat_type'] == 'season')
        ].set_index(['First Name', 'Last Name'])
        bat_deltas = []
        for r in rows:
            key = (r['first'], r['last'])
            if key in bat_s20.index:
                s20_war = float(bat_s20.loc[key, 'war'])
                bat_deltas.append((r['first'], r['last'], s20_war, r['xWAR'], r['xWAR'] - s20_war))
        bat_deltas.sort(key=lambda x: x[4], reverse=True)

        h3("WAR Delta (xWAR - S20 WAR)")
        p("Bounce-back candidates (top 10):")
        _war_delta_table(bat_deltas[:10])
        p("Regression candidates (bottom 10):")
        _war_delta_table(bat_deltas[-10:][::-1])

        # ── Pitching ──────────────────────────────────────────────────────────
        h2("Pitching")

        h3(f"All Pitchers ({len(pit_rows)})")
        _pit_all_table(sorted(pit_rows, key=lambda r: r['xWAR'], reverse=True))

        h3(f"Rookies ({len(pit_rookies)})")
        _pit_all_table(sorted(pit_rookies, key=lambda r: r['xWAR'], reverse=True))

        h3("Team Projections")
        _pit_team_summary_table(pit_team_rows_sorted)

        # WAR delta: xWAR vs Season 20 WAR
        pit_s20 = pit_module.stats[
            (pit_module.stats['Season'] == 20) & (pit_module.stats['stat_type'] == 'season')
        ].set_index(['First Name', 'Last Name'])
        pit_deltas = []
        for r in pit_rows:
            key = (r['first'], r['last'])
            if key in pit_s20.index:
                s20_war = float(pit_s20.loc[key, 'p_war'])
                pit_deltas.append((r['first'], r['last'], s20_war, r['xWAR'], r['xWAR'] - s20_war))
        pit_deltas.sort(key=lambda x: x[4], reverse=True)

        h3("WAR Delta (xWAR - S20 WAR)")
        p("Bounce-back candidates (top 10):")
        _war_delta_table(pit_deltas[:10])
        p("Regression candidates (bottom 10):")
        _war_delta_table(pit_deltas[-10:][::-1])

        _methodology_section()

    Path("docs/projections.html").write_text(str(doc))


def _methodology_section():
    h2("Methodology")

    # ── General approach ──────────────────────────────────────────────────────
    h3("General Approach")
    p("""Projections use a Marcel-style weighted blend of the three most recent
      seasons (weights 5/4/3, most recent to oldest). Each player's per-PA or
      per-BF component rates are blended across seasons. When a player did not
      reach the qualification threshold in a given season, the missing data is
      filled using a skill-based regression model trained on players who did
      qualify in all three seasons. The blended rates are then used to derive
      all projected stats.""")
    p("""Playing time (xPA for batters, xIP for pitchers) is projected
      separately using a linear regression on skill ratings. The two projections
      are then combined: counting stats equal the playing-time projection
      multiplied by the blended rate.""")
    p("""WAR is projected using the same formula as actual WAR, with projected
      component inputs substituted for observed ones. A zero-sum correction
      targets the expected total league WAR split between batters and pitchers.""")

    # ── Batting ───────────────────────────────────────────────────────────────
    h3("Batting Stats")

    def _stat(name, desc):
        with p():
            b(f"{name}: ")
            span(desc)

    _stat("xPA", "Projected plate appearances. Predicted by OLS regression on "
          "POW + CON + SPD + FLD + ARM skill ratings, fit on Season 20 data. "
          "Capped at 300.")
    _stat("Component rates (1B, 2B, 3B, HR, K, BB, HBP, SB, CS per PA)",
          "Blended 5/4/3 from the player's actual per-PA rates in each projection "
          "season. For seasons where the player did not reach the PA minimum, "
          "the missing rate is filled by blending actual data with a "
          "skill-model prediction (POW, CON, SPD) trained on qualified players.")
    _stat("xAVG / xOBP / xSLG / xOPS",
          "Derived from the blended component rates using the standard formulas. "
          "No separate historical blend; these are always computed from xStats.")
    _stat("xwOBA",
          "Weighted on-base average derived from projected component rates using "
          "the league wOBA weights.")
    _stat("xBABIP",
          "Projected BABIP derived from the projected non-HR hit rate divided by "
          "the projected ball-in-play rate.")
    _stat("xOPS+",
          "Park-adjusted OPS index: 100 x ((xOBP / lg_OBP) + (xSLG / lg_SLG) - 1) / pf, "
          "where league averages are the weighted blend across projection seasons "
          "and pf = (1 + team_park_factor) / 2.")
    _stat("xwRC+",
          "Park-adjusted weighted runs created index. xRbat is computed with the "
          "player's team park factor (same formula as actual wRC+), then "
          "scaled to 100 x league average.")
    _stat("xGB",
          "Projected games batted = xPA / league-average PA-per-game (from Season 20), "
          "rounded to an integer and capped at 0-80.")
    _stat("xHR / xK / xSB / xCS",
          "Counting stats = round(xPA x blended rate).")
    _stat("xR",
          "Projected runs scored. Separated into two components: (1) xHR, which "
          "are guaranteed runs, and (2) projected non-HR on-base events "
          "(x1B + x2B + x3B + xBB + xHBP) multiplied by the league-average "
          "RC% (Run Conversion Rate = (R - HR) / (H - HR + BB + HBP)), blended "
          "5/4/3 across projection seasons. Individual RC% is not used because "
          "it reflects lineup context, not player skill.")
    _stat("xRBI",
          "Projected runs batted in. Estimated by an OLS regression: "
          "RBI/PA ~ 1B_rate + 2B_rate + 3B_rate + HR_rate + (BB+HBP)_rate, "
          "fit on all qualified batter-seasons across the full history. "
          "BB and HBP are combined because both reach base without contact and "
          "almost never produce a direct RBI. The model is applied to each "
          "player's blended component rates.")
    _stat("xWAR",
          "Projected Wins Above Replacement. Combines xRbat (from xwOBA), "
          "xRbr (baserunning, from blended SB/CS rates vs. league), xRpos "
          "(positional adjustment), xRrep (replacement credit from xPA), "
          "and a league-wide zero-sum correction. Divided by runs-per-win.")
    _stat("xRbr",
          "Projected baserunning runs above average. Derived from blended SB "
          "and CS rates vs. the league-average stolen-base run value (wSB).")

    # ── Pitching ──────────────────────────────────────────────────────────────
    h3("Pitching Stats")

    _stat("xIP",
          "Projected innings pitched. For SP and RP/CL: a linear regression "
          "predicts IP/appearance from VEL + JNK + ACC, blended 5/4/3 with "
          "actual IP/appearance history, then multiplied by a full-season "
          "appearance count (20 GS for SP, 40 GR for RP/CL). "
          "SP/RP is assigned a fixed 65 IP (deployment-driven role).")
    _stat("xGS / xGP",
          "Projected games started (SP: 20, others: 0) and games pitched "
          "(SP: 20, RP/CL/SP-RP: 40).")
    _stat("Component rates (K, BB, HBP, HR, H per BF)",
          "Blended 5/4/3 from actual per-BF rates. Missing seasons are filled "
          "by blending with skill-model predictions (VEL, JNK, ACC) trained on "
          "pitchers qualified in all three projection seasons.")
    _stat("xBF",
          "Projected batters faced = xIP x (3 / out_rate), where "
          "out_rate = 1 - H_rate - BB_rate - HBP_rate. Derived per-pitcher "
          "rather than using the league average, so strikeout pitchers are not "
          "overcounted.")
    _stat("xK / xBB / xHR / xH",
          "Counting stats = round(xBF x blended rate).")
    _stat("xRA9",
          "Projected runs allowed per 9 innings. Estimated by an OLS regression "
          "on the five component rates (K, BB, HBP, HR, H per BF), fit on all "
          "qualified pitcher-seasons across the full history.")
    _stat("xERA",
          "Projected earned run average = xRA9 x league-average ER/RA ratio. "
          "The ER/RA ratio reflects scorer discretion and defense rather than "
          "pitcher skill, so the weighted league average across projection seasons "
          "is used for all pitchers.")
    _stat("xERA-",
          "ERA index: 100 x (xERA / lg_ERA), where lg_ERA is the "
          "weighted-average league ERA across projection seasons. Lower is better.")
    _stat("xFIP",
          "Fielding-independent pitching derived from projected components: "
          "(13 x xHR + 3 x (xBB + xHBP) - 2 x xK) / xIP + cFIP.")
    _stat("xWHIP",
          "Projected walks plus hits per inning = (BB_rate + H_rate) x proj_BF_per_IP.")
    _stat("xK% / xBB%",
          "Blended K and BB rates per BF (same rates used in xBF and counting stat calculations).")
    _stat("xBABIP",
          "Projected BABIP derived from projected non-HR hit rate divided by "
          "projected ball-in-play rate.")
    _stat("xW / xL",
          "Projected wins and losses. Individual W/L history has near-zero "
          "year-over-year reproducibility (r~0.07-0.16), so xRA9 is used instead. "
          "SP W/GS and L/GS are predicted by OLS on xRA9 (R2=0.33 and 0.27). "
          "RP/CL L/GR is predicted by OLS on xRA9 (R2=0.12). "
          "RP W/GR uses league average (R2=0.04, negligible spread). "
          "Starters are assigned 0 saves.")
    _stat("xSV",
          "Projected saves. CL SV/GR is predicted by OLS on xRA9 (r=-0.46 "
          "cross-sectionally). RP/SP-RP SV/GR uses league average (role-dependent, "
          "not skill-driven). Starters are assigned 0.")
    _stat("xWAR",
          "Projected Wins Above Replacement. Combines xRAA (defense-adjusted, "
          "park-adjusted runs above average vs. role-specific replacement RA9), "
          "xRlev (leverage bonus for saves), xRrep (replacement credit from xIP), "
          "and a league-wide zero-sum correction. Divided by runs-per-win.")
