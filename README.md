# WeChat Exporter

An independent, lightweight Windows utility for exporting your own locally available WeChat 4.x conversations and media. Built with Python 3.14 and PySide6 (Qt 6). No cloud, scheduler, background service or telemetry.

**Version 2.1.0-beta — Python source distribution.** No executable or automated build is provided.

## Quick start

Once the source import is complete, download the repository using **Code → Download ZIP**, extract it, and double-click `RUN.cmd`. Requires Windows 10/11 x64 and Python 3.14 x64. The launcher creates a local virtual environment and installs the required packages on first use.

Sign in to WeChat Desktop, click **Connect WeChat**, select conversations, and export. Use **Media Browser** to preview and export locally available images and videos.

## Features

- Conversation search, preview, date range and batch export.
- TXT, Markdown, CSV, Excel, JSON, JSONL and offline HTML.
- Media Browser with image preview, codec-dependent video playback, and selected/all visible media export.
- Local processing, progress, cancellation and export manifests.

## Limitations

Only locally available chat history and media can be exported. Some encrypted V2 images, missing originals and unverified attachments cannot be recovered. Export files are unencrypted. A readable temporary database snapshot may remain after an abnormal termination. Use only your own or authorized accounts. Windows live compatibility and media playback are not fully verified.

## License and attribution

GPL-3.0; includes modified modules from [Moect](https://github.com/mofan6/Moect). Independent project, not affiliated with Tencent or Moect. Full third-party notices accompany the application source.

**Repository status:** Source import is pending; `RUN.cmd` and the application files are not available in this repository yet.
