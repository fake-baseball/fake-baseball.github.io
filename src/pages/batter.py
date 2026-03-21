"""Generate an HTML page for a single position player."""
from pathlib import Path

import numpy as np
import pandas as pd
from dominate.tags import *
from dominate.util import raw

import batting
import leaders
import projections as proj_module
from data import players
from data import teams as teams_data
from stats_meta import BATTING_STATS, BASERUNNING_STATS, FIELDING_STATS
from util import fmt_df, fmt_round, render_stat_table, render_leaders_table, convert_name, make_doc

_ALL_BAT = {**BATTING_STATS, **BASERUNNING_STATS, **FIELDING_STATS}

_SUMMARY_COLS = [
    ('WAR', 'WAR'), ('AB', 'AB'), ('H', 'H'), ('HR', 'HR'),
    ('BA',  'AVG'), ('R',  'R'),  ('RBI', 'RBI'), ('SB', 'SB'),
    ('OBP', 'OBP'), ('SLG', 'SLG'), ('OPS', 'OPS'), ('OPS+', 'OPS+'),
]


def _summary_table(stats, proj_row):
    """Render BB-ref style summary strip: Season 20, Projected, Career."""
    def _fmt(col, val):
        meta = _ALL_BAT.get(col)
        if meta is None or (isinstance(val, float) and np.isnan(val)):
            return '-'
        return fmt_round(val, meta['decimal_places'], meta['leading_zero'], meta['percentage'])

    s20    = stats[(stats['Season'] == 20) & (stats['stat_type'] == 'season')]
    career = stats[stats['stat_type'] == 'career']

    rows_data = []
    if not s20.empty:
        rows_data.append(('Season 20', s20.iloc[0]))
    if proj_row is not None:
        rows_data.append(('Projected', proj_row.iloc[0]))
    if not career.empty:
        rows_data.append(('Career', career.iloc[0]))

    with table(cls='summary'):
        with thead():
            with tr():
                th('')
                for disp, _ in _SUMMARY_COLS:
                    th(disp)
        with tbody():
            for label, row in rows_data:
                with tr():
                    td(label)
                    for _, col in _SUMMARY_COLS:
                        td(_fmt(col, row[col]))


def _bat_proj_row(first, last, cols):
    """Return a single-row DataFrame for the projected season, or None."""
    rows = proj_module.compute_all()
    proj = next((r for r in rows if r['first'] == first and r['last'] == last), None)
    if proj is None:
        return None

    pa    = proj['proj_pa']
    bb    = int(round(pa * proj['BB']))
    hbp   = int(round(pa * proj['HBP']))
    oneb  = int(round(pa * proj['1B']))
    twob  = int(round(pa * proj['2B']))
    threeb = int(round(pa * proj['3B']))
    hr    = proj['xHR']
    k     = proj['xK']
    sb    = proj['xSB']
    cs    = proj['xCS']
    h     = oneb + twob + threeb + hr
    ab    = pa - bb - hbp
    tb    = oneb + 2*twob + 3*threeb + 4*hr
    bip   = ab - k
    xbh   = twob + threeb + hr
    sbatt = sb + cs

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
        'PA': pa, 'AB': ab, 'BB': bb, 'HBP': hbp,
        '2B': twob, '3B': threeb, 'HR': hr, 'H': h, 'TB': tb,
        'K': k, 'SB': sb, 'CS': cs, 'BIP': bip, 'XBH': xbh,
        'GB': proj['xGB'], 'R': proj['xR'], 'RBI': proj['xRBI'],
        'AVG': proj['xAVG'], 'OBP': proj['xOBP'], 'SLG': proj['xSLG'],
        'OPS': proj['xOPS'], 'OPS+': proj['xOPS+'], 'wOBA': proj['xwOBA'], 'wRC+': proj['xwRC+'],
        'BABIP': proj['xBABIP'], 'WAR': proj['xWAR'],
        'ISO': proj['xSLG'] - proj['xAVG'],
        'HR%': proj['HR'], 'K%': proj['K'], 'BB%': proj['BB'],
        'Rbr': proj['xRbr'],
        'wRC': proj['xwRC'],
        'Rbat': proj['xRbat'], 'Rpos': proj['xRpos'],
        'Rcorr': proj['xRcorr'], 'Rrep': proj['xRrep'],
        'RAA': proj['xRAA'], 'RAR': proj['xRAR'],
        'WAA': proj['xWAA'],
    })
    ob = h + bb + hbp
    if ob > 0:
        d['RS%'] = proj['xR'] / ob
    non_hr_ob = h - hr + bb + hbp
    if non_hr_ob > 0:
        d['RC%'] = (proj['xR'] - hr) / non_hr_ob
    if sbatt > 0:
        d['SB%']    = sb / sbatt
        d['SbAtt%'] = sbatt / oneb if oneb > 0 else np.nan
    if h > 0:
        d['XBH%'] = xbh / h
    if pi_row is not None:
        d['PP'] = pi_row['ppos']
        d['2P'] = pi_row['spos']
    return pd.DataFrame([d])


def generate_batter_page(first_name, last_name):
    if (first_name, last_name) in players.player_info.index:
        active        = True
        pi            = players.player_info.loc[(first_name, last_name)]
        team_name     = pi['team_name']
        jersey_number = pi['jersey']
        bat_hand      = pi['bats']
        throw_hand    = pi['throws']
        primary_pos   = pi['ppos']
        secondary_pos = pi['spos']
        age           = pi['age']
        salary        = pi['salary']
    else:
        active      = False
        mask        = (batting.stats['Last Name'] == last_name) & (batting.stats['First Name'] == first_name)
        primary_pos   = batting.stats.loc[mask, 'PP'].iloc[0]
        secondary_pos = batting.stats.loc[mask, '2P'].iloc[0]
        try:
            ret_mask          = (players.retired_batters['Last Name'] == last_name) & (players.retired_batters['First Name'] == first_name)
            retirement_season = players.retired_batters.loc[ret_mask, 'Retirement Season'].iloc[0]
            retirement_age    = players.retired_batters.loc[ret_mask, 'Age'].iloc[0]
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
            p(f"Bats: {bat_hand} - Throws: {throw_hand}")
            pos = f"Position: {primary_pos}"
            if secondary_pos:
                pos += f" (Secondary: {secondary_pos})"
            p(pos)
            p(f"Skills: POW {pi['power']} / CON {pi['contact']} / SPD {pi['speed']} / FLD {pi['fielding']} / ARM {pi['arm']}")
            p(f"Salary: {salary}")
        else:
            strong("Retired")
            pos = f"Position: {primary_pos}"
            if secondary_pos and secondary_pos != "None":
                pos += f" (Secondary: {secondary_pos})"
            p(pos)
            p(f"Retirement Season: {retirement_season}")
            p(f"Retirement Age: {retirement_age}")

        hr()

        stats = batting.stats[
            (batting.stats['First Name'] == first_name) &
            (batting.stats['Last Name']  == last_name)
        ].copy()

        proj_row = _bat_proj_row(first_name, last_name, stats.columns) if active else None
        _summary_table(stats, proj_row)

        if active and proj_row is not None:
            season = stats[stats['stat_type'] == 'season']
            career = stats[stats['stat_type'] == 'career']
            team   = stats[stats['stat_type'] == 'team']
            stats  = pd.concat([season, proj_row, career, team], ignore_index=True)

        h2("Stats")

        h3("Standard Batting")
        standard_batting = stats[[
            'Season', 'Age', 'Team', 'WAR',
            'GB', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'RBI',
            'SB', 'CS', 'BB', 'K', 'AVG', 'OBP', 'SLG', 'OPS', 'OPS+',
            'TB', 'HBP', 'SH', 'SF', 'stat_type',
        ]]
        team_conf_map = teams_data.teams.set_index('abbr')['conference_name'].to_dict() if teams_data.teams is not None else None
        if leaders.batting_leaders_conf and team_conf_map:
            render_leaders_table(standard_batting, leaders.batting_leaders_conf, _ALL_BAT,
                                 overall_leaders=leaders.batting_leaders, team_conf_map=team_conf_map)
        else:
            render_leaders_table(standard_batting, leaders.batting_leaders, _ALL_BAT)

        h3("Advanced Batting")
        render_stat_table(stats[['Season', 'Age', 'Team', 'PA',
                    'wOBA', 'wRC', 'wRC+', 'BIP', 'BABIP',
                    'ISO', 'XBH', 'XBH%', 'HR%', 'K%', 'BB%', 'stat_type']])

        h3("Baserunning")
        render_stat_table(stats[['Season', 'Age', 'Team', 'PA',
                    'SB', 'CS', 'SB%', 'SbAtt%', 'RS%', 'RC%', 'stat_type']])

        h3("Fielding")
        render_stat_table(stats[['Season', 'Age', 'Team', 'PP', '2P',
                    'GB', 'GF', 'E', 'E/GF', 'PB', 'PB/GF', 'stat_type']])

        h3("Value")
        render_stat_table(stats[[
            'Season', 'Age', 'Team', 'GB', 'PA',
            'Rbat', 'Rbr', 'Rdef', 'Rpos', 'Rcorr', 'Rrep', 'RAA', 'RAR', 'WAA', 'WAR', 'stat_type',
        ]])

        h2("Awards")

    path = Path(f"docs/players/{convert_name(first_name, last_name)}.html")
    path.write_text(str(doc))


