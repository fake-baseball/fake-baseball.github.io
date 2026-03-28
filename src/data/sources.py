"""Paths to all source data files (relative to the project root)."""
import glob
import os

BATTERS_CSV          = "sheets/MGL's BFBL with WAR - [Batters] by Season.csv"
PITCHERS_CSV         = "sheets/MGL's BFBL with WAR - [Pitchers] by Season.csv"
RETIRED_BATTERS_CSV  = "sheets/MGL's BFBL with WAR - Career Totals [Batters].csv"
RETIRED_PITCHERS_CSV = "sheets/MGL's BFBL with WAR - Career Totals [Pitchers].csv"
PLAYERS_CSV          = "sheets/players.csv"
TEAMS_CSV            = "sheets/teams.csv"
ROTATIONS_CSV        = "sheets/rotations.csv"
LINEUPS_CSV          = "sheets/lineups.csv"
STANDINGS_CSV        = "sheets/standings.csv"
SCHEDULE20_CSV       = "sheets/schedule20.csv"

SEASON21_DIR = "sheets/season21"


def _season21_files(prefix):
    """Return sorted list of sheets/season21/{prefix}_NN.csv paths."""
    pattern = os.path.join(SEASON21_DIR, f"{prefix}_*.csv")
    return sorted(glob.glob(pattern))


def season21_latest(prefix):
    """Path to the highest-numbered season21 file for this prefix."""
    files = _season21_files(prefix)
    return files[-1] if files else None


def season21_earliest(prefix):
    """Path to the lowest-numbered season21 file for this prefix."""
    files = _season21_files(prefix)
    return files[0] if files else None
