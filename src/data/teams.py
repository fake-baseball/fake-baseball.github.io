import pandas as pd

from data.sources import TEAMS_CSV

teams = None


def load_teams():
    global teams
    teams = pd.read_csv(TEAMS_CSV)[['team_name', 'division_name', 'conference_name']]
