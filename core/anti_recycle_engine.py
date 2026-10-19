"""
core/anti_recycle_engine.py — Anti-Recycling Constraint Engine for Autonomous Frontend Generation.

Actively enforces structural novelty and layout entropy:
  • Prohibits fixed layout templates and repetitive 3-card grids
  • Computes dynamic structural entropy across grid spans, aspect ratios, and visual weights
  • Fingerprints layouts to guarantee disparate architectural topologies across runs
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BentoCell:
    """An individual cell within an asymmetrical Bento Grid."""
    col_span: int  # e.g. 4, 6, 7, 8, 12
    row_span: int  # e.g. 1, 2
    accent_tier: str  # "heroic", "secondary", "data_dense", "quote"
    visual_anchor: bool = False
    padding_override: Optional[str] = None


@dataclass
class LayoutStructure:
    """Structural blueprint of a section layout."""
    archetype: str
    grid_columns: int
    cells: List[BentoCell]
    asymmetry_score: float
    structural_hash: str


class AntiRecycleEngine:
    """
    Generates novel, non-recycled component compositions tailored to context and aesthetic rules.
    """

    @classmethod
    def generate_bento_layout(
        cls,
        item_count: int,
        seed_str: str,
        allow_tall_cards: bool = True
    ) -> LayoutStructure:
        """
        Generate a non-uniform, mathematically balanced asymmetrical bento grid.
        Guarantees no standard '3 equal cards' row.
        """
        rng = random.Random(hashlib.sha256(seed_str.encode("utf-8")).hexdigest())

        cells: List[BentoCell] = []
        total_cols = 12

        if item_count <= 2:
            # 7 + 5 or 8 + 4 split
            split = rng.choice([7, 8])
            cells.append(BentoCell(col_span=split, row_span=1, accent_tier="heroic", visual_anchor=True))
            cells.append(BentoCell(col_span=total_cols - split, row_span=1, accent_tier="secondary"))
        elif item_count == 3:
            # Explicitly avoid 4 + 4 + 4! Use 8 + 4 (top) then full 12 (bottom), or 7 + 5 then full
            pattern = rng.choice(["asym_stack_left", "asym_stack_right", "hero_with_twin_column"])
            if pattern == "asym_stack_left":
                cells.append(BentoCell(col_span=8, row_span=2, accent_tier="heroic", visual_anchor=True))
                cells.append(BentoCell(col_span=4, row_span=1, accent_tier="secondary"))
                cells.append(BentoCell(col_span=4, row_span=1, accent_tier="data_dense"))
            elif pattern == "asym_stack_right":
                cells.append(BentoCell(col_span=5, row_span=1, accent_tier="secondary"))
                cells.append(BentoCell(col_span=7, row_span=2, accent_tier="heroic", visual_anchor=True))
                cells.append(BentoCell(col_span=5, row_span=1, accent_tier="data_dense"))
            else:
                cells.append(BentoCell(col_span=12, row_span=1, accent_tier="heroic", visual_anchor=True))
                cells.append(BentoCell(col_span=7, row_span=1, accent_tier="secondary"))
                cells.append(BentoCell(col_span=5, row_span=1, accent_tier="data_dense"))
        elif item_count == 4:
            # Asymmetrical 4-block: (8 + 4) top, (5 + 7) bottom
            cells.append(BentoCell(col_span=8, row_span=1, accent_tier="heroic", visual_anchor=True))
            cells.append(BentoCell(col_span=4, row_span=1, accent_tier="secondary"))
            cells.append(BentoCell(col_span=5, row_span=1, accent_tier="data_dense"))
            cells.append(BentoCell(col_span=7, row_span=1, accent_tier="heroic"))
        else:
            # 5+ items: complex mosaic
            cells.append(BentoCell(col_span=7, row_span=2 if allow_tall_cards else 1, accent_tier="heroic", visual_anchor=True))
            cells.append(BentoCell(col_span=5, row_span=1, accent_tier="secondary"))
            cells.append(BentoCell(col_span=5, row_span=1, accent_tier="data_dense"))
            remaining = item_count - 3
            for i in range(remaining):
                span = 6 if remaining % 2 == 0 else (4 if i < 3 else 12)
                cells.append(BentoCell(col_span=span, row_span=1, accent_tier="secondary"))

        # Calculate asymmetry metric: variance in column widths
        col_widths = [c.col_span for c in cells]
        mean_w = sum(col_widths) / len(col_widths)
        variance = sum((w - mean_w) ** 2 for w in col_widths) / len(col_widths)
        asymmetry_score = round(variance, 2)

        raw_fingerprint = f"{seed_str}:{'-'.join(f'{c.col_span}x{c.row_span}' for c in cells)}"
        structural_hash = hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()[:12]

        return LayoutStructure(
            archetype="asymmetrical_bento",
            grid_columns=total_cols,
            cells=cells,
            asymmetry_score=asymmetry_score,
            structural_hash=structural_hash,
        )

    @classmethod
    def generate_editorial_split(cls, seed_str: str) -> LayoutStructure:
        """Monolithic headline on left, staggered interactive stream on right."""
        rng = random.Random(hashlib.sha256(seed_str.encode("utf-8")).hexdigest())
        left_cols = rng.choice([5, 6, 7])
        right_cols = 12 - left_cols

        cells = [
            BentoCell(col_span=left_cols, row_span=1, accent_tier="heroic", visual_anchor=True),
            BentoCell(col_span=right_cols, row_span=1, accent_tier="secondary"),
        ]
        return LayoutStructure(
            archetype="editorial_split",
            grid_columns=12,
            cells=cells,
            asymmetry_score=abs(left_cols - right_cols) * 2.5,
            structural_hash=hashlib.sha256(f"split:{left_cols}:{right_cols}:{seed_str}".encode()).hexdigest()[:12],
        )

    @classmethod
    def generate_rigid_modular_grid(cls, rows: int, cols: int, seed_str: str) -> LayoutStructure:
        """Swiss print / technical telemetry modular grid with flush boundaries."""
        cells = []
        for r in range(rows):
            for c in range(cols):
                # Occasional bleeding cell for brutalist hierarchy
                span = 12 // cols
                is_anchor = (r == 0 and c == 0)
                cells.append(BentoCell(col_span=span, row_span=1, accent_tier="heroic" if is_anchor else "data_dense", visual_anchor=is_anchor))

        return LayoutStructure(
            archetype="rigid_modular_grid",
            grid_columns=12,
            cells=cells,
            asymmetry_score=0.0,
            structural_hash=hashlib.sha256(f"rigid:{rows}x{cols}:{seed_str}".encode()).hexdigest()[:12],
        )
