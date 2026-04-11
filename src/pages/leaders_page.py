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

_LABELS = {
    'season':   'Single-Season Records',
    'seasonal': 'Seasonal Leaders',
    'career':   'Career Leaders',
    'active':   'Active Leaders',
}


def generate_leaders():
    """Build the leaders index page and return a list of page descriptors.

    Each descriptor is a dict with keys: title, slug, stat, meta, worst, is_pitching.
    Pass each descriptor to write_leader_page() to generate the individual page.
    """
    conf_teams = {}
    for row in teams_data.teams.itertuples():
        conf = row.conference_name
        if conf not in conf_teams:
            conf_teams[conf] = []
        conf_teams[conf].append(row.team_id)
    conf_order = list(conf_teams.keys())

    descriptors = []

    def _index_row(title, slug):
        tr(td(title), *[
            td(a(label, href=f"{slug}_{suffix}.html"))
            for label, suffix in zip(
                ['Single-Season', 'Seasonal', 'Career', 'Active'],
                ['season',        'seasonal', 'career', 'active'],
            )
        ])

    def _add(title, slug, stat, meta, worst, is_pitching):
        _index_row(title, slug)
        descriptors.append({
            'title':       title,
            'slug':        slug,
            'stat':        stat,
            'meta':        meta,
            'worst':       worst,
            'is_pitching': is_pitching,
            'conf_order':  conf_order,
            'conf_teams':  conf_teams,
        })

    def _render_batting(stat, meta):
        slug = meta.get('slug', stat)
        if meta['has_worst']:
            _add(meta['label'] + " (Best)",  slug,            stat, meta, worst=False, is_pitching=False)
            _add(meta['label'] + " (Worst)", slug + '_worst', stat, meta, worst=True,  is_pitching=False)
        else:
            _add(meta['label'], slug, stat, meta, worst=False, is_pitching=False)

    def _render_pitching(stat, meta):
        slug = meta.get('slug', stat)
        if meta['has_worst']:
            _add(meta['label'] + " (Best)",  slug,            stat, meta, worst=False, is_pitching=True)
            _add(meta['label'] + " (Worst)", slug + '_worst', stat, meta, worst=True,  is_pitching=True)
        else:
            _add(meta['label'], slug, stat, meta, worst=False, is_pitching=True)

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

    _batting_stats     = {k: v for k, v in REGISTRY.items() if v.get('context') == 'batting'}
    _baserunning_stats = {k: v for k, v in REGISTRY.items() if v.get('context') == 'baserunning'}
    _fielding_stats    = {k: v for k, v in REGISTRY.items() if v.get('context') == 'fielding'}
    _pitching_stats    = {k: v for k, v in REGISTRY.items() if v.get('context') == 'pitching'}

    def _section(title, stat_dict, qual_note, render_fn):
        h2(title)
        has_qualified = any(v['qualified'] for v in stat_dict.values() if v['leaders'])
        if has_qualified:
            p(qual_note)
        with table(cls='leaders-index'):
            with thead():
                tr(th("Statistic"), th("Single-Season"), th("Seasonal"), th("Career"), th("Active"))
            with tbody():
                for stat, meta in stat_dict.items():
                    if meta['leaders']:
                        render_fn(stat, meta)

    doc = make_doc("Leaders")
    with doc:
        h1("Leaders")
        _section("Batting",     _batting_stats,     qual_notes['batting'],     _render_batting)
        _section("Baserunning", _baserunning_stats, qual_notes['baserunning'], _render_batting)
        _section("Fielding",    _fielding_stats,    qual_notes['fielding'],    _render_batting)
        _section("Pitching",    _pitching_stats,    qual_notes['pitching'],    _render_pitching)

    Path("docs/leaders/index.html").write_text(str(doc))

    for desc in descriptors:
        write_leader_page(desc)


def write_leader_page(desc):
    title       = desc['title']
    slug        = desc['slug']
    stat        = desc['stat']
    meta        = desc['meta']
    worst       = desc['worst']
    is_pitching = desc['is_pitching']
    conf_order  = desc['conf_order']
    conf_teams  = desc['conf_teams']

    if is_pitching:
        _write_pitching_pages(title, slug, stat, meta, worst, conf_order, conf_teams)
    else:
        _write_batting_pages(title, slug, stat, meta, worst, conf_order, conf_teams)


def _write_batting_pages(title, slug, stat, meta, worst, conf_order, conf_teams):
    qual_col = meta['qual_col']
    season_cols = list(dict.fromkeys(['player_id', stat, 'season', qual_col, 'team']))
    career_cols = list(dict.fromkeys(['player_id', stat, qual_col]))

    def _conf_sections_season():
        sections = []
        for conf in conf_order:
            cdf = get_leaders(stat, num=_CONF_LEADERS, worst=worst, teams=conf_teams[conf])
            cdf = cdf[season_cols].copy()
            cdf.insert(0, '#', cdf.index)
            cdf.insert(1, 'player', '')
            sections.append((conf, cdf))
        return sections

    def _conf_sections_seasonal():
        sections = []
        for conf in conf_order:
            cdf = get_leaders_by_season(stat, worst=worst, teams=conf_teams[conf])
            cdf = cdf[list(dict.fromkeys(['season', 'player_id', stat, qual_col, 'team']))].copy()
            cdf.insert(1, 'player', '')
            sections.append((conf, cdf))
        return sections

    # Season
    df = get_leaders(stat, num=_TOTAL_LEADERS, worst=worst)
    df = df[season_cols].copy()
    df.insert(0, '#', df.index)
    df.insert(1, 'player', '')
    _write_page(title, slug, 'season', df, _conf_sections_season())

    # Seasonal
    df = get_leaders_by_season(stat, worst=worst)
    df = df[list(dict.fromkeys(['season', 'player_id', stat, qual_col, 'team']))].copy()
    df.insert(1, 'player', '')
    _write_page(title, slug, 'seasonal', df, _conf_sections_seasonal())

    # Career
    df = get_career_leaders(stat, num=_TOTAL_LEADERS, worst=worst)
    df = df[career_cols].copy()
    df.insert(0, '#', df.index)
    df.insert(1, 'player', '')
    _write_page(title, slug, 'career', df, [])

    # Active
    df = get_career_leaders(stat, active=True, num=_CONF_LEADERS, worst=worst)
    df = df[career_cols].copy()
    df.insert(0, '#', df.index)
    df.insert(1, 'player', '')
    _write_page(title, slug, 'active', df, [])


def _write_pitching_pages(title, slug, stat, meta, worst, conf_order, conf_teams):
    import pitching as _pit
    season_role = (
        _pit.stats[_pit.stats['stat_type'] == 'season']
        .sort_values('season')
        .groupby('player_id')['role']
        .last()
    )

    def _apply_role(d):
        d = d.copy()
        d['role'] = d.apply(lambda r: season_role.get(r['player_id'], r['role']), axis=1)
        return d

    if stat == 'p_ip':
        season_cols   = ['player_id', 'role', 'p_ip', 'season', 'team']
        seasonal_cols = ['season', 'player_id', 'role', 'p_ip', 'team']
        career_cols   = ['player_id', 'role', 'p_ip']
    else:
        season_cols   = ['player_id', 'role', stat, 'season', 'p_ip', 'team']
        seasonal_cols = ['season', 'player_id', 'role', stat, 'p_ip', 'team']
        career_cols   = ['player_id', 'role', stat, 'p_ip']

    def _conf_sections_season():
        sections = []
        for conf in conf_order:
            cdf = get_leaders(stat, num=_CONF_LEADERS, worst=worst, teams=conf_teams[conf])
            cdf = cdf[list(dict.fromkeys(season_cols))].copy()
            cdf.insert(0, '#', cdf.index)
            cdf.insert(1, 'player', '')
            sections.append((conf, cdf))
        return sections

    def _conf_sections_seasonal():
        sections = []
        for conf in conf_order:
            cdf = get_leaders_by_season(stat, worst=worst, teams=conf_teams[conf])
            cdf = cdf[list(dict.fromkeys(seasonal_cols))].copy()
            cdf.insert(1, 'player', '')
            sections.append((conf, cdf))
        return sections

    # Season
    df = get_leaders(stat, num=_TOTAL_LEADERS, worst=worst)
    df = df[list(dict.fromkeys(season_cols))].copy()
    df.insert(0, '#', df.index)
    df.insert(1, 'player', '')
    _write_page(title, slug, 'season', df, _conf_sections_season())

    # Seasonal
    df = get_leaders_by_season(stat, worst=worst)
    df = df[list(dict.fromkeys(seasonal_cols))].copy()
    df.insert(1, 'player', '')
    _write_page(title, slug, 'seasonal', df, _conf_sections_seasonal())

    # Career
    df = _apply_role(get_career_leaders(stat, num=_TOTAL_LEADERS, worst=worst))
    df = df[list(dict.fromkeys(career_cols))].copy()
    df.insert(0, '#', df.index)
    df.insert(1, 'player', '')
    _write_page(title, slug, 'career', df, [])

    # Active
    df = _apply_role(get_career_leaders(stat, active=True, num=_CONF_LEADERS, worst=worst))
    df = df[list(dict.fromkeys(career_cols))].copy()
    df.insert(0, '#', df.index)
    df.insert(1, 'player', '')
    _write_page(title, slug, 'active', df, [])


def _write_page(title, slug, suffix, df, conf_sections):
    stat_cols = [c for c in df.columns if c in REGISTRY and REGISTRY[c].get('type', 'stat') == 'stat']
    display_name = REGISTRY[stat_cols[0]]['name'] if stat_cols else slug
    doc = make_doc(f"{display_name} - {_LABELS[suffix]}")
    with doc:
        h1(f"{_LABELS[suffix]} for {title}")
        render_table(df, depth=1)
        for conf, cdf in conf_sections:
            h2(conf)
            render_table(cdf, depth=1)
    Path(f"docs/leaders/{slug}_{suffix}.html").write_text(str(doc))
