"""Generate an individual season page (docs/seasons/{n}.html)."""
import math
from pathlib import Path

from dominate.tags import *

import pandas as pd
import league as lg
from constants import CURRENT_SEASON, num_games, SEASON_RANGE
from data import teams as teams_data
from pages.page_utils import make_doc, render_table, fmt_round
from registry import REGISTRY
import leaders as ld
import team_ranks
from team_ranks import BAT_RANK_COLS, PIT_RANK_COLS
from seasons import split_records, h2h_records, vs_division_records, strength_of_schedule

_BAT_LEADER_STATS = ['war', 'hr', 'rbi', 'avg', 'ops', 'sb']
_PIT_LEADER_STATS = ['p_war', 'p_w', 'p_sv', 'p_era', 'p_k', 'p_whip']


def _fmt_rec(w, l):
    return f"{w}-{l}"



def _standings_section(season_num):
    season_rows = teams_data.standings[teams_data.standings['Season'] == season_num].copy()
    if season_rows.empty:
        return
    season_rows['Diff'] = season_rows['runsFor'] - season_rows['runsAgainst']

    sched = teams_data.schedules.get(season_num)
    split = None
    sos   = None
    if sched is not None:
        teams_df = teams_data.teams
        div_map  = teams_df.set_index('team_id')['division_name'].to_dict()
        conf_map = teams_df.set_index('team_id')['conference_name'].to_dict()
        winning_teams = set(
            season_rows[season_rows['gamesWon'] > season_rows['gamesLost']]['team_id']
        )
        split = split_records(sched, div_map, conf_map, winning_teams)
        sos   = strength_of_schedule(sched, season_rows)

    h2("Standings")
    for conf_name, conf_group in season_rows.groupby('conference_name', sort=False):
        h3(conf_name)
        conf_group = conf_group.copy()
        conf_group['t_pct'] = conf_group['gamesWon'] / (conf_group['gamesWon'] + conf_group['gamesLost'])
        conf_rows = []
        conf_leader = conf_group.sort_values(['t_pct', 'Diff'], ascending=[False, False]).iloc[0]
        max_w, min_l = conf_leader['gamesWon'], conf_leader['gamesLost']
        for _, row in conf_group.sort_values(['t_pct', 'Diff'], ascending=[False, False]).iterrows():
            conf_gb = ((max_w - row['gamesWon']) + (row['gamesLost'] - min_l)) / 2
            rec = {
                'team_name': row['team_id'],
                't_w':    row['gamesWon'],
                't_l':    row['gamesLost'],
                't_pct':  row['t_pct'],
                't_gb':   conf_gb,
                't_rs':   row['runsFor'],
                't_ra':   row['runsAgainst'],
                't_diff': row['Diff'],
                'season': season_num,
                'stat_type': 'season',
            }
            if split:
                sp = split[row['team_id']]
                rec.update({
                    't_last10':      _fmt_rec(*sp['last10']),
                    't_home':        _fmt_rec(*sp['home']),
                    't_away':        _fmt_rec(*sp['away']),
                    't_conf':        _fmt_rec(*sp['conf']),
                    't_inter':       _fmt_rec(*sp['inter']),
                })
            if sos:
                s = sos[row['team_id']]
                rec['t_sos']     = s['sos']     if s['sos']     is not None else float('nan')
                rec['t_sos_rem'] = s['sos_rem'] if s['sos_rem'] is not None else float('nan')
            conf_rows.append(rec)
        conf_cols = ['team_name', 't_w', 't_l', 't_pct', 't_gb', 't_rs', 't_ra', 't_diff']
        if split:
            conf_cols += ['t_last10', 't_home', 't_away', 't_conf', 't_inter']
        if sos:
            conf_cols += ['t_sos', 't_sos_rem']
        render_table(pd.DataFrame(conf_rows)[conf_cols + ['season', 'stat_type']],
                     depth=1, hidden={'season'})
        for div_name, div_group in conf_group.groupby('division_name', sort=False):
            h4(div_name)
            rows = []
            div_group = div_group.copy()
            div_group['t_pct'] = div_group['gamesWon'] / (div_group['gamesWon'] + div_group['gamesLost'])
            for _, row in div_group.sort_values(['t_pct', 'Diff'], ascending=[False, False]).iterrows():
                rec = {
                    'team_name': row['team_id'],
                    't_w':    row['gamesWon'],
                    't_l':    row['gamesLost'],
                    't_pct':  row['gamesWon'] / (row['gamesWon'] + row['gamesLost']),
                    't_gb':   row['GB'],
                    't_rs':   row['runsFor'],
                    't_ra':   row['runsAgainst'],
                    't_diff': row['Diff'],
                    'season': season_num,
                    'stat_type': 'season',
                }
                if split:
                    sp = split[row['team_id']]
                    rec.update({
                        't_last10':      _fmt_rec(*sp['last10']),
                        't_div':         _fmt_rec(*sp['div']),
                        't_conf':        _fmt_rec(*sp['conf']),
                        't_inter':       _fmt_rec(*sp['inter']),
                        't_one_run':     _fmt_rec(*sp['one_run']),
                        't_blowout':     _fmt_rec(*sp['blowout']),
                        't_home':        _fmt_rec(*sp['home']),
                        't_away':        _fmt_rec(*sp['away']),
                        't_vs500':       _fmt_rec(*sp['vs500']),
                        't_first_half':  _fmt_rec(*sp['first_half']),
                        't_second_half': _fmt_rec(*sp['second_half']),
                        't_shutout':     _fmt_rec(*sp['shutout']),
                    })
                if sos:
                    s = sos[row['team_id']]
                    rec['t_sos']     = s['sos']     if s['sos']     is not None else float('nan')
                    rec['t_sos_rem'] = s['sos_rem'] if s['sos_rem'] is not None else float('nan')
                rows.append(rec)
            cols = ['team_name', 't_w', 't_l', 't_pct', 't_gb', 't_rs', 't_ra', 't_diff']
            if split:
                cols += ['t_last10', 't_div', 't_conf', 't_inter', 't_one_run',
                         't_blowout', 't_home', 't_away', 't_vs500',
                         't_first_half', 't_second_half', 't_shutout']
            if sos:
                cols += ['t_sos', 't_sos_rem']
            render_table(pd.DataFrame(rows)[cols + ['season', 'stat_type']],
                         depth=1, hidden={'season'})

    _wildcard_section(season_num, season_rows, split, sos)


def _wildcard_section(season_num, season_rows, split, sos):
    if season_rows.empty:
        return
    h2("Playoffs")
    for conf_name, conf_group in season_rows.groupby('conference_name', sort=False):
        h3(conf_name)
        conf_group = conf_group.copy()
        conf_group['t_pct'] = conf_group['gamesWon'] / (conf_group['gamesWon'] + conf_group['gamesLost'])

        div_leader_idx = (
            conf_group.groupby('division_name', sort=False)
            .apply(lambda g: g.sort_values(['t_pct', 'Diff'], ascending=[False, False]).index[0], include_groups=False)
        )
        div_leaders = conf_group.loc[div_leader_idx].sort_values(
            ['t_pct', 'Diff'], ascending=[False, False]
        )
        non_leaders = conf_group.drop(index=div_leader_idx).copy()

        if non_leaders.empty:
            continue
        wc_leader = non_leaders.sort_values(['t_pct', 'Diff'], ascending=[False, False]).iloc[0]
        max_w, min_l = wc_leader['gamesWon'], wc_leader['gamesLost']
        non_leaders['WC_GB'] = ((max_w - non_leaders['gamesWon']) + (non_leaders['gamesLost'] - min_l)) / 2
        non_leaders = non_leaders.sort_values(['WC_GB', 'Diff'], ascending=[True, False])

        rows = []

        def _make_rec(row, gb_val, stype):
            rec = {
                'team_name': row['team_id'],
                't_w':    row['gamesWon'],
                't_l':    row['gamesLost'],
                't_pct':  row['t_pct'],
                't_gb':   gb_val,
                't_rs':   row['runsFor'],
                't_ra':   row['runsAgainst'],
                't_diff': row['Diff'],
                'season': season_num,
                'stat_type': stype,
            }
            if split:
                rec['t_last10'] = _fmt_rec(*split[row['team_id']]['last10'])
            if sos:
                s = sos[row['team_id']]
                rec['t_sos']     = s['sos']     if s['sos']     is not None else float('nan')
                rec['t_sos_rem'] = s['sos_rem'] if s['sos_rem'] is not None else float('nan')
            return rec

        for _, row in div_leaders.iterrows():
            rows.append(_make_rec(row, 0.0, 'career'))

        for i, (_, row) in enumerate(non_leaders.iterrows()):
            gb = 0.0 if i == 0 else row['WC_GB']
            rows.append(_make_rec(row, gb, 'season'))

        cols = ['team_name', 't_w', 't_l', 't_pct', 't_gb', 't_rs', 't_ra', 't_diff']
        if split:
            cols.append('t_last10')
        if sos:
            cols += ['t_sos', 't_sos_rem']
        render_table(pd.DataFrame(rows)[cols + ['season', 'stat_type']],
                     depth=1, hidden={'season'})


def _league_stats_section(season_num):
    sb = lg.season_batting.loc[season_num]
    sp = lg.season_pitching.loc[season_num]

    h2("League Stats")

    h3("Batting")
    bat_row = pd.DataFrame([{
        'avg': sb['avg'], 'obp': sb['obp'], 'slg': sb['slg'], 'ops': sb['ops'],
        'woba': sb['woba'], 'r_per_g': sb['r_per_g'],
        'hr': sb['hr'], 'bb': sb['bb'], 'k': sb['k'],
        'stat_type': 'season',
    }])
    render_table(bat_row, depth=1)

    h3("Pitching")
    pit_row = pd.DataFrame([{
        'p_era': sp['p_era'], 'p_ra9': sp['p_ra9'], 'p_whip': sp['p_whip'],
        'p_k_per_9': sp['p_k_per_9'], 'p_bb_per_9': sp['p_bb_per_9'], 'p_babip': sp['p_babip'],
        'stat_type': 'season',
    }])
    render_table(pit_row, depth=1)


def _leader_table(stat, rows):
    h4(REGISTRY[stat]['name'] if stat in REGISTRY else stat)
    df = rows.reset_index().rename(columns={'index': '#'})
    df = df[['#', 'player_id', 'team', stat]].copy()
    df.insert(2, 'player', '')
    render_table(df, depth=1)


def _leaders_section(season_num):
    h2("Leaders")
    h3("Batting")
    for stat in _BAT_LEADER_STATS:
        rows = ld.get_leaders(stat, season=season_num, num=10)
        _leader_table(stat, rows)
    h3("Pitching")
    for stat in _PIT_LEADER_STATS:
        rows = ld.get_leaders(stat, season=season_num, num=10)
        _leader_table(stat, rows)

def _division_standings_section(season_num):
    season_rows = teams_data.standings[teams_data.standings['Season'] == season_num].copy()
    if season_rows.empty:
        return
    divisions, vs_div = vs_division_records(season_num)
    season_rows['Diff'] = season_rows['runsFor'] - season_rows['runsAgainst']

    h2("Division Records")
    for conf_name, conf_group in season_rows.groupby('conference_name', sort=False):
        h3(conf_name)
        for div_name, div_group in conf_group.groupby('division_name', sort=False):
            h4(div_name)
            rows = []
            for _, row in div_group.sort_values(['gamesWon', 'Diff'], ascending=[False, False]).iterrows():
                team = row['team_id']
                rec = {
                    'team_name': team,
                    't_w':   row['gamesWon'],
                    't_l':   row['gamesLost'],
                    't_pct': row['gamesWon'] / (row['gamesWon'] + row['gamesLost']),
                    't_gb':  row['GB'],
                    'season': season_num,
                    'stat_type': 'season',
                }
                if vs_div and team in vs_div:
                    for d in divisions:
                        w, l = vs_div[team][d]
                        rec[f'_div_{d}'] = f"{w}-{l}" if (w or l) else ''
                rows.append(rec)
            cols = ['team_name', 't_w', 't_l', 't_pct', 't_gb']
            if vs_div:
                cols += [f'_div_{d}' for d in divisions]
            df = pd.DataFrame(rows)[cols + ['season', 'stat_type']]
            if vs_div:
                df = df.rename(columns={f'_div_{d}': d for d in divisions})
            render_table(df, depth=1, hidden={'season'})


def _h2h_matrix(season_num):
    team_order, records = h2h_records(season_num)
    if team_order is None:
        return
    ti = teams_data.team_info
    h2("Head-to-Head")
    with table(border=1, cls='compact'):
        with thead():
            with tr():
                th('')
                for tid in team_order:
                    th(ti.loc[tid, 'abbr'] if tid in ti.index else tid)
        with tbody():
            for row_tid in team_order:
                with tr():
                    td(b(ti.loc[row_tid, 'abbr'] if row_tid in ti.index else row_tid))
                    for col_tid in team_order:
                        if row_tid == col_tid:
                            td('\u2014')
                        else:
                            rec = records.get((row_tid, col_tid), [0, 0])
                            td(f"{rec[0]}-{rec[1]}" if rec[0] or rec[1] else '')


def _totals_section(season_num):
    h2("Totals")
    for label, cols, df in [
        ('Batting',  BAT_RANK_COLS, team_ranks.batting),
        ('Pitching', PIT_RANK_COLS, team_ranks.pitching),
    ]:
        h3(label)
        if season_num not in df.index.get_level_values('season'):
            continue
        season_data = df.xs(season_num, level='season').reset_index()
        season_data.rename(columns={'team': 'team_name'}, inplace=True)
        season_data['stat_type'] = 'season'
        available_cols = [c for c in cols if c in season_data.columns]
        render_table(
            season_data[['team_name'] + available_cols + ['stat_type']],
            depth=1,
        )


def _rankings_section(season_num):
    h2("Rankings")
    for label, cols, df in [
        ('Batting',  BAT_RANK_COLS, team_ranks.batting),
        ('Pitching', PIT_RANK_COLS, team_ranks.pitching),
    ]:
        h3(label)
        if season_num not in df.index.get_level_values('season'):
            continue
        season_data = df.xs(season_num, level='season')
        available_cols = [c for c in cols if c in season_data.columns]
        ranks = team_ranks.season_ranks(season_num, df, cols)

        with table(cls='leaders-index', border=0):
            with thead():
                with tr():
                    th('Team')
                    for col in available_cols:
                        meta = REGISTRY.get(col, {})
                        th(meta.get('name', col))
            ti = teams_data.team_info
            with tbody():
                for team_id in season_data.index:
                    with tr():
                        lbl = ti.loc[team_id, 'abbr'] if team_id in ti.index else team_id
                        td(lbl)
                        for col in available_cols:
                            conf_str, bfbl_str = ranks.get(team_id, {}).get(col, ('-', '-'))
                            td(f"{bfbl_str}")


def generate_season_page(season_num):
    all_seasons = sorted(SEASON_RANGE)
    idx         = all_seasons.index(season_num)
    prev_season = all_seasons[idx - 1] if idx > 0 else None
    next_season = all_seasons[idx + 1] if idx < len(all_seasons) - 1 else None

    doc = make_doc(f"Season {season_num}")
    with doc:
        h1(f"Season {season_num}")
        with p():
            if prev_season:
                a(f"<< Season {prev_season}", href=f"{prev_season}.html")
            if prev_season and next_season:
                span(" | ")
            if next_season:
                a(f"Season {next_season} >>", href=f"{next_season}.html")
        _standings_section(season_num)
        #_division_standings_section(season_num)
        _h2h_matrix(season_num)
        _leaders_section(season_num)
        _totals_section(season_num)
        _rankings_section(season_num)
    Path(f"docs/seasons/{season_num}.html").write_text(str(doc))
