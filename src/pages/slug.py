"""URL slug helpers for players, teams, and seasons."""


def convert_name(first, last):
    """Turn a player name into a filename-safe string."""
    return f"{first.replace(' ', '')}{last.replace(' ', '')}"
