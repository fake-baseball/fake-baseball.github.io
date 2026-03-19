"""Generate an individual season page (docs/seasons/{n}.html)."""
from pathlib import Path

from dominate.tags import *

import league as lg
from data import teams as teams_data
from util import make_doc, fmt_round, fmt_ip, fmt_rdiff, convert_name
import leaders as ld
from stats_meta import BATTING_STATS, BASERUNNING_STATS, PITCHING_STATS

_ALL_BAT = {**BATTING_STATS, **BASERUNNING_STATS}

_BAT_LEADER_STATS = ['WAR', 'HR', 'RBI', 'AVG', 'OPS', 'SB']
_PIT_LEADER_STATS = ['WAR', 'W', 'SV', 'ERA', 'K', 'WHIP']


def _fmt_bat(stat, val):
    m = _ALL_BAT[stat]
    return fmt_round(val, m['decimal_places'], m['leading_zero'], m['percentage'])


def _fmt_pit(stat, val):
    m = PITCHING_STATS[stat]
    return fmt_round(val, m['decimal_places'], m['leading_zero'], m['percentage'])


def _fmt_gb(val):
    if val == 0:
        return '-'
    return f"{val:.1f}"


def _standings_section(season_num):
    season_rows = teams_data.standings[teams_data.standings['Season'] == season_num].copy()
    if season_rows.empty:
        return
    season_rows['Pct'] = (
        season_rows['gamesWon'] / (season_rows['gamesWon'] + season_rows['gamesLost'])
    ).map(lambda v: f"{v:.3f}".lstrip('0'))
    season_rows['Diff'] = season_rows['runsFor'] - season_rows['runsAgainst']

    h2("Standings")
    for conf_name, conf_group in season_rows.groupby('conference_name', sort=False):
        h3(conf_name)
        for div_name, div_group in conf_group.groupby('division_name', sort=False):
            h4(div_name)
            with table(border=0):
                with thead():
                    with tr():
                        for col in ['Team', 'W', 'L', 'Pct', 'GB', 'RS', 'RA', 'Diff']:
                            th(col)
                with tbody():
                    for _, row in div_group.sort_values('gamesWon', ascending=False).iterrows():
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


def _league_stats_section(season_num):
    sb = lg.season_batting.loc[season_num]
    sp = lg.season_pitching.loc[season_num]

    h2("League Stats")

    h3("Batting")
    bat_cols = ['AVG', 'OBP', 'SLG', 'OPS', 'wOBA', 'R/G', 'HR', 'BB', 'K']
    with table(border=0):
        with thead():
            with tr():
                for col in bat_cols:
                    th(col)
        with tbody():
            with tr():
                for stat in ['AVG', 'OBP', 'SLG', 'OPS', 'wOBA']:
                    m = BATTING_STATS[stat]
                    td(fmt_round(sb[stat], m['decimal_places'], m['leading_zero'], m['percentage']))
                td(f"{sb['R/G']:.2f}")
                td(int(sb['HR']))
                td(int(sb['BB']))
                td(int(sb['K']))

    h3("Pitching")
    pit_cols = ['ERA', 'RA9', 'WHIP', 'K/9', 'BB/9', 'BABIP']
    with table(border=0):
        with thead():
            with tr():
                for col in pit_cols:
                    th(col)
        with tbody():
            with tr():
                for stat in pit_cols:
                    m = PITCHING_STATS[stat]
                    td(fmt_round(sp[stat], m['decimal_places'], m['leading_zero'], m['percentage']))


def _leader_table(stat, rows, fmt_fn):
    h4(stat)
    with table(border=0):
        with thead():
            with tr():
                th('#')
                th('Player')
                th('Team')
                th(stat)
        with tbody():
            for rank, row in rows.iterrows():
                val = row['IP_true'] if stat == 'IP' else row[stat]
                first, last = row['First Name'], row['Last Name']
                with tr():
                    td(rank)
                    td(a(f"{first} {last}", href=f"../players/{convert_name(first, last)}.html"))
                    td(row['Team'])
                    td(fmt_fn(stat, val))


def _leaders_section(season_num):
    h2("Leaders")
    h3("Batting")
    for stat in _BAT_LEADER_STATS:
        rows = ld.get_batting_leaders(stat, season=season_num, num=5)
        _leader_table(stat, rows, _fmt_bat)
    h3("Pitching")
    for stat in _PIT_LEADER_STATS:
        rows = ld.get_pitching_leaders(stat, season=season_num, num=5)
        _leader_table(stat, rows, _fmt_pit)


def generate_season_page(season_num):
    doc = make_doc(f"Season {season_num}")
    with doc:
        h1(f"Season {season_num}")
        _standings_section(season_num)
        _leaders_section(season_num)
    Path(f"docs/seasons/{season_num}.html").write_text(str(doc))
