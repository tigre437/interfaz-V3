import os
import time
import cv2
import json
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import (
    QFileDialog, QDialog, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox, QGraphicsProxyWidget, QListWidgetItem, QDialog
)
from PyQt6.QtCore import pyqtSlot, Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QPixmap, QTransform
from pygrabber.dshow_graph import FilterGraph
import datetime

from interfazv1 import Ui_MainWindow
from configFotos import Ui_Dialog

import threading  

from lauda import lauda
from VideoThread import VideoThread


ruta_experimento_activo = None
parar = False
lista_imagenes_analisis = []
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    
    def __init__(self, *args, obj=None, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)  # Configura la interfaz gráfica definida en Ui_MainWindow
        global ruta_experimento_activo
        ruta_experimento_activo = None

        # Crear una instancia del diálogo y almacenarla como un atributo de instancia
        self.dialog = QtWidgets.QDialog()
        self.dialog.ui = Ui_Dialog()
        self.dialog.ui.setupUi(self.dialog)

        # Conectar el botón de aceptar del cuadro de diálogo a la función guardar_datos_camara
        self.dialog.ui.buttonBox.accepted.connect(self.guardar_datos_camara)


        self.lauda = lauda()
        self.video_thread = VideoThread(MainWindow)

        #self.video_thread.start()
        self.lauda.start()
        

        # Graficas
        scene = QtWidgets.QGraphicsScene()

        # Asignar el QGraphicsScene a graphicsView
        self.graphicsView.setScene(scene)

        # Conexiones de los botones con los métodos correspondientes
        self.buttonBuscarArchivos.clicked.connect(self.filechooser)
        self.buttonConfiguracion.clicked.connect(self.settings)
        self.comboBoxFiltro.addItem("Crear un filtro nuevo ...")
        

        # Llena el combobox de cámaras disponibles
        self.fillCameras()
        self.list_cameras()

        # Conexiones de señales
        
        self.comboBoxCamara.currentIndexChanged.connect(self.update_camera_index)
        self.checkBoxHabilitarA.stateChanged.connect(self.cambiarPlacaA)
        self.checkBoxHabilitarB.stateChanged.connect(self.cambiarPlacaB)
        global check_option_lambda
        check_option_lambda = lambda index: self.comprobar_opcion_seleccionada(index, self.comboBoxFiltro)
        self.comboBoxFiltro.currentIndexChanged.connect(check_option_lambda)
        self.buttonGuardarFiltro.clicked.connect(self.guardar_datos_filtro)
        self.buttonCancelarFiltro.clicked.connect(self.cancelar_cambios_filtro)
        self.buttonIniciar.clicked.connect(self.iniciar_experimento)

        self.tabWidget_2.currentChanged.connect(self.tab_changed)
        self.checkBoxHabilitarA.stateChanged.connect(self.tab_changed)
        self.checkBoxHabilitarB.stateChanged.connect(self.tab_changed)
        self.checkBoxAmbasPlacas.stateChanged.connect(self.tab_changed)
        self.checkBoxAmbasPlacas.stateChanged.connect(self.desactivar_placaB)

        self.buttonGuardarParamDetec.clicked.connect(self.guardar_datos_detection)
        self.buttonCancelarParamDetec.clicked.connect(self.cancelar_cambios_detect)

        self.buttonGuardarParamTemp.clicked.connect(self.guardar_datos_temp)
        self.buttonCancelarParamTemp.clicked.connect(self.cancelar_cambios_temp)

        self.buttonConfiguracionExper.clicked.connect(self.open_dialog)

        self.buttonCargar.clicked.connect(self.cargar_datos_experimento)
        self.buttonGuardar.clicked.connect(self.guardar_datos_experimento)

        self.buttonConectarTermo.clicked.connect(self.conectarTermostato)

        # Dimensiones para mostrar la imagen
        self.display_width = self.width() // 2
        self.display_height = self.height() // 2

        # Conectar Sliders con Spin box
        self.hSliderRadioMin.valueChanged.connect(self.dSpinBoxRadioMin.setValue)
        self.hSliderRadioMax.valueChanged.connect(self.dSpinBoxRadioMax.setValue)
        self.hSliderGradoPolig.valueChanged.connect(self.dSpinBoxGradoPolig.setValue)
        self.hSliderUmbral.valueChanged.connect(self.dSpinBoxUmbral.setValue)

        self.hSliderTempMin.valueChanged.connect(self.dSpinBoxTempMin.setValue)
        self.hSliderTempMax.valueChanged.connect(self.dSpinBoxTempMax.setValue)
        self.hSliderTempSet.valueChanged.connect(self.dSpinBoxTempSet.setValue)

        # Conectar Spin boxes con Sliders
        self.dSpinBoxRadioMin.valueChanged.connect(self.hSliderRadioMin.setValue)
        self.dSpinBoxRadioMax.valueChanged.connect(self.hSliderRadioMax.setValue)
        self.dSpinBoxGradoPolig.valueChanged.connect(self.hSliderGradoPolig.setValue)
        self.dSpinBoxUmbral.valueChanged.connect(self.hSliderUmbral.setValue)

        self.dSpinBoxTempMin.valueChanged.connect(self.hSliderTempMin.setValue)
        self.dSpinBoxTempMax.valueChanged.connect(self.hSliderTempMax.setValue)
        self.dSpinBoxTempSet.valueChanged.connect(self.hSliderTempSet.setValue)

        self.buttonRecargar.clicked.connect(lambda: self.filechooser(True))


        self.buttonParar.clicked.connect(self.pararExperimento)

        self.listExperimentos.itemDoubleClicked.connect(self.mostrar_nombre_experimento)
        self.sliderFotos.valueChanged.connect(self.actualizar_imagen)

        self.buttonRecargar.clicked.connect(lambda index: self.filechooser(self.txtArchivos.text()))

        #Aqui hay que setear de primeras las temperaturas de los liquidos cuando podamos obtenerlas
        #self.pintar_grafica(temp_bloc, temp_liquid, temp_set)


        # Timer de la grafica

       #self.timer = QTimer(self)
       #self.timer.timeout.connect(self.actualizar_grafica)
       #self.timer.start(1000)

        #SE AÑADE UN VALOR A LAS LISTAS DE DATO


        ######################  ANALISIS  ##########################

        self.comboBoxFiltroAn.currentIndexChanged.connect(lambda index: self.comprobar_opcion_seleccionada(index, self.comboBoxFiltroAn))

    def detener_timer(self):
        self.timer.stop()

    def open_dialog(self):
        # Ruta al archivo camera.json
        ruta_camera_json = self.obtener_ruta_json("camera.json")

        # Verificar si el archivo existe
        if os.path.exists(ruta_camera_json):
            # Leer el archivo y obtener los datos de la cámara
            datos_camara = self.leer_json_camara(ruta_camera_json)
        else:
            # Si el archivo no existe, crearlo con valores predeterminados
            self.crear_json_camara(os.path.dirname(ruta_camera_json))
            datos_camara = {
                'frecuencia': 2,
                'habilitado': True,
                'temp_set': -3
            }

        # Rellenar los campos del diálogo con los datos de la cámara
        self.dialog.ui.labelFrecuencia.setText(str(datos_camara['frecuencia']))
        self.dialog.ui.checkBox.setChecked(datos_camara['habilitado'])
        self.dialog.ui.doubleSpinTemp.setValue(datos_camara['temp_set'])

        # Mostrar el diálogo
        self.dialog.exec()

    def desactivar_placaB(self):
        if self.checkBoxAmbasPlacas.isChecked():
            self.checkBoxHabilitarB.setChecked(False)
            self.checkBoxHabilitarB.setEnabled(False)
            self.copiarDatosA()
        else:
            self.checkBoxHabilitarB.setEnabled(True)

    def copiarDatosA(self):
        self.txtNombrePlacaB.setText(self.txtNombrePlacaA.text())
        self.txtVDropPlacaB.setText(self.txtVDropPlacaA.text())
        self.txtVWashPlacaB.setText(self.txtVWashPlacaA.text())
        self.txtFactorDilucPlacaB.setText(self.txtFactorDilucPlacaA.text())
        self.txtFraccFiltroPlacaB.setText(self.txtFraccFiltroPlacaA.text())
        self.txtTasaMuestreoPlacaB.setText(self.txtTasaMuestreoPlacaA.text())
        self.txtVelEnfriamientoPlacaB.setText(self.txtVelEnfriamientoPlacaA.text())
        self.txtObservPlacaB.setPlainText(self.txtObservPlacaA.toPlainText())


    def cambiarPlacaA(self):
        """Habilita o deshabilita campos según el estado del checkbox."""
        if self.checkBoxHabilitarA.isChecked():
            self.txtNombrePlacaA.setEnabled(True)
            self.txtVDropPlacaA.setEnabled(True)
            self.txtVWashPlacaA.setEnabled(True)
            self.txtFactorDilucPlacaA.setEnabled(True)
            self.txtFraccFiltroPlacaA.setEnabled(True)
            self.txtTasaMuestreoPlacaA.setEnabled(True)
            self.txtVelEnfriamientoPlacaA.setEnabled(True)
            self.txtObservPlacaA.setEnabled(True)
        else:
            self.txtNombrePlacaA.setEnabled(False)
            self.txtVDropPlacaA.setEnabled(False)
            self.txtVWashPlacaA.setEnabled(False)
            self.txtFactorDilucPlacaA.setEnabled(False)
            self.txtFraccFiltroPlacaA.setEnabled(False)
            self.txtTasaMuestreoPlacaA.setEnabled(False)
            self.txtVelEnfriamientoPlacaA.setEnabled(False)
            self.txtObservPlacaA.setEnabled(False)

    def cambiarPlacaB(self):
        """Habilita o deshabilita campos según el estado del checkbox."""
        if self.checkBoxHabilitarB.isChecked():
            self.txtNombrePlacaB.setEnabled(True)
            self.txtVDropPlacaB.setEnabled(True)
            self.txtVWashPlacaB.setEnabled(True)
            self.txtFactorDilucPlacaB.setEnabled(True)
            self.txtFraccFiltroPlacaB.setEnabled(True)
            self.txtTasaMuestreoPlacaB.setEnabled(True)
            self.txtVelEnfriamientoPlacaB.setEnabled(True)
            self.txtObservPlacaB.setEnabled(True)
        else:
            self.txtNombrePlacaB.setEnabled(False)
            self.txtVDropPlacaB.setEnabled(False)
            self.txtVWashPlacaB.setEnabled(False)
            self.txtFactorDilucPlacaB.setEnabled(False)
            self.txtFraccFiltroPlacaB.setEnabled(False)
            self.txtTasaMuestreoPlacaB.setEnabled(False)
            self.txtVelEnfriamientoPlacaB.setEnabled(False)
            self.txtObservPlacaB.setEnabled(False)
            
    def buscar_carpetas_sns(self, directorio):
        """Retorna una lista de carpetas que comienzan con 'SNS' dentro del directorio dado."""
        carpetas = [nombre for nombre in os.listdir(directorio) if os.path.isdir(os.path.join(directorio, nombre))]
        carpetas_sns = [carpeta for carpeta in carpetas if carpeta.startswith("SNS")]
        return carpetas_sns

    def filechooser(self, folder = None):
        """Abre un diálogo para seleccionar una carpeta."""
        if not folder:
            selected_folder = QFileDialog.getExistingDirectory(self)
            if selected_folder:
                carpeta_seleccionada = selected_folder
            else:
                carpeta_seleccionada = self.txtArchivos.text()  # Usar el valor anterior si se cancela
        else:
            carpeta_seleccionada = self.txtArchivos.text()

        self.txtArchivos.setText(carpeta_seleccionada)
        carpetas_sns = self.buscar_carpetas_sns(carpeta_seleccionada)
        
        self.comboBoxFiltro.clear()
        self.comboBoxFiltroAn.clear()
        if carpetas_sns:
            
            self.comboBoxFiltro.addItem("Crear un filtro nuevo ...")
            for carpeta in carpetas_sns:
                self.comboBoxFiltro.addItem(carpeta)
            for carpeta in carpetas_sns:
                self.comboBoxFiltroAn.addItem(carpeta)
        else:
            QMessageBox.warning(self, "Alerta", "No se encontraron carpetas de filtros 'SNS' dentro de la carpeta seleccionada.")

    def comprobar_opcion_seleccionada(self, index, combobox):
        """Comprueba la opción seleccionada en el combobox de filtros."""
        if index == -1:
            pass
        elif index == 0 and combobox == self.comboBoxFiltro:  
            if(self.txtArchivos.text() == None or self.txtArchivos.text() == ""):
                QMessageBox.warning(self, "Alerta", "Seleccione una carpeta para guardar los filtros antes de continuar.")
                self.comboBoxFiltro.currentIndexChanged.disconnect(check_option_lambda)
                self.comboBoxFiltro.setCurrentIndex(-1)
                self.comboBoxFiltro.currentIndexChanged.connect(check_option_lambda)
                self.filechooser()
            nombre_carpeta = self.obtener_nombre_carpeta()
            if nombre_carpeta:
                self.crear_carpeta(nombre_carpeta)
        else:
            if combobox == self.comboBoxFiltro:  # Solo rellenar datos si el combobox es comboBoxFiltro
                datos_filtro = self.leer_json_filtro(self.txtArchivos.text() + "/" + combobox.currentText() + "/" + "filter.json")
                if (datos_filtro != None):
                    self.rellenar_datos_filtro(datos_filtro)

                datos_detection = self.leer_json_detection(self.txtArchivos.text() + "/" + combobox.currentText() + "/" + "detection.json")
                if (datos_detection != None):
                    self.rellenar_datos_detection(datos_detection)

                datos_temp = self.leer_json_temp(self.txtArchivos.text() + "/" + combobox.currentText() + "/" + "temp.json")
                if (datos_temp != None):
                    self.rellenar_datos_temp(datos_temp)
            else:
                carpetas = self.cargar_lista_experimentos(self.txtArchivos.text() + "/" + combobox.currentText())


    

    def cancelar_cambios_filtro(self):
        """Cancela la edición del filtro seleccionado."""
        datos_filtro = self.leer_json_filtro(self.txtArchivos.text() + "/" + self.comboBoxFiltro.currentText() + "/" + "filter.json")
        if (datos_filtro != None):
            self.rellenar_datos_filtro(datos_filtro)

    def cancelar_cambios_detect(self):
        """Cancela la edición del filtro seleccionado."""
        datos_detection = self.leer_json_detection(self.txtArchivos.text() + "/" + self.comboBoxFiltro.currentText() + "/" + "detection.json")
        if (datos_detection != None):
            self.rellenar_datos_detection(datos_detection)

    def cancelar_cambios_temp(self):
        """Cancela la edición del filtro seleccionado."""
        datos_temp = self.leer_json_temp(self.txtArchivos.text() + "/" + self.comboBoxFiltro.currentText() + "/" + "temp.json")
        if (datos_temp != None):
            self.rellenar_datos_temp(datos_temp)

    def obtener_nombre_carpeta(self):
        """Abre un diálogo para ingresar el nombre de la carpeta."""
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Nombre del filtro")
        
        etiqueta = QLabel("Ingrese el nombre del filtros:")
        campo_texto = QLineEdit()
        boton_aceptar = QPushButton("Aceptar")
        boton_cancelar = QPushButton("Cancelar")

        layout = QVBoxLayout()
        layout.addWidget(etiqueta)
        layout.addWidget(campo_texto)
        layout.addWidget(boton_aceptar)
        layout.addWidget(boton_cancelar)

        dialogo.setLayout(layout)

        def aceptar():
            nombre_carpeta = campo_texto.text()
            if nombre_carpeta:
                dialogo.accept()

        boton_aceptar.clicked.connect(aceptar)
        boton_cancelar.clicked.connect(dialogo.reject)

        if dialogo.exec() == QDialog.DialogCode.Accepted:
            return campo_texto.text()
        else:
            return None

    def crear_carpeta(self, nombre_carpeta):
        """Crea una carpeta para el nuevo filtro."""
        fecha_actual = datetime.datetime.now().strftime("%Y%m%d")
        nombre_carpeta_sns = f"SNS_{fecha_actual}_{nombre_carpeta}"
        directorio_seleccionado = self.txtArchivos.text()
        
        if os.path.isdir(directorio_seleccionado):
            ruta_carpeta_sns = os.path.join(directorio_seleccionado, nombre_carpeta_sns)
            os.makedirs(ruta_carpeta_sns)
            print(f"Carpeta '{nombre_carpeta_sns}' creada exitosamente en '{directorio_seleccionado}'.")
            carpetas_sns = self.buscar_carpetas_sns(directorio_seleccionado)

            self.comboBoxFiltro.currentIndexChanged.disconnect(check_option_lambda)
            self.comboBoxFiltro.clear()
            self.comboBoxFiltro.addItem("Crear un filtro nuevo ...")
            for carpeta in carpetas_sns:
                self.comboBoxFiltro.addItem(carpeta)
            self.comboBoxFiltro.setCurrentText(nombre_carpeta_sns)

            # Crear el archivo filter.json
            self.crear_json_filtro(ruta_carpeta_sns)
            
            # Cargar los datos del filtro recién creado
            self.comprobar_opcion_seleccionada(1, self.comboBoxFiltro)  # Índice 1 para seleccionar el nuevo filtro

            # Vuelve a conectar la señal currentIndexChanged
            self.comboBoxFiltro.currentIndexChanged.connect(check_option_lambda)
            
        else:
            print("Error: El directorio seleccionado no es válido.")


    ######################### TERMOSTATO ################################

    def conectarTermostato(self):
        url = self.txtIpTermos.text()

        self.lauda.open(url)



    ######################### JSON #################################

    def leer_json_filtro(self, archivo_json):
        """Lee un archivo JSON y devuelve los datos relevantes."""
        try:
            with open(archivo_json, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            QMessageBox.warning(self, "Advertencia", f"El archivo '{archivo_json}' no existe.", QMessageBox.StandardButton.Ok)
            return
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Advertencia", f"El archivo '{archivo_json}' no es un archivo JSON válido.", QMessageBox.StandardButton.Ok)
            return

        label = data.get('label', 'Sin etiqueta')
        storage_temperature = data.get('storage_temperature', 0)
        sampler_id = data.get('sampler_id', 'Sin ID')
        filter_position = data.get('filter_position', 0)
        air_volume = data.get('air_volume', 0.0)
        start_time = data.get('start_time', 'Sin hora de inicio')
        end_time = data.get('end_time', 'Sin hora de fin')
        observations = data.get('observations', 'Sin observaciones')

        return {
            'label': label,
            'storage_temperature': storage_temperature,
            'sampler_id': sampler_id,
            'filter_position': filter_position,
            'air_volume': air_volume,
            'start_time': start_time,
            'end_time': end_time,
            'observations': observations
        }

    def rellenar_datos_filtro(self, datos):
        """Asigna los valores correspondientes a cada campo de texto."""

        if self.tabWidget.tabText(self.tabWidget.currentIndex()) == "Experimento":

            self.txtNombreFiltro.setText(datos['label'])
            self.txtTempStorage.setText(str(datos['storage_temperature']))
            self.txtIdMuestreador.setText(datos['sampler_id'])
            self.txtPosFilter.setText(str(datos['filter_position']))
            self.txtAirVol.setText(str(datos['air_volume']))
            self.txtHoraInicio.setDateTime(QtCore.QDateTime.fromString(datos['start_time'], "yyyy-MM-dd hh:mm"))
            self.txtHoraFin.setDateTime(QtCore.QDateTime.fromString(datos['end_time'], "yyyy-MM-dd hh:mm"))
            
            # Observaciones puede ser nulo, así que verificamos antes de asignar
            if datos['observations'] is not None:
                self.txaObservFiltro.setPlainText(datos['observations'])
            else:
                self.txaObservFiltro.clear()  # Limpiamos el campo si las observaciones son nulas

    def crear_json_filtro(self, ruta_carpeta_sns):
        """Crea el archivo filter.json."""
        ruta_filter_json = os.path.join(ruta_carpeta_sns, 'filter.json')
        with open(ruta_filter_json, 'w') as file:
            json.dump({
                "label": "Sin etiqueta",
                "storage_temperature": "0",
                "sampler_id": "Sin ID",
                "filter_position": "0",
                "air_volume": "0.0",
                "start_time": "2000-01-01 00:00",
                "end_time": "2000-01-01 00:00",
                "observations": "Sin observaciones"
            }
            , file) 

    def guardar_datos_filtro(self):
        """Guarda los datos del filtro en un archivo JSON."""
        # Obtener los datos de los campos de texto
        label = self.txtNombreFiltro.text()
        storage_temperature = self.txtTempStorage.text()
        sampler_id = self.txtIdMuestreador.text()
        filter_position = self.txtPosFilter.text()
        air_volume = self.txtAirVol.text()
        start_time = self.txtHoraInicio.dateTime().toString("yyyy-MM-dd hh:mm")
        end_time = self.txtHoraFin.dateTime().toString("yyyy-MM-dd hh:mm")
        observations = self.txaObservFiltro.toPlainText()

        # Crear un diccionario con los datos
        datos_filtro = {
            'label': label,
            'storage_temperature': storage_temperature,
            'sampler_id': sampler_id,
            'filter_position': filter_position,
            'air_volume': air_volume,
            'start_time': start_time,
            'end_time': end_time,
            'observations': observations
        }

        # Obtener la ruta del archivo JSON
        ruta_json = self.obtener_ruta_json("filter.json")

        # Guardar los datos en el archivo JSON
        with open(ruta_json, 'w') as file:
            json.dump(datos_filtro, file)

        QMessageBox.information(self, "Guardado", "Los datos del filtro se han actualizado correctamente.", QMessageBox.StandardButton.Ok)



    def leer_json_camara(self, archivo_json):
        """Lee un archivo JSON y devuelve los datos relevantes."""
        try:
            with open(archivo_json, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            QMessageBox.warning(self, "Advertencia", f"El archivo '{archivo_json}' no existe.", QMessageBox.StandardButton.Ok)
            return
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Advertencia", f"El archivo '{archivo_json}' no es un archivo JSON válido.", QMessageBox.StandardButton.Ok)
            return

        frecuencia = data.get('frecuencia', 2)
        habilitado = data.get('habilitado', True)
        temp_set = data.get('temp_set', -3)

        return {
            'frecuencia': frecuencia,
            'habilitado': habilitado,
            'temp_set': temp_set
        }

    def rellenar_datos_camara(self, datos):
        """Asigna los valores correspondientes a cada campo de texto."""
        self.labelFrecuencia.setText(str(datos['frecuencia']))
        self.checkBox.setChecked(datos['habilitado'])
        self.doubleSpinTemp.setValue(datos['temp_set'])

    def crear_json_camara(self, ruta_carpeta_sns):
        """Crea el archivo camera.json."""
        ruta_camera_json = os.path.join(ruta_carpeta_sns, 'camera.json')
        with open(ruta_camera_json, 'w') as file:
            json.dump(
                {
                    "Frec": 2,
                    "habilitado": True,
                    "Temp_Set": -3
                },
                file
            )

    def guardar_datos_camara(self):
        """Guarda los datos de la cámara en un archivo JSON."""
        # Obtener los datos de los campos de texto del diálogo
        frecuencia = self.dialog.ui.labelFrecuencia.text()
        habilitado = self.dialog.ui.checkBox.isChecked()
        temp_set = self.dialog.ui.doubleSpinTemp.value()

        # Crear un diccionario con los datos
        datos_camara = {
            'frecuencia': frecuencia,
            'habilitado': habilitado,
            'temp_set': temp_set
        }

        # Obtener la ruta del archivo camera.json
        ruta_camera_json = self.obtener_ruta_json("camera.json")

        # Guardar los nuevos datos en el archivo camera.json
        with open(ruta_camera_json, 'w') as file:
            json.dump(datos_camara, file)

        # Informar al usuario que los datos han sido guardados correctamente
        QtWidgets.QMessageBox.information(self, "Guardado", "Los datos de la cámara se han actualizado correctamente.", QtWidgets.QMessageBox.StandardButton.Ok)




    def leer_json_detection(self, archivo_json):
        """Lee un archivo JSON de detección y devuelve los datos relevantes."""
        try:
            with open(archivo_json, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            QMessageBox.warning(self, "Advertencia", f"El archivo '{archivo_json}' no existe.", QMessageBox.StandardButton.Ok)
            return
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Advertencia", f"El archivo '{archivo_json}' no es un archivo JSON válido.", QMessageBox.StandardButton.Ok)
            return

        threshold = data.get('threshold', 180)
        min_radius = data.get('min_radius', 14)
        max_radius = data.get('max_radius', 20)
        polygon = data.get('polygon', 5)

        return {
            'threshold': threshold,
            'min_radius': min_radius,
            'max_radius': max_radius,
            'polygon': polygon
        }

    def rellenar_datos_detection(self, datos):
        """Asigna los valores correspondientes a cada campo de texto de detección."""
        self.hSliderUmbral.setValue(datos['threshold'])
        self.dSpinBoxUmbral.setValue(datos['threshold'])
        self.hSliderRadioMin.setValue(datos['min_radius'])
        self.dSpinBoxRadioMin.setValue(datos['min_radius'])
        self.hSliderRadioMax.setValue(datos['max_radius'])
        self.dSpinBoxRadioMax.setValue(datos['max_radius'])
        self.hSliderGradoPolig.setValue(datos['polygon'])
        self.dSpinBoxGradoPolig.setValue(datos['polygon'])

    def crear_json_detection(self, ruta_carpeta_sns):
        """Crea el archivo detection.json."""
        ruta_detection_json = os.path.join(ruta_carpeta_sns, 'detection.json')
        with open(ruta_detection_json, 'w') as file:
            json.dump({
                "threshold": 180,
                "min_radius": 14,
                "max_radius": 20,
                "polygon": 5
            }
            , file) 

    def guardar_datos_detection(self):
        """Guarda los datos de detección en un archivo JSON."""
        # Obtener los datos de los campos de detección
        threshold = self.dSpinBoxUmbral.value()
        min_radius = self.dSpinBoxRadioMin.value()
        max_radius = self.dSpinBoxRadioMax.value()
        polygon = self.dSpinBoxGradoPolig.value()


        # Crear un diccionario con los datos de detección
        datos_detection = {
            'threshold': threshold,
            'min_radius': min_radius,
            'max_radius': max_radius,
            'polygon': polygon
        }

        # Obtener la ruta del archivo JSON
        ruta_json = self.obtener_ruta_json("detection.json")

        # Guardar los datos de detección en el archivo JSON
        with open(ruta_json, 'w') as file:
            json.dump(datos_detection, file)

        QMessageBox.information(self, "Guardado", "Los datos de detección se han actualizado correctamente.", QMessageBox.StandardButton.Ok)


    def leer_json_temp(self, archivo_json):
        """Lee un archivo JSON de temperatura y devuelve los datos relevantes."""
        try:
            with open(archivo_json, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            QMessageBox.warning(self, "Advertencia", f"El archivo '{archivo_json}' no existe.", QMessageBox.StandardButton.Ok)
            return
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Advertencia", f"El archivo '{archivo_json}' no es un archivo JSON válido.", QMessageBox.StandardButton.Ok)
            return

        temp_max = data.get('tempMax', 0.00)
        temp_min = data.get('tempMin', 0.00)
        temp_set = data.get('tempSet', 0.00)

        return {
            'tempMax': temp_max,
            'tempMin': temp_min,
            'tempSet': temp_set
        }

    def rellenar_datos_temp(self, datos):
        """Asigna los valores correspondientes a cada campo de texto de temperatura."""
        self.dSpinBoxTempMax.setValue(datos['tempMax'])
        self.dSpinBoxTempMin.setValue(datos['tempMin'])
        self.dSpinBoxTempSet.setValue(datos['tempSet'])

    def crear_json_temp(self, ruta_carpeta_sns):
        """Crea el archivo temp.json."""
        ruta_temp_json = os.path.join(ruta_carpeta_sns, 'temp.json')
        with open(ruta_temp_json, 'w') as file:
            json.dump({
                "tempMax": 0.00,
                "tempMin": 0.00,
                "tempSet": 0.00
            }, file) 

    def guardar_datos_temp(self):
        """Guarda los datos de temperatura en un archivo JSON."""
        # Obtener los datos de los campos de temperatura
        temp_max = self.dSpinBoxTempMax.value()
        temp_min = self.dSpinBoxTempMin.value()
        temp_set = self.dSpinBoxTempSet.value()

        # Crear un diccionario con los datos de temperatura
        datos_temp = {
            'tempMax': temp_max,
            'tempMin': temp_min,
            'tempSet': temp_set
        }

        # Obtener la ruta del archivo JSON
        ruta_json = self.obtener_ruta_json("temp.json")

        # Guardar los datos de temperatura en el archivo JSON
        with open(ruta_json, 'w') as file:
            json.dump(datos_temp, file)

        QMessageBox.information(self, "Guardado", "Los datos de temperatura se han actualizado correctamente.", QMessageBox.StandardButton.Ok)




    def obtener_ruta_json(self, archivo):
        """Obtiene la ruta completa del archivo JSON."""
        carpeta_seleccionada = self.txtArchivos.text()
        nombre_filtro = self.comboBoxFiltro.currentText()
        ruta_json = os.path.join(carpeta_seleccionada, nombre_filtro, archivo)
        return ruta_json
    


    ######################## GRAFICA ####################################

    def actualizar_grafica(self):
        # HAY QUE HACER QUE LEA LAS LISTAS Y QUE LAS LISTAS SE ACTUALICEN CONFORME SE TOMAN DATOS
        temperatura_bloque = [20, 25, 30, 28, 27, 26, 25, 24, 23, 22]
        temperatura_liquido = [22, 24, 26, 28, 30, 32, 34, 36, 38, 40]
        temperatura_consigna = [25, 25, 25, 25, 25, 25, 25, 25, 25, 25]
        self.pintar_grafica(temperatura_bloque, temperatura_liquido, temperatura_consigna)
    
    def pintar_grafica(self, temperatura_bloque, temperatura_liquido, temperatura_consigna):
        """Pinta una gráfica utilizando PyQtGraph y la muestra en un QGraphicsView."""
        # Crear un widget de gráfico
        self.plot_widget = pg.PlotWidget()

        # Agregar las líneas de la gráfica
        self.plot_widget.plot(temperatura_bloque, pen=pg.mkPen(color='r'), name='Temperatura Bloque')  # Línea roja para la temperatura del bloque
        self.plot_widget.plot(temperatura_liquido, pen=pg.mkPen(color='b'), name='Temperatura Líquido')  # Línea azul para la temperatura del líquido
        self.plot_widget.plot(temperatura_consigna, pen=pg.mkPen(color='#939393'), name='Temperatura Consigna')  # Línea gris claro para la temperatura de consigna

        # Personalizar la apariencia del gráfico
        self.plot_widget.setBackground('k')  # Color de fondo
        self.plot_widget.setTitle('Rampa de enfriamiento')  # Título
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)  # Mostrar rejilla
        self.plot_widget.getAxis('bottom').setPen(pg.mkPen(color='w'))  # Color del eje x
        self.plot_widget.getAxis('left').setPen(pg.mkPen(color='w'))  # Color del eje y
        self.plot_widget.getAxis('bottom').setTextPen('w')  # Color de los números en el eje x
        self.plot_widget.getAxis('left').setTextPen('w')  # Color de los números en el eje y

        # Crear un proxy widget para el plot_widget
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(self.plot_widget)

        # Ajustar el tamaño del proxy para que coincida con el plot_widget
        proxy.setPos(0, 0)
        proxy.resize(self.graphicsView.width() - 2, self.graphicsView.height() - 2)

        # Agregar el proxy al graphicsView
        self.graphicsView.scene().addItem(proxy)

    ######################### EXPERIMENTO #################################

    def obtener_nombre_experimento(self):
        placa = self.tabWidget_2.tabText(self.tabWidget_2.currentIndex())
        if (placa == "Placa A"):
            nombre_experimento = self.txtNombrePlacaA.text()
            return nombre_experimento
        else:
            nombre_experimento = self.txtNombrePlacaB.text()
            return nombre_experimento
        
    def obtener_ruta_experimento_json(self):
        """Obtiene la ruta completa del archivo JSON."""
        carpeta_seleccionada = self.txtArchivos.text()
        nombre_filtro = self.comboBoxFiltro.currentText()
        fecha_actual = datetime.datetime.now().strftime("%Y%m%d")
        hora_actual = datetime.datetime.now().strftime("%H%M")

        nombre_experimento = self.obtener_nombre_experimento()

        nombre_experimento_con_fecha = f"{fecha_actual}_{hora_actual}_{nombre_experimento}_{self.tabWidget_2.tabText(self.tabWidget_2.currentIndex())}"
        if (not self.checkBoxAmbasPlacas.isChecked()):
            nombre_experimento_con_fecha = f"{fecha_actual}_{hora_actual}_{nombre_experimento}_{self.tabWidget_2.tabText(self.tabWidget_2.currentIndex())}"
        else:
            nombre_experimento_con_fecha = f"{fecha_actual}_{hora_actual}_{self.txtNombrePlacaA.text()}_Placa_AB"
        
        ruta_json = os.path.join(carpeta_seleccionada, nombre_filtro, nombre_experimento_con_fecha, "experimento.json")
        return ruta_json
        
    def obtener_ruta_experimento(self):
        """Obtiene la ruta completa del archivo JSON."""
        carpeta_seleccionada = self.txtArchivos.text()
        nombre_filtro = self.comboBoxFiltro.currentText()
        placa = self.tabWidget_2.tabText(self.tabWidget_2.currentIndex())
        if (placa == "Placa A"):
            nombre_experimento = self.txtNombrePlacaA.text()
        else:
            nombre_experimento = self.txtNombrePlacaB.text()

        fecha_actual = datetime.datetime.now().strftime("%Y%m%d")
        hora_actual = datetime.datetime.now().strftime("%H%M")

        if (not self.checkBoxAmbasPlacas.isChecked()):
            nombre_experimento_con_fecha = f"{fecha_actual}_{hora_actual}_{nombre_experimento}_{placa}"
        else:
            nombre_experimento_con_fecha = f"{fecha_actual}_{hora_actual}_{self.txtNombrePlacaA.text()}_Placa_AB"
        
        ruta_experimento = os.path.join(carpeta_seleccionada, nombre_filtro, nombre_experimento_con_fecha)
        return ruta_experimento

    def iniciar_experimento(self):
        datos_filtro = self.leer_json_filtro(os.path.join(self.txtArchivos.text(), self.comboBoxFiltro.currentText(), "filter.json"))
        datos_detection = self.leer_json_detection(os.path.join(self.txtArchivos.text(), self.comboBoxFiltro.currentText(), "detection.json"))
        placa = self.tabWidget_2.tabText(self.tabWidget_2.currentIndex())
        if (placa == "Placa A"):
            datos_exper = {
                "v_drop": float(self.txtVDropPlacaA.text()),
                "v_wash": float(self.txtVWashPlacaA.text()),
                "dil_factor": float(self.txtFactorDilucPlacaA.text()),
                "filter_fraction": float(self.txtFraccFiltroPlacaA.text()),
                "sampling_rate": float(self.txtTasaMuestreoPlacaA.text()),
                "cooling_rate": float(self.txtVelEnfriamientoPlacaA.text()),
                "observations_exp": self.txtObservPlacaA.toPlainText()
            }
        else:
            datos_exper = {
                "v_drop": float(self.txtVDropPlacaB.text()),
                "v_wash": float(self.txtVWashPlacaB.text()),
                "dil_factor": float(self.txtFactorDilucPlacaB.text()),
                "filter_fraction": float(self.txtFraccFiltroPlacaB.text()),
                "sampling_rate": float(self.txtTasaMuestreoPlacaB.text()),
                "cooling_rate": float(self.txtVelEnfriamientoPlacaB.text()),
                "observations_exp": self.txtObservPlacaB.toPlainText()
            }
        
        ruta_carpeta_experimento = self.obtener_ruta_experimento()

        # Verificar si la carpeta del experimento ya existe
        if not os.path.exists(ruta_carpeta_experimento):
            os.makedirs(ruta_carpeta_experimento)  # Crear la carpeta del experimento si no existe

        global ruta_experimento_activo
        ruta_experimento_activo = ruta_carpeta_experimento

        ruta_json = self.obtener_ruta_experimento_json()

        # Verificar si el archivo JSON ya existe y eliminarlo si es así
        if os.path.exists(ruta_json):
            respuesta = self.mostrar_dialogo_confirmacion("Sobreescribir experimento", "¿Estás seguro de que quieres sobreescribir los datos del experimento?")
            if not respuesta:
                return  
            else:
                os.remove(ruta_json)
        
        datos_experimento = {}
        datos_experimento.update(datos_filtro)
        datos_experimento.update(datos_detection)
        datos_experimento.update(datos_exper)

        with open(ruta_json, 'w') as file:
            json.dump(datos_experimento, file)

        self.buttonParar.setEnabled(True)
        global parar
        parar = False
        self.save()

    def pararExperimento(self):
        global parar
        parar = True


    def mostrar_dialogo_confirmacion(self, titulo, mensaje):
        dialogo = QMessageBox()
        dialogo.setWindowTitle(titulo)
        dialogo.setText(mensaje)
        dialogo.setIcon(QMessageBox.Icon.Question)
        dialogo.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialogo.setDefaultButton(QMessageBox.StandardButton.No)
        respuesta = dialogo.exec()
        return respuesta == QMessageBox.StandardButton.Yes


    def tab_changed(self):

        index = self.tabWidget_2.currentIndex()
        
        if index is not None:
            if index == 0:
                self.buttonIniciar.setEnabled(False)
            elif index == 1 and (self.checkBoxHabilitarA.isChecked() or self.checkBoxAmbasPlacas.isChecked()):
                self.buttonIniciar.setEnabled(True)
            elif index == 2 and self.checkBoxHabilitarB.isChecked():
                self.buttonIniciar.setEnabled(True)
            else:
                self.buttonIniciar.setEnabled(False)

    ####################### CAMARA ##############################
    
    def update_camera_index(self, index):
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()  # Detener el hilo existente
            self.video_thread.finished.connect(self.video_thread.deleteLater)  # Eliminar el objeto del hilo después de que termine

        self.video_thread = VideoThread(MainWindow)
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.set_camera_index(index)
        self.video_thread.start()

    def list_cameras(self):
        """Obtiene una lista de cámaras disponibles."""
        cameras = []
        filter_graph = FilterGraph()
        devices = filter_graph.get_input_devices()

        for index in enumerate(devices):
            cameras.append(index)

        return cameras


    def fillCameras(self):
        """Llena el combobox con las cámaras disponibles."""
        available_cameras = self.get_available_cameras()
        for camera_index, camera_name in available_cameras.items():
            self.comboBoxCamara.addItem(camera_name)

    def settings(self):
        self.video_thread.settings()

    def save(self):
        global ruta_experimento_activo
        if(ruta_experimento_activo is None):
            ruta_experimento_activo = self.obtener_ruta_experimento()
        ruta_imagenes = os.path.join(ruta_experimento_activo, "imagenes")
        
        # Crear la carpeta "imagenes" si no existe
        if not os.path.exists(ruta_imagenes):
            os.makedirs(ruta_imagenes)

        datos_camara = self.leer_json_camara(self.obtener_ruta_json("camera.json"))
        h1 = threading.Thread(name="guardado_imagenes", target=self.comprobar_fotos, args=(ruta_experimento_activo, datos_camara))
        h1.start()


    def comprobar_fotos(self, ruta_imagenes, datos_camara):
        global parar
        while not parar:
            if (self.dSpinBoxTempSet.value() == datos_camara['temp_set']):
                time.sleep(int(datos_camara['frecuencia']))
                self.video_thread.save(ruta_imagenes, self.tabWidget_2.tabText(self.tabWidget_2.currentIndex()), self.checkBoxAmbasPlacas.isChecked())
            else:
                time.sleep(int(datos_camara['frecuencia']))


    @pyqtSlot(np.ndarray)

    def get_available_cameras(self):
        """Obtiene las cámaras disponibles utilizando pygrabber."""
        devices = FilterGraph().get_input_devices()
        available_cameras = {}
        for device_index, device_name in enumerate(devices):
            available_cameras[device_index] = device_name
        return available_cameras

    def update_image(self, cv_img):
        """Actualiza el QLabel con una nueva imagen de OpenCV"""
        qt_img = self.convert_cv_qt(cv_img)
        transform = QTransform()
        transform.rotate(90)
        qt_img = qt_img.transformed(transform)

        # Ajustar el tamaño del widget labelCamara
        self.labelCamara.setPixmap(qt_img)
        self.labelCamara.setFixedSize(qt_img.size())

    def get_status(self):
        """Actualiza la fecha y hora en el widget datetime."""
        self.datetime.setText(f'{datetime.datetime.now():%m/%d/%Y %H:%M:%S}')

    def convert_cv_qt(self, cv_img):
        """Convierte una imagen de OpenCV a QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.display_width, self.display_height, Qt.AspectRatioMode.KeepAspectRatio)
        return QPixmap.fromImage(p)



######################## ANALISIS #################################

    def leer_json_experimento(self):
        """Lee un archivo JSON de temperatura y devuelve los datos relevantes."""

        archivo_json = self.txtArchivos.text() + "/" + self.comboBoxFiltroAn.currentText() + "/" + self.lblExperimentoSeleccionado.text() + "/" + "experimento.json"
        try:
            with open(archivo_json, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            QMessageBox.warning(self, "Advertencia", f"El archivo '{archivo_json}' no existe.", QMessageBox.StandardButton.Ok)
            return
        except json.JSONDecodeError:
            QMessageBox.warning(self, "Advertencia", f"El archivo '{archivo_json}' no es un archivo JSON válido.", QMessageBox.StandardButton.Ok)
            return

        label = data.get('label', '')
        storage_temperature = data.get('storage_temperature', 0.00)
        sampler_id = data.get('sampler_id', '')
        filter_position = data.get('filter_position', 0)
        air_volumen = data.get('air_volumen', 0.00)
        start_time = data.get('start_time', '')
        end_time = data.get('end_time', '')
        observations = data.get('observations', '')
        threshold = data.get('threshold', 0.00)
        min_radius = data.get('min_radius', 0.00)
        max_radius = data.get('max_radius', 0.00)
        polygon = data.get('polygon', 0.00)
        v_drop = data.get('v_drop', 0.00)
        v_wash = data.get('v_wash', 0.00)
        dil_factor = data.get('dil_factor', 0.00)
        filter_fraction = data.get('filter_fraction', 0.00)
        sampling_rate = data.get('sampling_rate', 0.00)
        cooling_rate = data.get('cooling_rate', 0.00)
        observations_exp = data.get('observations_exp', '')

        return {
            'label': label,
            'storage_temperature': storage_temperature,
            'sampler_id': sampler_id,
            'filter_position': filter_position,
            'air_volumen': air_volumen,
            'start_time': start_time,
            'end_time': end_time,
            'observations': observations,
            'threshold': threshold,
            'min_radius': min_radius,
            'max_radius': max_radius,
            'polygon': polygon,
            'v_drop': v_drop,
            'v_wash': v_wash,
            'dil_factor': dil_factor,
            'filter_fraction': filter_fraction,
            'sampling_rate': sampling_rate,
            'cooling_rate': cooling_rate,
            'observations_exp': observations_exp
        }
    
    def cargar_datos_experimento(self):
        datos = self.leer_json_experimento()
        """Asigna los valores correspondientes a cada campo de texto."""
        self.txtNombreExperimento.setText(self.lblExperimentoSeleccionado.text())
        self.txtNombreFiltroAn.setText(datos['label'])
        self.txtTempAlmacenamiento.setText(str(datos['storage_temperature']))
        self.txtIdMuestreador_2.setText(datos['sampler_id'])
        self.txtPosicionFiltro.setText(str(datos['filter_position']))
        self.txtVolAire.setText(str(datos['air_volumen']))
        self.txtHoraInicio_2.setDateTime(QtCore.QDateTime.fromString(datos['start_time'], "yyyy-MM-dd hh:mm"))
        self.txtHoraFin_2.setDateTime(QtCore.QDateTime.fromString(datos['end_time'], "yyyy-MM-dd hh:mm"))

        # Observaciones puede ser nulo, así que verificamos antes de asignar
        if datos['observations'] is not None:
            self.txtObserv.setPlainText(datos['observations'])
        else:
            self.txtObserv.clear()  # Limpiamos el campo si las observaciones son nulas

        self.txtVDrop.setText(str(datos.get('v_drop', '')))
        self.txtVWash.setText(str(datos.get('v_wash', '')))
        self.txtFactorDiluc.setText(str(datos.get('dil_factor', '')))
        self.txtFraccionFiltro.setText(str(datos.get('filter_fraction', '')))
        self.txtTasaMuestreo.setText(str(datos.get('sampling_rate', '')))
        self.txtVelEnfriamiento.setText(str(datos.get('cooling_rate', '')))
        self.txtObservExpe.setPlainText(str(datos.get('observations_exp', '')))

        self.cargar_imagenes()

    def cargar_lista_experimentos(self, ruta):
        self.listExperimentos.clear()
        carpetas_con_experiment_json = []

        # Verificar que la ruta exista y sea un directorio
        if os.path.exists(ruta) and os.path.isdir(ruta):
            # Recorrer cada elemento dentro de la ruta
            for elemento in os.listdir(ruta):
                # Verificar si el elemento es un directorio
                if os.path.isdir(os.path.join(ruta, elemento)):
                    # Verificar si dentro del directorio hay un archivo llamado "experiment.json"
                    if 'experimento.json' in os.listdir(os.path.join(ruta, elemento)):
                        carpetas_con_experiment_json.append(elemento)

        for carpeta in carpetas_con_experiment_json:
            item = QListWidgetItem(carpeta)  # Corrección aquí
            self.listExperimentos.addItem(item)

        return carpetas_con_experiment_json
    
    def mostrar_nombre_experimento(self, item):
        self.lblExperimentoSeleccionado.setText(item.text())


    def guardar_datos_experimento(self):
        """Guarda los datos del experimento en un archivo JSON."""
        # Obtener los datos de los campos del experimento
        nombre_experimento = self.lblExperimentoSeleccionado.text()
        nombre_filtro = self.txtNombreFiltroAn.text()
        temp_almacenamiento = float(self.txtTempAlmacenamiento.text())
        id_muestreador = self.txtIdMuestreador_2.text()
        posicion_filtro = int(self.txtPosicionFiltro.text())
        vol_aire = float(self.txtVolAire.text())
        hora_inicio = self.txtHoraInicio_2.dateTime().toString("yyyy-MM-dd hh:mm")
        hora_fin = self.txtHoraFin_2.dateTime().toString("yyyy-MM-dd hh:mm")
        observaciones = self.txtObserv.toPlainText()
        v_drop = float(self.txtVDrop.text())
        v_wash = float(self.txtVWash.text())
        factor_diluc = float(self.txtFactorDiluc.text())
        fraccion_filtro = float(self.txtFraccionFiltro.text())
        tasa_muestreo = float(self.txtTasaMuestreo.text())
        vel_enfriamiento = float(self.txtVelEnfriamiento.text())
        observaciones_exp = self.txtObservExpe.toPlainText()

        # Crear un diccionario con los datos del experimento
        datos_experimento = {
            'label': nombre_filtro,
            'storage_temperature': temp_almacenamiento,
            'sampler_id': id_muestreador,
            'filter_position': posicion_filtro,
            'air_volumen': vol_aire,
            'start_time': hora_inicio,
            'end_time': hora_fin,
            'observations': observaciones,
            'v_drop': v_drop,
            'v_wash': v_wash,
            'dil_factor': factor_diluc,
            'filter_fraction': fraccion_filtro,
            'sampling_rate': tasa_muestreo,
            'cooling_rate': vel_enfriamiento,
            'observations_exp': observaciones_exp
        }

        archivo_json = self.txtArchivos.text() + "/" + self.comboBoxFiltroAn.currentText() + "/" + self.lblExperimentoSeleccionado.text() + "/" + "experimento.json"

        # Guardar los datos del experimento en el archivo JSON
        with open(archivo_json, 'w') as file:
            json.dump(datos_experimento, file)

        QMessageBox.information(self, "Guardado", "Los datos del experimento se han actualizado correctamente.", QMessageBox.StandardButton.Ok)
        
    def cargar_imagenes(self):
        # Ruta de la carpeta que contiene las imágenes
        carpeta_imagenes = self.txtArchivos.text() + "/" + self.comboBoxFiltroAn.currentText() + "/" + self.lblExperimentoSeleccionado.text() + "/imagenes"

        # Lista para almacenar las imágenes ordenadas como QPixmap
        global lista_imagenes_analisis
        lista_imagenes_analisis = []

        # Obtener la lista de nombres de archivos en la carpeta
        archivos_en_carpeta = os.listdir(carpeta_imagenes)

        # Filtrar solo los archivos de imagen (suponiendo que solo quieres imágenes)
        imagenes = [archivo for archivo in archivos_en_carpeta if archivo.endswith(('.jpg', '.jpeg', '.png', '.gif'))]

        # Ordenar las imágenes por nombre de archivo
        imagenes.sort()

        # Cargar cada imagen como QPixmap y agregarla a la lista
        for imagen_nombre in imagenes:
            # Crea la ruta de la imagen
            ruta_imagen = os.path.join(carpeta_imagenes, imagen_nombre)
            
            # Carga la imagen como QPixmap
            pixmap = QPixmap(ruta_imagen)
            
            # Aplica cualquier transformación necesaria
            pixmap = pixmap.transformed(QTransform().rotate(90))
            
            # Crea una instancia de la clase Imagen y agrega a la lista
            imagen = Imagen(imagen_nombre, pixmap, 0)  # CAMBIAR POR LA TEMPERATURA QUE TENGA EL LIQUIDO
            lista_imagenes_analisis.append(imagen)

        self.sliderFotos.setMaximum(len(lista_imagenes_analisis) - 1) 
        
        self.MostrarPlacaA.setPixmap(lista_imagenes_analisis[0].get_pixmap())
        self.lblImagenA.setText(lista_imagenes_analisis[0].get_nombre())
        self.lblTempA.setText(lista_imagenes_analisis[0].get_temp())
        print("Dimensiones de la imagen:", pixmap.size().width(), "x", pixmap.size().height())
        print("Dimensiones del QLabel:", self.MostrarPlacaA.width(), "x", self.MostrarPlacaA.height())
    
    def actualizar_imagen(self):
        # Obtener el índice seleccionado por el slider
        indice_imagen = self.sliderFotos.value()
        # Cargar la imagen y mostrarla en el QLabel
        self.MostrarPlacaA.setPixmap(lista_imagenes_analisis[indice_imagen].get_pixmap())
        self.lblImagenA.setText(lista_imagenes_analisis[indice_imagen].get_nombre())
        self.lblTempA.setText(str(lista_imagenes_analisis[indice_imagen].get_temp()))


####################### OBJETO FOTO ###########################

class Imagen:
    def __init__(self, nombre, pixmap, temp):
        self._nombre = nombre
        self._pixmap = pixmap
        self._temp = temp

    def get_nombre(self):
        return self._nombre

    def set_nombre(self, nombre):
        self._nombre = nombre

    def get_pixmap(self):
        return self._pixmap

    def set_pixmap(self, pixmap):
        self._pixmap = pixmap

    def get_temp(self):
        return (self._temp + "º")

    def set_temp(self, temp):
        self._temp = temp


# Creación de la aplicación y ventana principal
app = QtWidgets.QApplication([])
window = MainWindow()
window.show()
app.exec()
