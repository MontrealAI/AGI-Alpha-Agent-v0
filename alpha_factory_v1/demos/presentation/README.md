# Presentation Assets

This directory stores the slide deck and PDF export used in Alpha-Factory demo presentations.
Use the PowerPoint source for edits and regenerate the PDF for distribution or embedding in docs.
Keep filenames stable so linked documentation and release notes continue to resolve.

## Regenerating the PDF

Use a headless conversion tool to refresh the PDF after edits:

```bash
libreoffice --headless --convert-to pdf AGI-Alpha-Agent-v0_Demos_Master_v0.pptx
```

Confirm the exported PDF renders correctly before publishing.
