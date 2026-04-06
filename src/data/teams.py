import pandas as pd

from constants import CURRENT_SEASON
from data.sources import TEAMS_CSV, STANDINGS_CSV, SCHEDULE20_CSV
from data.sources import season21_latest, read_s21

teams      = None
rotations  = None
lineups    = None
standings  = None
season_map = None  # maps internal season ID -> sequential season number (1, 2, 3...)
schedule20 = None  # season 20 schedule (kept for backward compatibility)
schedules  = {}    # {season_num: schedule_df} for all seasons with schedule data

# FOR_CLAUDE: we should add columns encountered here as stats in registry.py, so that
# down the line we can use `render_table` to format things correctly, and so that there's
# consistency between columns things exist. Note that there's discrepancies between how the
# same piece of data can be found (for example: "First Name", "firstName", and "first_name")
# By tying it to the registry, we can ensure all column names are the same. Here, in src/data
# we rename columns at load-time to the internally expected names by the registry to get ahead
# of any data wrangling nightmares. Remember to follow the naming convention when there is
# overloaded stats (e.g. `r` would be split up as `p_r` (pitcher runs allowed), `b_r` (batter runs scored),
# and `t_r` (team runs scored). Please do another pass through all data-loading files as well
# to ensure this convention is met.

def load_teams():
    global teams
    teams = pd.read_csv(TEAMS_CSV)[['team_name', 'abbr', 'division_name', 'conference_name']]


def load_rotations():
    global rotations
    df = read_s21(season21_latest('rotations'))
    rotations = df.rename(columns={'slot': 'rotation'})[['teamName', 'rotation', 'firstName', 'lastName', 'role']]


def load_lineups():
    global lineups
    df = read_s21(season21_latest('lineups'))
    lineups = df[df['lineupType'] == 'DH'][['teamName', 'battingOrder', 'firstName', 'lastName', 'pos']].copy()


def load_standings():
    global standings, season_map
    df = pd.read_csv(STANDINGS_CSV, index_col=0)[['seasonID', 'teamName', 'gamesWon', 'gamesLost', 'runsFor', 'runsAgainst']]
    season_ids = sorted(df['seasonID'].unique())
    season_map = {sid: i + 1 for i, sid in enumerate(season_ids)}
    df['Season'] = df['seasonID'].map(season_map)

    s21 = _standings_from_schedule21()
    if s21 is not None:
        df = pd.concat([df, s21], ignore_index=True)

    teams_df = pd.read_csv(TEAMS_CSV)[['team_name', 'division_name', 'conference_name']]
    df = df.merge(teams_df, left_on='teamName', right_on='team_name', how='left').drop(columns='team_name')

    chunks = []
    for _, group in df.groupby(['Season', 'division_name']):
        group = group.copy()
        group['run_diff'] = group['runsFor'] - group['runsAgainst']
        group_sorted = group.sort_values(['gamesWon', 'run_diff'], ascending=[False, False])
        leader = group_sorted.iloc[0]
        max_w, min_l = leader['gamesWon'], leader['gamesLost']
        group['GB'] = ((max_w - group['gamesWon']) + (group['gamesLost'] - min_l)) / 2
        chunks.append(group)
    df = pd.concat(chunks)
    standings = df


def _standings_from_schedule21():
    """Compute season 21 W/L/RF/RA from the schedule file."""
    path = season21_latest('schedule')
    if path is None:
        return None
    sched = read_s21(path)
    # Only completed games (non-null scores)
    played = sched.dropna(subset=['home_score', 'away_score']).copy()
    if played.empty:
        return None
    played['home_score'] = played['home_score'].astype(int)
    played['away_score'] = played['away_score'].astype(int)

    records = {}
    for _, row in played.iterrows():
        ht, at = row['home_team'], row['away_team']
        hs, as_ = row['home_score'], row['away_score']
        if ht not in records:
            records[ht] = {'gamesWon':0,'gamesLost':0,'runsFor':0,'runsAgainst':0}
        if at not in records:
            records[at] = {'gamesWon':0,'gamesLost':0,'runsFor':0,'runsAgainst':0}
        records[ht]['runsFor']     += hs
        records[ht]['runsAgainst'] += as_
        records[at]['runsFor']     += as_
        records[at]['runsAgainst'] += hs
        if hs > as_:
            records[ht]['gamesWon']  += 1
            records[at]['gamesLost'] += 1
        else:
            records[at]['gamesWon']  += 1
            records[ht]['gamesLost'] += 1

    rows = [{'seasonID': 71, 'teamName': t, 'Season': CURRENT_SEASON, **v}
            for t, v in records.items()]
    return pd.DataFrame(rows)


def load_schedule20():
    global schedule20, schedules
    df = pd.read_csv(SCHEDULE20_CSV)
    df.columns = df.columns.str.strip()
    schedule20 = df[['Game #', 'Day', 'Home Team', 'Home Score', 'Away Score', 'Away Team']]
    schedules[20] = schedule20
    _load_schedule21()


def _load_schedule21():
    """Load the most recent season 21 schedule into schedules[21]."""
    path = season21_latest('schedule')
    if path is None:
        return
    raw = read_s21(path)
    raw.columns = raw.columns.str.strip()
    if raw.empty:
        return
    all_games = raw.rename(columns={
        'home_team':  'Home Team',
        'home_score': 'Home Score',
        'away_score': 'Away Score',
        'away_team':  'Away Team',
    }).copy()
    played_mask = all_games['Home Score'].notna() & all_games['Away Score'].notna()
    all_games.loc[played_mask, 'Home Score'] = all_games.loc[played_mask, 'Home Score'].astype(int)
    all_games.loc[played_mask, 'Away Score'] = all_games.loc[played_mask, 'Away Score'].astype(int)
    all_games['Game #'] = range(1, len(all_games) + 1)
    all_games['Day']    = None
    schedules[CURRENT_SEASON] = all_games[['Game #', 'Day', 'Home Team', 'Home Score', 'Away Score', 'Away Team']]
