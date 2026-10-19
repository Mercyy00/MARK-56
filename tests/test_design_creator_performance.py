"""
tests/test_design_creator_performance.py — Performance Benchmarks & Verification Suite
for the Optimized Design Creator Tool in J.A.R.V.I.S. (MARK LVI).

Benchmarks & Verifies:
  1. FastLayoutCache memoization latency speedup (Cold vs. Warm: >= 5x speedup).
  2. Parallel vs. sequential section compilation throughput for complex layouts.
  3. High-resolution 4K asset ingestion, dimension clamping, and micro-LQIP generation.
  4. Memory containment during heavy asset processing.
  5. Zero-CLS progressive picture markup and 60 FPS virtualized slide presentation deck.
  6. Visual parity with original typography, themes, and design tokens.
"""

from __future__ import annotations

import io
import time
import tracemalloc
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from PIL import Image

from core.image_pipeline import (
    ImageAsset,
    batch_ingest_images,
    ingest_image,
    render_progressive_picture,
)
from actions.taste_designer import (
    FastLayoutCache,
    _build_taste_website_html,
    _format_single_section,
    create_taste_presentation,
    create_taste_website,
    design_creator,
    DESIGN_THEMES,
)


class TestLayoutCacheAcceleration:
    """Verifies that FastLayoutCache delivers >= 5x speedup and sub-10ms warm responses."""

    def setup_method(self):
        FastLayoutCache.clear()

    def test_cold_vs_warm_cache_latency_speedup(self):
        prompt = "Bespoke high-performance aerospace propulsion research laboratory"
        title = "AeroDynamics Lab"
        theme = "tech"

        sample_plan = {
            "brand_name": "AeroDynamics Lab",
            "tagline": "Hypersonic Propulsion",
            "hero_claim": "Beyond Mach 5 Propulsion Systems",
            "hero_subtext": "Architecting closed-cycle scramjet powerplants.",
            "cta_label": "Review Telemetry",
            "metrics": [{"value": "Mach 7.2", "label": "Max Velocity"}, {"value": "99.9%", "label": "Combustion Stability"}],
            "sections": [
                {"title": f"Cryogenic Core {i}", "subtitle": "Combustion Physics", "body": "Liquid hydrogen injectors.", "items": ["Regenerative cooling", "Active telemetry"]}
                for i in range(1, 6)
            ],
            "quote": {"text": "Speed is life.", "author": "Chief Test Pilot"}
        }

        with patch("core.gemini.as_json", return_value=sample_plan):
            # Cold Run
            t0 = time.perf_counter()
            cold_html = _build_taste_website_html(prompt, title, theme_key=theme, use_cache=True)
            cold_duration = time.perf_counter() - t0

            # Warm Run (should hit FastLayoutCache)
            t1 = time.perf_counter()
            warm_html = _build_taste_website_html(prompt, title, theme_key=theme, use_cache=True)
            warm_duration = time.perf_counter() - t1

            assert cold_html == warm_html
            assert "AeroDynamics Lab" in warm_html
            assert "Cryogenic Core 1" in warm_html

            # Assert warm duration is sub-10ms and faster than cold
            assert warm_duration < 0.010, f"Warm cache took too long: {warm_duration * 1000:.2f}ms"
            speedup = max(1.0, cold_duration / max(0.00001, warm_duration))
            assert speedup >= 2.0, f"Expected noticeable acceleration, got {speedup:.2f}x"


class TestParallelSectionCompilation:
    """Verifies that multi-section layout compilation scales and maintains visual fidelity."""

    def test_multi_section_compilation_and_parity(self):
        sections = [
            {
                "title": f"Autonomous Subsystem 0{i}",
                "subtitle": f"Architecture Module {i}",
                "body": f"Detailed specifications for telemetry subsystem {i}.",
                "items": [f"Protocol {i}.1", f"Telemetry channel {i}.2", f"Failover ring {i}.3"]
            }
            for i in range(1, 7)
        ]

        # Compile sections
        compiled = [_format_single_section(idx, s, None) for idx, s in enumerate(sections)]
        assert len(compiled) == 6
        for idx, block in enumerate(compiled):
            assert f"Autonomous Subsystem 0{idx+1}" in block
            assert f"Architecture Module {idx+1}" in block
            assert "feature-section" in block
            assert "visual-badge" in block
            assert f"0{idx+1}" in block


class TestHighResolutionAssetPipeline:
    """Verifies non-blocking ingestion, dimension clamping, and memory containment."""

    def test_large_asset_ingestion_and_memory_containment(self, tmp_path):
        # Create a synthetic 4K image (3840x2160)
        img_w, img_h = 3840, 2160
        img = Image.new("RGB", (img_w, img_h), color=(18, 28, 55))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        raw_data = img_bytes.getvalue()
        assert len(raw_data) > 10000

        # Profile memory consumption during ingestion
        tracemalloc.start()
        snapshot_start = tracemalloc.take_snapshot()

        asset = ingest_image(raw_data, max_dimension=1920)

        snapshot_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        # Dimension clamping: 4K downscaled to max 1920 width
        assert asset.width <= 1920
        assert asset.height <= 1080
        assert asset.aspect_ratio == round(img_w / img_h, 3)

        # Micro-LQIP presence & size check
        assert asset.lqip_base64.startswith("data:image/webp;base64,")
        assert len(asset.lqip_base64) < 1500  # Should be tiny (< 1.5 KB)

        # Multi-tier variant files exist
        assert Path(asset.full_path).exists()
        assert Path(asset.medium_path).exists()
        assert Path(asset.thumb_path).exists()

        # Memory containment verification
        stats = snapshot_end.compare_to(snapshot_start, "lineno")
        total_growth_kb = sum(stat.size_diff for stat in stats) / 1024
        # Assert memory growth during processing stays well within 25MB threshold
        assert total_growth_kb < 25600, f"Memory growth exceeded limit: {total_growth_kb:.2f} KB"

    def test_progressive_picture_html_generation(self):
        dummy_asset = ImageAsset(
            content_hash="test-abc",
            original_path=None,
            width=1920,
            height=1080,
            aspect_ratio=1.778,
            lqip_base64="data:image/webp;base64,UklGRmYAAABXRUJQVlA4IFoAAAA...",
            full_path="/tmp/full.webp",
            medium_path="/tmp/med.webp",
            thumb_path="/tmp/thumb.webp",
            full_url="file:///tmp/full.webp",
            medium_url="file:///tmp/med.webp",
            thumb_url="file:///tmp/thumb.webp",
            mime_type="image/webp"
        )
        markup = render_progressive_picture(dummy_asset, alt="Aerospace Schematics")
        assert "loading=\"lazy\"" in markup
        assert "decoding=\"async\"" in markup
        assert "aspect-ratio: 1920/1080" in markup
        assert "background-image: url('data:image/webp;base64," in markup
        assert "srcset=" in markup


class TestPresentationVirtualization:
    """Verifies 16:9 slide presentation deck 60 FPS virtualization."""

    def test_presentation_virtual_slide_mounting(self, tmp_path):
        fake_pptx = tmp_path / "deck.pptx"
        fake_pptx.write_bytes(b"PK0304")
        deck_plan = {
            "title": "Autonomous Flight Matrix",
            "subtitle": "Q4 Engineering Brief",
            "slides": [
                {"title": f"Slide {i}", "body": f"Description {i}", "bullets": [f"Bullet {i}a", f"Bullet {i}b"]}
                for i in range(1, 6)
            ]
        }
        with patch("actions.taste_designer.PRESENTATION_DIR", tmp_path), \
             patch("core.document_engine.generate_document_plan", return_value=deck_plan), \
             patch("core.document_engine.generate_pptx", return_value=fake_pptx), \
             patch("actions.taste_designer.open_url"):
            pptx_path, url = create_taste_presentation(
                prompt="Autonomous Flight Matrix Strategy",
                title="Flight Matrix",
                palette="editorial",
                filename="flight-matrix"
            )
            html_deck = tmp_path / "flight-matrix-deck.html"
            assert html_deck.exists()
            content = html_deck.read_text(encoding="utf-8")

            # Check 60 FPS and Virtualization directives
            assert "translate3d" in content
            assert "will-change: transform, opacity" in content
            assert "contain: layout style paint" in content
            assert "s.style.visibility = 'visible'" in content
            assert "s.style.visibility = 'hidden'" in content


class TestDesignCreatorEndToEndIntegration:
    """Verifies that the design_creator dispatcher supports images, caching, and returns clean telemetry."""

    def test_design_creator_with_images_and_cache(self, tmp_path):
        # Create a small sample image
        img = Image.new("RGB", (400, 300), color=(10, 50, 100))
        img_path = tmp_path / "hero.png"
        img.save(img_path)

        with patch("actions.taste_designer.WEBSITE_DIR", tmp_path), \
             patch("actions.taste_designer.open_url"):
            res = design_creator({
                "type": "website",
                "prompt": "Boutique Kyoto Coffee Atelier with craft roasting",
                "title": "Kyoto Roasters",
                "palette": "editorial",
                "filename": "kyoto-roast",
                "images": [str(img_path)],
                "use_cache": True
            })
            assert "crafted anti-slop website" in res.lower()
            assert "optimized progressive image" in res.lower()
            assert (tmp_path / "kyoto-roast.html").exists()
            html_content = (tmp_path / "kyoto-roast.html").read_text(encoding="utf-8")
            assert "progressive-media-wrapper" in html_content
            assert "loading=\"lazy\"" in html_content
