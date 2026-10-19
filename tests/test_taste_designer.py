"""
tests/test_taste_designer.py — Automated Unit Tests for actions/taste_designer.py.
Verifies the Anti-Slop Design & Craft Engine across:
  1. Website generation (HTML5/CSS3 with distinctive typography & curated theme).
  2. DOCX report generation.
  3. Presentation deck generation (PPTX & interactive HTML deck).
  4. MARK LVI action registration & error handling.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from actions.taste_designer import (
    TOOL,
    create_taste_docx,
    create_taste_presentation,
    create_taste_website,
    design_creator,
    _build_taste_website_html,
    DESIGN_THEMES,
)


class TestTasteDesignerActionSchema:
    """Verifies that the TOOL declaration conforms to Gemini Function Calling schema."""

    def test_tool_declaration_structure(self):
        assert TOOL["name"] == "design_creator"
        assert callable(TOOL["handler"])
        params = TOOL["parameters"]
        assert params["type"] == "OBJECT"
        assert "type" in params["properties"]
        assert "prompt" in params["properties"]
        assert "palette" in params["properties"]
        assert set(params["required"]) == {"type", "prompt"}


class TestWebsiteGeneration:
    """Verifies art-directed, anti-slop website output."""

    def test_html_contains_typography_and_theme_variables(self):
        sample_plan = {
            "brand_name": "Kyoto Roasters",
            "tagline": "Artisanal Craft",
            "hero_claim": "Pure Coffee Architecture",
            "hero_subtext": "Sustainably sourced.",
            "cta_label": "Order Now",
            "metrics": [{"value": "100%", "label": "Direct Trade"}],
            "sections": [{"title": "Roasting Process", "subtitle": "Craft", "body": "Slow roast.", "items": ["Item 1"]}],
            "quote": {"text": "Coffee is craft.", "author": "Master Roaster"}
        }
        with patch("core.gemini.as_json", return_value=sample_plan):
            html_code = _build_taste_website_html(
                prompt="Boutique Kyoto Coffee Roastery with artisanal beans",
                title="Kyoto Roasters",
                theme_key="editorial"
            )
            assert "<!DOCTYPE html>" in html_code
            assert "Kyoto Roasters" in html_code
            assert "Instrument Serif" in html_code or "Playfair Display" in html_code
            assert "--primary: #d94326" in html_code
            assert "hero-title" in html_code
            assert "feature-section" in html_code

    def test_create_taste_website_creates_file_and_launches_browser(self, tmp_path):
        sample_plan = {
            "brand_name": "Quantum Dynamics",
            "tagline": "Computing Lab",
            "hero_claim": "Next Generation Quantum",
            "hero_subtext": "Lab research.",
            "cta_label": "Discover",
            "metrics": [{"value": "100%", "label": "Fidelity"}],
            "sections": [{"title": "Quantum Gates", "subtitle": "Physics", "body": "Superconducting.", "items": ["Gate 1"]}],
            "quote": {"text": "Qubits in coherence.", "author": "Lead Scientist"}
        }
        with patch("actions.taste_designer.WEBSITE_DIR", tmp_path), \
             patch("core.gemini.as_json", return_value=sample_plan), \
             patch("actions.taste_designer.open_url", return_value="Opened in chrome") as mock_open:
            path, url = create_taste_website(
                prompt="Quantum computing research lab portfolio",
                title="Quantum Dynamics",
                palette="tech",
                filename="quantum-lab"
            )
            assert path.exists()
            assert path.name == "quantum-lab.html"
            content = path.read_text(encoding="utf-8")
            assert "Quantum Dynamics" in content
            assert "Space Grotesk" in content
            mock_open.assert_called_once()


class TestDocxGeneration:
    """Verifies styled Word document generation with document_engine."""

    def test_create_taste_docx_invokes_engine(self, tmp_path):
        fake_doc_path = tmp_path / "test-doc.docx"
        fake_doc_path.write_bytes(b"PK0304")
        with patch("actions.taste_designer.DOCUMENT_DIR", tmp_path), \
             patch("core.document_engine.generate_document_plan", return_value={"title": "Test Brief"}), \
             patch("core.document_engine.generate_docx", return_value=fake_doc_path) as mock_gen, \
             patch("os.startfile"):
            path, full_path = create_taste_docx(
                prompt="Annual cybersecurity resilience assessment",
                title="Security Report",
                palette="navy",
                filename="sec-report"
            )
            assert path == fake_doc_path
            mock_gen.assert_called_once()


class TestPresentationGeneration:
    """Verifies 16:9 slide deck and interactive HTML presentation generation."""

    def test_create_taste_presentation_dual_format(self, tmp_path):
        fake_pptx = tmp_path / "deck.pptx"
        fake_pptx.write_bytes(b"PK0304")
        deck_plan = {
            "title": "Autonomous AI Strategy",
            "subtitle": "Q4 Roadmap",
            "slides": [
                {"title": "Executive Vision", "body": "Key objectives", "bullets": ["Metric A", "Metric B"]}
            ]
        }
        with patch("actions.taste_designer.PRESENTATION_DIR", tmp_path), \
             patch("core.document_engine.generate_document_plan", return_value=deck_plan), \
             patch("core.document_engine.generate_pptx", return_value=fake_pptx), \
             patch("actions.taste_designer.open_url"):
            path, url = create_taste_presentation(
                prompt="Autonomous AI Strategy Presentation",
                title="AI Strategy",
                palette="tech",
                filename="ai-strategy"
            )
            html_deck = tmp_path / "ai-strategy-deck.html"
            assert html_deck.exists()
            content = html_deck.read_text(encoding="utf-8")
            assert "AI Strategy" in content
            assert "Executive Vision" in content
            assert "deck-container" in content


class TestDesignCreatorDispatcher:
    """Verifies action dispatching and error handling."""

    def test_missing_prompt_returns_failure(self):
        res = design_creator({"type": "website", "prompt": ""})
        assert "failed" in res.lower()
        assert "prompt or brief is required" in res.lower()

    def test_unknown_type_returns_failure(self):
        res = design_creator({"type": "unknown_asset_type_xyz", "prompt": "Test prompt"})
        assert "failed" in res.lower()
        assert "unknown design asset type" in res.lower()

    def test_dispatch_website_success(self, tmp_path):
        with patch("actions.taste_designer.create_taste_website", return_value=(tmp_path / "site.html", "file:///site.html")):
            res = design_creator({"type": "website", "prompt": "Coffee website"})
            assert "crafted anti-slop website" in res.lower()
            assert "google chrome" in res.lower()

    def test_dispatch_docx_success(self, tmp_path):
        with patch("actions.taste_designer.create_taste_docx", return_value=(tmp_path / "doc.docx", str(tmp_path / "doc.docx"))):
            res = design_creator({"type": "docx", "prompt": "Business Plan"})
            assert "generated styled word document" in res.lower()

    def test_dispatch_presentation_success(self, tmp_path):
        with patch("actions.taste_designer.create_taste_presentation", return_value=(tmp_path / "deck.pptx", "file:///deck.html")):
            res = design_creator({"type": "presentation", "prompt": "Product Launch"})
            assert "generated 16:9 presentation deck" in res.lower()

    def test_dispatch_multipage_success(self, tmp_path):
        with patch("actions.taste_designer.create_taste_multipage_website", return_value=(tmp_path / "movue" / "index.html", "file:///movue/index.html")):
            res = design_creator({"type": "multipage", "prompt": "Create modern streaming website movue"})
            assert "crafted modern anti-slop multipage streaming website" in res.lower()
            assert "google chrome" in res.lower()

    def test_create_taste_multipage_website_generates_all_pages(self, tmp_path):
        with patch("actions.taste_designer.WEBSITE_DIR", tmp_path), \
             patch("actions.taste_designer.open_url"):
            from actions.taste_designer import create_taste_multipage_website
            index_path, file_url = create_taste_multipage_website(
                prompt="Modern streaming website for testing",
                title="MOVUE",
                palette="tech",
                dirname="test-movue"
            )
            out_dir = tmp_path / "test-movue"
            assert out_dir.exists()
            assert (out_dir / "index.html").exists()
            assert (out_dir / "browse.html").exists()
            assert (out_dir / "watch.html").exists()
            assert (out_dir / "movie.html").exists()
            assert (out_dir / "plans.html").exists()
            assert (out_dir / "style.css").exists()
            assert (out_dir / "app.js").exists()

            index_content = (out_dir / "index.html").read_text(encoding="utf-8")
            assert "MOVUE" in index_content
            assert "NEUROMANCER" in index_content
            assert "watch.html" in index_content
            assert "browse.html" in index_content
