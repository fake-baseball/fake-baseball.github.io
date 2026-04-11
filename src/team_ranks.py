"""
Compute per-team, per-season stat totals for all teams.
Call compute() after batting.compute() and pitching.compute().

Module-level state:
    batting  - DataFrame indexed by (season, team) with summed batting counts
               and recomputed rate stats for every team-season.
    pitching - DataFrame indexed by (season, team) with summed pitching counts
               and recomputed rate stats for every team-season.

Public helpers:
    BAT_RANK_COLS  - batting stats used in team ranking tables
    PIT_RANK_COLS  - pitching stats used in team ranking tables
    ordinal(n)     - format an integer as an ordinal string (e.g. 1 -> '1st')
"""
import batting as bat_module
import pitching as pit_module
from util import weighted_avg

batting  = None
pitching = None

BAT_RANK_COLS = [
    'war', 'r', 'h', 'b_2b', 'b_3b', 'hr', 'rbi',
    'sb', 'cs', 'bb', 'k', 'avg', 'obp', 'slg', 'ops',
    'e', 'pb',
]

PIT_RANK_COLS = [
    'p_war', 'p_era', 'p_cg', 'p_sho', 'p_sv', 'p_ip',
    'p_h', 'p_ra', 'p_er', 'p_hr', 'p_bb', 'p_k', 'p_hbp', 'p_wp', 'p_fip', 'p_whip', 'p_baa'
]


def ordinal(n):
    """Format an integer as an ordinal string (e.g. 1 -> '1st', 11 -> '11th')."""
    suffix = 'th' if 11 <= (n % 100) <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def rank_label(season_num, abbr, col, ranks_df, scope_abbrs=None):
    """Return an ordinal rank string for `abbr` in `col` for `season_num`.

    scope_abbrs - if given, restrict comparison to this set of team abbreviations.
                  If None, all teams in the season are used.
    Returns '-' if the data is unavailable.
    """
    from registry import REGISTRY
    if season_num not in ranks_df.index.get_level_values('season'):
        return '-'
    season_data = ranks_df.xs(season_num, level='season')
    if col not in season_data.columns or abbr not in season_data.index:
        return '-'
    if scope_abbrs is not None:
        season_data = season_data[season_data.index.isin(scope_abbrs)]
    if abbr not in season_data.index:
        return '-'
    lowest = REGISTRY.get(col, {}).get('lowest', False)
    ranked = season_data[col].rank(ascending=lowest, method='min')
    rank_val = int(ranked.loc[abbr])
    tied = (ranked == rank_val).sum() > 1
    return ('T-' if tied else '') + ordinal(rank_val)


def season_ranks(season_num, ranks_df, cols):
    """Return a dict mapping abbr -> {col: (conf_label, bfbl_label)} for a season.

    Requires teams_data to be loaded (for conference membership).
    """
    from data import teams as teams_data
    from registry import REGISTRY

    if season_num not in ranks_df.index.get_level_values('season'):
        return {}
    season_data = ranks_df.xs(season_num, level='season')
    conf_map = teams_data.teams.set_index('team_id')['conference_name'].to_dict()
    available = [c for c in cols if c in season_data.columns]

    # Precompute BFBL-wide ranks for each col
    bfbl_ranked = {}
    for col in available:
        lowest = REGISTRY.get(col, {}).get('lowest', False)
        bfbl_ranked[col] = season_data[col].rank(ascending=lowest, method='min')

    # Precompute conf ranks per col (keyed by conference name)
    conf_ranked = {}
    confs = {conf_map.get(a, '') for a in season_data.index}
    for conf in confs:
        members = {a for a, c in conf_map.items() if c == conf}
        conf_data = season_data[season_data.index.isin(members)]
        conf_ranked[conf] = {}
        for col in available:
            lowest = REGISTRY.get(col, {}).get('lowest', False)
            conf_ranked[conf][col] = conf_data[col].rank(ascending=lowest, method='min')

    result = {}
    for abbr in season_data.index:
        conf = conf_map.get(abbr, '')
        result[abbr] = {}
        for col in available:
            b_r = bfbl_ranked[col]
            b_val = int(b_r.loc[abbr])
            b_tied = (b_r == b_val).sum() > 1
            bfbl_str = ('T-' if b_tied else '') + ordinal(b_val)

            c_ranks = conf_ranked.get(conf, {}).get(col)
            if c_ranks is not None and abbr in c_ranks.index:
                c_val = int(c_ranks.loc[abbr])
                c_tied = (c_ranks == c_val).sum() > 1
                conf_str = ('T-' if c_tied else '') + ordinal(c_val)
            else:
                conf_str = '-'
            result[abbr][col] = (conf_str, bfbl_str)
    return result


def compute():
    global batting, pitching
    batting  = _compute_batting()
    pitching = _compute_pitching()


def _compute_batting():
    season_rows = bat_module.stats[bat_module.stats['stat_type'] == 'season'].copy()

    groups = season_rows.groupby(['season', 'team'])
    totals = groups.sum(numeric_only=True).reset_index()

    bat_module._recompute_rates(totals)

    for col, wt in [('woba', 'pa'), ('ops_plus', 'pa'), ('wrc_plus', 'pa')]:
        if col in season_rows.columns and wt in season_rows.columns:
            totals[col] = groups.apply(
                lambda g, c=col, w=wt: weighted_avg(g, c, w), include_groups=False
            ).values

    return totals.set_index(['season', 'team'])


def _compute_pitching():
    season_rows = pit_module.stats[pit_module.stats['stat_type'] == 'season'].copy()

    groups = season_rows.groupby(['season', 'team'])
    totals = groups.sum(numeric_only=True).reset_index()

    pit_module._recompute_rates(totals)

    for col, wt in [('p_era_minus', 'p_ip'), ('p_fip', 'p_ip'), ('p_ra9_def', 'p_ip')]:
        if col in season_rows.columns and wt in season_rows.columns:
            totals[col] = groups.apply(
                lambda g, c=col, w=wt: weighted_avg(g, c, w), include_groups=False
            ).values

    return totals.set_index(['season', 'team'])
