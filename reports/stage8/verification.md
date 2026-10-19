# Stage 8

Implemented the local React shell, shared retro window/control components, #727eba accent, gray bevels, white workspaces and responsive 55/45 panel grid. Sensor values are controlled drafts with synchronized integer inputs, explicit connectivity/fault mode and no automatic submission. Placeholders are explicitly labelled; live hardware integration belongs to Stage 9.

TypeScript/Vite production build and actual Vite HTTP startup passed. Browser verification covers native numeric/slider controls and keyboard focus. `frontend/qa-layout.html` is a development-only iframe fixture for exact CSS viewport checks; it is not a production build entry.

Actual iframe CSS viewports1366x768 and1920x1080 produced two grid columns;568px produced stacked panes. Native numeric71 then slider ArrowRight produced72 in both controls. Screenshots are scaled iframe previews, not native desktop-resolution captures. Main actions are sticky within the scrollable control pane.
