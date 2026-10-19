"""
core/taste_schema.py — Formal Data Schema for Taste Skills in J.A.R.V.I.S. MARK LVI.

Defines the core data contracts and validation rules for aesthetic inputs:
  • Typography primitives (display, body, micro/mono, accent serif, banned fonts)
  • Palette & substrate systems (canvas, surfaces, carbon text, single-accent constraints)
  • Layout constraints (macro-whitespace, grid archetypes, mobile collapse, banned layouts)
  • Micro-aesthetics (enclosures: double-bezel/flat/monolithic, button archetypes, fluid motion)
  • Negative constraints (banned fonts, banned drop-shadows, banned copywriting clichés)
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Set, Tuple


@dataclass
class TypographyTokens:
    """Typographic primitives governing hierarchical scales and letterform constraints."""
    display_font: str
    display_scale: str  # e.g. "clamp(3.5rem, 8vw, 7.5rem)"
    display_tracking: str  # e.g. "-0.04em"
    display_leading: str  # e.g. "0.95"
    display_casing: Literal["uppercase", "lowercase", "none"] = "none"
    display_weight: str = "800"

    body_font: str = "system-ui, -apple-system, sans-serif"
    body_scale: str = "1.0625rem"  # 17px
    body_tracking: str = "-0.01em"
    body_leading: str = "1.65"
    body_weight: str = "400"

    micro_font: str = "ui-monospace, monospace"
    micro_scale: str = "0.75rem"  # 12px
    micro_tracking: str = "0.1em"
    micro_casing: Literal["uppercase", "none"] = "uppercase"
    micro_weight: str = "500"

    accent_serif_font: Optional[str] = None
    banned_fonts: List[str] = field(default_factory=lambda: [
        "Inter", "Roboto", "Arial", "Open Sans", "Helvetica", "Comic Sans"
    ])

    def validate(self) -> List[str]:
        errors = []
        for banned in self.banned_fonts:
            if banned.lower() in self.display_font.lower():
                errors.append(f"display_font '{self.display_font}' contains banned font '{banned}'")
            if banned.lower() in self.body_font.lower():
                errors.append(f"body_font '{self.body_font}' contains banned font '{banned}'")
        return errors


@dataclass
class PaletteTokens:
    """Color substrate and semantic highlight tokens."""
    canvas_bg: str  # e.g. "#050505" or "#F4F4F0"
    surface_bg: str  # e.g. "#111111" or "#FFFFFF"
    surface_raised: str  # e.g. "#181818" or "#EAE8E3"

    text_primary: str  # e.g. "#F8FAFC" or "#050505"
    text_secondary: str  # e.g. "#94A3B8" or "#555555"
    text_muted: str  # e.g. "#64748B" or "#888888"

    border_hairline: str  # e.g. "rgba(255, 255, 255, 0.08)" or "rgba(0, 0, 0, 0.12)"
    border_structural: str  # e.g. "rgba(255, 255, 255, 0.18)" or "#111111"

    accent_primary: str  # e.g. "#0284C7" or "#E61919"
    accent_secondary: Optional[str] = None
    accent_subtle: Optional[str] = None  # e.g. for muted tags / pastels

    mode: Literal["dark", "light", "monochrome_light", "monochrome_dark"] = "dark"
    allow_gradients: bool = False
    overlay_texture: Optional[str] = None  # e.g. "noise", "scanlines", "grid_dots"

    def validate(self) -> List[str]:
        errors = []
        if not self.canvas_bg.startswith(("#", "rgb", "hsl")):
            errors.append(f"Invalid canvas_bg color spec: {self.canvas_bg}")
        if not self.text_primary.startswith(("#", "rgb", "hsl")):
            errors.append(f"Invalid text_primary color spec: {self.text_primary}")
        return errors


@dataclass
class LayoutConstraintTokens:
    """Spatial rhythm, whitespace scaling, and structural grid rules."""
    macro_padding_y: str = "py-24 md:py-36"
    macro_padding_x: str = "px-6 md:px-12 lg:px-20"
    container_max_w: str = "max-w-7xl"
    section_gap: str = "gap-12 md:gap-20"

    allowed_archetypes: List[str] = field(default_factory=lambda: [
        "asymmetrical_bento", "editorial_split", "z_axis_cascade", "rigid_modular_grid"
    ])
    banned_layouts: List[str] = field(default_factory=lambda: [
        "centered-3-card", "edge-to-edge-sticky-nav", "symmetrical-bootstrap-3col"
    ])
    mobile_collapse_rule: str = "Stack vertically with full-width cards and generous gap"


@dataclass
class MicroAestheticTokens:
    """Component-level styling, haptic depth, and interaction dynamics."""
    enclosure_archetype: Literal["double_bezel", "flat_bordered", "monolithic_raw", "glass_acrylic"] = "double_bezel"
    outer_radius: str = "24px"
    inner_radius: str = "18px"
    pill_radius: str = "9999px"

    button_archetype: Literal["nested_island_pill", "sharp_tactical_block", "minimal_underline", "bezel_stamp"] = "nested_island_pill"
    button_padding: str = "px-7 py-3.5"

    shadow_style: Literal["ambient_diffuse", "crisp_hard", "none"] = "ambient_diffuse"
    shadow_rule: str = "0 20px 40px -15px rgba(0, 0, 0, 0.4)"

    motion_easing: str = "cubic-bezier(0.32, 0.72, 0, 1)"
    transition_duration: str = "500ms"
    entry_animation: str = "fade_slide_up"


@dataclass
class NegativeConstraints:
    """Global bans that prevent AI template clichés and generic output."""
    banned_copy: List[str] = field(default_factory=lambda: [
        "elevate", "seamless", "next-gen", "game-changer", "unleash", "delve", "testament"
    ])
    banned_icons: List[str] = field(default_factory=lambda: [
        "generic_thick_lucide", "fa_solid", "material_filled"
    ])
    ban_heavy_shadows: bool = True
    ban_generic_cards: bool = True


@dataclass
class TasteSkillDefinition:
    """The master taste skill manifest governing end-to-end frontend synthesis."""
    id: str
    name: str
    description: str
    persona: str
    typography: TypographyTokens
    palette: PaletteTokens
    layout: LayoutConstraintTokens
    micro: MicroAestheticTokens
    negative: NegativeConstraints = field(default_factory=NegativeConstraints)

    def validate(self) -> List[str]:
        """Validate the full specification and return any structural errors."""
        errs = []
        errs.extend(self.typography.validate())
        errs.extend(self.palette.validate())
        return errs

    def generate_css_variables(self) -> str:
        """Render CSS custom properties representing the full design tokens."""
        p = self.palette
        t = self.typography
        m = self.micro
        l = self.layout

        return f""":root {{
  /* Substrates & Colors */
  --bg-canvas: {p.canvas_bg};
  --bg-surface: {p.surface_bg};
  --bg-raised: {p.surface_raised};
  --text-primary: {p.text_primary};
  --text-secondary: {p.text_secondary};
  --text-muted: {p.text_muted};
  --border-hairline: {p.border_hairline};
  --border-structural: {p.border_structural};
  --accent-primary: {p.accent_primary};
  --accent-secondary: {p.accent_secondary or p.accent_primary};
  --accent-subtle: {p.accent_subtle or p.border_hairline};

  /* Typography */
  --font-display: {t.display_font};
  --font-body: {t.body_font};
  --font-micro: {t.micro_font};
  --scale-display: {t.display_scale};
  --tracking-display: {t.display_tracking};
  --leading-display: {t.display_leading};

  /* Micro-Aesthetics & Spacing */
  --radius-outer: {m.outer_radius};
  --radius-inner: {m.inner_radius};
  --radius-pill: {m.pill_radius};
  --shadow-ambient: {m.shadow_rule if m.shadow_style != "none" else "none"};
  --motion-ease: {m.motion_easing};
  --motion-dur: {m.transition_duration};
}}"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass tree to dictionary representation."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TasteSkillDefinition":
        """Instantiate a TasteSkillDefinition from a dictionary."""
        typo = TypographyTokens(**data.get("typography", {}))
        pal = PaletteTokens(**data.get("palette", {}))
        lay = LayoutConstraintTokens(**data.get("layout", {}))
        mic = MicroAestheticTokens(**data.get("micro", {}))
        neg = NegativeConstraints(**data.get("negative", {})) if "negative" in data else NegativeConstraints()

        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            persona=data.get("persona", "Vanguard_UI_Architect"),
            typography=typo,
            palette=pal,
            layout=lay,
            micro=mic,
            negative=neg,
        )
