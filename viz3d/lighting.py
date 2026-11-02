"""Sun, sky fill, bounce light and haze (the model1.jpeg mood)."""

from __future__ import annotations

from typing import Tuple

from panda3d.core import (
    AmbientLight, DirectionalLight, Fog, NodePath, Vec3, Vec4,
)

HAZE = (0.78, 0.40, 0.42)


def setup_lighting(render: NodePath, center: Tuple[float, float, float],
                   extent: float, shadow_size: int = 4096) -> NodePath:
    """Add the lights and fog to ``render`` and return the sun node."""
    sun = DirectionalLight("sun")
    sun.setColor(Vec4(1.05, 0.80, 0.55, 1))
    sun.setShadowCaster(True, shadow_size, shadow_size)
    lens = sun.getLens()
    lens.setFilmSize(extent * 1.5, extent * 1.5)
    lens.setNearFar(extent * 1.1, extent * 2.9)
    sun_np = render.attachNewNode(sun)
    direction = Vec3(0.62, -0.30, 0.62)
    direction.normalize()
    sun_np.setPos(center[0] + direction.x * extent * 2,
                  center[1] + direction.y * extent * 2,
                  center[2] + direction.z * extent * 2)
    sun_np.lookAt(center[0], center[1], center[2])
    render.setLight(sun_np)

    sky = AmbientLight("sky")
    sky.setColor(Vec4(0.50, 0.43, 0.64, 1))
    render.setLight(render.attachNewNode(sky))

    bounce = DirectionalLight("bounce")
    bounce.setColor(Vec4(0.28, 0.13, 0.18, 1))
    bounce_np = render.attachNewNode(bounce)
    bounce_np.setHpr(-20, 55, 0)
    render.setLight(bounce_np)

    fog = Fog("haze")
    fog.setColor(*HAZE)
    fog.setExpDensity(0.0012)
    render.setFog(fog)
    render.setShaderAuto()
    return sun_np
