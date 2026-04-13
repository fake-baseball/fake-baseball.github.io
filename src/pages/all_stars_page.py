"""Generate the All-Star Voting page (docs/all_stars.html)."""
from pathlib import Path

from dominate.tags import h1, h2, h3, h4, p

from constants import CURRENT_SEASON
from data import teams as teams_data
from leaders import get_leaders
from pages.page_utils import make_doc, render_table

_BAT_COLS = ['player_name', 'team', 'season', 'b_gp', 'pa', 'hr', 'r', 'rbi', 'sb',
             'avg', 'obp', 'slg', 'ops', 'woba', 'wrc_plus',
             'r_bat', 'r_br', 'r_def', 'r_pos', 'r_corr', 'r_rep', 'raa', 'rar', 'war',
             'stat_type']

_PIT_COLS = ['player_name', 'team', 'season', 'p_gp', 'p_gs', 'p_sv', 'p_ip',
             'p_w', 'p_l', 'p_era', 'p_fip', 'p_whip', 'p_k', 'p_bb',
             'p_r_def', 'p_raa', 'p_r_lev', 'p_raa_lev', 'p_r_rep', 'p_rar', 'p_war',
             'stat_type']

_POSITIONS = ['C', '1B', '2B', '3B', 'SS', 'OF']
_ROLES = [('SP', 10), ('SP/RP', 5), ('RP', 5), ('CL', 5)]


def generate_all_stars():
    teams = teams_data.teams
    conferences = list(dict.fromkeys(teams['conference_name']))
    abbr_by_conf = teams.groupby('conference_name')['team_id'].apply(list).to_dict()

    doc = make_doc("All-Star Voting", depth=0)
    with doc:
        h1("All-Star Voting")

        h2("Position Players")
        for conf in conferences:
            conf_teams = abbr_by_conf[conf]
            h3(conf)
            for pos in _POSITIONS:
                df = get_leaders('war', season=CURRENT_SEASON, num=10 if pos == 'OF' else 5,
                                 teams=conf_teams, pos=pos)
                h4(pos)
                if df.empty:
                    p("No players.")
                else:
                    render_table(df[_BAT_COLS].reset_index(drop=True), depth=0, hidden={'season'})

        h2("Pitchers")
        for conf in conferences:
            conf_teams = abbr_by_conf[conf]
            h3(conf)
            for role, num in _ROLES:
                df = get_leaders('p_war', season=CURRENT_SEASON, num=num,
                                 teams=conf_teams, role=role)
                h4(role)
                if df.empty:
                    p("No players.")
                else:
                    render_table(df[_PIT_COLS].reset_index(drop=True), depth=0, hidden={'season'})

    Path("docs/all_stars.html").write_text(str(doc))
