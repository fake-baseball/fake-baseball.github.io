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
from registry import REGISTRY
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
        cols = list(dict.fromkeys(['First Name', 'Last Name', stat, 'season', qual_col, 'team']))
        df = df[cols].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'player', '')
        pages.append((title, slug, 'season', df))

        df = get_leaders_by_season(stat, worst=worst)
        cols = list(dict.fromkeys(['season', 'First Name', 'Last Name', stat, qual_col, 'team']))
        df = df[cols].copy()
        df.insert(1, 'player', '')
        pages.append((title, slug, 'yearly', df))

        df = get_career_batting_leaders(stat, num=100, worst=worst)
        cols = list(dict.fromkeys(['First Name', 'Last Name', stat, qual_col]))
        df = df[cols].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'player', '')
        pages.append((title, slug, 'career', df))

        df = get_career_batting_leaders(stat, active=True, num=100, worst=worst)
        cols = list(dict.fromkeys(['First Name', 'Last Name', stat, qual_col]))
        df = df[cols].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'player', '')
        pages.append((title, slug, 'active', df))

    def _render_batting():
        def render(stat, meta):
            slug = meta.get('slug', stat)
            if meta['has_worst']:
                _build_batting(meta['label'] + " (Best)",  slug,            stat, meta, worst=False)
                _build_batting(meta['label'] + " (Worst)", slug + '_worst', stat, meta, worst=True)
            else:
                _build_batting(meta['label'], slug, stat, meta, worst=False)
        return render

    # ── Pitching leaders ──────────────────────────────────────────────────────

    def _build_pitching(title, slug, stat, meta, worst):
        _index_row(title, slug)

        # Season table
        df = get_pitching_leaders(stat, num=100, worst=worst)
        if stat == 'p_ip':
            cols = ['First Name', 'Last Name', 'role', 'p_ip', 'season', 'team']
        else:
            cols = ['First Name', 'Last Name', 'role', stat, 'season', 'p_ip', 'team']
        df = df[list(dict.fromkeys(cols))].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'player', '')
        pages.append((title, slug, 'season', df))

        # Yearly table
        df = get_pitching_leaders_by_season(stat, worst=worst)
        if stat == 'p_ip':
            cols = ['season', 'First Name', 'Last Name', 'role', 'p_ip', 'team']
        else:
            cols = ['season', 'First Name', 'Last Name', 'role', stat, 'p_ip', 'team']
        df = df[list(dict.fromkeys(cols))].copy()
        df.insert(1, 'player', '')
        pages.append((title, slug, 'yearly', df))

        # Career role lookup
        import pitching as _pit
        season_role = (
            _pit.stats[_pit.stats['stat_type'] == 'season']
            .sort_values('season')
            .groupby(['First Name', 'Last Name'])['role']
            .last()
        )

        if stat == 'p_ip':
            career_cols = ['First Name', 'Last Name', 'role', 'p_ip']
        else:
            career_cols = ['First Name', 'Last Name', 'role', stat, 'p_ip']

        # Career table
        df = get_career_pitching_leaders(stat, num=100, worst=worst)
        df = df.copy()
        df['role'] = df.apply(lambda r: season_role.get((r['First Name'], r['Last Name']), r['role']), axis=1)
        df = df[list(dict.fromkeys(career_cols))].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'player', '')
        pages.append((title, slug, 'career', df))

        # Active table
        df = get_career_pitching_leaders(stat, active=True, num=100, worst=worst)
        df = df.copy()
        df['role'] = df.apply(lambda r: season_role.get((r['First Name'], r['Last Name']), r['role']), axis=1)
        df = df[list(dict.fromkeys(career_cols))].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'player', '')
        pages.append((title, slug, 'active', df))

    def render_pitching(stat, meta):
        slug = meta.get('slug', stat)
        if meta['has_worst']:
            _build_pitching(meta['label'] + " (Best)",  slug,            stat, meta, worst=False)
            _build_pitching(meta['label'] + " (Worst)", slug + '_worst', stat, meta, worst=True)
        else:
            _build_pitching(meta['label'], slug, stat, meta, worst=False)

    # ── Leaders index page ────────────────────────────────────────────────────

    qual_notes = {
        'batting':     (f"For rate statistics, single-season records require {int(BAT_SEASON_MIN_PA):,} PA "
                        f"and career/active leaders require {int(BAT_CAREER_MIN_PA):,} PA."),
        'baserunning': (f"For rate statistics, single-season records require {int(BR_SEASON_MIN_SBATT):,} SB attempts "
                        f"and career/active leaders require {int(BR_CAREER_MIN_SBATT):,} SB attempts."),
        'fielding':    (f"For rate statistics, single-season records require {int(FLD_SEASON_MIN_GF):,} fielding games "
                        f"and career/active leaders require {int(FLD_CAREER_MIN_GF):,} fielding games."),
        'pitching':    (f"For rate statistics, single-season records require {int(PIT_SEASON_MIN_IP):,} IP "
                        f"and career/active leaders require {int(PIT_CAREER_MIN_IP):,} IP."),
    }

    def _section(title, stat_dict, qual_note, render_fn):
        h2(title)
        has_qualified = any(
            v['qualified'] for v in stat_dict.values()
            if v['leaders']
        )
        if has_qualified:
            p(qual_note)
        with table():
            with thead():
                tr(th("Statistic"), th("Single-Season"), th("Yearly"), th("Career"), th("Active"))
            with tbody():
                for stat, meta in stat_dict.items():
                    if meta['leaders']:
                        render_fn(stat, meta)

    _batting_stats     = {k: v for k, v in REGISTRY.items() if v.get('context') == 'batting'}
    _baserunning_stats = {k: v for k, v in REGISTRY.items() if v.get('context') == 'baserunning'}
    _fielding_stats    = {k: v for k, v in REGISTRY.items() if v.get('context') == 'fielding'}
    _pitching_stats    = {k: v for k, v in REGISTRY.items() if v.get('context') == 'pitching'}

    doc = make_doc("Leaders")
    with doc:
        h1("Leaders")
        _section("Batting",     _batting_stats,     qual_notes['batting'],     _render_batting())
        _section("Baserunning", _baserunning_stats, qual_notes['baserunning'], _render_batting())
        _section("Fielding",    _fielding_stats,    qual_notes['fielding'],    _render_batting())
        _section("Pitching",    _pitching_stats,    qual_notes['pitching'],    render_pitching)

    Path("docs/leaders/index.html").write_text(str(doc))

    # ── Individual stat sub-pages ─────────────────────────────────────────────

    labels = {
        'season': 'Single-Season Records',
        'yearly': 'Yearly Leaders',
        'career': 'Career Leaders',
        'active': 'Active Leaders',
    }
    for title, slug, suffix, df in pages:
        # Determine display name for page title: use meta['name'] if available
        stat_cols = [c for c in df.columns if c in REGISTRY and REGISTRY[c].get('type', 'stat') == 'stat']
        display_name = REGISTRY[stat_cols[0]]['name'] if stat_cols else slug
        subdoc = make_doc(f"{display_name} - {labels[suffix]}")
        with subdoc:
            h1(f"{labels[suffix]} for {title}")
            render_table(df, depth=1)
        Path(f"docs/leaders/{slug}_{suffix}.html").write_text(str(subdoc))
