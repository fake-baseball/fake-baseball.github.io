import pandas as pd

from constants import CURRENT_SEASON
from data.sources import TEAMS_CSV, STANDINGS_CSV, SCHEDULE20_CSV
from data.sources import season21_latest, read_s21
from data.data_utils import team_abbr_to_id

teams      = None
team_info  = None  # indexed by team_id; columns: team_name, abbr, division_name, conference_name
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
    global teams, team_info
    teams = pd.read_csv(TEAMS_CSV)[['team_name', 'abbr', 'division_name', 'conference_name']]
    teams['team_id'] = teams['abbr'].map(team_abbr_to_id)
    team_info = teams.set_index('team_id')[['team_name', 'abbr', 'division_name', 'conference_name']]


def _to_team_id(series):
    """Map a Series of full team names to team_id. Requires load_teams() to have run."""
    lookup = team_info.reset_index().set_index('team_name')['team_id']
    return series.map(lookup)


def load_rotations():
    global rotations
    df = read_s21(season21_latest('rotations'))
    df = df.rename(columns={'slot': 'rotation', 'firstName': 'first_name', 'lastName': 'last_name'})
    df['team_id'] = _to_team_id(df['teamName'])
    rotations = df[['team_id', 'rotation', 'first_name', 'last_name', 'role']]


def load_lineups():
    global lineups
    df = read_s21(season21_latest('lineups'))
    df = df[df['lineupType'] == 'DH'].copy()
    df = df.rename(columns={'battingOrder': 'batting_order', 'firstName': 'first_name', 'lastName': 'last_name'})
    df['team_id'] = _to_team_id(df['teamName'])
    lineups = df[['team_id', 'batting_order', 'first_name', 'last_name', 'pos']].copy()


def load_standings():
    global standings, season_map
    df = pd.read_csv(STANDINGS_CSV, index_col=0)[['seasonID', 'teamName', 'gamesWon', 'gamesLost', 'runsFor', 'runsAgainst']]
    season_ids = sorted(df['seasonID'].unique())
    season_map = {sid: i + 1 for i, sid in enumerate(season_ids)}
    df['Season'] = df['seasonID'].map(season_map)

    s21 = _standings_from_schedule21()
    if s21 is not None:
        df = pd.concat([df, s21], ignore_index=True)

    # Merge in division/conference from team_info, then convert to team_id
    df = df.merge(
        team_info[['team_name', 'division_name', 'conference_name']].reset_index(),
        left_on='teamName', right_on='team_name', how='left'
    ).drop(columns='team_name')

    chunks = []
    for _, group in df.groupby(['Season', 'division_name']):
        group = group.copy()
        group['run_diff'] = group['runsFor'] - group['runsAgainst']
        group['t_pct'] = group['gamesWon'] / (group['gamesWon'] + group['gamesLost'])
        group_sorted = group.sort_values(['t_pct', 'run_diff'], ascending=[False, False])
        leader = group_sorted.iloc[0]
        max_w, min_l = leader['gamesWon'], leader['gamesLost']
        group['GB'] = ((max_w - group['gamesWon']) + (group['gamesLost'] - min_l)) / 2
        chunks.append(group)
    df = pd.concat(chunks)
    df['team_id'] = _to_team_id(df['teamName'])
    standings = df


def _standings_from_schedule21():
    """Compute season 21 W/L/RF/RA from the schedule file."""
    path = season21_latest('schedule')
    if path is None:
        return None
    sched = read_s21(path)
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
    df = df[['Game #', 'Day', 'Home Team', 'Home Score', 'Away Score', 'Away Team']].copy()
    df['home_team_id'] = _to_team_id(df['Home Team'])
    df['away_team_id'] = _to_team_id(df['Away Team'])
    schedule20 = df
    schedules[20] = df
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
    df = raw.rename(columns={
        'home_team':  'Home Team',
        'home_score': 'Home Score',
        'away_score': 'Away Score',
        'away_team':  'Away Team',
    }).copy()
    played_mask = df['Home Score'].notna() & df['Away Score'].notna()
    df.loc[played_mask, 'Home Score'] = df.loc[played_mask, 'Home Score'].astype(int)
    df.loc[played_mask, 'Away Score'] = df.loc[played_mask, 'Away Score'].astype(int)
    df['Game #'] = range(1, len(df) + 1)
    df['Day']    = None
    df['home_team_id'] = _to_team_id(df['Home Team'])
    df['away_team_id'] = _to_team_id(df['Away Team'])
    schedules[CURRENT_SEASON] = df[['Game #', 'Day', 'Home Team', 'Home Score', 'Away Score', 'Away Team', 'home_team_id', 'away_team_id']]
