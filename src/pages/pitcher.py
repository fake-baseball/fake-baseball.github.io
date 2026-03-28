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

_PIT_SUMMARY_COLS = [
    ('WAR',   'p_war'),  ('W',    'p_w'),   ('L',  'p_l'),   ('ERA', 'p_era'),
    ('ERA-',  'p_era_minus'), ('G',    'p_gp'),  ('GS', 'p_gs'),  ('SV',  'p_sv'),
    ('IP',    'p_ip'), ('BB', 'p_bb'), ('SO', 'p_k'),   ('WHIP', 'p_whip'),
]


def _pit_summary_table(stats, proj_row):
    """Render BB-ref style summary strip: current season, Projected, Career."""
    def _fmt(col, val):
        meta = REGISTRY.get(col)
        if meta is None or (isinstance(val, float) and np.isnan(val)):
            return '-'
        if meta.get('type') == 'ip':
            from util import fmt_ip
            return fmt_ip(val)
        return fmt_round(val, meta['decimal_places'], meta['leading_zero'], meta['percentage'])

    s20    = stats[(stats['season'] == LAST_COMPLETED_SEASON) & (stats['stat_type'] == 'season')]
    career = stats[stats['stat_type'] == 'career']

    rows_data = []
    if not s20.empty:
        rows_data.append((f'Season {LAST_COMPLETED_SEASON}', s20.iloc[0]))
    if proj_row is not None:
        rows_data.append(('Projected', proj_row.iloc[0]))
    if not career.empty:
        rows_data.append(('Career', career.iloc[0]))

    with table(cls='summary'):
        with thead():
            with tr():
                th('')
                for disp, _ in _PIT_SUMMARY_COLS:
                    th(disp)
        with tbody():
            for label, row in rows_data:
                with tr():
                    td(label)
                    for _, col in _PIT_SUMMARY_COLS:
                        td(_fmt(col, row[col]))
from util import fmt_round, fmt_ip, render_table, convert_name, make_doc
from data.stats import pitching_stream_rows


def _pit_proj_row(first, last, cols):
    """Return a single-row DataFrame for the projected season, or None."""
    rows = pit_proj_module.compute_all()
    proj = next((r for r in rows if r['first'] == first and r['last'] == last), None)
    if proj is None:
        return None

    ip   = proj['proj_ip']
    xk   = proj['xK']
    xbb  = proj['xBB']
    xhbp = proj['xHBP']
    xhr  = proj['xHR']
    xh   = proj['xH']

    out_rate = 1.0 - proj['p_h'] - proj['p_bb'] - proj['p_hbp']
    xbf  = int(round(ip * 3.0 / out_rate)) if out_rate > 0 else np.nan
    xbip = (xbf - xk - xbb - xhbp - xhr) if not np.isnan(float(xbf)) else np.nan
    xra  = proj['xRA9'] * ip / 9.0 if ip > 0 else 0.0

    pi_row = players.player_info.loc[(first, last)] if (first, last) in players.player_info.index else None
    if pi_row is not None and teams_data.teams is not None:
        abbr_map = teams_data.teams.set_index('team_name')['abbr']
        team_abbr = abbr_map.get(pi_row['team_name'], '')
    else:
        team_abbr = ''
    d = {col: np.nan for col in cols}
    d.update({
        'season': 'Proj', 'stat_type': 'projected',
        'age':  pi_row['age'] if pi_row is not None else np.nan,
        'team': team_abbr,
        'p_w': proj['xW'], 'p_l': proj['xL'],
        'p_win_pct': proj['xW'] / (proj['xW'] + proj['xL']) if (proj['xW'] + proj['xL']) > 0 else np.nan,
        'p_gp': proj['xGP'], 'p_gs': proj['xGS'], 'p_sv': proj['xSV'],
        'p_ip': ip,
        'p_h': xh, 'p_hr': xhr, 'p_bb': xbb, 'p_k': xk, 'p_hbp': xhbp,
        'p_bf': xbf, 'p_bip': xbip, 'p_ra': xra,
        'p_er': proj['xER'], 'p_era': proj['xERA'], 'p_era_minus': proj['xERA-'],
        'p_fip': proj['xFIP'], 'p_whip': proj['xWHIP'],
        'p_ra9': proj['xRA9'], 'p_babip': proj['xBABIP'],
        'p_k_pct': proj['xK%'], 'p_bb_pct': proj['xBB%'],
        'p_war': proj['xWAR'],
        'p_baa': proj['xBAA'], 'p_obpa': proj['xOBPA'],
        'p_r_def': proj['xRdef'], 'p_r_lev': proj['xRlev'], 'p_r_corr': proj['xRcorr'],
        'p_raa': proj['xRAA'], 'p_raa_lev': proj['xRAAlev'], 'p_waa': proj['xWAA'],
        'p_r_rep': proj['xRrep'], 'p_rar': proj['xRAR'],
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
    'stream', 'p_w', 'p_l', 'p_win_pct', 'p_era', 'p_gp', 'p_gs', 'p_cg', 'p_sho', 'p_sv', 'p_ip',
    'p_h', 'p_ra', 'p_er', 'p_hr', 'p_bb', 'p_k', 'p_hbp', 'p_wp', 'p_bf', 'p_whip',
    'stat_type',
]


def _pit_streams_section(first, last):
    stream_rows = pitching_stream_rows(first, last)
    if not stream_rows:
        return

    frames = []
    for row in stream_rows:
        d = {c: np.nan for c in _PIT_STREAM_COLS}
        d['stream']    = row['stream']
        d['stat_type'] = 'season'
        for key in ('p_w', 'p_l', 'p_win_pct', 'p_era', 'p_gp', 'p_gs', 'p_cg', 'p_sho', 'p_sv',
                    'p_ip', 'p_h', 'p_ra', 'p_er', 'p_hr', 'p_bb', 'p_k', 'p_hbp', 'p_wp', 'p_bf', 'p_whip'):
            if key in row:
                d[key] = row[key]
        frames.append(d)

    # Season total row from the already-computed stats (includes WAR, ERA-, FIP, etc.)
    s21 = pitching.stats[
        (pitching.stats['First Name'] == first) &
        (pitching.stats['Last Name']  == last)  &
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
    h2("Stream-by-stream stats")
    render_table(stream_df)


def generate_pitcher_page(first_name, last_name):
    if (first_name, last_name) in players.player_info.index:
        active          = True
        pi              = players.player_info.loc[(first_name, last_name)]
        team_name       = pi['team_name']
        jersey_number   = pi['jersey']
        throw_hand      = pi['throws']
        pitcher_role    = pi['role']
        pitcher_arsenal = pi['pitchTypes']
        age             = pi['age']
        salary          = pi['salary']
    else:
        active = False
        mask   = (pitching.stats['Last Name'] == last_name) & (pitching.stats['First Name'] == first_name)
        pitcher_role = pitching.stats.loc[mask, 'role'].iloc[0]
        try:
            ret_mask          = (players.retired_pitchers['Last Name'] == last_name) & (players.retired_pitchers['First Name'] == first_name)
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
            p(f"Salary: {salary}")
        else:
            strong("Retired")
            p(f"Role: {pitcher_role}")
            p(f"Retirement Season: {retirement_season}")
            p(f"Retirement Age: {retirement_age}")

        hr()

        stats = pitching.stats[
            (pitching.stats['Last Name']  == last_name) &
            (pitching.stats['First Name'] == first_name)
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
        render_table(standard_pitching)

        h3("Advanced Pitching")
        render_table(stats[[
            'season', 'age', 'team', 'p_ip',
            'p_era', 'p_fip', 'p_ra9', 'p_baa', 'p_obpa', 'p_bip', 'p_babip',
            'p_h_per_9', 'p_hr_per_9', 'p_k_per_9', 'p_bb_per_9', 'p_k_per_bb', 'p_k_pct', 'p_bb_pct',
            'p_p_per_gp', 'p_ip_per_gp', 'p_p_per_ip', 'p_p_per_pa', 'stat_type',
        ]])

        h3("Value Pitching")
        render_table(stats[[
            'season', 'age', 'team', 'p_ip', 'p_gp', 'p_gs',
            'p_ra', 'p_r_def', 'p_ra9', 'p_ra9_def', 'p_r_lev', 'p_r_corr',
            'p_raa', 'p_raa_lev', 'p_waa', 'p_r_rep', 'p_rar', 'p_war', 'stat_type',
        ]])

        if active:
            _pit_streams_section(first_name, last_name)

        h2("Awards")

    path = Path(f"docs/players/{convert_name(first_name, last_name)}.html")
    path.write_text(str(doc))
