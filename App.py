import sys
import os
import queue
import traceback
import time
import json
import re
import subprocess
import shutil
import faulthandler
from urllib.parse import urlparse
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QLabel, QFileDialog, QMessageBox, QProgressBar, QGroupBox, 
                             QPlainTextEdit, QLineEdit, QSplitter, QTabWidget, QFormLayout, QMenu,
                             QSpinBox, QProgressBar, QDialog, QTreeWidget, QTreeWidgetItem,
                             QDialogButtonBox, QScrollArea, QFrame)
from PyQt6.QtGui import QColor, QFont, QIcon, QAction

# Import existing logic
from MasterDownloader import MasterDownloader

CRASH_LOG = None

def enable_crash_logging():
    global CRASH_LOG
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
        CRASH_LOG = open(log_path, "a", encoding="utf-8")
        CRASH_LOG.write(f"\n--- App start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        CRASH_LOG.flush()
        faulthandler.enable(CRASH_LOG)
    except Exception:
        faulthandler.enable()

APP_STYLE = """
QMainWindow {
    background: #101418;
    color: #e7edf3;
}
QWidget {
    color: #e7edf3;
    font-family: "Segoe UI", "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #27313b;
    border-radius: 8px;
    background: #141a20;
    top: -1px;
}
QTabBar::tab {
    background: #101418;
    color: #8f9dab;
    border: 1px solid #27313b;
    border-bottom: none;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: #141a20;
    color: #f7fafc;
}
QGroupBox {
    background: #161d24;
    border: 1px solid #2b3642;
    border-radius: 8px;
    margin-top: 18px;
    padding: 18px 14px 14px 14px;
    font-weight: 650;
    color: #f7fafc;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #a9b8c7;
}
QLineEdit, QPlainTextEdit {
    background: #0f1419;
    border: 1px solid #2c3742;
    border-radius: 7px;
    padding: 8px 10px;
    color: #edf3f9;
    selection-background-color: #2f80ed;
}
QLineEdit {
    min-height: 20px;
}
QLineEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #5aa7ff;
    background: #111922;
}
QLineEdit::placeholder, QPlainTextEdit::placeholder {
    color: #6f7d8b;
}
QFileDialog {
    background: #141a20;
    color: #e7edf3;
}
QFileDialog QLabel {
    color: #dce6ef;
}
QFileDialog QTreeView,
QFileDialog QListView {
    background: #0f1419;
    color: #e7edf3;
    border: 1px solid #2c3742;
    selection-background-color: #2f80ed;
    selection-color: #ffffff;
    alternate-background-color: #151d25;
}
QFileDialog QComboBox {
    background: #0f1419;
    color: #e7edf3;
    border: 1px solid #2c3742;
    border-radius: 6px;
    padding: 6px 8px;
}
QPushButton {
    background: #222c36;
    border: 1px solid #344250;
    border-radius: 7px;
    color: #ecf2f8;
    padding: 8px 13px;
    font-weight: 650;
}
QPushButton:hover {
    background: #2b3744;
    border-color: #445466;
}
QPushButton:pressed {
    background: #1b232b;
}
QPushButton:disabled {
    background: #1a2027;
    border-color: #2a333d;
    color: #657383;
}
QPushButton#primaryButton {
    background: #2f80ed;
    border-color: #4b97f1;
    color: #ffffff;
}
QPushButton#primaryButton:hover {
    background: #3d8df7;
}
QPushButton#warningButton {
    background: #b96b16;
    border-color: #d1842d;
    color: #fff8ed;
}
QPushButton#warningButton:hover {
    background: #c97920;
}
QPushButton#dangerButton {
    background: #b8393f;
    border-color: #d34d53;
    color: #fff5f5;
}
QPushButton#dangerButton:hover {
    background: #ca444a;
}
QTableWidget {
    background: #11171d;
    alternate-background-color: #151d25;
    border: 1px solid #2b3642;
    border-radius: 8px;
    gridline-color: #25303a;
    color: #dfe7ef;
    selection-background-color: #213e62;
    selection-color: #ffffff;
}
QHeaderView::section {
    background: #1b242d;
    color: #b6c4d2;
    border: none;
    border-right: 1px solid #2b3642;
    padding: 9px 8px;
    font-weight: 700;
}
QProgressBar {
    background: #0d1217;
    border: 1px solid #2a3641;
    border-radius: 5px;
    min-height: 8px;
}
QProgressBar::chunk {
    background: #2f80ed;
    border-radius: 4px;
}
QMenu {
    background: #151c23;
    border: 1px solid #2d3945;
    color: #edf3f9;
}
QMenu::item {
    padding: 8px 24px;
}
QMenu::item:selected {
    background: #223449;
}
QStatusBar {
    background: #0f1419;
    color: #9fb0c0;
    border-top: 1px solid #27313b;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    background: #0f1419;
    width: 12px;
    margin: 0;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #2f3b47;
    min-height: 28px;
    border-radius: 6px;
}
QScrollBar::handle:vertical:hover {
    background: #3c4b5a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
"""

PROGRESS_STYLE_DEFAULT = """
QProgressBar {
    background: #0d1217;
    border: 1px solid #2a3641;
    border-radius: 5px;
    min-height: 8px;
}
QProgressBar::chunk {
    background: #2f80ed;
    border-radius: 4px;
}
"""

PROGRESS_STYLE_SUCCESS = PROGRESS_STYLE_DEFAULT.replace("#2f80ed", "#28a36a")
PROGRESS_STYLE_ERROR = PROGRESS_STYLE_DEFAULT.replace("#2f80ed", "#d34d53")

# --- WORKER SIGNALS ---
class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    Supported signals are:
    finished: No data
    error: tuple (exctype, value, traceback.format_exc() )
    result: object data returned from processing, anything
    progress: tuple (row_id, percent_str, speed_str, status_msg)
    """
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(tuple)

# --- WORKER (RUNNABLE) ---
class DownloadWorker(QRunnable):
    """
    Worker thread for downloading.
    """
    def __init__(self, fn, row_id, *args, **kwargs):
        super(DownloadWorker, self).__init__()
        self.fn = fn
        self.row_id = row_id
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        
        # Inject progress callback into kwargs
        self.kwargs['progress_callback'] = self.report_progress

    def report_progress(self, percent, msg):
        # percent can be "45%" or just "45"
        # msg can include speed, eta, etc.
        self.signals.progress.emit((self.row_id, percent, "", msg))

    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()

class DuplicateWorker(QRunnable):
    """
    Worker thread for scanning duplicates.
    """
    def __init__(self, downloader, directory):
        super(DuplicateWorker, self).__init__()
        self.downloader = downloader
        self.directory = directory
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            def callback(msg):
                # We use row_id = -1 to indicate log-only progress
                self.signals.progress.emit((-1, "0", "", msg))

            groups, resurrected = self.downloader.find_duplicates(
                directory=self.directory,
                status_callback=callback
            )
            self.signals.result.emit((groups, resurrected))
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self.signals.finished.emit()

def human_size(num):
    """Doi byte sang chuoi de doc (KB/MB/GB)."""
    try:
        num = float(num)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


# --- DUPLICATES REVIEW DIALOG ---
class DuplicatesDialog(QDialog):
    """Hien thi cac nhom file trung, cho user chon ban nao xoa truoc khi xac nhan."""
    def __init__(self, groups, parent=None, resurrected=None):
        super().__init__(parent)
        self.groups = groups
        self.resurrected = resurrected or []
        self.setWindowTitle("Xử lý file trùng lặp")
        self.resize(860, 580)
        if parent:
            self.setStyleSheet(parent.styleSheet())

        layout = QVBoxLayout(self)

        total_dupes = sum(len(g) - 1 for g in groups)
        freed = sum(self._size(p) for g in groups for p in g[1:])
        freed += sum(self._size(p) for p in self.resurrected)
        resurrected_note = (
            f" + <b>{len(self.resurrected)}</b> file đã từng xoá (tải lại)"
            if self.resurrected else ""
        )
        info = QLabel(
            f"Tìm thấy <b>{len(groups)}</b> nhóm trùng, <b>{total_dupes}</b> bản sao"
            f"{resurrected_note} "
            f"(tối đa giải phóng <b>~{human_size(freed)}</b>).<br>"
            "Mục được <b>tick</b> sẽ bị <b>XÓA</b>. Mỗi nhóm tự giữ lại bản cũ nhất."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["File (tick = xóa)", "Kích thước", "Sửa đổi"])
        self.tree.setColumnWidth(0, 540)
        self.tree.setColumnWidth(1, 90)
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree)
        self._populate()

        btn_row = QHBoxLayout()
        btn_all = QPushButton("Chọn tất cả bản sao")
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none = QPushButton("Bỏ chọn tất cả")
        btn_none.clicked.connect(lambda: self._set_all(False))
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        bb = QDialogButtonBox()
        self.btn_delete = bb.addButton("Xóa các mục đã chọn", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_delete.setObjectName("primaryButton")
        bb.addButton("Hủy", QDialogButtonBox.ButtonRole.RejectRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    @staticmethod
    def _size(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    @staticmethod
    def _mtime(path):
        try:
            return time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(path)))
        except OSError:
            return ""

    def _populate(self):
        for i, group in enumerate(self.groups, 1):
            keeper = group[0]
            top = QTreeWidgetItem(self.tree, [f"Nhóm {i} — {len(group)} bản", "", ""])
            top.setFlags(top.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            top.setExpanded(True)

            kc = QTreeWidgetItem(top, [f"✅ GIỮ LẠI: {keeper}", human_size(self._size(keeper)), self._mtime(keeper)])
            kc.setFlags(Qt.ItemFlag.ItemIsEnabled)
            kc.setForeground(0, QColor("#28a36a"))

            for p in group[1:]:
                child = QTreeWidgetItem(top, [p, human_size(self._size(p)), self._mtime(p)])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)
                child.setData(0, Qt.ItemDataRole.UserRole, p)

        if self.resurrected:
            top = QTreeWidgetItem(
                self.tree,
                [f"🔁 Đã từng xoá trước đây — {len(self.resurrected)} file", "", ""],
            )
            top.setFlags(top.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            top.setExpanded(True)
            for p in self.resurrected:
                child = QTreeWidgetItem(top, [p, human_size(self._size(p)), self._mtime(p)])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)
                child.setData(0, Qt.ItemDataRole.UserRole, p)

    def _set_all(self, checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                child = top.child(j)
                if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    child.setCheckState(0, state)

    def selected_paths(self):
        paths = []
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                child = top.child(j)
                if (child.flags() & Qt.ItemFlag.ItemIsUserCheckable
                        and child.checkState(0) == Qt.CheckState.Checked):
                    p = child.data(0, Qt.ItemDataRole.UserRole)
                    if p:
                        paths.append(p)
        return paths


# --- MAIN WINDOW ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Master Downloader")
        self.resize(1180, 820)
        self.setMinimumSize(900, 620)
        
        # Logic Core
        self.downloader = MasterDownloader()
        self.threadpool = QThreadPool()

        self.row_mapping = {} # future/uid -> row_index (Dynamic management)
        self.failed_rows = set()
        self._log_pct_bucket = {} # row_id -> bucket cuoi cung da log (de throttle thanh tien trinh)
        # Since table rows can change index if we sort or delete, better to store an ID in the item data.
        # For simplicity in this demo, we assume append-only or carefully managed rows.
        
        # Configuration (Simple placeholder)
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.current_download_folder = self.base_dir
        
        self.config_file = os.path.join(self.base_dir, "gui_config.json")
        self.config = self.load_config()

        # Gioi han so luong tai dong thoi (doc tu config, mac dinh 3)
        self._apply_max_concurrent(self.config.get("max_concurrent", 3))
        print(f"Multimedia Thread Pool running with {self.threadpool.maxThreadCount()} threads.")

        self.init_ui()
        self.load_saved_links()

    def load_config(self):
        default = {
            "download_folder": "",
            "saved_links": [],
            "default_download_folder": self.get_system_download_folder(),
            "max_concurrent": 3,
        }
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge defaults
                    for k, v in default.items():
                        if k not in data:
                            data[k] = v
                    if not data.get("default_download_folder"):
                        data["default_download_folder"] = default["default_download_folder"]
                    return data
            except:
                return default
        return default

    def get_system_download_folder(self):
        """Return the OS Downloads folder, preferring Windows Downloads when running in WSL."""
        candidates = []

        if os.environ.get("WSL_DISTRO_NAME") and shutil.which("cmd.exe"):
            try:
                result = subprocess.run(
                    ["cmd.exe", "/c", "echo", "%USERPROFILE%"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
                win_profile = result.stdout.strip().replace("\\", "/")
                if re.match(r"^[A-Za-z]:/", win_profile):
                    drive = win_profile[0].lower()
                    rest = win_profile[2:]
                    candidates.append(f"/mnt/{drive}{rest}/Downloads")
            except Exception:
                pass

        home = os.path.expanduser("~")
        xdg_download = os.environ.get("XDG_DOWNLOAD_DIR")
        if xdg_download:
            candidates.append(os.path.expandvars(xdg_download).replace("$HOME", home))

        candidates.extend([
            os.path.join(home, "Downloads"),
            self.base_dir,
        ])

        for folder in candidates:
            if folder and os.path.isdir(folder):
                return folder

        return home

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except:
            pass

    def _apply_max_concurrent(self, value):
        """Ap dung gioi han so luong tai dong thoi cho thread pool (kep trong 1..16)."""
        try:
            n = int(value)
        except (TypeError, ValueError):
            n = 3
        n = max(1, min(16, n))
        self.threadpool.setMaxThreadCount(n)
        return n

    def init_ui(self):
        self.setStyleSheet(APP_STYLE)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 18, 18, 14)
        main_layout.setSpacing(14)

        header_layout = QHBoxLayout()
        title = QLabel("Master Downloader")
        title.setStyleSheet("font-size: 18px; font-weight: 750; color: #f7fafc;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self.btn_window_minimize = QPushButton("Minimize")
        self.btn_window_minimize.clicked.connect(self.showMinimized)
        header_layout.addWidget(self.btn_window_minimize)

        self.btn_window_maximize = QPushButton("Maximize")
        self.btn_window_maximize.setObjectName("primaryButton")
        self.btn_window_maximize.clicked.connect(self.toggle_window_size)
        header_layout.addWidget(self.btn_window_maximize)

        main_layout.addLayout(header_layout)

        # Tab Widget
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # --- TAB 1: DOWNLOADER ---
        tab_download = QWidget()
        download_layout = QVBoxLayout(tab_download)
        download_layout.setContentsMargins(14, 14, 14, 14)
        download_layout.setSpacing(14)

        # 1. Top Control Panel
        top_group = QGroupBox("Add Links")
        top_layout = QVBoxLayout()
        top_layout.setSpacing(12)
        
        # Row 1: URL input
        r1 = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste TikTok, Instagram, or Facebook link here...")
        r1.addWidget(self.url_input)
        
        self.btn_paste = QPushButton("Paste Clipboard")
        self.btn_paste.clicked.connect(self.paste_from_clipboard)
        r1.addWidget(self.btn_paste)
        top_layout.addLayout(r1)

        # Row 2: Folder input
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Save Folder (Optional):"))
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Default (Auto-create based on username)")
        r2.addWidget(self.folder_input)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_folder)
        r2.addWidget(btn_browse)
        top_layout.addLayout(r2)

        # Row 3: Buttons
        r3 = QHBoxLayout()
        self.btn_add = QPushButton("Download Now")
        self.btn_add.setObjectName("primaryButton")
        self.btn_add.clicked.connect(self.add_task)
        r3.addWidget(self.btn_add)

        r3.addSpacing(20)

        self.btn_scan = QPushButton("Xóa file trùng")
        self.btn_scan.setObjectName("warningButton")
        self.btn_scan.clicked.connect(self.scan_duplicates_ui)
        r3.addWidget(self.btn_scan)
        
        top_layout.addLayout(r3)
        top_group.setLayout(top_layout)
        download_layout.addWidget(top_group)

        # 2. Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["URL / ID", "Platform", "Save Folder", "Progress", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 200) # Progress column width
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSortingEnabled(False)
        self.table.setWordWrap(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        download_layout.addWidget(self.table)

        row_actions = QHBoxLayout()
        self.btn_download_selected = QPushButton("Download Selected")
        self.btn_download_selected.setObjectName("primaryButton")
        self.btn_download_selected.setMinimumWidth(150)
        self.btn_download_selected.clicked.connect(self.download_selected_row)
        row_actions.addWidget(self.btn_download_selected)

        self.btn_edit_selected_folder = QPushButton("Edit Folder")
        self.btn_edit_selected_folder.setMinimumWidth(110)
        self.btn_edit_selected_folder.clicked.connect(self.edit_row_folder)
        row_actions.addWidget(self.btn_edit_selected_folder)

        self.btn_remove_selected = QPushButton("Remove Selected")
        self.btn_remove_selected.setObjectName("dangerButton")
        self.btn_remove_selected.setMinimumWidth(140)
        self.btn_remove_selected.clicked.connect(self.remove_selected_row)
        row_actions.addWidget(self.btn_remove_selected)
        row_actions.addStretch()
        download_layout.addLayout(row_actions)

        tabs.addTab(tab_download, "📥 Downloads")

        # --- TAB 2: SETTINGS ---
        # Boc trong QScrollArea de noi dung khong bi nen/chong khi cao hon vung tab
        tab_settings = QWidget()
        tab_settings_outer = QVBoxLayout(tab_settings)
        tab_settings_outer.setContentsMargins(0, 0, 0, 0)

        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tab_settings_outer.addWidget(settings_scroll)

        settings_content = QWidget()
        settings_content.setStyleSheet("background: #141a20;")  # khop nen tab pane
        settings_scroll.setWidget(settings_content)
        settings_layout = QVBoxLayout(settings_content)
        settings_layout.setContentsMargins(14, 14, 14, 14)
        settings_layout.setSpacing(14)

        # General Settings (Default Folder)
        grp_general = QGroupBox("General Settings")
        gen_layout = QVBoxLayout()
        
        lbl_def = QLabel("Default Download Folder (for new/unknown users):")
        gen_layout.addWidget(lbl_def)
        
        h_def = QHBoxLayout()
        self.txt_default_folder = QLineEdit()
        self.txt_default_folder.setPlaceholderText("Select a folder to save videos from new users automatically...")
        h_def.addWidget(self.txt_default_folder)
        
        btn_browse_def = QPushButton("Browse...")
        btn_browse_def.clicked.connect(self.browse_default_folder)
        h_def.addWidget(btn_browse_def)
        
        btn_save_def = QPushButton("Save Config")
        btn_save_def.setObjectName("primaryButton")
        btn_save_def.clicked.connect(self.save_general_settings)
        h_def.addWidget(btn_save_def)
        
        gen_layout.addLayout(h_def)

        # Gioi han so luong tai dong thoi
        h_conc = QHBoxLayout()
        h_conc.addWidget(QLabel("Số lượng tải đồng thời (Max concurrent downloads):"))
        self.spin_max_concurrent = QSpinBox()
        self.spin_max_concurrent.setRange(1, 16)
        self.spin_max_concurrent.setValue(int(self.config.get("max_concurrent", 3)))
        self.spin_max_concurrent.setFixedWidth(70)
        self.spin_max_concurrent.valueChanged.connect(self.on_max_concurrent_changed)
        h_conc.addWidget(self.spin_max_concurrent)
        h_conc.addWidget(QLabel("(Instagram vẫn chạy tuần tự để tránh bị chặn 429)"))
        h_conc.addStretch()
        gen_layout.addLayout(h_conc)

        grp_general.setLayout(gen_layout)
        settings_layout.addWidget(grp_general)

        # IG Credentials Group
        grp_ig = QGroupBox("Instagram Credentials (User/Pass)")
        form_ig = QFormLayout()
        
        self.txt_ig_user = QLineEdit()
        self.txt_ig_pass = QLineEdit()
        self.txt_ig_pass.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_ig.addRow("Username:", self.txt_ig_user)
        form_ig.addRow("Password:", self.txt_ig_pass)
        
        btn_save_ig = QPushButton("Save Credentials")
        btn_save_ig.setObjectName("primaryButton")
        btn_save_ig.clicked.connect(self.save_ig_credentials)
        ig_btn_row = QHBoxLayout()
        ig_btn_row.addWidget(btn_save_ig)
        ig_btn_row.addStretch()
        form_ig.addRow("", ig_btn_row)
        
        grp_ig.setLayout(form_ig)
        settings_layout.addWidget(grp_ig)

        # IG Cookies
        grp_cookie_ig = QGroupBox("Instagram Cookie")
        ig_layout = QVBoxLayout()
        ig_layout.addWidget(QLabel("Paste full 'Cookie' header string for Instagram:"))
        
        self.txt_cookie_ig = QPlainTextEdit()
        self.txt_cookie_ig.setPlaceholderText("csrftoken=...; ds_user_id=...; sessionid=...")
        self.txt_cookie_ig.setMinimumHeight(110)
        self.txt_cookie_ig.setMaximumHeight(180)
        ig_layout.addWidget(self.txt_cookie_ig)
        
        btn_save_cookie_ig = QPushButton("Save Instagram Cookie")
        btn_save_cookie_ig.setObjectName("primaryButton")
        btn_save_cookie_ig.clicked.connect(lambda: self.save_manual_cookie("instagram"))
        ig_btn_wrap = QHBoxLayout()
        ig_btn_wrap.addWidget(btn_save_cookie_ig)
        ig_btn_wrap.addStretch()
        ig_layout.addLayout(ig_btn_wrap)
        grp_cookie_ig.setLayout(ig_layout)
        settings_layout.addWidget(grp_cookie_ig)

        # TikTok Cookies
        grp_cookie_tt = QGroupBox("TikTok Cookie (For 429 Errors)")
        tt_layout = QVBoxLayout()
        tt_layout.addWidget(QLabel("Paste full 'Cookie' header string for TikTok:"))
        
        self.txt_cookie_tt = QPlainTextEdit()
        self.txt_cookie_tt.setPlaceholderText("tt_chain_token=...; ttwid=...; ...")
        self.txt_cookie_tt.setMinimumHeight(110)
        self.txt_cookie_tt.setMaximumHeight(180)
        tt_layout.addWidget(self.txt_cookie_tt)
        
        btn_save_cookie_tt = QPushButton("Save TikTok Cookie")
        btn_save_cookie_tt.setObjectName("primaryButton")
        btn_save_cookie_tt.clicked.connect(lambda: self.save_manual_cookie("tiktok"))
        tt_btn_wrap = QHBoxLayout()
        tt_btn_wrap.addWidget(btn_save_cookie_tt)
        tt_btn_wrap.addStretch()
        tt_layout.addLayout(tt_btn_wrap)
        grp_cookie_tt.setLayout(tt_layout)
        settings_layout.addWidget(grp_cookie_tt)
        
        settings_layout.addStretch() # Push everything up
        
        tabs.addTab(tab_settings, "⚙️ Settings")

        # 3. Bottom Panel (Activity Log) - Shared across tabs
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(1500)
        log_font = QFont("Consolas")
        log_font.setStyleHint(QFont.StyleHint.Monospace)
        log_font.setPointSize(10)
        self.log_output.setFont(log_font)
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        
        main_layout.addWidget(log_group)
        
        # Status Bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Load Settings Data on Init
        self.load_settings_tab_data()

    def toggle_window_size(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_window_maximize.setText("Maximize")
        else:
            self.showMaximized()
            self.btn_window_maximize.setText("Restore")

    def load_settings_tab_data(self):
        # Load Default Folder
        def_folder = self.config.get("default_download_folder", "")
        if def_folder:
            self.txt_default_folder.setText(def_folder)

        # Load IG Creds
        creds = self.downloader.load_credentials()
        if creds:
            self.txt_ig_user.setText(creds[0])
            self.txt_ig_pass.setText(creds[1])
            
        # Load Cookies (New JSON system)
        ig_cookie = self.downloader.get_manual_cookie("instagram")
        if ig_cookie:
            self.txt_cookie_ig.setPlainText(ig_cookie)

        tt_cookie = self.downloader.get_manual_cookie("tiktok")
        if tt_cookie:
            self.txt_cookie_tt.setPlainText(tt_cookie)

    def select_directory(self, title, start_dir=None):
        start_dir = start_dir if start_dir and os.path.isdir(start_dir) else self.base_dir
        try:
            return QFileDialog.getExistingDirectory(
                self,
                title,
                start_dir,
                QFileDialog.Option.ShowDirsOnly,
            )
        except Exception as e:
            self.log(f"Folder picker failed: {e}", "ERROR")
            return ""

    def browse_default_folder(self):
        folder = self.select_directory("Select Default Download Folder", self.txt_default_folder.text().strip())
        if folder:
            self.txt_default_folder.setText(folder)

    def save_general_settings(self):
        folder = self.txt_default_folder.text().strip()
        self.config["default_download_folder"] = folder
        self.save_config()
        QMessageBox.information(self, "Saved", "General settings saved successfully.")
        self.log(f"Default download folder updated to: {folder}", "SUCCESS")

    def on_max_concurrent_changed(self, value):
        applied = self._apply_max_concurrent(value)
        self.config["max_concurrent"] = applied
        self.save_config()
        self.log(f"Số luồng tải đồng thời: {applied}", "INFO")

    def save_ig_credentials(self):
        user = self.txt_ig_user.text().strip()
        pwd = self.txt_ig_pass.text().strip()
        if not user or not pwd:
            QMessageBox.warning(self, "Missing Info", "Please enter both username and password.")
            return
            
        self.downloader.save_credentials(user, pwd)
        QMessageBox.information(self, "Saved", "Instagram credentials saved successfully.")
        self.log("Instagram credentials updated.", "SUCCESS")

    def save_manual_cookie(self, platform):
        if platform == "instagram":
             cookie = self.txt_cookie_ig.toPlainText().strip()
             label = "Instagram"
        elif platform == "tiktok":
             cookie = self.txt_cookie_tt.toPlainText().strip()
             label = "TikTok"
        else:
             return

        if self.downloader.set_manual_cookie(platform, cookie):
            QMessageBox.information(self, "Saved", f"{label} cookie saved successfully.")
            self.log(f"{label} cookie updated.", "SUCCESS")
        else:
            QMessageBox.critical(self, "Error", f"Failed to save {label} cookie.")


    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        self.url_input.setText(clipboard.text())

    def log(self, message, level="INFO"):
        timestamp = time.strftime("%H:%M:%S")
        color = "#d4d4d4" # INFO
        if level == "ERROR": color = "#ff5555"
        if level == "SUCCESS": color = "#50fa7b"
        
        html = f'<span style="color: #6272a4;">[{timestamp}]</span> <span style="font-weight:bold; color:{color};">[{level}]</span> {message}'
        self.log_output.appendHtml(html)

    def load_saved_links(self):
        # Load previously saved links from config
        saved_links = self.config.get("saved_links", [])
        if not saved_links:
            return

        self.log(f"Loading {len(saved_links)} saved links from history...", "INFO")
        for item in saved_links:
            url = item.get("url", "")
            folder = item.get("folder", "")
            if not url: continue
            
            # Simple platform check
            platform = "Unknown"
            if "tiktok" in url: platform = "TikTok"
            elif "facebook" in url: platform = "Facebook"
            elif "instagram" in url: platform = "Instagram"
            
            self.add_table_row(url, platform, folder, auto_start=False, status="History")

    def add_table_row(self, url, platform, folder="", auto_start=True, status="Queued"):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Col 0: URL
        self.table.setItem(row, 0, QTableWidgetItem(url))
        
        # Col 1: Platform
        self.table.setItem(row, 1, QTableWidgetItem(platform))
        
        # Col 2: Save Folder
        self.table.setItem(row, 2, QTableWidgetItem(folder))
        
        # Col 3: Progress (thanh tien trinh that cho moi file/dong)
        pbar = QProgressBar()
        pbar.setRange(0, 100)
        pbar.setValue(100 if status == "Completed" else 0)
        pbar.setTextVisible(True)
        pbar.setFormat("%p%")
        pbar.setStyleSheet(PROGRESS_STYLE_DEFAULT)
        self.table.setCellWidget(row, 3, pbar)

        # Col 4: Status
        self.table.setItem(row, 4, QTableWidgetItem(status))
        
        if auto_start:
            self.start_download(url, platform, row)

    def find_row_by_url(self, url):
        # Scan column 0
        filters = self.table.findItems(url, Qt.MatchFlag.MatchExactly)
        if filters:
            return filters[0].row()
        return -1

    def trigger_download_by_url(self, url, platform):
        row = self.find_row_by_url(url)
        if row >= 0:
            self.start_download(url, platform, row)

    def selected_row(self):
        row = self.table.currentRow()
        return row if 0 <= row < self.table.rowCount() else -1

    def download_selected_row(self):
        row = self.selected_row()
        if row < 0:
            self.log("Select a row before downloading.", "ERROR")
            return
        url_item = self.table.item(row, 0)
        platform_item = self.table.item(row, 1)
        if not url_item or not platform_item:
            return
        self.start_download(url_item.text(), platform_item.text(), row)

    def remove_selected_row(self):
        row = self.selected_row()
        if row < 0:
            self.log("Select a row before removing.", "ERROR")
            return
        url_item = self.table.item(row, 0)
        if not url_item:
            return
        self.delete_task_by_url(url_item.text(), confirm=False)

    def delete_task_by_url(self, url, confirm=True):
        # Confirm
        if confirm:
            answer = QMessageBox.question(self, "Remove Link",
                                        f"Remove this link from list?\n{url}",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return

        # 1. Update Config
        original_count = len(self.config["saved_links"])
        self.config["saved_links"] = [x for x in self.config["saved_links"] if x.get("url") != url]
        if len(self.config["saved_links"]) < original_count:
            self.save_config()
        
        # 2. Remove from Table
        row = self.find_row_by_url(url)
        if row >= 0:
            self.table.removeRow(row)
            self.log(f"Removed link: {url}", "INFO")

    def sanitize_account_name(self, value):
        value = (value or "").strip().strip("@")
        safe = "".join(c for c in value if c.isalnum() or c in ("-", "_", ".", " ")).strip()
        return safe or None

    def identify_platform(self, url):
        host = urlparse(url.strip()).netloc.lower()
        if "tiktok.com" in host or "douyin.com" in host or "vt.tiktok.com" in host:
            return "TikTok"
        if "instagram.com" in host:
            return "Instagram"
        if "facebook.com" in host or "fb.watch" in host:
            return "Facebook"
        return "Unknown"

    def extract_username_from_url(self, url):
        url = url.strip()
        platform = self.identify_platform(url)

        if platform == "TikTok":
            match_tt = re.search(r'(?:tiktok\.com|douyin\.com)/@([^/?#]+)', url, re.IGNORECASE)
            return self.sanitize_account_name(match_tt.group(1)) if match_tt else None, platform

        if platform == "Instagram":
            parsed = urlparse(url)
            parts = [p for p in parsed.path.split("/") if p]
            if not parts:
                return None, platform
            reserved = {
                "p", "reel", "reels", "stories", "explore", "explorer",
                "tv", "accounts", "direct", "share",
            }
            if parts[0].lower() in reserved:
                # Post/reel/story links need Instaloader to resolve the real owner.
                return None, platform
            return self.sanitize_account_name(parts[0]), platform

        if platform == "Facebook":
            parsed = urlparse(url)
            if "fb.watch" in parsed.netloc.lower():
                return None, platform
            parts = [p for p in parsed.path.split("/") if p]
            if not parts:
                return None, platform
            reserved = {"watch", "reel", "videos", "share", "story.php", "photo.php", "groups"}
            if parts[0].lower() in reserved:
                # watch/reel/share links need yt-dlp metadata to resolve the real owner.
                return None, platform
            return self.sanitize_account_name(parts[0]), platform

        return None, platform

    def resolve_folder_for_url(self, url):
        username, platform = self.extract_username_from_url(url)
        if not username:
             return None, platform
             
        # 1. Check saved links (History) logic
        # We look for an entry where the saved URL contains this username
        saved_links = self.config.get("saved_links", [])
        for item in saved_links:
            s_url = item.get("url", "")
            s_folder = item.get("folder", "")
            if not s_url or not s_folder: continue
            
            # Simple check: if username matches?
            s_user, s_platform = self.extract_username_from_url(s_url)
            if s_user and s_platform == platform and s_user.lower() == username.lower():
                self.log(f"Found existing folder for user '{username}': {s_folder}", "INFO")
                return s_folder, platform
                
        # 2. Check Default Folder
        default_root = self.config.get("default_download_folder", "")
        if default_root and os.path.exists(default_root):
            # We create a subfolder for the user to keep things organized
            # user asked "lưu trong thư mục đó luôn", but usually means inside the configured root.
            # To be safe and organized, we append username.
            # If user wanted flat structure, they would select specific folder.
            # But let's follow standard downloader pattern: Root/Username
            new_folder = os.path.join(default_root, username)
            return new_folder, platform
            
        return None, platform

    def add_task(self):
        url = self.url_input.text().strip()
        # Allow user input folder to override everything
        user_folder = self.folder_input.text().strip()
        
        if not url:
            return
        
        self.url_input.clear()
        
        # Resolve Folder and Platform
        final_folder = user_folder
        
        # Identify Platform and Folder Auto-Resolution if no user folder supplied
        resolved_folder, platform = self.resolve_folder_for_url(url)
        
        if not final_folder:
            final_folder = resolved_folder
        else:
            # If user manually selected a folder, verify if we should save this preference?
            pass

        if not final_folder:
            # Still no folder? 
            pass # MasterDownloader will handle default logic or use CWD
            
        # Identify Platform (fallback if resolve failed)
        if platform == "Unknown":
            if "tiktok" in url: platform = "TikTok"
            elif "facebook" in url: platform = "Facebook"
            elif "instagram" in url: platform = "Instagram"
        
        # Check duplicate before adding? 
        # For now, just add
        self.add_table_row(url, platform, final_folder if final_folder else "", auto_start=True)
        
        # Save to history/config
        # We only add to "saved_links" if it's a new unique user/link of interest?
        # Or just append everything? Original logic appended everything.
        # But if we auto-resolved, maybe we update the entry?
        
        entry = {"url": url, "folder": final_folder if final_folder else ""}
        
        # Avoid duplicate URLs in saved_links to keep config clean?
        # User might paste same link again.
        exists = False
        for item in self.config["saved_links"]:
            if item["url"] == url:
                item["folder"] = final_folder # Update folder preference
                exists = True
                break
        
        if not exists:
            self.config["saved_links"].append(entry)
            
        self.save_config()

    def browse_folder(self):
        folder = self.select_directory("Select Download Folder", self.folder_input.text().strip())
        if folder:
            self.folder_input.setText(folder)

    def edit_row_folder(self):
        row = self.table.currentRow()
        if row < 0: return

        current_url = self.table.item(row, 0).text()
        current_folder = self.table.item(row, 2).text()

        folder = self.select_directory("Select New Folder", current_folder or self.base_dir)
        if folder:
            self.table.setItem(row, 2, QTableWidgetItem(folder))
            self.log(f"Updated folder for row {row} to: {folder}", "INFO")
            
            # Update Config
            for item in self.config["saved_links"]:
                if item["url"] == current_url:
                    item["folder"] = folder
                    self.save_config()
                    break

    def start_download(self, url, platform, row_id):
        self.log(f"Preparing download: {platform} | {url}", "INFO")

        # Change button to "Running" or disable it
        self.update_status(row_id, "Queued")

        # Reset thanh tien trinh ve 0 + style mac dinh (truong hop tai lai)
        self.failed_rows.discard(row_id)
        self._log_pct_bucket.pop(row_id, None)
        bar = self.table.cellWidget(row_id, 3) if row_id < self.table.rowCount() else None
        if isinstance(bar, QProgressBar):
            bar.setStyleSheet(PROGRESS_STYLE_DEFAULT)
            bar.setValue(0)

        # Get Folder
        folder_item = self.table.item(row_id, 2)
        folder = folder_item.text() if folder_item else None
        if not folder: folder = None

        # Select function
        if platform == "Instagram":
            func = self.downloader.download_instagram
        elif platform == "TikTok":
            func = self.downloader.download_tiktok
        elif platform == "Facebook":
            func = self.downloader.download_facebook
        else:
             self.log(f"Unsupported URL: {url}", "ERROR")
             return

        # Create Worker
        worker = DownloadWorker(func, row_id, url, output_folder=folder)
        
        # Connect Signals
        worker.signals.progress.connect(self.handle_progress)
        worker.signals.finished.connect(lambda: self.handle_finished(row_id))
        worker.signals.error.connect(lambda err: self.handle_error(row_id, err))
        
        self.threadpool.start(worker)
        self.log(f"Started download for row {row_id}: {platform}", "INFO")

    @staticmethod
    def _parse_percent(percent_str):
        """'45.2%' -> 45 (int 0..100), tra ve None neu khong doc duoc."""
        if not percent_str:
            return None
        try:
            return max(0, min(100, int(round(float(percent_str.replace("%", "").strip())))))
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _ascii_bar(pct, width=20):
        filled = int(round(pct / 100 * width))
        return "█" * filled + "░" * (width - filled)

    def _set_row_progress(self, row_id, pct):
        """Cap nhat thanh tien trinh that o cot 3 cho dong row_id."""
        if row_id < 0 or row_id >= self.table.rowCount():
            return
        bar = self.table.cellWidget(row_id, 3)
        if isinstance(bar, QProgressBar) and pct is not None:
            bar.setValue(pct)

    def handle_progress(self, data):
        row_id, percent_str, speed_str, msg = data

        # Internal log messages (row_id = -1 for global tools)
        if row_id == -1:
            # Optionally log to text area if needed, or just update status bar
            self.status_bar.showMessage(msg)
            # Log significant messages
            if "Deleted" in msg or "Checking" in msg:
                 # Reduce spam in main log, only show if specific
                 pass
            return

        # Validate row (simple check)
        if row_id >= self.table.rowCount():
            return

        pct = self._parse_percent(percent_str)

        # Cap nhat thanh tien trinh that tren bang
        self._set_row_progress(row_id, pct)

        # Update Status Column
        self.table.setItem(row_id, 4, QTableWidgetItem("Downloading"))

        # Thanh tien trinh ASCII trong log (throttle theo buoc 10% de tranh spam)
        if pct is not None:
            bucket = pct // 10
            if self._log_pct_bucket.get(row_id) != bucket:
                self._log_pct_bucket[row_id] = bucket
                detail = msg.strip() if msg else ""
                self.log(f"Row {row_id} [{self._ascii_bar(pct)}] {pct:3d}% {('| ' + detail) if detail else ''}", "INFO")

    def handle_finished(self, row_id):
        self._log_pct_bucket.pop(row_id, None)
        if row_id in self.failed_rows:
            self.failed_rows.discard(row_id)
            return
        self.update_status(row_id, "Completed")
        self._set_row_progress(row_id, 100)
        bar = self.table.cellWidget(row_id, 3) if row_id < self.table.rowCount() else None
        if isinstance(bar, QProgressBar):
            bar.setStyleSheet(PROGRESS_STYLE_SUCCESS)
        self.log(f"Download Finished (Row {row_id})", "SUCCESS")

    def handle_error(self, row_id, err_info):
        self._log_pct_bucket.pop(row_id, None)
        self.failed_rows.add(row_id)
        exctype, value, traceback_str = err_info
        self.update_status(row_id, "Error")
        bar = self.table.cellWidget(row_id, 3) if row_id < self.table.rowCount() else None
        if isinstance(bar, QProgressBar):
            bar.setStyleSheet(PROGRESS_STYLE_ERROR)
        self.log(f"Error on row {row_id}: {value}", "ERROR")
        print(traceback_str)

    def scan_duplicates_ui(self):
        # Chon thu muc can quet (uu tien thu muc tai mac dinh)
        start = self.config.get("default_download_folder") or self.base_dir
        folder = self.select_directory("Chọn thư mục quét file trùng (ảnh + video)", start)
        if not folder:
            return

        self.log(f"Đang quét file trùng trong: {folder}", "INFO")
        self.btn_scan.setEnabled(False)

        worker = DuplicateWorker(self.downloader, folder)
        worker.signals.progress.connect(self.handle_progress)  # log qua row_id = -1
        worker.signals.result.connect(self.handle_scan_result)
        worker.signals.error.connect(self._on_scan_error)
        worker.signals.finished.connect(lambda: self.btn_scan.setEnabled(True))
        self.threadpool.start(worker)

    def _on_scan_error(self, err):
        self.btn_scan.setEnabled(True)
        self.log(f"Lỗi khi quét file trùng: {err[1]}", "ERROR")

    def handle_scan_result(self, result):
        groups, resurrected = result
        if not groups and not resurrected:
            self.log("Quét xong. Không tìm thấy file trùng.", "SUCCESS")
            QMessageBox.information(self, "Hoàn tất", "Không tìm thấy file trùng nào.")
            return

        dlg = DuplicatesDialog(groups, self, resurrected=resurrected)
        if not dlg.exec():
            self.log("Đã hủy xóa file trùng.", "INFO")
            return

        paths = dlg.selected_paths()
        if not paths:
            self.log("Không có mục nào được chọn để xóa.", "INFO")
            return

        deleted, freed = self.downloader.delete_paths(
            paths, status_callback=lambda m: self.log(m, "INFO")
        )
        self.log(f"Đã xóa {deleted} file trùng, giải phóng {human_size(freed)}.", "SUCCESS")
        QMessageBox.information(
            self, "Hoàn tất",
            f"Đã xóa {deleted} file trùng.\nGiải phóng {human_size(freed)}."
        )

    def update_status(self, row_id, text):
        if row_id < self.table.rowCount():
            self.table.setItem(row_id, 4, QTableWidgetItem(text))

if __name__ == "__main__":
    enable_crash_logging()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Check dependencies
    try:
        import yt_dlp
    except ImportError:
        QMessageBox.critical(None, "Missing Dependency", "yt_dlp is missing.")
        sys.exit(1)
        
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
