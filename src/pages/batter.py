"""Generate an HTML page for a single position player."""
from pathlib import Path

import numpy as np
import pandas as pd
from dominate.tags import *
from dominate.util import raw

import batting
import leaders
import projections as proj_module
from constants import CURRENT_SEASON, LAST_COMPLETED_SEASON
from data import players
from data import teams as teams_data
from registry import REGISTRY
from util import fmt_round, render_table, convert_name, make_doc
from data.stats import batting_stream_rows

_BAT_CONTEXTS = {'batting', 'baserunning', 'fielding'}
_ALL_BAT = {k: v for k, v in REGISTRY.items() if v.get('context') in _BAT_CONTEXTS}

_SUMMARY_COLS = [
    ('WAR', 'war'), ('AB', 'ab'), ('H', 'h'), ('HR', 'hr'),
    ('BA',  'avg'), ('R',  'r'),  ('RBI', 'rbi'), ('SB', 'sb'),
    ('OBP', 'obp'), ('SLG', 'slg'), ('OPS', 'ops'), ('OPS+', 'ops_plus'),
]


def _summary_table(stats, proj_row):
    """Render BB-ref style summary strip: current season, Projected, Career."""
    def _fmt(col, val):
        meta = _ALL_BAT.get(col)
        if meta is None or (isinstance(val, float) and np.isnan(val)):
            return '-'
        return fmt_round(val, meta['decimal_places'], meta['leading_zero'], meta['percentage'])

    s_cur  = stats[(stats['season'] == CURRENT_SEASON)       & (stats['stat_type'] == 'season')]
    s_last = stats[(stats['season'] == LAST_COMPLETED_SEASON) & (stats['stat_type'] == 'season')]
    s_row  = s_cur if not s_cur.empty else s_last
    career = stats[stats['stat_type'] == 'career']

    rows_data = []
    if not s_row.empty:
        label = CURRENT_SEASON if not s_cur.empty else LAST_COMPLETED_SEASON
        rows_data.append((f'Season {label}', s_row.iloc[0]))
    if proj_row is not None:
        # rows_data.append(('Projected', proj_row.iloc[0]))
        pass
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
    bb    = int(round(pa * proj['bb']))
    hbp   = int(round(pa * proj['hbp']))
    oneb  = int(round(pa * proj['b_1b']))
    twob  = int(round(pa * proj['b_2b']))
    threeb = int(round(pa * proj['b_3b']))
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
        'season': 'Proj', 'stat_type': 'projected',
        'age':  pi_row['age'] if pi_row is not None else np.nan,
        'team': team_abbr,
        'pa': pa, 'ab': ab, 'bb': bb, 'hbp': hbp,
        'b_2b': twob, 'b_3b': threeb, 'hr': hr, 'h': h, 'tb': tb,
        'k': k, 'sb': sb, 'cs': cs, 'bip': bip, 'xbh': xbh,
        'gb': proj['xGB'], 'r': proj['xR'], 'rbi': proj['xRBI'],
        'avg': proj['xAVG'], 'obp': proj['xOBP'], 'slg': proj['xSLG'],
        'ops': proj['xOPS'], 'ops_plus': proj['xOPS+'], 'woba': proj['xwOBA'], 'wrc_plus': proj['xwRC+'],
        'babip': proj['xBABIP'], 'war': proj['xWAR'],
        'iso': proj['xSLG'] - proj['xAVG'],
        'hr_pct': proj['hr'], 'k_pct': proj['k'], 'bb_pct': proj['bb'],
        'r_br': proj['xRbr'],
        'wrc': proj['xwRC'],
        'r_bat': proj['xRbat'], 'r_pos': proj['xRpos'],
        'r_corr': proj['xRcorr'], 'r_rep': proj['xRrep'],
        'raa': proj['xRAA'], 'rar': proj['xRAR'],
        'waa': proj['xWAA'],
    })
    ob = h + bb + hbp
    if ob > 0:
        d['rs_pct'] = proj['xR'] / ob
    non_hr_ob = h - hr + bb + hbp
    if non_hr_ob > 0:
        d['rc_pct'] = (proj['xR'] - hr) / non_hr_ob
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
        (batting.stats['First Name'] == first) &
        (batting.stats['Last Name']  == last)  &
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
    render_table(stream_df)


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
        primary_pos   = batting.stats.loc[mask, 'pos1'].iloc[0]
        secondary_pos = batting.stats.loc[mask, 'pos2'].iloc[0]
        try:
            ret_mask          = (players.retired_batters['Last Name'] == last_name) & (players.retired_batters['First Name'] == first_name)
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
            p(f"Salary: {salary}")
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
            'season', 'age', 'team', 'war',
            'gb', 'pa', 'ab', 'r', 'h', 'b_2b', 'b_3b', 'hr', 'rbi',
            'sb', 'cs', 'bb', 'k', 'avg', 'obp', 'slg', 'ops', 'ops_plus',
            'tb', 'hbp', 'sh', 'sf', 'stat_type',
        ]]
        render_table(standard_batting)

        h3("Advanced Batting")
        render_table(stats[['season', 'age', 'team', 'pa',
                    'woba', 'wrc', 'wrc_plus', 'bip', 'babip',
                    'iso', 'xbh', 'xbh_pct', 'hr_pct', 'k_pct', 'bb_pct', 'stat_type']])

        h3("Baserunning")
        render_table(stats[['season', 'age', 'team', 'pa',
                    'sb', 'cs', 'sb_pct', 'sb_att_pct', 'rs_pct', 'rc_pct', 'stat_type']])

        h3("Fielding")
        render_table(stats[['season', 'age', 'team', 'pos1', 'pos2',
                    'gb', 'gf', 'e', 'e_per_gf', 'pb', 'pb_per_gf', 'stat_type']])

        h3("Value")
        render_table(stats[[
            'season', 'age', 'team', 'gb', 'pa',
            'r_bat', 'r_br', 'r_def', 'r_pos', 'r_corr', 'r_rep', 'raa', 'rar', 'waa', 'war', 'stat_type',
        ]])

        if active:
            _bat_streams_section(first_name, last_name)

        h2("Awards")

    path = Path(f"docs/players/{convert_name(first_name, last_name)}.html")
    path.write_text(str(doc))
