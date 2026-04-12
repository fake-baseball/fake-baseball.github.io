"""Generate the Awards page (docs/awards.html)."""
from pathlib import Path

import pandas as pd
from dominate.tags import *

from pages.page_utils import make_doc, render_table
from triple_crown import (batting_triple_crown, pitching_triple_crown,
                          batting_triple_crown_conf, pitching_triple_crown_conf,
                          batting_title, era_title, hr_sb_club)
from data import teams as teams_data


def _to_row(w, extra=None):
    d = {**w, 'player_name': w['player_id'], 'stat_type': 'season'}
    if extra:
        d.update(extra)
    return d


def _triple_crown_table(winners, hidden=None):
    if not winners:
        p("No triple crown winners.")
        return
    render_table(pd.DataFrame([_to_row(w) for w in winners]), depth=0, hidden=hidden)


def _batting_title_table(winners):
    if not winners:
        p("No batting title winners.")
        return
    rows = [_to_row({k: v for k, v in w.items() if k != 'unqualified'}, {'Note': '* hitless AB rule' if w['unqualified'] else ''}) for w in winners]
    render_table(pd.DataFrame(rows), depth=0)


def _era_title_table(winners):
    if not winners:
        p("No ERA title winners.")
        return
    render_table(pd.DataFrame([_to_row(w) for w in winners]), depth=0)


def _hr_sb_table(members):
    if not members:
        p("No members.")
        return
    render_table(pd.DataFrame([_to_row(w) for w in members]), depth=0)


def generate_awards():
    bat_winners = batting_triple_crown()
    pit_winners = pitching_triple_crown()
    conferences = list(dict.fromkeys(teams_data.teams['conference_name']))
    conf_bat = {c: batting_triple_crown_conf(c)  for c in conferences}
    conf_pit = {c: pitching_triple_crown_conf(c) for c in conferences}
    conf_batting_title = {c: batting_title(c) for c in conferences}
    conf_era_title     = {c: era_title(c)     for c in conferences}

    doc = make_doc("Awards", depth=0)
    with doc:
        h1("Awards")

        h2("Triple Crown")
        h3("Batting")
        _triple_crown_table(bat_winners, hidden={'pa'})
        h3("Pitching")
        _triple_crown_table(pit_winners, hidden={'p_ip'})

        for conf in conferences:
            h2(f"{conf} Triple Crown")
            h3("Batting")
            _triple_crown_table(conf_bat[conf], hidden={'pa'})
            h3("Pitching")
            _triple_crown_table(conf_pit[conf], hidden={'p_ip'})

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
