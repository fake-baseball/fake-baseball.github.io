"""Generate an individual season page (docs/seasons/{n}.html)."""
from pathlib import Path

from dominate.tags import *

import pandas as pd

import league as lg
from data import teams as teams_data
from util import make_doc, render_table, fmt_round, fmt_rdiff
from registry import REGISTRY
import leaders as ld

_BAT_LEADER_STATS = ['war', 'hr', 'rbi', 'avg', 'ops', 'sb']
_PIT_LEADER_STATS = ['p_war', 'p_w', 'p_sv', 'p_era', 'p_k', 'p_whip']


def _fmt_gb(v):
    return '-' if v == 0 else f"{v:.1f}"


def _fmt_rec(w, l):
    return f"{w}-{l}"


def _split_records(sched, div_map, conf_map, winning_teams):
    """Return dict: team -> split W-L records, each a [w, l] list.

    winning_teams: set of team names that finished with a winning record.
    Shutout W = games where team held opponent to 0; L = games where team was held to 0.
    """
    keys = ['div', 'conf', 'inter', 'one_run', 'blowout', 'home', 'away', 'vs500',
            'first_half', 'second_half', 'shutout']
    records = {t: {k: [0, 0] for k in keys} for t in div_map}

    # Count total games per team to determine the half-season boundary.
    total_games = {t: 0 for t in div_map}
    for _, g in sched.iterrows():
        total_games[g['Home Team']] += 1
        total_games[g['Away Team']] += 1
    game_count = {t: 0 for t in div_map}

    for _, g in sched.sort_values('Game #').iterrows():
        ht, at = g['Home Team'], g['Away Team']
        hs, as_ = int(g['Home Score']), int(g['Away Score'])
        margin = abs(hs - as_)
        game_count[ht] += 1
        game_count[at] += 1
        for team, opp, ts, os, is_home in ((ht, at, hs, as_, True), (at, ht, as_, hs, False)):
            win = ts > os
            idx = 0 if win else 1
            if div_map[team] == div_map[opp]:
                cat = 'div'
            elif conf_map[team] == conf_map[opp]:
                cat = 'conf'
            else:
                cat = 'inter'
            records[team][cat][idx] += 1
            if margin == 1:
                records[team]['one_run'][idx] += 1
            if margin >= 5:
                records[team]['blowout'][idx] += 1
            records[team]['home' if is_home else 'away'][idx] += 1
            if opp in winning_teams:
                records[team]['vs500'][idx] += 1
            half = 'first_half' if game_count[team] <= total_games[team] // 2 else 'second_half'
            records[team][half][idx] += 1
            if os == 0:
                records[team]['shutout'][0] += 1  # team shut out opponent (always a win)
            if ts == 0:
                records[team]['shutout'][1] += 1  # team was shut out (always a loss)
    return records


def _standings_section(season_num):
    season_rows = teams_data.standings[teams_data.standings['Season'] == season_num].copy()
    if season_rows.empty:
        return
    season_rows['Pct'] = (
        season_rows['gamesWon'] / (season_rows['gamesWon'] + season_rows['gamesLost'])
    ).map(lambda v: f"{v:.3f}".lstrip('0'))
    season_rows['Diff'] = season_rows['runsFor'] - season_rows['runsAgainst']

    sched = teams_data.schedule20 if season_num == 20 else None
    split = None
    if sched is not None:
        teams_df = teams_data.teams
        div_map  = teams_df.set_index('team_name')['division_name'].to_dict()
        conf_map = teams_df.set_index('team_name')['conference_name'].to_dict()
        winning_teams = set(
            season_rows[season_rows['gamesWon'] > season_rows['gamesLost']]['teamName']
        )
        split = _split_records(sched, div_map, conf_map, winning_teams)

    extra_cols = ['Div', 'Conf', 'Inter', '1-Run', 'Blowout', 'Home', 'Away', 'vs.500',
                  '1st Half', '2nd Half', 'SHO'] if split else []

    h2("Standings")
    for conf_name, conf_group in season_rows.groupby('conference_name', sort=False):
        h3(conf_name)
        for div_name, div_group in conf_group.groupby('division_name', sort=False):
            h4(div_name)
            with table(border=0):
                with thead():
                    with tr():
                        for col in ['Team', 'W', 'L', 'Pct', 'GB', 'RS', 'RA', 'Diff'] + extra_cols:
                            th(col)
                with tbody():
                    for _, row in div_group.sort_values('gamesWon', ascending=False).iterrows():
                        slug = row['teamName'].replace(' ', '')
                        with tr():
                            td(a(row['teamName'], href=f"../teams/{slug}/{season_num}.html"))
                            td(row['gamesWon'])
                            td(row['gamesLost'])
                            td(row['Pct'])
                            td(_fmt_gb(row['GB']))
                            td(row['runsFor'])
                            td(row['runsAgainst'])
                            td(fmt_rdiff(row['Diff']))
                            if split:
                                rec = split[row['teamName']]
                                td(_fmt_rec(*rec['div']))
                                td(_fmt_rec(*rec['conf']))
                                td(_fmt_rec(*rec['inter']))
                                td(_fmt_rec(*rec['one_run']))
                                td(_fmt_rec(*rec['blowout']))
                                td(_fmt_rec(*rec['home']))
                                td(_fmt_rec(*rec['away']))
                                td(_fmt_rec(*rec['vs500']))
                                td(_fmt_rec(*rec['first_half']))
                                td(_fmt_rec(*rec['second_half']))
                                td(_fmt_rec(*rec['shutout']))


def _league_stats_section(season_num):
    sb = lg.season_batting.loc[season_num]
    sp = lg.season_pitching.loc[season_num]

    h2("League Stats")

    h3("Batting")
    bat_cols = ['AVG', 'OBP', 'SLG', 'OPS', 'wOBA', 'R/G', 'HR', 'BB', 'K']
    with table(border=0):
        with thead():
            with tr():
                for col in bat_cols:
                    th(col)
        with tbody():
            with tr():
                for stat in ['avg', 'obp', 'slg', 'ops', 'woba']:
                    m = REGISTRY[stat]
                    td(fmt_round(sb[stat], m['decimal_places'], m['leading_zero'], m['percentage']))
                td(f"{sb['R/G']:.2f}")
                td(int(sb['hr']))
                td(int(sb['bb']))
                td(int(sb['k']))

    h3("Pitching")
    # (stat key in REGISTRY, column name in season_pitching, display header)
    pit_cols = [
        ('p_era',    'ERA',   'ERA'),
        ('p_ra9',    'RA9',   'RA9'),
        ('p_whip',   'WHIP',  'WHIP'),
        ('p_k_per_9', 'p_k_per_9',  'K/9'),
        ('p_bb_per_9','p_bb_per_9', 'BB/9'),
        ('p_babip',  'BABIP', 'BABIP'),
    ]
    with table(border=0):
        with thead():
            with tr():
                for _, _, disp in pit_cols:
                    th(disp)
        with tbody():
            with tr():
                for stat_key, sp_col, _ in pit_cols:
                    m = REGISTRY[stat_key]
                    td(fmt_round(sp[sp_col], m['decimal_places'], m['leading_zero'], m['percentage']))


def _leader_table(stat, rows):
    h4(REGISTRY[stat]['name'] if stat in REGISTRY else stat)
    df = rows.reset_index().rename(columns={'index': '#'})
    df = df[['#', 'First Name', 'Last Name', 'team', stat]].copy()
    df.insert(2, 'player', '')
    render_table(df, depth=1)


def _leaders_section(season_num):
    h2("Leaders")
    h3("Batting")
    for stat in _BAT_LEADER_STATS:
        rows = ld.get_batting_leaders(stat, season=season_num, num=5)
        _leader_table(stat, rows)
    h3("Pitching")
    for stat in _PIT_LEADER_STATS:
        rows = ld.get_pitching_leaders(stat, season=season_num, num=5)
        _leader_table(stat, rows)


def _h2h_matrix(season_num):
    sched = teams_data.schedule20
    if sched is None:
        return
    h2("Head-to-Head")
    team_order = list(dict.fromkeys(
        teams_data.standings[teams_data.standings['Season'] == season_num]
        .sort_values(['conference_name', 'division_name', 'gamesWon'], ascending=[True, True, False])
        ['teamName']
    ))
    abbr_map = teams_data.teams.set_index('team_name')['abbr'].to_dict()

    # Build W-L lookup: (home_team, away_team) -> (wins, losses) from home_team's perspective
    records = {}
    for _, g in sched.iterrows():
        ht, at = g['Home Team'], g['Away Team']
        hs, as_ = int(g['Home Score']), int(g['Away Score'])
        records.setdefault((ht, at), [0, 0])
        records.setdefault((at, ht), [0, 0])
        if hs > as_:
            records[(ht, at)][0] += 1
            records[(at, ht)][1] += 1
        else:
            records[(ht, at)][1] += 1
            records[(at, ht)][0] += 1

    with table(border=1):
        with thead():
            with tr():
                th('')
                for t in team_order:
                    th(abbr_map[t])
        with tbody():
            for row_team in team_order:
                with tr():
                    td(b(abbr_map[row_team]))
                    for col_team in team_order:
                        if row_team == col_team:
                            td('—')
                        else:
                            rec = records.get((row_team, col_team), [0, 0])
                            td(f"{rec[0]}-{rec[1]}")


def generate_season_page(season_num):
    doc = make_doc(f"Season {season_num}")
    with doc:
        h1(f"Season {season_num}")
        _standings_section(season_num)
        _leaders_section(season_num)
        if season_num == 20:
            _h2h_matrix(season_num)
    Path(f"docs/seasons/{season_num}.html").write_text(str(doc))
