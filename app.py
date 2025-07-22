# app.py
# Punto de entrada principal para la aplicación Edu 24/7 Offline

from sync_manager import SyncManager
from gui import Edu247App

if __name__ == "__main__":
    # Instancia el manejador de sincronización (archivos y lógica)
    sync_manager = SyncManager()
    # Inicia la interfaz gráfica, pasando el manejador como dependencia
    Edu247App(sync_manager)
