import os
import json
import threading
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import sys
import subprocess

API_URL = "https://edu-24-7-3.onrender.com/api/files"
LOCAL_ROOT = os.path.join(os.getenv('LOCALAPPDATA'), "Edu247Offline")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def is_online():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except Exception:
        return False

def fetch_files(prefix=""):
    params = {"prefix": prefix} if prefix else {}
    r = requests.get(API_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def save_selection(selected):
    with open(os.path.join(LOCAL_ROOT, "selected.json"), "w", encoding="utf-8") as f:
        json.dump(selected, f)

def load_selection():
    path = os.path.join(LOCAL_ROOT, "selected.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def download_file(url, dest):
    print(f"Descargando {dest} ...")
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(4096):
            f.write(chunk)

def sync_folder(folder_prefix, status_label=None):
    try:
        files = fetch_files(folder_prefix)
    except Exception as e:
        if status_label:
            status_label.config(text="Sin conexión, se sincronizará luego.")
        return
    local_folder = os.path.join(LOCAL_ROOT, folder_prefix.replace('/', os.sep))
    ensure_dir(local_folder)
    for entry in files:
        # IGNORA .init
        if entry["name"].endswith(".init"):
            continue
        if entry["name"].endswith("/"):
            sync_folder(entry["name"], status_label)
        else:
            filename = entry["name"].split("/")[-1]
            dest_path = os.path.join(LOCAL_ROOT, entry["name"].replace('/', os.sep))
            if not os.path.exists(dest_path):
                try:
                    download_file(entry["url"], dest_path)
                except Exception as e:
                    print("Error descargando", entry["url"], e)

def sync_selected(selected, status_label=None):
    if status_label:
        status_label.config(text="Sincronizando...")
    for folder in selected:
        sync_folder(folder, status_label)
    if status_label:
        status_label.config(text="¡Sincronización completa!")

def periodic_sync(selected, status_label):
    if not selected:
        status_label.config(text="Selecciona carpetas a sincronizar.")
        return
    if is_online():
        status_label.config(text="Conectado. Descargando...")
        sync_selected(selected, status_label=status_label)
    else:
        status_label.config(text="Sin conexión. Se descargará automáticamente cuando vuelva el Internet.")
    root.after(60000, lambda: periodic_sync(load_selection(), status_label))

def open_file(filename):
    local_path = os.path.join(LOCAL_ROOT, filename.replace('/', os.sep))
    print("Intentando abrir:", local_path)
    print("¿Existe archivo?:", os.path.exists(local_path))
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        try:
            if sys.platform == "win32":
                os.startfile(local_path)
            elif sys.platform == "darwin":
                subprocess.call(["open", local_path])
            else:
                subprocess.call(["xdg-open", local_path])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{e}")
    else:
        messagebox.showinfo("No disponible", "El archivo aún no está completamente descargado o fue movido.")

def show_files(prefix):
    for widget in right_frame.winfo_children():
        widget.destroy()
    # Botón para retroceder si no estamos en raíz
    if prefix:
        parts = prefix.strip("/").split("/")
        if parts:
            prev = "/".join(parts[:-1])
            prev = prev + "/" if prev else ""
            btn_back = tk.Button(right_frame, text="⬅️ Atrás", command=lambda: show_files(prev), anchor="w", relief="flat")
            btn_back.pack(fill="x", padx=8, pady=3)
    try:
        files = fetch_files(prefix)
    except Exception as e:
        tk.Label(right_frame, text="No se pudo cargar el contenido.", fg="red").pack()
        return
    for entry in files:
        # IGNORA .init en la vista
        if entry["name"].endswith(".init"):
            continue
        if entry["name"].endswith("/"):
            folder = entry["name"].replace(prefix, "").strip("/")
            btn = tk.Button(right_frame, text="📁 " + folder, anchor="w", relief="flat", command=lambda p=entry["name"]: show_files(p))
            btn.pack(fill="x", padx=8, pady=1)
        else:
            file = entry["name"].replace(prefix, "")
            btn = tk.Button(right_frame, text="📄 " + file, anchor="w", relief="flat", command=lambda f=entry["name"]: open_file(f))
            btn.pack(fill="x", padx=28, pady=1)

def on_check(var, folder):
    selected = load_selection()
    if var.get():
        if folder not in selected:
            selected.append(folder)
    else:
        selected = [x for x in selected if x != folder]
    save_selection(selected)
    status_label.config(text="Sincronizando...")
    threading.Thread(target=sync_selected, args=(selected, status_label), daemon=True).start()

# ---- GUI setup ----
root = tk.Tk()
root.title("Edu 24/7 Offline")
root.geometry("750x680")
root.resizable(False, False)
ensure_dir(LOCAL_ROOT)

# Logo
logo_path = os.path.join("assets", "edu247_logo_libro_colombia_v2.png")
logo_img = None
if os.path.exists(logo_path):
    img = Image.open(logo_path).resize((90, 90))
    logo_img = ImageTk.PhotoImage(img)
    tk.Label(root, image=logo_img).pack(pady=10)

tk.Label(root, text="Edu 24/7", font=("Arial", 22, "bold")).pack()
tk.Label(root, text="Marca para sincronizar y explora carpetas y archivos. Haz clic en el nombre para explorar o en el checkbox para sincronizar.", wraplength=540, font=("Arial", 11)).pack(pady=5)

main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True, padx=20, pady=10)

left_frame = tk.Frame(main_frame)
left_frame.pack(side="left", fill="y", padx=(0,18))

tk.Label(left_frame, text="Carpetas raíz disponibles:", font=("Arial", 11, "bold")).pack(anchor="w")

right_frame = tk.Frame(main_frame, bg="#f8f8f8")
right_frame.pack(side="left", fill="both", expand=True)

status_label = tk.Label(root, text="", font=("Arial", 10), fg="green")
status_label.pack(pady=8)

# Cargar carpetas raíz con checklist + botón separado
try:
    files = fetch_files()
    selected = load_selection()
    for entry in files:
        if entry["name"].endswith("/"):
            folder = entry["name"]
            frame = tk.Frame(left_frame)
            frame.pack(fill="x", padx=3, pady=2)
            var = tk.BooleanVar(value=folder in selected)
            cb = tk.Checkbutton(frame, variable=var, command=lambda v=var, f=folder: on_check(v, f))
            cb.pack(side="left")
            btn = tk.Button(frame, text="📁 " + folder.replace("/", ""), anchor="w",
                            command=lambda f=folder: show_files(f), relief="flat", bd=0, bg="white", activebackground="#eaf1fb")
            btn.pack(side="left", padx=2)
    status_label.config(text="Selecciona carpetas a sincronizar o explora el contenido.")
except Exception as e:
    status_label.config(text="No se pudo cargar lista de carpetas. ¿Hay conexión?")
    print(e)

# Sincronización periódica
threading.Thread(target=periodic_sync, args=(load_selection(), status_label), daemon=True).start()

root.mainloop()