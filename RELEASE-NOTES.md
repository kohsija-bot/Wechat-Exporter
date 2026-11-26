# v2.1.2-beta — Media preview and cancellation

- Escape shortcut in main window and Media Browser; cancellation checks during database copies, validation, message queries and media preview.
- Image preview runs in a worker; nonstandard video cache suffixes get a temporary playable filename.
- Offline V2 DAT decoder can accept an explicitly imported existing image key; raster validation uses Pillow. No automatic image-key recovery is included.
- Chat export checks packed metadata and matching resource DB rows, retaining content-hash verification.
- Python source distribution only. Windows live GUI and video codec tests remain outstanding.
