"""Generate an individual team page (docs/teams/{TeamName}.html)."""
from pathlib import Path

from dominate.tags import *
import batting as bat_module
import pitching as pit_module
from constants import CURRENT_SEASON
from data import teams as teams_data
from data import players
from registry import REGISTRY
from util import make_doc, fmt_ip, fmt_round, fmt_rdiff, render_table

_PITCHER_COLS  = ['Name', '#', 'role', 'throws', 'velocity', 'junk', 'accuracy', 'fielding', 'Arsenal', 'age', 'Salary']
_POSITION_COLS = ['Name', '#', 'pos1', 'pos2', 'bats', 'power', 'contact', 'speed', 'fielding', 'arm', 'age', 'Salary']


def _batter_stats(first, last):
    """Returns dict of season 21 stats, or None if no games played."""
    df = bat_module.stats
    mask = ((df['First Name'] == first) & (df['Last Name'] == last) &
            (df['stat_type'] == 'season') & (df['season'] == CURRENT_SEASON))
    rows = df[mask]
    if rows.empty:
        return None
    row = rows.iloc[0]
    def _fmt(stat, val):
        m = REGISTRY[stat]
        return fmt_round(val, m['decimal_places'], m['leading_zero'])
    # FOR CLAUDE: use registry formatting everywhere, don't just blindly assume int
    return {
        'AVG': _fmt('avg', row['avg']),
        'HR':  int(row['hr']),
        'RBI': int(row['rbi']),
        'OPS': _fmt('ops', row['ops']),
        'WAR': _fmt('war', row['war']),
    }


def _pitcher_stats(first, last):
    """Returns dict of season 21 pitcher stats, or None if no games played."""
    df = pit_module.stats
    mask = ((df['First Name'] == first) & (df['Last Name'] == last) &
            (df['stat_type'] == 'season') & (df['season'] == CURRENT_SEASON))
    rows = df[mask]
    if rows.empty:
        return None
    row = rows.iloc[0]
    def _fmt(stat, val):
        m = REGISTRY[stat]
        return fmt_round(val, m['decimal_places'], m['leading_zero'])
    # FOR CLAUDE: use registry formatting everywhere, don't just blindly assume int
    return {
        'W-L': f"{int(row['p_w'])}-{int(row['p_l'])}",
        'SV':  int(row['p_sv']),
        'ERA': _fmt('p_era', row['p_era']),
        'IP':  fmt_ip(row['p_ip']),
        'K':   int(row['p_k']),
        'WAR': _fmt('p_war', row['p_war']),
    }


def _pitcher_table(players_list, stat_rows):
    """Transposed pitcher stat table. players_list: list of (col_label, first, last)."""
    data = [
        (label, first, last, _pitcher_stats(first, last))
        for label, first, last in players_list
    ]
    with table(border=0):
        with thead():
            with tr():
                th()
                for _, first, last, _ in data:
                    th(f"{first} {last}")
            with tr():
                th()
                for label, _, _, _ in data:
                    th(label)
        with tbody():
            for stat in stat_rows:
                with tr():
                    th(stat)
                    for _, _, _, s21 in data:
                        td(s21[stat] if s21 is not None else '-')


# FOR CLAUDE: this function is unused, remove it.
def _pitcher_statline(first, last):
    df = pit_module.stats
    mask = (df['First Name'] == first) & (df['Last Name'] == last) & (df['stat_type'] == 'season')
    rows = df[mask]
    if rows.empty:
        return None
    row = rows.loc[rows['season'].idxmax()]
    def _fmt(stat, val):
        m = REGISTRY[stat]
        return fmt_round(val, m['decimal_places'], m['leading_zero'])
    era = _fmt('p_era', row['p_era'])
    war = _fmt('p_war', row['p_war'])
    ip  = fmt_ip(row['p_ip'])
    return f"{int(row['p_w'])}-{int(row['p_l'])}, {era} ERA, {ip} IP, {int(row['p_k'])} K, {war} WAR"



# FOR CLAUDE: (kinda a big overarching thing I just realized) investigate any discrepancy 
# between the column names for "First Name" and "Last Name". From loading, we should fix it
# to ALWAYS be first_name and last_name so we NEVER have to do any renaming ANYWHERE within
# the core or display logic. You can add them as stats to src/registry.py if it's not there
def _roster_table(group, cols, link_col='Name'):
    df = group.rename(columns={'first_name': 'First Name', 'last_name': 'Last Name'}).copy()
    df['player'] = ''
    display_cols = ['player' if c == link_col else c for c in cols]
    render_table(df[display_cols + ['First Name', 'Last Name']], depth=2)


def generate_team_page(team_name, roster, team_info):
    """
    team_name - string team name
    roster    - DataFrame of players on this team (rows from player_info, reset_index'd)
    """
    slug     = team_name.replace(' ', '')
    pitchers = roster[roster['ppos'] == 'P'].sort_values(['last_name', 'first_name']).copy()
    position = roster[roster['ppos'] != 'P'].sort_values(['last_name', 'first_name']).copy()

    # Rename columns to REGISTRY keys (or display labels for non-REGISTRY columns)
    # FOR CLAUDE: ensure that BEFORE we get to this point (i.e. in src/data/*.py), the
    # columns have already been renamed appropriately. Then, src/registry.py can contain
    # the display column name which is handled by render_table
    for df in (pitchers, position):
        df.rename(columns={
            'jersey':     '#',
            'ppos':       'pos1',
            'spos':       'pos2',
            'salary':     'Salary',
            'pitchTypes': 'Arsenal',
        }, inplace=True)
        df['Name'] = None  # placeholder; _roster_table uses first_name/last_name directly

    rotation = teams_data.rotations[teams_data.rotations['teamName'] == team_name].sort_values('rotation')
    lineup   = teams_data.lineups[teams_data.lineups['teamName'] == team_name].sort_values('battingOrder')

    lineup_names   = set(zip(lineup['firstName'], lineup['lastName']))
    rotation_names = set(zip(rotation['firstName'], rotation['lastName']))

    bench = roster[
        (roster['ppos'] != 'P') &
        ~roster.apply(lambda r: (r['first_name'], r['last_name']) in lineup_names, axis=1)
    ].sort_values(['last_name', 'first_name'])

    bullpen = roster[
        (roster['ppos'] == 'P') &
        ~roster.apply(lambda r: (r['first_name'], r['last_name']) in rotation_names, axis=1)
    ]

    doc = make_doc(team_name, css='../../style.css')
    with doc:
        h1(team_name)
        p(f"{team_info['conference_name']} - {team_info['division_name']}")
        h2("Starters")
        h3("Lineup")
        players_data = [
            (row['firstName'], row['lastName'], row['pos'],
             _batter_stats(row['firstName'], row['lastName']))
            for _, row in lineup.iterrows()
        ]
        # FOR CLAUDE: abstract this into a _lineup_table function like you did _pitcher_table
        stat_rows = ['AVG', 'HR', 'RBI', 'OPS', 'WAR']
        with table(border=0):
            with thead():
                with tr():
                    th()
                    for first, last, pos, _ in players_data:
                        th(f"{first} {last}")
                with tr():
                    th()
                    for _, _, pos, _ in players_data:
                        th(pos)
            with tbody():
                for stat in stat_rows:
                    with tr():
                        th(stat)
                        for _, _, _, stats in players_data:
                            td(stats[stat] if stats is not None else '-')
        h3("Rotation")
        rotation_list = [
            (f"SP{int(row['rotation'])}", row['firstName'], row['lastName'])
            for _, row in rotation.iterrows()
        ]
        _pitcher_table(rotation_list, ['W-L', 'ERA', 'IP', 'K', 'WAR'])
        h3("Bullpen")
        _ROLE_ORDER = {'CL': 0, 'RP': 1, 'SP/RP': 2}
        bp_sorted = bullpen.sort_values('role', key=lambda s: s.map(lambda r: _ROLE_ORDER.get(r, 99)))
        bullpen_list = [
            (row['role'], row['first_name'], row['last_name'])
            for _, row in bp_sorted.iterrows()
        ]
        _pitcher_table(bullpen_list, ['SV', 'ERA', 'IP', 'K', 'WAR'])
        h2("Roster")
        h3("Pitchers")
        _roster_table(pitchers, _PITCHER_COLS)
        h3("Position Players")
        _roster_table(position, _POSITION_COLS)

        h2("History")
        team_standings = teams_data.standings[teams_data.standings['teamName'] == team_name].sort_values('Season').copy()
        team_standings['Pct'] = (team_standings['gamesWon'] / (team_standings['gamesWon'] + team_standings['gamesLost'])).map(lambda v: f"{v:.3f}".lstrip('0'))
        team_standings['Diff'] = team_standings['runsFor'] - team_standings['runsAgainst']
        total_w  = team_standings['gamesWon'].sum()
        total_l  = team_standings['gamesLost'].sum()
        total_rs = team_standings['runsFor'].sum()
        total_ra = team_standings['runsAgainst'].sum()
        total_pct  = f"{total_w / (total_w + total_l):.3f}".lstrip('0')
        total_diff = fmt_rdiff(total_rs - total_ra)
        p(f"Lifetime: {total_w}-{total_l} ({total_pct}), {total_rs} RS, {total_ra} RA, {total_diff} Diff")
        # FOR CLAUDE: use render_table (after column name adjustments and registry refactors are done)
        with table(border=0):
            with thead():
                with tr():
                    for col in ['Season', 'W', 'L', 'Pct', 'RS', 'RA', 'Diff']:
                        th(col)
            with tbody():
                for _, row in team_standings.iterrows():
                    with tr():
                        td(a(row['Season'], href=f"{int(row['Season'])}.html"))
                        td(row['gamesWon'])
                        td(row['gamesLost'])
                        td(row['Pct'])
                        td(row['runsFor'])
                        td(row['runsAgainst'])
                        td(fmt_rdiff(row['Diff']))

    Path(f"docs/teams/{slug}/index.html").write_text(str(doc))
