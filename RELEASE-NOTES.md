# v2.2.0-beta — Modern desktop UI

- Shared presentation tokens in `ui_theme.py`: Light, Dark and System modes.
- Modern spacing, panels, typography, accent actions and focus states.
- Updated conversation workspace and Media Browser with a dedicated preview surface.
- No changes to the existing media codec, image access, or exporter.
- Qt visual smoke tests are provided; Windows rendering not yet verified.

# v2.1.5-beta — image format compatibility

- Reuse existing account access, with bounded real-image check on Refresh image access.
- Share validated raster/WXGF rendering between Media Browser and chat attachment export.
- Remove structural cache trailers without treating thumbnails as originals.
- Render accessible WXGF HEVC as a PNG first frame with a local FFmpeg subprocess, cancellation and time limit.
- Preserve hash checks for matching chat resources.
- No automatic recovery of new image keys, no new process access, no network media downloads.
- Not verified against the user's real V2 files or Windows GUI.

# v2.1.4-beta — existing image access reuse

- Automatically reuse an already saved account-specific Moect image key and XOR value from the default local cache.
- Refresh image access without rescanning media; existing file import remains available.
- No new key recovery, no key persistence, no WXGF conversion.
- Keep v2.1.3 scan and cancellation fixes.
