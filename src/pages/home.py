"""Generate the site home page (docs/index.html)."""
from pathlib import Path

from dominate.tags import *

from util import make_doc


def generate_home():
    doc = make_doc("BFBL Homepage", css='style.css')
    with doc:
        h1("Bryonato's Fake Baseball League")
        h2(a("Players", href="players/index.html"))
        h2(a("Leaders", href="leaders/index.html"))
        h2(a("Seasons", href="seasons/"))
        h2(a("Teams", href="teams/index.html"))
        h2(a("Games", href="games/index.html"))
        h2(a("Awards", href="awards.html"))
    Path("docs/index.html").write_text(str(doc))
