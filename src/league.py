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
    _div, wOBA_num, wOBA_denom, compute_wOBA,
    compute_AVG, compute_OBP, compute_SLG, compute_SB_pct,
    compute_ERA, compute_RA9, compute_SV_pct,
    compute_BIP_pit, compute_BABIP_pit,
    compute_WHIP,
    compute_H_per_9, compute_HR_per_9, compute_BB_per_9,
    compute_K_per_9, compute_K_per_BB,
    compute_K_pct_pit, compute_BB_pct_pit, compute_HR_pct_pit,
    compute_E_per_GF, compute_PB_per_GF,
    compute_R_per_PA, compute_R_per_H, compute_FIP_raw, compute_cFIP,
    compute_P_per_IP, compute_P_per_PA,
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
    fld = batters.groupby(['PP', '2P']).agg({'E': 'sum', 'PB': 'sum', 'GF': 'sum'})  # fielding rates by position
    compute_E_per_GF(fld)
    compute_PB_per_GF(fld)
    pos_fielding = fld[['E/GF', 'PB/GF']]

    # ── Positional wOBA adjustments ──────────────────────────────────────────
    overall_wOBA = _div(wOBA_num(batters).sum(), wOBA_denom(batters).sum())

    wOBA_by_PP = (  # all-time wOBA per primary position, used for stabilization
        batters.groupby('PP')[['BB', 'HBP', '1B', '2B', '3B', 'HR', 'AB', 'SF']]
        .apply(lambda x: _div(wOBA_num(x).sum(), wOBA_denom(x).sum()))
        .to_dict()
    )

    posadj = (  # positional wOBA and run adjustment (Rpos) by (PP, 2P)
        batters.groupby(['PP', '2P'])
        .agg({'BB': 'sum', 'HBP': 'sum', '1B': 'sum', '2B': 'sum', '3B': 'sum',
              'HR': 'sum', 'AB': 'sum', 'SF': 'sum', 'PA': 'sum', 'GB': 'sum'})
        .reset_index()
    )
    posadj['wOBA_raw'] = _div(wOBA_num(posadj), wOBA_denom(posadj))
    posadj['wOBA'] = posadj.apply(
        lambda row: (
            (row['PA'] * row['wOBA_raw'] + MIN_PA * wOBA_by_PP[row['PP']]) / (row['PA'] + MIN_PA)
            if row['PA'] < MIN_PA else row['wOBA_raw']
        ),
        axis=1,
    )
    posadj['Rpos'] = ((overall_wOBA - posadj['wOBA']) / scale_wOBA) * (posadj['PA'] / posadj['GB']) * num_games
    posadj.set_index(['PP', '2P'], inplace=True)
    pos_adjustment = posadj[['PA', 'wOBA_raw', 'wOBA', 'Rpos']]

    # ── Season-level batting aggregates ─────────────────────────────────────
    sb = batters.groupby('Season').agg({  # season batting totals
        'PA': 'sum', 'AB': 'sum', 'R': 'sum', 'H': 'sum',
        '1B': 'sum', '2B': 'sum', '3B': 'sum', 'HR': 'sum', 'RBI': 'sum',
        'SB': 'sum', 'CS': 'sum', 'BB': 'sum', 'K': 'sum',
        'TB': 'sum', 'HBP': 'sum', 'SH': 'sum', 'SF': 'sum', 'BIP': 'sum',
        'E': 'sum', 'PB': 'sum',
    })
    compute_AVG(sb)
    compute_OBP(sb)
    compute_SLG(sb)
    compute_wOBA(sb)
    compute_SB_pct(sb)
    sb['OPS']  = sb['OBP'] + sb['SLG']
    sb['G']    = batters.groupby('Season')['Team'].nunique() * num_games
    sb['R/G']  = _div(sb['R'], sb['G'])
    sb['wRC']  = (((sb['wOBA'] - sb['wOBA'].mean()) / scale_wOBA) + (sb['R'] / sb['PA'])) * sb['PA']
    sb['lg_wSB'] = _div(
        sb['SB'] * runs_SB + sb['CS'] * runs_CS,
        sb['1B'] + sb['BB'] + sb['HBP'],
    )
    sb['R/W']   = RUNS_PER_WIN * sb['R'] / sb['R'].mean()
    sb['RW/PA'] = batter_WAR / sb['PA']
    sb['RR/PA'] = sb['RW/PA'] * sb['R/W']
    compute_R_per_PA(sb)
    season_batting = sb

    # ── Season-level pitching aggregates ────────────────────────────────────
    sp = pitchers.groupby('Season').agg({  # season pitching totals
        'GP': 'sum', 'GS': 'sum', 'CG': 'sum', 'SHO': 'sum', 'SV': 'sum',
        'IP_true': 'sum', 'H': 'sum', 'K': 'sum', 'BB': 'sum', 'ER': 'sum',
        'HR': 'sum', 'HBP': 'sum', 'TP': 'sum', 'BF': 'sum', 'RA': 'sum',
        'WP': 'sum',
    })
    compute_BIP_pit(sp)
    compute_BABIP_pit(sp)
    compute_R_per_H(sp)
    compute_ERA(sp)
    compute_WHIP(sp)
    compute_H_per_9(sp)
    compute_HR_per_9(sp)
    compute_BB_per_9(sp)
    compute_K_per_9(sp)
    compute_K_per_BB(sp)
    compute_K_pct_pit(sp)
    compute_BB_pct_pit(sp)
    compute_HR_pct_pit(sp)
    compute_RA9(sp)
    compute_FIP_raw(sp)
    compute_cFIP(sp)
    compute_P_per_IP(sp)
    compute_P_per_PA(sp)
    sp['GR'] = sp['GP'] - sp['GS']
    sp['G']  = pitchers.groupby('Season')['Team'].nunique() * num_games
    sp['R/G'] = _div(sp['RA'], sp['G'])
    season_pitching = sp

    # ── Team defense BABIP ───────────────────────────────────────────────────
    td = pitchers.groupby(['Season', 'Team']).agg(  # team defense: BABIP vs league average
        {'H': 'sum', 'HR': 'sum', 'BB': 'sum', 'HBP': 'sum', 'BF': 'sum', 'K': 'sum'})
    compute_BIP_pit(td)
    compute_BABIP_pit(td)
    td = td.merge(sp['BABIP'], left_on='Season', right_index=True, suffixes=('', '_lg'))
    td['BABIP_diff'] = td['BABIP'] - td['BABIP_lg']
    team_defense = td[['BABIP', 'BABIP_diff']]

    # ── Role RA9 (starter vs. reliever) ─────────────────────────────────────
    rp = pitchers.copy()  # RA9 by starter/reliever role
    rp['Starter'] = rp['Role'] == 'SP'
    rp = rp.groupby(['Season', 'Starter']).agg({'IP_true': 'sum', 'RA': 'sum'})
    compute_RA9(rp)
    role_pitching = rp

    # ── Role leverage (save run values) ─────────────────────────────────────
    rl = pitchers.groupby(['Season', 'Role']).agg({'GR': 'sum', 'SV': 'sum'})  # leverage run values by role
    compute_SV_pct(rl)
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
    ri = ri.groupby(['Season', 'Role']).agg({'IP_true': 'sum'})

    sprp_innings = ri.xs('SP/RP', level='Role')['IP_true']
    sp_innings   = ri.xs('SP',    level='Role')['IP_true']
    rp_innings   = ri.xs('RP',    level='Role')['IP_true']

    def ip_adjusted(row):
        season = row.name[0]
        role   = row.name[1]
        if role == 'SP':
            return starter_WAR / (row['IP_true'] + sprp_innings.get(season, 0) * SPRP_INNING_SHARE)
        elif role == 'RP':
            return reliever_WAR / (row['IP_true'] + sprp_innings.get(season, 0) * (1 - SPRP_INNING_SHARE))
        elif role == 'SP/RP':
            sp_war = starter_WAR  / (sp_innings.get(season, 0) + sprp_innings.get(season, 0) * SPRP_INNING_SHARE)
            rp_war = reliever_WAR / (rp_innings.get(season, 0) + sprp_innings.get(season, 0) * (1 - SPRP_INNING_SHARE))
            return (sp_war + rp_war) / 2
        else:
            raise ValueError(f"Unmatched role: {role}")

    ri['RW/IP'] = ri.apply(ip_adjusted, axis=1)
    role_innings = ri
