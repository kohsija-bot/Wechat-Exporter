WeChat Exporter 2.2.0-beta — Media Browser

1. Extract the full source distribution; run RUN.cmd (Python 3.14 x64).
2. Connect to your own WeChat account. Open Media Browser.
3. Choose Current account — known media folders, then Scan / Refresh. Keep
   Available only unchecked to see locked and unverified media.
4. Select a row for preview. Video playback depends on the available codec.
   Files with nonstandard suffixes are prepared in a temporary local folder.
5. Check files and Export checked, or Export all visible. The latter follows
   the current filters. manifest.json records saved and skipped files.
6. Press Esc or Cancel (Esc) to stop an active operation. Cancellation is
   cooperative; blocking I/O and codec calls can take time to return.

V2 IMAGES
The Moect source has separate account-image-key recovery functionality.
This application includes offline V2 DAT decoding using a matching image key
that the user already has, not automatic recovery of new image keys.
If you have a key file from your own authorized Moect account, connect to the
same account, open Media Browser and click Import V2 image key. Select its
existing image-keys.json or media-key.bin. Moect stores its media cache under
its configured application/cache data root. The key is not exported, logged
or persisted by this app. No key is required for ordinary videos/plain images.
V2 key supplied means a key is present, not that the file is verified. Some
V2 files still fail (wrong key, XOR layout, corrupt or unsupported WXGF).
Do not share key files. Without a matching key, use WeChat's Save As and
browse the saved folder instead. Missing remote originals cannot be restored.

CHAT EXPORT
Choose Full and Copy available local media. In addition to XML hashes, this
version checks packed message references and the supported resource database
schema for the same conversation/server ID. Content hash matching remains
mandatory to prevent incorrect cross-chat attachments. Some resources will
still be missing. Media Browser operates independently of chat associations.

LIMITATIONS
No automatic V2 key recovery or media downloads. WXGF first-frame conversion is supported with FFmpeg.
Codec compatibility and Esc shortcuts have not been exercised on Windows.
Preview temporary files are cleaned on normal changes/close, but abnormal
termination can leave temporary files. Exports are not encrypted.

2.1.3: Fix QDialog.finished / QThread.finished collision; target known media
folders with scandir; retain imported JSON XOR byte; no full rescan on key import.
To search an unusual folder, choose Choose a local folder. A key is still needed
for V2 files; no automatic key recovery or WXGF conversion is included.

## 2.1.4: automatic reuse of existing image access
For the selected account, the app checks only the account-specific default Moect/legacy cache on Connect and Media Browser scan. Use Refresh image access after using Moect for the same account. Custom cache paths require the existing file import. No new key recovery, process access added, key persistence, or guarantee of decryption. WXGF was unsupported in v2.1.4 (see v2.1.5 below).

## 2.1.5: local image rendering compatibility
- Shared raster validation and cache trailer removal based on Moect's raster_payload.
- Already accessible WXGF HEVC images can be rendered as PNG first frames via local FFmpeg. A first frame is not the original animated image; the preview and export manifest identify this quality.
- FFmpeg is installed as a local dependency with RUN.cmd (imageio-ffmpeg); an existing system FFmpeg is also supported. Conversion is bounded and cancellable.
- Existing account image access is reused as before. Refresh image access checks up to three existing V2 files and reports whether a sample actually opens. No new access is recovered, no keys are written or transmitted, and no process access is added.
- Chat exports verify the original content hash before rendering. Missing or encrypted images without matching access still cannot be opened.
- Synthetic tests cover complete raster boundaries, HEVC first-frame conversion and export; real Windows GUI and V2 recovery remain unverified.

## 2.2.0: Fluent-inspired desktop UI

Shared light/dark/system theme, emerald accent, clearer section hierarchy, chat and preview panels, primary actions, and denser media table without vertical grid lines. Native window chrome and existing workflow remain. No new dependencies or media engine changes. The System option follows the OS palette captured at startup.
