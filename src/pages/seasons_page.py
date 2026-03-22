"""Generate the Seasons page (docs/seasons.html)."""
import pandas as pd
from pathlib import Path

from dominate.tags import *
from dominate.util import raw

import league as lg
from util import fmt_df, per_game_df, make_doc


def generate_seasons():
    sb = lg.season_batting
    sp = lg.season_pitching

    # ── Counting ─────────────────────────────────────────────────────────────

    off_count = fmt_df(sb[[
        'g', 'pa', 'ab', 'r', 'h', 'b_1b', 'b_2b', 'b_3b', 'hr', 'rbi',
        'sb', 'cs', 'bb', 'k', 'tb', 'hbp', 'sh', 'sf', 'bip',
    ]])

    def_raw = sp[['g', 'p_cg', 'p_sho', 'p_sv', 'p_ip', 'p_h', 'p_ra', 'p_er', 'p_hr',
                  'p_bb', 'p_k', 'p_hbp', 'p_wp', 'p_bf', 'p_tp']].copy()
    def_raw['e']  = sb['e']
    def_raw['pb'] = sb['pb']
    def_count = fmt_df(def_raw).rename(columns={'RA': 'R'})

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

    rates = pd.DataFrame({
        'r_per_g':    sb['r_per_g'],
        'avg':        sb['avg'],
        'obp':        sb['obp'],
        'slg':        sb['slg'],
        'ops':        sb['ops'],
        'woba':       sb['woba'],
        'sb_pct':     sb['sb_pct'],
        'p_ra9':      sp['p_ra9'],
        'p_era':      sp['p_era'],
        'p_whip':     sp['p_whip'],
        'p_babip':    sp['p_babip'],
        'p_k_pct':    sp['p_k_pct'],
        'p_bb_pct':   sp['p_bb_pct'],
        'p_hr_pct':   sp['p_hr_pct'],
        'p_p_per_ip': sp['p_p_per_ip'],
        'p_p_per_pa': sp['p_p_per_pa'],
    }, index=sb.index)
    rates = fmt_df(rates)

    def _link_index(df):
        df = df.copy()
        df.index = [f'<a href="{i}.html">Season {i}</a>' for i in df.index]
        return df

    # ── Page ──────────────────────────────────────────────────────────────────

    doc = make_doc("Seasons")
    with doc:
        h1("Seasons")

        h2("Counting Stats")
        h3("Offense")
        raw(_link_index(off_count).to_html(border=0, index=True, escape=False))
        h3("Defense")
        raw(_link_index(def_count).to_html(border=0, index=True, escape=False))

        h2("Per-Game Counting")
        h3("Offense")
        raw(_link_index(off_pg).to_html(border=0, index=True, escape=False))
        h3("Defense")
        raw(_link_index(def_pg).to_html(border=0, index=True, escape=False))

        h2("Rate Stats")
        raw(_link_index(rates).to_html(border=0, index=True, escape=False))

    Path("docs/seasons/index.html").write_text(str(doc))
