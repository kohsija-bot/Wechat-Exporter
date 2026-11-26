WeChat Exporter 2.1.2-beta — Media Browser

1. Extract the full source distribution; run RUN.cmd (Python 3.14 x64).
2. Connect to your own WeChat account. Open Media Browser.
3. Choose Current account — all local media, then Scan / Refresh. Keep
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
No automatic V2 key recovery, WXGF/HEVC image conversion or media downloads.
Codec compatibility and Esc shortcuts have not been exercised on Windows.
Preview temporary files are cleaned on normal changes/close, but abnormal
termination can leave temporary files. Exports are not encrypted.
