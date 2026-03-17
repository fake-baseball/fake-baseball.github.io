"""Formatting helpers shared across page generators."""
import dominate
from dominate.tags import link


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


def fmt_ip(v):
    """Format a decimal IP value into base-3 baseball notation (e.g. 6.667 -> '6.2')."""
    whole  = int(v)
    thirds = int((v - whole) * 3 + 0.5)
    return f"{whole}.{thirds}"


def fmt_round(v, digits=3, keep_leading_zero=False, percentage=False):
    """Format a float to a fixed number of decimal places, optionally stripping the leading zero.
    If percentage=True, multiplies by 100 before formatting."""
    if percentage:
        v = v * 100
    s = f"{v:.{digits}f}"
    return s if keep_leading_zero or not s.startswith("0") else s[1:]


def per_game_df(df):
    """Return a copy of df with counting stats divided by G (games).
    Rate stats (decimal_places > 0) are left unchanged. Counting stats
    (decimal_places == 0, plus IP_true) are divided by G and shown to 2 dp."""
    from stats_meta import BATTING_STATS, BASERUNNING_STATS, FIELDING_STATS, PITCHING_STATS
    all_stats = {**BATTING_STATS, **BASERUNNING_STATS, **FIELDING_STATS, **PITCHING_STATS}

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
    from stats_meta import BATTING_STATS, BASERUNNING_STATS, FIELDING_STATS, PITCHING_STATS
    all_stats = {**BATTING_STATS, **BASERUNNING_STATS, **FIELDING_STATS, **PITCHING_STATS}

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
