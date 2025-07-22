# sync_manager.py
# Lógica de sincronización y acceso a archivos remotos/locales para Edu 24/7 Offline

import os
import json
import requests
import shutil

API_URL = "https://edu-24-7-3.onrender.com/api/files"
LOCAL_ROOT = os.path.join(os.getenv('LOCALAPPDATA'), "Edu247Offline")


class SyncManager:
    """
    Encapsula la lógica de sincronización de carpetas/archivos y almacenamiento local.
    """

    def __init__(self):
        self.local_root = LOCAL_ROOT
        if not os.path.exists(self.local_root):
            os.makedirs(self.local_root)

    def is_online(self):
        """
        Devuelve True si hay conexión a internet.
        """
        try:
            requests.get("https://www.google.com", timeout=3)
            return True
        except Exception:
            return False

    def fetch_files(self, prefix=""):
        """
        Obtiene la lista de archivos y carpetas desde la API, opcionalmente bajo un prefijo.
        """
        params = {"prefix": prefix} if prefix else {}
        r = requests.get(API_URL, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def save_selection(self, selected):
        """
        Guarda la selección de carpetas a sincronizar en local (como JSON).
        """
        with open(os.path.join(self.local_root, "selected.json"), "w", encoding="utf-8") as f:
            json.dump(selected, f)

    def load_selection(self):
        """
        Carga la selección de carpetas a sincronizar desde local (si existe).
        """
        path = os.path.join(self.local_root, "selected.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def download_file(self, url, dest):
        """
        Descarga un archivo desde la URL remota a la ruta local indicada.
        """
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(4096):
                f.write(chunk)

    def sync_folder(self, folder_prefix, status_callback=None):
        """
        Sincroniza recursivamente una carpeta (y su contenido) desde la nube al disco local.
        """
        print(f"Sincronizando folder: {folder_prefix}")
        try:
            files = self.fetch_files(folder_prefix)
        except Exception as e:
            print("Error al obtener archivos:", e)
            if status_callback:
                status_callback(text="Sin conexión, se sincronizará luego.")
            return
        local_folder = os.path.join(self.local_root, folder_prefix.replace('/', os.sep))
        if not os.path.exists(local_folder):
            os.makedirs(local_folder)
        for entry in files:
            # Ignora archivos .init en la nube
            if entry["name"].endswith(".init"):
                continue
            if entry["name"].endswith("/"):
                # Es carpeta: recursividad
                self.sync_folder(entry["name"], status_callback)
            else:
                dest_path = os.path.join(self.local_root, entry["name"].replace('/', os.sep))
                print("Descargando archivo:", entry["url"])
                if not os.path.exists(dest_path):
                    try:
                        self.download_file(entry["url"], dest_path)
                    except Exception as e:
                        print("Error descargando", entry["url"], e)

    def sync_selected(self, selected, status_callback=None):
        """
        Sincroniza todas las carpetas seleccionadas (en paralelo).
        """
        print("Iniciando sync_selected con: ", selected)
        if status_callback:
            status_callback(text="Sincronizando...")
        for folder in selected:
            print("Sincronizando carpeta: ", folder)
            self.sync_folder(folder, status_callback)
        if status_callback:
            status_callback(text="¡Sincronización completa!")

    def borrar_descargas(self):
        """
        Borra todos los archivos descargados localmente y recrea la carpeta raíz.
        """
        if os.path.exists(self.local_root):
            shutil.rmtree(self.local_root)
        os.makedirs(self.local_root, exist_ok=True)

    def hay_descargas(self):
        """
        Retorna True si hay al menos un archivo descargado en la carpeta local.
        """
        for root, dirs, files in os.walk(self.local_root):
            if files:
                return True
        return False

    def get_local_path(self, filename):
        """
        Devuelve la ruta absoluta local de un archivo dado (por nombre/nube).
        """
        return os.path.join(self.local_root, filename.replace('/', os.sep))
