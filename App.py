import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import sys
import threading
import re
import queue
from MasterDownloader import MasterDownloader

# --- ANSI Code cleaning for GUI Log ---
# We will now PARSE ANSI instead of stripping it
ANSI_REGEX = re.compile(r'(\x1b\[[0-9;]*m)')

class RedirectText:
    def __init__(self, text_widget, queue):
        self.text_widget = text_widget
        self.queue = queue

    def write(self, string):
        if string:
            self.queue.put(string)

    def flush(self):
        pass

class FolderSelectionDialog(tk.Toplevel):
    def __init__(self, parent, folders):
        super().__init__(parent)
        self.title("Chọn thư mục quét ảnh")
        self.geometry("500x350")
        self.result = None
        self.folders = folders
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        
    def create_widgets(self):
        ttk.Label(self, text="Chọn một thư mục từ danh sách đã lưu hoặc duyệt tìm:", font=("Segoe UI", 10, "bold")).pack(pady=10, padx=10, anchor="w")
        
        # Listbox with Scrollbar
        frame_list = ttk.Frame(self)
        frame_list.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.listbox = tk.Listbox(frame_list, font=("Segoe UI", 10), height=8)
        self.listbox.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(frame_list, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate
        for f in self.folders:
            self.listbox.insert("end", f)
            
        if self.folders:
            self.listbox.selection_set(0)
            
        # Bind double click
        self.listbox.bind("<Double-1>", lambda e: self.on_select())
            
        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=15)
        
        ttk.Button(btn_frame, text="📂 Duyệt thư mục khác...", command=self.on_browse).pack(side="left")
        
        ttk.Button(btn_frame, text="Hủy", command=self.on_cancel).pack(side="right", padx=(5, 0))
        ttk.Button(btn_frame, text="✅ Chọn Quyét", command=self.on_select, style="Accent.TButton").pack(side="right")
        
    def on_browse(self):
        d = filedialog.askdirectory(title="Chọn thư mục")
        if d:
            self.result = d
            self.destroy()
            
    def on_select(self):
        sel = self.listbox.curselection()
        if sel:
            self.result = self.listbox.get(sel[0])
            self.destroy()
        else:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một thư mục hoặc bấm Duyệt.")
            
    def on_cancel(self):
        self.destroy()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Initialize Downloader Logic IMMEDIATELY to avoid AttributeError later
        # This fixes the issue where create_widgets -> load_settings calls self.downloader before it exists.
        self.downloader = MasterDownloader()

        self.title("Master Downloader Ultimate Manager")
        self.geometry("950x700")
        
        # --- THEME & STYLES ---
        style = ttk.Style(self)
        try:
            # Try to use 'vista' or 'xpnative' on Windows for better look
            style.theme_use('vista') 
        except:
            style.theme_use('clam') # Fallback to clam which is clean

        # Global Config
        self.configure(bg="#f0f0f0")
        
        # Configure Styles
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("TLabelframe", background="#f0f0f0")
        style.configure("TLabelframe.Label", background="#f0f0f0", font=("Segoe UI", 10, "bold"), foreground="#333")
        
        # Treeview Style
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=28)
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))
        
        # Special Accent Button Style
        style.configure("Accent.TButton", foreground="#0066cc", font=("Segoe UI", 10, "bold"))

        # Color Map for ANSI codes
        self.ansi_map = {
            '30': 'BLACK', '31': 'RED', '32': 'GREEN', '33': 'YELLOW',
            '34': 'BLUE', '35': 'MAGENTA', '36': 'CYAN', '37': 'WHITE',
            '90': 'GREY', '91': 'LRED', '92': 'LGREEN', '93': 'LYELLOW',
            '94': 'LBLUE', '95': 'LMAGENTA', '96': 'LCYAN', '97': 'LWHITE',
        }
        
        # Paths
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.config_file = os.path.join(self.base_dir, "gui_config.json")
        
        # Data
        self.config = self.load_config()
        self.log_queue = queue.Queue()
        self.is_downloading = False
        self.stop_event = threading.Event()

        # Initialize Downloader Logic (Moved to top of __init__) - keeping this check here
        # Override downloader base dir if user selected a custom one
        if self.config.get("download_folder"):
            folder = self.config["download_folder"]
            self.downloader.base_dir = folder
            self.downloader.data_dir = folder
            
            # Re-map all paths to the new folder
            self.downloader.session_dir = os.path.join(folder, "sessions")
            self.downloader.archive_dir = os.path.join(folder, "archives")
            self.downloader.history_file = os.path.join(folder, "history.json")
            self.downloader.ig_credentials_file = os.path.join(folder, "ig_credentials.txt")
            self.downloader.manual_cookie_file = os.path.join(folder, "manual_cookie.txt")
            
            # Ensure dirs exist
            os.makedirs(self.downloader.session_dir, exist_ok=True)
            os.makedirs(self.downloader.archive_dir, exist_ok=True)

        # UI Layout
        self.create_widgets()
        
        # Redirect stdout
        sys.stdout = RedirectText(self.log_area, self.log_queue)
        sys.stderr = RedirectText(self.log_area, self.log_queue)
        
        # Start log polling
        self.after(100, self.poll_log)

    def load_config(self):
        config = {"download_folder": "", "saved_links": []}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    config.update(data)
            except:
                pass
        
        # Upgrade legacy links (strings) to objects
        new_links = []
        for item in config["saved_links"]:
            if isinstance(item, str):
                new_links.append({"url": item, "folder": ""})
            else:
                new_links.append(item)
        config["saved_links"] = new_links
        return config

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")

    def create_widgets(self):
        # MAIN CONTAINER
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Bottom: Logs (Moved up to reserve space at bottom) ---
        log_frame = ttk.LabelFrame(main_container, text="Nhật ký hoạt động (Logs)", padding=(10, 5))
        log_frame.pack(fill="x", pady=(10, 0), side="bottom")

        self.log_area = scrolledtext.ScrolledText(log_frame, state="disabled", height=8, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True)
        
        # Configure Tags for Colors (Dracula Theme inspired)
        self.log_area.tag_config("NORMAL", foreground="#f8f8f2")
        self.log_area.tag_config("BLACK", foreground="#6272a4")
        self.log_area.tag_config("RED", foreground="#ff5555")
        self.log_area.tag_config("GREEN", foreground="#50fa7b")
        self.log_area.tag_config("YELLOW", foreground="#f1fa8c")
        self.log_area.tag_config("BLUE", foreground="#bd93f9")
        self.log_area.tag_config("MAGENTA", foreground="#ff79c6")
        self.log_area.tag_config("CYAN", foreground="#8be9fd")
        self.log_area.tag_config("WHITE", foreground="#ffffff")
        
        # Light variants
        self.log_area.tag_config("GREY", foreground="#6272a4")
        self.log_area.tag_config("LRED", foreground="#ff6e6e")
        self.log_area.tag_config("LGREEN", foreground="#69ff94")
        self.log_area.tag_config("LYELLOW", foreground="#ffffa5")
        self.log_area.tag_config("LBLUE", foreground="#d6acff")
        self.log_area.tag_config("LMAGENTA", foreground="#ff92d0")
        self.log_area.tag_config("LCYAN", foreground="#a4ffff")
        self.log_area.tag_config("LWHITE", foreground="#ffffff")

        # Fallback Tags
        self.log_area.tag_config("INFO", foreground="#d4d4d4")
        self.log_area.tag_config("ERROR", foreground="#ff5555")
        self.log_area.tag_config("SUCCESS", foreground="#50fa7b")
        self.log_area.tag_config("WARNING", foreground="#f1fa8c")

        # NOTEBOOK (TABS) - Pack AFTER log frame so it takes remaining space
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill="both", expand=True)

        # TAB 1: DOWNLOAD MANAGER
        self.tab_download = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_download, text="   ⬇️ Quản lý Tải   ")

        # TAB 2: CONFIGURATION
        self.tab_config = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_config, text="   ⚙️ Cấu hình   ")

        # --- BUILD TABS ---
        self.create_download_tab_content(self.tab_download)
        self.create_config_tab_content(self.tab_config)

    def create_download_tab_content(self, parent_frame):
        # --- Top: Global Folder Selection (Default) ---
        top_frame = ttk.LabelFrame(parent_frame, text="Thư mục gốc (Mặc định)", padding=(15, 10))
        top_frame.pack(fill="x", pady=(0, 10))

        self.lbl_folder = ttk.Label(top_frame, text=self.config.get("download_folder") or "Mặc định (theo script)", font=("Segoe UI", 10, "italic"))
        self.lbl_folder.pack(side="left", expand=True, fill="x", padx=5)
        
        btn_browse = ttk.Button(top_frame, text="Thay đổi...", command=self.choose_global_folder)
        btn_browse.pack(side="right")

        # --- Middle: Main Content ---
        mid_frame = ttk.Frame(parent_frame)
        mid_frame.pack(expand=True, fill="both", pady=5)

        # Left: List Management
        left_frame = ttk.LabelFrame(mid_frame, text="Danh sách Links / Accounts", padding=(15, 10))
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        input_frame = ttk.Frame(left_frame)
        input_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(input_frame, text="Link:").pack(side="left")
        self.entry_link = ttk.Entry(input_frame, font=("Segoe UI", 10))
        self.entry_link.pack(side="left", fill="x", expand=True, padx=10, ipady=4)
        self.entry_link.bind("<Return>", lambda e: self.add_link())
        
        self.btn_pick_folder = ttk.Button(input_frame, text="📁 Chọn Lẻ", command=self.pick_single_folder)
        self.btn_pick_folder.pack(side="left", padx=2)
        self.single_folder_path = "" 

        btn_add = ttk.Button(input_frame, text="➕ Thêm", command=self.add_link, style="Accent.TButton")
        btn_add.pack(side="left", padx=5)

        # List Area
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill="both", expand=True)

        columns = ("url", "folder")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="extended", height=15)
        self.tree.heading("url", text="URL / Username")
        self.tree.heading("folder", text="Thư mục lưu (Tùy chọn)")
        self.tree.column("url", width=350)
        self.tree.column("folder", width=200)
        
        self.tree.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.config(yscrollcommand=scrollbar.set)

        self.refresh_list()

        # Toolbar under list
        btn_toolbar = ttk.Frame(left_frame)
        btn_toolbar.pack(fill="x", pady=10)
        
        tk.Button(btn_toolbar, text="Xóa Đã Chọn", command=self.remove_selected, bg="#e0e0e0", relief="groove", padx=10).pack(side="left", padx=(0, 5))
        tk.Button(btn_toolbar, text="Sửa Folder", command=self.edit_selected_folder, bg="#e0e0e0", relief="groove", padx=10).pack(side="left", padx=5)
        tk.Button(btn_toolbar, text="Xóa Hết", command=self.clear_all, bg="#ffdddd", relief="groove", padx=10).pack(side="right")

        # Right: Actions (Sidebar)
        right_frame = ttk.LabelFrame(mid_frame, text="Bảng điều khiển", padding=(15, 10))
        right_frame.pack(side="right", fill="y")

        ttk.Label(right_frame, text="Chế độ tải:").pack(pady=(5, 10), anchor="w")
        
        self.btn_download_all = ttk.Button(right_frame, text="⬇️\nTẢI TẤT CẢ", command=self.start_download_all, width=15)
        self.btn_download_all.pack(fill="x", pady=5)
        
        self.btn_download_selected = ttk.Button(right_frame, text="⬇️ Tải Đã Chọn", command=self.start_download_selected)
        self.btn_download_selected.pack(fill="x", pady=(5, 5))

        self.btn_stop = ttk.Button(right_frame, text="⏹️ DỪNG LẠI", command=self.stop_download, state="disabled")
        self.btn_stop.pack(fill="x", pady=(0, 20))

        ttk.Separator(right_frame, orient="horizontal").pack(fill="x", pady=10)
        
        ttk.Button(right_frame, text="📂 Mở thư mục gốc", command=self.open_global_folder).pack(fill="x", pady=5)
        ttk.Button(right_frame, text="❌ Thoát", command=self.destroy).pack(side="bottom", fill="x", pady=5)

    def create_config_tab_content(self, parent_frame):
        # Container for Configs
        container = ttk.Frame(parent_frame)
        container.pack(fill="both", expand=True)

        # --- 1. Instagram Credentials ---
        ig_frame = ttk.LabelFrame(container, text="🔑 Tài khoản Instagram (User/Pass)", padding=15)
        ig_frame.pack(fill="x", pady=(0, 15))

        # Grid layout for cleaner inputs
        ig_frame.columnconfigure(1, weight=1)

        ttk.Label(ig_frame, text="Username:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_ig_user = ttk.Entry(ig_frame, width=30)
        self.entry_ig_user.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(ig_frame, text="Password:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.entry_ig_pass = ttk.Entry(ig_frame, width=30, show="*")
        self.entry_ig_pass.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        btn_save_ig = ttk.Button(ig_frame, text="💾 Lưu Tài Khoản", command=self.save_ig_credentials)
        btn_save_ig.grid(row=2, column=1, sticky="w", padx=5, pady=(10, 5))
        
        # Checkbox toggle password
        self.var_show_pass = tk.BooleanVar(value=False)
        chk_show = ttk.Checkbutton(ig_frame, text="Hiển thị mật khẩu", variable=self.var_show_pass, 
                                   command=lambda: self.entry_ig_pass.config(show="" if self.var_show_pass.get() else "*"))
        chk_show.grid(row=1, column=2, sticky="w", padx=5)

        # --- 2. Manual Cookies ---
        cookie_frame = ttk.LabelFrame(container, text="🍪 Instagram Manual Cookies (Dùng khi 2FA/Lỗi)", padding=15)
        cookie_frame.pack(fill="both", expand=True, pady=(0, 15))

        ttk.Label(cookie_frame, text="Dán toàn bộ Cookie string vào đây (key=value;...):").pack(anchor="w", pady=(0, 5))
        
        self.txt_cookie = scrolledtext.ScrolledText(cookie_frame, height=8, font=("Consolas", 9))
        self.txt_cookie.pack(fill="both", expand=True, pady=5)
        
        btn_save_cookie = ttk.Button(cookie_frame, text="💾 Lưu Cookie", command=self.save_cookie_manual)
        btn_save_cookie.pack(anchor="w", pady=5)
        
        # --- 3. Image Tools ---
        tools_frame = ttk.LabelFrame(container, text="🛠️ Công cụ Ảnh", padding=15)
        tools_frame.pack(fill="x", pady=(0, 15))
        
        self.btn_scan_dupes = ttk.Button(tools_frame, text="🔍 Quét & Xoá Ảnh Trùng Lặp (Nội dung)", command=self.scan_duplicates_thread)
        self.btn_scan_dupes.pack(anchor="w", pady=5)
        ttk.Label(tools_frame, text="* Tính năng này sẽ quét toàn bộ thư mục tải xuống và xoá các bản sao hình ảnh.").pack(anchor="w")
        
        # --- Load Data on start ---
        self.load_settings_to_ui()

    def load_settings_to_ui(self):
        # Load IG Credentials
        ig_file = self.downloader.ig_credentials_file
        if os.path.exists(ig_file):
            try:
                with open(ig_file, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                    if len(lines) >= 1: self.entry_ig_user.insert(0, lines[0].strip())
                    if len(lines) >= 2: self.entry_ig_pass.insert(0, lines[1].strip())
            except: pass

        # Load Cookie
        cookie_file = self.downloader.manual_cookie_file
        if os.path.exists(cookie_file):
            try:
                with open(cookie_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    self.txt_cookie.insert("1.0", content)
            except: pass

    def save_ig_credentials(self):
        user = self.entry_ig_user.get().strip()
        pwd = self.entry_ig_pass.get().strip()
        
        if not user or not pwd:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Username và Password")
            return
            
        try:
            with open(self.downloader.ig_credentials_file, "w", encoding="utf-8") as f:
                f.write(f"{user}\n{pwd}")
            messagebox.showinfo("Thành công", "Đã lưu thông tin tài khoản Instagram!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")

    def save_cookie_manual(self):
        cookie = self.txt_cookie.get("1.0", "end-1c").strip()
        
        try:
            with open(self.downloader.manual_cookie_file, "w", encoding="utf-8") as f:
                f.write(cookie)
            messagebox.showinfo("Thành công", "Đã lưu Cookie mới!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")




    def poll_log(self):
        try:
            current_tag = "NORMAL"
            while True:
                text = self.log_queue.get_nowait()
                if not text: continue

                self.log_area.configure(state="normal")
                
                # Handle Carriage Return (\r) for Progress Bars
                # If we encounter \r, we delete the current line content before writing new text
                
                segments = text.split('\r')
                for i, segment in enumerate(segments):
                    if i > 0:
                        # If this is not the first segment, it means we hit a \r
                        # Delete the text on the current logical line (from linestart to insert mark)
                        self.log_area.delete("insert linestart", "insert")
                    
                    if not segment: continue

                    parts = ANSI_REGEX.split(segment)
                    for part in parts:
                        if not part: continue
                        
                        if part.startswith('\x1b['):
                            # Decode ANSI Code
                            codes = part.strip('\x1b[m').split(';')
                            for c in codes:
                                if c == '0' or c == '39':
                                    current_tag = "NORMAL"
                                elif c in self.ansi_map:
                                    current_tag = self.ansi_map[c]
                        else:
                            # Print Text
                            self.log_area.insert("insert", part, current_tag)

                self.log_area.see("end")
                self.log_area.configure(state="disabled")
                
        except queue.Empty:
            pass
        self.after(50, self.poll_log) # Faster polling

    def choose_global_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.config["download_folder"] = folder
            self.lbl_folder.config(text=folder)
            self.save_config()
            # Update downloader path
            self.downloader.base_dir = folder
            self.downloader.data_dir = os.path.join(folder, "data")
            self.downloader.session_dir = os.path.join(self.downloader.data_dir, "sessions")
            os.makedirs(self.downloader.data_dir, exist_ok=True)
            os.makedirs(self.downloader.session_dir, exist_ok=True)
            print(f"✅ Đã đổi thư mục gốc sang: {folder}")

    def pick_single_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.single_folder_path = folder
            self.btn_pick_folder.config(text="✅ Đã chọn")

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self.config["saved_links"]:
            folder_display = item["folder"] if item["folder"] else "(Mặc định)"
            self.tree.insert("", "end", values=(item["url"], folder_display))

    def add_link(self):
        link = self.entry_link.get().strip()
        if link:
            # Check duplicate
            for item in self.config["saved_links"]:
                if item["url"] == link:
                    messagebox.showinfo("Info", "Link này đã có trong danh sách!")
                    return

            new_item = {"url": link, "folder": self.single_folder_path}
            self.config["saved_links"].append(new_item)
            self.refresh_list()
            self.save_config()
            
            # Reset inputs
            self.entry_link.delete(0, "end")
            self.single_folder_path = ""
            self.btn_pick_folder.config(text="📁 Chọn Lẻ")
            
    def remove_selected(self):
        selection = self.tree.selection()
        if not selection:
            return
        
        # We need to map tree items back to config list
        # Since we populate in order, index matches
        indices = []
        for s in selection:
            idx = self.tree.index(s)
            indices.append(idx)
        
        # Remove from backend list (reverse order)
        for i in sorted(indices, reverse=True):
             del self.config["saved_links"][i]
        
        self.refresh_list()
        self.save_config()

    def edit_selected_folder(self):
        selection = self.tree.selection()
        if not selection:
            return
        
        folder = filedialog.askdirectory(title="Chọn thư mục lưu cho các link đã chọn")
        if not folder:
            return

        for s in selection:
            idx = self.tree.index(s)
            self.config["saved_links"][idx]["folder"] = folder
        
        self.refresh_list()
        self.save_config()

    def clear_all(self):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa HẾT danh sách link?"):
            self.config["saved_links"] = []
            self.refresh_list()
            self.save_config()

    def open_global_folder(self):
        path = self.config.get("download_folder") or self.downloader.base_dir
        os.startfile(path)

        
        # Stop button status is inverse of download buttons
        stop_state = "normal" if state == "disabled" else "disabled"
        self.btn_stop.config(state=stop_state)

    def stop_download(self):
        if self.is_downloading:
             if messagebox.askyesno("Xác nhận", "Bạn có muốn dừng các tác vụ đang chờ không? (Tác vụ hiện tại sẽ chạy nốt)"):
                 self.stop_event.set()
                 print("\n⚠️ ĐANG DỪNG... Vui lòng đợi tác vụ hiện tại hoàn tất.")
                 # Disable stop button to prevent multiple clicks
                 self.btn_stop.config(state="disabled")
    def set_buttons_state(self, state):
        self.btn_download_all.config(state=state)
        self.btn_download_selected.config(state=state)
        if hasattr(self, 'btn_scan_dupes'):
            self.btn_scan_dupes.config(state=state)
        
        # Update stop button state logic
        stop_state = "normal" if state == "disabled" else "disabled"
        self.btn_stop.config(state=stop_state)

    def start_download_all(self):
        links = self.config["saved_links"]
        if not links:
            messagebox.showwarning("Warning", "Danh sách trống!")
            return
        self.run_download_thread(links)

    def start_download_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Chưa chọn link nào!")
            return
        
        links = []
        for s in selection:
            idx = self.tree.index(s)
            links.append(self.config["saved_links"][idx])
            
        self.run_download_thread(links)

    def run_download_thread(self, links):
        if self.is_downloading:
            return
        
        self.is_downloading = True
        self.set_buttons_state("disabled")
        
        threading.Thread(target=self.process_downloads, args=(links,), daemon=True).start()

    def process_downloads(self, items):
        # items is a list of dict: {"url": "...", "folder": "..."}
        print(f"\n{'='*30}")
        print(f"🚀 BẮT ĐẦU TẢI {len(items)} LINKS...")
        print(f"{'='*30}\n")
        
        self.stop_event.clear()
        
        for i, item in enumerate(items):
            if self.stop_event.is_set():
                print(f"\n🛑 Đã dừng theo yêu cầu người dùng.")
                break

            link = item["url"]
            custom_folder = item["folder"] if item["folder"] else None
            
            print(f"\n🔹 [{i+1}/{len(items)}] Xử lý: {link}")
            if custom_folder:
                print(f"   📂 Lưu tại: {custom_folder}")

            try:
                if "tiktok.com" in link:
                    self.downloader.download_tiktok(link, output_folder=custom_folder)
                elif "facebook.com" in link:
                    self.downloader.download_facebook(link, output_folder=custom_folder)
                elif "instagram.com" in link:
                    # Check login
                    if not self.downloader.ig_logged_in:
                         if not self.downloader.get_ig_session():
                             print("❌ Cần đăng nhập Instagram trước!")
                             pass
                    
                    if self.downloader.ig_logged_in:
                        self.downloader.download_instagram(link, output_folder=custom_folder)
                else:
                    print("❓ Link không hỗ trợ.")
            except Exception as e:
                print(f"❌ Lỗi xử lý link: {e}")
        
        print(f"\n✅ HOÀN TẤT TẤT CẢ TÁC VỤ!")
        self.is_downloading = False
        # Update UI in main thread
        self.after(0, lambda: self.set_buttons_state("normal"))

    def scan_duplicates_thread(self):
        if self.is_downloading:
            messagebox.showwarning("Đang bận", "Vui lòng đợi tác vụ hiện tại hoàn tất.")
            return

        # 1. Thu thập danh sách thư mục tiềm năng
        candidates = set()
        
        # Thư mục gốc (từ cấu hình hoặc từ downloader)
        default_dir = self.config.get("download_folder", "") or self.downloader.base_dir
        if default_dir and os.path.exists(default_dir):
            candidates.add(os.path.abspath(default_dir))
            
        # Thư mục từ danh sách các link đã lưu
        # Duyệt qua các item trong User TreeView
        for item_id in self.tree.get_children():
            row_data = self.tree.item(item_id)["values"]
            # row_data = (url, folder)
            if len(row_data) >= 2:
                folder_path = row_data[1]
                if folder_path and os.path.exists(folder_path):
                    candidates.add(os.path.abspath(folder_path))
        
        # Sắp xếp danh sách
        sorted_folders = sorted(list(candidates))
        
        # 2. Hiển thị Dialog chọn
        if not sorted_folders:
            # Nếu không có folder nào trong list, fallback về browse thường
            target_dir = filedialog.askdirectory(title="Chọn Thư Mục Để Quét Ảnh Trùng", initialdir=default_dir)
        else:
            # Dùng Custom Dialog
            dlg = FolderSelectionDialog(self, sorted_folders)
            self.wait_window(dlg)
            target_dir = dlg.result
            
        if not target_dir:
            return  # User cancelled

        if messagebox.askyesno("Xác nhận quét trùng lặp", 
                               f"Bạn sắp quét thư mục:\n📂 {target_dir}\n\n"
                               "Tính năng này sẽ tìm và XOÁ các ảnh có nội dung giống nhau.\n"
                               "- Ảnh đầu tiên tìm thấy sẽ được giữ lại.\n"
                               "- Các ảnh trùng lặp sau đó sẽ bị xoá vĩnh viễn.\n\n"
                               "Bạn có CHẮC CHẮN muốn tiếp tục không?"):
            self.set_buttons_state("disabled")
            self.is_downloading = True 
            threading.Thread(target=self.run_scan_duplicates, args=(target_dir,), daemon=True).start()

    def run_scan_duplicates(self, target_dir):
        print(f"\n{'-'*30}")
        print(f"🧹 BẮT ĐẦU QUÉT ẢNH TRÙNG LẶP")
        print(f"📂 Thư mục đích: {target_dir}")
        print(f"{'-'*30}")
        
        self.stop_event.clear()
        count = 0
        error_msg = None

        try:
            # Gọi hàm scan từ MasterDownloader
            results = self.downloader.scan_for_duplicates(directory=target_dir, remove=True)
            count = len(results)
            
        except Exception as e:
            print(f"❌ Lỗi khi quét: {e}")
            error_msg = str(e)
        finally:
            print(f"\n✅ QUÉT HOÀN TẤT.")
            self.is_downloading = False
            
            def show_result():
                self.set_buttons_state("normal")
                if error_msg:
                    messagebox.showerror("Lỗi", f"Có lỗi xảy ra khi quét:\n{error_msg}")
                else:
                    if count > 0:
                        messagebox.showinfo("Thành công", f"Đã quét xong!\n🗑️ Đã xoá {count} ảnh trùng lặp.")
                    else:
                        messagebox.showinfo("Thành công", "Đã quét xong!\n✨ Không tìm thấy ảnh trùng nào.")

            self.after(0, show_result)

if __name__ == "__main__":
    app = App()
    app.mainloop()
