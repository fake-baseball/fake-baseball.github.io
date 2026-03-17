import pandas as pd

from data.sources import TEAMS_CSV


def load_teams():
    return pd.read_csv(TEAMS_CSV)[['team_name', 'division_name', 'conference_name']]
