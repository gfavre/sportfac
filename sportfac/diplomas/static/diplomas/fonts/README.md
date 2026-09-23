# Diploma font dependencies

BrushScriptMT.ttf is the BRUSHSCI.TTF file supplied by the project owner
on 2026-09-22. It replaces BrushScript Regular as the default for labels and years. Its licence is separate from
the OFL files below; those licences apply only to Courgette and Kalam.
The earlier BrushScript-Regular.ttf was round-tripped with fontTools.ttLib.TTFont.save to
normalize its tables/timestamps: Chromium rejected the original file. Glyphs
are unchanged; the resulting PDF was checked to embed BrushScript explicitly.

Vendored TrueType fonts from Google Fonts (SIL Open Font License, see adjacent files):
- Courgette Regular: https://github.com/google/fonts/tree/main/ofl/courgette
- Kalam Bold: https://github.com/google/fonts/tree/main/ofl/kalam

SegoeScript-Bold.ttf is the Segoe Script Bold file supplied by the project owner
on 2026-09-22 and is the default for red values. Its licence is separate from OFL.
Courgette and Kalam are retained as optional alternatives.
The reference embeds Brush Script MT for labels/years and Segoe Script Bold for values.
Do not redistribute those proprietary fonts without the appropriate licence.

The renderer embeds these files as data URLs so PDF generation needs no external font requests.
To use licensed originals, configure absolute TTF paths with KEPCHUP_DIPLOMA_LABEL_FONT
(Brush Script MT) and KEPCHUP_DIPLOMA_TEXT_FONT (Segoe Script Bold) on the server.
