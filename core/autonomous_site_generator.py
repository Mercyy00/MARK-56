"""
core/autonomous_site_generator.py — Autonomous Design-Governed Generation Pipeline.

Coordinates the end-to-end frontend generation lifecycle:
  1. Skill Ingestion & Parsing (TasteSkillParser)
  2. Contextual Synthesis & Argument Generation (ContextualSynthesizer)
  3. Anti-Recycling Layout Entropy Enforcement (AntiRecycleEngine)
  4. Attribute Binding & Semantic DOM Compilation (AttributeBinder)
  5. Automated Verification & Code Auditing
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from core.attribute_binder import AttributeBinder
from core.contextual_synthesizer import ContextualSynthesizer, SiteBlueprint
from core.taste_schema import TasteSkillDefinition
from core.taste_skill_parser import TasteSkillParser

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs" / "websites"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class AutonomousSiteGenerator:
    """Primary pipeline interface for autonomous design-governed website generation."""

    @classmethod
    def generate(
        cls,
        prompt: str,
        brand_name: str,
        skill_identifier: Union[str, Path, TasteSkillDefinition] = "vanguard-ethereal",
        output_filename: Optional[str] = None,
        custom_seed: Optional[str] = None,
    ) -> Tuple[Path, SiteBlueprint, Dict[str, Any]]:
        """
        Executes the design-governed generation pipeline:
          • Ingests and validates the specified taste skill
          • Synthesizes bespoke, non-recycled component topology
          • Compiles markup with 100% token binding
          • Audits generated code against negative constraints
          • Writes production-ready code to outputs/websites/<filename>.html

        Returns:
          (saved_file_path, compiled_blueprint, audit_report)
        """
        # 1. Resolve Taste Skill Definition
        if isinstance(skill_identifier, TasteSkillDefinition):
            skill = skill_identifier
        elif isinstance(skill_identifier, Path) or (isinstance(skill_identifier, str) and Path(skill_identifier).is_file()):
            p = Path(skill_identifier)
            if p.suffix.lower() == ".json":
                skill = TasteSkillParser.parse_json(p)
            else:
                skill = TasteSkillParser.parse_markdown_skill(p)
        else:
            skill = TasteSkillParser.get(str(skill_identifier))
            if not skill:
                TasteSkillParser.initialize_registry()
                skill = TasteSkillParser.get(str(skill_identifier))
            if not skill:
                # Default to vanguard
                skill = TasteSkillParser.get("vanguard-ethereal")

        # 2. Contextual Synthesis & Anti-Recycling Blueprint Generation
        blueprint = ContextualSynthesizer.synthesize(
            user_prompt=prompt,
            brand_name=brand_name,
            taste_skill=skill,
            custom_seed=custom_seed,
        )

        # 3. Compile DOM & Enforce 100% Attribute Binding
        html_code = AttributeBinder.compile_site(blueprint)

        # 4. Automated Code & Negative Constraint Audit
        audit = AttributeBinder.audit_generated_code(html_code, skill)

        # 5. Persist to Output Directory
        clean_name = "".join(c if c.isalnum() else "_" for c in brand_name).lower().strip("_")
        fname = output_filename or f"{clean_name}_{skill.id}.html"
        target_path = OUTPUT_DIR / fname
        target_path.write_text(html_code, encoding="utf-8")

        return target_path, blueprint, audit
