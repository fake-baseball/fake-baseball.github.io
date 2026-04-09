"""Generate an HTML page for a single pitcher."""
from pathlib import Path

import numpy as np
import pandas as pd
from dominate.tags import *
from dominate.util import raw

import pitching
import leaders
import pit_projections as pit_proj_module
from data import players
from data import teams as teams_data
from constants import CURRENT_SEASON, LAST_COMPLETED_SEASON
from registry import REGISTRY
from pages.page_utils import fmt_round, render_table, convert_name, make_doc
from util import fmt_ip
from data.stats import pitching_stream_rows
from leaders import SEASON_THRESHOLDS
from team_ranks import PIT_RANK_COLS, ordinal

_PIT_SUMMARY_COLS = ['season', 'p_war', 'p_w', 'p_l', 'p_era', 'p_gp', 'p_gs', 'p_sv', 'p_ip', 'p_k', 'p_whip']


def _pit_summary_table(stats, proj_row):
    """Render BB-ref style summary strip: current season, Projected, Career."""
    s_cur  = stats[(stats['season'] == CURRENT_SEASON)        & (stats['stat_type'] == 'season')]
    s_last = stats[(stats['season'] == LAST_COMPLETED_SEASON) & (stats['stat_type'] == 'season')]
    s_row  = s_cur if not s_cur.empty else s_last
    career = stats[stats['stat_type'] == 'career']

    frames = []
    if not s_row.empty:
        frames.append(s_row)
    if not career.empty:
        frames.append(career)
    if not frames:
        return

    summary_df = pd.concat(frames)[_PIT_SUMMARY_COLS + ['stat_type']]
    render_table(summary_df, depth=1)

def _pit_proj_row(first, last, cols):
    """Return a single-row DataFrame for the projected season, or None."""
    rows = pit_proj_module.compute_all()
    proj = next((r for r in rows if r['first'] == first and r['last'] == last), None)
    if proj is None:
        return None

    ip   = proj['proj_ip']
    xk   = proj['p_k']
    xbb  = proj['p_bb']
    xhbp = proj['p_hbp']
    xhr  = proj['p_hr']
    xh   = proj['p_h']

    out_rate = 1.0 - proj['p_h_rate'] - proj['p_bb_rate'] - proj['p_hbp_rate']
    xbf  = int(round(ip * 3.0 / out_rate)) if out_rate > 0 else np.nan
    xbip = (xbf - xk - xbb - xhbp - xhr) if not np.isnan(float(xbf)) else np.nan
    xra  = proj['p_ra9'] * ip / 9.0 if ip > 0 else 0.0

    pi_row = players.player_info.loc[(first, last)] if (first, last) in players.player_info.index else None
    if pi_row is not None:
        abbr_map = teams_data.teams.set_index('team_name')['abbr']
        team_abbr = abbr_map.get(pi_row['team_name'], '')
    else:
        team_abbr = ''
    d = {col: np.nan for col in cols}
    d.update({
        'season': 'Proj', 'stat_type': 'projected',
        'age':  pi_row['age'] if pi_row is not None else np.nan,
        'team': team_abbr,
        'p_w': proj['p_w'], 'p_l': proj['p_l'],
        'p_win_pct': proj['p_w'] / (proj['p_w'] + proj['p_l']) if (proj['p_w'] + proj['p_l']) > 0 else np.nan,
        'p_gp': proj['p_gp'], 'p_gs': proj['p_gs'], 'p_sv': proj['p_sv'],
        'p_ip': ip,
        'p_h': xh, 'p_hr': xhr, 'p_bb': xbb, 'p_k': xk, 'p_hbp': xhbp,
        'p_bf': xbf, 'p_bip': xbip, 'p_ra': xra,
        'p_er': proj['p_er'], 'p_era': proj['p_era'], 'p_era_minus': proj['p_era_minus'],
        'p_fip': proj['p_fip'], 'p_whip': proj['p_whip'],
        'p_ra9': proj['p_ra9'], 'p_babip': proj['p_babip'],
        'p_k_pct': proj['p_k_pct'], 'p_bb_pct': proj['p_bb_pct'],
        'p_war': proj['p_war'],
        'p_baa': proj['p_baa'], 'p_obpa': proj['p_obpa'],
        'p_r_def': proj['p_r_def'], 'p_r_lev': proj['p_r_lev'], 'p_r_corr': proj['p_r_corr'],
        'p_raa': proj['p_raa'], 'p_raa_lev': proj['p_raa_lev'], 'p_waa': proj['p_waa'],
        'p_r_rep': proj['p_r_rep'], 'p_rar': proj['p_rar'],
    })
    if ip > 0:
        d['p_h_per_9']  = xh  / ip * 9
        d['p_hr_per_9'] = xhr / ip * 9
        d['p_k_per_9']  = xk  / ip * 9
        d['p_bb_per_9'] = xbb / ip * 9
        if xbb > 0:
            d['p_k_per_bb'] = xk / xbb
    return pd.DataFrame([d])


_PIT_STREAM_COLS = [
    'stream', 'p_w', 'p_l', 'p_win_pct', 'p_era', 'p_fip', 'p_gp', 'p_gs', 'p_cg', 'p_sho', 'p_sv', 'p_ip',
    'p_h', 'p_ra', 'p_er', 'p_hr', 'p_bb', 'p_k', 'p_hbp', 'p_wp', 'p_bf', 'p_tp', 'p_whip', 'p_babip',
    'stat_type',
]


def _pit_rankings_section(first_name, last_name, player_seasons):
    """Render a Rankings table: one row per season, one column per PIT_RANK_COL."""
    import league as lg
    all_seasons = pitching.stats[pitching.stats['stat_type'] == 'season'].copy()
    cols = [c for c in PIT_RANK_COLS if c in all_seasons.columns]

    rows = []
    for _, ps in player_seasons.iterrows():
        season = ps['season']
        season_df = all_seasons[all_seasons['season'] == season]
        if season_df.empty:
            continue
        row = {'season': season}
        for col in cols:
            meta = REGISTRY.get(col, {})
            qualified = meta.get('qualified', False)
            lowest = meta.get('lowest', False)
            qual_col = meta.get('qual_col', 'p_ip')
            if qualified:
                base = SEASON_THRESHOLDS.get(qual_col, 0)
                scale = lg.season_scale.get(season, 1.0)
                threshold = base * scale
                pool = season_df[season_df[qual_col] >= threshold]
                player_val = ps.get(col, np.nan)
                if pd.isna(player_val) or (ps.get(qual_col, 0) < threshold):
                    row[col] = '--'
                    continue
            else:
                pool = season_df
                player_val = ps.get(col, np.nan)
                if pd.isna(player_val):
                    row[col] = '--'
                    continue

            vals = pool[col].dropna()
            if vals.empty:
                row[col] = '--'
                continue
            if lowest:
                rank_val = int((vals < player_val).sum() + 1)
                tied = (vals == player_val).sum() > 1
            else:
                rank_val = int((vals > player_val).sum() + 1)
                tied = (vals == player_val).sum() > 1
            row[col] = ('T-' if tied else '') + ordinal(rank_val)
        rows.append(row)

    if not rows:
        return

    h2("Rankings")
    col_headers = ['Season'] + [REGISTRY.get(c, {}).get('name', c) for c in cols]
    with table(cls='leaders-index'):
        with thead():
            with tr():
                for hdr in col_headers:
                    th(hdr)
        with tbody():
            for row in rows:
                with tr():
                    td(str(row['season']))
                    for col in cols:
                        td(row.get(col, '--'))


def _pit_streams_section(first, last):
    stream_rows = pitching_stream_rows(first, last)
    if not stream_rows:
        return

    frames = []
    for row in stream_rows:
        d = {c: np.nan for c in _PIT_STREAM_COLS}
        d['stream']    = row['stream']
        d['stat_type'] = 'season'
        for key in ('p_w', 'p_l', 'p_win_pct', 'p_era', 'p_fip', 'p_gp', 'p_gs', 'p_cg', 'p_sho', 'p_sv',
                    'p_ip', 'p_h', 'p_ra', 'p_er', 'p_hr', 'p_bb', 'p_k', 'p_hbp', 'p_wp', 'p_bf', 'p_tp',
                    'p_whip', 'p_babip'):
            if key in row:
                d[key] = row[key]
        frames.append(d)

    # Season total row from the already-computed stats (includes WAR, ERA-, FIP, etc.)
    s21 = pitching.stats[
        (pitching.stats['first_name'] == first) &
        (pitching.stats['last_name']  == last)  &
        (pitching.stats['season'] == CURRENT_SEASON) &
        (pitching.stats['stat_type'] == 'season')
    ]
    if not s21.empty:
        total = s21.iloc[0].reindex(_PIT_STREAM_COLS).copy()
        total['stream']    = 'Season'
        total['stat_type'] = 'career'
        frames.append(total.to_dict())

    if not frames:
        return

    stream_df = pd.DataFrame(frames, columns=_PIT_STREAM_COLS)
    h2("Stream Log")
    render_table(stream_df, depth=1)


def generate_pitcher_page(first_name, last_name):
    if (first_name, last_name) in players.player_info.index:
        active          = True
        pi              = players.player_info.loc[(first_name, last_name)]
        team_name       = pi['team_name']
        jersey_number   = pi['jersey']
        throw_hand      = pi['throws']
        pitcher_role    = pi['role']
        pitcher_arsenal = pi['arsenal']
        age             = pi['age']
        salary          = pi['salary']
    else:
        active = False
        mask   = (pitching.stats['last_name'] == last_name) & (pitching.stats['first_name'] == first_name)
        pitcher_role = pitching.stats.loc[mask, 'role'].iloc[0]
        try:
            ret_mask          = (players.retired_pitchers['last_name'] == last_name) & (players.retired_pitchers['first_name'] == first_name)
            retirement_season = players.retired_pitchers.loc[ret_mask, 'Retirement Season'].iloc[0]
            retirement_age    = players.retired_pitchers.loc[ret_mask, 'age'].iloc[0]
        except (IndexError, KeyError):
            print("Unable to fetch retirement info for", first_name, last_name)
            retirement_season = "Unknown"
            retirement_age    = "Unknown"

    doc = make_doc(f"{first_name} {last_name}")

    with doc:
        img(src="current.jpeg", width=100)
        h1(f"{first_name} {last_name}")

        if active:
            strong(f"{team_name} #{jersey_number}")
            p(f"Age: {age}")
            p(f"Throws: {throw_hand}")
            p(f"Role: {pitcher_role}")
            p(f"Arsenal: {pitcher_arsenal}")
            p(f"Skills: VEL {pi['velocity']} / JNK {pi['junk']} / ACC {pi['accuracy']}")
            p(f"Salary: ${salary:.1f}m")
        else:
            strong("Retired")
            p(f"Role: {pitcher_role}")
            p(f"Retirement Season: {retirement_season}")
            p(f"Retirement Age: {retirement_age}")

        hr()

        stats = pitching.stats[
            (pitching.stats['last_name']  == last_name) &
            (pitching.stats['first_name'] == first_name)
        ].copy()

        proj_row = _pit_proj_row(first_name, last_name, stats.columns) if active else None
        _pit_summary_table(stats, proj_row)

        if active and proj_row is not None:
            season = stats[stats['stat_type'] == 'season']
            career = stats[stats['stat_type'] == 'career']
            team   = stats[stats['stat_type'] == 'team']
            stats  = pd.concat([season, proj_row, career, team], ignore_index=True)

        h2("Stats")

        h3("Standard Pitching")
        standard_pitching = stats[[
            'season', 'age', 'team', 'p_war',
            'p_w', 'p_l', 'p_win_pct', 'p_era', 'p_gp', 'p_gs', 'p_cg', 'p_sho', 'p_sv', 'p_ip',
            'p_h', 'p_ra', 'p_er', 'p_hr', 'p_bb', 'p_k', 'p_hbp', 'p_wp', 'p_bf', 'p_era_minus', 'p_fip', 'p_whip',
            'stat_type',
        ]]
        render_table(standard_pitching, depth=1)

        h3("Advanced Pitching")
        render_table(stats[[
            'season', 'age', 'team', 'p_ip',
            'p_era', 'p_fip', 'p_ra9', 'p_baa', 'p_obpa', 'p_bip', 'p_babip',
            'p_h_per_9', 'p_hr_per_9', 'p_k_per_9', 'p_bb_per_9', 'p_k_per_bb', 'p_k_pct', 'p_bb_pct',
            'p_tp', 'p_p_per_gp', 'p_ip_per_gp', 'p_p_per_ip', 'p_p_per_pa', 'stat_type',
        ]], depth=1)

        h3("Value Pitching")
        render_table(stats[[
            'season', 'age', 'team', 'p_ip', 'p_gp', 'p_gs',
            'p_ra', 'p_r_def', 'p_ra9', 'p_ra9_def', 'p_r_lev', 'p_r_corr',
            'p_raa', 'p_raa_lev', 'p_waa', 'p_r_rep', 'p_rar', 'p_war', 'stat_type',
        ]], depth=1)

        if active:
            player_seasons = pitching.stats[
                (pitching.stats['first_name'] == first_name) &
                (pitching.stats['last_name']  == last_name) &
                (pitching.stats['stat_type'] == 'season')
            ]
            _pit_rankings_section(first_name, last_name, player_seasons)
            _pit_streams_section(first_name, last_name)

        h2("Awards")

    path = Path(f"docs/players/{convert_name(first_name, last_name)}.html")
    path.write_text(str(doc))
