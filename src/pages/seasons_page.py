"""Generate the Seasons page (docs/seasons.html)."""
import pandas as pd
from pathlib import Path

from dominate.tags import *
from dominate.util import raw

import league as lg
from pages.page_utils import per_game_df, make_doc, render_table


def _season_df(df, cols):
    """Reset index to season column and add stat_type for render_table."""
    out = df[cols].copy()
    out.index.name = 'season'
    out = out.reset_index()
    out['stat_type'] = 'league'
    return out


def _link_index(df):
    df = df.copy()
    df.index = [f'<a href="{i}.html">Season {i}</a>' for i in df.index]
    return df


def generate_seasons():
    sb = lg.season_batting
    sp = lg.season_pitching

    # ── Counting ─────────────────────────────────────────────────────────────

    off_count_cols = [
        'g', 'pa', 'ab', 'r', 'h', 'b_1b', 'b_2b', 'b_3b', 'hr', 'rbi',
        'sb', 'cs', 'bb', 'k', 'tb', 'hbp', 'sh', 'sf', 'bip',
    ]
    off_count = _season_df(sb, off_count_cols)

    def_raw = sp[['g', 'p_cg', 'p_sho', 'p_sv', 'p_ip', 'p_h', 'p_ra', 'p_er', 'p_hr',
                  'p_bb', 'p_k', 'p_hbp', 'p_wp', 'p_bf', 'p_tp']].copy()
    def_raw['e']  = sb['e']
    def_raw['pb'] = sb['pb']
    def_count_cols = list(def_raw.columns)
    def_count = _season_df(def_raw, def_count_cols)

    # ── Per game ──────────────────────────────────────────────────────────────

    off_pg_raw = sb[[
        'g', 'pa', 'ab', 'r', 'h', 'b_1b', 'b_2b', 'b_3b', 'hr', 'rbi',
        'sb', 'cs', 'bb', 'k', 'tb', 'hbp', 'sh', 'sf', 'bip',
    ]]
    off_pg = per_game_df(off_pg_raw).map(lambda x: f"{x:.2f}")
    off_pg.drop('g', axis=1, inplace=True)

    def_pg_raw = sp[['g', 'p_cg', 'p_sho', 'p_sv', 'p_ip', 'p_h', 'p_ra', 'p_er', 'p_hr',
                     'p_bb', 'p_k', 'p_hbp', 'p_wp', 'p_bf', 'p_tp']].copy()
    def_pg_raw['e']  = sb['e']
    def_pg_raw['pb'] = sb['pb']
    def_pg = per_game_df(def_pg_raw).map(lambda x: f"{x:.2f}")
    def_pg = def_pg.rename(columns={'p_ra': 'R', 'p_ip': 'IP'})
    def_pg.drop('g', axis=1, inplace=True)

    # ── Rates ─────────────────────────────────────────────────────────────────

    bat_rate_cols = ['r_per_g', 'avg', 'obp', 'slg', 'ops', 'woba', 'sb_pct']
    pit_rate_cols = ['p_ra9', 'p_era', 'p_whip', 'p_babip',
                     'p_k_pct', 'p_bb_pct', 'p_hr_pct', 'p_p_per_ip', 'p_p_per_pa']
    rates_raw = sb[bat_rate_cols].copy()
    rates_raw = rates_raw.join(sp[pit_rate_cols])
    bat_rates = _season_df(sb[bat_rate_cols], bat_rate_cols)
    pit_rates = _season_df(sp[pit_rate_cols], pit_rate_cols)

    # ── Page ──────────────────────────────────────────────────────────────────

    doc = make_doc("Seasons")
    with doc:
        h1("Seasons")

        h2("Counting Stats")
        h3("Offense")
        render_table(off_count, depth=1, pitching=False)
        h3("Defense")
        render_table(def_count, depth=1, pitching=False)

        h2("Per-Game Counting")
        h3("Offense")
        raw(_link_index(off_pg).to_html(border=0, index=True, escape=False))
        h3("Defense")
        raw(_link_index(def_pg).to_html(border=0, index=True, escape=False))

        h2("Rate Stats")
        h3("Batting")
        render_table(bat_rates, depth=1, pitching=False)
        h3("Pitching")
        render_table(pit_rates, depth=1, pitching=False)

    Path("docs/seasons/index.html").write_text(str(doc))
