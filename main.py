"""Simple English Qt desktop interface for local chat text exports."""
import sys, traceback, shutil, threading
from datetime import datetime, timedelta
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QDate, QSettings, QTimer
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QLineEdit,QListWidget,QListWidgetItem,QPlainTextEdit,QFileDialog,QComboBox,QCheckBox,QDateEdit,QProgressBar,QMessageBox,QSplitter,QInputDialog)
from reader import open_archive,sessions,messages,TZ
from rich_export import batch, FORMATS
from PySide6.QtGui import QDesktopServices, QPalette, QColor, QShortcut, QKeySequence
from PySide6.QtCore import QUrl
import live
import ui_theme as ui

class Cancelled(Exception): pass
class Worker(QThread):
    result=Signal(object); error=Signal(str); progress=Signal(int,int); status=Signal(str); cancelled=Signal()
    def __init__(self,fn,parent=None):
        super().__init__(parent);self.fn=fn;self.stop=threading.Event()
    def check(self):
        if self.stop.is_set():raise Cancelled()
    def run(self):
        try:self.result.emit(self.fn(self.progress.emit,self.status.emit,self.check))
        except Cancelled:self.cancelled.emit()
        except Exception as e:self.error.emit(str(e) or type(e).__name__)

class Window(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('WeChat Exporter | v2.2.0 Beta • Local workspace');self.resize(1180,800)
        self.worker=None;self.root='';self.wxid='';self.owned=False;self.account=None;self.pending=None;self.settings=QSettings('LocalTools','WeChatExporterV2');self.last_output='';self.image_keys=() 
        w=QWidget();self.setCentralWidget(w);v=QVBoxLayout(w);v.setContentsMargins(22,18,22,18);v.setSpacing(10)
        title=ui.label('WeChat Exporter','title');v.addWidget(title)
        v.addWidget(ui.label('LOCAL WORKSPACE  /  Chat history & media  ·  Offline','muted'))
        top=QHBoxLayout();self.connect=ui.role(QPushButton('Connect WeChat'),'primary');self.connect.clicked.connect(lambda:self.detect());self.browse_data=QPushButton('Browse data folder');self.browse_data.clicked.connect(self.choose_data);self.open=QPushButton('Open archive');self.open.clicked.connect(self.choose);self.refresh=QPushButton('Refresh');self.refresh.clicked.connect(self.reconnect)
        self.media_browser=QPushButton("Media Browser");self.media_browser.clicked.connect(self.open_media_browser)
        for btn in (self.connect,self.browse_data,self.open,self.refresh,self.media_browser):top.addWidget(btn)
        top.addStretch();self.theme=QComboBox();self.theme.addItems(["System","Light","Dark"]);self.theme.setCurrentText(self.settings.value("theme","System"));self.theme.currentTextChanged.connect(self.apply_theme);top.addWidget(self.theme);v.addLayout(top);self.source=QLineEdit();self.source.setReadOnly(True);self.source.setPlaceholderText('No account or archive connected');v.addWidget(self.source)
        self.warning=QLabel('');self.warning.setWordWrap(True);ui.role(self.warning,'warning');v.addWidget(self.warning)
        split=QSplitter();lv=QVBoxLayout();lv.setContentsMargins(12,12,12,12);lv.setSpacing(8);left=ui.panel(lv);lv.addWidget(ui.label('Conversations'));self.search=QLineEdit();self.search.setPlaceholderText('Search name or ID');self.search.textChanged.connect(self.filter);lv.addWidget(self.search);self.category=QComboBox();self.category.addItems(["All chats","Private chats","Groups"]);self.category.currentTextChanged.connect(lambda _:self.filter(self.search.text()));lv.addWidget(self.category);self.list=QListWidget();self.list.currentItemChanged.connect(self.preview);lv.addWidget(self.list);b=QHBoxLayout()
        self.select=QPushButton('Select visible');self.select.clicked.connect(lambda:self.check(Qt.CheckState.Checked));b.addWidget(self.select);self.clear=QPushButton('Clear all');self.clear.clicked.connect(lambda:self.check(Qt.CheckState.Unchecked));b.addWidget(self.clear);lv.addLayout(b);split.addWidget(left)
        rv=QVBoxLayout();rv.setContentsMargins(14,12,14,12);rv.setSpacing(8);right=ui.panel(rv);rv.addWidget(ui.label('Message preview'));rv.addWidget(ui.label('Latest 100 matching messages','muted'));queryrow=QHBoxLayout();self.keyword=QLineEdit();self.keyword.setPlaceholderText('Message keyword (preview and export)');self.keyword.returnPressed.connect(lambda:self.preview(self.list.currentItem(),None));queryrow.addWidget(self.keyword);self.find=QPushButton('Find');self.find.clicked.connect(lambda:self.preview(self.list.currentItem(),None));queryrow.addWidget(self.find);rv.addLayout(queryrow);self.text=QPlainTextEdit();self.text.setReadOnly(True);self.text.setPlaceholderText('Select a conversation to preview.');rv.addWidget(self.text);split.addWidget(right);split.setHandleWidth(10);split.setSizes([340,780]);v.addWidget(split,1)
        v.addWidget(ui.label("Export settings"));date=QHBoxLayout();self.use_dates=QCheckBox('Filter export dates (local time)');self.start=QDateEdit(QDate.currentDate().addMonths(-3));self.end=QDateEdit(QDate.currentDate());self.start.setCalendarPopup(True);self.end.setCalendarPopup(True);self.start.setDisplayFormat('yyyy-MM-dd');self.end.setDisplayFormat('yyyy-MM-dd');date.addWidget(self.use_dates);date.addWidget(self.start);date.addWidget(QLabel('to'));date.addWidget(self.end);date.addStretch();v.addLayout(date)
        options=QHBoxLayout();self.mode=QComboBox();self.mode.addItems(['Quick: text only','Full: all message types']);self.mode.setCurrentIndex(int(self.settings.value('mode',0)));self.media=QCheckBox('Copy available local media');self.media.setChecked(True);self.media.setEnabled(self.mode.currentIndex()==1);self.mode.currentIndexChanged.connect(lambda n:self.media.setEnabled(n==1 and self.worker is None));self.zip=QCheckBox('ZIP archive');options.addWidget(self.mode);options.addWidget(self.media);options.addWidget(self.zip);options.addStretch();v.addLayout(options);row=QHBoxLayout();self.folder=QLineEdit(self.settings.value('output',str(Path.home()/'Documents'/'WeChat Export')));browse=QPushButton('Browse');browse.clicked.connect(self.output);self.fmt=QComboBox();self.fmt.addItems(FORMATS);self.fmt.setCurrentText(self.settings.value('format','html'));self.export=ui.role(QPushButton('Export checked chats'),'primary');self.export.clicked.connect(self.do_export);row.addWidget(QLabel('Output'));row.addWidget(self.folder,1);row.addWidget(browse);row.addWidget(self.fmt);row.addWidget(self.export);self.open_result=QPushButton("Open result");self.open_result.setEnabled(False);self.open_result.clicked.connect(self.show_result);row.addWidget(self.open_result);v.addLayout(row)
        foot=QHBoxLayout();self.bar=QProgressBar();self.bar.setRange(0,1);self.bar.setValue(0);foot.addWidget(self.bar,1);self.cancel=QPushButton('Cancel (Esc)');self.esc=QShortcut(QKeySequence('Esc'),self);self.esc.setContext(Qt.ShortcutContext.WindowShortcut);self.esc.activated.connect(self.cancel_job);self.cancel.clicked.connect(self.cancel_job);foot.addWidget(self.cancel);v.addLayout(foot);self.status=QLabel('Sign in to your own WeChat Desktop account, then click Connect WeChat.');self.status.setWordWrap(True);ui.role(self.status,'status');v.addWidget(self.status);self.set_busy(False);self.system_palette=QApplication.palette();self.apply_theme(self.theme.currentText())
    def open_media_browser(self):
        from media_browser import MediaBrowser
        item=self.list.currentItem();chat=item.data(Qt.ItemDataRole.UserRole) if item else None
        account=self.account.get("path") if self.account else None
        dlg=MediaBrowser(self,account,chat,self.folder.text(),self.image_keys,wxid=self.wxid);dlg.exec();self.image_keys=dlg.keys if account else ()
    def apply_theme(self,name):
        self.settings.setValue("theme",name)
        ui.apply(name,self.system_palette)
    def show_result(self):
        if self.last_output:
            p=Path(self.last_output);QDesktopServices.openUrl(QUrl.fromLocalFile(str(p if p.is_dir() else p.parent)))
    def set_busy(self,busy):
        for widget in (self.connect,self.browse_data,self.open,self.media_browser,self.list,self.search,self.select,self.clear,self.category,self.keyword,self.find,self.mode,self.zip,self.fmt,self.folder,self.use_dates,self.start,self.end):widget.setEnabled(not busy)
        self.export.setEnabled(not busy and bool(self.root));self.refresh.setEnabled(not busy and bool(self.account));self.cancel.setEnabled(busy);self.media.setEnabled(not busy and self.mode.currentIndex()==1)
    def job(self,fn,done):
        if self.worker is not None:return
        self.set_busy(True);self.bar.setRange(0,0);self.worker=Worker(fn,self)
        self.worker.result.connect(done);self.worker.error.connect(self.fail);self.worker.progress.connect(self.update_progress);self.worker.status.connect(self.status.setText);self.worker.cancelled.connect(lambda:self.status.setText('Cancelled. Existing exports are preserved.'));self.worker.finished.connect(self.ready);self.worker.start()
    def ready(self):
        old=self.worker;self.worker=None;old.deleteLater();self.set_busy(False);self.bar.setRange(0,1);self.bar.setValue(0)
        if self.pending:
            fn=self.pending;self.pending=None;QTimer.singleShot(0,fn)
    def cancel_job(self):
        if self.worker:self.pending=None;self.worker.stop.set();self.status.setText('Cancelling…');self.cancel.setEnabled(False)
    def fail(self,s):self.status.setText('Operation failed.');QMessageBox.warning(self,'Operation failed',s)
    def update_progress(self,n,total):self.bar.setRange(0,max(total,1));self.bar.setValue(n)
    def detect(self,directory=None):
        self.status.setText('Finding local WeChat account folders…')
        def done(accounts):
            if len(accounts)==1:a=accounts[0]
            else:
                labels=[f"{i+1}. {x['wxid']} — {x['path']}" for i,x in enumerate(accounts)]
                label,ok=QInputDialog.getItem(self,'Select account','Select your signed-in account:',labels,0,False)
                if not ok:self.status.setText('Account selection cancelled.');return
                a=accounts[labels.index(label)]
            self.pending=lambda:self.connect_account(a)
        self.job(lambda p,s,c:live.detect(directory,cancel=c),done)
    def choose_data(self):
        path=QFileDialog.getExistingDirectory(self,'Select WeChat data folder (xwechat_files / account / db_storage)',str(Path.home()))
        if path:self.detect(path)
    def connect_account(self,a):
        self.status.setText('Connecting to the selected local account…')
        def work(p,s,c):
            root,wxid,warning=live.make_snapshot(a,s,c)
            try:
                d=open_archive(root,wxid,cancel=c)
                try:
                    rows=sessions(d,c);wxid=d.wxid or wxid
                finally:d.close()
                from media_catalog import existing_account_image_keys
                keys=existing_account_image_keys(a.get("path"),wxid,c)
                c();return root,wxid,rows,warning,keys
            except BaseException:shutil.rmtree(root,ignore_errors=True);raise
        def done(result):
            root,wxid,rows,warning,keys=result;self.load_rows(root,wxid,rows,True,a,warning)
            if keys:self.image_keys=keys
        self.job(work,done)
    def reconnect(self):
        if self.account:self.connect_account(dict(self.account))
    def clean_snapshot(self):
        if self.owned and self.root:shutil.rmtree(self.root,ignore_errors=True)
    def load_rows(self,path,wxid,rows,owned=False,account=None,warning=''):
        old_checked={self.list.item(i).data(Qt.ItemDataRole.UserRole)['id'] for i in range(self.list.count()) if self.list.item(i).checkState()==Qt.CheckState.Checked} if account and self.account==account else set()
        if self.account!=account:self.image_keys=()
        self.clean_snapshot();self.root=str(path);self.wxid=wxid;self.owned=owned;self.account=account;self.source.setText(f'Connected: {wxid}' if owned else str(path));self.warning.setText(warning);self.list.blockSignals(True);self.list.clear();self.text.clear()
        for r in rows:
            i=QListWidgetItem(r['name']);i.setToolTip(r['id']);i.setData(Qt.ItemDataRole.UserRole,r);i.setFlags(i.flags()|Qt.ItemFlag.ItemIsUserCheckable);i.setCheckState(Qt.CheckState.Checked if r['id'] in old_checked else Qt.CheckState.Unchecked);self.list.addItem(i)
        self.list.blockSignals(False);self.filter(self.search.text());self.status.setText(f'{len(rows)} conversations found. Select chats and export. Refresh to include newer desktop messages.')
    def choose(self):
        path=QFileDialog.getExistingDirectory(self,'Select an existing readable SQLite snapshot',self.settings.value('source',str(Path.home())))
        if not path:return
        def work(p,s,c):
            d=open_archive(path,cancel=c)
            try:return sessions(d,c)
            finally:d.close()
        def done(rows):
            self.settings.setValue('source',path);self.load_rows(path,'',rows)
        self.job(work,done)
    def filter(self,s):
        for n in range(self.list.count()):
            i=self.list.item(n);group=i.data(Qt.ItemDataRole.UserRole).get('group',False);category=self.category.currentIndex();i.setHidden(s.casefold() not in (i.text()+' '+i.toolTip()).casefold() or (category==1 and group) or (category==2 and not group))
    def check(self,state):
        for n in range(self.list.count()):
            i=self.list.item(n)
            if state==Qt.CheckState.Unchecked or not i.isHidden():i.setCheckState(state)
    def preview(self,i,previous):
        if i is None or not self.root or self.worker:return
        root,wxid,uid=self.root,self.wxid,i.data(Qt.ItemDataRole.UserRole)['id']
        keyword=self.keyword.text().strip();self.status.setText('Loading message preview…');self.text.clear()
        def work(p,s,c):
            d=open_archive(root,wxid,cancel=c)
            try:return messages(d,uid,limit=100,cancel=c,full=True,keyword=keyword)
            finally:d.close()
        def done(rows):
            self.text.setPlainText('\n\n'.join(f"[{r['timestamp']}] {r['sender']}:\n{r['text']}" for r in rows) or 'No matching messages.');self.status.setText(f'Preview: {len(rows)} messages.')
        self.job(work,done)
    def output(self):
        p=QFileDialog.getExistingDirectory(self,'Output folder',self.folder.text())
        if p:self.folder.setText(p)
    def do_export(self):
        chosen=[self.list.item(n).data(Qt.ItemDataRole.UserRole) for n in range(self.list.count()) if self.list.item(n).checkState()==Qt.CheckState.Checked]
        if not chosen:return QMessageBox.information(self,'Select chats','Check at least one conversation.')
        root,wxid,folder,fmt=self.root,self.wxid,self.folder.text().strip(),self.fmt.currentText();start=end=None
        if not folder:return QMessageBox.warning(self,'Output','Enter an output folder.')
        if self.use_dates.isChecked():
            a=self.start.date().toPython();b=self.end.date().toPython()
            if a>b:return QMessageBox.warning(self,'Date range','Start must not be after end.')
            start=datetime.combine(a,datetime.min.time(),TZ).timestamp();end=datetime.combine(b+timedelta(days=1),datetime.min.time(),TZ).timestamp()
        self.settings.setValue('output',folder);self.settings.setValue('format',fmt);self.settings.setValue('mode',self.mode.currentIndex())
        full=self.mode.currentIndex()==1;copy_media=full and self.media.isChecked();archive=self.zip.isChecked();keyword=self.keyword.text().strip();account=self.account.get('path') if self.account else None;keys=self.image_keys
        def work(p,s,c):
            d=open_archive(root,wxid,account_dir=account,cancel=c)
            try:return batch(d,chosen,folder,fmt,full,copy_media,archive,start,end,keyword,account,c,p,s,image_keys=keys)
            finally:d.close()
        def done(result):
            count,path,stats=result;self.last_output=path;self.open_result.setEnabled(True);self.status.setText(f'Export complete: {count} messages.');details='\n'.join(f'{k}: {v}' for k,v in sorted(stats.items()));QMessageBox.information(self,'Export complete',f'{count} messages saved.\n{path}\n\n{details}\nSee manifest.json for details.')
        self.job(work,done)
    def closeEvent(self,event):
        if self.worker is not None:event.ignore();self.cancel_job();QMessageBox.information(self,'Busy','Operation is cancelling. Close the window after it has stopped.')
        else:self.clean_snapshot();event.accept()

if __name__=='__main__':
    smoke = '--smoke-test' in sys.argv
    app=QApplication([arg for arg in sys.argv if arg != '--smoke-test'])
    if smoke:
        # Verify frozen imports and Qt startup without accessing any account.
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PySide6.QtMultimediaWidgets import QVideoWidget
        from media_browser import MediaBrowser
        if sys.platform == 'win32':
            from wx4 import key, decrypt, paths
        from wx4 import offline_image
        import xlsxwriter, zstandard, psutil
    win=Window();win.show()
    if smoke: QTimer.singleShot(500,win.close)
    sys.exit(app.exec())
