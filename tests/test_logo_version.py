"""Guard: the README banner image exists and is non-empty."""
from pathlib import Path

_LOGO = Path(__file__).resolve().parents[1] / "images" / "noxentra-banner.jpg"


def test_banner_image_exists():
    assert _LOGO.is_file() and _LOGO.stat().st_size > 0
