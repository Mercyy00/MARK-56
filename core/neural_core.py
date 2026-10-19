"""
core/neural_core.py — J.A.R.V.I.S. MARK LVI 3D Holographic Neural Core
Locked Physics:
  - Particle Density: 25% (0.25)
  - Radial Spoke Flux: 0.35x
  - Curl Turbulence: 1.90x
  - Gimbal Velocity: 1.55x
  - Photon Size: 0.50x

Full 3D holographic particle swarm + triple gyroscopic gimbal rings + reactive
waveform flux. Rendered via high-performance vector QPainter with depth sorting.
"""

from __future__ import annotations

import math
import random
import time
from typing import List, Tuple

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient

# ── LOCKED NEURAL PHYSICS SPECIFICATION ──────────────────────────────────────────
LOCKED_PHYSICS = {
    "particle_density": 0.25,      # 25% particle density
    "radial_spoke_flux": 0.35,     # 0.35x
    "curl_turbulence": 1.90,       # 1.90x
    "gimbal_velocity": 1.55,       # 1.55x
    "photon_size": 0.50,           # 0.50x
}

_NUM_PARTICLES = int(480 * LOCKED_PHYSICS["particle_density"])  # ~120 3D node points for smooth 60fps vector blitting


def _blend_color(c1: QColor | Qt.GlobalColor, c2: QColor | Qt.GlobalColor, ratio: float, alpha: float = 1.0) -> QColor:
    c1 = QColor(c1)
    c2 = QColor(c2)
    r = int(c1.red() * (1 - ratio) + c2.red() * ratio)
    g = int(c1.green() * (1 - ratio) + c2.green() * ratio)
    b = int(c1.blue() * (1 - ratio) + c2.blue() * ratio)
    a = int(255 * max(0.0, min(1.0, alpha)))
    return QColor(r, g, b, a)



class NeuralParticle:
    """3D point on spherical manifold with locked curl turbulence and flux."""

    def __init__(self, u: float, v: float, index: int):
        self.u = u  # azimuth
        self.v = v  # inclination
        self.index = index
        self.base_r = 0.72 + 0.28 * random.random()
        self.phase = random.random() * math.pi * 2
        self.speed = 0.8 + 0.4 * random.random()
        self.freq = 1.0 + random.random() * 2.0


class HolographicNeuralCore:
    """
    3D Holographic Neural Core for MARK LVI.
    Renders 3D particle shell with curl turbulence, triple gyroscopic gimbals,
    radial spoke flux, and acoustic audio spectrum reactivity.
    """

    def __init__(self):
        self.physics = LOCKED_PHYSICS.copy()
        self._particles: List[NeuralParticle] = []
        self._init_particle_swarm()

        # Rotation angles for 3 gimbals
        self._rot_x = 0.0
        self._rot_y = 0.0
        self._rot_z = 0.0

        # State transitions
        self._smooth_amp = 0.0
        self._state_blend = 0.0
        self._last_time = time.time()

    def _init_particle_swarm(self):
        # Golden ratio spherical Fibonacci distribution
        phi = (1 + math.sqrt(5)) / 2
        for i in range(_NUM_PARTICLES):
            theta = 2 * math.pi * i / phi
            inclination = math.acos(1 - 2 * (i + 0.5) / _NUM_PARTICLES)
            self._particles.append(NeuralParticle(theta, inclination, i))

    def step(self, dt: float, amp: float, state: str, speaking: bool):
        # Update audio amplitude smoothing
        self._smooth_amp += (amp - self._smooth_amp) * min(1.0, dt * 14.0)

        # Base gimbal angular rate (governed by locked Gimbal Velocity = 1.55x)
        vel = self.physics["gimbal_velocity"]
        if state in ("THINKING", "PROCESSING"):
            vel *= 2.4
        elif speaking or state == "SPEAKING":
            vel *= 1.8
        elif state == "LISTENING":
            vel *= 1.2
        else:
            vel *= 0.85

        self._rot_x += dt * 0.45 * vel
        self._rot_y += dt * 0.65 * vel
        self._rot_z += dt * 0.35 * vel

    def paint(
        self,
        p: QPainter,
        cx: float,
        cy: float,
        r: float,
        main: QColor,
        acc: QColor,
        bg: QColor,
        state: str = "LISTENING",
        speaking: bool = False,
        amp: float = 0.0,
        tick: int = 0,
        name: str = "J.A.R.V.I.S",
    ) -> None:
        if r < 12.0:
            return
        now = time.time()
        dt = max(0.001, min(0.1, now - self._last_time))
        self._last_time = now
        self.step(dt, amp, state, speaking)

        eff_amp = self._smooth_amp
        curl = self.physics["curl_turbulence"]
        flux = self.physics["radial_spoke_flux"]
        photon = self.physics["photon_size"]

        # ── 1. BACKGROUND GLOW & RETICLE ───────────────────────────────────────────
        core_r = r * 0.88
        glow_grad = QRadialGradient(QPointF(cx, cy), core_r)
        glow_alpha = 0.12 + 0.25 * eff_amp
        if state in ("THINKING", "PROCESSING"):
            glow_col = acc
            glow_alpha += 0.15
        elif speaking or state == "SPEAKING":
            glow_col = acc
            glow_alpha += 0.28
        else:
            glow_col = main

        glow_grad.setColorAt(0.0, _blend_color(glow_col, Qt.GlobalColor.white, 0.35, glow_alpha))
        glow_grad.setColorAt(0.4, _blend_color(glow_col, bg, 0.2, glow_alpha * 0.6))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(glow_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # ── 2. TRIPLE GYROSCOPIC GIMBALS (3D ROTATING RINGS) ─────────────────────────
        # Outer Gimbal Ring (Rotated around X and Y)
        self._paint_3d_ring(p, cx, cy, r * 0.94, self._rot_x, self._rot_y * 0.7, main, 0.35, 1.4)

        # Mid Gimbal Ring (Rotated around Y and Z with ticks)
        self._paint_3d_ring(p, cx, cy, r * 0.76, self._rot_y, self._rot_z * 0.9, acc, 0.55 + 0.3 * eff_amp, 1.8, ticks=36)

        # Inner Gimbal Ring (Fast core rotation)
        self._paint_3d_ring(p, cx, cy, r * 0.55, self._rot_z * 1.4, self._rot_x * 1.1, main, 0.75 + 0.2 * eff_amp, 1.5)

        # ── 3. RADIAL SPOKE FLUX (Locked to 0.35x) ──────────────────────────────────
        num_spokes = 32
        spoke_base_len = r * 0.40 * flux
        spoke_var = r * 0.25 * eff_amp
        spoke_pen = QPen(_blend_color(acc, main, 0.4, 0.5 + 0.4 * eff_amp), 1.2)
        p.setPen(spoke_pen)
        for i in range(num_spokes):
            ang = math.radians(i * (360.0 / num_spokes) + (tick * 0.4))
            cos_a, sin_a = math.cos(ang), math.sin(ang)
            harmonic = 0.5 + 0.5 * math.sin(ang * 4.0 + now * 5.0)
            slen = spoke_base_len + spoke_var * harmonic
            p.drawLine(
                QPointF(cx + cos_a * (r * 0.48), cy + sin_a * (r * 0.48)),
                QPointF(cx + cos_a * (r * 0.48 + slen), cy + sin_a * (r * 0.48 + slen)),
            )

        # ── 4. 3D PARTICLE SWARM WITH CURL TURBULENCE ──────────────────────────────
        points_to_draw: List[Tuple[float, float, float, float]] = []  # (x, y, z_depth, radius)

        rx, ry, rz = self._rot_x, self._rot_y, self._rot_z
        cx_x, sx_x = math.cos(rx), math.sin(rx)
        cy_y, sy_y = math.cos(ry), math.sin(ry)
        cz_z, sz_z = math.cos(rz), math.sin(rz)

        core_scale = r * 0.42
        if state == "LISTENING":
            core_scale *= (0.88 - 0.15 * eff_amp)  # inward acoustic contraction
        elif state in ("THINKING", "PROCESSING"):
            core_scale *= (0.75 + 0.1 * math.sin(now * 8.0))  # dense vortex compression
        elif speaking or state == "SPEAKING":
            core_scale *= (1.05 + 0.28 * eff_amp)  # harmonic outward emission

        t_noise = now * 1.5 * curl

        for pt in self._particles:
            # Spherical coordinate to Cartesian
            u = pt.u + now * 0.2 * pt.speed
            v = pt.v + math.sin(now * 0.3 * pt.speed + pt.phase) * 0.1

            # Locked curl turbulence displacement
            noise_val = math.sin(u * 3.0 + t_noise) * math.cos(v * 2.0 - t_noise) * (0.18 * curl)
            rad = pt.base_r * core_scale * (1.0 + noise_val + eff_amp * 0.4)

            px = rad * math.sin(v) * math.cos(u)
            py = rad * math.cos(v)
            pz = rad * math.sin(v) * math.sin(u)

            # 3D Euler Rotation
            # Y rotation
            x1 = px * cy_y + pz * sy_y
            y1 = py
            z1 = -px * sy_y + pz * cy_y

            # X rotation
            x2 = x1
            y2 = y1 * cx_x - z1 * sx_x
            z2 = y1 * sx_x + z1 * cx_x

            # Z rotation
            x3 = x2 * cz_z - y2 * sz_z
            y3 = x2 * sz_z + y2 * cz_z
            z3 = z2

            # Perspective projection
            fov = max(50.0, r * 2.8)
            denom = max(1.0, fov + z3)
            depth_scale = fov / denom
            screen_x = cx + x3 * depth_scale
            screen_y = cy + y3 * depth_scale

            particle_radius = max(1.0, (2.2 * photon) * depth_scale * (1.0 + eff_amp * 0.6))
            points_to_draw.append((screen_x, screen_y, z3, particle_radius))

        # Sort particles back-to-front by depth
        points_to_draw.sort(key=lambda item: item[2])

        # Draw particles with depth attenuation
        p.setPen(Qt.PenStyle.NoPen)
        core_scale_denom = max(1.0, core_scale * 2.0)
        for sx, sy_pt, z_depth, p_radius in points_to_draw:
            norm_depth = (z_depth + core_scale) / core_scale_denom
            norm_depth = max(0.05, min(1.0, norm_depth))
            alpha = 0.25 + 0.70 * norm_depth
            if eff_amp > 0.05:
                p_col = _blend_color(acc, main, 0.3, alpha)
            else:
                p_col = _blend_color(main, Qt.GlobalColor.white, 0.2 * norm_depth, alpha)

            p.setBrush(QBrush(p_col))
            p.drawEllipse(QPointF(sx, sy_pt), p_radius, p_radius)

        # ── 5. ARC REACTOR CENTERPIECE / SINGULARITY ────────────────────────────────
        center_r = max(6.0, r * (0.10 + 0.08 * eff_amp))
        center_grad = QRadialGradient(QPointF(cx, cy), center_r)
        center_grad.setColorAt(0.0, QColor(255, 255, 255, 240))
        center_grad.setColorAt(0.5, _blend_color(acc, Qt.GlobalColor.white, 0.4, 0.85))
        center_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(center_grad))
        p.drawEllipse(QPointF(cx, cy), center_r, center_r)

        # ── 6. CENTER IDENTITY BADGE / TELEMETRY ─────────────────────────────────────
        if name:
            p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
            p.setPen(QPen(_blend_color(Qt.GlobalColor.white, main, 0.3, 0.75 + 0.25 * eff_amp), 1))
            badge_rect = QRectF(cx - r * 0.4, cy - 8, r * 0.8, 16)
            p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, name)

    def _paint_3d_ring(
        self,
        p: QPainter,
        cx: float,
        cy: float,
        radius: float,
        rot_a: float,
        rot_b: float,
        color: QColor,
        alpha: float,
        width: float,
        ticks: int = 0,
    ) -> None:
        """Projects a circular ring in 3D perspective to an ellipse."""
        if radius < 5.0:
            return
        tilt_y = math.sin(rot_a) * 0.55
        tilt_x = math.cos(rot_b) * 0.35
        semi_major = radius
        semi_minor = radius * max(0.2, math.sqrt(max(0.0, 1.0 - tilt_y * tilt_y)))

        p.save()
        p.translate(cx, cy)
        p.rotate(math.degrees(rot_b * 0.5))

        pen_col = _blend_color(color, Qt.GlobalColor.white, 0.15, alpha)
        p.setPen(QPen(pen_col, width))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(0, 0), semi_major, semi_minor)

        if ticks > 0:
            tick_pen = QPen(_blend_color(color, Qt.GlobalColor.white, 0.3, alpha * 0.8), 1.0)
            p.setPen(tick_pen)
            for i in range(ticks):
                ang = i * (2 * math.pi / ticks)
                tx1 = semi_major * math.cos(ang)
                ty1 = semi_minor * math.sin(ang)
                scale = 1.05 if (i % 4 == 0) else 1.025
                tx2 = semi_major * scale * math.cos(ang)
                ty2 = semi_minor * scale * math.sin(ang)
                p.drawLine(QPointF(tx1, ty1), QPointF(tx2, ty2))

        p.restore()
