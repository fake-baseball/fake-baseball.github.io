"""Generate the Playoff Hunt page (docs/playoff_hunt.html)."""
import pandas as pd
from pathlib import Path

from dominate.tags import *

from constants import CURRENT_SEASON
from data import teams as teams_data
from pages.page_utils import make_doc, render_table
from seasons import split_records, strength_of_schedule


def _fmt_rec(w, l):
    return f"{w}-{l}"


def _make_rec(row, gb_val, stype, season_num, split, sos):
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


def _render_section(rows, season_num, split, sos):
    cols = ['team_name', 't_w', 't_l', 't_pct', 't_gb', 't_rs', 't_ra', 't_diff']
    if split:
        cols.append('t_last10')
    if sos:
        cols += ['t_sos', 't_sos_rem']
    render_table(pd.DataFrame(rows)[cols + ['season', 'stat_type']],
                 depth=0, hidden={'season'})


def generate_playoff_hunt():
    season_num  = CURRENT_SEASON
    standings   = teams_data.standings
    season_rows = standings[standings['Season'] == season_num].copy()

    if season_rows.empty:
        doc = make_doc("Playoff Hunt", depth=0)
        with doc:
            h1("Playoff Hunt")
            p("No data for the current season.")
        Path("docs/playoff_hunt.html").write_text(str(doc))
        return

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

    season_rows['Diff']  = season_rows['runsFor'] - season_rows['runsAgainst']
    season_rows['t_pct'] = season_rows['gamesWon'] / (season_rows['gamesWon'] + season_rows['gamesLost'])

    doc = make_doc("Playoff Hunt", depth=0)
    with doc:
        h1("Playoff Hunt")

        for conf_name, conf_group in season_rows.groupby('conference_name', sort=False):
            conf_group = conf_group.copy()
            h2(conf_name)

            div_leader_idx = (
                conf_group.groupby('division_name', sort=False)
                .apply(lambda g: g.sort_values(['t_pct', 'Diff'], ascending=[False, False]).index[0],
                       include_groups=False)
            )
            div_leaders  = conf_group.loc[div_leader_idx].sort_values(['t_pct', 'Diff'], ascending=[False, False])
            non_leaders  = conf_group.drop(index=div_leader_idx).copy()

            # Division leaders table
            h3("Division Leaders")
            lead_max_w = div_leaders.iloc[0]['gamesWon']
            lead_min_l = div_leaders.iloc[0]['gamesLost']
            lead_rows  = []
            for i, (_, row) in enumerate(div_leaders.iterrows()):
                gb = 0.0 if i == 0 else ((lead_max_w - row['gamesWon']) + (row['gamesLost'] - lead_min_l)) / 2
                lead_rows.append(_make_rec(row, gb, 'career', season_num, split, sos))
            _render_section(lead_rows, season_num, split, sos)

            # Wild card table
            if non_leaders.empty:
                continue
            h3("Wild Card")
            wc_leader = non_leaders.sort_values(['t_pct', 'Diff'], ascending=[False, False]).iloc[0]
            max_w, min_l = wc_leader['gamesWon'], wc_leader['gamesLost']
            non_leaders['WC_GB'] = ((max_w - non_leaders['gamesWon']) + (non_leaders['gamesLost'] - min_l)) / 2
            non_leaders = non_leaders.sort_values(['WC_GB', 'Diff'], ascending=[True, False])
            wc_rows = []
            for i, (_, row) in enumerate(non_leaders.iterrows()):
                gb = 0.0 if i == 0 else row['WC_GB']
                wc_rows.append(_make_rec(row, gb, 'season', season_num, split, sos))
            _render_section(wc_rows, season_num, split, sos)

    Path("docs/playoff_hunt.html").write_text(str(doc))
