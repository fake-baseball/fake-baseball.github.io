"""Generate individual team-season pages (docs/teams/{slug}/{n}.html)."""
from pathlib import Path

from dominate.tags import *

import batting as bat_module
import pitching as pit_module
from constants import CURRENT_SEASON
from data import teams as teams_data
from pages.page_utils import make_doc, render_table, fmt_round


_BAT_COLS = [
    'player', 'war',
    'gb', 'pa', 'ab', 'r', 'h', 'b_2b', 'b_3b', 'hr', 'rbi',
    'sb', 'cs', 'bb', 'k', 'avg', 'obp', 'slg', 'ops', 'ops_plus',
    'tb', 'hbp', 'sh', 'sf', 'e', 'pb', 'stat_type',
]

_PIT_COLS = [
    'player', 'p_war',
    'p_w', 'p_l', 'p_win_pct', 'p_era', 'p_gp', 'p_gs', 'p_cg', 'p_sho', 'p_sv', 'p_ip',
    'p_h', 'p_ra', 'p_er', 'p_hr', 'p_bb', 'p_k', 'p_hbp', 'p_wp', 'p_bf', 'p_era_minus', 'p_fip', 'p_whip',
    'stat_type',
]


def generate_team_season_page(team_name, season_num, abbr):
    standing = teams_data.standings[
        (teams_data.standings['teamName'] == team_name) &
        (teams_data.standings['Season'] == season_num)
    ]
    if standing.empty:
        return
    row = standing.iloc[0]
    w, l = int(row['gamesWon']), int(row['gamesLost'])
    win_pct = fmt_round(w / (w + l), 3, False)

    def _prep(df, cols):
        df = df.copy()
        df['player'] = ''
        available = ['first_name', 'last_name'] + [c for c in cols if c in df.columns]
        for extra in ('season', 'team'):
            if extra in df.columns and extra not in available:
                available.append(extra)
        return df[list(dict.fromkeys(available))]

    bat_stats = bat_module.stats[
        (bat_module.stats['team'] == abbr) &
        (bat_module.stats['season'] == season_num) &
        (bat_module.stats['stat_type'] != 'career')
    ].sort_values('pa', ascending=False)

    pit_stats = pit_module.stats[
        (pit_module.stats['team'] == abbr) &
        (pit_module.stats['season'] == season_num) &
        (pit_module.stats['stat_type'] != 'career')
    ].sort_values('p_ip', ascending=False)

    team_seasons = sorted(
        teams_data.standings[teams_data.standings['teamName'] == team_name]['Season'].unique()
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

        h2("Stats")
        p("Individual player stats here may show stats that a player achieved with another team "
          "or may not be present at all (in the case of mid-season transactions).")
        h3("Standard Batting")
        render_table(_prep(bat_stats, _BAT_COLS), depth=2, hidden={'season', 'team'}, pitching=False)

        h3("Standard Pitching")
        render_table(_prep(pit_stats, _PIT_COLS), depth=2, hidden={'season', 'team'}, pitching=True)

        if teams_data.schedules.get(season_num) is not None:
            h2("Game Log")
            import pandas as pd
            sched = teams_data.schedules[season_num]
            games = sched[(sched['Home Team'] == team_name) | (sched['Away Team'] == team_name)].copy()
            games = games.sort_values('Game #').reset_index(drop=True)
            w_count = l_count = streak_char = streak_len = 0
            gl_rows = []
            import math
            for game_num, (_, g) in enumerate(games.iterrows(), start=1):
                home      = g['Home Team'] == team_name
                opp       = g['Away Team'] if home else g['Home Team']
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
            render_table(pd.DataFrame(gl_rows), depth=2, hidden={'season'}, pitching=False)

    slug = team_name.replace(' ', '')
    Path(f"docs/teams/{slug}/{season_num}.html").write_text(str(doc))
