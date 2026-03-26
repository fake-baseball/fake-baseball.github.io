"""Generate an individual team page (docs/teams/{TeamName}.html)."""
from pathlib import Path

from dominate.tags import *
import batting as bat_module
import pitching as pit_module
import projections as proj_module
import pit_projections as pit_proj_module
from data import teams as teams_data
from data import players
from registry import REGISTRY
from util import make_doc, fmt_ip, fmt_round, fmt_rdiff, render_table

_PITCHER_COLS  = ['Name', '#', 'role', 'throws', 'velocity', 'junk', 'accuracy', 'fielding', 'Arsenal', 'age', 'Salary']
_POSITION_COLS = ['Name', '#', 'pos1', 'pos2', 'bats', 'power', 'contact', 'speed', 'fielding', 'arm', 'age', 'Salary']


def _batter_stats(first, last):
    """Returns dict of formatted stats for the most recent season, or None."""
    df = bat_module.stats
    mask = (df['First Name'] == first) & (df['Last Name'] == last) & (df['stat_type'] == 'season')
    rows = df[mask]
    if rows.empty:
        return None
    row = rows.loc[rows['season'].idxmax()]
    def _fmt(stat, val):
        m = REGISTRY[stat]
        return fmt_round(val, m['decimal_places'], m['leading_zero'])
    return {
        'AVG': _fmt('avg', row['avg']),
        'HR':  int(row['hr']),
        'RBI': int(row['rbi']),
        'OPS': _fmt('ops', row['ops']),
        'WAR': _fmt('war', row['war']),
    }


def _batter_proj(first, last, proj_by_player):
    """Returns dict of formatted projected stats, or None."""
    proj = proj_by_player.get((first, last))
    if proj is None:
        return None
    def _fmt(stat, val):
        m = REGISTRY[stat]
        return fmt_round(val, m['decimal_places'], m['leading_zero'])
    return {
        'AVG': _fmt('avg', proj['xAVG']),
        'HR':  int(round(proj['xHR'])),
        'RBI': int(round(proj['xRBI'])),
        'OPS': _fmt('ops', proj['xOPS']),
        'WAR': _fmt('war', proj['xWAR']),
    }


def _pitcher_s20(first, last):
    """Returns dict of Season 20 pitcher stats, or None."""
    df = pit_module.stats
    mask = ((df['First Name'] == first) & (df['Last Name'] == last) &
            (df['stat_type'] == 'season') & (df['season'] == 20))
    rows = df[mask]
    if rows.empty:
        return None
    row = rows.iloc[0]
    def _fmt(stat, val):
        m = REGISTRY[stat]
        return fmt_round(val, m['decimal_places'], m['leading_zero'])
    return {
        'W-L': f"{int(row['p_w'])}-{int(row['p_l'])}",
        'SV':  int(row['p_sv']),
        'ERA': _fmt('p_era', row['p_era']),
        'IP':  fmt_ip(row['p_ip']),
        'K':   int(row['p_k']),
        'WAR': _fmt('p_war', row['p_war']),
    }


def _pitcher_proj(first, last, proj_by_player):
    """Returns dict of formatted projected pitcher stats, or None."""
    proj = proj_by_player.get((first, last))
    if proj is None:
        return None
    def _fmt(stat, val):
        m = REGISTRY[stat]
        return fmt_round(val, m['decimal_places'], m['leading_zero'])
    return {
        'W-L': f"{int(round(proj['xW']))}-{int(round(proj['xL']))}",
        'SV':  int(round(proj['xSV'])),
        'ERA': _fmt('p_era', proj['xERA']),
        'IP':  f"{proj['proj_ip']:.1f}",
        'K':   int(round(proj['xK'])),
        'WAR': _fmt('p_war', proj['xWAR']),
    }


def _pitcher_table(players_list, stat_rows):
    """Transposed pitcher stat table. players_list: list of (col_label, first, last)."""
    proj_rows = pit_proj_module.compute_all()
    proj_by_player = {(r['first'], r['last']): r for r in proj_rows}
    data = [
        (label, first, last, _pitcher_s20(first, last), _pitcher_proj(first, last, proj_by_player))
        for label, first, last in players_list
    ]
    with table(border=0):
        with thead():
            with tr():
                th()
                for _, first, last, _, _ in data:
                    th(f"{first} {last}")
            with tr():
                th()
                for label, _, _, _, _ in data:
                    th(label)
        with tbody():
            for stat in stat_rows:
                with tr():
                    th(stat)
                    for _, _, _, s20, proj in data:
                        if s20 is None:
                            if proj is not None:
                                td(f"({proj[stat]})")
                            else:
                                td('-')
                        elif proj is not None:
                            td(f"{s20[stat]} ({proj[stat]})")
                        else:
                            td(s20[stat])


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
        proj_rows = proj_module.compute_all()
        proj_by_player = {(r['first'], r['last']): r for r in proj_rows}
        players_data = [
            (row['firstName'], row['lastName'], row['pos'],
             _batter_stats(row['firstName'], row['lastName']),
             _batter_proj(row['firstName'], row['lastName'], proj_by_player))
            for _, row in lineup.iterrows()
        ]
        _PROJ_STATS = {'AVG', 'HR', 'RBI', 'OPS', 'WAR'}
        stat_rows = ['AVG', 'HR', 'RBI', 'OPS', 'WAR']
        with table(border=0):
            with thead():
                with tr():
                    th()
                    for first, last, pos, _, _ in players_data:
                        th(f"{first} {last}")
                with tr():
                    th()
                    for _, _, pos, _, _ in players_data:
                        th(pos)
            with tbody():
                for stat in stat_rows:
                    with tr():
                        th(stat)
                        for _, _, _, stats, proj in players_data:
                            if stats is None:
                                if stat in _PROJ_STATS and proj is not None:
                                    td(f"({proj[stat]})")
                                else:
                                    td('-')
                            elif stat in _PROJ_STATS and proj is not None:
                                td(f"{stats[stat]} ({proj[stat]})")
                            else:
                                td(stats[stat])
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
