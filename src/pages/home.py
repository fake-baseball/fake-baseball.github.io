"""Generate the site home page (docs/index.html)."""
from pathlib import Path

from dominate.tags import *

from pages.page_utils import make_doc, NAV_LINKS


def generate_home(sections):
    doc = make_doc("BFBL Homepage", depth=0, nav=False)
    with doc:
        h1("Bryonato's Fake Baseball League")
        for key, label, href in NAV_LINKS:
            if key in sections:
                h2(a(label, href=href))
    Path("docs/index.html").write_text(str(doc))
