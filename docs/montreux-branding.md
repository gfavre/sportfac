# SSF Montreux logos

The seasonal SSF deployments use `sportfac.settings.montreux` (autumn) and
`sportfac.settings.montreux_ski` (winter). Local settings use the autumn theme.
EPA and PassVac are separate themes and retain their existing branding.

`KEPCHUP_LOGO` selects the logo for shared invoice/print templates and practical
reminder emails. It is exposed by `kepchup_context`, including in background PDF
rendering. Other deployments keep the default `img/logo.png`.

The SSF settings also set `KEPCHUP_DIPLOMA_LOGO`. An explicit `site__DIPLOMA_LOGO`
preference takes precedence; generated diploma batches freeze their own logo.
Previously generated PDFs and archived emails are not rewritten.

Shared static assets:

- `img/montreux-ssf-logo-dark-2026.png`: black lettering for light backgrounds.
- `img/montreux-ssf-logo-white-2026.png`: white lettering for dark backgrounds.
- `img/montreux-ssf-2026/`: square browser/mobile icons and their manifest.

The main transparent PNGs are resized proportionally to 1200 px wide. Templates
bound display widths: 240 px for footers/invoices, 200 px for print headings and
reminders, and 4.5 cm above the address in mailer PDFs. Browser icons use white
lettering on dark browser themes. The seasonal base templates and autumn splash
share `ssf-favicons.html`.

New filenames bypass existing static caches; seasonal footer fragments use the
new `footer-ssf-logo-2026` cache key. Keep historical image assets available for
archived messages and explicit staff preferences. Deploy with the normal static
collection and application restart.

## Local theme previews

Write a theme directory name in `.dev-theme` at the repository root, for example
`montreux_ski`, `montreux_epa`, `montreux_passvac` or `vevey`, then restart runserver.
This file is ignored by Git. Alternatively set `KEPCHUP_DEV_THEME=montreux_ski` in
the terminal or PyCharm run configuration; the environment variable takes precedence.
Without either selection, local settings keep the Montreux autumn theme.

Only local settings read this selection, once at startup. It switches template
and static directories, default logos and diploma palette. It does not import
production settings or change the database, SSO, tenant, permissions or feature
flags. Template fragments use a dedicated local memory cache so old footer markup
does not survive a theme switch; the default cache is preserved. Existing static collections may need rebuilding if the development server
serves collected files rather than Django's staticfiles finder.

SSF Montreux diplomas use anthracite text with lime-green stars and borders;
other themes retain their existing blue/red palette. Generated PDFs are not
recolored until regenerated.

## Web palette

Autumn, winter and the autumn splash page load the shared
`css/ssf-montreux-2026.css` after the base styles and seasonal layout stylesheet.
The old Pom/Royal theme stylesheets are no longer added on those pages. Other
deployments retain their own stylesheets.

Edit `sportfac/static/scss/themes/ssf-montreux.scss`, then rebuild from the
repository root with `npm run build:montreux-theme`. This command requires the
`sass` executable (Dart Sass; validated with the locally installed 1.15.3).
Commit both the SCSS and generated CSS. No shared legacy bundle rebuild is needed.

The palette uses logo lime for primary actions, anthracite text and navigation,
dark olive links, and neutral secondary actions. Semantic success, warning,
danger and information use deeper green, amber, brick red and slate teal;
their notice backgrounds are pale tints. Hover, active, disabled and keyboard
focus states are defined together with buttons, notices, selection and forms.
New stylesheet filenames and versioned links handle cache refreshes.
