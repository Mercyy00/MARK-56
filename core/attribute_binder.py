"""
core/attribute_binder.py — Attribute Binding & DOM Compilation Engine.

Binds 100% of DOM attributes (classes, CSS custom variables, styles) directly
to the ingested TasteSkillDefinition, eliminating generic templates.
Includes automated verification and code auditing routines.
"""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional

from core.contextual_synthesizer import ContentCard, SectionBlueprint, SiteBlueprint, UIActionElement
from core.taste_schema import TasteSkillDefinition


class AttributeBinder:
    """Compiles a SiteBlueprint into production-ready HTML with 100% token binding."""

    @classmethod
    def compile_site(cls, blueprint: SiteBlueprint) -> str:
        skill = blueprint.taste_skill
        css_vars = skill.generate_css_variables()
        google_fonts_url = cls._resolve_google_fonts(skill)

        # Compile Nav
        nav_html = cls._compile_nav(blueprint)

        # Compile Sections
        sections_html = ""
        for sec in blueprint.sections:
            sections_html += cls._compile_section(sec, skill)

        # Compile Footer
        footer_html = cls._compile_footer(blueprint)

        # Compile Interactive Script
        script_js = cls._compile_script(skill)

        # Compile Document Styles
        custom_css = cls._compile_custom_css(skill)

        # Assemble Full Document
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(blueprint.site_title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  {google_fonts_url}
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
{css_vars}

{custom_css}
  </style>
</head>
<body class="site-body antialiased">
  {nav_html}

  <main class="site-main">
    {sections_html}
  </main>

  {footer_html}

  <script>
{script_js}
  </script>
</body>
</html>
"""

    @classmethod
    def _resolve_google_fonts(cls, skill: TasteSkillDefinition) -> str:
        """Inject appropriate font imports based on the active taste skill."""
        t = skill.typography
        fonts_to_load = []

        if "Clash Display" in t.display_font or "Plus Jakarta Sans" in t.body_font:
            fonts_to_load.append("family=Plus+Jakarta+Sans:wght@400;500;600;700;800")
            fonts_to_load.append("family=Instrument+Serif:ital@0;1")
        if "Archivo Black" in t.display_font or "Space Grotesk" in t.body_font:
            fonts_to_load.append("family=Archivo+Black")
            fonts_to_load.append("family=Space+Grotesk:wght@400;600;700")
            fonts_to_load.append("family=JetBrains+Mono:wght@400;500;700")
        if "Newsreader" in t.display_font or "Switzer" in t.body_font:
            fonts_to_load.append("family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400")
            fonts_to_load.append("family=Geist+Mono:wght@400;500")

        if not fonts_to_load:
            fonts_to_load.append("family=Plus+Jakarta+Sans:wght@400;600;700")

        query = "&".join(fonts_to_load)
        return f'<link href="https://fonts.googleapis.com/css2?{query}&display=swap" rel="stylesheet">'

    @classmethod
    def _compile_nav(cls, bp: SiteBlueprint) -> str:
        skill = bp.taste_skill
        m = skill.micro
        p = skill.palette

        links_html = "".join(
            f'<a href="{url}" class="nav-item-link">{html.escape(label)}</a>'
            for url, label in bp.nav_links
        )

        if m.button_archetype == "nested_island_pill":
            # Vanguard Floating Glass Island
            return f"""
  <header class="nav-island-wrapper">
    <nav class="nav-island">
      <a href="#hero" class="nav-brand">
        <span class="brand-dot"></span>
        <span class="brand-text">{html.escape(bp.brand_name)}</span>
      </a>
      <div class="nav-links-cluster hidden md:flex">
        {links_html}
      </div>
      <a href="#deploy" class="nav-cta-btn">
        <span>Get Started</span>
        <span class="btn-icon-capsule">↗</span>
      </a>
    </nav>
  </header>
"""
        elif m.button_archetype == "sharp_tactical_block":
            # Brutalist Tactical Top Bar
            return f"""
  <header class="tactical-header">
    <div class="tactical-header-inner">
      <div class="tactical-brand">
        <span class="tactical-tag">[SYS.01]</span>
        <span class="tactical-name">{html.escape(bp.brand_name.upper())}</span>
      </div>
      <nav class="tactical-nav hidden md:flex">
        {links_html}
      </nav>
      <div class="tactical-status">
        <span class="status-indicator"></span>
        <span>STATUS: LIVE</span>
      </div>
    </div>
  </header>
"""
        else:
            # Minimalist Clean Document Header
            return f"""
  <header class="minimal-header">
    <div class="minimal-header-inner">
      <a href="#hero" class="minimal-brand">{html.escape(bp.brand_name)}</a>
      <nav class="minimal-nav">
        {links_html}
      </nav>
      <a href="#deploy" class="minimal-cta">Deploy →</a>
    </div>
  </header>
"""

    @classmethod
    def _compile_section(cls, sec: SectionBlueprint, skill: TasteSkillDefinition) -> str:
        l = skill.layout
        p = skill.palette

        cards_html = ""
        for card in sec.cards:
            cards_html += cls._compile_card(card, skill)

        eyebrow_html = (
            f'<div class="section-eyebrow-badge">{html.escape(sec.eyebrow)}</div>'
            if sec.eyebrow
            else ""
        )

        subhead_html = (
            f'<p class="section-subheading">{html.escape(sec.subheading)}</p>'
            if sec.subheading
            else ""
        )

        actions_html = ""
        if sec.primary_action or sec.secondary_action:
            act_items = ""
            if sec.primary_action:
                act_items += cls._compile_action_button(sec.primary_action, skill)
            if sec.secondary_action:
                act_items += cls._compile_action_button(sec.secondary_action, skill)
            actions_html = f'<div class="section-actions-row">{act_items}</div>'

        return f"""
    <section id="{sec.id}" class="content-section {l.macro_padding_y}">
      <div class="{l.container_max_w} mx-auto {l.macro_padding_x}">
        <div class="section-header-block scroll-reveal">
          {eyebrow_html}
          <h2 class="section-headline">{html.escape(sec.headline)}</h2>
          {subhead_html}
          {actions_html}
        </div>

        <div class="bento-grid-container grid grid-cols-1 md:grid-cols-12 {l.section_gap} mt-12 md:mt-16">
          {cards_html}
        </div>
      </div>
    </section>
"""

    @classmethod
    def _compile_card(cls, card: ContentCard, skill: TasteSkillDefinition) -> str:
        m = skill.micro
        span_classes = f"md:col-span-{card.col_span} md:row-span-{card.row_span}"

        eyebrow_tag = (
            f'<span class="card-eyebrow">{html.escape(card.eyebrow)}</span>'
            if card.eyebrow
            else ""
        )

        metric_html = ""
        if card.metric_value:
            metric_html = f"""
          <div class="card-metric-block">
            <span class="metric-numeral">{html.escape(card.metric_value)}</span>
            <span class="metric-caption">{html.escape(card.metric_label or "")}</span>
          </div>
"""

        actions_html = ""
        if card.actions:
            act_items = "".join(cls._compile_action_button(act, skill) for act in card.actions)
            actions_html = f'<div class="card-actions-cluster mt-6">{act_items}</div>'

        if m.enclosure_archetype == "double_bezel":
            # Vanguard Double-Bezel: Machined Outer Shell + Nested Inner Core
            return f"""
        <div class="card-outer-shell {span_classes} scroll-reveal">
          <div class="card-inner-core">
            <div class="card-meta-row">
              {eyebrow_tag}
              <span class="card-corner-indicator"></span>
            </div>
            <h3 class="card-title">{html.escape(card.title)}</h3>
            <p class="card-body">{html.escape(card.body)}</p>
            {metric_html}
            {actions_html}
          </div>
        </div>
"""
        elif m.enclosure_archetype == "monolithic_raw":
            # Brutalist Raw Monolithic Card
            return f"""
        <div class="brutalist-block {span_classes} scroll-reveal">
          <div class="brutalist-block-header">
            {eyebrow_tag}
            <span class="brutalist-coord">[{card.col_span}x{card.row_span}]</span>
          </div>
          <div class="brutalist-block-content">
            <h3 class="card-title">{html.escape(card.title)}</h3>
            <p class="card-body">{html.escape(card.body)}</p>
            {metric_html}
            {actions_html}
          </div>
        </div>
"""
        else:
            # Minimalist Crisp Flat Card
            return f"""
        <div class="minimal-card {span_classes} scroll-reveal">
          {eyebrow_tag}
          <h3 class="card-title">{html.escape(card.title)}</h3>
          <p class="card-body">{html.escape(card.body)}</p>
          {metric_html}
          {actions_html}
        </div>
"""

    @classmethod
    def _compile_action_button(cls, action: UIActionElement, skill: TasteSkillDefinition) -> str:
        m = skill.micro
        variant = action.style_variant

        if m.button_archetype == "nested_island_pill":
            icon_markup = '<span class="btn-icon-capsule">↗</span>' if action.has_nested_icon else ""
            cls_name = "btn-island-primary" if variant == "primary" else "btn-island-secondary"
            return f'<a href="{action.url}" class="{cls_name}"><span>{html.escape(action.label)}</span>{icon_markup}</a>'
        elif m.button_archetype == "sharp_tactical_block":
            cls_name = "btn-tactical-primary" if variant == "primary" else "btn-tactical-secondary"
            return f'<a href="{action.url}" class="{cls_name}"><span>{html.escape(action.label.upper())}</span><span class="btn-status-square">■</span></a>'
        else:
            cls_name = "btn-minimal-primary" if variant == "primary" else "btn-minimal-ghost"
            return f'<a href="{action.url}" class="{cls_name}">{html.escape(action.label)} →</a>'

    @classmethod
    def _compile_footer(cls, bp: SiteBlueprint) -> str:
        skill = bp.taste_skill
        return f"""
  <footer class="site-footer">
    <div class="{skill.layout.container_max_w} mx-auto {skill.layout.macro_padding_x} py-12 flex flex-col md:flex-row items-center justify-between gap-6">
      <div class="footer-brand font-bold text-sm tracking-wider">{html.escape(bp.brand_name)}</div>
      <div class="footer-copy text-xs opacity-60 text-center md:text-right">{html.escape(bp.footer_text)}</div>
    </div>
  </footer>
"""

    @classmethod
    def _compile_custom_css(cls, skill: TasteSkillDefinition) -> str:
        """Emits strict CSS rules adhering 100% to the aesthetic tokens."""
        return """
    body {
      background-color: var(--bg-canvas);
      color: var(--text-primary);
      font-family: var(--font-body);
      margin: 0;
      padding: 0;
      overflow-x: hidden;
    }

    /* Headings & Display Scale */
    .section-headline {
      font-family: var(--font-display);
      font-size: var(--scale-display);
      letter-spacing: var(--tracking-display);
      line-height: var(--leading-display);
      margin-top: 1rem;
      margin-bottom: 1.25rem;
    }

    .section-subheading {
      color: var(--text-secondary);
      font-size: 1.125rem;
      max-width: 48rem;
      line-height: 1.7;
    }

    .section-eyebrow-badge {
      display: inline-block;
      font-family: var(--font-micro);
      font-size: 0.75rem;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      padding: 0.35rem 0.85rem;
      border-radius: var(--radius-pill);
      background-color: var(--accent-subtle);
      color: var(--accent-primary);
      border: 1px solid var(--border-hairline);
    }

    /* Navigation Island */
    .nav-island-wrapper {
      position: sticky;
      top: 1.5rem;
      z-index: 50;
      width: 100%;
      display: flex;
      justify-content: center;
      padding: 0 1rem;
    }

    .nav-island {
      background: rgba(13, 13, 14, 0.75);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--border-hairline);
      border-radius: var(--radius-pill);
      padding: 0.6rem 1.4rem;
      display: flex;
      align-items: center;
      gap: 2rem;
      box-shadow: var(--shadow-ambient);
    }

    .nav-brand {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-weight: 700;
      font-family: var(--font-display);
      text-decoration: none;
      color: var(--text-primary);
    }

    .brand-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--accent-primary);
    }

    .nav-item-link {
      color: var(--text-secondary);
      text-decoration: none;
      font-size: 0.9rem;
      transition: color 200ms ease;
    }

    .nav-item-link:hover {
      color: var(--text-primary);
    }

    /* Buttons: Island Pill */
    .btn-island-primary, .nav-cta-btn {
      display: inline-flex;
      align-items: center;
      gap: 0.75rem;
      background: var(--text-primary);
      color: var(--bg-canvas);
      padding: 0.5rem 1.25rem 0.5rem 1.5rem;
      border-radius: var(--radius-pill);
      font-weight: 600;
      font-size: 0.875rem;
      text-decoration: none;
      transition: transform var(--motion-dur) var(--motion-ease), box-shadow 300ms ease;
    }

    .btn-island-primary:hover, .nav-cta-btn:hover {
      transform: scale(0.98);
      box-shadow: 0 0 25px rgba(255, 255, 255, 0.2);
    }

    .btn-icon-capsule {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.75rem;
      height: 1.75rem;
      border-radius: 50%;
      background: rgba(0, 0, 0, 0.12);
      transition: transform 300ms ease;
    }

    .btn-island-primary:hover .btn-icon-capsule, .nav-cta-btn:hover .btn-icon-capsule {
      transform: translate(2px, -2px);
    }

    /* Double Bezel Architecture */
    .card-outer-shell {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border-hairline);
      border-radius: var(--radius-outer);
      padding: 0.5rem;
      box-shadow: var(--shadow-ambient);
      transition: transform var(--motion-dur) var(--motion-ease), border-color 300ms ease;
    }

    .card-outer-shell:hover {
      transform: translateY(-4px);
      border-color: var(--border-structural);
    }

    .card-inner-core {
      background: var(--bg-surface);
      border-radius: var(--radius-inner);
      padding: 2.25rem;
      height: 100%;
      display: flex;
      flex-direction: column;
      border: 1px solid var(--border-hairline);
    }

    .card-title {
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 700;
      line-height: 1.2;
      margin-top: 1rem;
      margin-bottom: 0.75rem;
      color: var(--text-primary);
    }

    .card-body {
      color: var(--text-secondary);
      font-size: 0.95rem;
      line-height: 1.65;
      flex-grow: 1;
    }

    .card-metric-block {
      margin-top: 1.5rem;
      padding-top: 1.25rem;
      border-top: 1px solid var(--border-hairline);
      display: flex;
      flex-direction: column;
    }

    .metric-numeral {
      font-family: var(--font-display);
      font-size: 2.25rem;
      font-weight: 800;
      color: var(--accent-primary);
    }

    .metric-caption {
      font-family: var(--font-micro);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }

    /* Tactical Brutalist Styles */
    .tactical-header {
      background: var(--bg-canvas);
      border-bottom: 2px solid var(--border-structural);
      padding: 1rem 1.5rem;
    }
    .tactical-header-inner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      max-width: 1440px;
      margin: 0 auto;
      font-family: var(--font-micro);
    }
    .brutalist-block {
      background: var(--bg-surface);
      border: 2px solid var(--border-structural);
      display: flex;
      flex-direction: column;
    }
    .brutalist-block-header {
      padding: 0.75rem 1.25rem;
      border-bottom: 2px solid var(--border-structural);
      display: flex;
      justify-content: space-between;
      font-family: var(--font-micro);
      background: var(--bg-raised);
    }
    .brutalist-block-content {
      padding: 2rem;
    }
    .btn-tactical-primary {
      display: inline-flex;
      align-items: center;
      gap: 1rem;
      background: var(--text-primary);
      color: var(--bg-canvas);
      padding: 1rem 2rem;
      font-family: var(--font-micro);
      font-weight: 700;
      text-decoration: none;
      border: 2px solid var(--border-structural);
    }

    /* Minimalist Editorial Styles */
    .minimal-header {
      border-bottom: 1px solid var(--border-hairline);
      background: var(--bg-canvas);
      padding: 1.25rem 2rem;
    }
    .minimal-header-inner {
      max-width: 72rem;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .minimal-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-hairline);
      border-radius: var(--radius-outer);
      padding: 2rem;
    }
    .btn-minimal-primary {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: var(--text-primary);
      color: var(--bg-surface);
      padding: 0.75rem 1.5rem;
      border-radius: var(--radius-inner);
      text-decoration: none;
      font-weight: 500;
      font-size: 0.95rem;
    }

    .site-footer {
      border-top: 1px solid var(--border-hairline);
      background: var(--bg-canvas);
    }
"""

    @classmethod
    def _compile_script(cls, skill: TasteSkillDefinition) -> str:
        """Vanilla JS handling scroll reveals and micro-interactions."""
        return """
    document.addEventListener('DOMContentLoaded', () => {
      // IntersectionObserver scroll reveal
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('opacity-100', 'translate-y-0');
            entry.target.classList.remove('opacity-0', 'translate-y-8');
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.1 });

      document.querySelectorAll('.scroll-reveal').forEach(el => {
        el.classList.add('transition-all', 'duration-700', 'opacity-0', 'translate-y-8');
        observer.observe(el);
      });
    });
"""

    @classmethod
    def audit_generated_code(cls, html_str: str, skill: TasteSkillDefinition) -> Dict[str, Any]:
        """
        Audit the generated frontend code against the active TasteSkillDefinition
        and absolute negative constraints.
        """
        violations: List[str] = []

        # 1. Check for banned fonts
        for banned_font in skill.typography.banned_fonts:
            # Check font-family usage outside of comments
            if re.search(rf"font-family:[^;]*\b{re.escape(banned_font)}\b", html_str, re.IGNORECASE):
                violations.append(f"CRITICAL: Banned font '{banned_font}' found in CSS.")

        # 2. Check for banned generic copy
        for cliché in skill.negative.banned_copy:
            if re.search(rf"\b{re.escape(cliché)}\b", html_str, re.IGNORECASE):
                violations.append(f"WARNING: Banned copywriting cliché '{cliché}' found in text.")

        # 3. Check for banned generic drop shadows
        if skill.negative.ban_heavy_shadows:
            if "shadow-md" in html_str or "shadow-lg" in html_str or "shadow-xl" in html_str:
                violations.append("CRITICAL: Generic Tailwind drop shadow (shadow-md/lg/xl) found.")

        # 4. Check for banned generic 3-card equal row (col-span-4 without asymmetric variance)
        if "asymmetrical_bento" in skill.layout.allowed_archetypes:
            card_col_spans = re.findall(r"md:col-span-(\d+)", html_str)
            if card_col_spans and all(span == "4" for span in card_col_spans[:3]):
                violations.append("CRITICAL: Symmetrical 3-card row detected (violation of Anti-Recycling constraint).")

        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "skill_id": skill.id,
            "skill_name": skill.name,
            "total_bytes": len(html_str),
        }
