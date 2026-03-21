"""Formatting helpers shared across page generators."""
import numpy as np
import dominate
from dominate.tags import link


def fit_metrics(y, preds):
    """Return r2 and rmse for a fitted model given actuals y and predictions preds."""
    residuals = y - preds
    rmse      = np.sqrt(np.mean(residuals ** 2))
    ss_res    = np.sum(residuals ** 2)
    ss_tot    = np.sum((y - y.mean()) ** 2)
    return {
        'r2':   1 - ss_res / ss_tot if ss_tot > 0 else 0.0,
        'rmse': rmse,
    }


def make_doc(title, css='../style.css'):
    """Create a dominate document pre-linked to the global stylesheet.

    css - relative path from the page's location to docs/style.css.
          Use '../style.css' for pages in subdirectories (default).
          Use 'style.css' for pages at the docs/ root.
    """
    doc = dominate.document(title=title)
    with doc.head:
        link(rel='stylesheet', href=css)
    return doc


def rank_column(series, ascending=False):
    """Return a list of 1-based ranks with standard competition ranking (1,1,3,...) for ties."""
    ranks = []
    prev_val = None
    prev_rank = 0
    for i, val in enumerate(series, 1):
        if val != prev_val:
            prev_rank = i
            prev_val = val
        ranks.append(prev_rank)
    return ranks


def fmt_rdiff(v):
    """Format a run differential value, prefixing positive values with '+'."""
    return f"+{v}" if v > 0 else str(v)


def fmt_ip(v):
    """Format a decimal IP value into base-3 baseball notation (e.g. 6.667 -> '6.2')."""
    try:
        if np.isnan(v):
            return '-'
    except (TypeError, ValueError):
        pass
    whole  = int(v)
    thirds = int((v - whole) * 3 + 0.5)
    return f"{whole}.{thirds}"


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
    from stats_meta import ALL_STATS
    all_stats = ALL_STATS

    g = df['G']
    out = df.copy()
    for col in out.columns:
        if col == 'G':
            continue
        is_counting = (col in all_stats and all_stats[col]['decimal_places'] == 0) or col == 'IP_true'
        if is_counting:
            out[col] = out[col] / g
    return out


def fmt_df(df):
    """Return a display copy of df with stats_meta-registered columns formatted as strings.
    The original DataFrame is not modified, preserving numeric types for calculations."""
    from stats_meta import ALL_STATS
    all_stats = ALL_STATS

    out = df.copy()
    for col in out.columns:
        if col not in all_stats:
            continue
        meta = all_stats[col]
        if col == 'IP_true':
            out[col] = out[col].map(fmt_ip)
        else:
            out[col] = out[col].map(
                lambda v, m=meta: fmt_round(v, m['decimal_places'], m['leading_zero'], m['percentage'])
            )
    return out



def render_table(df, *, prefix='', hidden=None, row_class=None, cell_style=None, border=0):
    """Render a DataFrame as a dominate table with formatting, bolding, and player links.

    df         - DataFrame; may contain 'First Name'/'Last Name' for Player links,
                 'stat_type' for row CSS classes, 'Season'/'Team' for bolding lookups.
    prefix     - prepended to player link hrefs (e.g. '../players/').
    hidden     - set of column names to exclude from display; 'stat_type', 'First Name',
                 and 'Last Name' are always hidden.
    row_class  - callable (row) -> str override for <tr> CSS class.
    cell_style - callable (col, raw_val, row) -> str or None for inline style= on cells.
    border     - HTML border attribute on <table>.
    """
    import numpy as np
    from dominate.tags import table, thead, tbody, tr, th, td
    from dominate.tags import b as bold_tag, i as italic_tag, a as anchor_tag
    from stats_meta import ALL_STATS, COLUMN_META
    import leaders as leaders_mod
    from data import teams as teams_data
    from leaders import SEASON_THRESHOLDS

    _always_hidden = {'stat_type', 'First Name', 'Last Name'}
    _hidden = _always_hidden | (set(hidden) if hidden else set())

    def _resolve_meta(col):
        if col in ALL_STATS:
            return ALL_STATS[col]
        if col in COLUMN_META:
            return COLUMN_META[col]
        return {'name': col, 'type': 'text', 'align': 'right'}

    def _header_name(col, meta):
        if meta.get('type') == 'stat':
            return meta.get('display_col') or col
        return meta.get('name', col)

    def _format_cell(col, meta, val):
        ctype = meta.get('type', 'text')
        if col == 'IP_true' or ctype == 'ip':
            return fmt_ip(val)
        if ctype == 'stat':
            return fmt_round(val, meta['decimal_places'], meta['leading_zero'], meta['percentage'])
        if ctype == 'integer':
            try:
                if isinstance(val, float) and np.isnan(val):
                    return '-'
                return str(int(val))
            except (ValueError, TypeError):
                return str(val) if val is not None else '-'
        return str(val) if val is not None else ''

    visible_cols = [c for c in df.columns if c not in _hidden]
    has_player_link = ('Player' in visible_cols
                       and 'First Name' in df.columns
                       and 'Last Name' in df.columns)
    col_meta = {c: _resolve_meta(c) for c in visible_cols}

    bat_ldr      = leaders_mod.batting_leaders
    pit_ldr      = leaders_mod.pitching_leaders
    bat_ldr_conf = leaders_mod.batting_leaders_conf
    pit_ldr_conf = leaders_mod.pitching_leaders_conf

    abbr_to_conf = {}
    if teams_data.teams is not None:
        abbr_to_conf = teams_data.teams.set_index('abbr')['conference_name'].to_dict()

    # Detect batting vs pitching table: pitcher tables always include IP_true.
    _is_pitching_table = 'IP_true' in df.columns

    def _leaders_for_col(col):
        """Return (overall_ldr, conf_ldr_dict) for a stat column, or (None, None).
        Check pitching leaders first for pitcher tables so overlapping stat names
        (K, BB, HR, H, HBP) resolve to the correct leaders DataFrame."""
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
                    th(_header_name(col, col_meta[col]))
        with tbody():
            for _, raw_row in df.iterrows():
                stat_type = raw_row['stat_type'] if 'stat_type' in df.columns else ''
                cls = row_class(raw_row) if row_class is not None else stat_type
                with tr(cls=cls):
                    for col in visible_cols:
                        meta    = col_meta[col]
                        raw_val = raw_row[col]

                        # Build display content
                        if col == 'Player' and has_player_link:
                            first = raw_row['First Name']
                            last  = raw_row['Last Name']
                            slug  = convert_name(first, last)
                            content = anchor_tag(f"{first} {last}", href=f"{prefix}{slug}.html")
                        else:
                            disp_val = _format_cell(col, meta, raw_val)

                            # Bolding: only stat columns on season rows
                            is_bold = is_italic = False
                            if stat_type == 'season' and meta.get('type') == 'stat':
                                overall_ldr, conf_ldr_dict = _leaders_for_col(col)
                                if overall_ldr is not None:
                                    season = raw_row.get('Season')
                                    try:
                                        fval     = float(raw_val)
                                        qual_col = meta.get('qual_col', 'PA')
                                        qualifies = (
                                            not meta['qualified']
                                            or raw_row.get(qual_col, 0) >= SEASON_THRESHOLDS.get(qual_col, 0)
                                        )
                                        if qualifies and season in overall_ldr.index and col in overall_ldr.columns:
                                            best_o = float(overall_ldr.loc[season, col])
                                            overall_best = fval <= best_o if meta['lowest'] else fval >= best_o

                                            if conf_ldr_dict and 'Team' in df.columns:
                                                team     = raw_row.get('Team', '')
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

                        style_str = cell_style(col, raw_val, raw_row) if cell_style else None
                        if style_str:
                            td(content, style=style_str)
                        else:
                            td(content)
    return t




def convert_name(first, last):
    """Turn a player name into a filename-safe string."""
    return f"{first.replace(' ', '')}{last.replace(' ', '')}"


def player_link(first, last, prefix='../players/', label=None):
    """Return a dominate <a> tag linking to a player page.

    prefix - relative path from the calling page's directory to docs/players/.
             Defaults to '../players/' for pages one level deep (teams/, leaders/).
             Use 'players/' for pages at the docs/ root.
             Use '' for pages already inside docs/players/.
    label  - link text; defaults to 'First Last'.
    """
    from dominate.tags import a
    href = f"{prefix}{convert_name(first, last)}.html"
    return a(label or f"{first} {last}", href=href)


def min_prefix(names):
    """Return the shortest unique prefix for each name in the list."""
    unique_names = list(set(names))
    result = {}
    for name in unique_names:
        for length in range(1, len(name) + 1):
            prefix = name[:length]
            if sum(n.startswith(prefix) for n in unique_names) == 1:
                result[name] = prefix
                break
    return result


def weighted_avg(df, stat, weight_col):
    """Weighted average of stat by weight_col; returns 0 if total weight is zero."""
    w = df[weight_col].sum()
    return (df[stat] * df[weight_col]).sum() / w if w != 0 else 0.0


def resolve_conflicts(df):
    """Add a 'Boxscore Name' column that disambiguates players sharing a surname."""
    df = df.copy()
    groups = df.groupby('Last Name')['First Name'].apply(list)

    def get_boxscore(row):
        last       = row['Last Name']
        first      = row['First Name']
        first_names = groups[last]
        if len(set(first_names)) <= 1:
            return last
        prefix = min_prefix(first_names)[first]
        return f"{last}, {prefix}"

    df['Boxscore Name'] = df.apply(get_boxscore, axis=1)
    return df
