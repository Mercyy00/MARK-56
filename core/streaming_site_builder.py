"""
core/streaming_site_builder.py — Modern Multipage Cinema & Streaming Platform Generator.

Generates complete, anti-slop, multipage streaming web applications (e.g. MOVUE)
with cohesive art direction, responsive layouts, client-side category filtering,
and an ambient-backlight interactive cinema player.

Pages generated:
  1. index.html   — Cinematic Hero, Trending Carousel, Top 10, Curated IMAX Collections.
  2. browse.html  — Interactive Catalog with live search and genre category pills.
  3. watch.html   — Cinema Player with Canvas stream visualizer, ambient room glow, and chapter selector.
  4. movie.html   — In-depth Title Overview, Cast & Crew gallery, and 4K HDR technical specs.
  5. plans.html   — Cinema Pass comparison (Standard, Cinema Club, Director's Cut VIP).
  6. style.css    — Dark obsidian & cyan/coral cinema design tokens, glassmorphism, responsive grid.
  7. app.js       — Search filtering, ambient glow engine, player controls, toast notifications.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def _build_shared_nav(active_page: str, brand_name: str = "MOVUE") -> str:
    """Builds the glassmorphic top navigation bar."""
    pages = [
        ("index.html", "Home"),
        ("browse.html", "Browse Catalog"),
        ("watch.html", "Cinema Player"),
        ("movie.html", "Featured Title"),
        ("plans.html", "VIP Passes"),
    ]

    links_markup = ""
    for href, label in pages:
        active_cls = " active" if href == active_page else ""
        links_markup += f'<a href="{href}" class="nav-link{active_cls}">{html.escape(label)}</a>\n'

    return f"""
  <header class="movue-navbar">
    <div class="nav-container">
      <a href="index.html" class="nav-brand">
        <span class="brand-prism">▶</span>
        <span class="brand-text">{html.escape(brand_name)}</span>
        <span class="brand-badge">4K ULTRA</span>
      </a>

      <nav class="nav-links">
        {links_markup}
      </nav>

      <div class="nav-actions">
        <a href="browse.html" class="nav-search-btn" title="Search Catalog">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </a>
        <a href="watch.html" class="btn-direct-play">
          <span>Stream Now</span>
        </a>
        <div class="user-pill" title="J.A.R.V.I.S. Neural Core Session">
          <div class="user-status-dot"></div>
          <span>VIP J.A.R.V.I.S.</span>
        </div>
      </div>
    </div>
  </header>
"""


def _build_shared_footer(brand_name: str = "MOVUE") -> str:
    """Builds the unified cinema footer."""
    return f"""
  <footer class="movue-footer">
    <div class="footer-container">
      <div class="footer-col-brand">
        <div class="footer-brand">{html.escape(brand_name)} CINEMA</div>
        <p class="footer-tagline">
          The next-generation autonomous streaming platform. Engineered by J.A.R.V.I.S. (MARK LVI) with zero-compromise anti-slop art direction, lossless spatial audio, and pristine 4K HDR playback.
        </p>
        <div class="footer-meta">© 2026 {html.escape(brand_name)} Entertainment Systems. All rights reserved.</div>
      </div>

      <div class="footer-links-grid">
        <div class="footer-group">
          <h4>Navigation</h4>
          <a href="index.html">Featured Home</a>
          <a href="browse.html">Catalog & Search</a>
          <a href="watch.html">Cinema Player</a>
          <a href="movie.html">Featured Showcase</a>
          <a href="plans.html">VIP Passes</a>
        </div>
        <div class="footer-group">
          <h4>Technologies</h4>
          <span>Dolby Atmos 7.1</span>
          <span>IMAX Enhanced</span>
          <span>4K Ultra HD</span>
          <span>Zero-CLS Engine</span>
        </div>
        <div class="footer-group">
          <h4>System</h4>
          <span>J.A.R.V.I.S. MARK LVI</span>
          <span>FastLayoutCache</span>
          <span>Web Worker Stream</span>
          <span>Status: Online</span>
        </div>
      </div>
    </div>
  </footer>
"""


def _build_css() -> str:
    """Generates the master cinema design system stylesheet."""
    return """/* MOVUE Streaming Platform Design System — Anti-Slop Art Direction */
@import url('https://fonts.googleapis.com/css2?family=Cabinet+Grotesk:wght@700;800;900&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Syne:wght@700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #06080f;
  --bg-deep: #030408;
  --surface: #0e1322;
  --surface-hover: #151d33;
  --border: #1b253b;
  --border-focus: #00f0ff;
  --text: #f1f5f9;
  --text-muted: #8a99b5;
  --cyan: #00f0ff;
  --coral: #ff2a5f;
  --amber: #ffb800;
  --font-display: 'Cabinet Grotesk', 'Syne', sans-serif;
  --font-body: 'Plus Jakarta Sans', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background-color: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  overflow-x: hidden;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Glassmorphic Navbar */
.movue-navbar {
  position: sticky;
  top: 0;
  z-index: 200;
  background: rgba(6, 8, 15, 0.88);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border);
  transition: background-color 0.3s ease;
}

.nav-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 2rem;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
  color: var(--text);
}

.brand-prism {
  color: var(--cyan);
  font-size: 1.3rem;
  filter: drop-shadow(0 0 8px rgba(0, 240, 255, 0.6));
}

.brand-text {
  font-family: var(--font-display);
  font-size: 1.6rem;
  font-weight: 900;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, #ffffff 40%, var(--cyan) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.brand-badge {
  font-size: 0.65rem;
  font-family: var(--font-mono);
  font-weight: 700;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  background: rgba(0, 240, 255, 0.12);
  color: var(--cyan);
  border: 1px solid rgba(0, 240, 255, 0.3);
  letter-spacing: 0.08em;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 1.75rem;
}

.nav-link {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: color 0.2s ease;
  position: relative;
  padding: 0.25rem 0;
}

.nav-link:hover {
  color: var(--text);
}

.nav-link.active {
  color: var(--cyan);
  font-weight: 600;
}

.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  width: 100%;
  height: 2px;
  background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan);
  border-radius: 2px;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.nav-search-btn {
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
  border-radius: 8px;
  transition: color 0.2s, background-color 0.2s;
}

.nav-search-btn:hover {
  color: var(--cyan);
  background: rgba(255, 255, 255, 0.05);
}

.btn-direct-play {
  background: linear-gradient(135deg, var(--coral), #d91b4c);
  color: #fff;
  text-decoration: none;
  padding: 0.55rem 1.3rem;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 4px 15px rgba(255, 42, 95, 0.35);
}

.btn-direct-play:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 42, 95, 0.5);
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.85rem;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  font-size: 0.75rem;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

.user-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}

/* Main Container */
main {
  flex: 1;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  padding: 0 2rem 5rem;
}

/* Hero Section */
.movue-hero {
  position: relative;
  min-height: 560px;
  border-radius: 24px;
  overflow: hidden;
  margin: 2rem 0 4rem;
  border: 1px solid var(--border);
  display: flex;
  align-items: flex-end;
  background: radial-gradient(circle at 75% 30%, rgba(0, 240, 255, 0.15), transparent 50%),
              radial-gradient(circle at 20% 80%, rgba(255, 42, 95, 0.12), transparent 45%),
              #080c18;
}

.hero-backdrop-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.45;
  mix-blend-mode: screen;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 20%, rgba(6, 8, 15, 0.95) 90%);
}

.hero-content {
  position: relative;
  z-index: 10;
  padding: 4rem;
  max-width: 820px;
}

.hero-badges {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}

.badge-pill {
  padding: 0.25rem 0.65rem;
  border-radius: 6px;
  font-size: 0.7rem;
  font-family: var(--font-mono);
  font-weight: 600;
  letter-spacing: 0.05em;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--text);
}

.badge-pill.highlight {
  background: rgba(0, 240, 255, 0.15);
  border-color: var(--cyan);
  color: var(--cyan);
}

.badge-pill.rating {
  background: rgba(255, 184, 0, 0.15);
  border-color: var(--amber);
  color: var(--amber);
}

.hero-title {
  font-family: var(--font-display);
  font-size: clamp(2.5rem, 5vw, 4.25rem);
  line-height: 1.05;
  font-weight: 900;
  letter-spacing: -0.02em;
  margin-bottom: 1rem;
}

.hero-synopsis {
  font-size: 1.1rem;
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 2rem;
  max-width: 700px;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.btn-hero-play {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.9rem 2.2rem;
  border-radius: 9999px;
  background: var(--text);
  color: var(--bg);
  font-weight: 700;
  font-size: 0.95rem;
  text-decoration: none;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.btn-hero-play:hover {
  transform: translateY(-2px);
  opacity: 0.94;
}

.btn-hero-details {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.9rem 2rem;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: var(--text);
  font-weight: 600;
  font-size: 0.95rem;
  text-decoration: none;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

.btn-hero-details:hover {
  background: rgba(255, 255, 255, 0.14);
  border-color: var(--cyan);
}

/* Movie Carousel & Grids */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin: 3.5rem 0 1.5rem;
}

.section-title {
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 800;
  letter-spacing: -0.01em;
}

.section-link {
  color: var(--cyan);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.movie-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1.75rem;
}

.movie-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s ease, box-shadow 0.25s ease;
  position: relative;
  display: flex;
  flex-direction: column;
}

.movie-card:hover {
  transform: translateY(-6px) scale(1.02);
  border-color: rgba(0, 240, 255, 0.4);
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.6);
}

.card-poster {
  width: 100%;
  aspect-ratio: 16/10;
  background: #080c14;
  position: relative;
  overflow: hidden;
}

.card-poster svg, .card-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.movie-card:hover .card-poster svg,
.movie-card:hover .card-poster img {
  transform: scale(1.05);
}

.card-quality-tag {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(6, 8, 15, 0.85);
  backdrop-filter: blur(8px);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--cyan);
  border: 1px solid rgba(0, 240, 255, 0.3);
}

.card-play-hover {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(6, 8, 15, 0.4);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.movie-card:hover .card-play-hover {
  opacity: 1;
}

.play-circle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--coral);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  box-shadow: 0 0 16px rgba(255, 42, 95, 0.6);
}

.card-body {
  padding: 1.25rem;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.card-title {
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 0.35rem;
}

.card-genre {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 0.85rem;
}

.card-meta {
  margin-top: auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.75rem;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

.card-rating {
  color: var(--amber);
  font-weight: 600;
}

/* Cinema Player (watch.html) */
.cinema-theater-wrapper {
  margin: 2rem 0;
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 2rem;
  align-items: start;
}

.cinema-stage {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid var(--border);
  background: #000;
  aspect-ratio: 16/9;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8);
}

.ambient-glow-layer {
  position: absolute;
  inset: -40px;
  background: radial-gradient(ellipse at center, rgba(0, 240, 255, 0.25), rgba(255, 42, 95, 0.2), transparent 70%);
  filter: blur(50px);
  z-index: 1;
  opacity: 0.85;
  transition: opacity 0.4s ease;
  pointer-events: none;
}

.canvas-player {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
  display: block;
}

.player-controls-hud {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 10;
  background: linear-gradient(0deg, rgba(6, 8, 15, 0.95), transparent);
  padding: 1.5rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.scrubber-bar-container {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  cursor: pointer;
  position: relative;
}

.scrubber-progress {
  height: 100%;
  width: 48%;
  background: linear-gradient(90deg, var(--cyan), var(--coral));
  border-radius: 3px;
  box-shadow: 0 0 10px var(--cyan);
}

.controls-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.controls-left, .controls-right {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.hud-btn {
  background: none;
  border: none;
  color: var(--text);
  font-size: 1.1rem;
  cursor: pointer;
  transition: color 0.2s, transform 0.15s;
}

.hud-btn:hover {
  color: var(--cyan);
  transform: scale(1.1);
}

.timecode-display {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-muted);
}

.sidebar-episodes {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 1.5rem;
}

.episodes-title {
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 800;
  margin-bottom: 1rem;
}

.episode-item {
  display: flex;
  gap: 1rem;
  padding: 0.85rem;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid transparent;
  margin-bottom: 0.75rem;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s;
}

.episode-item:hover, .episode-item.active {
  background: rgba(0, 240, 255, 0.08);
  border-color: rgba(0, 240, 255, 0.3);
}

.episode-num {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--cyan);
  font-weight: 700;
}

.episode-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text);
}

.episode-dur {
  font-size: 0.75rem;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

/* Movie Details (movie.html) */
.movie-details-header {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 3.5rem;
  margin: 3rem 0;
  align-items: start;
}

.movie-poster-large {
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid var(--border);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
  aspect-ratio: 2/3;
  background: var(--surface);
}

.movie-specs-table {
  width: 100%;
  border-collapse: collapse;
  margin: 2rem 0;
  font-size: 0.85rem;
  font-family: var(--font-mono);
}

.movie-specs-table td {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--border);
}

.movie-specs-table td:first-child {
  color: var(--text-muted);
  width: 35%;
}

/* Plans (plans.html) */
.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin: 3rem 0;
}

.plan-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 2.5rem;
  display: flex;
  flex-direction: column;
  position: relative;
  transition: transform 0.25s ease, border-color 0.25s ease;
}

.plan-card:hover {
  transform: translateY(-5px);
}

.plan-card.featured {
  border-color: var(--cyan);
  background: linear-gradient(180deg, rgba(0, 240, 255, 0.05), var(--surface));
  box-shadow: 0 15px 40px rgba(0, 240, 255, 0.15);
}

.plan-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--cyan);
  color: #000;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 800;
  padding: 0.25rem 0.8rem;
  border-radius: 9999px;
  letter-spacing: 0.05em;
}

.plan-price {
  font-family: var(--font-display);
  font-size: 2.75rem;
  font-weight: 900;
  color: var(--text);
  margin: 1rem 0;
}

.plan-features {
  list-style: none;
  margin: 2rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  font-size: 0.9rem;
}

.plan-features li::before {
  content: "✔";
  color: var(--cyan);
  margin-right: 0.6rem;
  font-weight: 700;
}

/* Toast Alerts */
.movue-toast {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  background: rgba(14, 19, 34, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid var(--cyan);
  color: var(--text);
  padding: 0.85rem 1.4rem;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  font-size: 0.85rem;
  font-family: var(--font-mono);
  z-index: 9999;
  display: none;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

/* Footer */
.movue-footer {
  border-top: 1px solid var(--border);
  background: var(--bg-deep);
  padding: 4rem 2rem;
  margin-top: auto;
}

.footer-container {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.5fr 2fr;
  gap: 4rem;
}

.footer-brand {
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 900;
  color: var(--text);
  margin-bottom: 0.85rem;
}

.footer-tagline {
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.6;
  max-width: 440px;
  margin-bottom: 1.5rem;
}

.footer-meta {
  font-size: 0.75rem;
  font-family: var(--font-mono);
  color: var(--text-muted);
}

.footer-links-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
}

.footer-group h4 {
  font-family: var(--font-display);
  font-size: 0.95rem;
  margin-bottom: 1rem;
  color: var(--text);
}

.footer-group a, .footer-group span {
  display: block;
  font-size: 0.8rem;
  color: var(--text-muted);
  text-decoration: none;
  margin-bottom: 0.6rem;
}

.footer-group a:hover {
  color: var(--cyan);
}

@media (max-width: 900px) {
  .cinema-theater-wrapper { grid-template-columns: 1fr; }
  .movie-details-header { grid-template-columns: 1fr; }
  .footer-container { grid-template-columns: 1fr; gap: 2rem; }
  .nav-links { display: none; }
}
"""


def _build_js() -> str:
    """Generates the interactive cinema streaming script."""
    return """/* MOVUE Interactive Streaming Engine */

// Toast notification helper
function showToast(message) {
  let toast = document.getElementById('movue-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'movue-toast';
    toast.className = 'movue-toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.display = 'block';
  setTimeout(() => {
    toast.style.display = 'none';
  }, 2800);
}

// Watchlist toggle
function toggleWatchlist(title) {
  showToast(`✦ "${title}" added to your VIP Watchlist.`);
}

// Live Category Filter on browse.html
function filterCategory(category) {
  const cards = document.querySelectorAll('.movie-card[data-category]');
  const pills = document.querySelectorAll('.filter-pill');
  
  pills.forEach(p => p.classList.toggle('active', p.getAttribute('data-cat') === category));

  cards.forEach(card => {
    const cardCat = card.getAttribute('data-category');
    if (category === 'all' || cardCat.includes(category)) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });
}

// Live Search filter
function filterSearch(query) {
  const q = query.toLowerCase().trim();
  const cards = document.querySelectorAll('.movie-card');
  cards.forEach(card => {
    const title = (card.querySelector('.card-title')?.textContent || '').toLowerCase();
    const genre = (card.querySelector('.card-genre')?.textContent || '').toLowerCase();
    if (!q || title.includes(q) || genre.includes(q)) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });
}

// Interactive Cinema Player Animation (watch.html)
window.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('cinemaPlayerCanvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let isPlaying = true;
  let animId;
  let t = 0;

  function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  function renderStreamFrame() {
    if (!isPlaying) return;
    t += 0.02;
    const w = canvas.width;
    const h = canvas.height;

    // Deep space gradient
    const grad = ctx.createLinearGradient(0, 0, w, h);
    grad.addColorStop(0, '#040711');
    grad.addColorStop(0.5, '#0d1326');
    grad.addColorStop(1, '#050a16');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);

    // Dynamic cyber energy waves
    for (let i = 0; i < 4; i++) {
      ctx.beginPath();
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = i % 2 === 0 ? 'rgba(0, 240, 255, 0.45)' : 'rgba(255, 42, 95, 0.35)';
      for (let x = 0; x < w; x += 15) {
        const y = h * 0.5 + Math.sin(x * 0.008 + t + i * 1.2) * 55 * Math.cos(t * 0.5);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }

    // HUD target reticle
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.3)';
    ctx.lineWidth = 1;
    ctx.strokeRect(w * 0.2, h * 0.2, w * 0.6, h * 0.6);

    ctx.font = '12px "JetBrains Mono", monospace';
    ctx.fillStyle = '#00f0ff';
    ctx.fillText('MOVUE STREAM // 4K 60FPS // DOLBY ATMOS 7.1 // LIVE', w * 0.2 + 15, h * 0.2 + 25);
    ctx.fillStyle = '#ff2a5f';
    ctx.fillText('AUDIO STREAM: LOSSLESS BITSTREAM', w * 0.2 + 15, h * 0.2 + 42);

    animId = requestAnimationFrame(renderStreamFrame);
  }

  renderStreamFrame();

  // Play/Pause button
  const playBtn = document.getElementById('playPauseBtn');
  if (playBtn) {
    playBtn.addEventListener('click', () => {
      isPlaying = !isPlaying;
      playBtn.textContent = isPlaying ? '⏸' : '▶';
      if (isPlaying) renderStreamFrame();
      showToast(isPlaying ? 'Stream Resumed (4K 60FPS)' : 'Stream Paused');
    });
  }

  // Ambient Glow Toggle
  const glowBtn = document.getElementById('toggleGlowBtn');
  const ambientLayer = document.querySelector('.ambient-glow-layer');
  if (glowBtn && ambientLayer) {
    glowBtn.addEventListener('click', () => {
      const isVisible = ambientLayer.style.display !== 'none';
      ambientLayer.style.display = isVisible ? 'none' : 'block';
      showToast(isVisible ? 'Ambient Glow Disabled' : 'Ambient Room Glow Engaged');
    });
  }
});
"""


def _sample_movie_svg(title: str, accent: str = "#00f0ff", bg: str = "#070c18") -> str:
    """Generates an embedded, anti-slop SVG movie backdrop."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="100%" height="100%">'
        f'<rect width="800" height="500" fill="{bg}"/>'
        f'<circle cx="400" cy="250" r="180" fill="none" stroke="{accent}" stroke-width="2" opacity="0.3"/>'
        f'<circle cx="400" cy="250" r="90" fill="none" stroke="{accent}" stroke-width="1.5" stroke-dasharray="8,8" opacity="0.5"/>'
        f'<text x="400" y="245" fill="#f1f5f9" font-family="sans-serif" font-weight="900" font-size="28" letter-spacing="2" text-anchor="middle">{html.escape(title.upper())}</text>'
        f'<text x="400" y="280" fill="{accent}" font-family="monospace" font-size="12" letter-spacing="3" text-anchor="middle">CINEMA MASTERWORK // 4K</text>'
        f'</svg>'
    )


def build_streaming_multipage_site(
    target_dir: Path,
    brand_name: str = "MOVUE",
    palette: str = "tech",
    **kwargs
) -> Tuple[Path, str]:
    """
    Assembles the complete 5-page Movue streaming application in target_dir.
    Returns (index_path, file_url).
    """
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write CSS and JS
    (target_dir / "style.css").write_text(_build_css(), encoding="utf-8")
    (target_dir / "app.js").write_text(_build_js(), encoding="utf-8")

    # Sample catalog data
    movies = [
        {"title": "Neuromancer: Chrono Shift", "genre": "Cyberpunk • Sci-Fi", "rating": "★ 9.2", "year": "2026", "cat": "cyberpunk sci-fi", "color": "#00f0ff"},
        {"title": "Neon Abyss", "genre": "Dystopian • Action", "rating": "★ 8.9", "year": "2025", "cat": "cyberpunk action", "color": "#ff2a5f"},
        {"title": "The Obsidian Protocol", "genre": "Crime • Dark Thriller", "rating": "★ 9.1", "year": "2026", "cat": "thriller noir", "color": "#d4af37"},
        {"title": "Solaris Drift", "genre": "Space Opera • Mystery", "rating": "★ 9.4", "year": "2026", "cat": "sci-fi space", "color": "#3b82f6"},
        {"title": "Quantum Echo", "genre": "Psychological • Mind-Bending", "rating": "★ 8.8", "year": "2024", "cat": "psychological sci-fi", "color": "#10b981"},
        {"title": "Cyberia 2099", "genre": "Sci-Fi • Thriller", "rating": "★ 9.0", "year": "2025", "cat": "cyberpunk thriller", "color": "#a855f7"},
        {"title": "Sub-Zero Protocol", "genre": "Espionage • Tactical", "rating": "★ 8.7", "year": "2026", "cat": "action thriller", "color": "#06b6d4"},
        {"title": "The Glass Citadel", "genre": "Dark Noir • Drama", "rating": "★ 9.3", "year": "2025", "cat": "noir drama", "color": "#e8a838"},
    ]

    # ── Page 1: index.html ──
    cards_html = ""
    for idx, m in enumerate(movies[:6]):
        cards_html += f"""
      <a href="movie.html" class="movie-card" data-category="{m['cat']}">
        <div class="card-poster">
          {_sample_movie_svg(m['title'], accent=m['color'])}
          <span class="card-quality-tag">4K HDR</span>
          <div class="card-play-hover">
            <div class="play-circle">▶</div>
          </div>
        </div>
        <div class="card-body">
          <h3 class="card-title">{html.escape(m['title'])}</h3>
          <div class="card-genre">{html.escape(m['genre'])}</div>
          <div class="card-meta">
            <span class="card-rating">{m['rating']}</span>
            <span>{m['year']}</span>
          </div>
        </div>
      </a>
        """

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(brand_name)} — Next-Gen 4K Streaming</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  {_build_shared_nav("index.html", brand_name)}

  <main>
    <section class="movue-hero">
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <div class="hero-badges">
          <span class="badge-pill highlight">EXCLUSIVE PREMIERE</span>
          <span class="badge-pill">4K ULTRA HD</span>
          <span class="badge-pill">DOLBY ATMOS</span>
          <span class="badge-pill rating">★ 9.2 IMDb</span>
          <span class="badge-pill">18+</span>
        </div>
        <h1 class="hero-title">NEUROMANCER:<br>CHRONO SHIFT</h1>
        <p class="hero-synopsis">
          In a neon-drenched megacity, a rogue neural hacker discovers a fractured simulation loop that controls the memories of 40 million citizens. Directed by Denis Villeneuve with an original score by Hans Zimmer.
        </p>
        <div class="hero-actions">
          <a href="watch.html" class="btn-hero-play">
            <span>▶ Play in 4K HDR</span>
          </a>
          <a href="movie.html" class="btn-hero-details">
            <span>ℹ Film Overview</span>
          </a>
          <button type="button" class="btn-hero-details" onclick="toggleWatchlist('Neuromancer: Chrono Shift')">
            <span>＋ Add to Watchlist</span>
          </button>
        </div>
      </div>
    </section>

    <div class="section-header">
      <h2 class="section-title">Trending Global Releases</h2>
      <a href="browse.html" class="section-link">View Full Catalog →</a>
    </div>

    <div class="movie-grid">
      {cards_html}
    </div>

    <div class="section-header">
      <h2 class="section-title">Curated IMAX Masterworks</h2>
      <a href="browse.html" class="section-link">Explore Collection →</a>
    </div>

    <div style="background: linear-gradient(135deg, rgba(0, 240, 255, 0.08), rgba(255, 42, 95, 0.05)); border: 1px solid var(--border); border-radius: 20px; padding: 3rem; display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
      <div>
        <span class="badge-pill highlight" style="margin-bottom: 0.75rem; display: inline-block;">LOSSLESS AUDIO</span>
        <h3 style="font-family: var(--font-display); font-size: 2rem; margin-bottom: 0.5rem;">The Cybernetic Cinema Experience</h3>
        <p style="color: var(--text-muted); max-width: 600px;">Stream in uncompressed 24-bit 96kHz spatial audio directly to your reference theater setup.</p>
      </div>
      <a href="plans.html" class="btn-direct-play" style="padding: 0.9rem 2rem; font-size: 0.95rem;">Upgrade to VIP Pass</a>
    </div>
  </main>

  {_build_shared_footer(brand_name)}
  <script src="app.js"></script>
</body>
</html>
"""
    (target_dir / "index.html").write_text(index_html, encoding="utf-8")

    # ── Page 2: browse.html ──
    browse_cards_html = ""
    for m in movies:
        browse_cards_html += f"""
      <a href="movie.html" class="movie-card" data-category="{m['cat']}">
        <div class="card-poster">
          {_sample_movie_svg(m['title'], accent=m['color'])}
          <span class="card-quality-tag">4K HDR</span>
          <div class="card-play-hover">
            <div class="play-circle">▶</div>
          </div>
        </div>
        <div class="card-body">
          <h3 class="card-title">{html.escape(m['title'])}</h3>
          <div class="card-genre">{html.escape(m['genre'])}</div>
          <div class="card-meta">
            <span class="card-rating">{m['rating']}</span>
            <span>{m['year']}</span>
          </div>
        </div>
      </a>
        """

    browse_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Browse Catalog — {html.escape(brand_name)}</title>
  <link rel="stylesheet" href="style.css">
  <style>
    .browse-filter-bar {{
      margin: 2rem 0;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }}
    .search-input {{
      width: 100%;
      padding: 1rem 1.5rem;
      border-radius: 14px;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      font-family: var(--font-body);
      font-size: 1rem;
      outline: none;
      transition: border-color 0.2s;
    }}
    .search-input:focus {{ border-color: var(--cyan); box-shadow: 0 0 15px rgba(0,240,255,0.2); }}
    .pill-group {{
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
    }}
    .filter-pill {{
      padding: 0.5rem 1.2rem;
      border-radius: 9999px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--border);
      color: var(--text-muted);
      cursor: pointer;
      font-size: 0.85rem;
      font-weight: 500;
      transition: all 0.2s;
    }}
    .filter-pill:hover, .filter-pill.active {{
      background: rgba(0, 240, 255, 0.15);
      border-color: var(--cyan);
      color: var(--cyan);
    }}
  </style>
</head>
<body>
  {_build_shared_nav("browse.html", brand_name)}

  <main>
    <div class="section-header" style="margin-top: 2rem;">
      <div>
        <h1 class="section-title">Film & Series Catalog</h1>
        <p style="color: var(--text-muted); font-size: 0.9rem;">Explore over 12,000 curated 4K cinema masterworks.</p>
      </div>
    </div>

    <div class="browse-filter-bar">
      <input type="text" class="search-input" placeholder="Search by title, genre, director or actor..." oninput="filterSearch(this.value)">
      <div class="pill-group">
        <button type="button" class="filter-pill active" data-cat="all" onclick="filterCategory('all')">All Genres</button>
        <button type="button" class="filter-pill" data-cat="cyberpunk" onclick="filterCategory('cyberpunk')">Cyberpunk</button>
        <button type="button" class="filter-pill" data-cat="sci-fi" onclick="filterCategory('sci-fi')">Sci-Fi</button>
        <button type="button" class="filter-pill" data-cat="thriller" onclick="filterCategory('thriller')">Dark Thriller</button>
        <button type="button" class="filter-pill" data-cat="noir" onclick="filterCategory('noir')">Neo-Noir</button>
        <button type="button" class="filter-pill" data-cat="space" onclick="filterCategory('space')">Space Opera</button>
        <button type="button" class="filter-pill" data-cat="psychological" onclick="filterCategory('psychological')">Psychological</button>
      </div>
    </div>

    <div class="movie-grid" id="catalogGrid">
      {browse_cards_html}
    </div>
  </main>

  {_build_shared_footer(brand_name)}
  <script src="app.js"></script>
</body>
</html>
"""
    (target_dir / "browse.html").write_text(browse_html, encoding="utf-8")

    # ── Page 3: watch.html ──
    watch_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cinema Player — Neuromancer: Chrono Shift</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  {_build_shared_nav("watch.html", brand_name)}

  <main>
    <div class="cinema-theater-wrapper">
      <div>
        <div class="cinema-stage">
          <div class="ambient-glow-layer"></div>
          <canvas id="cinemaPlayerCanvas" class="canvas-player"></canvas>

          <div class="player-controls-hud">
            <div class="scrubber-bar-container">
              <div class="scrubber-progress"></div>
            </div>

            <div class="controls-row">
              <div class="controls-left">
                <button type="button" class="hud-btn" id="playPauseBtn" title="Play / Pause">⏸</button>
                <div class="timecode-display">01:14:22 / 02:24:00</div>
              </div>

              <div class="controls-right">
                <button type="button" class="hud-btn" id="toggleGlowBtn" title="Toggle Ambient Room Glow">💡 Ambient Glow</button>
                <button type="button" class="hud-btn" onclick="showToast('Audio set to Dolby Atmos 7.1 TrueHD')">🔊 7.1 Atmos</button>
                <button type="button" class="hud-btn" onclick="showToast('Subtitles: English SDH')">💬 CC</button>
                <button type="button" class="hud-btn" onclick="showToast('Max Quality: 4K UHD 60FPS')">⚙ 4K 60</button>
              </div>
            </div>
          </div>
        </div>

        <div style="margin-top: 1.5rem; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <h1 style="font-family: var(--font-display); font-size: 2rem;">Neuromancer: Chrono Shift</h1>
            <p style="color: var(--text-muted); font-size: 0.9rem;">Chapter 03: The Simulation Matrix • 4K HDR • 5.1 & Atmos</p>
          </div>
          <div style="display: flex; gap: 1rem;">
            <button type="button" class="btn-hero-details" onclick="toggleWatchlist('Neuromancer: Chrono Shift')">＋ Watchlist</button>
            <a href="movie.html" class="btn-hero-details">Film Info</a>
          </div>
        </div>
      </div>

      <aside class="sidebar-episodes">
        <h3 class="episodes-title">Timeline Chapters</h3>
        <div class="episode-item active" onclick="showToast('Switched to Chapter 01')">
          <div class="episode-num">01</div>
          <div>
            <div class="episode-name">The Glitch in Sector 4</div>
            <div class="episode-dur">24 min • 4K HDR</div>
          </div>
        </div>
        <div class="episode-item" onclick="showToast('Switched to Chapter 02')">
          <div class="episode-num">02</div>
          <div>
            <div class="episode-name">The Neural Breach</div>
            <div class="episode-dur">31 min • 4K HDR</div>
          </div>
        </div>
        <div class="episode-item" onclick="showToast('Switched to Chapter 03')">
          <div class="episode-num">03</div>
          <div>
            <div class="episode-name">Obsidian Overdrive</div>
            <div class="episode-dur">28 min • 4K HDR</div>
          </div>
        </div>
        <div class="episode-item" onclick="showToast('Switched to Chapter 04')">
          <div class="episode-num">04</div>
          <div>
            <div class="episode-name">Reality Synthesis</div>
            <div class="episode-dur">38 min • 4K HDR</div>
          </div>
        </div>
      </aside>
    </div>
  </main>

  {_build_shared_footer(brand_name)}
  <script src="app.js"></script>
</body>
</html>
"""
    (target_dir / "watch.html").write_text(watch_html, encoding="utf-8")

    # ── Page 4: movie.html ──
    movie_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Overview — Neuromancer: Chrono Shift</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  {_build_shared_nav("movie.html", brand_name)}

  <main>
    <div class="movie-details-header">
      <div class="movie-poster-large">
        {_sample_movie_svg("Neuromancer: Chrono Shift", accent="#00f0ff")}
      </div>

      <div>
        <div class="hero-badges">
          <span class="badge-pill highlight">MASTERWORK</span>
          <span class="badge-pill rating">★ 9.2 IMDb</span>
          <span class="badge-pill">98% ROTTEN TOMATOES</span>
          <span class="badge-pill">2h 24m</span>
          <span class="badge-pill">2026</span>
        </div>

        <h1 class="hero-title" style="font-size: 3.25rem;">Neuromancer: Chrono Shift</h1>
        <p style="color: var(--cyan); font-family: var(--font-mono); font-size: 0.9rem; margin-bottom: 1.25rem;">
          DIRECTED BY DENIS VILLENEUVE • WRITTEN BY WILLIAM GIBSON & JONATHAN NOLAN
        </p>

        <p style="font-size: 1.15rem; color: var(--text-muted); line-height: 1.7; margin-bottom: 2rem;">
          In the neon-drenched sprawl of Chiba City and the orbiting luxury archipelago of Freeside, Case—a former console cowboy whose nervous system was damaged by neural mycotoxin—is offered one final chance at restoration. A shadowy operative known as Armitage recruits him for a dangerous heist into the core of an omnipresent artificial intelligence known as Wintermute.
        </p>

        <div style="display: flex; gap: 1.25rem; margin-bottom: 2.5rem;">
          <a href="watch.html" class="btn-hero-play" style="padding: 1rem 2.5rem; font-size: 1rem;">
            <span>▶ Watch Feature Now</span>
          </a>
          <button type="button" class="btn-hero-details" onclick="toggleWatchlist('Neuromancer: Chrono Shift')">
            <span>＋ Add to Watchlist</span>
          </button>
        </div>

        <h3 class="section-title" style="font-size: 1.3rem; margin-bottom: 0.75rem;">Technical Specifications</h3>
        <table class="movie-specs-table">
          <tr><td>Native Resolution</td><td>4K UHD (3840 × 2160) at 60 FPS</td></tr>
          <tr><td>Color Grading</td><td>Dolby Vision Profile 8 & HDR10+ Adaptive</td></tr>
          <tr><td>Spatial Audio</td><td>Dolby Atmos 7.1.4 Lossless TrueHD & DTS:X</td></tr>
          <tr><td>Aspect Ratio</td><td>2.39:1 Anamorphic Widescreen</td></tr>
          <tr><td>Production Studio</td><td>Alcon Entertainment & Warner Bros.</td></tr>
        </table>
      </div>
    </div>
  </main>

  {_build_shared_footer(brand_name)}
  <script src="app.js"></script>
</body>
</html>
"""
    (target_dir / "movie.html").write_text(movie_html, encoding="utf-8")

    # ── Page 5: plans.html ──
    plans_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cinema VIP Passes — {html.escape(brand_name)}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  {_build_shared_nav("plans.html", brand_name)}

  <main>
    <div style="text-align: center; max-width: 750px; margin: 3rem auto 2rem;">
      <span class="badge-pill highlight">UNCOMPROMISING STREAMING</span>
      <h1 class="hero-title" style="font-size: 3rem; margin: 0.75rem 0;">Experience Cinema at Home</h1>
      <p style="color: var(--text-muted); font-size: 1.1rem;">
        Choose the pass that fits your reference display and spatial audio setup. Zero advertisements, zero bitrate throttling.
      </p>
    </div>

    <div class="plans-grid">
      <div class="plan-card">
        <h3>Standard Cinema</h3>
        <p style="color: var(--text-muted); font-size: 0.85rem;">For pristine personal viewing</p>
        <div class="plan-price">$9.99<span style="font-size: 1rem; color: var(--text-muted);">/mo</span></div>
        <ul class="plan-features">
          <li>1080p Full HD Resolution</li>
          <li>5.1 Surround Sound</li>
          <li>Watch on 2 screens simultaneously</li>
          <li>Standard download speeds</li>
        </ul>
        <button type="button" class="btn-hero-details" style="width: 100%; justify-content: center;" onclick="showToast('Selected Standard Plan')">Select Standard</button>
      </div>

      <div class="plan-card featured">
        <div class="plan-badge">MOST POPULAR</div>
        <h3>Cinema Club 4K</h3>
        <p style="color: var(--text-muted); font-size: 0.85rem;">The ultimate home theater experience</p>
        <div class="plan-price" style="color: var(--cyan);">$15.99<span style="font-size: 1rem; color: var(--text-muted);">/mo</span></div>
        <ul class="plan-features">
          <li>4K Ultra HD & Dolby Vision HDR</li>
          <li>Dolby Atmos 7.1 Spatial Audio</li>
          <li>Watch on 4 screens simultaneously</li>
          <li>Ultra-high 80Mbps bitrate stream</li>
          <li>Early weekend premiere access</li>
        </ul>
        <button type="button" class="btn-direct-play" style="width: 100%; text-align: center;" onclick="showToast('Upgraded to Cinema Club 4K Pass!')">Upgrade to 4K Club</button>
      </div>

      <div class="plan-card">
        <h3>Director's Cut VIP</h3>
        <p style="color: var(--text-muted); font-size: 0.85rem;">For reference mastering rooms & cinephiles</p>
        <div class="plan-price">$24.99<span style="font-size: 1rem; color: var(--text-muted);">/mo</span></div>
        <ul class="plan-features">
          <li>IMAX Enhanced 4K Widescreen</li>
          <li>Lossless 24-bit 96kHz Master Audio</li>
          <li>Unlimited concurrent screens</li>
          <li>Offline ProRes archiving</li>
          <li>Exclusive Director commentary tracks</li>
        </ul>
        <button type="button" class="btn-hero-details" style="width: 100%; justify-content: center;" onclick="showToast('Director Cut VIP Selected')">Select Director VIP</button>
      </div>
    </div>
  </main>

  {_build_shared_footer(brand_name)}
  <script src="app.js"></script>
</body>
</html>
"""
    (target_dir / "plans.html").write_text(plans_html, encoding="utf-8")

    index_path = target_dir / "index.html"
    file_url = f"file:///{index_path.resolve().as_posix()}"
    return index_path, file_url
