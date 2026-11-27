"""Optional media browser for WeChat Exporter v2.0; English Qt widgets."""
from pathlib import Path
from datetime import datetime
import threading, tempfile, shutil
from PySide6.QtCore import Qt,QThread,Signal,QAbstractTableModel,QModelIndex,QSortFilterProxyModel,QUrl,QBuffer,QByteArray,QIODevice,QSize,QTimer
from PySide6.QtGui import QImageReader,QPixmap,QDesktopServices,QShortcut,QKeySequence
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QLineEdit,QFileDialog,QTableView,QSplitter,QWidget,QProgressBar,QMessageBox,QCheckBox,QStackedWidget,QHeaderView,QAbstractItemView,QSlider)
import media_catalog as catalog
import ui_theme as ui

class Cancelled(Exception):pass
class Job(QThread):
    result=Signal(object);error=Signal(str);progress=Signal(int,int);status=Signal(str);cancelled=Signal()
    def __init__(self,fn,parent):super().__init__(parent);self.fn=fn;self.stop=threading.Event()
    def check(self):
        if self.stop.is_set():raise Cancelled()
    def run(self):
        try:self.result.emit(self.fn(self.check,self.progress.emit,self.status.emit))
        except Cancelled:self.cancelled.emit()
        except Exception as e:self.error.emit(str(e))

class Model(QAbstractTableModel):
    headers=('File','Type','Status','Size','Modified','Folder')
    def __init__(self):super().__init__();self.items=[];self.checked=set()
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.items)
    def columnCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.headers)
    def headerData(self,section,orientation,role=Qt.ItemDataRole.DisplayRole):
        if role==Qt.ItemDataRole.DisplayRole and orientation==Qt.Orientation.Horizontal:return self.headers[section]
    def data(self,index,role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():return None
        x=self.items[index.row()];col=index.column()
        if role==Qt.ItemDataRole.CheckStateRole and col==0:return Qt.CheckState.Checked if x.path in self.checked else Qt.CheckState.Unchecked
        if role==Qt.ItemDataRole.ToolTipRole:return x.relative+'\n'+x.status+(' • possible thumbnail' if x.thumbnail else '')
        if role==Qt.ItemDataRole.DisplayRole:return (Path(x.path).name,x.kind,x.status+(' (thumbnail?)' if x.thumbnail else ''),f'{x.size/1024:,.1f} KB',datetime.fromtimestamp(x.modified).strftime('%Y-%m-%d %H:%M'),str(Path(x.relative).parent))[col]
        if role==Qt.ItemDataRole.UserRole:return (Path(x.path).name.casefold(),x.kind,x.status,x.size,x.modified,str(Path(x.relative).parent).casefold())[col]
    def flags(self,index):return super().flags(index)|(Qt.ItemFlag.ItemIsUserCheckable if index.column()==0 else Qt.ItemFlag.NoItemFlags)
    def setData(self,index,value,role):
        if role!=Qt.ItemDataRole.CheckStateRole or index.column()!=0:return False
        p=self.items[index.row()].path
        if value==Qt.CheckState.Checked or value==Qt.CheckState.Checked.value:self.checked.add(p)
        else:self.checked.discard(p)
        self.dataChanged.emit(index,index,[Qt.ItemDataRole.CheckStateRole]);return True
    def reset(self,items):self.beginResetModel();self.items=items;self.checked.clear();self.endResetModel()
    def refresh_keys(self,keys):
        self.items=[catalog.with_keys(x,keys) for x in self.items]
        if self.items:self.dataChanged.emit(self.index(0,0),self.index(len(self.items)-1,5))
    def mark(self,items,checked):
        if checked:self.checked.update(x.path for x in items)
        else:self.checked.difference_update(x.path for x in items)
        if self.items:self.dataChanged.emit(self.index(0,0),self.index(len(self.items)-1,0),[Qt.ItemDataRole.CheckStateRole])

class Filter(QSortFilterProxyModel):
    def __init__(self):super().__init__();self.term='';self.kind='All media';self.only=False;self.thumbs=True;self.setSortRole(Qt.ItemDataRole.UserRole)
    def filterAcceptsRow(self,row,parent):
        x=self.sourceModel().items[row]
        return (not self.term or self.term in x.relative.casefold()) and (self.kind=='All media' or x.kind==self.kind) and (not self.only or x.available) and (self.thumbs or not x.thumbnail)
    def update(self,term,kind,only,thumbs):self.term=term.casefold();self.kind=kind;self.only=only;self.thumbs=thumbs;self.invalidateFilter()

class MediaBrowser(QDialog):
    def __init__(self,parent=None,account=None,chat=None,output=None,keys=(),wxid=""):
        super().__init__(parent);self.setWindowTitle('Media Browser | WeChat Exporter');self.resize(1280,820);self.account=Path(account) if account else None;self.chat=chat;self.worker=None;self.current=None;self.output=output or str(Path.home()/'Documents'/'WeChat Export');self.result_path='';self.player=None;self.pix=None;self.keys=keys;self.wxid=wxid;self.preview_dir=None;self.preview_file=None
        v=QVBoxLayout(self);v.setContentsMargins(22,18,22,18);v.setSpacing(10);v.addWidget(ui.label('Media Browser','title'));v.addWidget(ui.label('LOCAL LIBRARY  /  Browse, preview and export cached media','muted'))
        row=QHBoxLayout();self.scope=QComboBox();self.scope.addItem('Choose a local folder','folder')
        if self.account:self.scope.addItem('Current account — known media folders','account');self.scope.setCurrentIndex(1)
        if self.account and self.chat:self.scope.addItem('Selected conversation — attachment folder only','chat')
        self.path=QLineEdit(str(self.account or ''));self.path.setReadOnly(True);self.browse=QPushButton('Browse folder…');self.browse.clicked.connect(self.pick);self.scan_btn=ui.role(QPushButton('Scan / Refresh'),'primary');self.scan_btn.clicked.connect(self.scan);row.addWidget(self.scope);row.addWidget(self.path,1);row.addWidget(self.browse);row.addWidget(self.scan_btn);v.addLayout(row);self.key_btn=QPushButton('Use existing image access file…');self.key_btn.clicked.connect(self.import_keys);self.access_btn=QPushButton('Refresh image access');self.access_btn.clicked.connect(self.refresh_access);access=QHBoxLayout();access.addWidget(self.access_btn);access.addWidget(self.key_btn);access.addStretch();v.addLayout(access);self.scope.currentIndexChanged.connect(self.scope_change)
        self.folder='';self.scope_change();self.note=QLabel('Account-wide cache files may not be linked to a particular conversation. Modified date is file time, not message time.');self.note.setWordWrap(True);ui.role(self.note,'muted');v.addWidget(self.note)
        row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Search filename or folder');self.kind=QComboBox();self.kind.addItems(['All media','Image','Video']);self.only=QCheckBox('Available only');self.only.setChecked(False);self.thumbs=QCheckBox('Include possible thumbnails');self.thumbs.setChecked(True)
        for w in (self.search,self.kind,self.only,self.thumbs):row.addWidget(w)
        v.addLayout(row);self.model=Model();self.proxy=Filter();self.proxy.setSourceModel(self.model);self.table=QTableView();self.table.setModel(self.proxy);self.table.setSortingEnabled(True);self.table.sortByColumn(4,Qt.SortOrder.DescendingOrder);self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection);self.table.setAlternatingRowColors(True);self.table.verticalHeader().setDefaultSectionSize(34);self.table.setShowGrid(False);self.table.verticalHeader().hide();self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch);self.table.setColumnWidth(1,66);self.table.setColumnWidth(2,140);self.table.setColumnWidth(3,90);self.table.setColumnWidth(4,130);self.table.setColumnWidth(5,180)
        for sig in (self.search.textChanged,self.kind.currentTextChanged,self.only.toggled,self.thumbs.toggled):sig.connect(self.apply_filter)
        self.model.dataChanged.connect(self.count);self.table.selectionModel().currentChanged.connect(self.preview)
        split=QSplitter();split.addWidget(self.table);r=QVBoxLayout();r.setContentsMargins(14,12,14,12);right=ui.panel(r);r.addWidget(ui.label('Media preview'));self.info=QLabel('Select a file to preview.');self.info.setWordWrap(True);ui.role(self.info,'muted');r.addWidget(self.info);self.stack=QStackedWidget();self.image=ui.role(QLabel('Select a media file to preview'),'preview');self.image.setAlignment(Qt.AlignmentFlag.AlignCenter);self.image.setMinimumSize(240,180);self.stack.addWidget(self.image);r.addWidget(self.stack,1);self.controls=QWidget();controls=QHBoxLayout(self.controls);controls.setContentsMargins(0,0,0,0);self.play=QPushButton('Play / Pause');self.play.clicked.connect(self.play_pause);self.seek=QSlider(Qt.Orientation.Horizontal);self.seek.sliderMoved.connect(lambda p:self.player.setPosition(p) if self.player else None);controls.addWidget(self.play);controls.addWidget(self.seek,1);r.addWidget(self.controls);self.controls.hide()
        try:
            from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
            from PySide6.QtMultimediaWidgets import QVideoWidget
            self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.audio.setVolume(0.5);self.video=QVideoWidget();self.stack.addWidget(self.video);self.player.setAudioOutput(self.audio);self.player.setVideoOutput(self.video);self.player.durationChanged.connect(lambda p:self.seek.setRange(0,min(p,2147483647)));self.player.positionChanged.connect(lambda p:self.seek.setValue(min(p,2147483647)) if not self.seek.isSliderDown() else None);self.player.errorOccurred.connect(lambda *_:self.info.setText('Video preview unavailable with this codec. Try Open in default app.'))
        except (ImportError,OSError):self.player=None
        self.external=QPushButton('Open in default app');self.external.clicked.connect(self.open_external);self.external.setEnabled(False);r.addWidget(self.external);split.addWidget(right);split.setHandleWidth(10);split.setSizes([760,460]);v.addWidget(split,1)
        row=QHBoxLayout();self.select=QPushButton('Check visible');self.select.clicked.connect(lambda:self.model.mark(self.visible(),True));self.clear=QPushButton('Clear all checks');self.clear.clicked.connect(lambda:self.model.mark(self.model.items,False));self.summary=ui.label('','muted');row.addWidget(self.select);row.addWidget(self.clear);row.addWidget(self.summary,1);v.addLayout(row)
        row=QHBoxLayout();self.dest=QLineEdit(self.output);self.dest_browse=QPushButton('Output folder…');self.dest_browse.clicked.connect(self.pick_output);self.export_checked=ui.role(QPushButton('Export checked'),'primary');self.export_checked.clicked.connect(lambda:self.export(False));self.export_all=QPushButton('Export all visible');self.export_all.clicked.connect(lambda:self.export(True));self.open_result=QPushButton('Open result');self.open_result.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(self.result_path)));row.addWidget(self.dest,1);row.addWidget(self.dest_browse);row.addWidget(self.export_checked);row.addWidget(self.export_all);row.addWidget(self.open_result);v.addLayout(row)
        row=QHBoxLayout();self.progress=QProgressBar();self.progress.setRange(0,1);self.cancel=QPushButton('Cancel (Esc)');self.esc=QShortcut(QKeySequence('Esc'),self);self.esc.setContext(Qt.ShortcutContext.WindowShortcut);self.esc.activated.connect(self.cancel_job);self.cancel.clicked.connect(self.cancel_job);row.addWidget(self.progress,1);row.addWidget(self.cancel);v.addLayout(row);self.status=QLabel('Choose a scope and scan.');self.status.setWordWrap(True);ui.role(self.status,'status');v.addWidget(self.status);self.busy(False);self.apply_filter()
        if self.account:QTimer.singleShot(0,self.scan)
    def scope_change(self,*_):
        self.path.setText(self.folder if self.scope.currentData()=='folder' else str(self.account or ''));self.browse.setEnabled(self.scope.currentData()=='folder')
        if hasattr(self,'model'):self.stop_preview();self.model.reset([]);self.count()
    def pick(self):
        p=QFileDialog.getExistingDirectory(self,'Choose a local media folder',self.folder or str(Path.home()))
        if p:self.folder=p;self.scope.setCurrentIndex(0);self.scope_change();self.scan()
    def pick_output(self):
        p=QFileDialog.getExistingDirectory(self,'Choose export destination',self.dest.text())
        if p:self.dest.setText(p)
    def visible(self):return [self.model.items[self.proxy.mapToSource(self.proxy.index(i,0)).row()] for i in range(self.proxy.rowCount())]
    def count(self,*_):
        self.summary.setText(f'{self.proxy.rowCount():,} visible / {len(self.model.items):,} found • {len(self.model.checked):,} checked');self.export_checked.setEnabled(self.worker is None and bool(self.model.checked));self.export_all.setEnabled(self.worker is None and bool(self.proxy.rowCount()));self.open_result.setEnabled(self.worker is None and bool(self.result_path))
    def apply_filter(self,*_):self.proxy.update(self.search.text(),self.kind.currentText(),self.only.isChecked(),self.thumbs.isChecked());self.count()
    def busy(self,state):
        for w in (self.scope,self.scan_btn,self.key_btn,self.access_btn,self.search,self.kind,self.only,self.thumbs,self.table,self.select,self.clear,self.dest,self.dest_browse):w.setEnabled(not state)
        self.browse.setEnabled(not state and self.scope.currentData()=='folder');self.cancel.setEnabled(state);self.count()
        if state:self.export_checked.setEnabled(False);self.export_all.setEnabled(False);self.open_result.setEnabled(False)
    def start_job(self,fn,done):
        if self.worker:return
        job=Job(fn,self)
        try:
            job.result.connect(done);job.error.connect(self.job_error);job.cancelled.connect(lambda:self.status.setText('Cancelled. Previous exports are preserved.'));job.status.connect(self.status.setText);job.progress.connect(self.set_progress);job.finished.connect(self.on_job_finished)
            self.worker=job;self.busy(True);self.progress.setRange(0,0);job.start()
        except Exception as exc:
            self.worker=None;job.deleteLater();self.progress.setRange(0,1);self.progress.setValue(0);self.busy(False);self.job_error(str(exc))
    def job_error(self,message):
        self.status.setText('Operation failed: '+message)
        self.image.setText('Operation failed: '+message)

    def on_job_finished(self):old=self.worker;self.worker=None;old.deleteLater();self.progress.setRange(0,1);self.progress.setValue(0);self.busy(False)
    def set_progress(self,n,total):self.progress.setRange(0,max(1,total));self.progress.setValue(n)
    def cancel_job(self):
        if self.worker:self.worker.stop.set();self.status.setText('Cancelling…');self.cancel.setEnabled(False)
    def scan(self):
        mode=self.scope.currentData();root=self.path.text();folders=None
        if not root:return self.pick()
        if mode=='account':folders=catalog.ACCOUNT_MEDIA_FOLDERS  # Fast, targeted scan; use Browse folder for other paths.
        if mode=='chat':
            from wx4.reader import Wx4Data
            folders=['msg/attach/'+Wx4Data.msg_table_for(self.chat['id'])[4:]]
        self.stop_preview();self.model.reset([]);self.status.setText('Scanning known media folders…')
        def done(result):
            items,errors,keys=result
            if mode!='folder':self.keys=keys
            self.model.reset(items);self.apply_filter();self.status.setText(f'{len(items):,} files found: {sum(x.kind=="Image" for x in items):,} images, {sum(x.kind=="Video" for x in items):,} videos; {sum(not x.available for x in items):,} locked/unverified; {errors:,} scan errors.')
        def work(c,p,s):
            keys=self.keys if mode!='folder' else ()
            if mode!='folder' and not keys:
                keys=catalog.existing_account_image_keys(self.account,self.wxid,c)
            items,errors=catalog.scan(root,folders,c,s,keys)
            return items,errors,keys
        self.start_job(work,done)
    def refresh_access(self):
        if not self.account or self.scope.currentData()=='folder':
            self.status.setText('Connect your WeChat account first.');return
        # Recheck existing account access without scanning the filesystem again.
        samples=[x for x in self.model.items if x.status in ('Encrypted V2 image','V2 key supplied')][:3]
        previous=self.keys
        def work(c,p,s):
            keys=catalog.existing_account_image_keys(self.account,self.wxid,c) or previous
            passed=0;checked=0
            if keys:
                for item in samples:
                    c();checked+=1;s(f'Checking existing image access… {checked}/{len(samples)}')
                    try:catalog.image_result(item,keys,c);passed+=1
                    except (ValueError,OSError,ImportError):pass
                    if passed:break
            return keys,passed,checked
        def done(result):
            keys,passed,checked=result
            if keys:
                self.keys=keys;self.stop_preview();self.model.refresh_keys(keys);self.apply_filter()
                self.status.setText(f'Image access verified on {passed}/{checked} tested images. Other images may still be locked.' if passed else ('Saved access found, but no tested image could be opened.' if checked else 'Saved access loaded. Select an image to test.'))
            else:
                self.status.setText('No saved image access for this account. Save images from WeChat into a folder, or use an existing image access file.')
        self.start_job(work,done)
    def import_keys(self):
        if not self.account or self.scope.currentData()=='folder':return QMessageBox.information(self,'V2 image key','Select a connected account first.')
        p,_=QFileDialog.getOpenFileName(self,'Select your existing Moect image-keys.json or media-key.bin',str(Path.home()),'Key files (*.json *.bin *.txt);;All files (*)')
        if not p:return
        try:self.keys=catalog.load_image_keys(p)
        except (OSError,ValueError) as e:return QMessageBox.warning(self,'Image key',str(e))
        # Reclassify existing V2 rows without reopening every file.
        self.stop_preview();self.model.refresh_keys(self.keys);self.apply_filter();self.status.setText('Image key imported. Select a V2 image to test it; a supplied key is not proof of successful decoding.')
    def stop_preview(self):
        if self.player:self.player.stop();self.player.setSource(QUrl())
        self.current=None;self.preview_file=None;
        if self.preview_dir:shutil.rmtree(self.preview_dir,ignore_errors=True);self.preview_dir=None
        self.controls.hide();self.external.setEnabled(False);self.image.clear();self.image.setText('No preview');self.stack.setCurrentWidget(self.image)
    def preview(self,index,*_):
        if self.worker:return
        self.stop_preview()
        if not index.isValid():return
        item=self.model.items[self.proxy.mapToSource(index).row()];self.current=item;self.info.setText(item.relative+'\n'+item.status+' • '+f'{item.size:,} bytes')
        keys=self.keys if self.scope.currentData()!='folder' else ()
        if not item.available and not (keys and item.status=='Encrypted V2 image'):
            self.image.setText('Image access not available. Try Refresh image access after Moect image recovery for the same account, or save the image in WeChat. Missing originals must first be downloaded.');return
        self.image.setText('Loading preview… (Esc to cancel)')
        size=QSize(max(240,self.image.width()),max(180,self.image.height()))
        def work(c,p,s):
            c()
            if item.kind=='Video':
                # Cache entries without a normal suffix may not be accepted by Qt/OS.
                src=Path(item.path)
                if src.suffix.lower() in catalog.VIDEO:return ('video',str(src),None)
                folder=Path(tempfile.mkdtemp(prefix='wechat-preview-'))
                try:
                    dst=folder/('preview'+item.extension)
                    with src.open('rb') as a,dst.open('wb') as b:
                        for block in iter(lambda:a.read(1024*1024),b''):c();b.write(block)
                    c();return ('video',str(dst),str(folder))
                except BaseException:shutil.rmtree(folder,ignore_errors=True);raise
            quality='Original local raster'
            if item.status=='Ready':reader=QImageReader(item.path);buffer=None
            else:
                blob,_,quality=catalog.image_result(item,keys,c);buffer=QBuffer();buffer.setData(QByteArray(blob));buffer.open(QIODevice.OpenModeFlag.ReadOnly);reader=QImageReader(buffer)
            reader.setDecideFormatFromContent(True);reader.setAutoTransform(True);dim=reader.size()
            if dim.isValid():dim.scale(size,Qt.AspectRatioMode.KeepAspectRatio);reader.setScaledSize(dim)
            img=reader.read();c()
            if img.isNull():raise ValueError(reader.errorString())
            return ('image',img,quality)
        def done(result):
            kind,value,temp=result
            if kind=='video':
                self.preview_dir=temp;self.preview_file=value;self.external.setEnabled(True)
                if self.player:self.stack.setCurrentWidget(self.video);self.controls.show();self.player.setSource(QUrl.fromLocalFile(value))
                else:self.image.setText('Video player unavailable. Use Open in default app.')
            else:
                self.image.setPixmap(QPixmap.fromImage(value));self.external.setEnabled(item.status=='Ready' and Path(item.path).suffix.lower() in catalog.IMAGE)
            self.status.setText('Preview ready. '+str(temp) if kind=='image' else 'Video ready.')
        self.start_job(work,done)
    def play_pause(self):
        if self.player:
            if self.player.playbackState()==self.player.PlaybackState.PlayingState:self.player.pause()
            else:self.player.play()
    def open_external(self):
        if self.current and self.external.isEnabled():QDesktopServices.openUrl(QUrl.fromLocalFile(self.preview_file or self.current.path))
    def export(self,all_visible):
        items=self.visible() if all_visible else [x for x in self.model.items if x.path in self.model.checked];out=self.dest.text().strip()
        if not items or not out:return QMessageBox.information(self,'Export','Choose files and an output folder.')
        if QMessageBox.question(self,'Export media',f'Export {len(items):,} files? Locked or unsupported files will be reported as skipped. Checked files include hidden checks.')!=QMessageBox.StandardButton.Yes:return
        self.stop_preview();self.status.setText('Exporting local media…')
        def done(result):
            self.result_path,saved,skipped=result;self.status.setText(f'Saved {saved:,}; skipped {skipped:,}. See manifest.json.');QMessageBox.information(self,'Export complete',f'Saved: {saved:,}\nSkipped: {skipped:,}\n{self.result_path}')
        keys=self.keys if self.scope.currentData()!='folder' else ()
        self.start_job(lambda c,p,s:catalog.export(items,out,c,p,s,keys),done)
    def reject(self):
        if self.worker:self.cancel_job();self.status.setText('Cancelling. Close after the job stops.');return
        self.stop_preview();super().reject()
    def closeEvent(self,event):
        if self.worker:event.ignore();self.cancel_job()
        else:self.stop_preview();super().closeEvent(event)
