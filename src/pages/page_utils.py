"""Page-generation utilities: document construction, table rendering, and formatting."""
import numpy as np
import dominate
from dominate.tags import link
from dominate.tags import table, thead, tbody, tr, th, td, abbr as abbr_tag
from dominate.tags import b as bold_tag, i as italic_tag, a as anchor_tag

from registry import REGISTRY
from pages.slug import convert_name
from util import fmt_ip, weighted_avg


def make_doc(title, depth=1):
    """Create a dominate document pre-linked to the global stylesheet.

    depth - number of directory levels below docs/ root for the calling page.
            0 = docs/ (e.g. index.html), 1 = docs/leaders/, 2 = docs/teams/Team/.
            The href is built as '../' * depth + 'style.css'.
    """
    css = '../' * depth + 'style.css'
    doc = dominate.document(title=title)
    with doc.head:
        link(rel='stylesheet', href=css)
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


def render_table(df, *, depth=0, hidden=None, row_class=None, cell_style=None, border=0, pitching):
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

    def _resolve_meta(col):
        if col in REGISTRY:
            return REGISTRY[col]
        return {'name': col, 'type': 'text', 'align': 'right'}

    def _header_name(col, meta):
        return meta.get('name', col)

    def _format_cell(col, meta, val):
        ctype = meta.get('type', 'text')
        if ctype == 'ip':
            return fmt_ip(val)
        if ctype == 'stat':
            return fmt_round(val, meta['decimal_places'], meta['leading_zero'], meta['percentage'])
        if ctype == 'salary':
            try:
                if isinstance(val, float) and np.isnan(val):
                    return '-'
                return f'${float(val):.1f}m'
            except (ValueError, TypeError):
                return str(val) if val is not None else '-'
        if ctype == 'integer':
            try:
                if isinstance(val, float) and np.isnan(val):
                    return '-'
                return str(int(val))
            except (ValueError, TypeError):
                return str(val) if val is not None else '-'
        if ctype == 'gb':
            try:
                v = float(val)
                return '-' if v == 0 else f'{v:.1f}'
            except (ValueError, TypeError):
                return str(val) if val is not None else '-'
        if ctype == 'rdiff':
            try:
                return fmt_rdiff(int(val))
            except (ValueError, TypeError):
                return str(val) if val is not None else '-'
        return str(val) if val is not None else ''

    visible_cols = [c for c in df.columns if c not in _hidden]
    has_player_link = ('player' in visible_cols
                       and 'first_name' in df.columns
                       and 'last_name' in df.columns)
    col_meta = {c: _resolve_meta(c) for c in visible_cols}

    bat_ldr      = leaders_mod.batting_leaders
    pit_ldr      = leaders_mod.pitching_leaders
    bat_ldr_conf = leaders_mod.batting_leaders_conf
    pit_ldr_conf = leaders_mod.pitching_leaders_conf

    abbr_to_conf = {}
    if teams_data.teams is not None:
        abbr_to_conf = teams_data.teams.set_index('abbr')['conference_name'].to_dict()

    _is_pitching_table = pitching

    def _leaders_for_col(col):
        """Return (overall_ldr, conf_ldr_dict) for a stat column, or (None, None).
        Check pitching leaders first for pitcher tables so overlapping stat names
        (K, BB, HR, H, HBP) resolve to the correct leaders DataFrame."""
        # TODO fix this, because we don't use overlapping stat names
        if _is_pitching_table:
            if pit_ldr is not None and col in pit_ldr.columns:
                return pit_ldr, pit_ldr_conf
            if bat_ldr is not None and col in bat_ldr.columns:
                return bat_ldr, bat_ldr_conf
        else:
            if bat_ldr is not None and col in bat_ldr.columns:
                return bat_ldr, bat_ldr_conf
            if pit_ldr is not None and col in pit_ldr.columns:
                return pit_ldr, pit_ldr_conf
        return None, None

    t = table(border=border)
    with t:
        with thead():
            with tr():
                for col in visible_cols:
                    meta = col_meta[col]
                    label = meta.get('label', '')
                    header = _header_name(col, meta)
                    align_style = f"text-align: {meta['align']}" if meta['align'] != 'right' else None
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
                        if col == 'player' and has_player_link:
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
                                _pfx = '../' * depth + 'seasons/'
                                content = anchor_tag(f"S{s_int}", href=f"{_pfx}{s_int}.html")
                            except (ValueError, TypeError):
                                content = str(raw_val) if raw_val is not None else ''
                        else:
                            disp_val = _format_cell(col, meta, raw_val)

                            is_bold = is_italic = False
                            if stat_type == 'season' and meta.get('type') in ('stat', 'ip'):
                                overall_ldr, conf_ldr_dict = _leaders_for_col(col)
                                if overall_ldr is not None:
                                    season = raw_row.get('season')
                                    try:
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

                                            if conf_ldr_dict and 'team' in df.columns:
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
                                    except (ValueError, TypeError):
                                        pass

                            if is_bold and is_italic:
                                content = bold_tag(italic_tag(disp_val))
                            elif is_bold:
                                content = bold_tag(disp_val)
                            elif is_italic:
                                content = italic_tag(disp_val)
                            else:
                                content = disp_val

                        align_style = f"text-align: {meta['align']}" if meta['align'] != 'right' else None
                        extra_style = cell_style(col, raw_val, raw_row) if cell_style else None
                        style_str = '; '.join(filter(None, [align_style, extra_style])) or None
                        td(content, style=style_str) if style_str else td(content)
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
