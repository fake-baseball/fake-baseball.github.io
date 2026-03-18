import pandas as pd

from data.sources import TEAMS_CSV, ROTATIONS_CSV, LINEUPS_CSV

teams     = None
rotations = None
lineups   = None


def load_teams():
    global teams
    teams = pd.read_csv(TEAMS_CSV)[['team_name', 'division_name', 'conference_name']]


def load_rotations():
    global rotations
    rotations = pd.read_csv(ROTATIONS_CSV, index_col=0)[['teamName', 'rotation', 'firstName', 'lastName', 'role']]


def load_lineups():
    global lineups
    lineups = pd.read_csv(LINEUPS_CSV, index_col=0)[['teamName', 'battingOrder', 'firstName', 'lastName', 'pos']]
