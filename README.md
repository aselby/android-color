# Color Studio

A free, ad-free coloring book app for Android. Every palette and tool is unlocked.

## Features

- **65 built-in coloring pages** (mandalas, patterns, nature scenes, animals, anime characters, hero-academy heroes, food, space, intricate advanced designs, easy pages for kids),
  generated from the SVG art in `tools/gen_pages.py`.
- **Free coloring**: paint-bucket fill that respects the outlines, a radial "Shine" fill, soft brush,
  pencil and eraser (optionally kept inside the lines), eyedropper, opacity and shade controls,
  28 named palettes plus a full custom color picker and a list of recently used colors.
- **Color by Numbers**: the same pages with every area numbered, a chip row showing what is left,
  highlights for the current number, hints, and completion tracking.
- **Import your own pictures**: turn anime / cartoon art (outline extraction), a photo (edge detection) or a
  scanned sketch into a page. Pick from the gallery inside the app, or share an image to Color Studio from
  any other app.
- Pinch to zoom, undo/redo, automatic progress saving, export to the gallery and share sheet.
- No ads, no accounts, no network access.

## Building

Requirements: JDK 17 and the Android SDK (platform 35, build-tools 35). Point `local.properties` at
the SDK (`sdk.dir=...`).

```bash
export JAVA_HOME=/path/to/jdk-17
./gradlew :app:assembleDebug      # app/build/outputs/apk/debug/app-debug.apk
./gradlew :app:assembleRelease    # signed if keystore/release.jks exists
```

Release signing: create `keystore/release.jks` (alias `colorstudio`, store/key password `colorstudio`),
or edit `signingConfigs` in `app/build.gradle.kts`. The keystore is ignored by git.

## Installing on a phone

Copy the release APK to the phone and open it (allow "install unknown apps" for your file manager or
browser if asked), or with a USB cable: `adb install app/build/outputs/apk/release/app-release.apk`.

## Regenerating the pages

```bash
python3 tools/gen_pages.py            # needs python3, Pillow, cairosvg
```

## Project layout

- `app/src/main/java/com/anthonyselby/coloring/engine` – region labelling, fills, strokes, undo,
  numbers planning and photo-to-line-art conversion.
- `.../data` – page index, palettes, saved work, export.
- `.../ui` – Jetpack Compose screens and the zoomable canvas view.
- `app/src/debug/AndroidManifest.xml` – debug builds render in software so they can be tested on the
  Android emulator, whose GPU translation crashes on this app's large bitmap draws.
