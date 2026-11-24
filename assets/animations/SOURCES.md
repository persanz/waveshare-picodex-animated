# Complete animation collection

Upstream: [PokeAPI/sprites](https://github.com/PokeAPI/sprites), pinned at
`c0542f7c51215d9672439012838c99f520596cbd`.
The source directory is `sprites/pokemon/other/showdown`, including its female
variants. That tree is `fd7003b1d05b68e0f632807e18aa12788378abfe`.

`manifest.json` records the source GIF path and Git blob SHA for each artwork
entry, output frame counts, mode, output SHA-256 and pack checksums.

- **sprite**: an upstream animated GIF, fitted inside a 64 × 64 source canvas
  and sampled to at most 64 frames; grouped frame durations are preserved, with
  delays clamped to 60–2,000 ms for the device.
- **artwork_motion**: the original artwork for that exact entry, fitted into a
  64 × 64 canvas and gently moved vertically in six frames. These are not new
  Pokémon poses. This is used where a matching animated sprite is absent or
  the source GIF has only one frame, as requested by the owner.

All 1,538 original artwork entries are retained. Variant names and entry mapping
are checked against the original binary archive, so a missing form is not
silently replaced with another form's sprite.

Pixels are pre-expanded horizontally 3× and encoded as big-endian RGB565.
Each frame is compressed independently with raw DEFLATE and a 512-byte window;
the player expands rows vertically 3× into the existing display framebuffer.
`PAX1` packs group up to 128 `PKA3` animations each, indexed by original artwork
archive position, not species number. This keeps files below GitHub's per-file
limit and avoids loading the catalog or whole animations into device RAM.

Pokémon artwork, sprites and characters belong to their respective owners.
No new license grant over upstream artwork is asserted.
