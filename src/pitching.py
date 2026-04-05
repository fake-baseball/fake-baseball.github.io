"""
Compute derived pitching stats from basic stats and league context.
Call compute() after data.stats.load_pitching() and league.compute_league().
Results are stored in pitching.stats.
"""
import pandas as pd

from data import stats as raw
from util import fmt_ip, weighted_avg, append_summary_rows

import formulas as f
from formulas import _div

stats = None

def compute():
    global stats
    d = raw.pitching_stats.copy()

    f.compute_p_era(d)
    f.compute_p_era_minus(d)
    f.compute_p_ra9(d)
    f.compute_p_whip(d)
    f.compute_p_fip(d)
    f.compute_p_baa(d)
    f.compute_p_obpa(d)
    f.compute_p_babip(d)
    f.compute_p_win_pct(d)
    f.compute_p_k_per_9(d)
    f.compute_p_h_per_9(d)
    f.compute_p_hr_per_9(d)
    f.compute_p_bb_per_9(d)
    f.compute_p_k_per_bb(d)
    f.compute_p_hr_pct(d)
    f.compute_p_k_pct(d)
    f.compute_p_bb_pct(d)
    f.compute_p_p_per_gp(d)
    f.compute_p_p_per_ip(d)
    f.compute_p_p_per_pa(d)
    f.compute_p_ip_per_gp(d)
    f.compute_p_sv_pct(d)

    # Defense-adjusted RA9
    f.compute_p_r_def(d)
    f.compute_p_ra9_def(d)

    # WAR
    f.compute_p_raa(d)
    f.compute_p_r_lev(d)
    f.compute_p_raa_lev(d)
    f.compute_p_waa(d)
    f.compute_p_r_rep(d)
    f.compute_p_rar(d)
    f.compute_p_war(d)

    # Cy Young Predictor
    from data import teams as teams_data
    div_winners = set()
    if teams_data.standings is not None and teams_data.teams is not None:
        abbr_map = teams_data.teams.set_index('team_name')['abbr'].to_dict()
        for _, row in teams_data.standings[teams_data.standings['GB'] == 0].iterrows():
            abbr = abbr_map.get(row['teamName'])
            if abbr:
                div_winners.add((row['Season'], abbr))
    d['p_vb'] = d.apply(lambda row: 1 if (row['season'], row['team']) in div_winners else 0, axis=1)
    f.compute_p_cyp(d)
    f.compute_p_cyp2(d)
    f.compute_p_cyp3(d)

    d['stat_type'] = 'season'
    stats = _append_summary_rows(d)

def _append_summary_rows(d):
    return append_summary_rows(
        d,
        player_keys=['first_name', 'last_name'],
        recompute_fn=_recompute_rates,
        weighted_avg_specs=[
            ('p_era_minus', 'p_ip'),
            ('p_fip',       'p_ip'),
            ('p_ra9_def',   'p_ip'),
        ],
        extra_meta={'role': ''},
    )


def _recompute_rates(df):
    # DataFrame already has final column names - just call formula functions directly
    f.compute_p_era(df)
    f.compute_p_ra9(df)
    f.compute_p_whip(df)
    f.compute_p_baa(df)
    f.compute_p_obpa(df)
    f.compute_p_babip(df)
    f.compute_p_win_pct(df)
    f.compute_p_k_per_9(df)
    f.compute_p_h_per_9(df)
    f.compute_p_hr_per_9(df)
    f.compute_p_bb_per_9(df)
    f.compute_p_k_per_bb(df)
    f.compute_p_k_pct(df)
    f.compute_p_bb_pct(df)
    f.compute_p_p_per_gp(df)
    f.compute_p_p_per_ip(df)
    f.compute_p_p_per_pa(df)
    f.compute_p_ip_per_gp(df)
    f.compute_p_sv_pct(df)
    return df
