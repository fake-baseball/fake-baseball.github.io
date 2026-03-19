"""Generate individual team-season pages (docs/teams/{slug}/{n}.html)."""
from pathlib import Path

from dominate.tags import *

import batting as bat_module
import pitching as pit_module
from data import teams as teams_data
from util import make_doc, render_stat_table, player_link, fmt_round


_BAT_COLS = [
    'Player', 'WAR',
    'GB', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'RBI',
    'SB', 'CS', 'BB', 'K', 'AVG', 'OBP', 'SLG', 'OPS', 'OPS+',
    'TB', 'HBP', 'SH', 'SF', 'E', 'PB', 'stat_type',
]

_PIT_COLS = [
    'Player', 'WAR',
    'W', 'L', 'WIN%', 'ERA', 'GP', 'GS', 'CG', 'SHO', 'SV', 'IP',
    'H', 'RA', 'ER', 'HR', 'BB', 'K', 'HBP', 'WP', 'BF', 'ERA-', 'FIP', 'WHIP',
    'stat_type',
]


def _add_player_col(df):
    df = df.copy()
    df.insert(0, 'Player', df.apply(
        lambda r: player_link(r['First Name'], r['Last Name'], prefix='../../players/'),
        axis=1,
    ))
    return df.drop(columns=['First Name', 'Last Name', 'Season', 'Age', 'Team'])


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

    bat_stats = bat_module.stats[
        (bat_module.stats['Team'] == abbr) &
        (bat_module.stats['Season'] == season_num) &
        (bat_module.stats['stat_type'] != 'career')
    ].sort_values('PA', ascending=False).copy()
    bat_stats = _add_player_col(bat_stats)

    pit_stats = pit_module.stats[
        (pit_module.stats['Team'] == abbr) &
        (pit_module.stats['Season'] == season_num) &
        (pit_module.stats['stat_type'] != 'career')
    ].sort_values('IP_true', ascending=False).copy()
    pit_stats = _add_player_col(pit_stats)

    doc = make_doc(f"{team_name} Season {season_num}", css='../../style.css')
    with doc:
        h1(f"{team_name} Season {season_num}")
        p(f"{row['conference_name']} - {row['division_name']}")
        p(f"Record: {w}-{l} ({win_pct})")

        h2("Stats")
        p("Individual player stats here may show stats that a player achieved with another team "
          "or may not be present at all (in the case of mid-season transactions).")
        h3("Standard Batting")
        render_stat_table(bat_stats[[c for c in _BAT_COLS if c in bat_stats.columns]])

        h3("Standard Pitching")
        render_stat_table(pit_stats[[c for c in _PIT_COLS if c in pit_stats.columns]])

    slug = team_name.replace(' ', '')
    Path(f"docs/teams/{slug}/{season_num}.html").write_text(str(doc))
