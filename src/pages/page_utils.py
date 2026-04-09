"""Page-generation utilities: document construction, table rendering, and formatting."""
import numpy as np
import dominate
from dominate.tags import link
from dominate.tags import table, thead, tbody, tr, th, td, abbr as abbr_tag
from dominate.tags import b as bold_tag, i as italic_tag, a as anchor_tag

from registry import REGISTRY
from pages.slug import convert_name
from util import fmt_ip, weighted_avg


NAV_LINKS = [
    ("players",     "Players",                "players/index.html"),
    ("leaders",     "Leaders",                "leaders/index.html"),
    ("seasons",     "Seasons",                "seasons/index.html"),
    ("teams",       "Teams",                  "teams/index.html"),
    ("games",       "Games",                  "games/index.html"),
    ("awards",      "Awards",                 "awards.html"),
    ("projections", "Projections",            "projections.html"),
    ("dh",          "Positional Adjustments", "dh.html"),
    ("salaries",    "Salaries",               "salaries.html"),
    ("cy_young",    "Cy Young Predictor",     "cy_young.html"),
    ("glossary",    "Glossary",               "glossary.html"),
]

# Set of active section keys; populated by build.py before page generation.
# When None (e.g. running page generators standalone), all links are shown.
active_sections = None


def make_doc(title, depth=1, nav=True):
    """Create a dominate document pre-linked to the global stylesheet.

    depth - number of directory levels below docs/ root for the calling page.
            0 = docs/ (e.g. index.html), 1 = docs/leaders/, 2 = docs/teams/Team/.
            The href is built as '../' * depth + 'style.css'.
    nav   - if True (default), prepend a site-wide navigation header to the body.
            Pass nav=False for the home page.
    """
    from dominate.tags import nav as nav_tag, span
    root = '../' * depth
    css = root + 'style.css'
    doc = dominate.document(title=title)
    with doc.head:
        link(rel='stylesheet', href=css)
    if nav:
        with doc:
            with nav_tag(cls='site-nav'):
                with anchor_tag(href=root + 'index.html', cls='site-nav-home'):
                    bold_tag('BFBL')
                for key, label, href in NAV_LINKS:
                    if active_sections is None or key in active_sections:
                        anchor_tag(label, href=root + href, cls='site-nav-link')
    return doc


def fmt_rdiff(v):
    """Format a run differential value, prefixing positive values with '+'."""
    return f"+{v}" if v > 0 else str(v)


def fmt_round(v, digits=3, keep_leading_zero=False, percentage=False):
    """Format a float to a fixed number of decimal places, optionally stripping the leading zero.
    If percentage=True, multiplies by 100 before formatting."""
    try:
        if np.isnan(v):
            return '-'
    except (TypeError, ValueError):
        pass
    if percentage:
        v = v * 100
    s = f"{v:.{digits}f}"
    return s if keep_leading_zero or not s.startswith("0") else s[1:]


def per_game_df(df):
    """Return a copy of df with counting stats divided by G (games).
    Rate stats (decimal_places > 0) are left unchanged. Counting stats
    (decimal_places == 0, plus IP_true) are divided by G and shown to 2 dp."""
    g = df['g']
    out = df.copy()
    for col in out.columns:
        if col == 'g':
            continue
        is_counting = (
            (col in REGISTRY and REGISTRY[col].get('decimal_places', 0) == 0
             and REGISTRY[col].get('type', 'stat') == 'stat')
            or (col in REGISTRY and REGISTRY[col].get('type') == 'ip')
        )
        if is_counting:
            out[col] = out[col] / g
    return out


def render_table(df, *, depth=0, hidden=None, row_class=None, cell_style=None, border=0):
    """Render a DataFrame as a dominate table with formatting, bolding, and player links.

    df         - DataFrame; may contain 'first_name'/'last_name' for Player links,
                 'stat_type' for row CSS classes, 'Season'/'Team' for bolding lookups.
    depth      - number of directory levels above docs/ root for the calling page.
                 0 = docs/ (e.g. index.html), 1 = docs/leaders/, 2 = docs/teams/Team/.
                 Player links are built as '../' * depth + 'players/{slug}.html'.
    hidden     - set of column names to exclude from display; 'stat_type', 'first_name',
                 and 'last_name' are always hidden.
    row_class  - callable (row) -> str override for <tr> CSS class.
    cell_style - callable (col, raw_val, row) -> str or None for inline style= on cells.
    border     - HTML border attribute on <table>.
    """
    import leaders as leaders_mod
    from data import teams as teams_data
    from leaders import SEASON_THRESHOLDS
    import league as lg

    _always_hidden = {'stat_type', 'first_name', 'last_name'}
    _hidden = _always_hidden | (set(hidden) if hidden else set())

    _LEFT_ALIGNED  = {'player_link', 'team_link', 'season_link', 'mono', 'text'}
    _RIGHT_ALIGNED = {'stat', 'ip', 'integer', 'salary', 'gb', 'rdiff', 'record'}

    def _align(ctype):
        if ctype in _LEFT_ALIGNED:
            return 'left'
        return 'right'

    def _resolve_meta(col):
        if col in REGISTRY:
            return REGISTRY[col]
        return {'name': col, 'type': 'text'}

    def _header_name(col, meta):
        return meta.get('name', col)

    def _format_cell(col, meta, val):
        ctype = meta.get('type', 'text')
        if ctype == 'ip':
            return fmt_ip(val)
        if ctype == 'stat':
            return fmt_round(val, meta['decimal_places'], meta['leading_zero'], meta['percentage'])
        if ctype == 'salary':
            if isinstance(val, float) and np.isnan(val):
                return '-'
            return f'${float(val):.1f}m'
        if ctype == 'integer':
            if isinstance(val, float) and np.isnan(val):
                return '-'
            try:
                return str(int(val))
            except (ValueError, TypeError):
                return str(val) if val is not None else '-'
        if ctype == 'gb':
            v = float(val)
            return '-' if v == 0 else f'{v:.1f}'
        if ctype == 'rdiff':
            return fmt_rdiff(int(val))
        return str(val) if val is not None else ''

    visible_cols = [c for c in df.columns if c not in _hidden]
    has_name_cols = 'first_name' in df.columns and 'last_name' in df.columns
    col_meta = {c: _resolve_meta(c) for c in visible_cols}

    bat_ldr      = leaders_mod.batting_leaders
    pit_ldr      = leaders_mod.pitching_leaders
    bat_ldr_conf = leaders_mod.batting_leaders_conf
    pit_ldr_conf = leaders_mod.pitching_leaders_conf

    abbr_to_conf = teams_data.teams.set_index('abbr')['conference_name'].to_dict()


    t = table(border=border)
    with t:
        with thead():
            with tr():
                for col in visible_cols:
                    meta = col_meta[col]
                    ctype = meta.get('type', 'text')
                    label = meta.get('label', '')
                    header = _header_name(col, meta)
                    align_style = 'text-align: left' if _align(ctype) == 'left' else None
                    if label:
                        th(abbr_tag(header, title=label), style=align_style) if align_style else th(abbr_tag(header, title=label))
                    else:
                        th(header, style=align_style) if align_style else th(header)
        with tbody():
            for _, raw_row in df.iterrows():
                stat_type = raw_row['stat_type'] if 'stat_type' in df.columns else ''
                cls = row_class(raw_row) if row_class is not None else stat_type
                with tr(cls=cls):
                    for col in visible_cols:
                        meta    = col_meta[col]
                        raw_val = raw_row[col]

                        ctype = meta.get('type', 'text')
                        if ctype == 'player_link' and has_name_cols:
                            first  = raw_row['first_name']
                            last   = raw_row['last_name']
                            slug   = convert_name(first, last)
                            _pfx   = '../' * depth + 'players/'
                            content = anchor_tag(f"{first} {last}", href=f"{_pfx}{slug}.html")
                        elif ctype == 'team_link' and raw_val:
                            team_slug = str(raw_val).replace(' ', '')
                            _pfx = '../' * depth + 'teams/'
                            row_season = raw_row.get('season') if 'season' in df.columns else None
                            try:
                                s_int = int(row_season)
                                href = f"{_pfx}{team_slug}/{s_int}.html"
                            except (ValueError, TypeError):
                                href = f"{_pfx}{team_slug}/index.html"
                            content = anchor_tag(str(raw_val), href=href)
                        elif ctype == 'season_link':
                            try:
                                s_int = int(raw_val)
                            except (ValueError, TypeError):
                                content = str(raw_val) if raw_val is not None else ''
                            else:
                                _pfx = '../' * depth + 'seasons/'
                                content = anchor_tag(f"S{s_int}", href=f"{_pfx}{s_int}.html")
                        else:
                            disp_val = _format_cell(col, meta, raw_val)

                            is_bold = is_italic = False
                            if stat_type == 'season' and meta.get('context') not in (None, 'meta') and meta.get('type') in ('stat', 'ip'):
                                is_pitching_col = meta.get('context') == 'pitching'
                                overall_ldr  = pit_ldr  if is_pitching_col else bat_ldr
                                conf_ldr_dict = pit_ldr_conf if is_pitching_col else bat_ldr_conf
                                season   = raw_row.get('season')
                                fval     = float(raw_val)
                                qual_col = meta.get('qual_col', 'pa')
                                threshold = SEASON_THRESHOLDS.get(qual_col, 0) * lg.season_scale.get(season, 1.0)
                                qualifies = (
                                    not meta['qualified']
                                    or raw_row.get(qual_col, 0) >= threshold
                                )
                                if qualifies and season in overall_ldr.index and col in overall_ldr.columns:
                                    best_o = float(overall_ldr.loc[season, col])
                                    overall_best = fval <= best_o if meta['lowest'] else fval >= best_o

                                    if 'team' in df.columns:
                                        team     = raw_row.get('team', '')
                                        conf     = abbr_to_conf.get(team)
                                        conf_ldr = conf_ldr_dict.get(conf) if conf else None
                                        if conf_ldr is not None and season in conf_ldr.index and col in conf_ldr.columns:
                                            best_c    = float(conf_ldr.loc[season, col])
                                            conf_best = fval <= best_c if meta['lowest'] else fval >= best_c
                                            is_bold   = conf_best
                                            is_italic = overall_best
                                        else:
                                            is_bold = overall_best
                                    else:
                                        is_bold = overall_best

                            if is_bold and is_italic:
                                content = bold_tag(italic_tag(disp_val))
                            elif is_bold:
                                content = bold_tag(disp_val)
                            elif is_italic:
                                content = italic_tag(disp_val)
                            else:
                                content = disp_val

                        align_style = 'text-align: left' if _align(ctype) == 'left' else None
                        extra_style = cell_style(col, raw_val, raw_row) if cell_style else None
                        style_str = '; '.join(filter(None, [align_style, extra_style])) or None
                        is_name_col = ctype in ('player_link', 'team_link')
                        is_streak_col = ctype == 'mono'
                        cls_val = 'name-col' if is_name_col else ('mono-col' if is_streak_col else None)
                        if style_str and cls_val:
                            td(content, style=style_str, cls=cls_val)
                        elif style_str:
                            td(content, style=style_str)
                        elif cls_val:
                            td(content, cls=cls_val)
                        else:
                            td(content)
    return t


def player_link(first, last, depth=1, label=None):
    """Return a dominate <a> tag linking to a player page.

    depth - number of directory levels above docs/ root for the calling page.
            0 = docs/ (e.g. index.html), 1 = docs/leaders/, 2 = docs/teams/Team/.
            The href is built as '../' * depth + 'players/{slug}.html'.
    label - link text; defaults to 'First Last'.
    """
    from dominate.tags import a
    prefix = '../' * depth + 'players/'
    href = f"{prefix}{convert_name(first, last)}.html"
    return a(label or f"{first} {last}", href=href)
