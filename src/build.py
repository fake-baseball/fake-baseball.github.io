"""
Entry point for the BFBL website generator.
Run from the project root: python3 src/build.py

Options:
  --players   player profile pages + players index
  --leaders   leaders pages
  --seasons   seasons page
  --teams     teams index page
  --home      home page

If no options are given, everything is built.

--- Module-level state ---
Each module owns its data as module-level variables; other modules import
directly rather than receiving values as function arguments.

  data/stats.py    batting_stats, pitching_stats  (raw CSV)
  data/players.py  player_info, retired_batters, retired_pitchers
  league.py        season_batting, season_pitching, pos_fielding,
                   pos_adjustment, team_defense, role_pitching,
                   role_leverage, role_innings
  batting.py       stats  (derived batting stats)
  pitching.py      stats  (derived pitching stats)
  leaders.py       max_batters, max_qual_batters,
                   max_pitchers, max_qual_pitchers, min_qual_pitchers
"""
import argparse
import sys
import os
from pathlib import Path

# Allow imports from src/ without a package prefix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import league
import batting
import pitching
import leaders

from data.stats    import load_batting, load_pitching
from data.players  import load_player_info, load_retirements
from data.teams    import load_teams

from pages.batter        import generate_batter_page
from pages.pitcher       import generate_pitcher_page
from pages.leaders_page  import generate_leaders
from pages.players_index import generate_players_index
from pages.seasons_page  import generate_seasons
from pages.teams_page    import generate_teams_index
from pages.home          import generate_home
from pages.games_page    import generate_games


def main():
    parser = argparse.ArgumentParser(description="Build the BFBL website.")
    parser.add_argument("--players", action="store_true", help="Build player pages and player index")
    parser.add_argument("--leaders", action="store_true", help="Build leaders pages")
    parser.add_argument("--seasons", action="store_true", help="Build seasons page")
    parser.add_argument("--teams",   action="store_true", help="Build teams index page")
    parser.add_argument("--home",    action="store_true", help="Build home page")
    parser.add_argument("--games",   action="store_true", help="Copy game files to docs/games/")
    args = parser.parse_args()

    # If nothing specified, build everything.
    build_all = not any([args.players, args.leaders, args.seasons, args.teams, args.home, args.games])
    do_players = build_all or args.players
    do_leaders = build_all or args.leaders
    do_seasons = build_all or args.seasons
    do_teams   = build_all or args.teams
    do_home    = build_all or args.home
    do_games   = build_all or args.games or do_home

    # ── Ensure output directories exist ──────────────────────────────────────
    Path("docs/players").mkdir(parents=True, exist_ok=True)
    Path("docs/leaders").mkdir(parents=True, exist_ok=True)
    Path("docs/teams").mkdir(parents=True, exist_ok=True)

    # ── Raw data (needed by most pages) ──────────────────────────────────────
    need_raw = do_players or do_leaders or do_seasons
    if need_raw:
        print("Loading raw data...")
        load_batting()
        load_pitching()

    # ── League averages (needed by players, leaders, seasons) ─────────────
    need_lg = do_players or do_leaders or do_seasons
    if need_lg:
        print("Computing league averages...")
        league.compute_league()

    # ── Player roster info (needed by players, leaders, teams) ────────────
    need_player_info = do_players or do_leaders or do_teams
    if need_player_info:
        print("Loading player/roster info...")
        load_player_info()

    # ── Per-player stats (needed by players, leaders) ─────────────────────
    need_stats = do_players or do_leaders
    if need_stats:
        print("Computing player stats...")
        batting.compute()
        pitching.compute()

        print("Loading retirements...")
        load_retirements()

    # ── Player pages + index ──────────────────────────────────────────────
    if do_players:
        leaders.compute_season_leaders()

        print("Generating player pages...")
        for first, last in batting.stats[['First Name', 'Last Name']].drop_duplicates().itertuples(index=False):
            generate_batter_page(first, last)

        for first, last in pitching.stats[['First Name', 'Last Name']].drop_duplicates().itertuples(index=False):
            generate_pitcher_page(first, last)

        print("Generating players index...")
        generate_players_index()

    # ── Other pages ───────────────────────────────────────────────────────
    if do_seasons:
        print("Generating seasons page...")
        generate_seasons()

    if do_teams:
        print("Generating teams page...")
        load_teams()
        generate_teams_index()

    if do_games:
        print("Generating games...")
        generate_games()

    if do_home:
        print("Generating home page...")
        generate_home()

    if do_leaders:
        print("Generating leaders pages...")
        generate_leaders()

    print("Done.")


if __name__ == "__main__":
    main()
