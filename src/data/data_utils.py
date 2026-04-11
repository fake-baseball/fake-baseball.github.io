"""Data-layer utilities."""
import re


def convert_name(first, last):
    """Turn a player name into a player_id (filename-safe, used as URL slug).

    Concatenates first and last name, stripping all non-letter characters
    (spaces, periods, hyphens, apostrophes, etc.).
    Example: Kennedy St. King-Smith -> KennedyStKingSmith
    """
    return re.sub(r'[^A-Za-z]', '', first) + re.sub(r'[^A-Za-z]', '', last)
