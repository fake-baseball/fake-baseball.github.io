"""Load and prepare game HTML files for display."""
import re
import shutil
from pathlib import Path

GAMES_SRC = Path("data/games")
GAMES_DST = Path("docs/games")

_TITLE_RE = re.compile(r'<title>(.*?)</title>', re.IGNORECASE)
_STYLESHEET = '<link rel="stylesheet" href="../style.css">'


def _extract_title(path):
    m = _TITLE_RE.search(path.read_text())
    return m.group(1) if m else path.stem


def load_games():
    """Copy game files to docs/games/ (injecting stylesheet) and return list of (filename, title)."""
    GAMES_DST.mkdir(parents=True, exist_ok=True)
    games = []
    for src in sorted(GAMES_SRC.glob("*.html")):
        content = src.read_text().replace('</head>', f'{_STYLESHEET}</head>', 1)
        (GAMES_DST / src.name).write_text(content)
        games.append((src.name, _extract_title(src)))
    return games
