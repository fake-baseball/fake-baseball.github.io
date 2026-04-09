"""Generate the leaders index page and all individual stat leader sub-pages."""
from pathlib import Path

from dominate.tags import *

from constants import (
    BAT_SEASON_MIN_PA,   BAT_CAREER_MIN_PA,
    BR_SEASON_MIN_SBATT, BR_CAREER_MIN_SBATT,
    FLD_SEASON_MIN_GF,   FLD_CAREER_MIN_GF,
    PIT_SEASON_MIN_IP,   PIT_CAREER_MIN_IP,
)
from leaders import get_leaders, get_career_leaders, get_leaders_by_season
from data import teams as teams_data
from registry import REGISTRY
from pages.page_utils import make_doc, render_table

_TOTAL_LEADERS = 100
_CONF_LEADERS  = 25

def generate_leaders():
    # Each entry: (title, slug, suffix, df, is_pitching, conf_sections)
    # conf_sections: list of (conf_name, conf_df) pairs, pre-built at build time
    pages = []

    # Build conference -> team abbr list mapping (if teams loaded)
    _conf_teams = {}
    if teams_data.teams is not None:
        for row in teams_data.teams.itertuples():
            conf = row.conference_name
            if conf not in _conf_teams:
                _conf_teams[conf] = []
            _conf_teams[conf].append(row.abbr)
    _conf_order = list(_conf_teams.keys())

    # ── Shared index-row builder ──────────────────────────────────────────────

    def _index_row(title, slug):
        tr(td(title), *[
            td(a(label, href=f"{slug}_{suffix}.html"))
            for label, suffix in zip(
                ['Single-Season', 'Seasonal', 'Career', 'Active'],
                ['season',        'seasonal', 'career', 'active'],
            )
        ])

    # ── Batting / baserunning / fielding leaders ──────────────────────────────

    def _build_batting(title, slug, stat, meta, worst):
        qual_col = meta['qual_col']
        _index_row(title, slug)

        df = get_leaders(stat, num=_TOTAL_LEADERS, worst=worst)
        cols = list(dict.fromkeys(['first_name', 'last_name', stat, 'season', qual_col, 'team']))
        df = df[cols].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'player', '')
        conf_sections = []
        for conf in _conf_order:
            abbrs = _conf_teams[conf]
            cdf = get_leaders(stat, num=_CONF_LEADERS, worst=worst, teams=abbrs)
            cdf = cdf[cols].copy()
            cdf.insert(0, '#', cdf.index)
            cdf.insert(1, 'player', '')
            conf_sections.append((conf, cdf))
        pages.append((title, slug, 'season', df, False, conf_sections))

        df = get_leaders_by_season(stat, worst=worst)
        cols = list(dict.fromkeys(['season', 'first_name', 'last_name', stat, qual_col, 'team']))
        df = df[cols].copy()
        df.insert(1, 'player', '')
        conf_sections = []
        for conf in _conf_order:
            abbrs = _conf_teams[conf]
            cdf = get_leaders_by_season(stat, worst=worst, teams=abbrs)
            cdf = cdf[cols].copy()
            cdf.insert(1, 'player', '')
            conf_sections.append((conf, cdf))
        pages.append((title, slug, 'seasonal', df, False, conf_sections))

        career_cols = list(dict.fromkeys(['first_name', 'last_name', stat, qual_col]))

        df = get_career_leaders(stat, num=_TOTAL_LEADERS, worst=worst)
        df = df[career_cols].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'player', '')
        pages.append((title, slug, 'career', df, False, []))

        df = get_career_leaders(stat, active=True, num=_CONF_LEADERS, worst=worst)
        df = df[career_cols].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'player', '')
        pages.append((title, slug, 'active', df, False, []))

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

        if stat == 'p_ip':
            season_cols = ['first_name', 'last_name', 'role', 'p_ip', 'season', 'team']
            seasonal_cols = ['season', 'first_name', 'last_name', 'role', 'p_ip', 'team']
            career_cols = ['first_name', 'last_name', 'role', 'p_ip']
        else:
            season_cols = ['first_name', 'last_name', 'role', stat, 'season', 'p_ip', 'team']
            seasonal_cols = ['season', 'first_name', 'last_name', 'role', stat, 'p_ip', 'team']
            career_cols = ['first_name', 'last_name', 'role', stat, 'p_ip']

        # Season table
        df = get_leaders(stat, num=_TOTAL_LEADERS, worst=worst)
        df = df[list(dict.fromkeys(season_cols))].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'player', '')
        conf_sections = []
        for conf in _conf_order:
            abbrs = _conf_teams[conf]
            cdf = get_leaders(stat, num=_CONF_LEADERS, worst=worst, teams=abbrs)
            cdf = cdf[list(dict.fromkeys(season_cols))].copy()
            cdf.insert(0, '#', cdf.index)
            cdf.insert(1, 'player', '')
            conf_sections.append((conf, cdf))
        pages.append((title, slug, 'season', df, True, conf_sections))

        # Seasonal table
        df = get_leaders_by_season(stat, worst=worst)
        df = df[list(dict.fromkeys(seasonal_cols))].copy()
        df.insert(1, 'player', '')
        conf_sections = []
        for conf in _conf_order:
            abbrs = _conf_teams[conf]
            cdf = get_leaders_by_season(stat, worst=worst, teams=abbrs)
            cdf = cdf[list(dict.fromkeys(seasonal_cols))].copy()
            cdf.insert(1, 'player', '')
            conf_sections.append((conf, cdf))
        pages.append((title, slug, 'seasonal', df, True, conf_sections))

        # Career role lookup
        import pitching as _pit
        season_role = (
            _pit.stats[_pit.stats['stat_type'] == 'season']
            .sort_values('season')
            .groupby(['first_name', 'last_name'])['role']
            .last()
        )

        def _apply_role(d):
            d = d.copy()
            d['role'] = d.apply(lambda r: season_role.get((r['first_name'], r['last_name']), r['role']), axis=1)
            return d

        # Career table
        df = _apply_role(get_career_leaders(stat, num=_TOTAL_LEADERS, worst=worst))
        df = df[list(dict.fromkeys(career_cols))].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'player', '')
        pages.append((title, slug, 'career', df, True, []))

        # Active table
        df = _apply_role(get_career_leaders(stat, active=True, num=_CONF_LEADERS, worst=worst))
        df = df[list(dict.fromkeys(career_cols))].copy()
        df.insert(0, '#', df.index)
        df.insert(1, 'player', '')
        pages.append((title, slug, 'active', df, True, []))

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
        with table(cls='leaders-index'):
            with thead():
                tr(th("Statistic"), th("Single-Season"), th("Seasonal"), th("Career"), th("Active"))
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
        'seasonal': 'Seasonal Leaders',
        'career': 'Career Leaders',
        'active': 'Active Leaders',
    }

    for title, slug, suffix, df, is_pitching, conf_sections in pages:
        stat_cols = [c for c in df.columns if c in REGISTRY and REGISTRY[c].get('type', 'stat') == 'stat']
        display_name = REGISTRY[stat_cols[0]]['name'] if stat_cols else slug
        subdoc = make_doc(f"{display_name} - {labels[suffix]}")
        with subdoc:
            h1(f"{labels[suffix]} for {title}")
            render_table(df, depth=1)
            for conf, cdf in conf_sections:
                h2(conf)
                render_table(cdf, depth=1)
        Path(f"docs/leaders/{slug}_{suffix}.html").write_text(str(subdoc))
