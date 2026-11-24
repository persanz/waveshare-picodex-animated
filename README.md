# Waveshare PICODEX Animated

Experimental animated-sprite version of [Waveshare PICODEX](https://github.com/persanz/waveshare-picodex).
Pikachu has a 58-frame animation; other Pokémon retain static artwork.
Current measured playback is about **2.1 fps**, so this is a feasibility prototype.


A standalone, offline Pokémon picture book for the **Waveshare
RP2350-Touch-LCD-1.54**, running MicroPython 1.29. A Pokémon logo and Poké Ball splash shows `Loading....` for five seconds,
then opens the first Pokémon: **no launcher, no app selection, no Virtual Pokemon**.

Includes 1,538 high-resolution 240 × 240 artwork entries, Spanish descriptions,
touch and button controls, motion shuffle and shutdown screen.
There is no battery percentage display or automatic charging popup.

## Controls

- **Left/right third of the screen:** previous/next Pokémon.
- **Left/right hardware button, short press:** previous/next Pokémon.
- **Hold the centre of the artwork for about one second:** read its description.
- **Tap a description:** advance a page; tap the final page to return to the
  exact same artwork. Movement pauses while reading.
- **Hold the right button for two seconds:** return to the first Pokémon.
- **Move gently:** choose a different random Pokémon. Let the device settle
  before shaking again; continuous shaking does not repeatedly change it.
- **Hold the left button for about two seconds:** show `GOODBYE!` and switch off
  on battery. USB can keep the device powered after its screen goes black.

Power-on starts from the first entry. There is no menu to return to, no pet
state or care meters. The startup splash leads straight into PICODEX.

## Files and setup

This repository was separated from the `feature/pikachu-animation` experiment in
[persanz/waveshare-picodex](https://github.com/persanz/waveshare-picodex) at commit
`2960718`. Its full development history is preserved here. The stable static
project remains in that original repository. Both derive from
[persanz/waveshare-pokemon-frame](https://github.com/persanz/waveshare-pokemon-frame)
at `75f1b3c`.

Use MicroPython **1.29, mpy format v6.3**. The board must have a FAT-formatted
microSD card. Place the included `pokemon_hd.dat` on the card at:

```text
/waveshare_pokemon_frame/pokemon_hd.dat
```

Also put `pikachu_animation.dat` in `/waveshare_pokemon_frame/` on the SD card.
The original folder name is retained so an existing artwork SD card can be
reused unchanged. The firmware mounts it at `/sd`.

Copy these files to the board root:

```text
main.py
boot_splash.mpy
boot_splash.dat
lcd.mpy
frame_app.mpy
dex_description.mpy
pikachu_animation.mpy
shutdown_screen.mpy
sdcard.mpy
pokemon_order.bin
pokemon_dex.bin
pokemon_descriptions_es.bin
```

The `lcd.py` source is the preserved Waveshare board driver from the original
project's local board backup. Its compiled module is supplied too. An existing
working `lcd.py` on the board can remain; the firmware uses its `LCD_1inch54` API.
The artwork archive belongs on the SD card, not in the board's internal flash.

Find the port with `uv tool run mpremote connect list`. Back up the current board
files before replacing them. A hardware reset clears an existing watchdog;
interrupt startup before transferring large files. Stage files under temporary
names and verify their SHA-256 checksums before renaming them to activate a set
of changes. Activate `main.py` last, then reset the board.

This repository does not automatically install itself or remove files from an
existing two-app board. The old launcher and companion modules are unused by the
new `main.py`; they do not need to be deleted to run this version.

## Build and checks

The matching `.mpy` firmware modules are included. Rebuild on the host with:

```sh
for module in boot_splash lcd frame_app dex_description pikachu_animation shutdown_screen sdcard; do
  uv tool run --from mpy-cross mpy-cross "$module.py"
done
python3 -m unittest discover -s tests -v
python3 validate_assets.py
```

`main.py` remains source. Allocate the 115,200-byte display buffer before loading
the app; `gc.threshold(1024)` and compiled modules are important for heap space.
The display uses byte-swapped RGB565 (for example red is `0x00f8`).

Rebuild the Spanish binary database from its included JSON with:

```sh
python3 build_descriptions.py
```

The JSON retains per-entry translation provenance. Artwork archive format:
32-bit entry count, then 16-byte entries `(art_id, offset, compressed_size,
name_offset)`; bodies are raw DEFLATE with a 1 KiB window, yielding 115,200 bytes
of RGB565 data. `pokemon_order.bin` maps National Pokédex order to archive indices;
`pokemon_dex.bin` maps alternate-form IDs to displayed species numbers.

Hardware regression scripts in `tests/hardware_description_*.py` use simulated
inputs with a real board, LCD and SD card. Compile and upload them as `.mpy`
modules before importing them. Host tests do not substitute for physical touch,
button, SD-card and power checks. The standalone firmware has been installed on the board. Simulated-input
on-board checks passed for byte-identical description return and shutdown
control flow despite failing touch reads. Physical power cutoff requires owner
handling.

## Power and memory

USB charging is handled by the board hardware. PICODEX does not display charge
percentages, monitor the charger-status GPIO, or write startup battery logs.
The left button still controls shutdown. USB can keep the board powered after
the screen switches off.

Description return restores a flash-backed artwork snapshot, avoiding the
previous low-memory decompression failure. Power handling precedes touch
rendering, and shared I2C reads have a 50 ms timeout.

## Rebuild the startup splash

The original splash assets and attribution are in `assets/splash/`. To rebuild:

```sh
uv run --with pillow --with resvg-py python build_boot_splash.py
```

The splash reuses the existing framebuffer and its module is unloaded before
PICODEX imports, preserving heap space for artwork. Missing or incomplete
splash data is logged and PICODEX still starts. On-board startup verification
confirmed a 5,003 ms splash followed by the first artwork, with no menu.

## Sources and rights

Artwork and names originate from PokeAPI's official-artwork collection. Spanish
text and translation provenance are retained from the source project. The SD
and Waveshare display driver sources retain their existing notices. No new
license grant is asserted over upstream material. Pokémon artwork, names and
trademarks belong to their respective owners.

## Pikachu animation prototype

Pikachu (#25) uses an optional 58-frame pixel animation. Other entries retain static artwork. Playback pauses during a centre
hold and while reading descriptions; returning restores the held frame before
animation resumes. A missing/invalid animation keeps Pikachu static.

Rebuild the compact asset on the host:

```sh
uv run --no-project --python 3.11 --with pillow python build_pikachu_animation.py
uv tool run --from mpy-cross mpy-cross pikachu_animation.py
uv tool run --from mpy-cross mpy-cross frame_app.py
```

Upload `pikachu_animation.mpy` and the updated `frame_app.mpy` to the board root.
Place `pikachu_animation.dat` on the SD at
`/waveshare_pokemon_frame/pikachu_animation.dat`. Normal startup still begins
with the first Pokémon; `frame_app.start(..., initial_index=37)` starts a
one-session Pikachu demo for this archive/order. This does not persist a new
startup selection.

The asset is 47,253 bytes (about 46 KiB), with pre-expanded horizontal rows
and independent raw-DEFLATE frames (512-byte window).
The player repeats each row vertically into the existing framebuffer to display
150 × 138 pixels, using one 300-byte row buffer plus decoder memory. It never buffers the entire
animation or allocates another framebuffer. Firmware/code also consumes heap.
The source GIF, blob hash and attribution are in `assets/animated/SOURCES.md`.
See `tests/hardware_pikachu_animation.py` for the board playback/description test.

On-board prototype checks passed animation playback, pausing for a description,
and restoring the held frame before resuming. The measured integrated rate was
approximately **2.1 frames/second**, below the GIF's intended 5–10 fps; playback
is a feasibility test, not yet smooth game-speed animation. Minimum free heap
in the instrumented test was 3,664 bytes. Six host tests passed. The static
artwork archive is unchanged. The experiment is maintained in this separate repository, independently of the
stable static PICODEX project.
