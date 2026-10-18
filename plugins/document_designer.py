"""
plugins/document_designer.py — Ultimate Document & Presentation Design Skill for JARVIS

Generates high-quality, stylistically beautiful PDF and DOCX documents and
PPTX presentations. Handles AI content creation, professional styling, palettes,
structured tables, and bidirectional file conversion (PDF <-> DOCX, PPTX -> PDF).
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from core import document_engine

PLUGIN = {
    "name": "document_designer",
    "description": (
        "Generate high-quality, stylistically beautiful PDF and DOCX documents and "
        "presentations (PPTX), or convert existing PDF files to DOCX and DOCX/PPTX to PDF. "
        "Handles content creation from user prompts, formatting with curated palettes "
        "(navy, editorial, emerald, slate, tech), and delivers professional, polished outputs."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "The action to execute: "
                    "'create_pdf' (generate styled PDF from prompt), "
                    "'create_docx' (generate styled Word document from prompt), "
                    "'create_presentation' (generate 16:9 styled PPTX slides from prompt), "
                    "'convert_pdf_to_docx' (convert existing PDF file to DOCX), "
                    "'convert_docx_to_pdf' (convert existing DOCX file to PDF), "
                    "'convert_pptx_to_pdf' (convert existing PPTX presentation to PDF)"
                )
            },
            "prompt": {
                "type": "STRING",
                "description": "Topic, outline, or content requirements for creating the document or presentation."
            },
            "file_path": {
                "type": "STRING",
                "description": "Path to input file for conversion or existing text file to reformat."
            },
            "output_path": {
                "type": "STRING",
                "description": "Optional destination file path. If omitted, saves to Desktop with an automatic name."
            },
            "palette": {
                "type": "STRING",
                "description": "Visual theme palette: 'navy' (default), 'editorial', 'emerald', 'slate', 'tech'."
            },
            "title": {
                "type": "STRING",
                "description": "Optional custom title for the document or presentation."
            }
        },
        "required": ["action"]
    }
}


def _default_output_path(stem: str, ext: str) -> Path:
    desktop = Path.home() / "Desktop"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_stem = stem.replace(" ", "_")[:30] if stem else "jarvis_doc"
    return desktop / f"{clean_stem}_{ts}{ext}"


def run(parameters: dict, player=None, session_memory=None) -> str:
    """
    Executes document generation or conversion based on user parameters.
    """
    action = (parameters.get("action") or "").strip().lower()
    prompt = parameters.get("prompt") or ""
    file_path = parameters.get("file_path") or ""
    output_path = parameters.get("output_path") or ""
    palette = (parameters.get("palette") or "navy").lower()
    title = parameters.get("title") or ""

    try:
        # ─────────────────────────────────────────────────────────────────
        #  1. Document / Presentation Generation
        # ─────────────────────────────────────────────────────────────────
        if action in ("create_pdf", "generate_pdf", "pdf"):
            if not prompt and not file_path:
                return "Sir, please provide a prompt or topic for the PDF document."

            doc_topic = prompt or f"Document based on {file_path}"
            plan = document_engine.generate_document_plan(doc_topic, doc_type="pdf")
            if title:
                plan["title"] = title

            target_out = Path(output_path) if output_path else _default_output_path(plan.get("title", "document"), ".pdf")
            result_file = document_engine.generate_pdf(plan, target_out, palette_key=palette)
            msg = f"Sir, I have crafted your PDF document '{result_file.name}' with the {palette.title()} theme. Saved to your Desktop."
            _notify(player, msg)
            return msg

        elif action in ("create_docx", "generate_docx", "docx", "create_word"):
            if not prompt and not file_path:
                return "Sir, please provide a prompt or topic for the Word document."

            doc_topic = prompt or f"Document based on {file_path}"
            plan = document_engine.generate_document_plan(doc_topic, doc_type="docx")
            if title:
                plan["title"] = title

            target_out = Path(output_path) if output_path else _default_output_path(plan.get("title", "document"), ".docx")
            result_file = document_engine.generate_docx(plan, target_out, palette_key=palette)
            msg = f"Sir, I have generated your Word document '{result_file.name}' with professional typography and styled tables. Saved to your Desktop."
            _notify(player, msg)
            return msg

        elif action in ("create_presentation", "generate_presentation", "pptx", "create_slides", "slides"):
            if not prompt and not file_path:
                return "Sir, please provide a topic or outline for the presentation."

            deck_topic = prompt or f"Presentation based on {file_path}"
            plan = document_engine.generate_document_plan(deck_topic, doc_type="pptx")
            if title:
                plan["title"] = title

            target_out = Path(output_path) if output_path else _default_output_path(plan.get("title", "presentation"), ".pptx")
            result_file = document_engine.generate_pptx(plan, target_out, palette_key=palette)
            msg = f"Sir, I have designed your 16:9 widescreen presentation '{result_file.name}' with styled executive cards and metrics. Saved to your Desktop."
            _notify(player, msg)
            return msg

        # ─────────────────────────────────────────────────────────────────
        #  2. Bidirectional Conversions
        # ─────────────────────────────────────────────────────────────────
        elif action in ("convert_pdf_to_docx", "pdf_to_word", "pdf_to_docx"):
            if not file_path:
                return "Sir, please specify the path to the PDF file you wish to convert."
            src = Path(file_path)
            if not src.exists():
                return f"Sir, I could not find the file at '{file_path}'."

            target_out = Path(output_path) if output_path else _default_output_path(src.stem, ".docx")
            res = document_engine.convert_pdf_to_docx(src, target_out)
            _notify(player, f"JARVIS: {res}")
            return f"Sir, the PDF has been converted to an editable Word document: {target_out.name}."

        elif action in ("convert_docx_to_pdf", "word_to_pdf", "docx_to_pdf"):
            if not file_path:
                return "Sir, please specify the path to the Word document you wish to convert."
            src = Path(file_path)
            if not src.exists():
                return f"Sir, I could not find the file at '{file_path}'."

            target_out = Path(output_path) if output_path else _default_output_path(src.stem, ".pdf")
            res = document_engine.convert_docx_to_pdf(src, target_out)
            _notify(player, f"JARVIS: {res}")
            return f"Sir, the Word document has been converted to a high-fidelity PDF: {target_out.name}."

        elif action in ("convert_pptx_to_pdf", "slides_to_pdf", "presentation_to_pdf"):
            if not file_path:
                return "Sir, please specify the path to the presentation you wish to convert."
            src = Path(file_path)
            if not src.exists():
                return f"Sir, I could not find the file at '{file_path}'."

            target_out = Path(output_path) if output_path else _default_output_path(src.stem, ".pdf")
            res = document_engine.convert_pptx_to_pdf(src, target_out)
            _notify(player, f"JARVIS: {res}")
            return f"Sir, the presentation has been exported to PDF: {target_out.name}."

        else:
            return (
                f"Unknown action '{action}'. Available actions: "
                f"'create_pdf', 'create_docx', 'create_presentation', "
                f"'convert_pdf_to_docx', 'convert_docx_to_pdf', 'convert_pptx_to_pdf'."
            )

    except Exception as e:
        err = f"Sir, document_designer encountered an issue: {e}"
        _notify(player, err)
        return err


def _notify(player, text: str) -> None:
    if player:
        try:
            player.write_log(f"JARVIS: {text}")
        except Exception:
            pass
