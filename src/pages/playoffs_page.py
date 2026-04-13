"""Generate the Playoffs page (docs/playoffs.html)."""
from pathlib import Path

from dominate.tags import *

from pages.page_utils import make_doc


def generate_playoffs():
    doc = make_doc("Playoffs", depth=0)
    with doc:
        h1("Playoffs")
    Path("docs/playoffs.html").write_text(str(doc))
