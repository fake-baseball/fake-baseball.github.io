"""Generate the Awards page (docs/awards.html)."""
from pathlib import Path

import pandas as pd
from dominate.tags import *

from util import make_doc, render_table
from triple_crown import (batting_triple_crown, pitching_triple_crown,
                          batting_triple_crown_conf, pitching_triple_crown_conf,
                          batting_title, era_title, hr_sb_club)
from data import teams as teams_data


def _triple_crown_table(winners, stat_cols):
    if not winners:
        p("No triple crown winners.")
        return
    rows = [
        {'First Name': w['first'], 'Last Name': w['last'], 'player': '',
         'season': w['season'], **{col: w[col] for col in stat_cols}}
        for w in winners
    ]
    render_table(pd.DataFrame(rows), prefix='players/')


def _batting_title_table(winners):
    if not winners:
        p("No batting title winners.")
        return
    rows = [
        {'First Name': w['first'], 'Last Name': w['last'], 'player': '',
         'season': w['season'], 'avg': w['AVG'], 'pa': w['PA'],
         'Note': '* hitless AB rule' if w['unqualified'] else ''}
        for w in winners
    ]
    render_table(pd.DataFrame(rows), prefix='players/')


def _era_title_table(winners):
    if not winners:
        p("No ERA title winners.")
        return
    rows = [
        {'First Name': w['first'], 'Last Name': w['last'], 'player': '',
         'season': w['season'], 'p_era': w['ERA'], 'p_ip': w['IP_true']}
        for w in winners
    ]
    render_table(pd.DataFrame(rows), prefix='players/')


def _hr_sb_table(members):
    if not members:
        p("No members.")
        return
    rows = [
        {'First Name': w['first'], 'Last Name': w['last'], 'player': '',
         'season': w['season'], 'team': w['team'],
         'hr': w['HR'], 'sb': w['SB'], 'avg': w['AVG']}
        for w in members
    ]
    render_table(pd.DataFrame(rows), prefix='players/')


def generate_awards():
    bat_winners = batting_triple_crown()
    pit_winners = pitching_triple_crown()
    conferences = list(dict.fromkeys(teams_data.teams['conference_name']))
    conf_bat = {c: batting_triple_crown_conf(c)  for c in conferences}
    conf_pit = {c: pitching_triple_crown_conf(c) for c in conferences}
    conf_batting_title = {c: batting_title(c) for c in conferences}
    conf_era_title     = {c: era_title(c)     for c in conferences}

    doc = make_doc("Awards", css='style.css')
    with doc:
        h1("Awards")

        h2("Triple Crown")
        h3("Batting")
        _triple_crown_table(bat_winners, ['avg', 'hr', 'rbi'])
        h3("Pitching")
        _triple_crown_table(pit_winners, ['p_w', 'p_era', 'p_k'])

        for conf in conferences:
            h2(f"{conf} Triple Crown")
            h3("Batting")
            _triple_crown_table(conf_bat[conf], ['avg', 'hr', 'rbi'])
            h3("Pitching")
            _triple_crown_table(conf_pit[conf], ['p_w', 'p_era', 'p_k'])

        h2("Batting Title")
        for conf in conferences:
            h3(conf)
            _batting_title_table(conf_batting_title[conf])

        h2("ERA Title")
        for conf in conferences:
            h3(conf)
            _era_title_table(conf_era_title[conf])

        h2("HR-SB Club")
        for n in (15, 20):
            h3(f"{n}-{n} Club")
            _hr_sb_table(hr_sb_club(n))

    Path("docs/awards.html").write_text(str(doc))
