# WeChat Exporter

Independent lightweight Windows utility for exporting your own locally available WeChat 4.x conversations and media. Python 3.14 + PySide6 (Qt 6). No cloud, scheduler, background service or telemetry.

**Version 2.2.0-beta — Python source only.** No EXE, installer or automated build is provided.

## Quick start

1. Install [Python 3.14 x64](https://www.python.org/downloads/windows/) if needed.
2. On GitHub choose **Code → Download ZIP**, then extract the entire archive.
3. Sign in to your own WeChat Desktop 4.x account.
4. Double-click `RUN.cmd`. On first use it creates a local `.venv` and installs dependencies from PyPI; Internet access is needed for this step.
5. Click **Connect WeChat**, select conversations, choose a format, then export. Use **Media Browser** for independent media browsing and export.

To try the app without a real account, choose **Open archive** and select `demo_archive` (synthetic data only).

### Manual startup

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Features

- Conversation filters, preview, keyword search, date ranges and batch export.
- TXT, Markdown, CSV, Excel, JSON, JSONL and offline HTML; optional ZIP.
- Quick text-only mode and full message mode including supported quoted and forwarded records.
- Media Browser: local account cache, selected conversation attachment folder or user-selected folder; image preview, video playback where supported, filters and selected/all visible export.
- Progress, Esc cancellation, manifests and system/light/dark themes. English UI.

## Limits and privacy

Only locally available history and media can be exported. Missing originals, V2 DAT images without a matching imported image key and unverified attachments cannot be recovered. Conversation media scope does not guarantee a complete message-to-file mapping. Voice blobs may remain SILK; video playback depends on codecs. Exports and ZIP archives are unencrypted. A readable temporary database snapshot is removed on normal close but may remain after a crash. Only use your own or authorized accounts. No Tencent affiliation.

The app is a beta. Synthetic unit tests do not establish compatibility with every Windows or WeChat version. See `README.txt` and `README-MEDIA.txt` for detailed guidance. Keep your working version as a fallback.

## Development

After the initial dependency installation, run `TEST.cmd` or `.venv\Scripts\python.exe -m unittest discover -v` to execute the tests. No compilation is required; anyone who wants a binary may package the source independently, subject to applicable licenses.

## License and attribution

GPL-3.0. Includes modified modules from [Moect](https://github.com/mofan6/Moect) v1.3.2. See `LICENSE` and `MOECT-THIRD-PARTY-NOTICES.md`. Original notices are retained; those notices also describe upstream components not bundled here. Python, Qt/PySide6 and other dependencies retain their respective licenses.

### Media discovery update
Account-wide Media Browser scans known media directories in the selected account, including cache, recognizes file signatures despite unusual extensions, and shows encrypted V2 files by default. Use Available only to hide locked files. Chat exports still require verified matching. V2 decoding can use an existing user-supplied Moect image-key file; this version does not recover new image keys. See the media guide.

### Media recovery and cancellation
Press **Esc** or **Cancel (Esc)** while scanning, reading previews, preparing snapshots or exporting. Cancellation is cooperative; a codec or a blocking disk operation may need to return before cancellation completes. Image preview decoding and temporary video preparation run in a worker. V2 image keys are held in memory only, scoped to the connected account. A supplied key is not a guarantee of successful decoding.

### 2.1.3 hotfix
Fixes the Qt worker signal collision, scans known media folders using `os.scandir`, and retains the optional XOR byte in an existing user-supplied image key JSON. Importing a key does not rescan the account. WXGF conversion and Windows GUI validation remain outstanding.

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
