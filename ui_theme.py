"""Shared Fluent-inspired presentation tokens. No additional dependencies."""
from PySide6.QtGui import QColor, QPalette, QFont
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout

LIGHT=dict(bg='#F3F6F5',surface='#FFFFFF',sub='#EAF0ED',text='#172A26',muted='#536B63',line='#D6E0DB',accent='#087F65',on='#FFFFFF',hover='#076B55',pressed='#065744',selection='#D4EEE5',warning='#8A5100',success='#08705A',disabled='#84928C')
DARK=dict(bg='#101917',surface='#1B2724',sub='#22332E',text='#E8F2EF',muted='#A5BAB1',line='#354940',accent='#5DD9B1',on='#102C24',hover='#83E6C6',pressed='#40BD96',selection='#284C40',warning='#F3C170',success='#82E4C2',disabled='#82938C')
_current=LIGHT

def tokens():return _current

def label(text,role='section'):
    w=QLabel(text);w.setProperty('role',role);return w

def role(widget,value):
    widget.setProperty('role',value);return widget

def panel(layout):
    w=QWidget();w.setProperty('role','panel');w.setLayout(layout);return w

def apply(name,system_palette):
    global _current
    app=QApplication.instance();dark=name=='Dark' or (name=='System' and system_palette.color(QPalette.ColorRole.Window).lightness()<128)
    c=_current=DARK if dark else LIGHT
    p=QPalette(system_palette)
    for key,value in {'Window':'bg','WindowText':'text','Base':'surface','AlternateBase':'bg','Text':'text','Button':'surface','ButtonText':'text','Highlight':'selection','HighlightedText':'text','PlaceholderText':'muted','ToolTipBase':'surface','ToolTipText':'text','Link':'accent'}.items():p.setColor(getattr(QPalette.ColorRole,key),QColor(c[value]))
    for key in ('Text','WindowText','ButtonText'):p.setColor(QPalette.ColorGroup.Disabled,getattr(QPalette.ColorRole,key),QColor(c['disabled']))
    app.setStyle('Fusion');app.setPalette(p);app.setFont(QFont('Segoe UI',10))
    app.setStyleSheet('''
QMainWindow,QDialog {background:%(bg)s;color:%(text)s;}
QWidget[role="panel"] {background:%(surface)s;border:1px solid %(line)s;border-radius:12px;}
QLabel {color:%(text)s;background:transparent;}
QLabel[role="title"] {font-size:26px;font-weight:700;}
QLabel[role="section"] {font-size:15px;font-weight:600;}
QLabel[role="muted"] {color:%(muted)s;font-size:12px;}
QLabel[role="warning"] {color:%(warning)s;}
QLabel[role="preview"] {background:%(sub)s;border:1px solid %(line)s;border-radius:10px;color:%(muted)s;padding:8px;}
QLabel[role="status"] {color:%(muted)s;padding:4px;}
QPushButton {background:%(surface)s;color:%(text)s;border:1px solid %(line)s;border-radius:7px;padding:7px 12px;min-height:20px;}
QPushButton:hover {background:%(sub)s;border-color:%(muted)s;}
QPushButton:pressed {background:%(selection)s;}
QPushButton[role="primary"] {background:%(accent)s;color:%(on)s;border-color:%(accent)s;font-weight:600;}
QPushButton[role="primary"]:hover {background:%(hover)s;}
QPushButton[role="primary"]:pressed {background:%(pressed)s;}
QPushButton:disabled,QPushButton[role="primary"]:disabled {background:%(sub)s;color:%(disabled)s;border-color:%(line)s;}
QLineEdit,QComboBox,QDateEdit,QPlainTextEdit,QListWidget,QTableView {background:%(surface)s;color:%(text)s;border:1px solid %(line)s;border-radius:7px;selection-background-color:%(selection)s;selection-color:%(text)s;}
QLineEdit,QComboBox,QDateEdit {padding:6px 9px;min-height:22px;}
QLineEdit[readOnly="true"] {background:%(sub)s;color:%(muted)s;}
QPushButton:focus,QLineEdit:focus,QComboBox:focus,QDateEdit:focus,QPlainTextEdit:focus,QListWidget:focus,QTableView:focus {border:1px solid %(accent)s;}
QComboBox::drop-down {width:24px;border:none;}
QComboBox QAbstractItemView {background:%(surface)s;color:%(text)s;selection-background-color:%(selection)s;selection-color:%(text)s;}
QPlainTextEdit {padding:10px;}
QListWidget::item {padding:8px 6px;border-bottom:1px solid %(line)s;}
QListWidget::item:selected,QTableView::item:selected {background:%(selection)s;color:%(text)s;}
QTableView {gridline-color:%(line)s;alternate-background-color:%(bg)s;}
QHeaderView::section {background:%(sub)s;color:%(muted)s;font-weight:600;padding:8px 5px;border:0;border-bottom:1px solid %(line)s;}
QCheckBox {spacing:6px;color:%(text)s;}
QCheckBox:disabled {color:%(disabled)s;}
QProgressBar {border:0;background:%(sub)s;border-radius:5px;min-height:10px;max-height:14px;text-align:center;color:%(text)s;}
QProgressBar::chunk {background:%(accent)s;border-radius:5px;}
QSplitter::handle {background:transparent;}
QSplitter::handle:hover {background:%(line)s;}
QToolTip {background:%(surface)s;color:%(text)s;border:1px solid %(line)s;padding:5px;}
'''%c)
