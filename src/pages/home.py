"""Generate the site home page (docs/index.html)."""
from pathlib import Path

from dominate.tags import *

from util import make_doc


def generate_home(sections):
    _LINKS = [
        ('players',     "Players",              "players/index.html"),
        ('leaders',     "Leaders",              "leaders/index.html"),
        ('seasons',     "Seasons",              "seasons/index.html"),
        ('teams',       "Teams",                "teams/index.html"),
        ('games',       "Games",                "games/index.html"),
        ('awards',      "Awards",               "awards.html"),
        ('projections', "Projections",          "projections.html"),
        ('dh',          "Positional Adjustments", "dh.html"),
        ('salaries',    "Salaries",             "salaries.html"),
        ('cy_young',    "Cy Young Predictor",   "cy_young.html"),
        ('glossary',    "Glossary",             "glossary.html"),
    ]
    doc = make_doc("BFBL Homepage", css='style.css')
    with doc:
        h1("Bryonato's Fake Baseball League")
        for key, label, href in _LINKS:
            if key in sections:
                h2(a(label, href=href))
    Path("docs/index.html").write_text(str(doc))
