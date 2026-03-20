"""Generate an individual team page (docs/teams/{TeamName}.html)."""
from pathlib import Path

from dominate.tags import *
import batting as bat_module
import pitching as pit_module
import projections as proj_module
import pit_projections as pit_proj_module
from data import teams as teams_data
from data import players
from stats_meta import BATTING_STATS, BASERUNNING_STATS, PITCHING_STATS

_ALL_BAT = {**BATTING_STATS, **BASERUNNING_STATS}
from util import player_link, make_doc, fmt_ip, fmt_round, fmt_rdiff

_PITCHER_COLS  = ['Name', '#', 'Role', 'T', 'VEL', 'JNK', 'ACC', 'FLD', 'Arsenal', 'Age', 'Salary']
_POSITION_COLS = ['Name', '#', 'PP', '2P', 'B', 'POW', 'CON', 'SPD', 'FLD', 'ARM', 'Age', 'Salary']


def _batter_stats(first, last):
    """Returns dict of formatted stats for the most recent season, or None."""
    df = bat_module.stats
    mask = (df['First Name'] == first) & (df['Last Name'] == last) & (df['stat_type'] == 'season')
    rows = df[mask]
    if rows.empty:
        return None
    row = rows.loc[rows['Season'].idxmax()]
    def _fmt(stat, val):
        m = BATTING_STATS[stat]
        return fmt_round(val, m['decimal_places'], m['leading_zero'])
    return {
        'AVG': _fmt('AVG', row['AVG']),
        'HR':  int(row['HR']),
        'RBI': int(row['RBI']),
        'OPS': _fmt('OPS', row['OPS']),
        'WAR': _fmt('WAR', row['WAR']),
    }


def _pitcher_statline(first, last):
    df = pit_module.stats
    mask = (df['First Name'] == first) & (df['Last Name'] == last) & (df['stat_type'] == 'season')
    rows = df[mask]
    if rows.empty:
        return None
    row = rows.loc[rows['Season'].idxmax()]
    def _fmt(stat, val):
        m = PITCHING_STATS[stat]
        return fmt_round(val, m['decimal_places'], m['leading_zero'])
    era = _fmt('ERA', row['ERA'])
    war = _fmt('WAR', row['WAR'])
    ip  = fmt_ip(row['IP_true'])
    return f"{int(row['W'])}-{int(row['L'])}, {era} ERA, {ip} IP, {int(row['K'])} K, {war} WAR"


_LINEUP_HEADERS = ['#', 'Pos', 'Name', 'B', 'Age', 'POW', 'CON', 'SPD', 'FLD', 'ARM',
                   'PA', 'xPA', 'AVG', 'xAVG', 'HR', 'xHR', 'SB', 'xSB', 'OPS', 'xOPS',
                   'wRC+', 'xwRC+', 'BABIP', 'xBABIP', 'WAR', 'xWAR']

# (actual stat key, proj row key, stat meta key for formatting)
_LINEUP_PAIRED = [
    ('PA',    'proj_pa',  'PA'),
    ('AVG',   'xAVG',    'AVG'),
    ('HR',    'xHR',     'HR'),
    ('SB',    'xSB',     'SB'),
    ('OPS',   'xOPS',    'OPS'),
    ('wRC+',  'xwRC+',   'wRC+'),
    ('BABIP', 'xBABIP',  'BABIP'),
    ('WAR',   'xWAR',    'WAR'),
]


def _lineup_table(lineup, bench):
    def _fmt(stat_key, val):
        m = _ALL_BAT[stat_key]
        return fmt_round(val, m['decimal_places'], m['leading_zero'], m['percentage'])

    proj_rows = proj_module.compute_all()
    proj_by_player = {(r['first'], r['last']): r for r in proj_rows}

    df = bat_module.stats
    t = table(border=1)
    with t:
        with thead():
            with tr():
                for col in _LINEUP_HEADERS:
                    th(col)
        with tbody():
            for _, row in lineup.iterrows():
                first, last = row['firstName'], row['lastName']
                pi   = players.player_info.loc[(first, last)] if (first, last) in players.player_info.index else None
                mask = ((df['First Name'] == first) & (df['Last Name'] == last) &
                        (df['stat_type'] == 'season') & (df['Season'] == 20))
                s20  = df[mask].iloc[0] if not df[mask].empty else None
                proj = proj_by_player.get((first, last))
                with tr():
                    td(row['battingOrder'])
                    td(row['pos'])
                    td(f"{first} {last}")
                    td(pi['bats']     if pi is not None else '')
                    td(pi['age']      if pi is not None else '')
                    td(pi['power']    if pi is not None else '')
                    td(pi['contact']  if pi is not None else '')
                    td(pi['speed']    if pi is not None else '')
                    td(pi['fielding'] if pi is not None else '')
                    td(pi['arm']      if pi is not None else '')
                    for actual_key, proj_key, fmt_key in _LINEUP_PAIRED:
                        td(_fmt(fmt_key, s20[actual_key])  if s20  is not None else '-')
                        td(_fmt(fmt_key, proj[proj_key])   if proj is not None else '-')
            for _, row in bench.iterrows():
                first, last = row['first_name'], row['last_name']
                pi   = players.player_info.loc[(first, last)] if (first, last) in players.player_info.index else None
                mask = ((df['First Name'] == first) & (df['Last Name'] == last) &
                        (df['stat_type'] == 'season') & (df['Season'] == 20))
                s20  = df[mask].iloc[0] if not df[mask].empty else None
                proj = proj_by_player.get((first, last))
                with tr():
                    td('BN')
                    td(row['ppos'])
                    td(f"{first} {last}")
                    td(pi['bats']     if pi is not None else '')
                    td(pi['age']      if pi is not None else '')
                    td(pi['power']    if pi is not None else '')
                    td(pi['contact']  if pi is not None else '')
                    td(pi['speed']    if pi is not None else '')
                    td(pi['fielding'] if pi is not None else '')
                    td(pi['arm']      if pi is not None else '')
                    for actual_key, proj_key, fmt_key in _LINEUP_PAIRED:
                        td(_fmt(fmt_key, s20[actual_key])  if s20  is not None else '-')
                        td(_fmt(fmt_key, proj[proj_key])   if proj is not None else '-')
    return t


_ROTATION_HEADERS = ['#', 'Name', 'Role', 'T', 'Age', 'VEL', 'JNK', 'ACC', 'FLD',
                     'IP', 'xIP', 'ERA', 'xRA9',
                     'K%', 'xK%', 'BB%', 'xBB%', 'BABIP', 'xBABIP', 'WAR', 'xWAR']

# (actual pitching.stats key, proj row key, PITCHING_STATS meta key or None for special)
_ROTATION_PAIRED = [
    ('IP_true', 'proj_ip',  None),    # special: fmt_ip actual, .1f proj
    ('ERA',     'xRA9',    'ERA'),
    ('K%',      'xK%',     'K%'),
    ('BB%',     'xBB%',    'BB%'),
    ('BABIP',   'xBABIP',  'BABIP'),
    ('WAR',     'xWAR',    'WAR'),
]


_ROLE_ORDER = {'SP': 0, 'SP/RP': 1, 'RP': 2, 'CL': 3}


def _rotation_table(rotation, bullpen):
    def _fmt_pit(meta_key, val):
        m = PITCHING_STATS[meta_key]
        return fmt_round(val, m['decimal_places'], m['leading_zero'], m['percentage'])

    def _pit_row(num, first, last):
        pi   = players.player_info.loc[(first, last)] if (first, last) in players.player_info.index else None
        mask = ((df['First Name'] == first) & (df['Last Name'] == last) &
                (df['stat_type'] == 'season') & (df['Season'] == 20))
        s20  = df[mask].iloc[0] if not df[mask].empty else None
        proj = proj_by_player.get((first, last))
        with tr():
            td(num)
            td(f"{first} {last}")
            td(pi['role']     if pi is not None else '')
            td(pi['throws']   if pi is not None else '')
            td(pi['age']      if pi is not None else '')
            td(pi['velocity'] if pi is not None else '')
            td(pi['junk']     if pi is not None else '')
            td(pi['accuracy'] if pi is not None else '')
            td(pi['fielding'] if pi is not None else '')
            for actual_key, proj_key, meta_key in _ROTATION_PAIRED:
                if actual_key == 'IP_true':
                    td(fmt_ip(s20['IP_true'])       if s20  is not None else '-')
                    td(f"{proj['proj_ip']:.1f}"     if proj is not None else '-')
                else:
                    td(_fmt_pit(meta_key, s20[actual_key])  if s20  is not None else '-')
                    td(_fmt_pit(meta_key, proj[proj_key])   if proj is not None else '-')

    proj_rows = pit_proj_module.compute_all()
    proj_by_player = {(r['first'], r['last']): r for r in proj_rows}

    df = pit_module.stats
    t = table(border=1)
    with t:
        with thead():
            with tr():
                for col in _ROTATION_HEADERS:
                    th(col)
        with tbody():
            for _, row in rotation.iterrows():
                _pit_row(row['rotation'], row['firstName'], row['lastName'])
            bp_sorted = bullpen.sort_values(
                'role', key=lambda s: s.map(lambda r: _ROLE_ORDER.get(r, 99))
            )
            for _, row in bp_sorted.iterrows():
                _pit_row('BP', row['first_name'], row['last_name'])
    return t


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
                            td(player_link(row['first_name'], row['last_name'], prefix='../../players/'))
                        else:
                            td(row[col])
    return t


def generate_team_page(team_name, roster, team_info):
    """
    team_name - string team name
    roster    - DataFrame of players on this team (rows from player_info, reset_index'd)
    """
    slug     = team_name.replace(' ', '')
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
        with ol():
            for _, row in lineup.iterrows():
                first, last = row['firstName'], row['lastName']
                stats = _batter_stats(first, last)
                text = f"{first} {last} {row['pos']}"
                if stats:
                    text += f" - {stats['AVG']} AVG, {stats['HR']} HR, {stats['RBI']} RBI, {stats['OPS']} OPS, {stats['WAR']} WAR"
                else:
                    text += " (R)"
                li(text)
        players_data = [
            (row['firstName'], row['lastName'], row['pos'], _batter_stats(row['firstName'], row['lastName']))
            for _, row in lineup.iterrows()
        ]
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
                            td(stats[stat] if stats else '(R)')
        _lineup_table(lineup, bench)
        h3("Rotation")
        with ol():
            for _, row in rotation.iterrows():
                first, last = row['firstName'], row['lastName']
                statline = _pitcher_statline(first, last)
                text = f"{first} {last}"
                text += f" - {statline}" if statline else " (R)"
                li(text)
        _rotation_table(rotation, bullpen)
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
