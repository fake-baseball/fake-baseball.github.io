"""Season-level calculations: split records, head-to-head matrix."""
import math
from constants import num_games
from data import teams as teams_data


def split_records(sched, div_map, conf_map, winning_teams):
    """Return dict: team -> split W-L records, each a [w, l] list.

    winning_teams: set of team names that finished with a winning record.
    Shutout W = games where team held opponent to 0; L = games where team was held to 0.
    """
    keys = ['div', 'conf', 'inter', 'one_run', 'blowout', 'home', 'away', 'vs500',
            'first_half', 'second_half', 'last10', 'shutout']
    records = {t: {k: [0, 0] for k in keys} for t in div_map}

    HALF = num_games // 2  # first half = games 1-40, second half = games 41-80
    total_games = {t: 0 for t in div_map}
    for _, g in sched.iterrows():
        if isinstance(g['Home Score'], float) and math.isnan(g['Home Score']):
            continue
        total_games[g['Home Team']] += 1
        total_games[g['Away Team']] += 1
    game_count = {t: 0 for t in div_map}

    for _, g in sched.sort_values('Game #').iterrows():
        if isinstance(g['Home Score'], float) and math.isnan(g['Home Score']):
            continue
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
            half = 'first_half' if game_count[team] <= HALF else 'second_half'
            records[team][half][idx] += 1
            if game_count[team] > total_games[team] - 10:
                records[team]['last10'][idx] += 1
            if os == 0:
                records[team]['shutout'][0] += 1  # team shut out opponent (always a win)
            if ts == 0:
                records[team]['shutout'][1] += 1  # team was shut out (always a loss)
    return records


def vs_division_records(season_num):
    """Return (divisions, records_dict) for per-division records.

    divisions: ordered list of division names.
    records_dict: team -> div_name -> [wins, losses]
    Returns (None, None) if no schedule data available.
    """
    sched = teams_data.schedules.get(season_num)
    if sched is None:
        return None, None
    teams_df = teams_data.teams
    div_map = teams_df.set_index('team_name')['division_name'].to_dict()
    divisions = list(dict.fromkeys(teams_df['division_name']))
    records = {t: {d: [0, 0] for d in divisions} for t in div_map}
    for _, g in sched.iterrows():
        ht, at = g['Home Team'], g['Away Team']
        hs, as_ = int(g['Home Score']), int(g['Away Score'])
        opp_div_ht = div_map.get(at)
        opp_div_at = div_map.get(ht)
        if opp_div_ht and ht in records:
            if hs > as_:
                records[ht][opp_div_ht][0] += 1
            else:
                records[ht][opp_div_ht][1] += 1
        if opp_div_at and at in records:
            if as_ > hs:
                records[at][opp_div_at][0] += 1
            else:
                records[at][opp_div_at][1] += 1
    return divisions, records


def h2h_records(season_num):
    """Return (team_order, abbr_map, records_dict) for a head-to-head matrix.

    records_dict: (team, opp) -> [wins, losses] from team's perspective.
    Returns None if no schedule data available.
    """
    sched = teams_data.schedules.get(season_num)
    if sched is None:
        return None, None, None
    team_order = list(dict.fromkeys(
        teams_data.standings[teams_data.standings['Season'] == season_num]
        .sort_values(['conference_name', 'division_name', 'gamesWon'], ascending=[True, True, False])
        ['teamName']
    ))
    abbr_map = teams_data.teams.set_index('team_name')['abbr'].to_dict()
    records = {}
    for _, g in sched.iterrows():
        if isinstance(g['Home Score'], float) and math.isnan(g['Home Score']):
            continue
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
    return team_order, abbr_map, records
