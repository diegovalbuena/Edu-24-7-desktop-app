import os
import json
import requests
import shutil

API_URL = "https://edu-24-7-3.onrender.com/api/files"
LOCAL_ROOT = os.path.join(os.getenv('LOCALAPPDATA'), "Edu247Offline")

class SyncManager:
    def __init__(self):
        self.local_root = LOCAL_ROOT
        if not os.path.exists(self.local_root):
            os.makedirs(self.local_root)

    def is_online(self):
        try:
            requests.get("https://www.google.com", timeout=3)
            return True
        except Exception:
            return False

    def fetch_files(self, prefix=""):
        params = {"prefix": prefix} if prefix else {}
        r = requests.get(API_URL, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def save_selection(self, selected):
        with open(os.path.join(self.local_root, "selected.json"), "w", encoding="utf-8") as f:
            json.dump(selected, f)

    def load_selection(self):
        path = os.path.join(self.local_root, "selected.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def download_file(self, url, dest):
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(4096):
                f.write(chunk)

    def sync_folder(self, folder_prefix, status_callback=None):
        try:
            files = self.fetch_files(folder_prefix)
        except Exception as e:
            if status_callback:
                status_callback("Sin conexión, se sincronizará luego.")
            return
        local_folder = os.path.join(self.local_root, folder_prefix.replace('/', os.sep))
        if not os.path.exists(local_folder):
            os.makedirs(local_folder)
        for entry in files:
            # IGNORA .init
            if entry["name"].endswith(".init"):
                continue
            if entry["name"].endswith("/"):
                self.sync_folder(entry["name"], status_callback)
            else:
                dest_path = os.path.join(self.local_root, entry["name"].replace('/', os.sep))
                if not os.path.exists(dest_path):
                    try:
                        self.download_file(entry["url"], dest_path)
                    except Exception as e:
                        print("Error descargando", entry["url"], e)

    def sync_selected(self, selected, status_callback=None):
        if status_callback:
            status_callback("Sincronizando...")
        for folder in selected:
            self.sync_folder(folder, status_callback)
        if status_callback:
            status_callback("¡Sincronización completa!")

    def borrar_descargas(self):
        if os.path.exists(self.local_root):
            shutil.rmtree(self.local_root)
            os.makedirs(self.local_root)

    def hay_descargas(self):
        # Devuelve True si hay archivos descargados en el LOCAL_ROOT
        for root, dirs, files in os.walk(self.local_root):
            if files:
                return True
        return False

    def get_local_path(self, filename):
        return os.path.join(self.local_root, filename.replace('/', os.sep))
