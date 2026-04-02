"""Paths to all source data files (relative to the project root)."""
import glob
import os
import pandas as pd

# Known team name discrepancies in season21 export files -> correct name
TEAM_NAME_CORRECTIONS = {
    'Dakar-Yoff Mariners': 'Yoff-Mariners Dakar',
}

_TEAM_COLS = ('mostRecentTeam', 'teamName', 'Home Team', 'Away Team', 'home_team', 'away_team')


def read_s21(path):
    """Read a season21 CSV and apply known team name corrections."""
    raw = pd.read_csv(path)
    for col in _TEAM_COLS:
        if col in raw.columns:
            raw[col] = raw[col].replace(TEAM_NAME_CORRECTIONS)
    return raw

BATTERS_CSV          = "sheets/batters_season.csv"
PITCHERS_CSV         = "sheets/pitchers_season.csv"
RETIRED_BATTERS_CSV  = "sheets/batters_career.csv"
RETIRED_PITCHERS_CSV = "sheets/pitchers_career.csv"
PLAYERS_CSV          = "sheets/players.csv"
TEAMS_CSV            = "sheets/teams.csv"
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


def season21_all(prefix):
    """Sorted list of ALL sheets/season21/{prefix}_NN.csv paths."""
    return _season21_files(prefix)
