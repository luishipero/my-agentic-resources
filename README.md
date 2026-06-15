# My Agentic Resources

Personal collection of Claude Code skills, design systems, and development tools. Reusable resources for frontend development, performance optimization, and design workflows.

## What's Inside

### 📋 [React Best Practices](./react-best-practices)
Comprehensive React and Next.js performance optimization guide with 40+ rules.

**Focus areas:**
- Eliminating waterfalls (critical)
- Bundle size optimization
- Server-side performance (RSC, data fetching)
- Client-side caching and SWR patterns
- Re-render optimization
- Rendering performance
- JavaScript micro-optimizations

**Quick wins:**
- Defer `await` until needed
- Use `Promise.all()` for parallel operations
- Avoid barrel imports
- Dynamic imports for code splitting
- Strategic Suspense boundaries

📁 **Structure:** `references/rules/` contains 40+ individual optimization rules with code examples and explanations.

---

### 🎨 [UI Design System](./ui-design-system)
Toolkit for creating and maintaining scalable design systems.

**Includes:**
- Design token generation (colors, typography, spacing)
- Component system architecture
- Responsive design calculations
- Accessibility compliance patterns
- Developer handoff documentation

**Key script:** `design_token_generator.py` - Generates complete token sets from brand colors.

```bash
python scripts/design_token_generator.py [brand_color] [style] [format]
# Styles: modern, classic, playful
# Formats: json, css, scss
```

---

### 🖌️ [Canvas Design](./canvas-design)
Design resources and typography assets for canvas-based projects.

**Includes:**
- 20+ professional fonts (TTF format)
- Font licensing information
- Canvas rendering guidelines
- Design token references

**Font families:** Arsenal, BigShoulders, Bricolage Grotesque, Crimson Pro, IBM Plex (Mono & Serif), Instrument (Sans & Serif), JetBrains Mono, and more.

---

## Quick Start

Each subdirectory contains a `SKILL.md` file documenting:
- When and how to use the resource
- Key capabilities and patterns
- Usage examples
- Implementation guidelines

## Usage in Claude Code

These skills are designed to be used with Claude Code:

1. **React Best Practices**: Use when optimizing React/Next.js apps, reviewing performance, or refactoring components
2. **UI Design System**: Use when creating design systems, maintaining visual consistency, or handing off designs to developers
3. **Canvas Design**: Use when building canvas-based applications or implementing custom rendering

## License

- **React Best Practices**: MIT (Vercel Engineering)
- **Canvas Design**: OFL 1.1 (Font licenses) + MIT (Design assets)
- Individual font licenses included in respective directories

## Organization

```
my-agentic-resources/
├── react-best-practices/
│   ├── SKILL.md
│   ├── references/
│   │   ├── react-performance-guidelines.md
│   │   └── rules/
│   │       ├── [40+ optimization rules]
│   │       └── [_template.md, _sections.md]
│
├── ui-design-system/
│   ├── SKILL.md
│   └── scripts/
│       └── design_token_generator.py
│
├── canvas-design/
│   ├── SKILL.md
│   ├── canvas-fonts/
│   │   ├── [20+ font files]
│   │   └── [Font licenses]
│   └── LICENSE.txt
```

---

**Last updated:** 2026-06-16
