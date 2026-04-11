"""Generate the Designated Hitter and Defense page (docs/dh.html)."""
from pathlib import Path

import pandas as pd
from dominate.tags import *

import bat_projections as proj_module
import batting as bat_module
from data import players
from data import teams as teams_data
from constants import num_games, runs_E_new, runs_PB, mlb_E_rate, CURRENT_SEASON, LAST_COMPLETED_SEASON

from pages.page_utils import make_doc, render_table, fmt_round
from registry import REGISTRY
from dh import (
    attach_dh_model,
    RPOS, DEF_TIERS, POS_WEIGHTS, DEF_SCALE,
)


def _dh_table(rows):
    records = []
    for row in rows:
        if row.get('_dh_off') is None:
            continue
        records.append({
            'player_id': row['player_id'], 'player': '',
            'team':     row['team'],
            'pos':      row['_dh_pos'],
            'pos2':     row.get('_dh_spos', ''),
            'power':    row['power'],
            'contact':  row['contact'],
            'speed':    row['speed'],
            'fielding': row['fielding'],
            'arm':      row['arm'],
            'dh_off':   row['_dh_off'],
            'dh_def':   row['_dh_def'],
            'p_dh':     row['_dh_p'],
            'rpos_per_gb': row['_dh_rpos_per_gb'],
            'rpos_per_80g': row['_dh_rpos_per_80g'],
            'rdef_attr':   row['_dh_rdef_attr'],
            'rdef_e20':    row['_dh_rdef_e20'],
            'rdef_old':    row.get('_dh_rdef_old'),
            'rdef':        row['_dh_rdef'],
        })
    render_table(pd.DataFrame(records), depth=0)


def generate_dh():
    pi = players.player_info
    ppos_map = pi['pos1'].to_dict()  # keyed by player_id
    spos_map = pi['pos2'].to_dict()
    rows = proj_module.rows

    # Last completed season error/PB rates per player
    edf = bat_module.stats[(bat_module.stats['season'] == LAST_COMPLETED_SEASON) & (bat_module.stats['gb'] > 0)].copy()
    edf['e_rate'] = edf['e'] / edf['gb']
    edf['pb_rate'] = edf['pb'] / edf['gb']
    e_rate_map = {}
    for _, row in edf.iterrows():
        e_rate_map[row['player_id']] = {
            'e_rate':  row['e_rate'],
            'pb_rate': row['pb_rate'],
        }
    # League-average PB/GB for catchers from current season
    cat_df = edf[edf['pos1'] == 'C']
    lg_pb_rate = cat_df['pb_rate'].mean() if len(cat_df) > 0 else 0.0

    # Old model Rdef from current season
    s20 = bat_module.stats[(bat_module.stats['season'] == LAST_COMPLETED_SEASON)][['player_id', 'r_def']]
    old_rdef_map = s20.set_index('player_id')['r_def'].to_dict()
    for r in rows:
        r['_dh_rdef_old'] = old_rdef_map.get(r['player_id'])

    attach_dh_model(rows, ppos_map, spos_map, e_rate_map, lg_pb_rate)
    rows.sort(key=lambda r: r['_dh_rdef'] or 0, reverse=True)

    doc = make_doc("Positional Adjustments", depth=0)
    with doc:
        h1("Positional Adjustments")
        h2("Defense")
        with table(border=0):
            with thead():
                with tr():
                    for col in ['Pos', 'ARM', 'SPD', 'FLD']:
                        th(col)
            with tbody():
                for pos, (arm_w, spd_w, fld_w) in POS_WEIGHTS.items():
                    with tr():
                        td(pos)
                        td(f"{arm_w:.0%}")
                        td(f"{spd_w:.0%}")
                        td(f"{fld_w:.0%}")
        h2("Positional Adjustment")
        with table(border=0):
            with thead():
                with tr():
                    th('Pos')
                    th('Rpos')
            with tbody():
                for pos, rpos in sorted(RPOS.items(), key=lambda x: -x[1]):
                    with tr():
                        td(pos)
                        td(f"{rpos:+.1f}")
        h2("Defensive Tiers")
        with table(border=0):
            with thead():
                with tr():
                    for col in ['Pos', 'Range (runs/season)', 'Scale']:
                        th(col)
            with tbody():
                for pos, hi in DEF_TIERS:
                    with tr():
                        td(pos)
                        td(f"+/-{hi:.1f}")
                        td(str(DEF_SCALE[pos]))
        h2("Errors")
        with table(border=0):
            with thead():
                with tr():
                    th('Pos')
                    for e in range(16):
                        th(str(e))
            with tbody():
                for pos in ['C', 'SS', '2B', '3B', '1B', 'LF', 'CF', 'RF']:
                    with tr():
                        td(pos)
                        for e in range(16):
                            val = (e - mlb_E_rate[pos] * num_games) * runs_E_new
                            td(fmt_round(val, 1))
        h2("Players")
        _dh_table(rows)
        h2("Explanations")
        h3("OFF Score")
        p("A player's offensive score on a 0-1 scale, used to estimate how much value they bring "
          "to the lineup as a bat-only contributor. Formula: "
          "(0.45 x CON + 0.45 x POW + 0.10 x SPD) / 99. "
          "Higher contact and power increase DH candidacy; speed is included because fast players "
          "also provide value on the bases even when not fielding.")
        h3("DEF Score")
        p("A player's defensive score on a 0-1 scale, representing how much fielding value they "
          "provide to the team. Computed as a position-weighted blend of ARM, SPD, and FLD across "
          "the player's primary and secondary positions. Secondary positions apply a 20-point FLD "
          "penalty to reflect reduced effectiveness. The blend is then multiplied by a versatility "
          "factor (1 + 0.1 x sqrt(N)) where N is the number of secondary positions, so players "
          "who can cover more positions are harder to strand at DH.")
        h3("P(DH)")
        p("The probability that a given player is designated as the DH in a 9-player lineup, "
          "derived from each player's OFF/DEF ratio. Players with a high offensive score relative "
          "to their defensive score are more likely to DH. Formula: "
          "P(DH | i) = (1/9) x N x (OFF_i / DEF_i)^2 / sum_j (OFF_j / DEF_j)^2. "
          "The exponent k=2 controls spread: higher k pushes the distribution toward all-or-nothing, "
          "lower k compresses everyone toward equal probability. "
          "Values above ~30% indicate a strong DH candidate; below ~5% indicates a full-time fielder.")
        h3("Rpos")
        p("Positional adjustment in runs above average per 80-game season. Reflects the relative "
          "difficulty of each defensive position: harder positions (C, SS) receive a positive credit "
          "because teams accept worse offense to get elite defense there, while easier positions "
          "(1B, DH) receive a penalty. The values are zero-sum across a 9-player lineup. "
          "For players who split time across positions (including DH), Rpos is a weighted average "
          "of positional run values scaled by each position's probability.")
        h3("Rdef(A)")
        p("Attribute-based defensive runs above average per projected season. Measures how much "
          "better or worse a player defends relative to the league-average defender at each position "
          "they play, based purely on their ARM, SPD, and FLD ratings. "
          "Formula: sum over positions of (DEF_score - lg_mean_DEF_score) x scale x (xGB x P(pos) / 80). "
          "The league mean DEF score at each position is computed from primary-position players only. "
          "Scale factors are set per position so that the P10-P90 spread in DEF scores among "
          "primary-position players maps to the target run range shown in the Defensive Tiers table above. "
          "Secondary positions use the same scale factor and league mean as the corresponding primary position. "
          "Positive values mean above-average defense; negative values mean below-average.")
        h3("Rdef(E20)")
        p(f"Error-based defensive correction using Season {LAST_COMPLETED_SEASON} data. Compares a player's actual error "
          "rate (errors per game batted) against the MLB positional average error rate (2021-2025), "
          "weighted by their probability of playing each position. "
          "Formula: (actual_E_rate - expected_E_rate) x xGB x runs_E, "
          "where runs_E = -0.4 runs per error. "
          f"For catchers, a passed ball correction is also applied using the Season {LAST_COMPLETED_SEASON} league-average "
          "PB rate as the baseline. Positive values indicate fewer errors than positionally expected.")
        h3("Rdef")
        p("Total defensive runs above average: Rdef(A) + Rdef(E20). "
          "Rdef(A) captures range and skill from attributes; Rdef(E20) captures execution from "
          "actual error data. Together with Rpos, the full defensive contribution to WAR is Rdef + Rpos.")
    Path("docs/dh.html").write_text(str(doc))
