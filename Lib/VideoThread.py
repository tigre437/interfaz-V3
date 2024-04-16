import cv2
import os
import datetime
from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np


class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self, clase):
        super().__init__()
        self.cap = None
        self._run_flag = True
        self.app = clase

    def run(self):
        # Captura desde la cámara web
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        while self._run_flag:
            ret, cv_img = self.cap.read()
            if ret:
                # Imprimir las dimensiones del fotograma
                height, width, _ = cv_img.shape

                # Emitir la señal con el fotograma capturado
                self.change_pixmap_signal.emit(cv_img)
        # Apagar el sistema de captura
        self.cap.release()

    def stop(self):
        """Sets run flag to False and waits for thread to finish"""
        self._run_flag = False
        self.wait()

    def settings(self):
        self.cap.set(cv2.CAP_PROP_SETTINGS, 1)

    def save(self, ruta_experimento, area, doble):
        # Obtener la fecha y hora actual
        now = datetime.datetime.now()

        # Formatear la fecha y hora en el formato deseado, por ejemplo: HHMMSS
        timestamp = now.strftime("%H%M%S")

        ret, cv_img = self.cap.read()
        if ret:
            if not doble:
                height, width, _ = cv_img.shape
                if area == 'Placa A':
                    cv_img = cv_img[:, :width // 2]  # Recortar la mitad izquierda de la imagen
                elif area == 'Placa B':
                    cv_img = cv_img[:, width // 2:]  # Recortar la mitad derecha de la imagen
            # Guardar la imagen en la carpeta "imagenes"
            cv2.imwrite(os.path.join(f"{ruta_experimento}/imagenes", f"{timestamp}.jpg"), cv_img)
        else:
            print("Error al capturar la imagen. No se guardará.")

    def set_camera_index(self, index):
        """Establece el índice del dispositivo de captura"""
        self.camera_index = index