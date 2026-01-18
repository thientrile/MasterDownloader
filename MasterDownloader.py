import os
import re
import sys
import time
import random
import itertools
import json
import errno
from urllib.parse import unquote
import yt_dlp
import instaloader
import browser_cookie3
from PIL import Image
import imagehash
from cryptography.fernet import Fernet
from colorama import init, Fore, Style

# --- FIX LỖI HIỂN THỊ TIẾNG VIỆT TRÊN WINDOWS ---
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
# -----------------------------------------------

# Khởi tạo màu sắc
init(autoreset=True)

class MasterDownloader:
    def __init__(self):
        # Determine if we are running in a bundle or a normal python environment
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        # Thu muc du lieu chung (history, credentials, sessions)
        self.data_dir = self.base_dir
        # os.makedirs(self.data_dir, exist_ok=True) # Not needed if base_dir is root
        # Thu muc rieng de giu session, de de quan ly va xoa khi can
        self.session_dir = os.path.join(self.data_dir, "sessions")
        os.makedirs(self.session_dir, exist_ok=True)
        # Thu muc luu lich su tai xuong (archives) de tranh trung lap
        self.archive_dir = os.path.join(self.data_dir, "archives")
        os.makedirs(self.archive_dir, exist_ok=True)
        # File luu lich su cau hinh thu muc theo platform/user
        self.history_file = os.path.join(self.data_dir, "history.json")
        self.ig = instaloader.Instaloader(
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        # Crypto setup
        self.key_file = os.path.join(self.data_dir, "secret.key")
        self.cipher = self._load_crypto_key()
        
        self.ig_credentials_file = os.path.join(self.data_dir, "ig_credentials.txt")
        self.cookies_file = os.path.join(self.data_dir, "cookies.json")
        self.ig_username = None  # Nho username da nhap de khong hoi lai
        self.ig_password = None  # Luu password da nhap lan dau
        self.ig_logged_in = False
        # Cau hinh giam nhip de giam 401
        self.ig_profile_backoff = [180, 300, 600]
        self.ig_wait_401_base = 420
        self.ig_wait_401_jitter = (45, 120)
        self.ig_sleep_range = (8, 15)
        self.ig_retry_on_401 = 3
        self.ig_max_posts = 30  # Gioi han so bai tai moi lan de giam risk (None de khong gioi han)
        self.history = self.load_history()
        self.migrate_archives()
        self.migrate_security()

    def migrate_security(self):
        """Auto-encrypt plain text credentials on startup."""
        # 1. Credentials
        if os.path.exists(self.ig_credentials_file):
            try:
                with open(self.ig_credentials_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                # Simple check: Fernet tokens are usually long and start with gAAAA
                if not content.startswith("gAAAA"):
                    # It's likely plain text
                    print("🔒 Encrypting legacy credentials file...")
                    self.save_credentials(content.splitlines()[0], content.splitlines()[1])
            except:
                 pass
        
        # 2. Cookies
        if os.path.exists(self.cookies_file):
            changed = False
            try:
                with open(self.cookies_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for k, v in data.items():
                    if v and not v.startswith("gAAAA"):
                        print(f"🔒 Encrypting legacy cookie for {k}...")
                        data[k] = self._encrypt_text(v)
                        changed = True
                
                if changed:
                    with open(self.cookies_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
            except:
                pass

    def _load_crypto_key(self):
        """Load or create encryption key."""
        if os.path.exists(self.key_file):
            try:
                with open(self.key_file, "rb") as kf:
                    key = kf.read()
                return Fernet(key)
            except:
                pass # Re-create if corrupt
        
        # Create new key
        key = Fernet.generate_key()
        try:
            with open(self.key_file, "wb") as kf:
                kf.write(key)
        except:
            pass # Fail silently if cannot write
        return Fernet(key)

    def _encrypt_text(self, text):
        if not text: return ""
        try:
            # Need to handle if text is already encrypted? No, we trust caller.
            # But wait, if we are saving, we invoke this.
            return self.cipher.encrypt(text.encode('utf-8')).decode('utf-8')
        except Exception as e:
            print(f"Encryption error: {e}")
            return text

    def _decrypt_text(self, text):
        if not text: return ""
        try:
            return self.cipher.decrypt(text.encode('utf-8')).decode('utf-8')
        except Exception:
            # Fallback if text is not encrypted (migration support)
            return text

    def migrate_archives(self):
        """Move legacy downloaded.txt files to new centralized archives folder."""
        if not self.history:
            return

        print(f"{Fore.CYAN}🧹 Checking for legacy history files...")
        
        for key, data in self.history.items():
            folder = data.get("folder")
            if not folder or not os.path.exists(folder):
                continue

            # 1. Migrate yt-dlp downloaded.txt (TikTok/Facebook)
            legacy_file = os.path.join(folder, "downloaded.txt")
            if os.path.exists(legacy_file):
                # Guess platform/username from key
                lower_key = key.lower()
                username = key.split(':')[-1]
                safe_name = "".join(c for c in username if c.isalnum() or c in ('-','_','.',' '))
                
                target_name = None
                if "facebook" in lower_key or "fb" in lower_key:
                    target_name = f"facebook_{safe_name}.txt"
                elif "tiktok" in lower_key:
                    target_name = f"tiktok_{safe_name}.txt"
                else:
                    # heuristic: try to read content?
                    if "tiktok" in folder.lower():
                        target_name = f"tiktok_{safe_name}.txt"
                    elif "facebook" in folder.lower():
                         target_name = f"facebook_{safe_name}.txt"
                
                if target_name:
                    new_path = os.path.join(self.archive_dir, target_name)
                    try:
                        # Append content if target exists
                        if os.path.exists(new_path):
                            with open(legacy_file, 'r', encoding='utf-8', errors='ignore') as f_src, open(new_path, 'a', encoding='utf-8') as f_dst:
                                f_dst.write("\n" + f_src.read())
                            os.remove(legacy_file)
                            print(f"{Fore.GREEN}   -> Merged old history to {target_name}")
                        else:
                            os.rename(legacy_file, new_path)
                            print(f"{Fore.GREEN}   -> Moved old history to {target_name}")
                    except Exception as e:
                        print(f"{Fore.RED}   -> Error migrating {legacy_file}: {e}")

    def session_file_path(self, username):
        return os.path.join(self.session_dir, f"session-{username}")

    def load_history(self):
        if not os.path.exists(self.history_file):
            return {}
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _touch_archive_file(self, archive_path):
        """Ensure the download archive file exists and is writable."""
        if not archive_path:
            return True

        dir_name = os.path.dirname(archive_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        try:
            with open(archive_path, "a", encoding="utf-8"):
                return True
        except OSError as e:
            print(f"{Fore.YELLOW}⚠️  Khong the mo download archive {archive_path!r}: {e}")
            return False

    def _reset_archive_file(self, archive_path):
        if not archive_path:
            return False
        try:
            with open(archive_path, "w", encoding="utf-8"):
                return True
        except OSError as e:
            print(f"{Fore.YELLOW}⚠️  Reset download archive that bai {archive_path!r}: {e}")
            return False

    def _read_manual_cookie_deprecated(self):
        """Helper to read and clean manual cookie string. DEPRECATED."""
        return self.get_manual_cookie("instagram") or self.get_manual_cookie("tiktok")

    def _prepare_yt_dlp(self, ydl_opts, label):
        """Build a YoutubeDL instance with resilient archive handling."""
        opts = dict(ydl_opts)
        archive_path = opts.get('download_archive')

        if archive_path and not self._touch_archive_file(archive_path):
            print(f"{Fore.YELLOW}⚠️  Tat che do tranh trung cho {label} trong lan nay.")
            opts.pop('download_archive', None)
            archive_path = None

        try:
            return yt_dlp.YoutubeDL(opts)
        except OSError as e:
            if archive_path and e.errno == errno.EINVAL:
                print(f"{Fore.YELLOW}⚠️  Download archive bi loi cho {label}, dang reset...")
                if self._reset_archive_file(archive_path):
                    try:
                        return yt_dlp.YoutubeDL(opts)
                    except OSError as retry_err:
                        if retry_err.errno != errno.EINVAL:
                            raise
                        print(f"{Fore.YELLOW}⚠️  Archive van loi sau khi reset, se tat tranh trung cho {label}.")
                else:
                    print(f"{Fore.YELLOW}⚠️  Khong reset duoc archive, se tat tranh trung cho {label}.")
                opts.pop('download_archive', None)
                return yt_dlp.YoutubeDL(opts)
            raise

    def resolve_folder(self, platform, username, default_folder):
        # Dung chung mot key theo username cho ca IG/TikTok
        key = username
        # Back-compat: neu truoc day co luu kieu platform:username thi lay ra luon
        old_key = f"{platform}:{username}"
        folder = None
        if key in self.history:
            folder = self.history[key].get("folder")
        elif old_key in self.history:
            folder = self.history[old_key].get("folder")

        # Neu chua co thi lay default
        if not folder:
            folder = default_folder

        # Chuan hoa: neu folder cu dang TikTok_username hoac IG_username thi doi ve username thuan
        basename = os.path.basename(folder)
        if (basename.startswith("TikTok_") or basename.startswith("IG_")) and basename.endswith(username):
            folder = os.path.join(self.root_dir, username)

        # Luu lai mapping moi
        self.history[key] = {"folder": folder}
        self.save_history()
        return folder

    def update_folder(self, platform, username, folder):
        key = username
        self.history[key] = {"folder": folder}
        self.save_history()

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def load_credentials(self):
        if not os.path.exists(self.ig_credentials_file):
            return None
        try:
            with open(self.ig_credentials_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                
            # Try to decrypt entire content
            decrypted = self._decrypt_text(content)
            
            # If decryption worked or it was plain text, we expect lines
            lines = decrypted.splitlines()
            if len(lines) >= 2:
                # If it was migrated, re-save encrypted immediately?
                # Best to just return.
                return lines[0].strip(), lines[1].strip()
        except Exception:
            return None
        return None

    def save_credentials(self, username, password):
        try:
            content = f"{username}\n{password}"
            encrypted = self._encrypt_text(content)
            with open(self.ig_credentials_file, "w", encoding="utf-8") as f:
                f.write(encrypted)
        except Exception:
            pass

    def get_manual_cookie(self, platform):
        """Get cookie string for platform (instagram/tiktok) from json file."""
        if not os.path.exists(self.cookies_file):
            return None
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cookie_encrypted = data.get(platform, "")
                if not cookie_encrypted: return None
                
                # Decrypt here
                cookie = self._decrypt_text(cookie_encrypted)
                
                return cookie.strip('"').strip("'").replace('\n', '').strip()
        except:
            return None

    def set_manual_cookie(self, platform, cookie_content):
        """Save cookie string for platform."""
        data = {}
        if os.path.exists(self.cookies_file):
             try:
                 with open(self.cookies_file, 'r', encoding='utf-8') as f:
                     data = json.load(f)
             except: pass
        
        # Encrypt before saving
        data[platform] = self._encrypt_text(cookie_content)
        
        try:
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving cookie: {e}")
            return False

    def load_session_from_manual_file(self):
        """Doc cookie tu cookies.json (dinh dang raw HTTP header)"""
        print(f"{Fore.CYAN}🔄 Dang nap cookie IG tu cookies.json...")
        
        cookie_data = self.get_manual_cookie("instagram")
        if not cookie_data:
            return False

        try:
            # Reset cookie jar de dam bao sach se
            self.ig.context._session.cookies.clear()
            
            user_id_val = None
            csrf_token_val = None

            # --- PARSE COOKIES INTO JAR (SUA LOI: KHONG DUNG HEADER TRUC TIEP) ---
            # Parse chuoicookie vao cookie jar de requests tu dong quan ly (cap nhat csrf, version...)
            # Format: name=value; name2=value2
            pairs = cookie_data.split(';')
            for pair in pairs:
                if '=' not in pair:
                    continue
                name, val = pair.split('=', 1)
                name = name.strip()
                val = val.strip().strip('"')
                
                # Add to jar for .instagram.com
                self.ig.context._session.cookies.set(name, val, domain='.instagram.com', path='/')

                if name == 'ds_user_id':
                    user_id_val = val
                
                if name == 'csrftoken':
                    csrf_token_val = val

            # Update headers (Delete manual 'Cookie' header if it exists from previous runs/edits to be safe, 
            # though we are just initializing here)
            if 'Cookie' in self.ig.context._session.headers:
                del self.ig.context._session.headers['Cookie']

            # Cap nhat headers day du nhu Chrome that de tranh bi chan
            headers = {
                'Referer': 'https://www.instagram.com/',
                'Origin': 'https://www.instagram.com',
                'X-Requested-With': 'XMLHttpRequest',
                'X-IG-App-ID': '936619743392459', 
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Connection': 'keep-alive',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Upgrade-Insecure-Requests': '1',
            }
            if csrf_token_val:
                headers['X-CSRFToken'] = csrf_token_val
            
            self.ig.context._session.headers.update(headers)

            # BYPASS: Khong can test_login neu da co ds_user_id
            if user_id_val:
                self.ig_username = user_id_val
                # QUAN TRONG: Set username cho context de instaloader biet dang la ai
                self.ig.context.username = self.ig_username
                self.ig.context._is_logged_in = True
                self.ig_logged_in = True
                print(f"{Fore.GREEN}✅ Da Force Manual Login cho User ID: {self.ig_username}")
                
                # FORCE SAVE: Xoa session cu, chi save cookie jar
                try:
                    session_path = self.session_file_path(self.ig_username)
                    if os.path.exists(session_path):
                        os.remove(session_path)
                    
                    # Chi save session neu khong gay loi
                    self.ig.save_session_to_file(filename=session_path)
                    print(f"{Fore.GREEN}✅ Da cap nhat session file moi cho: {self.ig_username}")
                except Exception as e:
                    # Neu save session fail, ta van tiep tuc vi cookies da nam trong memory roi
                    print(f"{Fore.YELLOW}⚠️ Canh bao: Khong the luu session ra file (khong anh huong tai ve): {e}")
                
                return True

            # Test thu xem login duoc khong (fallback neu khong tim thay user_id)
            print(f"{Fore.CYAN}👉 Dang kiem tra login voi Manual Cookie (khong tim thay User ID)...")
            username = self.ig.test_login()
            if username:
                self.ig_username = username
                self.ig.save_session_to_file(filename=self.session_file_path(username))
                self.ig_logged_in = True
                print(f"{Fore.GREEN}✅ Da nap thanh cong Manual Cookies cho user: {username}")
                return True
            else:
                print(f"{Fore.RED}❌ Cookie IG trong cookies.json khong hop le.")
                return False

        except Exception as e:
            print(f"{Fore.RED}❌ Loi khi doc manual cookie: {e}")
            return False

    def load_session_from_browser(self):
        print(f"{Fore.CYAN}🔄 Dang thu lay cookie tu trinh duyet (Edge)...")
        try:
            # Thu lay tu Edge
            cookies = browser_cookie3.edge(domain_name="instagram.com")
            self.ig.context._session.cookies.update(cookies)
            
            # Kiem tra xem cookie co hieu luc khong (da login chua)
            username = self.ig.test_login()
            if username:
                self.ig_username = username
                self.ig.save_session_to_file(filename=self.session_file_path(username))
                self.ig_logged_in = True
                print(f"{Fore.GREEN}✅ Da muon cookie tu Edge cho {username} va luu Session.")
                return True
            else:
                print(f"{Fore.YELLOW}⚠️  Tim thay cookie Edge nhung hinh nhu chua dang nhap hoac cookie da het han.")
        except Exception as e:
             print(f"{Fore.YELLOW}⚠️  Khong lay duoc cookie tu Edge: {e}")
             
        return False

    def get_ig_session(self):
        """Đảm bảo đã đăng nhập IG, ưu tiên session lưu và cookie browser."""
        if self.ig.context.is_logged_in:
            self.ig_logged_in = True
            return True

        # 1. Thu Load Manual Cookie truoc (vi nguoi dung moi cung cap no)
        if self.load_session_from_manual_file():
            return True

        if not (self.ig_username and self.ig_password):
            saved = self.load_credentials()
            if saved:
                self.ig_username, self.ig_password = saved

        if self.ig_username:
            try:
                self.ig.load_session_from_file(self.ig_username, filename=self.session_file_path(self.ig_username))
                self.ig_logged_in = True
                print(f"{Fore.GREEN}✅ Da nap Session cua {self.ig_username} tu folder sessions.")
                return True
            except FileNotFoundError:
                pass
            except Exception:
                pass

        if self.load_session_from_browser():
            return True

        if not self.ig_username:
            self.ig_username = input(f"{Fore.WHITE}👉 Nhap Username IG (se luu txt): ").strip()
        if not self.ig_password:
            self.ig_password = input(f"{Fore.WHITE}🔑 Nhap Password IG (se luu txt, hien chu): ").strip()

        if not (self.ig_username and self.ig_password):
            print(f"{Fore.RED}❌ Thieu username hoac password IG.")
            return False

        print(f"{Fore.CYAN}👉 Dang dang nhap cho: {self.ig_username}")
        try:
            self.ig.login(self.ig_username, self.ig_password)
            self.ig.save_session_to_file(filename=self.session_file_path(self.ig_username))
            self.save_credentials(self.ig_username, self.ig_password)
            self.ig_logged_in = True
            print(f"{Fore.GREEN}✅ Dang nhap thanh cong va da luu Session!")
            return True
        except Exception as e:
            print(f"{Fore.RED}❌ Loi dang nhap: {e}")
            return False

    def _handle_ydl_progress(self, d, progress_callback):
        """Helper to handle yt-dlp progress hooks via callback."""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '').strip()
            speed = d.get('_speed_str', '').strip()
            eta = d.get('_eta_str', '').strip()
            msg = f"{percent} | {speed} | ETA: {eta}"
            print(f"{Fore.YELLOW}📥 {msg}", end='\r')
            if progress_callback:
                progress_callback(percent, msg)
        elif d['status'] == 'finished':
            msg = "Đang xử lý file..."
            print(f"\n{Fore.GREEN}✅ {msg}")
            if progress_callback:
                progress_callback("100%", msg)

    def _create_temp_cookie_file(self, cookie_string, domain=".tiktok.com"):
        """Creates a temporary Netscape cookie file from a cookie string."""
        if not cookie_string: return None
        
        try:
            temp_file = os.path.join(self.data_dir, "temp_cookies.txt")
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This file was generated by MasterDownloader\n")
                
                parts = cookie_string.split(';')
                for part in parts:
                    if '=' not in part: continue
                    key, val = part.split('=', 1)
                    key = key.strip()
                    val = val.strip()
                    # DOMAIN FLAG PATH SECURE EXPIRY NAME VALUE
                    f.write(f"{domain}\tTRUE\t/\tFALSE\t2147483647\t{key}\t{val}\n")
            return temp_file
        except:
            return None

    def download_tiktok(self, url, output_folder=None, progress_callback=None):
        """Xử lý tải TikTok (Video/Photo)"""
        # Giữ nguyên tham số URL vì Story có thể cần tham số để định danh chính xác
        # url = url.split('?')[0].strip() 
        url = url.strip()
        
        if "/photo/" in url:
            url = url.replace("/photo/", "/video/")
            
        match = re.search(r'@([^/?]+)', url)
        username = match.group(1) if match else "Unknown"
        
        # Tao thu muc rieng cho user (uu tien lay tu history neu co)
        if output_folder:
             folder = output_folder
        else:
             default_folder = os.path.join(self.base_dir, username)
             folder = self.resolve_folder("tiktok", username, default_folder)
        os.makedirs(folder, exist_ok=True)
            
        archive = os.path.join(self.archive_dir, f"tiktok_{username}.txt")
        
        ydl_opts_base = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(folder, '%(upload_date)s - %(title|No Title).100s [%(id)s] - %(playlist_index)s.%(ext)s'),
            'download_archive': archive,
            'ignoreerrors': True,
            'writethumbnails': True,
            'postprocessors': [{
                'key': 'FFmpegThumbnailsConvertor',
                'format': 'jpg',
            }],
            'quiet': False,
            'no_warnings': True,
            'force_ipv4': True, # Fix loi 403 CDN TikTok
            'sleep_interval': 5, # Doi 5s giua cac lan tai video
            'max_sleep_interval': 15, # Random toi da 15s
            'sleep_interval_requests': 2, # Doi 2s giua cac request API (tranh 429 khi lay list video)
            # Setup User-Agent mac dinh cua yt-dlp thuong tot hon hardcode
            # 'http_headers': {
            #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            # },
            # Thanh tien trinh don gian cho TikTok
            'progress_hooks': [
                lambda d: self._handle_ydl_progress(d, progress_callback)
            ],
        }

        print(f"{Fore.CYAN}🚀 Dang quet TikTok cua: {username}")
        if progress_callback: progress_callback("0%", "Đang lấy thông tin...")

        manual_cookie = self.get_manual_cookie("tiktok")
        
        # Chien luoc: 1. Manual Cookie File (Uu tien so 1) -> 2. Browser -> 3. No Cookie
        strategies = []
        
        if manual_cookie:
            # Create temp netscape cookie file
            temp_cookie_path = self._create_temp_cookie_file(manual_cookie)
            if temp_cookie_path:
                strategies.append(("Manual Cookie", {'cookiefile': temp_cookie_path}))
            
        strategies.append(("Browser Cookies", {'cookiesfrombrowser': ('edge',)}))
        strategies.append(("No Cookies", {}))

        for label, extra_opts in strategies:
            opts = ydl_opts_base.copy()
            opts.update(extra_opts)
            
            try:
                if label == "Manual Cookie":
                    print(f"{Fore.CYAN}🍪 Dang dung Manual Cookie tu settings...")
                elif label == "Browser Cookies":
                    # Kiem tra xem co manual cookie khong, neu co ma loi thi moi qua day, in log cho ro
                    print(f"{Fore.CYAN}ℹ️  Dang thu lay cookie tu Edge...")
                
                with self._prepare_yt_dlp(opts, f"TikTok {username}") as ydl:
                    ydl.download([url])
                
                # Neu chay OK ma khong loi thi thoat vong lap chien luoc
                break 

            except Exception as e:
                err_msg = str(e)
                # Check loi permission (do mo trinh duyet) hoac loi load cookie
                is_cookie_error = "Permission denied" in err_msg or "CookieLoadError" in err_msg or "Could not copy" in err_msg
                
                if is_cookie_error:
                    if label == "Browser Cookies":
                        print(f"{Fore.YELLOW}⚠️  Khong doc duoc cookie Edge (do dang mo). Bo qua.")
                    else:
                         print(f"{Fore.RED}❌ Loi cookie: {e}")
                    continue 

                # Check loi 429
                if "429" in err_msg or "Too Many Requests" in err_msg:
                    print(f"{Fore.RED}❌ Bi TikTok chan (429) o che do {label}.")
                    if label == "Manual Cookie":
                         print(f"{Fore.YELLOW}👉 Cookie thu cong co ve da het han hoac bi chan.")
                    continue
                
                # Cac loi khac thi raise luon
                print(f"{Fore.RED}❌ Loi TikTok: {e}")
                raise e

    def download_instagram(self, url, output_folder=None, progress_callback=None):
        """Xử lý tải Instagram Profile/Post"""
        url = url.split('?')[0].strip('/')
        target = url.split('/')[-1]
        
        if "/p/" in url or "/reels/" in url or "/reel/" in url:
            try:
                post = instaloader.Post.from_shortcode(self.ig.context, target)
                target = post.owner_username
            except Exception as e:
                print(f"{Fore.RED}❌ Khong tim thay bai viet: {e}")
                return

        print(f"{Fore.MAGENTA}📸 Dang quet Instagram cua: {target}")
        
        try:
            profile = None
            for attempt, delay in enumerate(self.ig_profile_backoff, start=1):
                try:
                    profile = instaloader.Profile.from_username(self.ig.context, target)
                    break
                except Exception:
                    if attempt == len(self.ig_profile_backoff):
                        raise
                    jitter = random.uniform(10, 25)
                    total_wait = delay + jitter
                    print(f"{Fore.YELLOW}⏳ IG chan tam thoi (401). Cho {total_wait:.1f}s roi thu lai...")
                    time.sleep(total_wait)

            if profile is None:
                return

            # Thiet lap thu muc luu cho IG (dung chung theo username, uu tien history)
            if output_folder:
                 resolved_folder = output_folder
            else:
                 default_folder = os.path.join(self.base_dir, target)
                 resolved_folder = self.resolve_folder("instagram", target, default_folder)
            os.makedirs(resolved_folder, exist_ok=True)
            self.ig.dirname_pattern = resolved_folder

            # --- LOAD HISTORY (Added Feature) ---
            # Ensure archive dir exists
            os.makedirs(self.archive_dir, exist_ok=True)
            
            archive_filename = f"instagram_{target}.txt"
            archive_path = os.path.join(self.archive_dir, archive_filename)
            
            print(f"{Fore.CYAN}📜 History File: {archive_path}")
            
            # Touch file if not exists
            if not os.path.exists(archive_path):
                with open(archive_path, 'w', encoding='utf-8') as f:
                    pass

            downloaded_shortcodes = set()
            try:
                with open(archive_path, 'r', encoding='utf-8') as f:
                    downloaded_shortcodes = set(line.strip() for line in f if line.strip())
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️  Khong doc duoc history file: {e}")
            # ------------------------------------

            # --- TẢI STORY (Added Feature) ---
            print(f"{Fore.MAGENTA}🎞️  Dang quet & tai Stories...")
            if progress_callback: progress_callback("Wait", "Đang quét Stories...")
            try:
                # Lay stories cua user hien tai (can login)
                if self.ig_logged_in:
                    stories = self.ig.get_stories(userids=[profile.userid])
                    has_story = False
                    for story in stories:
                        for item in story.get_items():
                            has_story = True
                            
                            # Check Metadata History (Story ID)
                            story_id = str(item.mediaid)
                            if story_id in downloaded_shortcodes:
                                continue

                            # download_storyitem tra ve True neu tai moi
                            downloaded = self.ig.download_storyitem(item, target=target)
                            
                            # Luu vao history
                            if downloaded:
                                print(f"{Fore.GREEN}   + Da tai story moi: {item.date_local}")
                                try:
                                    with open(archive_path, 'a', encoding='utf-8') as f:
                                        f.write(f"{story_id}\n")
                                    downloaded_shortcodes.add(story_id)
                                except: pass
                                time.sleep(random.uniform(2, 5))
                            else:
                                # Mark as downloaded if file exists but not in history
                                # (Optional, but good for consistency)
                                if story_id not in downloaded_shortcodes:
                                    try:
                                        with open(archive_path, 'a', encoding='utf-8') as f:
                                            f.write(f"{story_id}\n")
                                        downloaded_shortcodes.add(story_id)
                                    except: pass
                    
                    if not has_story:
                        print(f"{Fore.YELLOW}   ℹ️  Khong co story nao (hoac khong xem duoc).")
                else:
                    print(f"{Fore.YELLOW}   ⚠️  Chua login, bo qua quet Story.")

            except Exception as e:
                print(f"{Fore.RED}   ❌ Khong the tai Story (co the do loi API hoac cookies): {e}")

            # --- TẢI HIGHLIGHTS (Added Feature) ---
            print(f"{Fore.MAGENTA}🌟 Dang quet & tai Highlights...")
            try:
                if self.ig_logged_in:
                    highlights = self.ig.get_highlights(user=profile)
                    has_highlight = False
                    for highlight in highlights:
                        print(f"{Fore.CYAN}   > Dang quet Highlight: {highlight.title}")
                        for item in highlight.get_items():
                            has_highlight = True
                            if self.ig.download_storyitem(item, target=target):
                                print(f"{Fore.GREEN}     + Da tai item trong highlight '{highlight.title}': {item.date_local}")
                                time.sleep(random.uniform(2, 5))
                    
                    if not has_highlight:
                        print(f"{Fore.YELLOW}   ℹ️  Khong co highlight nao.")
                else:
                    print(f"{Fore.YELLOW}   ⚠️  Chua login, bo qua quet Highlights.")
            except Exception as e:
                print(f"{Fore.RED}   ❌ Khong the tai Highlights: {e}")

            # retry_on_401 = self.ig_retry_on_401  <-- Khong dung bien cuc bo nay nua, chuyen sang outer loop
            # wait_401_base = self.ig_wait_401_base

            # --- ROBUST LOOP: Bao ve ca qua trinh duyet iterator ---
            outer_retries = 5 # Tang so lan thu lai vi loi 401 rat hay gap
            post_count = 0
            while outer_retries > 0:
                try:
                    posts_iter = profile.get_posts()
                    if self.ig_max_posts:
                        posts_iter = itertools.islice(posts_iter, self.ig_max_posts)

                    for post in posts_iter:
                        post_count += 1
                        
                        # --- CHECK HISTORY ---
                        if post.shortcode in downloaded_shortcodes:
                            msg = f"Đã tải {post.shortcode} (History)"
                            print(f"{Fore.YELLOW}🛡️  [Post {post_count}] {msg}           ")
                            if progress_callback: progress_callback("Skipped", msg)
                            break
                        # ---------------------

                        # Hien thi tien trinh (overwrite line)
                        msg_check = f"Đang kiểm tra: {post.shortcode}..."
                        print(f"{Fore.CYAN}⏳ [Post {post_count}] {msg_check}", end='\r')
                        if progress_callback: progress_callback(f"Post {post_count}", msg_check)
                        
                        try:
                            # download_post trả về True nếu tải mới, False nếu bài đã tồn tại
                            downloaded = self.ig.download_post(post, target=target)
                            
                            # Luu vao history NGAY LAP TUC (append mode)
                            try:
                                with open(archive_path, 'a', encoding='utf-8') as f:
                                    f.write(f"{post.shortcode}\n")
                                downloaded_shortcodes.add(post.shortcode)
                            except Exception as e:
                                print(f"{Fore.RED}❌ Loi ghi history: {e}")

                            if downloaded:
                                msg_done = f"Đã tải xong: {post.shortcode}"
                                print(f"{Fore.GREEN}✅ [Post {post_count}] {msg_done}     ")
                                if progress_callback: progress_callback(f"Post {post_count}", "Tải xong")
                                wait_time = random.uniform(*self.ig_sleep_range)
                                time.sleep(wait_time)
                            else:
                                print(f"{Fore.YELLOW}🛡️  [Post {post_count}] Bai cu tren dia ({post.date_local}). Dung quet.             ")
                                # Neu gap bai cu thi coi nhu xong viec cho profile nay (hoac co the bo break neu muon quet het)
                                break 
                        except Exception as inner_e:
                            print(f"\n{Fore.RED}❌ [Post {post_count}] Loi tai: {inner_e}")
                            if "401" in str(inner_e) or "Unauthorized" in str(inner_e):
                                raise inner_e
                            continue
                    
                    # Neu vong for chay xong (hoac break do gap bai cu) -> Thanh cong
                    break

                except Exception as e:
                    # Bat loi gay ra boi next(posts_iter) hoac raise 401 tu ben trong
                    msg = str(e)
                    is_cnt_error = "Connection" in msg or "401" in msg or "Unauthorized" in msg or "few minutes" in msg
                    
                    if is_cnt_error and outer_retries > 1:
                        wait_time = 300 + random.uniform(30, 90) # Doi 5-6 phut
                        print(f"{Fore.YELLOW}⚠️  IG chan request (401/Network). Doi {wait_time:.0f}s roi quet lai tu dau...")
                        time.sleep(wait_time)
                        outer_retries -= 1
                        print(f"{Fore.CYAN}🔄 Dang thu lai (lan {6 - outer_retries}/5)...")
                        continue # Restart loop -> tao lai iterator moi
                    else:
                        print(f"{Fore.RED}❌ Loi nghiem trong hoac het luot thu: {e}")
                        break
        except Exception as e:
            print(f"{Fore.RED}❌ Loi khi quet Profile: {e}")

    def download_facebook(self, url, output_folder=None, progress_callback=None):
        """Xử lý tải Facebook video/post"""
        url = url.split('?')[0].strip()
        match = re.search(r"facebook\.com/([^/?#]+)", url, re.IGNORECASE)
        username = match.group(1) if match else "facebook"

        # Chi ho tro link video/watch/reel. Link profile se bi FB chan (yt_dlp khong lay duoc).
        if not ("/videos/" in url or "/watch" in url or "/reel/" in url):
            print(f"{Fore.RED}❌ Link Facebook nay khong phai video/post. Hay dan link /videos/, /watch?v=... hoac /reel/.")
            return

        if output_folder:
             folder = output_folder
        else:
             default_folder = os.path.join(self.base_dir, username)
             folder = self.resolve_folder("facebook", username, default_folder)
        os.makedirs(folder, exist_ok=True)

        safe_name = "".join(c for c in username if c.isalnum() or c in ('-','_','.',' '))
        archive = os.path.join(self.archive_dir, f"facebook_{safe_name}.txt")

        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(folder, '%(upload_date)s - %(title|No Title).150s [%(id)s].%(ext)s'),
            'download_archive': archive,
            'ignoreerrors': True,
            'writethumbnails': True,
            'quiet': False,
            'no_warnings': True,
            'progress_hooks': [
                lambda d: self._handle_ydl_progress(d, progress_callback)
            ],
        }

        print(f"{Fore.CYAN}🚀 Dang tai Facebook cua: {username}")
        if progress_callback: progress_callback("0%", "Đang lấy thông tin...")
        with self._prepare_yt_dlp(ydl_opts, f"Facebook {username}") as ydl:
            ydl.download([url])

    def scan_for_duplicates(self, directory=None, remove=False, status_callback=None):
        """
        Quét và tìm ảnh trùng lặp dựa trên nội dung (Perceptual Hashing).
        :param directory: Thư mục cần quét. Nếu None, dùng thư mục hiện tại.
        :param remove: Nếu True, sẽ xoá ảnh trùng (giữ lại 1 ảnh đầu tiên).
        :param status_callback: Hàm callback(msg) để báo trạng thái scan.
        :return: Danh sách các file trùng.
        """
        duplicates = []
        if directory is None:
            directory = self.base_dir
        
        # Hàm in nội bộ có callback
        def log(msg):
            # Strip color codes for callback if needed, but keeping simple for now
            # App handles ANSI stripping or parsing
            print(msg)
            if status_callback:
                status_callback(msg)

        log(f"{Fore.CYAN}🔍 Bắt đầu quét ảnh trùng trong: {directory}...")
        
        hashes = {}
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}
        
        scanned_count = 0
        
        for root, _, files in os.walk(directory):
            # Bỏ qua các thư mục hệ thống / cache của tool
            if "sessions" in root or "__pycache__" in root or ".git" in root:
                continue
                
            for filename in files:
                filepath = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()
                
                if ext in image_extensions:
                    scanned_count += 1
                    try:
                        with Image.open(filepath) as img:
                            # Tính hash trung bình (nhanh và đủ tốt cho trùng lặp gần như tuyệt đối)
                            # Resize nhỏ để tính nhanh
                            h = str(imagehash.average_hash(img))
                            
                            if h in hashes:
                                original = hashes[h]
                                duplicates.append((filepath, original))
                                log(f"{Fore.YELLOW}⚠️  TRÙNG: {filename} giống với {os.path.basename(original)}")
                                
                                if remove:
                                    try:
                                        os.remove(filepath)
                                        log(f"{Fore.RED}🗑️  Đã xoá bản sao: {filename}")
                                    except Exception as e:
                                        log(f"{Fore.RED}❌ Lỗi xoá {filename}: {e}")
                            else:
                                hashes[h] = filepath
                    except Exception as e:
                        # File lỗi hoặc không đọc được
                        pass
        
        log(f"{Fore.GREEN}✅ Quét xong {scanned_count} ảnh.")
        if len(duplicates) == 0:
             log(f"{Fore.GREEN}✨ Không tìm thấy ảnh trùng nào.")
        else:
             log(f"{Fore.GREEN}♻️  Tổng cộng {len(duplicates)} ảnh trùng đã được xử lý.")
             
        return duplicates

    def run(self):
        self.clear_screen()
        print(f"{Fore.GREEN}{'='*50}")
        print(f"{Fore.GREEN}   SIEU CONG CU TAI TIKTOK & INSTAGRAM (2026)")
        print(f"{Fore.GREEN}{'='*50}\n")
        try:
            print(f"{Fore.YELLOW}ℹ️  yt-dlp version: {yt_dlp.version.__version__}")
            print(f"{Fore.YELLOW}ℹ️  Instaloader version: {instaloader.__version__}")
        except Exception:
            pass

        while True:
            print(f"\n{Fore.WHITE}{'-'*50}")
            link = input(f"{Fore.CYAN}🔗 Dan link (TikTok/IG) hoac go 'exit' de thoat: ").strip()
            
            if link.lower() == 'exit':
                break
            
            if "tiktok.com" in link:
                self.download_tiktok(link)
            elif "facebook.com" in link:
                self.download_facebook(link)
            elif "instagram.com" in link:
                if not self.get_ig_session():
                    print(f"{Fore.RED}❌ Dang nhap IG that bai. Thu lai sau.")
                    continue

                self.download_instagram(link)
            else:
                print(f"{Fore.RED}❓ Link khong hop le bro oi!")
            
            print(f"\n{Fore.GREEN}✅ Xong! Tiep bai khac nao...")

if __name__ == "__main__":
    try:
        app = MasterDownloader()
        app.run()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Bye bro!")