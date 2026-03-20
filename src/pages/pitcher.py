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
from stats_meta import PITCHING_STATS
from util import fmt_df, render_stat_table, render_leaders_table, convert_name, make_doc


def _pit_proj_row(first, last, cols):
    """Return a single-row DataFrame for the projected season, or None."""
    rows = pit_proj_module.compute_all()[0]
    proj = next((r for r in rows if r['first'] == first and r['last'] == last), None)
    if proj is None:
        return None

    ip   = proj['proj_ip']
    xk   = proj['xK']
    xbb  = proj['xBB']
    xhbp = proj['xHBP']
    xhr  = proj['xHR']
    xh   = proj['xH']

    out_rate = 1.0 - proj['H'] - proj['BB'] - proj['HBP']
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
        'Season': 'Proj', 'stat_type': 'projected',
        'Age':  pi_row['age'] if pi_row is not None else np.nan,
        'Team': team_abbr,
        'W': proj['xW'], 'L': proj['xL'],
        'WIN%': proj['xW'] / (proj['xW'] + proj['xL']) if (proj['xW'] + proj['xL']) > 0 else np.nan,
        'GP': proj['xGP'], 'GS': proj['xGS'], 'SV': proj['xSV'],
        'IP': round(ip, 1), 'IP_true': ip,
        'H': xh, 'HR': xhr, 'BB': xbb, 'K': xk, 'HBP': xhbp,
        'BF': xbf, 'BIP': xbip, 'RA': xra,
        'ER': proj['xER'], 'ERA': proj['xERA'], 'ERA-': proj['xERA-'],
        'FIP': proj['xFIP'], 'WHIP': proj['xWHIP'],
        'RA9': proj['xRA9'], 'BABIP': proj['xBABIP'],
        'K%': proj['xK%'], 'BB%': proj['xBB%'],
        'WAR': proj['xWAR'],
    })
    if ip > 0:
        d['H/9']  = xh  / ip * 9
        d['HR/9'] = xhr / ip * 9
        d['K/9']  = xk  / ip * 9
        d['BB/9'] = xbb / ip * 9
        if xbb > 0:
            d['K/BB'] = xk / xbb
    return pd.DataFrame([d])


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
        pitcher_role = pitching.stats.loc[mask, 'Role'].iloc[0]
        try:
            ret_mask          = (players.retired_pitchers['Last Name'] == last_name) & (players.retired_pitchers['First Name'] == first_name)
            retirement_season = players.retired_pitchers.loc[ret_mask, 'Retirement Season'].iloc[0]
            retirement_age    = players.retired_pitchers.loc[ret_mask, 'Age'].iloc[0]
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
            p(f"Salary: {salary}")
        else:
            strong("Retired")
            p(f"Role: {pitcher_role}")
            p(f"Retirement Season: {retirement_season}")
            p(f"Retirement Age: {retirement_age}")

        hr()
        h2("Stats")

        stats = pitching.stats[
            (pitching.stats['Last Name']  == last_name) &
            (pitching.stats['First Name'] == first_name)
        ].copy()

        if active:
            proj_row = _pit_proj_row(first_name, last_name, stats.columns)
            if proj_row is not None:
                season = stats[stats['stat_type'] == 'season']
                career = stats[stats['stat_type'] == 'career']
                team   = stats[stats['stat_type'] == 'team']
                stats  = pd.concat([season, proj_row, career, team], ignore_index=True)

        h3("Standard Pitching")
        standard_pitching = stats[[
            'Season', 'Age', 'Team', 'WAR',
            'W', 'L', 'WIN%', 'ERA', 'GP', 'GS', 'CG', 'SHO', 'SV', 'IP',
            'H', 'RA', 'ER', 'HR', 'BB', 'K', 'HBP', 'WP', 'BF', 'ERA-', 'FIP', 'WHIP',
            'stat_type', 'IP_true',
        ]]
        render_leaders_table(standard_pitching, leaders.pitching_leaders, PITCHING_STATS,
                             hidden={'stat_type', 'IP_true'}, col_aliases={'IP': 'IP_true'})

        h3("Advanced Pitching")
        render_stat_table(stats[[
            'Season', 'Age', 'Team', 'IP',
            'ERA', 'FIP', 'RA9', 'BAA', 'OBPA', 'BIP', 'BABIP',
            'H/9', 'HR/9', 'K/9', 'BB/9', 'K/BB', 'K%', 'BB%',
            'P/GP', 'P/IP', 'P/PA', 'stat_type',
        ]])

        h3("Value Pitching")
        render_stat_table(stats[[
            'Season', 'Age', 'Team', 'IP', 'GP', 'GS',
            'RA', 'Rdef', 'RA9', 'RA9def', 'Rlev', 'Rcorr',
            'RAA', 'RAAlev', 'WAA', 'Rrep', 'RAR', 'WAR', 'stat_type',
        ]])

        h2("Awards")

    path = Path(f"docs/players/{convert_name(first_name, last_name)}.html")
    path.write_text(str(doc))


