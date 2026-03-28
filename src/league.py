"""
League-wide context tables, computed from raw batting and pitching data.
Call compute_league() after data.stats.load_batting() and load_pitching().
All tables are then available as module-level attributes (e.g. league.season_batting).
"""
import numpy as np
import pandas as pd

from constants import (
    scale_wOBA, MIN_PA,
    runs_SB, runs_CS,
    runs_SV, SPRP_INNING_SHARE,
    batter_WAR, starter_WAR, reliever_WAR, RUNS_PER_WIN,
    num_games,
    CURRENT_SEASON, TOTAL_SEASON_GAMES,
)
from formulas import (
    _div,
    wOBA_num, wOBA_denom, compute_woba,
    compute_avg, compute_obp, compute_slg, compute_sb_pct,
    compute_e_per_gf, compute_pb_per_gf,
    compute_p_bip, compute_p_babip,
    compute_p_era, compute_p_ra9, compute_p_whip,
    compute_p_h_per_9, compute_p_hr_per_9, compute_p_bb_per_9, compute_p_k_per_9,
    compute_p_k_per_bb, compute_p_k_pct, compute_p_bb_pct, compute_p_hr_pct,
    compute_p_sv_pct, compute_p_gr,
    compute_p_p_per_ip, compute_p_p_per_pa,
    compute_fip_raw, compute_p_cfip,
    compute_r_per_h, compute_r_per_pa,
)


pos_fielding    = None
pos_adjustment  = None
season_batting  = None
season_pitching = None
team_defense    = None
role_pitching   = None
role_leverage   = None
role_innings    = None
season_scale    = {}  # season -> float: 1.0 for completed seasons, fraction for in-progress


def _completed_games_s21():
    """Return the number of completed games in Season 21 from the schedule CSV."""
    from data.sources import season21_latest
    path = season21_latest('schedule')
    if path is None:
        return 0
    sched = pd.read_csv(path)
    return int(sched.dropna(subset=['home_score', 'away_score']).shape[0])


def compute_league():
    global pos_fielding, pos_adjustment, season_batting, season_pitching
    global team_defense, role_pitching, role_leverage, role_innings, season_scale

    from data import stats as raw
    batters  = raw.batting_stats
    pitchers = raw.pitching_stats

    # ── Fielding averages by position ────────────────────────────────────────
    # batting_stats now uses final column names (e, pb, gf) after load_batting()
    fld = batters.groupby(['pos1', 'pos2']).agg({'e': 'sum', 'pb': 'sum', 'gf': 'sum'})  # fielding rates by position
    compute_e_per_gf(fld)
    compute_pb_per_gf(fld)
    pos_fielding = fld[['e_per_gf', 'pb_per_gf']]

    # ── Positional wOBA adjustments ──────────────────────────────────────────
    # batting_stats uses final names; wOBA_num/denom use final names (bb, hbp, b_1b, etc.)
    overall_wOBA = _div(wOBA_num(batters).sum(), wOBA_denom(batters).sum())

    wOBA_by_PP = (  # all-time wOBA per primary position, used for stabilization
        batters.groupby('pos1')[['bb', 'hbp', 'b_1b', 'b_2b', 'b_3b', 'hr', 'ab', 'sf']]
        .apply(lambda x: _div(wOBA_num(x).sum(), wOBA_denom(x).sum()))
        .to_dict()
    )

    posadj = (  # positional wOBA and run adjustment (r_pos) by (pos1, pos2)
        batters.groupby(['pos1', 'pos2'])
        .agg({'bb': 'sum', 'hbp': 'sum', 'b_1b': 'sum', 'b_2b': 'sum', 'b_3b': 'sum',
              'hr': 'sum', 'ab': 'sum', 'sf': 'sum', 'pa': 'sum', 'gb': 'sum'})
        .reset_index()
    )
    posadj['wOBA_raw'] = _div(wOBA_num(posadj), wOBA_denom(posadj))
    posadj['wOBA'] = posadj.apply(
        lambda row: (
            (row['pa'] * row['wOBA_raw'] + MIN_PA * wOBA_by_PP[row['pos1']]) / (row['pa'] + MIN_PA)
            if row['pa'] < MIN_PA else row['wOBA_raw']
        ),
        axis=1,
    )
    posadj['r_pos'] = ((overall_wOBA - posadj['wOBA']) / scale_wOBA) * (posadj['pa'] / posadj['gb']) * num_games
    posadj.set_index(['pos1', 'pos2'], inplace=True)
    pos_adjustment = posadj[['pa', 'wOBA_raw', 'wOBA', 'r_pos']]

    # ── Season-level batting aggregates ─────────────────────────────────────
    sb = batters.groupby('season').agg({  # season batting totals
        'pa': 'sum', 'ab': 'sum', 'r': 'sum', 'h': 'sum',
        'b_1b': 'sum', 'b_2b': 'sum', 'b_3b': 'sum', 'hr': 'sum', 'rbi': 'sum',
        'sb': 'sum', 'cs': 'sum', 'bb': 'sum', 'k': 'sum',
        'tb': 'sum', 'hbp': 'sum', 'sh': 'sum', 'sf': 'sum', 'bip': 'sum',
        'e': 'sum', 'pb': 'sum',
    })
    # season_batting uses final batting column names; use final-name formula functions
    compute_avg(sb)
    compute_obp(sb)
    compute_slg(sb)
    compute_woba(sb)
    compute_sb_pct(sb)
    sb['ops']     = sb['obp'] + sb['slg']
    # Season scale: 1.0 for completed seasons, X = completed_games/TOTAL_SEASON_GAMES for in-progress
    s_scale = {s: 1.0 for s in sb.index}
    if CURRENT_SEASON in sb.index:
        s_scale[CURRENT_SEASON] = _completed_games_s21() / TOTAL_SEASON_GAMES
    season_scale = s_scale

    sb['g'] = batters.groupby('season')['team'].nunique() * num_games
    if CURRENT_SEASON in sb.index:
        sb.loc[CURRENT_SEASON, 'g'] *= s_scale[CURRENT_SEASON]
    sb['r_per_g'] = _div(sb['r'], sb['g'])
    sb['wrc']     = (((sb['woba'] - sb['woba'].mean()) / scale_wOBA) + (sb['r'] / sb['pa'])) * sb['pa']
    sb['lg_wsb']  = _div(
        sb['sb'] * runs_SB + sb['cs'] * runs_CS,
        sb['b_1b'] + sb['bb'] + sb['hbp'],
    )
    # Use per-game run rate (not total) so partial seasons don't distort r_per_w
    sb['r_per_w']   = RUNS_PER_WIN * sb['r_per_g'] / sb['r_per_g'].mean()
    scale_s = sb.index.map(lambda s: s_scale.get(s, 1.0))
    sb['rw_per_pa'] = batter_WAR * scale_s / sb['pa']
    sb['rr_per_pa'] = sb['rw_per_pa'] * sb['r_per_w']
    sb['r_per_pa']  = _div(sb['r'], sb['pa'])
    season_batting = sb

    # ── Season-level pitching aggregates ────────────────────────────────────
    # pitchers DataFrame now uses final p_-prefixed column names after load_pitching()
    sp = pitchers.groupby('season').agg({  # season pitching totals
        'p_gp': 'sum', 'p_gs': 'sum', 'p_cg': 'sum', 'p_sho': 'sum', 'p_sv': 'sum',
        'p_ip': 'sum', 'p_h': 'sum', 'p_k': 'sum', 'p_bb': 'sum', 'p_er': 'sum',
        'p_hr': 'sum', 'p_hbp': 'sum', 'p_tp': 'sum', 'p_bf': 'sum', 'p_ra': 'sum',
        'p_wp': 'sum',
    })
    compute_p_bip(sp)
    compute_p_babip(sp)
    compute_r_per_h(sp)
    compute_p_era(sp)
    compute_p_ra9(sp)
    compute_p_whip(sp)
    compute_p_h_per_9(sp)
    compute_p_hr_per_9(sp)
    compute_p_bb_per_9(sp)
    compute_p_k_per_9(sp)
    compute_p_k_per_bb(sp)
    compute_p_k_pct(sp)
    compute_p_bb_pct(sp)
    compute_p_hr_pct(sp)
    compute_fip_raw(sp)
    compute_p_cfip(sp)
    compute_p_p_per_ip(sp)
    compute_p_p_per_pa(sp)
    compute_p_gr(sp)
    sp['g'] = pitchers.groupby('season')['team'].nunique() * num_games
    if CURRENT_SEASON in sp.index:
        sp.loc[CURRENT_SEASON, 'g'] *= s_scale[CURRENT_SEASON]
    sp['p_r_per_g'] = _div(sp['p_ra'], sp['g'])
    season_pitching = sp

    # ── Team defense BABIP ───────────────────────────────────────────────────
    td = pitchers.groupby(['season', 'team']).agg(  # team defense: BABIP vs league average
        {'p_h': 'sum', 'p_hr': 'sum', 'p_bb': 'sum', 'p_hbp': 'sum', 'p_bf': 'sum', 'p_k': 'sum'})
    compute_p_bip(td)
    compute_p_babip(td)
    td = td.merge(sp['p_babip'], left_on='season', right_index=True, suffixes=('', '_lg'))
    td['p_babip_diff'] = td['p_babip'] - td['p_babip_lg']
    team_defense = td[['p_babip', 'p_babip_diff']]

    # ── Role RA9 (starter vs. reliever) ─────────────────────────────────────
    rp = pitchers.copy()  # RA9 by starter/reliever role
    rp['Starter'] = rp['role'] == 'SP'
    rp = rp.groupby(['season', 'Starter']).agg({'p_ip': 'sum', 'p_ra': 'sum'})
    compute_p_ra9(rp)
    role_pitching = rp

    # ── Role leverage (save run values) ─────────────────────────────────────
    rl = pitchers.groupby(['season', 'role']).agg({'p_gr': 'sum', 'p_sv': 'sum'})  # leverage run values by role
    compute_p_sv_pct(rl)
    rl['r_sv'] = np.select(
        [rl.index.get_level_values('role') == 'SP',
         rl.index.get_level_values('role') == 'SP/RP'],
        [0, runs_SV / 2],
        default=runs_SV,
    )
    rl['r_no_sv'] = -rl['p_sv_pct'] * runs_SV / (1 - rl['p_sv_pct'])
    role_leverage = rl

    # ── Replacement level innings (WAR/IP by role) ───────────────────────────
    ri = pitchers.copy()  # replacement-level WAR/IP by role
    ri['role'] = ri['role'].apply(lambda r: 'RP' if r == 'CL' else r)
    ri = ri.groupby(['season', 'role']).agg({'p_ip': 'sum'})

    sprp_innings = ri.xs('SP/RP', level='role')['p_ip']
    sp_innings   = ri.xs('SP',    level='role')['p_ip']
    rp_innings   = ri.xs('RP',    level='role')['p_ip']

    def ip_adjusted(row):
        season = row.name[0]
        role   = row.name[1]
        sc  = s_scale.get(season, 1.0)
        sw  = starter_WAR  * sc
        rw  = reliever_WAR * sc
        if role == 'SP':
            return sw / (row['p_ip'] + sprp_innings.get(season, 0) * SPRP_INNING_SHARE)
        elif role == 'RP':
            return rw / (row['p_ip'] + sprp_innings.get(season, 0) * (1 - SPRP_INNING_SHARE))
        elif role == 'SP/RP':
            sp_war = sw / (sp_innings.get(season, 0) + sprp_innings.get(season, 0) * SPRP_INNING_SHARE)
            rp_war = rw / (rp_innings.get(season, 0) + sprp_innings.get(season, 0) * (1 - SPRP_INNING_SHARE))
            return (sp_war + rp_war) / 2
        else:
            raise ValueError(f"Unmatched role: {role}")

    ri['rw_per_ip'] = ri.apply(ip_adjusted, axis=1)
    role_innings = ri
