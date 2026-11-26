# WeChat Exporter

Independent lightweight Windows utility for exporting your own locally available WeChat 4.x conversations and media. Python 3.14 + PySide6 (Qt 6). No cloud, scheduler, background service or telemetry.

**Version 2.1.2-beta — Python source only.** No EXE, installer or automated build is provided.

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
Account-wide Media Browser scans the selected account including cache, recognizes file signatures despite unusual extensions, and shows encrypted V2 files by default. Use Available only to hide locked files. Chat exports still require verified matching. V2 decoding can use an existing user-supplied Moect image-key file; this version does not recover new image keys. See the media guide.

### Media recovery and cancellation
Press **Esc** or **Cancel (Esc)** while scanning, reading previews, preparing snapshots or exporting. Cancellation is cooperative; a codec or a blocking disk operation may need to return before cancellation completes. Image preview decoding and temporary video preparation run in a worker. V2 image keys are held in memory only, scoped to the connected account. A supplied key is not a guarantee of successful decoding.
