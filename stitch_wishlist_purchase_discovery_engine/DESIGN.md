---
name: InsightStream Canvas
colors:
  surface: '#fff8f7'
  surface-dim: '#f0d3d5'
  surface-bright: '#fff8f7'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fff0f0'
  surface-container: '#ffe9ea'
  surface-container-high: '#ffe1e3'
  surface-container-highest: '#f9dcdd'
  on-surface: '#271719'
  on-surface-variant: '#5b4042'
  inverse-surface: '#3e2c2e'
  inverse-on-surface: '#ffeced'
  outline: '#8f6f72'
  outline-variant: '#e3bdc0'
  surface-tint: '#bc0543'
  primary: '#8d002f'
  on-primary: '#ffffff'
  primary-container: '#b90041'
  on-primary-container: '#ffc7cc'
  inverse-primary: '#ffb2ba'
  secondary: '#5a5d73'
  on-secondary: '#ffffff'
  secondary-container: '#dcdef8'
  on-secondary-container: '#5e6177'
  tertiary: '#004f3c'
  on-tertiary: '#ffffff'
  tertiary-container: '#006951'
  on-tertiary-container: '#92e5c7'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffd9dc'
  primary-fixed-dim: '#ffb2ba'
  on-primary-fixed: '#400011'
  on-primary-fixed-variant: '#910031'
  secondary-fixed: '#dfe1fb'
  secondary-fixed-dim: '#c3c5de'
  on-secondary-fixed: '#171a2d'
  on-secondary-fixed-variant: '#42465a'
  tertiary-fixed: '#9ff3d4'
  tertiary-fixed-dim: '#83d6b9'
  on-tertiary-fixed: '#002117'
  on-tertiary-fixed-variant: '#00513e'
  background: '#fff8f7'
  on-background: '#271719'
  surface-variant: '#f9dcdd'
  background-warm: '#fff8f7'
  surface-card: '#ffffff'
  success-data: '#03a685'
  warning-data: '#fa9e59'
  error-data: '#ba1a1a'
  info-data: '#1d85ff'
  border-subtle: '#e3bdc0'
  text-muted: '#535766'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-sm:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 12px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 8px
  sm: 16px
  md: 24px
  lg: 32px
  xl: 48px
  margin-mobile: 16px
  margin-desktop: 32px
  gutter: 24px
  container-max: 1440px
---

## Brand & Style

InsightStream Canvas is a sophisticated consumer research platform designed for product managers and researchers. The brand personality is **analytical yet empathetic**, bridging the gap between raw data and human sentiment. 

The visual style is **Soft-Institutional**, a hybrid of **Modern Corporate** and **Minimalism**. It utilizes a warm, "paper-like" background to reduce eye strain during long research sessions. The interface relies on clean structural lines, subtle glassmorphism for navigation, and a high-fidelity color palette that uses temperature to indicate data significance. It feels precise, trustworthy, and airy, avoiding the "heavy" feel of traditional enterprise dashboards.

## Colors

The palette is anchored by a warm-white background (`#fff8f7`) that provides a soft canvas for high-contrast data visualization. 

- **Primary (`#b90041`):** A deep berry-red used for brand presence, primary actions, and high-intensity data points.
- **Secondary (`#5a5d73`):** A cool slate-blue used for utility icons and secondary structural elements.
- **Semantic Colors:** Green (`#03a685`), Orange (`#fa9e59`), and Red (`#ba1a1a`) are used strictly for confidence scores and priority status.
- **Neutral Surfaces:** We use a tier of "Surface Containers" that move from pure white for the lowest elevation (content cards) to slightly tinted pink-greys for background grouping.

## Typography

The system uses **Inter** exclusively to maintain a utilitarian, highly legible, and neutral tone. 

The hierarchy relies heavily on **letter spacing** and **casing** for categorization. `Label-sm` and `Label-md` are often used in all-caps with increased letter spacing to denote section headers or metadata labels. `Display-lg` is reserved for "Hero Metrics" to provide an immediate visual anchor for the user. Body text follows a standard 1.5x line-height ratio for optimal readability in dense evidence logs.

## Layout & Spacing

The system follows a **Fixed-Width Content Canvas** centered within a fluid background. 

- **Grid Strategy:** A standard 12-column grid is used for desktop, reflowing to a single column on mobile. 
- **The "Unit" System:** All spacing is derived from a 4px base unit. 
- **Vertical Rhythm:** Sections are separated by `lg` (32px) or `xl` (48px) units to create clear mental breaks between different data visualizations. 
- **Margins:** Desktop views maintain a 32px safe area on the left and right of the viewport, while mobile scales down to 16px.

## Elevation & Depth

Hierarchy is established through **Tonal Layering** and **Ambient Depth**:

1.  **Level 0 (Background):** `#fff8f7` - The base of the application.
2.  **Level 1 (Cards/Containers):** White background with a `1px` border of `outline-variant` (`#e3bdc0`).
3.  **Elevation (Shadow-Ambient):** `0 4px 12px rgba(0, 0, 0, 0.03)` is used for persistent UI elements like the filter bar.
4.  **Interaction (Shadow-Hover):** `0 10px 20px rgba(39, 23, 25, 0.05)` is applied to cards on hover, accompanied by a `-2px` Y-axis translation ("hover-lift").
5.  **Overlays:** Modals use a `50%` opacity `on-surface` backdrop with a `blur(4px)` to pull focus.

## Shapes

The shape language is **Soft-Geometric**. 

- **Standard Containers:** Cards and input fields use a `0.125rem` (2px) radius for a precise, "notched" look.
- **Interactive Elements:** Buttons use a `0.25rem` (4px) radius.
- **Badges & Filters:** Chips and category filters use a **Pill** shape (Full Radius) to distinguish them from structural content containers.

## Components

- **Buttons:** Primary buttons are outlined or ghosted with the primary color. They feature a `transition-colors` effect and `label-md` typography.
- **Metric Cards:** Large-format typography (`headline-lg`) centered or left-aligned within a Level 1 container. They should include a subtle `label-md` description at the top.
- **Filters:** Pill-shaped, light-bordered containers. On hover, the border-color transitions to the primary brand color.
- **AI Input:** A pinned bottom bar with `glassmorphism` (90% white, 12px blur). It includes a leading icon in the primary color and suggested prompt "chips" above the input field.
- **Evidence Logs:** Stacked cards within a Level 2 container (modal). Each log entry uses a light semantic background (e.g., light red for YouTube, light orange for Reddit) to indicate the source at a glance.
- **Progress Bars:** Use a `surface-container-high` track with a primary-colored fill. Fill opacity should be stepped (100%, 80%, 60%) for multi-bar comparisons.