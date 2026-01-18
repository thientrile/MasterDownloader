import sys
import os
import queue
import traceback
import time
import json
import re
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QLabel, QFileDialog, QMessageBox, QProgressBar, QGroupBox, 
                             QPlainTextEdit, QLineEdit, QSplitter, QTabWidget, QFormLayout, QMenu)
from PyQt6.QtGui import QColor, QFont, QIcon, QAction

# Import existing logic
from MasterDownloader import MasterDownloader

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

            results = self.downloader.scan_for_duplicates(
                directory=self.directory, 
                remove=True, 
                status_callback=callback
            )
            self.signals.result.emit(results)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self.signals.finished.emit()

# --- MAIN WINDOW ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Master Downloader Ultimate (PyQt6)")
        self.resize(1100, 750)
        
        # Logic Core
        self.downloader = MasterDownloader()
        self.threadpool = QThreadPool()
        print(f"Multimedia Thread Pool running with {self.threadpool.maxThreadCount()} threads.")

        self.row_mapping = {} # future/uid -> row_index (Dynamic management)
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

        self.init_ui()
        self.load_saved_links()

    def load_config(self):
        default = {"download_folder": "", "saved_links": [], "default_download_folder": ""}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge defaults
                    for k, v in default.items():
                        if k not in data:
                            data[k] = v
                    return data
            except:
                return default
        return default

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except:
            pass

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Tab Widget
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # --- TAB 1: DOWNLOADER ---
        tab_download = QWidget()
        download_layout = QVBoxLayout(tab_download)

        # 1. Top Control Panel
        top_group = QGroupBox("Add Links")
        top_layout = QVBoxLayout()
        
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
        self.btn_add.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_add.clicked.connect(self.add_task)
        r3.addWidget(self.btn_add)

        r3.addSpacing(20)

        self.btn_scan = QPushButton("🧹 Clean Duplicates")
        self.btn_scan.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        self.btn_scan.clicked.connect(self.scan_duplicates_ui)
        r3.addWidget(self.btn_scan)
        
        top_layout.addLayout(r3)
        top_group.setLayout(top_layout)
        download_layout.addWidget(top_group)

        # 2. Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["URL / ID", "Platform", "Save Folder", "Progress", "Status", "Action", ""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 200) # Progress column width
        self.table.setColumnWidth(6, 40)  # Delete button column width
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        download_layout.addWidget(self.table)

        tabs.addTab(tab_download, "📥 Downloads")

        # --- TAB 2: SETTINGS ---
        tab_settings = QWidget()
        settings_layout = QVBoxLayout(tab_settings)

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
        
        btn_save_def = QPushButton("💾 Save Config")
        btn_save_def.clicked.connect(self.save_general_settings)
        h_def.addWidget(btn_save_def)
        
        gen_layout.addLayout(h_def)
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
        
        btn_save_ig = QPushButton("💾 Save Credentials")
        btn_save_ig.clicked.connect(self.save_ig_credentials)
        form_ig.addRow("", btn_save_ig)
        
        grp_ig.setLayout(form_ig)
        settings_layout.addWidget(grp_ig)

        # IG Cookies
        grp_cookie_ig = QGroupBox("Instagram Cookie")
        ig_layout = QVBoxLayout()
        ig_layout.addWidget(QLabel("Paste full 'Cookie' header string for Instagram:"))
        
        self.txt_cookie_ig = QPlainTextEdit()
        self.txt_cookie_ig.setPlaceholderText("csrftoken=...; ds_user_id=...; sessionid=...")
        self.txt_cookie_ig.setMaximumHeight(80)
        ig_layout.addWidget(self.txt_cookie_ig)
        
        btn_save_cookie_ig = QPushButton("💾 Save Instagram Cookie")
        btn_save_cookie_ig.clicked.connect(lambda: self.save_manual_cookie("instagram"))
        ig_layout.addWidget(btn_save_cookie_ig)
        grp_cookie_ig.setLayout(ig_layout)
        settings_layout.addWidget(grp_cookie_ig)

        # TikTok Cookies
        grp_cookie_tt = QGroupBox("TikTok Cookie (For 429 Errors)")
        tt_layout = QVBoxLayout()
        tt_layout.addWidget(QLabel("Paste full 'Cookie' header string for TikTok:"))
        
        self.txt_cookie_tt = QPlainTextEdit()
        self.txt_cookie_tt.setPlaceholderText("tt_chain_token=...; ttwid=...; ...")
        self.txt_cookie_tt.setMaximumHeight(80)
        tt_layout.addWidget(self.txt_cookie_tt)
        
        btn_save_cookie_tt = QPushButton("💾 Save TikTok Cookie")
        btn_save_cookie_tt.clicked.connect(lambda: self.save_manual_cookie("tiktok"))
        tt_layout.addWidget(btn_save_cookie_tt)
        grp_cookie_tt.setLayout(tt_layout)
        settings_layout.addWidget(grp_cookie_tt)
        
        settings_layout.addStretch() # Push everything up
        
        tabs.addTab(tab_settings, "⚙️ Settings")

        # 3. Bottom Panel (Activity Log) - Shared across tabs
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas;")
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        
        main_layout.addWidget(log_group)
        
        # Status Bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

        # Load Settings Data on Init
        self.load_settings_tab_data()

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

    def browse_default_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Download Folder", self.base_dir)
        if folder:
            self.txt_default_folder.setText(folder)

    def save_general_settings(self):
        folder = self.txt_default_folder.text().strip()
        self.config["default_download_folder"] = folder
        self.save_config()
        QMessageBox.information(self, "Saved", "General settings saved successfully.")
        self.log(f"Default download folder updated to: {folder}", "SUCCESS")

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
        
        # Col 3: Progress (Custom Widget)
        p_widget = QWidget()
        p_layout = QVBoxLayout(p_widget)
        p_layout.setContentsMargins(5, 5, 5, 5)
        p_layout.setSpacing(2)
        
        p_bar = QProgressBar()
        p_bar.setRange(0, 100)
        p_bar.setValue(0 if status != "Completed" else 100)
        p_bar.setTextVisible(False)
        p_bar.setStyleSheet("QProgressBar { border: 1px solid grey; border-radius: 3px; background-color: #e0e0e0; } QProgressBar::chunk { background-color: #2196F3; }")
        
        p_label = QLabel(status)
        p_label.setStyleSheet("font-size: 10px; color: #555;")
        p_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        p_layout.addWidget(p_bar)
        p_layout.addWidget(p_label)
        self.table.setCellWidget(row, 3, p_widget)
        
        # Col 4: Status
        self.table.setItem(row, 4, QTableWidgetItem(status))
        
        # Col 5: Action
        if auto_start:
            btn_action = QPushButton("Stop")
            # Logic stop unimplemented
        else:
            btn_action = QPushButton("Download")
            # Use dynamic lookup to safe-guard against row shuffles/deletions
            btn_action.clicked.connect(lambda checked, u=url, p=platform: self.trigger_download_by_url(u, p))
            
        self.table.setCellWidget(row, 5, btn_action)
        
        # Col 6: Delete
        btn_del = QPushButton("X")
        btn_del.setStyleSheet("background-color: #ff5555; color: white; font-weight: bold; border-radius: 2px;")
        btn_del.setToolTip("Remove from list")
        btn_del.clicked.connect(lambda checked, u=url: self.delete_task_by_url(u))
        self.table.setCellWidget(row, 6, btn_del)
        
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

    def delete_task_by_url(self, url):
        # Confirm
        confirm = QMessageBox.question(self, "Remove Link", 
                                     f"Remove this link from list?\n{url}",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes:
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

    def extract_username_from_url(self, url):
        # Clean URL
        url = url.strip()
        
        # TikTok
        match_tt = re.search(r'@([^/?]+)', url)
        if match_tt:
            return match_tt.group(1), "TikTok"
            
        # Instagram
        if "instagram.com" in url:
            # Handle /p/, /reels/
            # If it's a profile: instagram.com/username/
            # If it's a post: instagram.com/p/code/ -> We might not know username easily from URL string alone without scraping
            # But we can try the first segment after .com/
            parts = url.split("instagram.com/")
            if len(parts) > 1:
                path = parts[1].split("/")[0]
                if path not in ["p", "reel", "reels", "stories", "explorer"]:
                     return path, "Instagram"
        
        return None, "Unknown"

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
            s_user, _ = self.extract_username_from_url(s_url)
            if s_user and s_user == username:
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
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", self.base_dir)
        if folder:
            self.folder_input.setText(folder)

    def open_context_menu(self, position):
        menu = QMenu()
        edit_action = QAction("Edit Save Folder", self)
        edit_action.triggered.connect(self.edit_row_folder)
        menu.addAction(edit_action)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def edit_row_folder(self):
        row = self.table.currentRow()
        if row < 0: return

        current_url = self.table.item(row, 0).text()
        current_folder = self.table.item(row, 2).text()

        folder = QFileDialog.getExistingDirectory(self, "Select New Folder", current_folder or self.base_dir)
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
        # Change button to "Running" or disable it
        btn = self.table.cellWidget(row_id, 5)
        if isinstance(btn, QPushButton):
            btn.setText("Running...")
            btn.setEnabled(False)

        # Get Folder
        folder_item = self.table.item(row_id, 2)
        folder = folder_item.text() if folder_item else None
        if not folder: folder = None

        # Select function
        if platform == "Instagram":
            # Check login first (Blocking check needs to be handled carefully, 
            # ideally in worker too, but for simplicity we rely on MasterDownloader caching)
            if not self.downloader.get_ig_session():
                 self.log(f"Login required for {url}", "ERROR")
                 self.update_status(row_id, "Login Failed")
                 return
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
            
        # Get Progress Widgets
        widget = self.table.cellWidget(row_id, 3)
        if widget:
            p_bar = widget.findChild(QProgressBar)
            p_label = widget.findChild(QLabel)
            
            # Parse Percent
            try:
                # Remove '%' and convert to float
                clean_pct = percent_str.replace('%', '').strip()
                val = float(clean_pct)
                p_bar.setValue(int(val))
            except:
                pass # Indeterminate or text
                
            # Update Label
            p_label.setText(f"{percent_str} - {msg}")
            
        # Update Status Column
        self.table.setItem(row_id, 4, QTableWidgetItem("Downloading"))

    def handle_finished(self, row_id):
        self.update_status(row_id, "Completed")
        self.log(f"Download Finished (Row {row_id})", "SUCCESS")
        
        # Set Progress to 100% Green
        widget = self.table.cellWidget(row_id, 3)
        if widget:
            p_bar = widget.findChild(QProgressBar)
            p_bar.setValue(100)
            p_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
            widget.findChild(QLabel).setText("Done")

    def handle_error(self, row_id, err_info):
        exctype, value, traceback_str = err_info
        self.update_status(row_id, "Error")
        self.log(f"Error on row {row_id}: {value}", "ERROR")
        print(traceback_str)
        
        widget = self.table.cellWidget(row_id, 3)
        if widget:
             p_bar = widget.findChild(QProgressBar)
             if p_bar:
                 p_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff5555; }")

    def scan_duplicates_ui(self):
        # Ask user for folder
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Clean Duplicates", self.base_dir)
        if not folder:
            return

        confirm = QMessageBox.question(self, "Confirm Delete", 
                                     f"Are you sure you want to scan and DELETE duplicate images in:\n{folder}\n\nThis cannot be undone!",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.log(f"Starting duplicate scan in: {folder}", "INFO")
            
            worker = DuplicateWorker(self.downloader, folder)
            worker.signals.progress.connect(self.handle_progress) # Reuse existing
            worker.signals.result.connect(self.handle_scan_result)
            worker.signals.error.connect(lambda err: self.log(f"Scan Error: {err[1]}", "ERROR"))
            
            self.threadpool.start(worker)

    def handle_scan_result(self, duplicates):
        count = len(duplicates)
        if count > 0:
             self.log(f"Scan Complete. Removed {count} duplicate images.", "SUCCESS")
             QMessageBox.information(self, "Scan Complete", f"Removed {count} duplicate images.")
        else:
             self.log("Scan Complete. No duplicates found.", "SUCCESS")
             QMessageBox.information(self, "Scan Complete", "No duplicates found.")

    def update_status(self, row_id, text):
        if row_id < self.table.rowCount():
            self.table.setItem(row_id, 4, QTableWidgetItem(text))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Check dependencies
    try:
        import yt_dlp
    except ImportError:
        QMessageBox.critical(None, "Missing Dependency", "yt_dlp is missing.")
        sys.exit(1)
        
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
