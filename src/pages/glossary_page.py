"""Generate the Glossary page (docs/glossary.html)."""
from pathlib import Path

from dominate.tags import *

from registry import REGISTRY
from util import make_doc


_SECTIONS = [
    ('batting',     'Batting'),
    ('baserunning', 'Baserunning'),
    ('fielding',    'Fielding'),
    ('pitching',    'Pitching'),
]


def _stat_list(context):
    stats = [(k, v) for k, v in REGISTRY.items()
             if v.get('context') == context and 'label' in v]
    with dl():
        for key, meta in stats:
            dt(f"{meta['label']} ({meta['name']})")
            dd(meta.get('description', ''))


def generate_glossary():
    doc = make_doc("Glossary", depth=0)
    with doc:
        h1("Glossary")

        for context, title in _SECTIONS:
            h2(title)
            _stat_list(context)

        h2("WAR Methodology")
        h3("Position Players")
        p(
            "WAR is built from five run-value components. "
            "Rbat measures batting runs above average using wRAA, park-adjusted and scaled to league run environment. "
            "Rbr measures baserunning runs above average from stolen base attempts, weighted by the run value of a successful steal and a caught stealing. "
            "Rdef measures defensive runs above average from errors and passed balls relative to positional averages. "
            "Rpos is a fixed positional adjustment that credits players at premium defensive positions. "
            "Rcorr is a small zero-sum correction applied proportionally by plate appearances each season to ensure the league sums to zero RAA. "
            "These five components sum to RAA (runs above average). "
            "Rrep adds replacement-level run credit proportional to plate appearances, giving RAR (runs above replacement). "
            "WAR = RAR divided by the season's runs-per-win value."
        )
        h3("Pitchers")
        p(
            "Pitcher WAR begins with RA9def, the pitcher's runs-allowed rate adjusted for team defense (via BABIP differential) and park factor. "
            "RAA compares RA9def to a role-specific replacement level (starter vs. reliever) over the pitcher's innings. "
            "Rcorr applies a zero-sum correction proportional to innings pitched. "
            "Rlev adds a leverage bonus for saves and penalizes non-save relief appearances relative to a neutral-leverage baseline. "
            "RAAlev = RAA + Rlev. "
            "Rrep adds replacement-level run credit based on innings pitched and role, giving RAR. "
            "WAR = RAR divided by the season's runs-per-win value."
        )

        h2("Qualification Thresholds")

        h2("Park Factors")

        h2("Cy Young Predictor")

    Path("docs/glossary.html").write_text(str(doc))
