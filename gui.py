import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import subprocess

class Edu247App:
    def __init__(self, sync_manager):
        self.sync_manager = sync_manager
        self.root = tk.Tk()
        self.root.title("Edu 24/7 Offline")
        self.root.geometry("750x680")
        self.root.resizable(False, False)
        self.selected_vars = {}

        self.build_gui()

        # Lanzar sincronización automática periódica
        self.periodic_sync()
        self.root.mainloop()

    def build_gui(self):
        # Logo
        logo_path = os.path.join("assets", "edu247_logo_libro_colombia_v2.png")
        logo_img = None
        if os.path.exists(logo_path):
            img = Image.open(logo_path).resize((90, 90))
            logo_img = ImageTk.PhotoImage(img)
            tk.Label(self.root, image=logo_img).pack(pady=10)
            self.root.logo_img = logo_img  # evita que lo borre el recolector de basura

        tk.Label(self.root, text="Edu 24/7", font=("Arial", 22, "bold")).pack()
        tk.Label(
            self.root,
            text="Marca para sincronizar y explora carpetas y archivos. Haz clic en el nombre para explorar o en el checkbox para sincronizar.",
            wraplength=540, font=("Arial", 11)).pack(pady=5)

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side="left", fill="y", padx=(0,18))

        tk.Label(self.left_frame, text="Carpetas raíz disponibles:", font=("Arial", 11, "bold")).pack(anchor="w")

        self.right_frame = tk.Frame(self.main_frame, bg="#f8f8f8")
        self.right_frame.pack(side="left", fill="both", expand=True)

        self.status_label = tk.Label(self.root, text="", font=("Arial", 10), fg="green")
        self.status_label.pack(pady=8)

        # Botón borrar descargas (solo visible si hay archivos)
        self.btn_borrar = tk.Button(
            self.root,
            text="🗑️ Borrar todos los archivos descargados",
            command=self.on_borrar_descargas,
            bg="#e04a4a", fg="white",
            font=("Arial", 10, "bold")
        )
        self.btn_borrar.pack(pady=(2, 10))
        self.update_borrar_btn_visibility()

        self.load_folders()

    def load_folders(self):
        # Limpia panel de la izquierda
        for widget in self.left_frame.winfo_children():
            if isinstance(widget, tk.Checkbutton) or isinstance(widget, tk.Frame):
                widget.destroy()
        try:
            files = self.sync_manager.fetch_files()
            selected = self.sync_manager.load_selection()
            for entry in files:
                if entry["name"].endswith("/"):
                    folder = entry["name"]
                    frame = tk.Frame(self.left_frame)
                    frame.pack(fill="x", padx=3, pady=2)
                    var = tk.BooleanVar(value=folder in selected)
                    cb = tk.Checkbutton(frame, variable=var, command=lambda v=var, f=folder: self.on_check(v, f))
                    cb.pack(side="left")
                    btn = tk.Button(frame, text="📁 " + folder.replace("/", ""), anchor="w",
                                    command=lambda f=folder: self.show_files(f), relief="flat", bd=0, bg="white", activebackground="#eaf1fb")
                    btn.pack(side="left", padx=2)
                    self.selected_vars[folder] = var
            self.status_label.config(text="Selecciona carpetas a sincronizar o explora el contenido.")
        except Exception as e:
            self.status_label.config(text="No se pudo cargar lista de carpetas. ¿Hay conexión?")
            print(e)

    def show_files(self, prefix):
        for widget in self.right_frame.winfo_children():
            widget.destroy()
        # Botón para retroceder si no estamos en raíz
        if prefix:
            parts = prefix.strip("/").split("/")
            if parts:
                prev = "/".join(parts[:-1])
                prev = prev + "/" if prev else ""
                btn_back = tk.Button(self.right_frame, text="⬅️ Atrás", command=lambda: self.show_files(prev), anchor="w", relief="flat")
                btn_back.pack(fill="x", padx=8, pady=3)
        try:
            files = self.sync_manager.fetch_files(prefix)
        except Exception as e:
            tk.Label(self.right_frame, text="No se pudo cargar el contenido.", fg="red").pack()
            return
        for entry in files:
            # IGNORA .init en la vista
            if entry["name"].endswith(".init"):
                continue
            if entry["name"].endswith("/"):
                folder = entry["name"].replace(prefix, "").strip("/")
                btn = tk.Button(self.right_frame, text="📁 " + folder, anchor="w", relief="flat", command=lambda p=entry["name"]: self.show_files(p))
                btn.pack(fill="x", padx=8, pady=1)
            else:
                file = entry["name"].replace(prefix, "")
                btn = tk.Button(self.right_frame, text="📄 " + file, anchor="w", relief="flat", command=lambda f=entry["name"]: self.open_file(f))
                btn.pack(fill="x", padx=28, pady=1)

    def on_check(self, var, folder):
        selected = self.sync_manager.load_selection()
        if var.get():
            if folder not in selected:
                selected.append(folder)
        else:
            selected = [x for x in selected if x != folder]
        self.sync_manager.save_selection(selected)
        self.status_label.config(text="Sincronizando...")
        threading.Thread(target=self.sync_manager.sync_selected, args=(selected, self.status_label.config), daemon=True).start()

    def periodic_sync(self):
        selected = self.sync_manager.load_selection()
        if not selected:
            self.status_label.config(text="Selecciona carpetas a sincronizar.")
            self.update_borrar_btn_visibility()
            self.root.after(60000, self.periodic_sync)
            return
        if self.sync_manager.is_online():
            self.status_label.config(text="Conectado. Descargando...")
            threading.Thread(target=self.sync_manager.sync_selected, args=(selected, self.status_label.config), daemon=True).start()
        else:
            self.status_label.config(text="Sin conexión. Se descargará automáticamente cuando vuelva el Internet.")
        self.update_borrar_btn_visibility()
        self.root.after(60000, self.periodic_sync)

    def open_file(self, filename):
        local_path = self.sync_manager.get_local_path(filename)
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

    def on_borrar_descargas(self):
        if not self.sync_manager.hay_descargas():
            messagebox.showinfo("Nada que borrar", "No hay archivos descargados aún.")
            return
        respuesta = messagebox.askyesno(
            "Confirmar",
            "¿Seguro que quieres borrar TODOS los archivos descargados? Esta acción NO se puede deshacer."
        )
        if not respuesta:
            return
        try:
            self.sync_manager.borrar_descargas()
            messagebox.showinfo("Listo", "¡Todos los archivos descargados han sido eliminados!")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo borrar:\n{e}")
        self.update_borrar_btn_visibility()

    def update_borrar_btn_visibility(self):
        # Solo mostrar botón si hay archivos descargados
        if self.sync_manager.hay_descargas():
            self.btn_borrar.pack_configure(pady=(2,10))
        else:
            self.btn_borrar.pack_forget()
