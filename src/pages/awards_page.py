"""Generate the Awards page (docs/awards.html)."""
from pathlib import Path

from dominate.tags import *

from util import make_doc, fmt_round, fmt_ip, convert_name
from stats_meta import BATTING_STATS, PITCHING_STATS
from triple_crown import (batting_triple_crown, pitching_triple_crown,
                          batting_triple_crown_conf, pitching_triple_crown_conf,
                          batting_title, era_title, hr_sb_club)
from data import teams as teams_data


def _triple_crown_table(winners, stat_cols, stat_meta):
    if not winners:
        p("No triple crown winners.")
        return
    with table(border=0):
        with thead():
            with tr():
                th('Season')
                th('Player')
                for col in stat_cols:
                    th(col)
        with tbody():
            for w in winners:
                first, last = w['first'], w['last']
                with tr():
                    td(w['season'])
                    td(a(f"{first} {last}", href=f"players/{convert_name(first, last)}.html"))
                    for col in stat_cols:
                        m = stat_meta[col]
                        td(fmt_round(w[col], m['decimal_places'], m['leading_zero'], m['percentage']))


def _batting_title_table(winners):
    if not winners:
        p("No batting title winners.")
        return
    m = BATTING_STATS['AVG']
    with table(border=0):
        with thead():
            with tr():
                th('Season')
                th('Player')
                th('AVG')
                th('PA')
                th('Note')
        with tbody():
            for w in winners:
                first, last = w['first'], w['last']
                with tr():
                    td(w['season'])
                    td(a(f"{first} {last}", href=f"players/{convert_name(first, last)}.html"))
                    td(fmt_round(w['AVG'], m['decimal_places'], m['leading_zero'], m['percentage']))
                    td(w['PA'])
                    td('* hitless AB rule' if w['unqualified'] else '')


def _era_title_table(winners):
    if not winners:
        p("No ERA title winners.")
        return
    m = PITCHING_STATS['ERA']
    with table(border=0):
        with thead():
            with tr():
                th('Season')
                th('Player')
                th('ERA')
                th('IP')
        with tbody():
            for w in winners:
                first, last = w['first'], w['last']
                with tr():
                    td(w['season'])
                    td(a(f"{first} {last}", href=f"players/{convert_name(first, last)}.html"))
                    td(fmt_round(w['ERA'], m['decimal_places'], m['leading_zero'], m['percentage']))
                    td(fmt_ip(w['IP_true']))


def _hr_sb_table(members):
    if not members:
        p("No members.")
        return
    m_avg = BATTING_STATS['AVG']
    with table(border=0):
        with thead():
            with tr():
                for col in ['Season', 'Player', 'Team', 'HR', 'SB', 'AVG']:
                    th(col)
        with tbody():
            for w in members:
                first, last = w['first'], w['last']
                with tr():
                    td(w['season'])
                    td(a(f"{first} {last}", href=f"players/{convert_name(first, last)}.html"))
                    td(w['team'])
                    td(w['HR'])
                    td(w['SB'])
                    td(fmt_round(w['AVG'], m_avg['decimal_places'], m_avg['leading_zero'], m_avg['percentage']))


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
        _triple_crown_table(bat_winners, ['AVG', 'HR', 'RBI'], BATTING_STATS)
        h3("Pitching")
        _triple_crown_table(pit_winners, ['W', 'ERA', 'K'], PITCHING_STATS)

        for conf in conferences:
            h2(f"{conf} Triple Crown")
            h3("Batting")
            _triple_crown_table(conf_bat[conf], ['AVG', 'HR', 'RBI'], BATTING_STATS)
            h3("Pitching")
            _triple_crown_table(conf_pit[conf], ['W', 'ERA', 'K'], PITCHING_STATS)

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
