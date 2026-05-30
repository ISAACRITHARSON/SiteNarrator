---
inclusion: always
---

# SiteNarrator — Design System (Implemented)

## Theme: Dark Desktop Software
Navy-based dark theme with amber/gold accents. Feels like Linear, Arc, or VS Code — not a web app.

## Colors (CSS Variables)
- --background: #1a1a2e (deep navy)
- --surface: #16213e (slightly lighter)
- --card: #1f2b47 (card backgrounds)
- --foreground: #e8e8e8 (light text)
- --foreground-muted: #8892a4 (gray text)
- --primary: #e8a830 (amber/gold)
- --primary-hover: #d4891f (darker gold)
- --border: #2a3a5c (subtle borders)
- --success: #4caf50 (green)
- --destructive: #ef5350 (red)
- --sidebar-bg: #0f1629 (darkest)

## Typography
- Font: Inter (Google Fonts)
- Headings: font-bold, tracking-tight
- Body: text-sm, leading-relaxed
- Labels: text-xs, uppercase, tracking-wide

## Layout
- Fixed sidebar (240px) with navigation
- Active nav item: amber background, dark text
- Project card in sidebar with amber accent
- Main content area with max-width constraints
- Rounded corners (rounded-xl, rounded-lg)

## Components
- Cards: rounded-xl, var(--card) bg, var(--border) border
- Buttons: rounded-full, amber primary, border for secondary
- Inputs: rounded-xl, var(--input-bg), var(--input-border)
- Status badges: colored backgrounds with matching text
- Collapsible accordions for detailed data

## What to AVOID
- Light/white backgrounds
- Cold corporate blue
- Flat gray
- Sharp corners
- Enterprise dashboard aesthetic
