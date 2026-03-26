"""Generate the Designated Hitter and Defense page (docs/dh.html)."""
from pathlib import Path

import pandas as pd
from dominate.tags import *

import projections as proj_module
import batting as bat_module
from data import players
from data import teams as teams_data
from constants import num_games, runs_E_new, runs_PB, mlb_E_rate

from util import make_doc, render_table, fmt_round
from registry import REGISTRY

# Positional adjustments (runs/80-game season), rounded to nearest 1.5
_RPOS = {
    'C':   +7.0,
    'SS':  +4.0,
    '2B':  +2.5,
    'CF':  +2.5,
    '3B':  +1.0,
    'LF':  -2.0,
    'RF':  -2.0,
    '1B':  -5.0,
    'DH':  -8.0,
}

# Per-position defensive run ranges (runs/80-game season)
# Calibrated from MLB UZR/DRS literature, adjusted for BFBL context (no framing)
_DEF_TIERS = [
    ('SS',  10.0),
    ('CF',   8.0),
    ('3B',   7.0),
    ('2B',   6.0),
    ('C',    5.0),
    ('RF',   5.0),
    ('LF',   4.0),
    ('1B',   3.0),
]

_DH_SHARPNESS = 2      # exponent for P(DH) ratio contrast; higher = more spread
_DH_VERSATILITY = 0.1  # DEF multiplier per secondary position (sqrt-scaled); more positions = less likely to DH
_DH_FLD_DEBUFF = 20    # flat FLD penalty when playing a secondary position
_DH_SEC_BASE_RATE = 0.1        # rate of secondary-position play when N=1
_DH_SEC_RATE_BASE = 2 ** 0.5   # geometric growth base per additional secondary position

# Expansion of group secondary positions to individual positions
_SPOS_EXPAND = {
    'IF':    ['1B', '2B', '3B', 'SS'],
    'OF':    ['LF', 'CF', 'RF'],
    '1B/OF': ['1B', 'LF', 'CF', 'RF'],
    'IF/OF': ['1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF'],
}

# Position-specific defensive weights: (ARM, SPD, FLD)
_POS_WEIGHTS = {
    'C':  (0.50, 0.10, 0.40),
    '1B': (0.10, 0.20, 0.70),
    '2B': (0.15, 0.30, 0.55),
    'SS': (0.25, 0.30, 0.45),
    '3B': (0.30, 0.15, 0.55),
    'LF': (0.20, 0.35, 0.45),
    'CF': (0.15, 0.45, 0.40),
    'RF': (0.35, 0.30, 0.35),
}

# Per-position defensive run scale factors (runs / DEF-score-unit / 80-game season)
# Calibrated so that the P10-P90 DEF spread maps to the midpoint of each position's run range
_DEF_SCALE = {
    'SS': 89,
    'CF': 58,
    '3B': 45,
    '2B': 44,
    'C':  33,
    'RF': 46,
    'LF': 26,
    '1B': 14,
}


def _expand_secondary_positions(ppos, spos_str):
    """Return list of unique individual secondary positions, excluding ppos."""
    if not spos_str:
        return []
    expanded = _SPOS_EXPAND.get(spos_str, [spos_str])
    return [p for p in expanded if p != ppos]


def _def_score(pos, arm, spd, fld, debuff=0):
    """Compute DEF score for a position with optional FLD debuff."""
    arm_w, spd_w, fld_w = _POS_WEIGHTS[pos]
    return (arm_w * arm + spd_w * spd + fld_w * max(0, fld - debuff)) / 99


def attach_dh_model(rows, ppos_map, spos_map, e_rate_map=None, lg_pb_rate=0.0):
    """Compute OFF, DEF, and P(DH) for each row and attach as '_dh_*' keys in-place.

    DEF: position-weighted blend (primary + secondaries with 20-pt FLD debuff),
    then multiplied by a versatility factor (1 + alpha * sqrt(N)) so players
    who cover more positions are less likely to be designated as the DH.
    e_rate_map: optional dict keyed by (first, last) -> {'e_rate': float, 'pb_rate': float}
    lg_pb_rate: league-average PB/GB for catchers (used as baseline for PB correction)
    """
    n_total = len(rows)
    eligible = []
    for r in rows:
        ppos = ppos_map.get((r['first'], r['last']), '')
        spos_str = spos_map.get((r['first'], r['last']), '')
        r['_dh_pos'] = ppos
        r['_dh_spos'] = spos_str
        if ppos not in _POS_WEIGHTS:
            r['_dh_off'] = r['_dh_def'] = r['_dh_ratio'] = None
            continue
        arm, spd, fld = r['arm'], r['speed'], r['fielding']
        r['_dh_off'] = (0.45 * r['contact'] + 0.45 * r['power'] + 0.10 * spd) / 99

        sec_pos = _expand_secondary_positions(ppos, spos_str)
        sec_pos = [p for p in sec_pos if p in _POS_WEIGHTS]
        n_sec = len(sec_pos)

        # DEF: position-weighted blend with 20-pt FLD debuff on secondaries,
        # then scaled up by versatility multiplier (sqrt-scaled diminishing returns)
        if n_sec == 0:
            blend = _def_score(ppos, arm, spd, fld)
        else:
            sec_rate = _DH_SEC_BASE_RATE * _DH_SEC_RATE_BASE ** (n_sec - 1)
            pri_rate = 1.0 - sec_rate
            sec_rate_each = sec_rate / n_sec
            blend = pri_rate * _def_score(ppos, arm, spd, fld)
            for sp in sec_pos:
                blend += sec_rate_each * _def_score(sp, arm, spd, fld, debuff=_DH_FLD_DEBUFF)
        r['_dh_def'] = blend * (1 + _DH_VERSATILITY * n_sec ** 0.5)

        r['_dh_ratio'] = r['_dh_off'] / r['_dh_def'] if r['_dh_def'] > 0 else 0.0
        eligible.append(r)
    total = sum(r['_dh_ratio'] ** _DH_SHARPNESS for r in eligible)
    for r in eligible:
        r['_dh_p'] = (1 / 9) * n_total * r['_dh_ratio'] ** _DH_SHARPNESS / total if total > 0 else 0.0

    # Rpos per GB: weighted average of positional adjustments across all positions including DH
    for r in eligible:
        p_dh = r['_dh_p']
        ppos = r['_dh_pos']
        spos_str = r['_dh_spos']
        sec_pos = _expand_secondary_positions(ppos, spos_str)
        sec_pos = [p for p in sec_pos if p in _POS_WEIGHTS]
        n_sec = len(sec_pos)
        if n_sec == 0:
            pri_rate, sec_rate_each = 1.0, 0.0
        else:
            sec_rate = _DH_SEC_BASE_RATE * _DH_SEC_RATE_BASE ** (n_sec - 1)
            pri_rate = 1.0 - sec_rate
            sec_rate_each = sec_rate / n_sec
        field_scale = 1.0 - p_dh
        rpos = _RPOS.get(ppos, 0.0) * pri_rate * field_scale
        for sp in sec_pos:
            rpos += _RPOS.get(sp, 0.0) * sec_rate_each * field_scale
        rpos += _RPOS['DH'] * p_dh
        r['_dh_rpos_per_gb'] = rpos / num_games
        r['_dh_rpos_per_80g'] = rpos

    # Rdef: attribute-based defensive runs above average, weighted by playing time
    # lg_mean_def[pos] = average DEF score at that position across all primary-position players
    pos_scores = {}
    for r in eligible:
        pos = r['_dh_pos']
        score = _def_score(pos, r['arm'], r['speed'], r['fielding'])
        pos_scores.setdefault(pos, []).append(score)
    lg_mean_def = {pos: sum(v) / len(v) for pos, v in pos_scores.items()}

    for r in eligible:
        p_dh = r['_dh_p']
        ppos = r['_dh_pos']
        spos_str = r['_dh_spos']
        sec_pos = _expand_secondary_positions(ppos, spos_str)
        sec_pos = [p for p in sec_pos if p in _POS_WEIGHTS]
        n_sec = len(sec_pos)
        if n_sec == 0:
            pri_rate, sec_rate_each = 1.0, 0.0
        else:
            sec_rate = _DH_SEC_BASE_RATE * _DH_SEC_RATE_BASE ** (n_sec - 1)
            pri_rate = 1.0 - sec_rate
            sec_rate_each = sec_rate / n_sec
        field_scale = 1.0 - p_dh
        arm, spd, fld = r['arm'], r['speed'], r['fielding']
        xgb = r.get('xGB') or 0.0
        rdef_attr = 0.0
        # Primary position
        if ppos in _DEF_SCALE:
            def_pri = _def_score(ppos, arm, spd, fld)
            time_pri = xgb * pri_rate * field_scale / num_games
            rdef_attr += (def_pri - lg_mean_def.get(ppos, def_pri)) * _DEF_SCALE[ppos] * time_pri
        # Secondary positions
        for sp in sec_pos:
            if sp in _DEF_SCALE:
                def_sec = _def_score(sp, arm, spd, fld)
                time_sec = xgb * sec_rate_each * field_scale / num_games
                rdef_attr += (def_sec - lg_mean_def.get(sp, def_sec)) * _DEF_SCALE[sp] * time_sec
        r['_dh_rdef_attr'] = rdef_attr
        # Rdef_errors: actual vs expected errors given position split
        rdef_e20 = 0.0
        if e_rate_map is not None:
            rates = e_rate_map.get((r['first'], r['last']))
            if rates is not None:
                exp_e_rate = 0.0
                if ppos in mlb_E_rate:
                    exp_e_rate += mlb_E_rate[ppos] * pri_rate * field_scale
                for sp in sec_pos:
                    if sp in mlb_E_rate:
                        exp_e_rate += mlb_E_rate[sp] * sec_rate_each * field_scale
                rdef_e20 += (rates['e_rate'] - exp_e_rate) * xgb * runs_E_new
                # Passed balls: catchers only
                if ppos == 'C' and lg_pb_rate > 0:
                    exp_pb_rate = lg_pb_rate * pri_rate * field_scale
                    rdef_e20 += (rates['pb_rate'] - exp_pb_rate) * xgb * runs_PB
        r['_dh_rdef_e20'] = rdef_e20
        r['_dh_rdef'] = rdef_attr + rdef_e20

    for r in rows:
        if r.get('_dh_ratio') is None:
            r['_dh_p'] = r['_dh_rpos_per_gb'] = r['_dh_rpos_per_80g'] = r['_dh_rdef_attr'] = r['_dh_rdef_e20'] = r['_dh_rdef'] = None


def _dh_table(rows):
    records = []
    for row in rows:
        if row.get('_dh_off') is None:
            continue
        abbr = row.get('_team_abbr') or 'FA'
        records.append({
            'First Name': row['first'], 'Last Name': row['last'], 'player': '',
            'team':     abbr,
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
    ppos_map = pi['ppos'].to_dict()  # keyed by (first_name, last_name) index
    spos_map = pi['spos'].to_dict()
    abbr_map = teams_data.teams.set_index('team_name')['abbr'] if teams_data.teams is not None else {}

    rows = proj_module.compute_all()
    for r in rows:
        r['_team_abbr'] = abbr_map.get(r['team'], r['team']) if r['team'] != 'FREE AGENT' else None

    # Season 20 error/PB rates per player
    edf = bat_module.stats[(bat_module.stats['season'] == 20) & (bat_module.stats['gb'] > 0)].copy()
    edf['e_rate'] = edf['e'] / edf['gb']
    edf['pb_rate'] = edf['pb'] / edf['gb']
    e_rate_map = {}
    for _, row in edf.iterrows():
        e_rate_map[(row['First Name'], row['Last Name'])] = {
            'e_rate':  row['e_rate'],
            'pb_rate': row['pb_rate'],
        }
    # League-average PB/GB for catchers from Season 20
    cat_df = edf[edf['pos1'] == 'C']
    lg_pb_rate = cat_df['pb_rate'].mean() if len(cat_df) > 0 else 0.0

    # Old model Rdef from Season 20
    s20 = bat_module.stats[bat_module.stats['season'] == 20][['First Name', 'Last Name', 'r_def']]
    old_rdef_map = {(row['First Name'], row['Last Name']): row['r_def'] for _, row in s20.iterrows()}
    for r in rows:
        r['_dh_rdef_old'] = old_rdef_map.get((r['first'], r['last']))

    attach_dh_model(rows, ppos_map, spos_map, e_rate_map, lg_pb_rate)
    rows.sort(key=lambda r: r['_dh_rdef'] or 0, reverse=True)

    doc = make_doc("Positional Adjustments", css='style.css')
    with doc:
        h1("Positional Adjustments")
        h2("Defense")
        with table(border=0):
            with thead():
                with tr():
                    for col in ['Pos', 'ARM', 'SPD', 'FLD']:
                        th(col)
            with tbody():
                for pos, (arm_w, spd_w, fld_w) in _POS_WEIGHTS.items():
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
                for pos, rpos in sorted(_RPOS.items(), key=lambda x: -x[1]):
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
                for pos, hi in _DEF_TIERS:
                    with tr():
                        td(pos)
                        td(f"+/-{hi:.1f}")
                        td(str(_DEF_SCALE[pos]))
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
        p("Error-based defensive correction using Season 20 data. Compares a player's actual error "
          "rate (errors per game batted) against the MLB positional average error rate (2021-2025), "
          "weighted by their probability of playing each position. "
          "Formula: (actual_E_rate - expected_E_rate) x xGB x runs_E, "
          "where runs_E = -0.4 runs per error. "
          "For catchers, a passed ball correction is also applied using the Season 20 league-average "
          "PB rate as the baseline. Positive values indicate fewer errors than positionally expected.")
        h3("Rdef")
        p("Total defensive runs above average: Rdef(A) + Rdef(E20). "
          "Rdef(A) captures range and skill from attributes; Rdef(E20) captures execution from "
          "actual error data. Together with Rpos, the full defensive contribution to WAR is Rdef + Rpos.")
    Path("docs/dh.html").write_text(str(doc))
