"""Generate individual team-season pages (docs/teams/{slug}/{n}.html)."""
from pathlib import Path

from dominate.tags import *

import batting as bat_module
import pitching as pit_module
from data import teams as teams_data
from util import make_doc, render_table, fmt_round


_BAT_COLS = [
    'player', 'war',
    'gb', 'pa', 'ab', 'r', 'h', 'b_2b', 'b_3b', 'hr', 'rbi',
    'sb', 'cs', 'bb', 'k', 'avg', 'obp', 'slg', 'ops', 'ops_plus',
    'tb', 'hbp', 'sh', 'sf', 'e', 'pb', 'stat_type',
]

_PIT_COLS = [
    'player', 'p_war',
    'p_w', 'p_l', 'p_win_pct', 'p_era', 'p_gp', 'p_gs', 'p_cg', 'p_sho', 'p_sv', 'p_ip',
    'p_h', 'p_ra', 'p_er', 'p_hr', 'p_bb', 'p_k', 'p_hbp', 'p_wp', 'p_bf', 'p_era_minus', 'p_fip', 'p_whip',
    'stat_type',
]


def generate_team_season_page(team_name, season_num, abbr):
    standing = teams_data.standings[
        (teams_data.standings['teamName'] == team_name) &
        (teams_data.standings['Season'] == season_num)
    ]
    if standing.empty:
        return
    row = standing.iloc[0]
    w, l = int(row['gamesWon']), int(row['gamesLost'])
    win_pct = fmt_round(w / (w + l), 3, False)

    def _prep(df, cols):
        df = df.copy()
        df['player'] = ''
        available = ['First Name', 'Last Name'] + [c for c in cols if c in df.columns]
        return df[list(dict.fromkeys(available))]

    bat_stats = bat_module.stats[
        (bat_module.stats['team'] == abbr) &
        (bat_module.stats['season'] == season_num) &
        (bat_module.stats['stat_type'] != 'career')
    ].sort_values('pa', ascending=False)

    pit_stats = pit_module.stats[
        (pit_module.stats['team'] == abbr) &
        (pit_module.stats['season'] == season_num) &
        (pit_module.stats['stat_type'] != 'career')
    ].sort_values('p_ip', ascending=False)

    team_seasons = sorted(
        teams_data.standings[teams_data.standings['teamName'] == team_name]['Season'].unique()
    )
    idx = team_seasons.index(season_num) if season_num in team_seasons else -1
    prev_season = team_seasons[idx - 1] if idx > 0 else None
    next_season = team_seasons[idx + 1] if idx >= 0 and idx < len(team_seasons) - 1 else None

    doc = make_doc(f"{team_name} Season {season_num}", css='../../style.css')
    with doc:
        h1(f"{team_name} Season {season_num}")
        with p():
            if prev_season:
                a(f"<< Season {prev_season}", href=f"{prev_season}.html")
            if prev_season and next_season:
                span(" | ")
            if next_season:
                a(f"Season {next_season} >>", href=f"{next_season}.html")
        p(f"{row['conference_name']} - {row['division_name']}")
        p(f"Record: {w}-{l} ({win_pct})")

        h2("Stats")
        p("Individual player stats here may show stats that a player achieved with another team "
          "or may not be present at all (in the case of mid-season transactions).")
        h3("Standard Batting")
        render_table(_prep(bat_stats, _BAT_COLS), depth=2)

        h3("Standard Pitching")
        render_table(_prep(pit_stats, _PIT_COLS), depth=2)

    slug = team_name.replace(' ', '')
    Path(f"docs/teams/{slug}/{season_num}.html").write_text(str(doc))
