"""
core/taste_skill_parser.py — Ingestion & Interpretation Engine for Taste Skills.

Parses external taste skill definitions from:
  1. Structured JSON / TS object specifications
  2. Markdown skill definitions with YAML frontmatter and rules (e.g. SKILL.md)
  3. Pre-registered canonical taste skill archetypes (Vanguard, Brutalist, Minimalist)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.taste_schema import (
    LayoutConstraintTokens,
    MicroAestheticTokens,
    NegativeConstraints,
    PaletteTokens,
    TasteSkillDefinition,
    TypographyTokens,
)


def get_canonical_vanguard_skill() -> TasteSkillDefinition:
    """Canonical High-End Vanguard UI Architect (Linear / Apple-tier Awwwards style)."""
    return TasteSkillDefinition(
        id="vanguard-ethereal",
        name="Vanguard Ethereal Glass & Motion",
        description="High-end agency grade digital experience with double-bezel enclosures, fluid physics, and OLED contrast.",
        persona="Vanguard_UI_Architect",
        typography=TypographyTokens(
            display_font="'Clash Display', 'Geist', 'Plus Jakarta Sans', sans-serif",
            display_scale="clamp(3.2rem, 7.5vw, 6.8rem)",
            display_tracking="-0.035em",
            display_leading="0.96",
            display_weight="700",
            body_font="'Plus Jakarta Sans', 'Geist Sans', system-ui, sans-serif",
            body_scale="1.0625rem",
            body_tracking="-0.012em",
            body_leading="1.68",
            micro_font="'Geist Mono', ui-monospace, monospace",
            micro_scale="0.6875rem",
            micro_tracking="0.18em",
            accent_serif_font="'PP Editorial New', 'Instrument Serif', serif",
            banned_fonts=["Inter", "Roboto", "Arial", "Open Sans", "Helvetica"],
        ),
        palette=PaletteTokens(
            canvas_bg="#050505",
            surface_bg="#0D0D0E",
            surface_raised="#151518",
            text_primary="#F8FAFC",
            text_secondary="#94A3B8",
            text_muted="#475569",
            border_hairline="rgba(255, 255, 255, 0.08)",
            border_structural="rgba(255, 255, 255, 0.16)",
            accent_primary="#38BDF8",  # Electric Cyan
            accent_secondary="#818CF8",  # Ethereal Indigo
            accent_subtle="rgba(56, 189, 248, 0.12)",
            mode="dark",
            allow_gradients=True,
            overlay_texture="noise",
        ),
        layout=LayoutConstraintTokens(
            macro_padding_y="py-24 md:py-36",
            macro_padding_x="px-6 md:px-12 lg:px-20",
            container_max_w="max-w-7xl",
            section_gap="gap-12 md:gap-20",
            allowed_archetypes=["asymmetrical_bento", "editorial_split", "z_axis_cascade"],
            banned_layouts=["centered-3-card", "edge-to-edge-sticky-nav", "symmetrical-bootstrap-3col"],
        ),
        micro=MicroAestheticTokens(
            enclosure_archetype="double_bezel",
            outer_radius="28px",
            inner_radius="22px",
            pill_radius="9999px",
            button_archetype="nested_island_pill",
            button_padding="px-7 py-3.5",
            shadow_style="ambient_diffuse",
            shadow_rule="0 25px 50px -12px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(255, 255, 255, 0.08)",
            motion_easing="cubic-bezier(0.32, 0.72, 0, 1)",
            transition_duration="600ms",
            entry_animation="fade_slide_up",
        ),
        negative=NegativeConstraints(
            banned_copy=["elevate", "seamless", "next-gen", "game-changer", "unleash", "delve"],
            banned_icons=["generic_thick_lucide", "fa_solid"],
            ban_heavy_shadows=True,
            ban_generic_cards=True,
        ),
    )


def get_canonical_brutalist_skill() -> TasteSkillDefinition:
    """Canonical Industrial Brutalism & Tactical Telemetry (Swiss Print / CRT Terminal)."""
    return TasteSkillDefinition(
        id="industrial-swiss-print",
        name="Swiss Industrial Print & Telemetry",
        description="Rigid modular grid, monolithic neo-grotesque type, carbon ink, and aviation hazard red accents.",
        persona="Tactical_Telemetry_Engineer",
        typography=TypographyTokens(
            display_font="'Archivo Black', 'Neue Haas Grotesk', 'Monument Extended', sans-serif",
            display_scale="clamp(3.8rem, 9.5vw, 9.5rem)",
            display_tracking="-0.045em",
            display_leading="0.88",
            display_casing="uppercase",
            display_weight="900",
            body_font="'Space Grotesk', system-ui, sans-serif",
            body_scale="1.0rem",
            body_tracking="-0.01em",
            body_leading="1.5",
            micro_font="'JetBrains Mono', 'IBM Plex Mono', monospace",
            micro_scale="0.75rem",
            micro_tracking="0.12em",
            micro_casing="uppercase",
            banned_fonts=["Comic Sans", "Papyrus", "Lobster", "Inter"],
        ),
        palette=PaletteTokens(
            canvas_bg="#F4F4F0",  # Unbleached documentation paper
            surface_bg="#EAE8E3",
            surface_raised="#DFDDD8",
            text_primary="#050505",  # Carbon Ink
            text_secondary="#2A2A2A",
            text_muted="#666666",
            border_hairline="#050505",  # Solid visible dividing lines
            border_structural="#050505",
            accent_primary="#E61919",  # Aviation / Hazard Red (ONLY ACCENT)
            accent_secondary="#E61919",
            accent_subtle="rgba(230, 25, 25, 0.1)",
            mode="monochrome_light",
            allow_gradients=False,  # Gradients strictly banned in brutalism
            overlay_texture="grid_lines",
        ),
        layout=LayoutConstraintTokens(
            macro_padding_y="py-16 md:py-28",
            macro_padding_x="px-4 md:px-10 lg:px-16",
            container_max_w="max-w-[1440px]",
            section_gap="gap-0",  # Flush structural borders
            allowed_archetypes=["rigid_modular_grid", "technical_telemetry", "horizon_bleed"],
            banned_layouts=["soft-floating-cards", "centered-3-card", "radial-glows"],
        ),
        micro=MicroAestheticTokens(
            enclosure_archetype="monolithic_raw",
            outer_radius="0px",  # Zero radius in brutalism
            inner_radius="0px",
            pill_radius="0px",
            button_archetype="sharp_tactical_block",
            button_padding="px-8 py-4",
            shadow_style="none",
            shadow_rule="none",
            motion_easing="steps(4, jump-end)",  # Mechanical stepped motion
            transition_duration="150ms",
            entry_animation="instant_cut",
        ),
        negative=NegativeConstraints(
            banned_copy=["elevate", "seamless", "next-gen", "unleash", "future of"],
            banned_icons=["soft_icons", "rounded_pill_badges"],
            ban_heavy_shadows=True,
            ban_generic_cards=True,
        ),
    )


def get_canonical_minimalist_skill() -> TasteSkillDefinition:
    """Canonical Utilitarian Minimalist Editorial (Warm Monochrome & Muted Pastels)."""
    return TasteSkillDefinition(
        id="utilitarian-minimalist",
        name="Utilitarian Minimalist Editorial",
        description="Warm bone substrates, editorial serif headings, bento grid, and muted pastel highlights.",
        persona="Minimalist_Editorial_Architect",
        typography=TypographyTokens(
            display_font="'Newsreader', 'Lyon Text', 'Instrument Serif', serif",
            display_scale="clamp(2.8rem, 6.5vw, 5.5rem)",
            display_tracking="-0.025em",
            display_leading="1.05",
            display_weight="600",
            body_font="'Switzer', 'SF Pro Display', system-ui, sans-serif",
            body_scale="1.0625rem",
            body_tracking="-0.01em",
            body_leading="1.65",
            micro_font="'Geist Mono', monospace",
            micro_scale="0.75rem",
            micro_tracking="0.06em",
            banned_fonts=["Inter", "Roboto", "Open Sans", "Arial"],
        ),
        palette=PaletteTokens(
            canvas_bg="#F7F6F3",  # Warm Bone / Linen
            surface_bg="#FFFFFF",
            surface_raised="#F0EFEB",
            text_primary="#111111",  # Charcoal / Off-black
            text_secondary="#444444",
            text_muted="#787774",
            border_hairline="#EAEAEA",
            border_structural="#DCDCDC",
            accent_primary="#111111",
            accent_secondary="#346538",  # Pale Green
            accent_subtle="#EDF3EC",  # Muted pastel wash
            mode="monochrome_light",
            allow_gradients=False,
            overlay_texture=None,
        ),
        layout=LayoutConstraintTokens(
            macro_padding_y="py-20 md:py-32",
            macro_padding_x="px-6 md:px-12 lg:px-24",
            container_max_w="max-w-6xl",
            section_gap="gap-8 md:gap-14",
            allowed_archetypes=["asymmetrical_bento", "editorial_split"],
            banned_layouts=["centered-3-card", "neon-gradients", "heavy-skeuomorphism"],
        ),
        micro=MicroAestheticTokens(
            enclosure_archetype="flat_bordered",
            outer_radius="10px",
            inner_radius="6px",
            pill_radius="9999px",
            button_archetype="minimal_underline",
            button_padding="px-6 py-2.5",
            shadow_style="none",
            shadow_rule="none",
            motion_easing="cubic-bezier(0.16, 1, 0.3, 1)",
            transition_duration="400ms",
            entry_animation="fade_in",
        ),
        negative=NegativeConstraints(
            banned_copy=["elevate", "seamless", "next-gen", "game-changer", "delve"],
            banned_icons=["thick_lucide", "fa_solid"],
            ban_heavy_shadows=True,
            ban_generic_cards=True,
        ),
    )


class TasteSkillParser:
    """Ingestion mechanism to parse, validate, and index taste skills."""

    _registry: Dict[str, TasteSkillDefinition] = {}

    @classmethod
    def initialize_registry(cls) -> None:
        """Register canonical skills."""
        cls.register(get_canonical_vanguard_skill())
        cls.register(get_canonical_brutalist_skill())
        cls.register(get_canonical_minimalist_skill())

    @classmethod
    def register(cls, skill: TasteSkillDefinition) -> None:
        errs = skill.validate()
        if errs:
            raise ValueError(f"Cannot register invalid taste skill '{skill.id}': {errs}")
        cls._registry[skill.id.lower()] = skill

    @classmethod
    def get(cls, skill_id: str) -> Optional[TasteSkillDefinition]:
        if not cls._registry:
            cls.initialize_registry()
        return cls._registry.get(skill_id.lower())

    @classmethod
    def list_all(cls) -> List[TasteSkillDefinition]:
        if not cls._registry:
            cls.initialize_registry()
        return list(cls._registry.values())

    @classmethod
    def parse_json(cls, json_str_or_path: Union[str, Path]) -> TasteSkillDefinition:
        """Parse taste skill from a JSON string or file path."""
        if isinstance(json_str_or_path, (str, Path)) and Path(str(json_str_or_path)).is_file():
            content = Path(str(json_str_or_path)).read_text(encoding="utf-8")
        else:
            content = str(json_str_or_path)

        data = json.loads(content)
        skill = TasteSkillDefinition.from_dict(data)
        errs = skill.validate()
        if errs:
            raise ValueError(f"Taste skill JSON validation failed: {errs}")
        return skill

    @classmethod
    def parse_markdown_skill(cls, file_path: Union[str, Path]) -> TasteSkillDefinition:
        """
        Parse taste directives directly from an existing SKILL.md file.
        Detects archetype cues, banned tokens, and color patterns.
        """
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError(f"SKILL.md not found at '{file_path}'")

        text = p.read_text(encoding="utf-8")

        # Detect archetype by keywords
        text_lower = text.lower()
        if "brutalism" in text_lower or "tactical telemetry" in text_lower:
            base = get_canonical_brutalist_skill()
        elif "minimalism" in text_lower or "warm monochrome" in text_lower:
            base = get_canonical_minimalist_skill()
        else:
            base = get_canonical_vanguard_skill()

        # Extract frontmatter name / description if present
        name_match = re.search(r"name:\s*(.+)", text)
        desc_match = re.search(r"description:\s*(.+)", text)

        name = name_match.group(1).strip() if name_match else base.name
        desc = desc_match.group(1).strip() if desc_match else base.description
        skill_id = Path(file_path).parent.name or "injected-taste-skill"

        parsed = TasteSkillDefinition(
            id=skill_id,
            name=name,
            description=desc,
            persona=base.persona,
            typography=base.typography,
            palette=base.palette,
            layout=base.layout,
            micro=base.micro,
            negative=base.negative,
        )
        return parsed
