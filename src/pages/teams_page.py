"""Generate the Teams index page (docs/teams/index.html) and individual team pages."""
from pathlib import Path

from dominate.tags import *

from pages.team_page import generate_team_page
from data import players
from data import teams as teams_data
from util import make_doc


def generate_teams_index():
    teams  = teams_data.teams
    roster = players.player_info.reset_index()

    doc = make_doc("BFBL Teams")
    with doc:
        h1("Teams")
        conferences = list(dict.fromkeys(teams['conference_name']))
        for conf in conferences:
            h2(conf)
            conf_teams = teams[teams['conference_name'] == conf]
            divisions = list(dict.fromkeys(conf_teams['division_name']))
            for div in divisions:
                h3(div)
                div_teams = conf_teams[conf_teams['division_name'] == div]
                with ul():
                    for _, row in div_teams.iterrows():
                        slug = row['team_name'].replace(' ', '')
                        li(a(row['team_name'], href=f"{slug}/index.html"))

    Path("docs/teams").mkdir(parents=True, exist_ok=True)
    Path("docs/teams/index.html").write_text(str(doc))

    for _, row in teams.iterrows():
        team_name = row['team_name']
        team_roster = roster[roster['team_name'] == team_name]
        generate_team_page(team_name, team_roster, row)
