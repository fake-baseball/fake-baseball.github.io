"""Generate the games index page (docs/games/index.html)."""
from dominate.tags import h1, ul, li, a
from pathlib import Path

from data.games import load_games, GAMES_DST
from pages.page_utils import make_doc


def generate_games():
    games = load_games()

    doc = make_doc("Games")
    with doc:
        h1("Games")
        with ul():
            for filename, title in games:
                li(a(title, href=filename))
    (GAMES_DST / "index.html").write_text(str(doc))
