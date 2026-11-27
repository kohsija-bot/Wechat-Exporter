"""Optional GUI smoke test; run offscreen or on Windows with Qt installed."""
import importlib.util, os, unittest
from unittest.mock import patch

@unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 not installed')
class ThemeSmoke(unittest.TestCase):
    def test_both_windows_and_theme_modes(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QSettings
        import main, media_browser, ui_theme
        app=QApplication.instance() or QApplication([])
        with patch.object(main,'QSettings',lambda *_: QSettings(QSettings.Format.IniFormat,QSettings.Scope.UserScope,'WeChatExporterTest','UI220')):
            w=main.Window();d=media_browser.MediaBrowser(w)
            try:
                for name in ('Light','Dark','System'):
                    w.apply_theme(name);app.processEvents()
                    self.assertIn('QPushButton',app.styleSheet())
                    self.assertEqual(w.connect.property('role'),'primary')
                    self.assertEqual(d.scan_btn.property('role'),'primary')
                    self.assertTrue(w.grab().width()>0)
                    self.assertTrue(d.grab().width()>0)
            finally:
                d.close();w.close();app.processEvents()
