"""
Compute derived batting stats from basic stats and league context.
Call compute() after data.stats.load_batting() and league.compute_league().
Results are stored in batting.stats.
"""
import pandas as pd

from data import stats as raw
from util import weighted_avg, append_summary_rows

import formulas as f

stats = None

def compute():
    global stats
    # batting_stats already has final column names from load_batting()
    d = raw.batting_stats.copy()

    f.compute_avg(d)
    f.compute_obp(d)
    f.compute_slg(d)
    f.compute_ops(d)
    f.compute_babip_bat(d)
    f.compute_woba(d)
    f.compute_iso(d)
    f.compute_hr_pct_bat(d)
    f.compute_k_pct_bat(d)
    f.compute_bb_pct_bat(d)
    f.compute_pa_per_gb(d)
    f.compute_pa_per_hr(d)
    f.compute_xbh_pct(d)
    f.compute_rs_pct(d)
    f.compute_rc_pct(d)
    f.compute_rs(d)
    f.compute_rb(d)
    f.compute_sb_pct(d)
    f.compute_sb_att_pct(d)
    f.compute_e_per_gf(d)
    f.compute_pb_per_gf(d)

    # Batting value (r_bat must come before wrc_plus)
    f.compute_r_bat(d)
    f.compute_r_br(d)
    f.compute_e_runs(d)
    f.compute_pb_runs(d)
    f.compute_skill_runs(d)
    f.compute_r_def(d)
    f.compute_r_pos(d)

    d['r_corr'] = 0.0
    f.compute_b_raa(d)

    # Zero-sum correction: distribute the season RAA imbalance proportionally by PA
    season_raa = d.groupby('season')['raa'].sum()
    season_pa  = d.groupby('season')['pa'].sum()
    d['r_corr'] = d['season'].map(-season_raa / season_pa) * d['pa']
    f.compute_b_raa(d)

    f.compute_r_rep(d)
    f.compute_b_rar(d)
    f.compute_b_waa(d)
    f.compute_b_war(d)

    # Park-adjusted rate stats (computed after r_bat so order is correct)
    f.compute_ops_plus(d)
    f.compute_wrc(d)
    f.compute_wrc_plus(d)

    d['stat_type'] = 'season'
    stats = _append_summary_rows(d)
    stats['player_name'] = stats['player_id']


def _append_summary_rows(d):
    return append_summary_rows(
        d,
        player_keys=['player_id'],
        recompute_fn=_recompute_rates,
        weighted_avg_specs=[
            ('woba',     'pa'),
            ('ops_plus', 'pa'),
            ('wrc_plus', 'pa'),
        ],
        extra_meta={'pos1': '', 'pos2': ''},
    )


def _recompute_rates(df):
    # DataFrame already has final column names - just call formula functions directly
    f.compute_avg(df)
    f.compute_obp(df)
    f.compute_slg(df)
    f.compute_ops(df)
    f.compute_babip_bat(df)
    f.compute_iso(df)
    f.compute_hr_pct_bat(df)
    f.compute_k_pct_bat(df)
    f.compute_bb_pct_bat(df)
    f.compute_pa_per_gb(df)
    f.compute_pa_per_hr(df)
    f.compute_xbh_pct(df)
    f.compute_rs_pct(df)
    f.compute_rc_pct(df)
    f.compute_sb_pct(df)
    f.compute_sb_att_pct(df)
    f.compute_e_per_gf(df)
    f.compute_pb_per_gf(df)
    return df
