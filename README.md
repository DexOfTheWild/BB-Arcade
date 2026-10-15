# BB-Arcade

Optional cabinet artwork and metadata for ACGC PC Port BB, separate from
[BB-Rentals](https://github.com/DexOfTheWild/BB-Rentals). This repository remains
private. It contains no ROMs, BIOS, emulator DLLs, save states or player saves.

The launcher **Games** page can install/update the latest stable release, install
a local ZIP, or disable/re-enable the pack. Private downloads require
`ACGC_GITHUB_TOKEN` with read access to this repository. No token is stored in
this repository or its releases. A local release ZIP works offline.

Use **BB-Arcade.zip** and **BB-Arcade.json** from Releases. GitHub source archives
are not installable packs. The launcher verifies ZIP/asset hashes, stages an
immutable installation and atomically selects it. Restart to apply. The previous
pointer is preserved, and failed installations keep the current pack active.

## Cabinets

| Cabinet | State | Furniture / content | Player-supplied ROM shortname |
|---|---|---|---|
| TMNT | Integrated | 1371 / 1 | `tmnt.zip` |
| Ms. Pac-Man | Integrated | 1372 / 2 | `mspacman.zip` |
| NBA Jam | Integrated | 1373 / 3 | `nbajam.zip` |
| Metal Slug | Integrated | 1374 / 4 | `mslug.zip` |
| Marvel vs. Capcom | Integrated, existing opt-in gate | 1375 / 5 | `mvscu.zip` |
| Ultimate Mortal Kombat 3 | Integrated | 1376 / 6 | `umk3.zip` |
| Mega Man 2: The Power Fighters | Authoring only | Not assigned | `megaman2.zip` |
| Primal Rage | Authoring only | Not assigned | `primrage.zip` |
| Battletoads | Authoring only | Not assigned | `btoads.zip` |

ROM names are descriptive metadata. This pack never scans, downloads, copies,
renames or modifies them and does not change emulator compatibility or readiness.
Authoring entries do not grant furniture, seed rooms or start new sessions.

## Data and assets

`catalog.json` stores stable cabinet keys, titles, integration status, existing
native IDs, informational ROM shortnames, footprint/scale, aspect and mesh paths.
`assets/<key>/` holds OBJ/MTL/PNG files. Integrated cabinets have full models,
split static bodies, separate live screens and adjacent material/texture files.
Artwork is stylized fan art; reference photographs and extracted game data are
not included. New models need deliberate engine adapters/identity policy first.

Each engine version pins its integrated geometry and material hashes. Compatible
pack textures override bundled artwork. Changed geometry/materials, damaged files,
missing or disabled packs fall back per cabinet to bundled art. This preserves
the compiled screen vertices, furniture origins/collision and lighting emitters.
The pack cannot change native IDs, saves, schedules, ROM routing or core binaries.
Geometry/material changes require a corresponding engine compatibility update;
texture-only revisions can ship independently.

## Release

Python 3.10+ standard library only:

```sh
python -m unittest test_build_pack
python build_pack.py
```

The deterministic ZIP has `pack.json` and only its listed assets. The descriptor
records repository, tag, archive size and SHA-256; `pack.json` records per-file
size/hash. Limits are 128 cabinet records, 1024 art files, 16 MiB per file and
128 MiB expanded. PNGs may be 4..4096 per axis; the game fits them to its existing
GPU caches once. Traversal, links, unexpected extensions and unlisted references
are rejected. Source/workflow/tests are not installed into the game.

Commit the version update, then push its matching `v<version>` tag. GitHub Actions
tests, builds and publishes the two release assets. The main project's
`tools/prepare_bb_arcade.py` refreshes the local authoring handoff and the compiled
compatibility records; it does not publish or run a native game build.
