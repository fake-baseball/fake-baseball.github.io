import pandas as pd

from data.sources import TEAMS_CSV, ROTATIONS_CSV, LINEUPS_CSV, STANDINGS_CSV

teams      = None
rotations  = None
lineups    = None
standings  = None
season_map = None  # maps internal season ID -> sequential season number (1, 2, 3...)


def load_teams():
    global teams
    teams = pd.read_csv(TEAMS_CSV)[['team_name', 'abbr', 'division_name', 'conference_name']]


def load_rotations():
    global rotations
    rotations = pd.read_csv(ROTATIONS_CSV, index_col=0)[['teamName', 'rotation', 'firstName', 'lastName', 'role']]


def load_lineups():
    global lineups
    lineups = pd.read_csv(LINEUPS_CSV, index_col=0)[['teamName', 'battingOrder', 'firstName', 'lastName', 'pos']]


def load_standings():
    global standings, season_map
    df = pd.read_csv(STANDINGS_CSV, index_col=0)[['seasonID', 'teamName', 'gamesWon', 'gamesLost', 'runsFor', 'runsAgainst']]
    season_ids = sorted(df['seasonID'].unique())
    season_map = {sid: i + 1 for i, sid in enumerate(season_ids)}
    df['Season'] = df['seasonID'].map(season_map)

    teams_df = pd.read_csv(TEAMS_CSV)[['team_name', 'division_name', 'conference_name']]
    df = df.merge(teams_df, left_on='teamName', right_on='team_name', how='left').drop(columns='team_name')

    chunks = []
    for _, group in df.groupby(['Season', 'division_name']):
        group = group.copy()
        max_w = group['gamesWon'].max()
        min_l = group.loc[group['gamesWon'] == max_w, 'gamesLost'].min()
        group['GB'] = ((max_w - group['gamesWon']) + (group['gamesLost'] - min_l)) / 2
        chunks.append(group)
    df = pd.concat(chunks)
    standings = df
