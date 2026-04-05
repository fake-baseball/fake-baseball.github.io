"""Generate an HTML page for a single position player."""
from pathlib import Path

import numpy as np
import pandas as pd
from dominate.tags import *
from dominate.util import raw

import batting
import leaders
import bat_projections as proj_module
from constants import CURRENT_SEASON, LAST_COMPLETED_SEASON
from data import players
from data import teams as teams_data
from registry import REGISTRY
from pages.page_utils import fmt_round, render_table, convert_name, make_doc
from data.stats import batting_stream_rows

_BAT_CONTEXTS = {'batting', 'baserunning', 'fielding'}
_ALL_BAT = {k: v for k, v in REGISTRY.items() if v.get('context') in _BAT_CONTEXTS}

_SUMMARY_COLS = ['season', 'war', 'ab', 'h', 'hr', 'avg', 'r', 'rbi', 'sb', 'ops']


def _summary_table(stats, proj_row):
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

    summary_df = pd.concat(frames)[_SUMMARY_COLS + ['stat_type']]
    render_table(summary_df, pitching=False)


def _bat_proj_row(first, last, cols):
    """Return a single-row DataFrame for the projected season, or None."""
    rows = proj_module.compute_all()
    proj = next((r for r in rows if r['first'] == first and r['last'] == last), None)
    if proj is None:
        return None

    pa     = proj['proj_pa']
    bb     = int(round(pa * proj['bb_rate']))
    hbp    = int(round(pa * proj['hbp_rate']))
    oneb   = int(round(pa * proj['b_1b_rate']))
    twob   = int(round(pa * proj['b_2b_rate']))
    threeb = int(round(pa * proj['b_3b_rate']))
    hr     = proj['hr']
    k      = proj['k']
    sb     = proj['sb']
    cs     = proj['cs']
    h      = oneb + twob + threeb + hr
    ab     = pa - bb - hbp
    tb     = oneb + 2*twob + 3*threeb + 4*hr
    bip    = ab - k
    xbh    = twob + threeb + hr
    sbatt  = sb + cs

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
        'pa': pa, 'ab': ab, 'bb': bb, 'hbp': hbp,
        'b_2b': twob, 'b_3b': threeb, 'hr': hr, 'h': h, 'tb': tb,
        'k': k, 'sb': sb, 'cs': cs, 'bip': bip, 'xbh': xbh,
        'gb': proj['gb'], 'r': proj['r'], 'rbi': proj['rbi'],
        'avg': proj['avg'], 'obp': proj['obp'], 'slg': proj['slg'],
        'ops': proj['ops'], 'ops_plus': proj['ops_plus'], 'woba': proj['woba'],
        'wrc_plus': proj['wrc_plus'], 'babip': proj['babip'], 'war': proj['war'],
        'iso': proj['slg'] - proj['avg'],
        'hr_pct': proj['hr_rate'], 'k_pct': proj['k_rate'], 'bb_pct': proj['bb_rate'],
        'r_br': proj['r_br'], 'wrc': proj['wrc'],
        'r_bat': proj['r_bat'], 'r_pos': proj['r_pos'],
        'r_corr': proj['r_corr'], 'r_rep': proj['r_rep'],
        'raa': proj['raa'], 'rar': proj['rar'], 'waa': proj['waa'],
    })
    ob = h + bb + hbp
    if ob > 0:
        d['rs_pct'] = proj['r'] / ob
    non_hr_ob = h - hr + bb + hbp
    if non_hr_ob > 0:
        d['rc_pct'] = (proj['r'] - hr) / non_hr_ob
    if sbatt > 0:
        d['sb_pct']     = sb / sbatt
        d['sb_att_pct'] = sbatt / oneb if oneb > 0 else np.nan
    if h > 0:
        d['xbh_pct'] = xbh / h
    if pi_row is not None:
        d['pos1'] = pi_row['ppos']
        d['pos2'] = pi_row['spos']
    return pd.DataFrame([d])


_BAT_STREAM_COLS = [
    'stream', 'gb', 'pa', 'ab', 'r', 'h', 'b_2b', 'b_3b', 'hr', 'rbi',
    'sb', 'cs', 'bb', 'k', 'avg', 'obp', 'slg', 'ops', 'woba', 'babip',
    'tb', 'hbp', 'sh', 'sf', 'stat_type',
]


def _bat_streams_section(first, last):
    stream_rows = batting_stream_rows(first, last)
    if not stream_rows:
        return

    frames = []
    for row in stream_rows:
        d = {c: np.nan for c in _BAT_STREAM_COLS}
        d['stream']    = row['stream']
        d['stat_type'] = 'season'
        for key in ('gb', 'pa', 'ab', 'r', 'h', 'b_2b', 'b_3b', 'hr', 'rbi',
                    'sb', 'cs', 'bb', 'k', 'hbp', 'sh', 'sf', 'tb',
                    'avg', 'obp', 'slg', 'ops', 'woba', 'babip'):
            if key in row:
                d[key] = row[key]
        frames.append(d)

    # Season total row from the already-computed stats (includes OPS+, etc.)
    s21 = batting.stats[
        (batting.stats['first_name'] == first) &
        (batting.stats['last_name']  == last)  &
        (batting.stats['season'] == CURRENT_SEASON) &
        (batting.stats['stat_type'] == 'season')
    ]
    if not s21.empty:
        total = s21.iloc[0].reindex(_BAT_STREAM_COLS).copy()
        total['stream']    = 'Season'
        total['stat_type'] = 'career'
        frames.append(total.to_dict())

    if not frames:
        return

    stream_df = pd.DataFrame(frames, columns=_BAT_STREAM_COLS)
    h2("Stream Log")
    render_table(stream_df, pitching=False)


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
        mask        = (batting.stats['last_name'] == last_name) & (batting.stats['first_name'] == first_name)
        primary_pos   = batting.stats.loc[mask, 'pos1'].iloc[0]
        secondary_pos = batting.stats.loc[mask, 'pos2'].iloc[0]
        try:
            ret_mask          = (players.retired_batters['last_name'] == last_name) & (players.retired_batters['first_name'] == first_name)
            retirement_season = players.retired_batters.loc[ret_mask, 'Retirement Season'].iloc[0]
            retirement_age    = players.retired_batters.loc[ret_mask, 'age'].iloc[0]
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
            p(f"Salary: ${salary:.1f}m")
        else:
            strong("Retired")
            pos = f"Position: {primary_pos}"
            if secondary_pos:
                pos += f" (Secondary: {secondary_pos})"
            p(pos)
            p(f"Retirement Season: {retirement_season}")
            p(f"Retirement Age: {retirement_age}")

        hr()

        stats = batting.stats[
            (batting.stats['first_name'] == first_name) &
            (batting.stats['last_name']  == last_name)
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
            'season', 'age', 'team', 'war',
            'gb', 'pa', 'ab', 'r', 'h', 'b_2b', 'b_3b', 'hr', 'rbi',
            'sb', 'cs', 'bb', 'k', 'avg', 'obp', 'slg', 'ops', 'ops_plus',
            'tb', 'hbp', 'sh', 'sf', 'stat_type',
        ]]
        render_table(standard_batting, pitching=False)

        h3("Advanced Batting")
        render_table(stats[['season', 'age', 'team', 'pa',
                    'woba', 'wrc', 'wrc_plus', 'bip', 'babip',
                    'iso', 'xbh', 'xbh_pct', 'hr_pct', 'k_pct', 'bb_pct', 'stat_type']], pitching=False)

        h3("Baserunning")
        render_table(stats[['season', 'age', 'team', 'pa',
                    'sb', 'cs', 'sb_pct', 'sb_att_pct', 'rs_pct', 'rc_pct', 'stat_type']], pitching=False)

        h3("Fielding")
        render_table(stats[['season', 'age', 'team', 'pos1', 'pos2',
                    'gb', 'gf', 'e', 'e_per_gf', 'pb', 'pb_per_gf', 'stat_type']], pitching=False)

        h3("Value")
        render_table(stats[[
            'season', 'age', 'team', 'gb', 'pa',
            'r_bat', 'r_br', 'r_def', 'r_pos', 'r_corr', 'r_rep', 'raa', 'rar', 'waa', 'war', 'stat_type',
        ]], pitching=False)

        if active:
            _bat_streams_section(first_name, last_name)

        h2("Awards")

    path = Path(f"docs/players/{convert_name(first_name, last_name)}.html")
    path.write_text(str(doc))
