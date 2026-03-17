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
from util import fmt_round, convert_name, make_doc


def generate_leaders(data_batters, data_pitchers, player_info):
    # Each entry: (title, slug, suffix, stat, display_col, df)
    pages = []

    def _linkify(df):
        """Replace First Name / Last Name columns with a single linked Player column."""
        df = df.copy()
        df.insert(0, 'Player', df.apply(
            # XXX manually reconstructing <a> tag
            lambda r: f'<a href="../players/{convert_name(r["First Name"], r["Last Name"])}.html">{r["First Name"]} {r["Last Name"]}</a>',
            axis=1
        ))
        return df.drop(columns=['First Name', 'Last Name'])

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

    def _build_batting(title, slug, stat, meta, lowest, qual_col):
        qualified = meta['qualified']
        _fmt = lambda v: fmt_round(v, meta['decimal_places'], meta['leading_zero'], meta['percentage'])

        _index_row(title, slug)

        df = get_batting_leaders(data_batters, stat, num=100, qualified=qualified, qual_col=qual_col, lowest=lowest)
        df = _linkify(df[['First Name', 'Last Name', stat, 'Season', qual_col, 'Team']])
        df.index = range(1, len(df) + 1)
        df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'season', stat, stat, df))

        df = get_leaders_by_season(data_batters, stat, qualified=qualified, qual_col=qual_col, lowest=lowest)
        df = _linkify(df[['Season', 'First Name', 'Last Name', stat, qual_col, 'Team']].set_index('Season'))
        df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'yearly', stat, stat, df))

        df = get_career_batting_leaders(data_batters, player_info, stat, num=100, qualified=qualified, qual_col=qual_col, lowest=lowest)
        df = _linkify(df[['First Name', 'Last Name', stat, qual_col]])
        df.index = range(1, len(df) + 1)
        df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'career', stat, stat, df))

        df = get_career_batting_leaders(data_batters, player_info, stat, active=True, num=100, qualified=qualified, qual_col=qual_col, lowest=lowest)
        df = _linkify(df[['First Name', 'Last Name', stat, qual_col]])
        df.index = range(1, len(df) + 1)
        df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'active', stat, stat, df))

    def _render_batting(qual_col):
        def render(stat, meta):
            lowest = meta['lowest']
            if meta['slug_worst']:
                _build_batting(meta['name'] + " (Best)",  meta['slug'],               stat, meta, lowest=lowest,     qual_col=qual_col)
                _build_batting(meta['name'] + " (Worst)", meta['slug'] + '_worst',    stat, meta, lowest=not lowest, qual_col=qual_col)
            else:
                _build_batting(meta['name'], meta['slug'], stat, meta, lowest=lowest, qual_col=qual_col)
        return render

    # ── Pitching leaders ──────────────────────────────────────────────────────

    def _build_pitching(title, slug, stat, meta, lowest):
        qualified  = meta['qualified']
        _fmt       = lambda v: fmt_round(v, meta['decimal_places'], meta['leading_zero'])
        display_col = meta['display_col'] or stat
        is_aliased  = display_col != stat   # True for IP_true → shown as IP

        _index_row(title, slug)

        df = get_pitching_leaders(data_pitchers, stat, num=100, qualified=qualified, lowest=lowest)
        cols = (['First Name', 'Last Name', display_col, 'Season', 'Team'] if is_aliased
                else ['First Name', 'Last Name', stat, 'Season', 'IP', 'Team'])
        df = _linkify(df[cols])
        df.index = range(1, len(df) + 1)
        if not is_aliased:
            df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'season', stat, display_col, df))

        df = get_pitching_leaders_by_season(data_pitchers, stat, qualified=qualified, lowest=lowest)
        cols = (['Season', 'First Name', 'Last Name', display_col, 'Team'] if is_aliased
                else ['Season', 'First Name', 'Last Name', stat, 'IP', 'Team'])
        df = _linkify(df[cols].set_index('Season'))
        if not is_aliased:
            df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'yearly', stat, display_col, df))

        career_cols = (['First Name', 'Last Name', display_col] if is_aliased
                       else ['First Name', 'Last Name', stat, 'IP'])
        df = get_career_pitching_leaders(data_pitchers, player_info, stat, num=100, qualified=qualified, lowest=lowest)
        df = _linkify(df[career_cols])
        df.index = range(1, len(df) + 1)
        if not is_aliased:
            df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'career', stat, display_col, df))

        df = get_career_pitching_leaders(data_pitchers, player_info, stat, active=True, num=100, qualified=qualified, lowest=lowest)
        df = _linkify(df[career_cols])
        df.index = range(1, len(df) + 1)
        if not is_aliased:
            df[stat] = df[stat].map(_fmt)
        pages.append((title, slug, 'active', stat, display_col, df))

    def render_pitching(stat, meta):
        lowest = meta['lowest']
        if meta['slug_worst']:
            _build_pitching(meta['name'] + " (Best)",  meta['slug'],            stat, meta, lowest=lowest)
            _build_pitching(meta['name'] + " (Worst)", meta['slug'] + '_worst', stat, meta, lowest=not lowest)
        else:
            _build_pitching(meta['name'], meta['slug'], stat, meta, lowest=lowest)

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
            v.get('qualified') for v in stat_dict.values()
            if 'slug' in v
        )
        if has_qualified:
            p(qual_note)
        with table():
            with thead():
                tr(th("Statistic"), th("Single-Season"), th("Yearly"), th("Career"), th("Active"))
            with tbody():
                for stat, meta in stat_dict.items():
                    if 'slug' in meta:
                        render_fn(stat, meta)

    doc = make_doc("Leaders")
    with doc:
        h1("Leaders")
        _section("Batting",     BATTING_STATS,     qual_notes['batting'],     _render_batting('PA'))
        _section("Baserunning", BASERUNNING_STATS, qual_notes['baserunning'], _render_batting('SBatt'))
        _section("Fielding",    FIELDING_STATS,    qual_notes['fielding'],    _render_batting('GF'))
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
