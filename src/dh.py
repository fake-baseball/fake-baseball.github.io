"""DH model: positional adjustments, defensive scoring, and P(DH) calculation."""
from constants import num_games, runs_E_new, runs_PB, mlb_E_rate

# Positional adjustments (runs/80-game season), rounded to nearest 1.5
RPOS = {
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
DEF_TIERS = [
    ('SS',  10.0),
    ('CF',   8.0),
    ('3B',   7.0),
    ('2B',   6.0),
    ('C',    5.0),
    ('RF',   5.0),
    ('LF',   4.0),
    ('1B',   3.0),
]

DH_SHARPNESS = 2      # exponent for P(DH) ratio contrast; higher = more spread
DH_VERSATILITY = 0.1  # DEF multiplier per secondary position (sqrt-scaled); more positions = less likely to DH
DH_FLD_DEBUFF = 20    # flat FLD penalty when playing a secondary position
DH_SEC_BASE_RATE = 0.1        # rate of secondary-position play when N=1
DH_SEC_RATE_BASE = 2 ** 0.5   # geometric growth base per additional secondary position

# Expansion of group secondary positions to individual positions
SPOS_EXPAND = {
    'IF':    ['1B', '2B', '3B', 'SS'],
    'OF':    ['LF', 'CF', 'RF'],
    '1B/OF': ['1B', 'LF', 'CF', 'RF'],
    'IF/OF': ['1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF'],
}

# Position-specific defensive weights: (ARM, SPD, FLD)
POS_WEIGHTS = {
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
DEF_SCALE = {
    'SS': 89,
    'CF': 58,
    '3B': 45,
    '2B': 44,
    'C':  33,
    'RF': 46,
    'LF': 26,
    '1B': 14,
}


def expand_secondary_positions(ppos, spos_str):
    """Return list of unique individual secondary positions, excluding ppos."""
    if not spos_str:
        return []
    expanded = SPOS_EXPAND.get(spos_str, [spos_str])
    return [p for p in expanded if p != ppos]


def def_score(pos, arm, spd, fld, debuff=0):
    """Compute DEF score for a position with optional FLD debuff."""
    arm_w, spd_w, fld_w = POS_WEIGHTS[pos]
    return (arm_w * arm + spd_w * spd + fld_w * max(0, fld - debuff)) / 99


def attach_dh_model(rows, ppos_map, spos_map, e_rate_map=None, lg_pb_rate=0.0):
    """Compute OFF, DEF, and P(DH) for each row and attach as '_dh_*' keys in-place.

    DEF: position-weighted blend (primary + secondaries with 20-pt FLD debuff),
    then multiplied by a versatility factor (1 + alpha * sqrt(N)) so players
    who cover more positions are less likely to be designated as the DH.
    e_rate_map: optional dict keyed by player_id -> {'e_rate': float, 'pb_rate': float}
    lg_pb_rate: league-average PB/GB for catchers (used as baseline for PB correction)
    """
    n_total = len(rows)
    eligible = []
    for r in rows:
        ppos = ppos_map.get(r['player_id'], '')
        spos_str = spos_map.get(r['player_id'], '')
        r['_dh_pos'] = ppos
        r['_dh_spos'] = spos_str
        if ppos not in POS_WEIGHTS:
            r['_dh_off'] = r['_dh_def'] = r['_dh_ratio'] = None
            continue
        arm, spd, fld = r['arm'], r['speed'], r['fielding']
        r['_dh_off'] = (0.45 * r['contact'] + 0.45 * r['power'] + 0.10 * spd) / 99

        sec_pos = expand_secondary_positions(ppos, spos_str)
        sec_pos = [p for p in sec_pos if p in POS_WEIGHTS]
        n_sec = len(sec_pos)

        # DEF: position-weighted blend with 20-pt FLD debuff on secondaries,
        # then scaled up by versatility multiplier (sqrt-scaled diminishing returns)
        if n_sec == 0:
            blend = def_score(ppos, arm, spd, fld)
        else:
            sec_rate = DH_SEC_BASE_RATE * DH_SEC_RATE_BASE ** (n_sec - 1)
            pri_rate = 1.0 - sec_rate
            sec_rate_each = sec_rate / n_sec
            blend = pri_rate * def_score(ppos, arm, spd, fld)
            for sp in sec_pos:
                blend += sec_rate_each * def_score(sp, arm, spd, fld, debuff=DH_FLD_DEBUFF)
        r['_dh_def'] = blend * (1 + DH_VERSATILITY * n_sec ** 0.5)

        r['_dh_ratio'] = r['_dh_off'] / r['_dh_def'] if r['_dh_def'] > 0 else 0.0
        eligible.append(r)
    total = sum(r['_dh_ratio'] ** DH_SHARPNESS for r in eligible)
    for r in eligible:
        r['_dh_p'] = (1 / 9) * n_total * r['_dh_ratio'] ** DH_SHARPNESS / total if total > 0 else 0.0

    # Rpos per GB: weighted average of positional adjustments across all positions including DH
    for r in eligible:
        p_dh = r['_dh_p']
        ppos = r['_dh_pos']
        spos_str = r['_dh_spos']
        sec_pos = expand_secondary_positions(ppos, spos_str)
        sec_pos = [p for p in sec_pos if p in POS_WEIGHTS]
        n_sec = len(sec_pos)
        if n_sec == 0:
            pri_rate, sec_rate_each = 1.0, 0.0
        else:
            sec_rate = DH_SEC_BASE_RATE * DH_SEC_RATE_BASE ** (n_sec - 1)
            pri_rate = 1.0 - sec_rate
            sec_rate_each = sec_rate / n_sec
        field_scale = 1.0 - p_dh
        rpos = RPOS.get(ppos, 0.0) * pri_rate * field_scale
        for sp in sec_pos:
            rpos += RPOS.get(sp, 0.0) * sec_rate_each * field_scale
        rpos += RPOS['DH'] * p_dh
        r['_dh_rpos_per_gb'] = rpos / num_games
        r['_dh_rpos_per_80g'] = rpos

    # Rdef: attribute-based defensive runs above average, weighted by playing time
    # lg_mean_def[pos] = average DEF score at that position across all primary-position players
    pos_scores = {}
    for r in eligible:
        pos = r['_dh_pos']
        score = def_score(pos, r['arm'], r['speed'], r['fielding'])
        pos_scores.setdefault(pos, []).append(score)
    lg_mean_def = {pos: sum(v) / len(v) for pos, v in pos_scores.items()}

    for r in eligible:
        p_dh = r['_dh_p']
        ppos = r['_dh_pos']
        spos_str = r['_dh_spos']
        sec_pos = expand_secondary_positions(ppos, spos_str)
        sec_pos = [p for p in sec_pos if p in POS_WEIGHTS]
        n_sec = len(sec_pos)
        if n_sec == 0:
            pri_rate, sec_rate_each = 1.0, 0.0
        else:
            sec_rate = DH_SEC_BASE_RATE * DH_SEC_RATE_BASE ** (n_sec - 1)
            pri_rate = 1.0 - sec_rate
            sec_rate_each = sec_rate / n_sec
        field_scale = 1.0 - p_dh
        arm, spd, fld = r['arm'], r['speed'], r['fielding']
        xgb = r.get('gb') or 0.0
        rdef_attr = 0.0
        # Primary position
        if ppos in DEF_SCALE:
            def_pri = def_score(ppos, arm, spd, fld)
            time_pri = xgb * pri_rate * field_scale / num_games
            rdef_attr += (def_pri - lg_mean_def.get(ppos, def_pri)) * DEF_SCALE[ppos] * time_pri
        # Secondary positions
        for sp in sec_pos:
            if sp in DEF_SCALE:
                def_sec = def_score(sp, arm, spd, fld)
                time_sec = xgb * sec_rate_each * field_scale / num_games
                rdef_attr += (def_sec - lg_mean_def.get(sp, def_sec)) * DEF_SCALE[sp] * time_sec
        r['_dh_rdef_attr'] = rdef_attr
        # Rdef_errors: actual vs expected errors given position split
        rdef_e20 = 0.0
        if e_rate_map is not None:
            rates = e_rate_map.get(r['player_id'])
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


def compute_season_rdef_rpos(ppos_map, spos_map, pl_skills, bat_gb):
    """Integrate Rdef(A) and Rpos over all season21 snapshots.

    pl_skills: {file_num: {player_id: {'arm', 'speed', 'fielding'}}} -- from load_s21_snapshots()
    bat_gb:    {file_num: {player_id: cumulative gamesBatting}}       -- from load_s21_snapshots()
    Skills from players_NN apply to the games played between batting_NN and batting_(NN+1).
    Returns a dict: player_id -> {'s21_rdef_attr': float, 's21_rpos': float}.
    """
    if not pl_skills or not bat_gb:
        return {}

    # All player ids across all batting files
    all_pids = set()
    for gb_map in bat_gb.values():
        all_pids.update(gb_map.keys())

    # For each interval N: skills from players_N, games = batting_(N+1).gb - batting_N.gb
    bat_nums = sorted(bat_gb.keys())
    pl_nums  = sorted(pl_skills.keys())

    # Compute league-mean DEF score per position from the final players snapshot
    # (positional identity doesn't change, so any snapshot works; use last for most complete roster)
    final_pl_num = pl_nums[-1]
    pos_scores = {}
    for pid in all_pids:
        ppos = ppos_map.get(pid, '')
        if ppos not in POS_WEIGHTS:
            continue
        skills = pl_skills[final_pl_num].get(pid) or pl_skills[pl_nums[0]].get(pid)
        if skills is None:
            continue
        score = def_score(ppos, skills['arm'], skills['speed'], skills['fielding'])
        pos_scores.setdefault(ppos, []).append(score)
    lg_mean_def = {pos: sum(v) / len(v) for pos, v in pos_scores.items()}

    # Accumulate
    result = {pid: {'s21_rdef_attr': 0.0, 's21_rpos': 0.0} for pid in all_pids}

    for i, pl_num in enumerate(pl_nums):
        # Find the batting interval this skills snapshot covers
        # skills_N -> games between batting_N and batting_(N+1)
        next_bat_nums = [n for n in bat_nums if n > pl_num]
        prev_bat_nums = [n for n in bat_nums if n <= pl_num]
        if not next_bat_nums or not prev_bat_nums:
            continue
        next_bat = next_bat_nums[0]
        prev_bat = prev_bat_nums[-1]

        for pid in all_pids:
            ppos = ppos_map.get(pid, '')
            if ppos not in POS_WEIGHTS:
                continue
            skills = pl_skills[pl_num].get(pid)
            if skills is None:
                continue

            gb_next = bat_gb[next_bat].get(pid, 0)
            gb_prev = bat_gb[prev_bat].get(pid, 0)
            interval_gb = max(0, gb_next - gb_prev)
            if interval_gb == 0:
                continue

            spos_str = spos_map.get(pid, '')
            sec_pos  = expand_secondary_positions(ppos, spos_str)
            sec_pos  = [p for p in sec_pos if p in POS_WEIGHTS]
            n_sec    = len(sec_pos)

            if n_sec == 0:
                pri_rate, sec_rate_each = 1.0, 0.0
            else:
                sec_rate = DH_SEC_BASE_RATE * DH_SEC_RATE_BASE ** (n_sec - 1)
                pri_rate = 1.0 - sec_rate
                sec_rate_each = sec_rate / n_sec

            arm, spd, fld = skills['arm'], skills['speed'], skills['fielding']

            # Rpos contribution for this interval (no DH probability adjustment here)
            rpos_interval = RPOS.get(ppos, 0.0) * pri_rate
            for sp in sec_pos:
                rpos_interval += RPOS.get(sp, 0.0) * sec_rate_each
            result[pid]['s21_rpos'] += rpos_interval * interval_gb / num_games

            # Rdef(A) contribution for this interval
            if ppos in DEF_SCALE:
                def_pri = def_score(ppos, arm, spd, fld)
                time_pri = interval_gb * pri_rate / num_games
                result[pid]['s21_rdef_attr'] += (def_pri - lg_mean_def.get(ppos, def_pri)) * DEF_SCALE[ppos] * time_pri
            for sp in sec_pos:
                if sp in DEF_SCALE:
                    def_sec = def_score(sp, arm, spd, fld, debuff=DH_FLD_DEBUFF)
                    time_sec = interval_gb * sec_rate_each / num_games
                    result[pid]['s21_rdef_attr'] += (def_sec - lg_mean_def.get(sp, def_sec)) * DEF_SCALE[sp] * time_sec

    return result
