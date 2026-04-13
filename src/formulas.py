"""
Centralized stat calculators.

Each function takes a single subscriptable `d` - a DataFrame, a Series row,
or a plain dict - reads its inputs via `d['col']`, and writes the result back
as `d['col'] = ...`.

The safe-division helper `_div` handles both the array case (DataFrame column
returns a Series) and the scalar case (dict/row returns a plain number).

Function naming convention: compute_<output_column_name>.
For columns shared between batting and pitching DataFrames (war, raa, rar, etc.),
use b_ or p_ prefix to disambiguate: compute_b_war, compute_p_war, etc.
"""
import numpy as np
import pandas as pd

from constants import (
    weight_BB, weight_HBP, weight_1B, weight_2B, weight_3B, weight_HR, ratio_GF,
    scale_wOBA, runs_SB, runs_CS, runs_E, park_factors, num_games, DEF_IMPACT,
)


# -- Safe division -------------------------------------------------------------

def _div(num, denom):
    """Return num/denom, substituting 0 wherever denom is zero."""
    if isinstance(denom, pd.Series):
        return np.divide(num, denom, out=np.zeros(len(denom), dtype=float), where=denom != 0)
    return (num / denom) if denom != 0 else 0.0


# -- Shared wOBA building blocks (batting column names) ------------------------

def wOBA_num(d):     return weight_BB*d['bb'] + weight_HBP*d['hbp'] + weight_1B*d['b_1b'] + weight_2B*d['b_2b'] + weight_3B*d['b_3b'] + weight_HR*d['hr']
def wOBA_denom(d):   return d['ab'] + d['bb'] + d['hbp'] + d['sf']
def compute_woba(d): d['woba'] = _div(wOBA_num(d), wOBA_denom(d))

# -- Batting counting stats (final column names) --------------------------------

def compute_tb(d):      d['tb']     = d['b_1b'] + 2*d['b_2b'] + 3*d['b_3b'] + 4*d['hr']
def compute_xbh(d):     d['xbh']    = d['b_2b'] + d['b_3b'] + d['hr']
def compute_bip_bat(d): d['bip']    = d['ab'] - d['k'] - d['hr'] + d['sf']
def compute_gf(d):      d['gf']     = d['gb'] * ratio_GF
def compute_sb_att(d):  d['sb_att'] = d['sb'] + d['cs']
def compute_rs(d):      d['rs']     = d['r'] * 4
def compute_rb(d):      d['rb']     = d['bb'] + d['hbp'] + d['b_1b'] + 2*d['b_2b'] + 3*d['b_3b'] + 4*d['hr']


# -- Batting rate stats (final column names) ------------------------------------

def compute_avg(d):        d['avg']        = _div(d['h'], d['ab'])
def compute_obp(d):        d['obp']        = _div(d['h'] + d['bb'] + d['hbp'], d['ab'] + d['bb'] + d['hbp'] + d['sf'])
def compute_slg(d):        d['slg']        = _div(d['tb'], d['ab'])
def compute_ops(d):        d['ops']        = d['obp'] + d['slg']
def compute_iso(d):        d['iso']        = d['slg'] - d['avg']
def compute_babip_bat(d):  d['babip']      = _div(d['h'] - d['hr'], d['bip'])
def compute_hr_pct_bat(d): d['hr_pct']     = _div(d['hr'], d['pa'])
def compute_k_pct_bat(d):  d['k_pct']      = _div(d['k'],  d['pa'])
def compute_bb_pct_bat(d): d['bb_pct']     = _div(d['bb'], d['pa'])
def compute_pa_per_gb(d):  d['pa_per_gb']  = _div(d['pa'], d['gb'])
def compute_pa_per_hr(d):  d['pa_per_hr']  = _div(d['pa'], d['hr'])
def compute_xbh_pct(d):    d['xbh_pct']    = _div(d['xbh'], d['h'])
def compute_rs_pct(d):     d['rs_pct']     = _div(d['r'], d['h'] + d['bb'] + d['hbp'])
def compute_rc_pct(d):     d['rc_pct']     = _div(d['r'] - d['hr'], d['h'] - d['hr'] + d['bb'] + d['hbp'])
def compute_sb_pct(d):     d['sb_pct']     = _div(d['sb'], d['sb'] + d['cs'])
def compute_sb_att_pct(d): d['sb_att_pct'] = _div(d['sb'] + d['cs'], d['b_1b'])
def compute_e_per_gf(d):   d['e_per_gf']   = _div(d['e'], d['gf'])
def compute_pb_per_gf(d):  d['pb_per_gf']  = _div(d['pb'], d['gf'])
def compute_b_raa(d):      d['raa']        = d['r_bat'] + d['r_br'] + d['r_def'] + d['r_pos'] + d['r_corr']
def compute_b_rar(d):      d['rar']        = d['raa'] + d['r_rep']


# -- Batting league-context stats (require league module) ----------------------

def compute_r_bat(d):
    import league as lg
    pf = (1 + d['team'].map(park_factors).fillna(0)) / 2
    lg_woba = d['season'].map(lg.season_batting['woba'])
    d['r_bat'] = ((d['woba'] - lg_woba * pf) / scale_wOBA) * d['pa']

def compute_r_br(d):
    import league as lg
    lg_wsb = d['season'].map(lg.season_batting['lg_wsb'])
    d['r_br'] = d['sb'] * runs_SB + d['cs'] * runs_CS - lg_wsb * (d['b_1b'] + d['bb'] + d['hbp'])

def compute_e_runs(d):
    import league as lg
    avg_e       = d.set_index(['pos1', 'pos2']).index.map(lg.pos_fielding['e_per_gf'])
    d['e_runs'] = (_div(d['e'], d['gf']) - avg_e) * runs_E * d['gb']

def compute_pb_runs(d):
    import league as lg
    avg_pb       = d.set_index(['pos1', 'pos2']).index.map(lg.pos_fielding['pb_per_gf'])
    d['pb_runs'] = (_div(d['pb'], d['gf']) - avg_pb) * runs_E * d['gb']

def compute_skill_runs(d):
    """Attribute-based defensive runs above average, integrated over season21 skill snapshots.

    For season 21 rows, integrates each snapshot's DEF score against the games played under
    those skills. For all other seasons, skill_runs = 0.0.
    Skills from players_NN apply to the games played between batting_NN and batting_(NN+1).
    """
    from constants import CURRENT_SEASON, num_games
    from data.stats import load_s21_snapshots
    from data.players import player_info
    from dh import (
        def_score, expand_secondary_positions,
        POS_WEIGHTS, DEF_SCALE, DH_FLD_DEBUFF,
        DH_SEC_BASE_RATE, DH_SEC_RATE_BASE,
    )

    d['skill_runs'] = 0.0

    pl_skills, bat_gb = load_s21_snapshots()
    if not pl_skills or not bat_gb:
        return

    ppos_map = player_info['pos1'].to_dict()
    spos_map = player_info['pos2'].to_dict()

    all_pids = set()
    for gb_map in bat_gb.values():
        all_pids.update(gb_map.keys())

    bat_nums = sorted(bat_gb.keys())
    pl_nums  = sorted(pl_skills.keys())

    # League-mean DEF score per position (from final snapshot for most complete roster)
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

    # Accumulate skill_runs per player_id
    skill_map = {pid: 0.0 for pid in all_pids}

    for pl_num in pl_nums:
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

            if ppos in DEF_SCALE:
                def_pri  = def_score(ppos, arm, spd, fld)
                time_pri = interval_gb * pri_rate / num_games
                skill_map[pid] += (def_pri - lg_mean_def.get(ppos, def_pri)) * DEF_SCALE[ppos] * time_pri
            for sp in sec_pos:
                if sp in DEF_SCALE:
                    def_sec  = def_score(sp, arm, spd, fld, debuff=DH_FLD_DEBUFF)
                    time_sec = interval_gb * sec_rate_each / num_games
                    skill_map[pid] += (def_sec - lg_mean_def.get(sp, def_sec)) * DEF_SCALE[sp] * time_sec

    # Apply only to CURRENT_SEASON rows
    mask = d['season'] == CURRENT_SEASON
    d.loc[mask, 'skill_runs'] = d.loc[mask, 'player_id'].map(skill_map).fillna(0.0)

def compute_r_def(d):  d['r_def'] = d['e_runs'] + d['pb_runs'] + d['skill_runs']

def compute_r_pos(d):
    import league as lg
    rpos = d.set_index(['pos1', 'pos2']).index.map(lg.pos_adjustment['r_pos'])
    d['r_pos'] = rpos * d['gb'] / num_games

def compute_r_rep(d):
    import league as lg
    d['r_rep'] = d['pa'] * d['season'].map(lg.season_batting['rr_per_pa'])

def compute_b_waa(d):
    import league as lg
    d['waa'] = d['raa'] / d['season'].map(lg.season_batting['r_per_w'])

def compute_b_war(d):
    import league as lg
    d['war'] = d['rar'] / d['season'].map(lg.season_batting['r_per_w'])

def compute_ops_plus(d):
    import league as lg
    pf = (1 + d['team'].map(park_factors).fillna(0)) / 2
    lg_obp = d['season'].map(lg.season_batting['obp'])
    lg_slg = d['season'].map(lg.season_batting['slg'])
    d['ops_plus'] = 100 * ((d['obp'] / lg_obp) + (d['slg'] / lg_slg) - 1) / pf

def compute_wrc(d):
    import league as lg
    lg_woba     = d['season'].map(lg.season_batting['woba'])
    lg_r_per_pa = d['season'].map(lg.season_batting['r_per_pa'])
    d['wrc'] = ((d['woba'] - lg_woba) / scale_wOBA + lg_r_per_pa) * d['pa']

def compute_wrc_plus(d):
    import league as lg
    lg_r_per_pa = d['season'].map(lg.season_batting['r_per_pa'])
    lg_wrc      = d['season'].map(lg.season_batting['wrc'])
    lg_pa       = d['season'].map(lg.season_batting['pa'])
    d['wrc_plus'] = 100 * (d['r_bat'] / d['pa'] + lg_r_per_pa) / (lg_wrc / lg_pa)

def compute_r_per_pa(d): d['r_per_pa'] = _div(d['r'], d['pa'])

# -- Pitching counting stats (final column names) ------------------------------

def compute_p_gr(d):      d['p_gr']  = d['p_gp'] - d['p_gs']
def compute_p_bip(d):     d['p_bip'] = d['p_bf'] - d['p_k'] - d['p_hr'] - d['p_bb'] - d['p_hbp']

# -- Pitching rate stats (final column names) -----------------------------------

def compute_p_ra9_def(d):  d['p_ra9_def'] = _div((d['p_ra'] + d['p_r_def']) * 9, d['p_ip'])
def compute_p_raa_lev(d):  d['p_raa_lev'] = d['p_raa'] + d['p_r_lev']
def compute_p_rar(d):      d['p_rar']      = d['p_raa_lev'] + d['p_r_rep']

# -- Pitching league-context stats (require league module) ---------------------

def compute_p_era_minus(d):
    import league as lg
    d['p_era_minus'] = 100 * d['p_era'] / d['season'].map(lg.season_pitching['p_era'])

def compute_p_fip(d):
    import league as lg
    compute_fip_raw(d)
    d['p_fip'] = d['p_fip'] + d['season'].map(lg.season_pitching['p_cfip'])

def compute_p_r_def(d):
    import league as lg
    bip = d['p_bf'] - d['p_bb'] - d['p_hbp'] - d['p_k'] - d['p_hr']
    babip_diff = d.apply(
        lambda row: lg.team_defense.loc[(row['season'], row['team']), 'p_babip_diff']
        if pd.notna(row['team']) else 0.0, axis=1)
    rh = d['season'].map(lg.season_pitching['r_per_h'])
    d['p_r_def'] = -bip * babip_diff * rh * DEF_IMPACT

def compute_p_raa(d):
    import league as lg
    pf = (1 + d['team'].map(park_factors).fillna(0)) / 2
    ra9_comp = d.apply(
        lambda row: lg.role_pitching.loc[(row['season'], row['role'] == 'SP'), 'p_ra9'], axis=1)
    base_raa = (ra9_comp * pf - d['p_ra9_def']) / 9 * d['p_ip']
    d['p_r_corr'] = 0.0
    d['p_raa']    = base_raa
    season_raa = d.groupby('season')['p_raa'].sum()
    season_ip  = d.groupby('season')['p_ip'].sum()
    d['p_r_corr'] = d['season'].map(-season_raa / season_ip) * d['p_ip']
    d['p_raa']    = base_raa + d['p_r_corr']

def compute_p_r_lev(d):
    import league as lg
    d['p_r_lev'] = d.apply(
        lambda row: (
            row['p_sv']               * lg.role_leverage.loc[(row['season'], row['role']), 'r_sv'] +
            (row['p_gr'] - row['p_sv']) * lg.role_leverage.loc[(row['season'], row['role']), 'r_no_sv']
        ), axis=1)

def compute_p_waa(d):
    import league as lg
    d['p_waa'] = d['p_raa_lev'] / d['season'].map(lg.season_batting['r_per_w'])

def compute_p_r_rep(d):
    import league as lg
    rpw  = d['season'].map(lg.season_batting['r_per_w'])
    wrep = d['p_ip'] * d.apply(
        lambda row: lg.role_innings.loc[
            (row['season'], 'RP' if row['role'] == 'CL' else row['role']), 'rw_per_ip'
        ], axis=1)
    d['p_r_rep'] = rpw * wrep

def compute_p_war(d):
    import league as lg
    d['p_war'] = d['p_rar'] / d['season'].map(lg.season_batting['r_per_w'])

def compute_p_era(d):        d['p_era']       = 9 * _div(d['p_er'], d['p_ip'])
def compute_p_ra9(d):        d['p_ra9']       = 9 * _div(d['p_ra'], d['p_ip'])
def compute_p_whip(d):       d['p_whip']      = _div(d['p_bb'] + d['p_h'], d['p_ip'])
def compute_p_baa(d):        d['p_baa']       = _div(d['p_h'], d['p_bf'] - d['p_bb'] - d['p_hbp'])
def compute_p_obpa(d):       d['p_obpa']      = _div(d['p_h'] + d['p_bb'] + d['p_hbp'], d['p_bf'])
def compute_p_babip(d):      d['p_babip']     = _div(d['p_h'] - d['p_hr'], d['p_bip'])
def compute_p_win_pct(d):    d['p_win_pct']   = _div(d['p_w'], d['p_w'] + d['p_l'])
def compute_p_k_per_9(d):    d['p_k_per_9']   = 9 * _div(d['p_k'],  d['p_ip'])
def compute_p_h_per_9(d):    d['p_h_per_9']   = 9 * _div(d['p_h'],  d['p_ip'])
def compute_p_hr_per_9(d):   d['p_hr_per_9']  = 9 * _div(d['p_hr'], d['p_ip'])
def compute_p_bb_per_9(d):   d['p_bb_per_9']  = 9 * _div(d['p_bb'], d['p_ip'])
def compute_p_k_per_bb(d):   d['p_k_per_bb']  = _div(d['p_k'],  d['p_bb'])
def compute_p_hr_pct(d):     d['p_hr_pct']    = _div(d['p_hr'], d['p_bf'])
def compute_p_k_pct(d):      d['p_k_pct']     = _div(d['p_k'],  d['p_bf'])
def compute_p_bb_pct(d):     d['p_bb_pct']    = _div(d['p_bb'], d['p_bf'])
def compute_p_p_per_gp(d):   d['p_p_per_gp']  = _div(d['p_tp'], d['p_gp'])
def compute_p_p_per_ip(d):   d['p_p_per_ip']  = _div(d['p_tp'], d['p_ip'])
def compute_p_p_per_pa(d):   d['p_p_per_pa']  = _div(d['p_tp'], d['p_bf'])
def compute_p_ip_per_gp(d):  d['p_ip_per_gp'] = _div(d['p_ip'], d['p_gp'])
def compute_p_sv_pct(d):     d['p_sv_pct']    = _div(d['p_sv'], d['p_gr'])
def compute_p_cyp(d):        d['p_cyp']       = ((5 * d['p_ip'] / 9) - d['p_er']) + (d['p_k'] / 12) + (d['p_sv'] * 2.5) + d['p_sho'] + ((d['p_w'] * 6) - (d['p_l'] * 2)) + (d['p_vb'] * 12)
def compute_p_cyp2(d):       d['p_cyp2']      = (d['p_ip'] / 2) - d['p_er'] + (d['p_k'] / 10) + d['p_w']
def compute_p_cyp3(d):       d['p_cyp3']      = (d['p_ip'] / 2) - (d['p_fip'] / 9 * d['p_ip']) + (d['p_k'] / 10) + d['p_w']

# FIP without the cFIP constant - add league cFIP to get final FIP
def compute_fip_raw(d): d['p_fip'] = _div(13*d['p_hr'] + 3*(d['p_bb'] + d['p_hbp']) - 2*d['p_k'], d['p_ip'])

# Useful for league context only - not meaningful for individual players:
def compute_r_per_h(d): d['r_per_h'] = _div(d['p_ra'], d['p_h'])
def compute_p_cfip(d):  d['p_cfip']  = d['p_era'] - d['p_fip']
