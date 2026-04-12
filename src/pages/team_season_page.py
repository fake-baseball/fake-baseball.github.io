"""Generate individual team-season pages (docs/teams/{slug}/{n}.html)."""
from pathlib import Path
import math

import pandas as pd
from dominate.tags import *

import batting as bat_module
import pitching as pit_module
import team_ranks
from constants import CURRENT_SEASON
from data import teams as teams_data
from registry import REGISTRY
from pages.page_utils import make_doc, render_table, fmt_round


_BAT_COLS = [
    'player_name', 'war',
    'gb', 'pa', 'ab', 'r', 'h', 'b_2b', 'b_3b', 'hr', 'rbi',
    'sb', 'cs', 'bb', 'k', 'avg', 'obp', 'slg', 'ops', 'ops_plus',
    'tb', 'hbp', 'sh', 'sf', 'e', 'pb', 'stat_type',
]

_PIT_COLS = [
    'player_name', 'p_war',
    'p_w', 'p_l', 'p_win_pct', 'p_era', 'p_gp', 'p_gs', 'p_cg', 'p_sho', 'p_sv', 'p_ip',
    'p_h', 'p_ra', 'p_er', 'p_hr', 'p_bb', 'p_k', 'p_hbp', 'p_wp', 'p_bf', 'p_era_minus', 'p_fip', 'p_whip',
    'stat_type',
]

from team_ranks import BAT_RANK_COLS, PIT_RANK_COLS


def _totals_row(season_num, abbr):
    """Return a one-row DataFrame of team totals from team_ranks for use as the summary row."""
    key = (season_num, abbr)
    bat_row = team_ranks.batting.loc[[key]].copy() if key in team_ranks.batting.index else None
    pit_row = team_ranks.pitching.loc[[key]].copy() if key in team_ranks.pitching.index else None
    return bat_row, pit_row


def _rank_table(season_num, team_id, conference, cols, ranks_df):
    """Render a transposed ranking table: columns=stats, rows=Conf rank / BFBL rank."""
    conf_map = teams_data.teams.set_index('team_id')['conference_name'].to_dict()
    conf_teams = {tid for tid, c in conf_map.items() if c == conference}

    with table(cls='leaders-index', border=0):
        with thead():
            with tr():
                th('')
                for col in cols:
                    meta = REGISTRY.get(col, {})
                    th(meta.get('name', col))
        with tbody():
            for scope_label, scope_abbrs in [('Conf', conf_teams), ('BFBL', None)]:
                with tr():
                    th(scope_label)
                    for col in cols:
                        td(team_ranks.rank_label(season_num, team_id, col, ranks_df, scope_abbrs))


def generate_team_season_page(team_name, season_num, team_id):
    standing = teams_data.standings[
        (teams_data.standings['team_id'] == team_id) &
        (teams_data.standings['Season'] == season_num)
    ]
    if standing.empty:
        return
    row = standing.iloc[0]
    w, l = int(row['gamesWon']), int(row['gamesLost'])
    win_pct = fmt_round(w / (w + l), 3, False)
    conference = row['conference_name']

    bat_total, pit_total = _totals_row(season_num, team_id)

    def _prep(df, cols, total_row=None):
        df = df.copy()
        if total_row is not None:
            total_row = total_row.copy()
            total_row['stat_type']  = 'totals'
            df = pd.concat([df, total_row], ignore_index=True)
        available = ['player_name'] + [c for c in cols if c in df.columns and c != 'player_name']
        for extra in ('season', 'team'):
            if extra in df.columns and extra not in available:
                available.append(extra)
        return df[list(dict.fromkeys(available))]

    bat_stats = bat_module.stats[
        (bat_module.stats['team'] == team_id) &
        (bat_module.stats['season'] == season_num) &
        (bat_module.stats['stat_type'] != 'career')
    ].sort_values('pa', ascending=False)

    pit_stats = pit_module.stats[
        (pit_module.stats['team'] == team_id) &
        (pit_module.stats['season'] == season_num) &
        (pit_module.stats['stat_type'] != 'career')
    ].sort_values('p_ip', ascending=False)

    team_seasons = sorted(
        teams_data.standings[teams_data.standings['team_id'] == team_id]['Season'].unique()
    )
    idx = team_seasons.index(season_num) if season_num in team_seasons else -1
    prev_season = team_seasons[idx - 1] if idx > 0 else None
    next_season = team_seasons[idx + 1] if idx >= 0 and idx < len(team_seasons) - 1 else None

    doc = make_doc(f"{team_name} Season {season_num}", depth=2)
    with doc:
        h1(f"{team_name} Season {season_num}")
        with p():
            if prev_season:
                a(f"<< Season {prev_season}", href=f"{prev_season}.html")
            if prev_season and next_season:
                span(" | ")
            if next_season:
                a(f"Season {next_season} >>", href=f"{next_season}.html")
        p(f"{row['conference_name']} - {row['division_name']}")
        p(f"Record: {w}-{l} ({win_pct})")

        h2("Rankings")
        h3("Batting")
        _rank_table(season_num, team_id, conference, BAT_RANK_COLS, team_ranks.batting)
        h3("Pitching")
        _rank_table(season_num, team_id, conference, PIT_RANK_COLS, team_ranks.pitching)

        h2("Stats")
        p("Individual player stats here may show stats that a player achieved with another team "
          "or may not be present at all (in the case of mid-season transactions).")
        h3("Standard Batting")
        render_table(_prep(bat_stats, _BAT_COLS, bat_total), depth=2, hidden={'season', 'team'})

        h3("Standard Pitching")
        render_table(_prep(pit_stats, _PIT_COLS, pit_total), depth=2, hidden={'season', 'team'})

        if teams_data.schedules.get(season_num) is not None:
            h2("Game Log")
            sched = teams_data.schedules[season_num]
            games = sched[(sched['home_team_id'] == team_id) | (sched['away_team_id'] == team_id)].copy()
            games = games.sort_values('Game #').reset_index(drop=True)
            w_count = l_count = streak_char = streak_len = 0
            gl_rows = []
            for game_num, (_, g) in enumerate(games.iterrows(), start=1):
                home      = g['home_team_id'] == team_id
                opp       = g['away_team_id'] if home else g['home_team_id']
                rs        = g['Home Score'] if home else g['Away Score']
                ras       = g['Away Score'] if home else g['Home Score']
                played    = rs is not None and not (isinstance(rs, float) and math.isnan(rs))
                day       = g.get('Day')
                if played:
                    r, ra = int(rs), int(ras)
                    win = r > ra
                    if win:
                        w_count += 1
                        if streak_char == 'W':
                            streak_len += 1
                        else:
                            streak_char, streak_len = 'W', 1
                    else:
                        l_count += 1
                        if streak_char == 'L':
                            streak_len += 1
                        else:
                            streak_char, streak_len = 'L', 1
                    gl_rows.append({
                        'gl_num':    int(day) if day is not None else game_num,
                        'gl_ha':     'H' if home else 'A',
                        'gl_opp':    opp,
                        'gl_r':      r,
                        'gl_ra':     ra,
                        'gl_wl':     'W' if win else 'L',
                        'gl_rec':    f"{w_count}-{l_count}",
                        'gl_streak': '+' * streak_len if streak_char == 'W' else '-' * streak_len,
                        'season':    season_num,
                        'stat_type': 'season',
                    })
                else:
                    gl_rows.append({
                        'gl_num':    int(day) if day is not None else game_num,
                        'gl_ha':     'H' if home else 'A',
                        'gl_opp':    opp,
                        'gl_r':      '',
                        'gl_ra':     '',
                        'gl_wl':     '',
                        'gl_rec':    f"{w_count}-{l_count}",
                        'gl_streak': '',
                        'season':    season_num,
                        'stat_type': 'season',
                    })
            render_table(pd.DataFrame(gl_rows), depth=2, hidden={'season'})

    Path(f"docs/teams/{team_id}/{season_num}.html").write_text(str(doc))
