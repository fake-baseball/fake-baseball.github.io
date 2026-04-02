"""Generate an individual season page (docs/seasons/{n}.html)."""
from pathlib import Path

from dominate.tags import *

import pandas as pd

import pandas as pd
import league as lg
from constants import CURRENT_SEASON, num_games, SEASON_RANGE
from data import teams as teams_data
from util import make_doc, render_table, fmt_round, fmt_rdiff
from registry import REGISTRY
import leaders as ld
from seasons import split_records, h2h_records

_BAT_LEADER_STATS = ['war', 'hr', 'rbi', 'avg', 'ops', 'sb']
_PIT_LEADER_STATS = ['p_war', 'p_w', 'p_sv', 'p_era', 'p_k', 'p_whip']


def _fmt_gb(v):
    return '-' if v == 0 else f"{v:.1f}"


def _fmt_rec(w, l):
    return f"{w}-{l}"



def _standings_section(season_num):
    season_rows = teams_data.standings[teams_data.standings['Season'] == season_num].copy()
    if season_rows.empty:
        return
    season_rows['Pct'] = (
        season_rows['gamesWon'] / (season_rows['gamesWon'] + season_rows['gamesLost'])
    ).map(lambda v: f"{v:.3f}".lstrip('0'))
    season_rows['Diff'] = season_rows['runsFor'] - season_rows['runsAgainst']

    sched = teams_data.schedules.get(season_num)
    split = None
    if sched is not None:
        teams_df = teams_data.teams
        div_map  = teams_df.set_index('team_name')['division_name'].to_dict()
        conf_map = teams_df.set_index('team_name')['conference_name'].to_dict()
        winning_teams = set(
            season_rows[season_rows['gamesWon'] > season_rows['gamesLost']]['teamName']
        )
        split = split_records(sched, div_map, conf_map, winning_teams)

    extra_cols = ['L10', 'Div', 'Conf', 'Inter', '1-Run', 'Blowout', 'Home', 'Away', 'vs. >.500',
                  '1st Half', '2nd Half', 'SHO'] if split else []

    h2("Standings")
    for conf_name, conf_group in season_rows.groupby('conference_name', sort=False):
        h3(conf_name)
        for div_name, div_group in conf_group.groupby('division_name', sort=False):
            h4(div_name)
            # FOR CLAUDE: use render_table here too. You may want to add to
            # src/registry.py team-based stats (i.e. all the records) and use the
            # utility there (perhaps update to render_table required) to make sure
            # that the records are formatted as records properly
            # When you add team-based columns to src/registry.py, remember to follow
            # our rules for the names of the slugs (something like RA would be t_ra, for example)
            with table(border=0):
                with thead():
                    with tr():
                        for col in ['Team', 'W', 'L', 'Pct', 'GB', 'RS', 'RA', 'Diff'] + extra_cols:
                            th(col)
                with tbody():
                    for _, row in div_group.sort_values(['gamesWon', 'Diff'], ascending=[False, False]).iterrows():
                        slug = row['teamName'].replace(' ', '')
                        with tr():
                            td(a(row['teamName'], href=f"../teams/{slug}/{season_num}.html"))
                            td(row['gamesWon'])
                            td(row['gamesLost'])
                            td(row['Pct'])
                            td(_fmt_gb(row['GB']))
                            td(row['runsFor'])
                            td(row['runsAgainst'])
                            td(fmt_rdiff(row['Diff']))
                            if split:
                                rec = split[row['teamName']]
                                td(_fmt_rec(*rec['last10']))
                                td(_fmt_rec(*rec['div']))
                                td(_fmt_rec(*rec['conf']))
                                td(_fmt_rec(*rec['inter']))
                                td(_fmt_rec(*rec['one_run']))
                                td(_fmt_rec(*rec['blowout']))
                                td(_fmt_rec(*rec['home']))
                                td(_fmt_rec(*rec['away']))
                                td(_fmt_rec(*rec['vs500']))
                                td(_fmt_rec(*rec['first_half']))
                                td(_fmt_rec(*rec['second_half']))
                                td(_fmt_rec(*rec['shutout']))

    _wildcard_section(season_num, season_rows, split)


def _wildcard_section(season_num, season_rows, split):
    wc = season_rows[season_rows['GB'] != 0].copy()
    if wc.empty:
        return
    h2("Wild Card")
    for conf_name, conf_group in wc.groupby('conference_name', sort=False):
        h3(conf_name)
        conf_group = conf_group.copy()
        leader = conf_group.sort_values(['gamesWon', 'gamesLost'], ascending=[False, True]).iloc[0]
        max_w, min_l = leader['gamesWon'], leader['gamesLost']
        conf_group['WC_GB'] = ((max_w - conf_group['gamesWon']) + (conf_group['gamesLost'] - min_l)) / 2
        conf_group = conf_group.sort_values(['WC_GB', 'Diff'], ascending=[True, False])
        wc_cols = ['Team', 'W', 'L', 'Pct', 'GB', 'RS', 'RA', 'Diff']
        if split:
            wc_cols.append('L10')
        # FOR CLAUDE: like identified above, use render_table after refactoring column names
        with table(border=0):
            with thead():
                with tr():
                    for col in wc_cols:
                        th(col)
            with tbody():
                for _, row in conf_group.iterrows():
                    slug = row['teamName'].replace(' ', '')
                    with tr():
                        td(a(row['teamName'], href=f"../teams/{slug}/{season_num}.html"))
                        td(row['gamesWon'])
                        td(row['gamesLost'])
                        td(row['Pct'])
                        td(_fmt_gb(row['WC_GB']))
                        td(row['runsFor'])
                        td(row['runsAgainst'])
                        td(fmt_rdiff(row['Diff']))
                        if split:
                            td(_fmt_rec(*split[row['teamName']]['last10']))


def _league_stats_section(season_num):
    sb = lg.season_batting.loc[season_num]
    sp = lg.season_pitching.loc[season_num]

    h2("League Stats")

    h3("Batting")
    bat_row = pd.DataFrame([{
        'avg': sb['avg'], 'obp': sb['obp'], 'slg': sb['slg'], 'ops': sb['ops'],
        'woba': sb['woba'], 'r_per_g': sb['r_per_g'],
        'hr': sb['hr'], 'bb': sb['bb'], 'k': sb['k'],
        'stat_type': 'season',
    }])
    render_table(bat_row, depth=1)

    h3("Pitching")
    pit_row = pd.DataFrame([{
        'p_era': sp['p_era'], 'p_ra9': sp['p_ra9'], 'p_whip': sp['p_whip'],
        'p_k_per_9': sp['p_k_per_9'], 'p_bb_per_9': sp['p_bb_per_9'], 'p_babip': sp['p_babip'],
        'stat_type': 'season',
    }])
    render_table(pit_row, depth=1)


def _leader_table(stat, rows):
    h4(REGISTRY[stat]['name'] if stat in REGISTRY else stat)
    df = rows.reset_index().rename(columns={'index': '#'})
    df = df[['#', 'First Name', 'Last Name', 'team', stat]].copy()
    df.insert(2, 'player', '')
    render_table(df, depth=1)


def _leaders_section(season_num):
    h2("Leaders")
    h3("Batting")
    for stat in _BAT_LEADER_STATS:
        rows = ld.get_batting_leaders(stat, season=season_num, num=5)
        _leader_table(stat, rows)
    h3("Pitching")
    for stat in _PIT_LEADER_STATS:
        rows = ld.get_pitching_leaders(stat, season=season_num, num=5)
        _leader_table(stat, rows)

def _h2h_matrix(season_num):
    team_order, abbr_map, records = h2h_records(season_num)
    if team_order is None:
        return
    h2("Head-to-Head")
    with table(border=1):
        with thead():
            with tr():
                th('')
                for t in team_order:
                    th(abbr_map[t])
        with tbody():
            for row_team in team_order:
                with tr():
                    td(b(abbr_map[row_team]))
                    for col_team in team_order:
                        if row_team == col_team:
                            td('\u2014')
                        else:
                            rec = records.get((row_team, col_team), [0, 0])
                            td(f"{rec[0]}-{rec[1]}" if rec[0] or rec[1] else '')


def generate_season_page(season_num):
    all_seasons = sorted(SEASON_RANGE)
    idx         = all_seasons.index(season_num)
    prev_season = all_seasons[idx - 1] if idx > 0 else None
    next_season = all_seasons[idx + 1] if idx < len(all_seasons) - 1 else None

    doc = make_doc(f"Season {season_num}")
    with doc:
        h1(f"Season {season_num}")
        with p():
            if prev_season:
                a(f"<< Season {prev_season}", href=f"{prev_season}.html")
            if prev_season and next_season:
                span(" | ")
            if next_season:
                a(f"Season {next_season} >>", href=f"{next_season}.html")
        _standings_section(season_num)
        _leaders_section(season_num)
        if season_num == CURRENT_SEASON:
            _h2h_matrix(season_num)
    Path(f"docs/seasons/{season_num}.html").write_text(str(doc))
