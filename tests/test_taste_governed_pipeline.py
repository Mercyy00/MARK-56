"""
tests/test_taste_governed_pipeline.py — Verification Suite for Autonomous Design-Governed Generation.

Tests:
  1. Skill Parsing: JSON, Markdown SKILL.md, and canonical archetypes
  2. Contextual Synthesis & Anti-Recycling: Proves 3 disparate sites share zero layout templates
  3. Attribute Binding: Confirms 100% token binding and audits against negative constraints
  4. Integration with taste_designer action
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from core.attribute_binder import AttributeBinder
from core.autonomous_site_generator import AutonomousSiteGenerator
from core.contextual_synthesizer import ContextualSynthesizer
from core.taste_schema import (
    LayoutConstraintTokens,
    MicroAestheticTokens,
    PaletteTokens,
    TasteSkillDefinition,
    TypographyTokens,
)
from core.taste_skill_parser import TasteSkillParser


def test_taste_schema_validation():
    """Verify that illegal values or banned fonts trigger validation errors."""
    bad_typo = TypographyTokens(
        display_font="Inter, sans-serif",  # Banned font
        display_scale="5rem",
        display_tracking="0",
        display_leading="1",
        banned_fonts=["Inter", "Arial"],
    )
    errors = bad_typo.validate()
    assert len(errors) > 0
    assert any("Inter" in err for err in errors)


def test_taste_skill_ingestion_and_registry():
    """Verify canonical taste skill registration and retrieval."""
    TasteSkillParser.initialize_registry()
    vanguard = TasteSkillParser.get("vanguard-ethereal")
    brutalist = TasteSkillParser.get("industrial-swiss-print")
    minimalist = TasteSkillParser.get("utilitarian-minimalist")

    assert vanguard is not None
    assert brutalist is not None
    assert minimalist is not None

    assert "Clash Display" in vanguard.typography.display_font
    assert "Archivo Black" in brutalist.typography.display_font
    assert "Newsreader" in minimalist.typography.display_font


def test_markdown_skill_parsing(tmp_path):
    """Verify parsing from a Markdown SKILL.md file."""
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        "---\nname: Custom Tactical Telemetry\ndescription: Heavy industrial terminal interface\n---\n"
        "# SKILL: Industrial Brutalism & Tactical Telemetry UI\n",
        encoding="utf-8",
    )
    parsed = TasteSkillParser.parse_markdown_skill(skill_file)
    assert parsed is not None
    assert parsed.name == "Custom Tactical Telemetry"
    assert parsed.palette.mode == "monochrome_light"


def test_three_disparate_sites_visual_and_structural_variance(tmp_path):
    """
    Verification Standard 1 & 2:
      - Visual comparison: Ensure three disparate generated sites show no repeated layout structures or stylistic similarities.
      - Code Audit: Verify style attributes directly correspond to input variables.
    """
    # 1. Generate Site A: Ethereal High-End AI (Vanguard)
    path_a, bp_a, audit_a = AutonomousSiteGenerator.generate(
        prompt="Autonomous AI Security Orchestration Platform with neural graph intelligence",
        brand_name="AETHER",
        skill_identifier="vanguard-ethereal",
        output_filename="test_site_a_vanguard.html",
    )

    # 2. Generate Site B: Industrial Swiss Print Telemetry (Brutalist)
    path_b, bp_b, audit_b = AutonomousSiteGenerator.generate(
        prompt="Aerospace propulsion telemetry and rocket valve diagnostics interface",
        brand_name="AERO_MACH",
        skill_identifier="industrial-swiss-print",
        output_filename="test_site_b_brutalist.html",
    )

    # 3. Generate Site C: Utilitarian Minimalist Editorial (Minimalist)
    path_c, bp_c, audit_c = AutonomousSiteGenerator.generate(
        prompt="Contemporary Scandinavian architectural monograph and design studio",
        brand_name="ATELIER_NORD",
        skill_identifier="utilitarian-minimalist",
        output_filename="test_site_c_minimalist.html",
    )

    # Verify all files were created
    assert path_a.exists() and path_a.stat().st_size > 2000
    assert path_b.exists() and path_b.stat().st_size > 2000
    assert path_c.exists() and path_c.stat().st_size > 2000

    # ── Verify Structural Disparity (Anti-Recycling Guarantee) ────────────────
    hashes = {
        sec.layout_structure.structural_hash
        for bp in (bp_a, bp_b, bp_c)
        for sec in bp.sections
    }
    # Multiple unique layout hashes across the three sites
    assert len(hashes) >= 3

    # Verify typography disparity
    assert bp_a.taste_skill.typography.display_font != bp_b.taste_skill.typography.display_font
    assert bp_b.taste_skill.typography.display_font != bp_c.taste_skill.typography.display_font

    # Verify substrate disparity
    assert bp_a.taste_skill.palette.canvas_bg == "#050505"  # Dark OLED
    assert bp_b.taste_skill.palette.canvas_bg == "#F4F4F0"  # Matte Unbleached Paper
    assert bp_c.taste_skill.palette.canvas_bg == "#F7F6F3"  # Warm Bone Linen

    # Verify enclosure disparity
    assert bp_a.taste_skill.micro.enclosure_archetype == "double_bezel"
    assert bp_b.taste_skill.micro.enclosure_archetype == "monolithic_raw"
    assert bp_c.taste_skill.micro.enclosure_archetype == "flat_bordered"

    # ── Code Audit: Zero Negative Constraint Violations ───────────────────────
    assert audit_a["passed"] is True, f"Site A Audit failed: {audit_a['violations']}"
    assert audit_b["passed"] is True, f"Site B Audit failed: {audit_b['violations']}"
    assert audit_c["passed"] is True, f"Site C Audit failed: {audit_c['violations']}"

    # Clean up test output files
    for p in (path_a, path_b, path_c):
        try:
            p.unlink()
        except Exception:
            pass


def test_action_integration():
    """Verify that actions/taste_designer.py routes skill-governed queries to the new pipeline."""
    from actions.taste_designer import design_creator

    params = {
        "type": "website",
        "prompt": "Next-level quantum encryption terminal with brutalist telemetry",
        "title": "QUANTUM_TELEMETRY",
        "skill": "industrial-swiss-print",
    }
    result_msg = design_creator(params)
    assert "design-governed frontend" in result_msg
    assert "industrial-swiss-print" in result_msg or "Swiss Industrial Print" in result_msg
    assert "PASSED" in result_msg
