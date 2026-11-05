# ridgeway-site

The website for Ridgeway, offline topo maps and navigation for trail runners and hikers on
iPhone and Apple Watch: a marketing page, a privacy policy and a support page. This repository is
the website only — the app's Swift source is not here.

Static files, no build step and no dependencies, so it still works in three years when nobody has
run an install command in it. Published with GitHub Pages from `main` at the repository root, on
`ridgeway.enalmar.uk` (`CNAME`).

The app links to `https://ridgeway.enalmar.uk/privacy/` and `/support/` (Settings › About, App
Store Connect, and the contact in the map-tile User-Agent), so those two addresses must not move.

- `index.html` — what the app is. Its CSS and its few lines of script are inline.
- `privacy/`, `support/` — the policy and the help, sharing `assets/page.css`. The words are
  `docs/legal/privacy-policy.md` and `support.md` from the app repository, without the internal
  "Checking this policy" table and the "Published at" lines. Contact: support@enalmar.uk.
- `404.html` — self-contained, with root-relative links, because GitHub Pages serves it at any depth.
- `assets/` — the contour backgrounds, the icons, the social card (`og.jpg`), `shots/` (iPhone
  captures) and `watch/` (Apple Watch captures).
- `tools/shots.py` — turns the raw captures into `assets/shots/` and `assets/watch/`.
- `tools/art/` — the scripts that drew the contours, the route, the icons and the social card.
- `robots.txt`, `sitemap.xml`, `LICENSE`, `.github/workflows/guard.yml` — as in the other app sites.

## Before it goes live

**The App Store link.** The site goes live before the listing exists (App Store Connect needs the
privacy and support addresses), so nothing on it pretends to download. The hero and the closing
section show a plain "Coming to the App Store" pill that is not a link, and the bar has no download
button. The live markup is already in `index.html`, in three comments marked `STAGED`: the bar's
Download, and a "Download on the App Store" text button in the hero and in the closing section. At
launch, delete the two pills, remove those comments' markers, replace `APPLE_ID` with the numeric
Apple ID from App Store Connect, and add `downloadUrl` to the JSON-LD in the head (marked the same
way). The button is plain text; never a home-made copy of Apple's badge. If the official badge is
wanted, it comes from Apple's marketing resources, with their rules (BRAND §3.4).

No price appears anywhere. Ridgeway Plus is priced by the App Store, and the page only says it is
an optional one-time purchase, shared through Family Sharing.

## The look

Its own, not the other app sites': a night survey of the hills.

- **The contours are real.** Helvellyn and Striding Edge from public terrain tiles, every 20 m
  with a 100 m index line (`assets/contours.svg`; `contours-mobile.svg` is a sparser portrait cut
  for phones). The SVG is a CSS mask over coloured layers, so the lines take any colour: pale
  blue-grey everywhere, Ridgeway Blue around the hero. Masks need the SVG on the same origin, so
  preview over HTTP, not `file://`.
- **Motion is small and optional.** Where scroll-driven animations exist (Chrome, Safari 26) the
  contours drift a little as you scroll and the hero's light fades as you leave it; elsewhere a few
  lines of script fade the light and nothing drifts. The hero's route draws itself once, the Trail
  Run and closing profiles draw when they come into view, and sections rise in.
  `prefers-reduced-motion` turns all of that off and shows everything drawn.
- **The route and the profile** are `route.svg` and `route-profile.svg` from `tools/art`, inlined
  in `index.html` (the route without its own local contours, since the page has its terrain).
  They are illustrative: the waypoints are approximate, so they are never presented as a route
  to follow.
- **The devices are CSS**, drawn around the captures: rounded titanium edge, black bezel, the
  Dynamic Island exactly where the captures' own one is (so captures that show it line up), and
  the Digital Crown on the watch. Container units, so one `--w` sets a device's size and
  everything inside scales. No Apple device artwork, no Apple badge artwork.
- **Colours** are BRAND.md's: Night ground, Paper ink, Ridgeway Blue `#409CFF` as the one accent,
  the route's magenta only where the app uses it, and never a blue field. Fonts are the system
  stack in BRAND.md §3.4; nothing is embedded.

## The captures

Real captures of the app, not mock-ups: a Debug build of `feature/trail-run` at `5661f21`, on two
simulators made for the job, "Site iPhone 17 Pro Max" (iOS 26.5) and "Site Apple Watch Ultra 3
(49mm)" (watchOS 26.5), paired. British English, dark appearance (light for the Standard Light
and Minimal Light styles), Ridgeway Plus on, Health history from the app's built-in sample data, location at
Glenridding, and the iPhone status bar set to 9:41. Every map finished loading before its capture.
Race Day has three stops added to the sample route "Helvellyn via Striding Edge": Hole-in-the-Wall,
Helvellyn and Red Tarn, each with a cutoff. Every map-style capture is the same view: the sample
route opened with Library › the route › Show on Map, then the style chosen in Map Style (Minimal
Light was added later from the same build and simulator, the same way).

Things that are true of them, so nobody is surprised:

- The Trail Run dashboard and the watch screens say "Demo": they come from the app's demo mode
  and its screen gallery, which show the real session pages with sample data.
- The watch clock reads 16:20–17:03. watchOS simulators cannot set the status bar, so the
  Next Aid page's ETA 9:43 and cutoff 10:21 sit under a 17:03 clock.
- The You tab's numbers are sample Health history (the page says so), and its full-screen world
  map is Apple Maps, with Apple's credit in the capture.
- There is no Lock Screen capture: the simulator would not lock, and a faked notification would
  not be the app's alert. It needs a real device.

The raw files live outside this repository, in `~/Dev/ridgeway-site-assets-raw/` (`all-phone/` at
1320 × 2868, `site/` for the watch at 400 × 487). To make the site's copies:

```bash
pip3 install pillow           # once
python3 tools/shots.py ~/Dev/ridgeway-site-assets-raw
```

That crops where a tile shows only part of a screen (the turn banner and the route under it, the
climbs, the download card, and the Hiking Pro detail around Helvellyn that sits in a loupe over
its thumbnail, so the style's 10 m contours and crags show at full size), scales iPhone captures to 720 px wide (480 for the map-style thumbnails) and writes
progressive JPEG with optimised tables, quality 84. That is about 40% smaller than the
`sips -s format jpeg` route the other sites use, with no difference visible on the map text at
2x. Watch captures stay PNG, apart from the map page.

JPEG, not AVIF, for the reason in `trackload-site`: `sips` writes a tiled AVIF with an HDR
property that Firefox's parser rejects, and because Firefox does support AVIF a `<picture>` never
falls back to the JPEG. Check any new image format in Firefox before using it here.

If the app's interface changes, retake the captures rather than editing them. Map captures carry
"Map data © OpenStreetMap contributors · © OpenMapTiles · OpenFreeMap" next to them on the page.

## The art

Everything that is not a capture comes from the scripts in `tools/art/`, copied unchanged from
the folder they were written in. They expect to sit at `art/tools/` with their output in `art/`
and the terrain tiles in a sibling `dem-tiles/`, so run them from a scratch folder:

```bash
mkdir -p /tmp/ridgeway-art/art && cp -R tools/art /tmp/ridgeway-art/art/tools
APPICON=<app repo>/App/iOS/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png \
  sh /tmp/ridgeway-art/art/tools/build.sh    # python3, swift, curl and Google Chrome
```

`build.sh` downloads 20 Terrarium elevation tiles around Helvellyn (zoom 13, the same public
source the app uses), stitches and decodes them, draws both contour SVGs by marching squares,
traces the route (hand-placed waypoints, ridge sections snapped to the crest in the terrain) and
its profile, cuts the icons from the app icon (`APPICON=` to point at it), and renders the social
card with headless Chrome. Copy what changed into `assets/`; the route and the profile are
inlined in `index.html`, between the comments that name them.

The social card on the site was rendered with the trail-run-first tagline and saved as JPEG
(quality 88; the PNG is eight times the size):

```bash
python3 -I /tmp/ridgeway-art/art/tools/og.py "Offline maps and navigation<br>for trail runs and hikes."
sips -s format jpeg -s formatOptions 88 /tmp/ridgeway-art/art/og.png --out assets/og.jpg
```

Credit: the terrain is Terrain Tiles (Mapzen, SRTM, GMTED2010, 3DEP, EU-DEM and others), credited
in the footer as "Elevation from public terrain datasets." The OpenStreetMap / OpenMapTiles /
OpenFreeMap credit belongs next to the captures, where map data appears.

## Claims on this page

Every feature named here is in BRAND.md's App Store description (§3.2), PLUS.md (what Ridgeway
Plus adds and what stays free), the Trail Run SPEC's run column, or one of the captures. Max
Battery is not mentioned: it is experimental and hidden in release builds. Numbers that differ
between Hike and Trail Run (how far ahead a climb is announced, for one) are left out rather than
quoted for one mode. Do not add a number that is not in the app.

## Local preview

```bash
python3 -m http.server 8417
```

Then open <http://127.0.0.1:8417/>. The 404 page's root-relative links work there too.

The page weighs about 2.2 MB with every image loaded, 0.6 MB before scrolling: images below the
hero load lazily, and each has its width and height set so nothing shifts.
