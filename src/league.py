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
)
from formulas import (
    _div,
    wOBA_num_raw, wOBA_denom_raw, compute_woba_raw,
    compute_avg_raw, compute_obp_raw, compute_slg_raw, compute_sb_pct_raw,
    compute_era_raw, compute_ra9_raw, compute_sv_pct_raw,
    compute_bip_pit_raw, compute_babip_pit_raw,
    compute_whip_raw,
    compute_h_per_9_raw, compute_hr_per_9_raw, compute_bb_per_9_raw,
    compute_k_per_9_raw, compute_k_per_bb_raw,
    compute_k_pct_pit_raw, compute_bb_pct_pit_raw, compute_hr_pct_pit_raw,
    compute_e_per_gf_raw, compute_pb_per_gf_raw,
    compute_r_per_pa, compute_r_per_h, compute_fip_raw_raw, compute_cfip,
    compute_p_per_ip_raw, compute_p_per_pa_raw,
)


pos_fielding    = None
pos_adjustment  = None
season_batting  = None
season_pitching = None
team_defense    = None
role_pitching   = None
role_leverage   = None
role_innings    = None


def compute_league():
    global pos_fielding, pos_adjustment, season_batting, season_pitching
    global team_defense, role_pitching, role_leverage, role_innings

    from data import stats as raw
    batters  = raw.batting_stats
    pitchers = raw.pitching_stats

    # ── Fielding averages by position ────────────────────────────────────────
    # batting_stats now uses final column names (e, pb, gf) after load_batting()
    fld = batters.groupby(['PP', '2P']).agg({'e': 'sum', 'pb': 'sum', 'gf': 'sum'})  # fielding rates by position
    from formulas import compute_e_per_gf, compute_pb_per_gf
    compute_e_per_gf(fld)
    compute_pb_per_gf(fld)
    pos_fielding = fld[['e_per_gf', 'pb_per_gf']]

    # ── Positional wOBA adjustments ──────────────────────────────────────────
    # batting_stats uses final names; wOBA_num/denom use final names (bb, hbp, b_1b, etc.)
    from formulas import wOBA_num, wOBA_denom
    overall_wOBA = _div(wOBA_num(batters).sum(), wOBA_denom(batters).sum())

    wOBA_by_PP = (  # all-time wOBA per primary position, used for stabilization
        batters.groupby('PP')[['bb', 'hbp', 'b_1b', 'b_2b', 'b_3b', 'hr', 'ab', 'sf']]
        .apply(lambda x: _div(wOBA_num(x).sum(), wOBA_denom(x).sum()))
        .to_dict()
    )

    posadj = (  # positional wOBA and run adjustment (r_pos) by (PP, 2P)
        batters.groupby(['PP', '2P'])
        .agg({'bb': 'sum', 'hbp': 'sum', 'b_1b': 'sum', 'b_2b': 'sum', 'b_3b': 'sum',
              'hr': 'sum', 'ab': 'sum', 'sf': 'sum', 'pa': 'sum', 'gb': 'sum'})
        .reset_index()
    )
    posadj['wOBA_raw'] = _div(wOBA_num(posadj), wOBA_denom(posadj))
    posadj['wOBA'] = posadj.apply(
        lambda row: (
            (row['pa'] * row['wOBA_raw'] + MIN_PA * wOBA_by_PP[row['PP']]) / (row['pa'] + MIN_PA)
            if row['pa'] < MIN_PA else row['wOBA_raw']
        ),
        axis=1,
    )
    posadj['r_pos'] = ((overall_wOBA - posadj['wOBA']) / scale_wOBA) * (posadj['pa'] / posadj['gb']) * num_games
    posadj.set_index(['PP', '2P'], inplace=True)
    pos_adjustment = posadj[['pa', 'wOBA_raw', 'wOBA', 'r_pos']]

    # ── Season-level batting aggregates ─────────────────────────────────────
    sb = batters.groupby('Season').agg({  # season batting totals
        'pa': 'sum', 'ab': 'sum', 'r': 'sum', 'h': 'sum',
        'b_1b': 'sum', 'b_2b': 'sum', 'b_3b': 'sum', 'hr': 'sum', 'rbi': 'sum',
        'sb': 'sum', 'cs': 'sum', 'bb': 'sum', 'k': 'sum',
        'tb': 'sum', 'hbp': 'sum', 'sh': 'sum', 'sf': 'sum', 'bip': 'sum',
        'e': 'sum', 'pb': 'sum',
    })
    # season_batting uses final batting column names; use final-name formula functions
    from formulas import compute_avg, compute_obp, compute_slg, compute_woba, compute_sb_pct
    compute_avg(sb)
    compute_obp(sb)
    compute_slg(sb)
    compute_woba(sb)
    compute_sb_pct(sb)
    sb['ops']  = sb['obp'] + sb['slg']
    sb['G']    = batters.groupby('Season')['Team'].nunique() * num_games
    sb['R/G']  = _div(sb['r'], sb['G'])
    sb['wRC']  = (((sb['woba'] - sb['woba'].mean()) / scale_wOBA) + (sb['r'] / sb['pa'])) * sb['pa']
    sb['lg_wSB'] = _div(
        sb['sb'] * runs_SB + sb['cs'] * runs_CS,
        sb['b_1b'] + sb['bb'] + sb['hbp'],
    )
    sb['R/W']   = RUNS_PER_WIN * sb['r'] / sb['r'].mean()
    sb['RW/PA'] = batter_WAR / sb['pa']
    sb['RR/PA'] = sb['RW/PA'] * sb['R/W']
    sb['R/PA']  = _div(sb['r'], sb['pa'])
    # Also store upper-case aliases needed by projections.py and pit_projections.py
    sb['wOBA'] = sb['woba']
    sb['OBP']  = sb['obp']
    sb['SLG']  = sb['slg']
    sb['PA']   = sb['pa']
    season_batting = sb

    # ── Season-level pitching aggregates ────────────────────────────────────
    # pitchers DataFrame now uses final p_-prefixed column names after load_pitching()
    sp = pitchers.groupby('Season').agg({  # season pitching totals
        'p_gp': 'sum', 'p_gs': 'sum', 'p_cg': 'sum', 'p_sho': 'sum', 'p_sv': 'sum',
        'p_ip': 'sum', 'p_h': 'sum', 'p_k': 'sum', 'p_bb': 'sum', 'p_er': 'sum',
        'p_hr': 'sum', 'p_hbp': 'sum', 'p_tp': 'sum', 'p_bf': 'sum', 'p_ra': 'sum',
        'p_wp': 'sum',
    })
    # Add raw-name aliases so the _raw helper functions work on this aggregated DataFrame
    sp['BF']     = sp['p_bf']
    sp['K']      = sp['p_k']
    sp['HR']     = sp['p_hr']
    sp['BB']     = sp['p_bb']
    sp['HBP']    = sp['p_hbp']
    sp['H']      = sp['p_h']
    sp['BIP']    = sp['p_bf'] - sp['p_k'] - sp['p_hr'] - sp['p_bb'] - sp['p_hbp']
    sp['IP_true'] = sp['p_ip']
    sp['ER']     = sp['p_er']
    sp['RA']     = sp['p_ra']
    sp['TP']     = sp['p_tp']
    compute_babip_pit_raw(sp)
    compute_r_per_h(sp)
    compute_era_raw(sp)
    compute_whip_raw(sp)
    compute_h_per_9_raw(sp)
    compute_hr_per_9_raw(sp)
    compute_bb_per_9_raw(sp)
    compute_k_per_9_raw(sp)
    compute_k_per_bb_raw(sp)
    compute_k_pct_pit_raw(sp)
    compute_bb_pct_pit_raw(sp)
    compute_hr_pct_pit_raw(sp)
    compute_ra9_raw(sp)
    compute_fip_raw_raw(sp)
    compute_cfip(sp)
    compute_p_per_ip_raw(sp)
    compute_p_per_pa_raw(sp)
    sp['GR'] = sp['p_gp'] - sp['p_gs']
    sp['G']  = pitchers.groupby('Season')['Team'].nunique() * num_games
    sp['R/G'] = _div(sp['p_ra'], sp['G'])
    season_pitching = sp

    # ── Team defense BABIP ───────────────────────────────────────────────────
    td = pitchers.groupby(['Season', 'Team']).agg(  # team defense: BABIP vs league average
        {'p_h': 'sum', 'p_hr': 'sum', 'p_bb': 'sum', 'p_hbp': 'sum', 'p_bf': 'sum', 'p_k': 'sum'})
    # Add raw-name aliases for the _raw helper functions
    td['H']   = td['p_h']
    td['HR']  = td['p_hr']
    td['BB']  = td['p_bb']
    td['HBP'] = td['p_hbp']
    td['BF']  = td['p_bf']
    td['K']   = td['p_k']
    td['BIP'] = td['p_bf'] - td['p_k'] - td['p_hr'] - td['p_bb'] - td['p_hbp']
    compute_babip_pit_raw(td)
    td = td.merge(sp['BABIP'], left_on='Season', right_index=True, suffixes=('', '_lg'))
    td['BABIP_diff'] = td['BABIP'] - td['BABIP_lg']
    team_defense = td[['BABIP', 'BABIP_diff']]

    # ── Role RA9 (starter vs. reliever) ─────────────────────────────────────
    rp = pitchers.copy()  # RA9 by starter/reliever role
    rp['Starter'] = rp['Role'] == 'SP'
    rp = rp.groupby(['Season', 'Starter']).agg({'p_ip': 'sum', 'p_ra': 'sum'})
    rp['IP_true'] = rp['p_ip']
    rp['RA']      = rp['p_ra']
    compute_ra9_raw(rp)
    role_pitching = rp

    # ── Role leverage (save run values) ─────────────────────────────────────
    rl = pitchers.groupby(['Season', 'Role']).agg({'p_gr': 'sum', 'p_sv': 'sum'})  # leverage run values by role
    rl['GR'] = rl['p_gr']
    rl['SV'] = rl['p_sv']
    compute_sv_pct_raw(rl)
    rl['R_sv'] = np.select(
        [rl.index.get_level_values('Role') == 'SP',
         rl.index.get_level_values('Role') == 'SP/RP'],
        [0, runs_SV / 2],
        default=runs_SV,
    )
    rl['R_no_SV'] = -rl['SV%'] * runs_SV / (1 - rl['SV%'])
    role_leverage = rl

    # ── Replacement level innings (WAR/IP by role) ───────────────────────────
    ri = pitchers.copy()  # replacement-level WAR/IP by role
    ri['Role'] = ri['Role'].apply(lambda r: 'RP' if r == 'CL' else r)
    ri = ri.groupby(['Season', 'Role']).agg({'p_ip': 'sum'})

    sprp_innings = ri.xs('SP/RP', level='Role')['p_ip']
    sp_innings   = ri.xs('SP',    level='Role')['p_ip']
    rp_innings   = ri.xs('RP',    level='Role')['p_ip']

    def ip_adjusted(row):
        season = row.name[0]
        role   = row.name[1]
        if role == 'SP':
            return starter_WAR / (row['p_ip'] + sprp_innings.get(season, 0) * SPRP_INNING_SHARE)
        elif role == 'RP':
            return reliever_WAR / (row['p_ip'] + sprp_innings.get(season, 0) * (1 - SPRP_INNING_SHARE))
        elif role == 'SP/RP':
            sp_war = starter_WAR  / (sp_innings.get(season, 0) + sprp_innings.get(season, 0) * SPRP_INNING_SHARE)
            rp_war = reliever_WAR / (rp_innings.get(season, 0) + sprp_innings.get(season, 0) * (1 - SPRP_INNING_SHARE))
            return (sp_war + rp_war) / 2
        else:
            raise ValueError(f"Unmatched role: {role}")

    ri['RW/IP'] = ri.apply(ip_adjusted, axis=1)
    role_innings = ri
