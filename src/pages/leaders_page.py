"""Generate the leaders index page and all individual stat leader sub-pages."""
from pathlib import Path

from dominate.tags import *
from dominate.util import raw

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
from util import fmt_round, linkify_players, make_doc


def generate_leaders():
    # Each entry: (title, slug, suffix, stat, display_col, df)
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
        _fmt = lambda v: fmt_round(v, meta['decimal_places'], meta['leading_zero'], meta['percentage'])
        qual_col = meta['qual_col']

        _index_row(title, slug)

        df = get_batting_leaders(stat, num=100, worst=worst)
        cols = list(dict.fromkeys(['First Name', 'Last Name', stat, 'Season', qual_col, 'Team']))
        df = linkify_players(df[cols])
        df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'season', stat, stat, df))

        df = get_leaders_by_season(stat, worst=worst)
        df = linkify_players(df[['Season', 'First Name', 'Last Name', stat, qual_col, 'Team']].set_index('Season'))
        df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'yearly', stat, stat, df))

        df = get_career_batting_leaders(stat, num=100, worst=worst)
        df = linkify_players(df[list(dict.fromkeys(['First Name', 'Last Name', stat, qual_col]))])
        df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'career', stat, stat, df))

        df = get_career_batting_leaders(stat, active=True, num=100, worst=worst)
        df = linkify_players(df[list(dict.fromkeys(['First Name', 'Last Name', stat, qual_col]))])
        df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'active', stat, stat, df))

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
        _fmt        = lambda v: fmt_round(v, meta['decimal_places'], meta['leading_zero'])
        display_col = meta['display_col'] or stat
        is_aliased  = display_col != stat   # True for IP_true → shown as IP

        _index_row(title, slug)

        df = get_pitching_leaders(stat, num=100, worst=worst)
        cols = (['First Name', 'Last Name', display_col, 'Season', 'Team'] if is_aliased
                else ['First Name', 'Last Name', stat, 'Season', 'IP', 'Team'])
        df = linkify_players(df[cols])
        if not is_aliased:
            df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'season', stat, display_col, df))

        df = get_pitching_leaders_by_season(stat, worst=worst)
        cols = (['Season', 'First Name', 'Last Name', display_col, 'Team'] if is_aliased
                else ['Season', 'First Name', 'Last Name', stat, 'IP', 'Team'])
        df = linkify_players(df[cols].set_index('Season'))
        if not is_aliased:
            df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'yearly', stat, display_col, df))

        career_cols = (['First Name', 'Last Name', display_col] if is_aliased
                       else ['First Name', 'Last Name', stat, 'IP'])
        df = get_career_pitching_leaders(stat, num=100, worst=worst)
        df = linkify_players(df[career_cols])
        if not is_aliased:
            df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'career', stat, display_col, df))

        df = get_career_pitching_leaders(stat, active=True, num=100, worst=worst)
        df = linkify_players(df[career_cols])
        if not is_aliased:
            df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'active', stat, display_col, df))

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
    for title, slug, suffix, stat, display_col, df in pages:
        subdoc = make_doc(f"{display_col} - {labels[suffix]}")
        with subdoc:
            h1(f"{labels[suffix]} for {title}")
            raw(df.to_html(border=0, index=True, escape=False))
        Path(f"docs/leaders/{slug}_{suffix}.html").write_text(str(subdoc))
