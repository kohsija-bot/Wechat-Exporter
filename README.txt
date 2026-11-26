WeChat Exporter 2.1.2-beta — Windows x64, Python 3.14 + PySide6
========================================================
Independent GPL-3.0 utility, not affiliated with Tencent or Moect.

QUICK START
1. Extract this ZIP into a new folder (keep your earlier working version separately).
2. Open and sign in to your own Windows WeChat 4.x account.
3. Double-click RUN.cmd. First run installs dependencies from PyPI.
4. Connect WeChat, select chats, choose format and output folder.
5. Quick mode exports plain text. Full mode includes parsed message types.
6. Click Export checked chats. Open result opens the output folder.
   For HTML, open index.html or a conversation's chat.html. Keep the entire
   output directory together. For ZIP, extract it before reading HTML.
7. Clear Message keyword to export all messages. This filter applies to all
   selected conversations during export, not just to the preview.
8. Refresh reloads the desktop snapshot. Phone-only history is not included.

DEMO
Open archive > select demo_archive. No WeChat connection is needed for this.
TEST.cmd runs unit tests after the initial dependency installation.

FEATURES
- Single-window English UI, system/light/dark theme, conversation name search,
  private/group filter, latest 100 matching messages, optional local-date range.
- TXT, Markdown, CSV, JSON, JSONL, Excel (XLSX), searchable offline HTML.
- Quick text-only and full message modes; optional local media; ZIP archive.
- Full mode parses quoted replies, forwarded records, links, file/image/voice/
  video/sticker markers, system messages and other types supported by the reader.
- Streaming message output across database shards, cancel, per-batch manifest.
- No scheduler, NAS integration, background service, cloud or telemetry.

LIMITS / PRIVACY
The WeChat connection adapter is based on the v1.0 code; optional media databases
are now included. Windows live connection and the Qt GUI have not been executed
in the development environment. Keep the known-working v1.0 for fallback.
Only chat history locally present in Windows WeChat is available. This is not a
complete account backup and is not a restore utility.
Attachment matching is intentionally conservative: original-content hashes are
required for local cached images, stickers, videos and files. A matching filename
alone is not enough. Missing files and account-key encrypted V2 DAT images are
reported rather than guessed. Legacy XOR/fixed V1 image decoding is included;
its dependency-backed path has not been exercised in this environment. Voice
blobs, when available, are exported in original format (often SILK), not WAV.
Forwarded content may be truncated by parser safety limits. Some system/type
labels from the upstream parser can remain Chinese. Thai UI is not implemented.
Excel limits text cells to 32,767 characters; use JSON/JSONL/TXT for long records.
The HTML viewer loads all exported messages for a conversation in the browser;
for very large chats, choose a date range or JSONL/TXT.
Data processing is local. The first-run package installation requires Internet.
A readable temporary snapshot is created under local application data and removed
on normal close; after a crash it may remain. Exported files are not encrypted.
ZIP compression is not encryption. Do not share archives unintentionally.
Do not run tools against accounts you are not authorized to access.

SOURCE / LICENSE
Includes modified Moect v1.3.2 reader and connection modules, plus offline
image functions and forward parser. Source: https://github.com/mofan6/Moect
See LICENSE and MOECT-THIRD-PARTY-NOTICES.md. Original source notices retained.
The application is distributed as Python source; no Windows EXE is included.

Media Browser: see README-MEDIA.txt for V2 image keys and Esc cancellation.
