"""Generate the leaders index page and all individual stat leader sub-pages."""
from pathlib import Path

import pandas as pd
from dominate.tags import *

from constants import (
    BAT_SEASON_MIN_PA,   BAT_CAREER_MIN_PA,
    BR_SEASON_MIN_SBATT, BR_CAREER_MIN_SBATT,
    FLD_SEASON_MIN_GF,   FLD_CAREER_MIN_GF,
    PIT_SEASON_MIN_IP,   PIT_CAREER_MIN_IP,
)
from leaders import (
    get_batting_leaders, get_career_batting_leaders, get_leaders_by_season,
    get_pitching_leaders, get_career_pitching_leaders, get_pitching_leaders_by_season,
)
from stats_meta import BATTING_STATS, BASERUNNING_STATS, FIELDING_STATS, PITCHING_STATS
from util import make_doc, render_table


def generate_leaders():
    # Each entry: (title, slug, suffix, df)
    pages = []

    # ── Shared index-row builder ──────────────────────────────────────────────

    def _index_row(title, slug):
        tr(td(title), *[
            td(a(label, href=f"{slug}_{suffix}.html"))
            for label, suffix in zip(
                ['Single-Season', 'Yearly', 'Career', 'Active'],
                ['season',        'yearly', 'career', 'active'],
            )
        ])

    # ── Batting / baserunning / fielding leaders ──────────────────────────────

    def _build_batting(title, slug, stat, meta, worst):
        qual_col = meta['qual_col']
        _index_row(title, slug)

        df = get_batting_leaders(stat, num=100, worst=worst)
        cols = list(dict.fromkeys(['First Name', 'Last Name', stat, 'Season', qual_col, 'Team']))
        df = df[cols].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'Player', '')
        pages.append((title, slug, 'season', df))

        df = get_leaders_by_season(stat, worst=worst)
        cols = list(dict.fromkeys(['Season', 'First Name', 'Last Name', stat, qual_col, 'Team']))
        df = df[cols].copy()
        df.insert(1, 'Player', '')
        pages.append((title, slug, 'yearly', df))

        df = get_career_batting_leaders(stat, num=100, worst=worst)
        cols = list(dict.fromkeys(['First Name', 'Last Name', stat, qual_col]))
        df = df[cols].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'Player', '')
        pages.append((title, slug, 'career', df))

        df = get_career_batting_leaders(stat, active=True, num=100, worst=worst)
        cols = list(dict.fromkeys(['First Name', 'Last Name', stat, qual_col]))
        df = df[cols].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'Player', '')
        pages.append((title, slug, 'active', df))

    def _render_batting():
        def render(stat, meta):
            if meta['slug_worst']:
                _build_batting(meta['name'] + " (Best)",  meta['slug'],            stat, meta, worst=False)
                _build_batting(meta['name'] + " (Worst)", meta['slug'] + '_worst', stat, meta, worst=True)
            else:
                _build_batting(meta['name'], meta['slug'], stat, meta, worst=False)
        return render

    # ── Pitching leaders ──────────────────────────────────────────────────────

    def _build_pitching(title, slug, stat, meta, worst):
        _index_row(title, slug)

        # Season table
        df = get_pitching_leaders(stat, num=100, worst=worst)
        if stat == 'IP_true':
            cols = ['First Name', 'Last Name', 'Role', 'IP_true', 'Season', 'Team']
        else:
            cols = ['First Name', 'Last Name', 'Role', stat, 'Season', 'IP_true', 'Team']
        df = df[list(dict.fromkeys(cols))].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'Player', '')
        pages.append((title, slug, 'season', df))

        # Yearly table
        df = get_pitching_leaders_by_season(stat, worst=worst)
        if stat == 'IP_true':
            cols = ['Season', 'First Name', 'Last Name', 'Role', 'IP_true', 'Team']
        else:
            cols = ['Season', 'First Name', 'Last Name', 'Role', stat, 'IP_true', 'Team']
        df = df[list(dict.fromkeys(cols))].copy()
        df.insert(1, 'Player', '')
        pages.append((title, slug, 'yearly', df))

        # Career role lookup
        import pitching as _pit
        season_role = (
            _pit.stats[_pit.stats['stat_type'] == 'season']
            .sort_values('Season')
            .groupby(['First Name', 'Last Name'])['Role']
            .last()
        )

        if stat == 'IP_true':
            career_cols = ['First Name', 'Last Name', 'Role', 'IP_true']
        else:
            career_cols = ['First Name', 'Last Name', 'Role', stat, 'IP_true']

        # Career table
        df = get_career_pitching_leaders(stat, num=100, worst=worst)
        df = df.copy()
        df['Role'] = df.apply(lambda r: season_role.get((r['First Name'], r['Last Name']), r['Role']), axis=1)
        df = df[list(dict.fromkeys(career_cols))].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'Player', '')
        pages.append((title, slug, 'career', df))

        # Active table
        df = get_career_pitching_leaders(stat, active=True, num=100, worst=worst)
        df = df.copy()
        df['Role'] = df.apply(lambda r: season_role.get((r['First Name'], r['Last Name']), r['Role']), axis=1)
        df = df[list(dict.fromkeys(career_cols))].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'Player', '')
        pages.append((title, slug, 'active', df))

    def render_pitching(stat, meta):
        if meta['slug_worst']:
            _build_pitching(meta['name'] + " (Best)",  meta['slug'],            stat, meta, worst=False)
            _build_pitching(meta['name'] + " (Worst)", meta['slug'] + '_worst', stat, meta, worst=True)
        else:
            _build_pitching(meta['name'], meta['slug'], stat, meta, worst=False)

    # ── Leaders index page ────────────────────────────────────────────────────

    qual_notes = {
        'batting':     (f"For rate statistics, single-season records require {BAT_SEASON_MIN_PA:,} PA "
                        f"and career/active leaders require {BAT_CAREER_MIN_PA:,} PA."),
        'baserunning': (f"For rate statistics, single-season records require {BR_SEASON_MIN_SBATT:g} SB attempts "
                        f"and career/active leaders require {BR_CAREER_MIN_SBATT} SB attempts."),
        'fielding':    (f"For rate statistics, single-season records require {FLD_SEASON_MIN_GF:g} fielding games "
                        f"and career/active leaders require {FLD_CAREER_MIN_GF} fielding games."),
        'pitching':    (f"For rate statistics, single-season records require {PIT_SEASON_MIN_IP:g} IP "
                        f"and career/active leaders require {PIT_CAREER_MIN_IP:,.0f} IP."),
    }

    def _section(title, stat_dict, qual_note, render_fn):
        h2(title)
        has_qualified = any(
            v['qualified'] for v in stat_dict.values()
            if v['slug']
        )
        if has_qualified:
            p(qual_note)
        with table():
            with thead():
                tr(th("Statistic"), th("Single-Season"), th("Yearly"), th("Career"), th("Active"))
            with tbody():
                for stat, meta in stat_dict.items():
                    if meta['slug']:
                        render_fn(stat, meta)

    doc = make_doc("Leaders")
    with doc:
        h1("Leaders")
        _section("Batting",     BATTING_STATS,     qual_notes['batting'],     _render_batting())
        _section("Baserunning", BASERUNNING_STATS, qual_notes['baserunning'], _render_batting())
        _section("Fielding",    FIELDING_STATS,    qual_notes['fielding'],    _render_batting())
        _section("Pitching",    PITCHING_STATS,    qual_notes['pitching'],    render_pitching)

    Path("docs/leaders/index.html").write_text(str(doc))

    # ── Individual stat sub-pages ─────────────────────────────────────────────

    labels = {
        'season': 'Single-Season Records',
        'yearly': 'Yearly Leaders',
        'career': 'Career Leaders',
        'active': 'Active Leaders',
    }
    for title, slug, suffix, df in pages:
        # Determine display name for page title: use display_col if set
        all_meta = {**BATTING_STATS, **BASERUNNING_STATS, **FIELDING_STATS, **PITCHING_STATS}
        stat_cols = [c for c in df.columns if c in all_meta]
        display_col = all_meta[stat_cols[0]].get('display_col') or stat_cols[0] if stat_cols else slug
        subdoc = make_doc(f"{display_col} - {labels[suffix]}")
        with subdoc:
            h1(f"{labels[suffix]} for {title}")
            render_table(df, prefix='../players/')
        Path(f"docs/leaders/{slug}_{suffix}.html").write_text(str(subdoc))
