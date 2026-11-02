"""Tests for the reusable resources used by the 3D viewer."""

from viz3d.assets import (
    DRONE_MODEL,
    MESAS_MODEL,
    SKY_MODEL,
    site_model_path,
    zone_sprite_path,
)


def test_static_models_are_exported() -> None:
    """Keep the drone and environment models available to the viewer."""
    assert DRONE_MODEL.is_file()
    assert SKY_MODEL.is_file()
    assert MESAS_MODEL.is_file()


def test_official_map_zone_styles_are_exported() -> None:
    """Keep both common and custom official-map zone variants."""
    assert site_model_path("normal", "blue").is_file()
    assert site_model_path("restricted", "brown").is_file()
    assert site_model_path("start", "green").is_file()
    assert site_model_path("end", "rainbow").is_file()


def test_zone_legend_sprites_are_png_images() -> None:
    """Each displayed zone kind has a valid PNG sprite resource."""
    for kind in (
        "start", "end", "normal", "priority", "restricted", "blocked",
    ):
        sprite = zone_sprite_path(kind)
        assert sprite.is_file()
        assert sprite.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
