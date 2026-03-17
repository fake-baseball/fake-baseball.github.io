"""Copy game HTML files to docs/games/ and return metadata for the home page."""
import re
import shutil
from pathlib import Path

GAMES_SRC = Path("data/games")
GAMES_DST = Path("docs/games")

_TITLE_RE = re.compile(r'<title>(.*?)</title>', re.IGNORECASE)


def _extract_title(path):
    m = _TITLE_RE.search(path.read_text())
    return m.group(1) if m else path.stem


_STYLESHEET = '<link rel="stylesheet" href="../style.css">'


def generate_games():
    """Copy game files to docs/games/ (injecting stylesheet) and generate docs/games/index.html."""
    from dominate.tags import h1, ul, li, a
    from util import make_doc

    GAMES_DST.mkdir(parents=True, exist_ok=True)
    games = []
    for src in sorted(GAMES_SRC.glob("*.html")):
        content = src.read_text().replace('</head>', f'{_STYLESHEET}</head>', 1)
        (GAMES_DST / src.name).write_text(content)
        games.append((src.name, _extract_title(src)))

    doc = make_doc("Games")
    with doc:
        h1("Games")
        with ul():
            for filename, title in games:
                li(a(title, href=filename))
    (GAMES_DST / "index.html").write_text(str(doc))
