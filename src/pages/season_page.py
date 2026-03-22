"""Generate an individual season page (docs/seasons/{n}.html)."""
from pathlib import Path

from dominate.tags import *

import pandas as pd

import league as lg
from data import teams as teams_data
from util import make_doc, render_table, fmt_round, fmt_rdiff
from registry import REGISTRY
import leaders as ld

_BAT_LEADER_STATS = ['war', 'hr', 'rbi', 'avg', 'ops', 'sb']
_PIT_LEADER_STATS = ['p_war', 'p_w', 'p_sv', 'p_era', 'p_k', 'p_whip']


def _fmt_gb(v):
    return '-' if v == 0 else f"{v:.1f}"


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
                for stat in ['avg', 'obp', 'slg', 'ops', 'woba']:
                    m = REGISTRY[stat]
                    td(fmt_round(sb[stat], m['decimal_places'], m['leading_zero'], m['percentage']))
                td(f"{sb['R/G']:.2f}")
                td(int(sb['hr']))
                td(int(sb['bb']))
                td(int(sb['k']))

    h3("Pitching")
    # (stat key in REGISTRY, column name in season_pitching, display header)
    pit_cols = [
        ('p_era',    'ERA',   'ERA'),
        ('p_ra9',    'RA9',   'RA9'),
        ('p_whip',   'WHIP',  'WHIP'),
        ('p_k_per_9', 'p_k_per_9',  'K/9'),
        ('p_bb_per_9','p_bb_per_9', 'BB/9'),
        ('p_babip',  'BABIP', 'BABIP'),
    ]
    with table(border=0):
        with thead():
            with tr():
                for _, _, disp in pit_cols:
                    th(disp)
        with tbody():
            with tr():
                for stat_key, sp_col, _ in pit_cols:
                    m = REGISTRY[stat_key]
                    td(fmt_round(sp[sp_col], m['decimal_places'], m['leading_zero'], m['percentage']))


def _leader_table(stat, rows):
    h4(REGISTRY[stat]['name'] if stat in REGISTRY else stat)
    df = rows.reset_index().rename(columns={'index': '#'})
    df = df[['#', 'First Name', 'Last Name', 'team', stat]].copy()
    df.insert(2, 'player', '')
    render_table(df, prefix='../players/')


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


def generate_season_page(season_num):
    doc = make_doc(f"Season {season_num}")
    with doc:
        h1(f"Season {season_num}")
        _standings_section(season_num)
        _leaders_section(season_num)
    Path(f"docs/seasons/{season_num}.html").write_text(str(doc))
