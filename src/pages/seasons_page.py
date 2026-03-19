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
        'G', 'PA', 'AB', 'R', 'H', '1B', '2B', '3B', 'HR', 'RBI',
        'SB', 'CS', 'BB', 'K', 'TB', 'HBP', 'SH', 'SF', 'BIP',
    ]])

    def_raw = sp[['G', 'CG', 'SHO', 'SV', 'IP_true', 'H', 'RA', 'ER', 'HR',
                  'BB', 'K', 'HBP', 'WP', 'BF', 'TP']].copy()
    def_raw['E']  = sb['E']
    def_raw['PB'] = sb['PB']
    def_count = fmt_df(def_raw).rename(columns={'IP_true': 'IP', 'RA': 'R'})

    # ── Per game ──────────────────────────────────────────────────────────────

    off_pg_raw = sb[[
        'G', 'PA', 'AB', 'R', 'H', '1B', '2B', '3B', 'HR', 'RBI',
        'SB', 'CS', 'BB', 'K', 'TB', 'HBP', 'SH', 'SF', 'BIP',
    ]]
    off_pg = per_game_df(off_pg_raw).map(lambda x: f"{x:.2f}")
    off_pg.drop('G', axis=1, inplace=True)

    def_pg_raw = sp[['G', 'CG', 'SHO', 'SV', 'IP_true', 'H', 'RA', 'ER', 'HR',
                     'BB', 'K', 'HBP', 'WP', 'BF', 'TP']].copy()
    def_pg_raw['E']  = sb['E']
    def_pg_raw['PB'] = sb['PB']
    def_pg = per_game_df(def_pg_raw).map(lambda x: f"{x:.2f}")
    def_pg = def_pg.rename(columns={'IP_true': 'IP', 'RA': 'R'})
    def_pg.drop('G', axis=1, inplace=True)

    # ── Rates ─────────────────────────────────────────────────────────────────

    rates = pd.DataFrame({
        'R/G':   sb['R/G'],
        'AVG':   sb['AVG'],
        'OBP':   sb['OBP'],
        'SLG':   sb['SLG'],
        'OPS':   sb['OPS'],
        'wOBA':  sb['wOBA'],
        'SB%':   sb['SB%'],
        'RA9':   sp['RA9'],
        'ERA':   sp['ERA'],
        'WHIP':  sp['WHIP'],
        'BABIP': sp['BABIP'],
        'K%':    sp['K%'],
        'BB%':   sp['BB%'],
        'HR%':   sp['HR%'],
        'P/IP':  sp['P/IP'],
        'P/PA':  sp['P/PA'],
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
