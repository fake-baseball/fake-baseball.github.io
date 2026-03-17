"""Generate an individual team page (docs/teams/{TeamName}.html)."""
from pathlib import Path

from dominate.tags import *
from util import player_link, make_doc

_PITCHER_COLS  = ['Name', '#', 'Role', 'T', 'VEL', 'JNK', 'ACC', 'FLD', 'Arsenal', 'Age', 'Salary']
_POSITION_COLS = ['Name', '#', 'PP', '2P', 'B', 'POW', 'CON', 'SPD', 'FLD', 'ARM', 'Age', 'Salary']


def _roster_table(group, cols, link_col='Name'):
    t = table(border=0)
    with t:
        with thead():
            with tr():
                for col in cols:
                    th(col)
        with tbody():
            for _, row in group.iterrows():
                with tr():
                    for col in cols:
                        if col == link_col:
                            td(player_link(row['first_name'], row['last_name']))
                        else:
                            td(row[col])
    return t


def generate_team_page(team_name, roster, team_info):
    """
    team_name - string team name
    roster    - DataFrame of players on this team (rows from player_info, reset_index'd)
    """
    pitchers = roster[roster['ppos'] == 'P'].sort_values(['last_name', 'first_name']).copy()
    position = roster[roster['ppos'] != 'P'].sort_values(['last_name', 'first_name']).copy()

    # Rename columns to display labels
    for df in (pitchers, position):
        df.rename(columns={
            'jersey':     '#',
            'age':        'Age',
            'role':       'Role',
            'ppos':       'PP',
            'spos':       '2P',
            'throws':     'T',
            'bats':       'B',
            'salary':     'Salary',
            'power':      'POW',
            'contact':    'CON',
            'speed':      'SPD',
            'fielding':   'FLD',
            'arm':        'ARM',
            'velocity':   'VEL',
            'junk':       'JNK',
            'accuracy':   'ACC',
            'pitchTypes': 'Arsenal',
        }, inplace=True)
        df['Name'] = None  # placeholder; _roster_table uses first_name/last_name directly

    doc = make_doc(team_name)
    with doc:
        h1(team_name)
        p(f"{team_info['conference_name']} - {team_info['division_name']}")
        h2("Pitchers")
        _roster_table(pitchers, _PITCHER_COLS)
        h2("Position Players")
        _roster_table(position, _POSITION_COLS)

    slug = team_name.replace(' ', '')
    Path(f"docs/teams/{slug}.html").write_text(str(doc))
