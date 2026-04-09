"""
Entry point for the BFBL website generator.
Run from the project root: python3 src/build.py

Options:
  --players     player profile pages + players index
  --leaders     leaders pages
  --seasons     seasons page + individual season pages
  --teams       teams index + individual team/season pages
  --home        home page
  --games       copy game files and generate index
  --awards      awards page
  --projections projections page
  --salaries    salaries page
  --cy-young    Cy Young Predictor page
  --glossary    Glossary page
  --dh          Designated Hitter and Defense page

If no options are given, everything is built.
"""
import argparse
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import league
import batting
import pitching
import leaders
import team_ranks
import player_ranks
from constants         import SEASON_RANGE
from data.stats        import load_batting, load_pitching
from data.players      import load_player_info, load_retirements
from data.teams        import load_teams, load_rotations, load_lineups, load_standings, load_schedule20
from data              import teams as teams_data
import pages.page_utils as page_utils
from pages.batter           import generate_batter_page
from pages.pitcher          import generate_pitcher_page
from pages.players_index    import generate_players_index
from pages.seasons_page     import generate_seasons
from pages.season_page      import generate_season_page
from pages.teams_page       import generate_teams_index
from pages.team_season_page import generate_team_season_page
from pages.games_page       import generate_games
from pages.home             import generate_home
from pages.awards_page      import generate_awards
from pages.projections_page import generate_projections
from pages.salaries_page    import generate_salaries
from pages.glossary_page    import generate_glossary
from pages.dh_page          import generate_dh
from pages.leaders_page     import generate_leaders
from pages.cy_young_page    import generate_cy_young

# Dependencies

_DATA_DEPS = {
    'raw':         set(),
    'teams':       set(),
    'schedule':    set(),
    'rotations':   set(),
    'lineups':     set(),
    'player_info': set(),
    'retirements': set(),
    'standings':   {'teams'},
    'league':      {'raw'},
    'stats':       {'raw', 'league', 'teams', 'standings'},
    'team_ranks':   {'raw', 'league', 'teams', 'standings', 'stats'},
    'player_ranks': {'raw', 'league', 'stats'},
    'leaders':      {'raw', 'league', 'teams', 'standings', 'stats'},
}

_PAGE_DEPS = {
    'players':     {'raw', 'league', 'teams', 'standings', 'stats', 'team_ranks', 'player_ranks', 'leaders', 'player_info', 'retirements'},
    'leaders_page':{'raw', 'league', 'teams', 'standings', 'stats', 'leaders'},
    'seasons':     {'raw', 'league', 'teams', 'standings', 'schedule', 'stats', 'team_ranks', 'leaders'},
    'teams_page':  {'raw', 'league', 'teams', 'standings', 'schedule', 'rotations', 'lineups', 'player_info', 'stats', 'team_ranks', 'leaders'},
    'awards':      {'raw', 'league', 'teams', 'standings', 'stats', 'leaders'},
    'cy_young':    {'raw', 'league', 'teams', 'standings', 'stats', 'leaders'},
    'projections': {'raw', 'league', 'teams', 'standings', 'stats', 'leaders', 'player_info'},
    'salaries':    {'raw', 'league', 'teams', 'standings', 'stats', 'leaders', 'player_info'},
    'dh':          {'raw', 'league', 'teams', 'standings', 'stats', 'leaders', 'player_info'},
    'home':        set(),
    'games':       set(),
    'glossary':    set(),
}

# Topological order for data loading
_LOAD_ORDER = [
    # data loading
    'raw', 'teams', 'schedule', 'rotations', 'lineups', 'player_info', 'retirements',
    # data processing
    'standings', 'league', 'stats', 'leaders', 'team_ranks', 'player_ranks',
]

_NAV_PAGE_MAP = {
    'players':      'players',
    'leaders_page': 'leaders',
    'seasons':      'seasons',
    'teams_page':   'teams',
    'games':        'games',
    'awards':       'awards',
    'projections':  'projections',
    'dh':           'dh',
    'salaries':     'salaries',
    'cy_young':     'cy_young',
    'glossary':     'glossary',
}

_ALL_PAGES = {'players', 'leaders_page', 'seasons', 'teams_page', 'home',
              'awards', 'projections', 'salaries', 'cy_young', 'glossary', 'dh', 'games'}


def main():
    t0 = time.time()
    parser = argparse.ArgumentParser(description="Build the BFBL website.")
    parser.add_argument("--players",     action="store_true")
    parser.add_argument("--leaders",     action="store_true")
    parser.add_argument("--seasons",     action="store_true")
    parser.add_argument("--teams",       action="store_true")
    parser.add_argument("--home",        action="store_true")
    parser.add_argument("--awards",      action="store_true")
    parser.add_argument("--projections", action="store_true")
    parser.add_argument("--salaries",    action="store_true")
    parser.add_argument("--cy-young",    action="store_true")
    parser.add_argument("--glossary",    action="store_true")
    parser.add_argument("--dh",          action="store_true")
    parser.add_argument("--games",       action="store_true")
    args = parser.parse_args()

    requested = {
        'players':      args.players,
        'leaders_page': args.leaders,
        'seasons':      args.seasons,
        'teams_page':   args.teams,
        'home':         args.home,
        'awards':       args.awards,
        'projections':  args.projections,
        'salaries':     args.salaries,
        'cy_young':     args.cy_young,
        'glossary':     args.glossary,
        'dh':           args.dh,
        'games':        args.games,
    }

    pages = {k for k, v in requested.items() if v} or _ALL_PAGES

    page_utils.active_sections = {_NAV_PAGE_MAP[p] for p in pages if p in _NAV_PAGE_MAP}

    Path("docs/players").mkdir(parents=True, exist_ok=True)
    Path("docs/leaders").mkdir(parents=True, exist_ok=True)
    Path("docs/teams").mkdir(parents=True, exist_ok=True)
    Path("docs/seasons").mkdir(parents=True, exist_ok=True)

    # ── Phase 1: load and process data ───────────────────────────────────────
    needed = set().union(*(_PAGE_DEPS[p] for p in pages))

    for key in _LOAD_ORDER:
        if key not in needed:
            continue
        if key == 'raw':
            print("Loading raw data...")
            load_batting()
            load_pitching()
        elif key == 'teams':
            print("Loading teams...")
            load_teams()
        elif key == 'standings':
            print("Loading standings...")
            load_standings()
        elif key == 'schedule':
            print("Loading schedule...")
            load_schedule20()
        elif key == 'rotations':
            print("Loading rotations...")
            load_rotations()
        elif key == 'lineups':
            print("Loading lineups...")
            load_lineups()
        elif key == 'player_info':
            print("Loading player info...")
            load_player_info()
        elif key == 'league':
            print("Computing league averages...")
            league.compute_league()
        elif key == 'stats':
            print("Computing player stats...")
            batting.compute()
            pitching.compute()
        elif key == 'retirements':
            print("Loading retirements...")
            load_retirements()
        elif key == 'team_ranks':
            print("Computing team ranks...")
            team_ranks.compute()
        elif key == 'player_ranks':
            print("Computing player ranks...")
            player_ranks.compute()
        elif key == 'leaders':
            print("Computing season leaders...")
            leaders.compute_season_leaders()

    # ── Phase 2: generate pages ───────────────────────────────────────────────
    if 'players' in pages:
        print("Generating player pages...")
        for first, last in batting.stats[['first_name', 'last_name']].drop_duplicates().itertuples(index=False):
            generate_batter_page(first, last)
        for first, last in pitching.stats[['first_name', 'last_name']].drop_duplicates().itertuples(index=False):
            generate_pitcher_page(first, last)
        print("Generating players index...")
        generate_players_index()

    if 'seasons' in pages:
        print("Generating seasons page...")
        generate_seasons()
        print("Generating individual season pages...")
        for season_num in SEASON_RANGE:
            generate_season_page(season_num)

    if 'teams_page' in pages:
        print("Generating teams pages...")
        for _, t_row in teams_data.teams.iterrows():
            Path(f"docs/teams/{t_row['team_name'].replace(' ', '')}").mkdir(exist_ok=True)
        generate_teams_index()
        print("Generating team-season pages...")
        team_abbr = teams_data.teams.set_index('team_name')['abbr']
        for _, ts_row in teams_data.standings[['teamName', 'Season']].drop_duplicates().iterrows():
            tname, season_num = ts_row['teamName'], ts_row['Season']
            generate_team_season_page(tname, season_num, team_abbr[tname])

    if 'games' in pages:
        print("Generating games...")
        generate_games()

    if 'awards' in pages:
        print("Generating awards page...")
        generate_awards()

    if 'projections' in pages:
        print("Generating projections page...")
        generate_projections()

    if 'salaries' in pages:
        print("Generating salaries page...")
        generate_salaries()

    if 'glossary' in pages:
        print("Generating glossary page...")
        generate_glossary()

    if 'dh' in pages:
        print("Generating DH and Defense page...")
        generate_dh()

    if 'leaders_page' in pages:
        print("Generating leaders pages...")
        generate_leaders()

    if 'cy_young' in pages:
        print("Generating Cy Young Predictor page...")
        generate_cy_young()

    if 'home' in pages:
        print("Generating home page...")
        generate_home(page_utils.active_sections)

    print(f"Done in {time.time() - t0:.1f}s!")


if __name__ == "__main__":
    main()
