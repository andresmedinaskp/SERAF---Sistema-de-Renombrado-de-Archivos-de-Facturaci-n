import os
import sys
import json
import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QMessageBox, QLabel, QGroupBox, QHBoxLayout, QListWidget,
    QAbstractItemView, QMainWindow, QAction, QMenu, QStatusBar,
    QFrame, QProgressBar, QCheckBox, QScrollArea, QComboBox, QListWidgetItem,
    QTabWidget, QFormLayout, QLineEdit, QDialog, QGridLayout
)
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QGraphicsDropShadowEffect
from database_manager import obtener_datos_ips
from config_manager import list_configs, create_config, update_config, delete_config, get_active_config, get_config_by_id

# -------------------------
# Licencia (tu implementación sin parámetros)
# -------------------------
try:
    from licencia import verificar_licencia_global, ControlLicencia
except Exception:
    def verificar_licencia_global():
        return True, "Licencia OK"
    class ControlLicencia:
        def verificar_licencia(self):
            return True, "Licencia OK"

# -------------------------
# Verificar conexión a BD
# -------------------------
_CONFIG_MANAGER_OK = False
_CONFIG_MANAGER_ERROR_MSG = ""  # <-- nueva variable para almacenar el detalle del error
try:
    # Verificar conexión intentando listar configuraciones
    list_configs()
    _CONFIG_MANAGER_OK = True
except Exception as e:
    _CONFIG_MANAGER_OK = False
    _CONFIG_MANAGER_ERROR_MSG = str(e)
    # imprimir en consola para depuración; NO mostrar QMessageBox aquí (aún no hay QApplication seguro)
    print(f"Error de conexión a BD: {_CONFIG_MANAGER_ERROR_MSG}")
    # No hacer sys.exit aquí para permitir que main() maneje la alerta cuando la UI exista

# -------------------------
# UI helpers
# -------------------------
class ElegantButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Segoe UI", 9))  # Reducido de 10 a 9
        self.setMinimumHeight(28)  # Reducido de 34 a 28
        self.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(6)
        shadow.setXOffset(1)
        shadow.setYOffset(1)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(shadow)

class ElegantListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QListWidget {
                background-color: #fbfbfb;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 6px;
                font-family: Segoe UI;
            }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background: #e8f4ff; color: #0b63b7; }
        """)
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setDragDropMode(QAbstractItemView.DropOnly)

class DragDropLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    def dropEvent(self, event):
        if hasattr(self.parent(), 'procesar_arrastre'):
            self.parent().procesar_arrastre(event)

# -------------------------
# SELECTOR VISUAL DE VARIABLES
# -------------------------
class SelectorVariablesDialog(QDialog):
    def __init__(self, campo_actual="", parent=None):
        super().__init__(parent)
        self.campo_destino = None
        self.setWindowTitle("Insertar Variable")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.init_ui(campo_actual)
        
    def init_ui(self, campo_actual):
        layout = QVBoxLayout(self)
        
        # Descripción
        desc = QLabel("Selecciona una variable para insertar en el formato:")
        layout.addWidget(desc)
        
        # Grid de variables
        grid = QGridLayout()
        variables = [
            ("{numFactura}", "Número de factura", "Ej: 12345"),
            ("{ProcesoId}", "ID del proceso", "Ej: 999"),
            ("{ips}", "Código IPS", "Ej: 890000000"),
            ("{nit}", "NIT", "Ej: 900000000"),
            ("{fecha}", "Fecha actual (YYYYMMDD)", "Ej: 20231201"),
            ("{ano}", "Año actual", "Ej: 2023"),
            ("{mes}", "Mes actual", "Ej: 12"),
            ("{dia}", "Día actual", "Ej: 01"),
            ("{nombreCarpeta}", "Nombre de la carpeta", "Ej: CarpetaEjemplo"),
        ]
        
        self.botones_variables = []
        for i, (var, descripcion, ejemplo) in enumerate(variables):
            btn = QPushButton(var)
            btn.setToolTip(f"{descripcion}\n{ejemplo}")
            btn.setStyleSheet("""
                QPushButton {
                    background: #e3f2fd;
                    border: 1px solid #90caf9;
                    border-radius: 3px;
                    padding: 8px;
                    text-align: left;
                }
                QPushButton:hover {
                    background: #bbdefb;
                }
            """)
            btn.clicked.connect(lambda checked, v=var: self.insertar_variable(v))
            grid.addWidget(btn, i, 0)
            
            lbl_desc = QLabel(f"<b>{descripcion}</b><br/><small>{ejemplo}</small>")
            lbl_desc.setStyleSheet("color: #666;")
            grid.addWidget(lbl_desc, i, 1)
            
            self.botones_variables.append(btn)
        
        layout.addLayout(grid)
        
        # Vista previa
        layout.addWidget(QLabel("<b>Vista previa del formato:</b>"))
        self.lbl_preview = QLabel(campo_actual if campo_actual else "(vacío)")
        self.lbl_preview.setStyleSheet("background: #f5f5f5; padding: 8px; border: 1px solid #ddd; border-radius: 3px;")
        self.lbl_preview.setWordWrap(True)
        layout.addWidget(self.lbl_preview)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_limpiar = QPushButton("Limpiar Campo")
        btn_limpiar.clicked.connect(self.limpiar_campo)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_aceptar = QPushButton("Aceptar")
        btn_aceptar.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_limpiar)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_aceptar)
        layout.addLayout(btn_layout)
        
        self.campo_actual = campo_actual
        
    def insertar_variable(self, variable):
        if not self.campo_actual:
            self.campo_actual = variable
        else:
            self.campo_actual += variable
        self.lbl_preview.setText(self.campo_actual)
        
    def limpiar_campo(self):
        self.campo_actual = ""
        self.lbl_preview.setText("(vacío)")
        
    def get_valor(self):
        return self.campo_actual

class CampoConSelector(QWidget):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.init_ui(placeholder)
        
    def init_ui(self, placeholder):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.campo_texto = QLineEdit()
        self.campo_texto.setPlaceholderText(placeholder)
        layout.addWidget(self.campo_texto)
        
        self.btn_selector = QPushButton("📝")
        self.btn_selector.setToolTip("Abrir selector de variables")
        self.btn_selector.setMaximumWidth(40)
        self.btn_selector.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background: #1976D2;
            }
        """)
        self.btn_selector.clicked.connect(self.abrir_selector)
        layout.addWidget(self.btn_selector)
        
    def abrir_selector(self):
        dialogo = SelectorVariablesDialog(self.campo_texto.text(), self)
        if dialogo.exec_() == QDialog.Accepted:
            nuevo_valor = dialogo.get_valor()
            self.campo_texto.setText(nuevo_valor)
            
    def text(self):
        return self.campo_texto.text()
    
    def setText(self, text):
        self.campo_texto.setText(text)

# -------------------------
# Formateo seguro
# -------------------------
class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"

def apply_format(format_str, context):
    if not format_str:
        return None
    try:
        safe = _SafeDict(**context)
        return format_str.format_map(safe)
    except Exception:
        out = format_str
        for k, v in context.items():
            out = out.replace("{" + k + "}", v)
        return out

def needs_placeholder(format_str, placeholder):
    return ("{" + placeholder + "}") in (format_str or "")

# -------------------------
# Configuración de base de datos (REAL desde BD)
# -------------------------
def obtener_configuracion_db():
    """
    Obtiene la configuración real desde la base de datos.
    """
    try:
        return obtener_datos_ips()
    except Exception as e:
        QMessageBox.critical(None, "Error de Base de Datos", 
                           f"No se pudieron obtener los datos de configuración:\n{str(e)}")
        sys.exit(1)

# -------------------------
# Widget: Configuración (pestaña) - MEJORADO CON SELECTOR VISUAL
# -------------------------
class ConfiguracionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pagina = 0
        self.page_size = 12
        self.busqueda_actual = ""
        self.init_ui()
        self.cargar_lista()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10,10,10,10)
        title = QLabel("⚙️ Configuración Global de Nombres de Archivos")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Información sobre variables - MÁS CLARA
        info_label = QLabel(
            "📝 <b>¿Cómo usar?</b> Haz clic en el botón 📝 junto a cada campo para abrir el selector visual de variables.\n"
            "Selecciona las variables que necesites y se insertarán automáticamente en el formato."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("background: #f0f8ff; padding: 10px; border-radius: 5px; border: 1px solid #bde5ff;")
        layout.addWidget(info_label)

        # búsqueda
        search_layout = QHBoxLayout()
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar configuración por nombre...")
        self.txt_buscar.textChanged.connect(self.aplicar_filtro_tiempo_real)
        self.btn_buscar = ElegantButton("🔎 Buscar")
        self.btn_buscar.clicked.connect(self.buscar)
        search_layout.addWidget(self.txt_buscar)
        search_layout.addWidget(self.btn_buscar)
        layout.addLayout(search_layout)

        # lista
        self.tabla = ElegantListWidget()
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.itemDoubleClicked.connect(self.seleccionar_item)
        self.tabla.itemClicked.connect(self.seleccionar_item)
        self.tabla.setMinimumHeight(220)
        layout.addWidget(self.tabla)

        # paginación
        nav = QHBoxLayout()
        self.btn_prev = ElegantButton("⬅️")
        self.btn_prev.clicked.connect(self.anterior_pagina)
        self.btn_next = ElegantButton("➡️")
        self.btn_next.clicked.connect(self.siguiente_pagina)
        nav.addWidget(self.btn_prev)
        nav.addWidget(self.btn_next)
        layout.addLayout(nav)

        # formulario CON SELECTORES VISUALES
        form = QFormLayout()
        
        self.txt_nombre = QLineEdit()
        
        # Campos con selector visual
        self.txt_xml = CampoConSelector("Ej: Factura_{numFactura}_{ips}.xml")
        self.txt_pdf = CampoConSelector("Ej: Comprobante_{numFactura}.pdf")
        self.txt_cuv = CampoConSelector("Ej: Resultado_{numFactura}_CUV.json")
        self.txt_json = CampoConSelector("Ej: RIPS_{numFactura}.json")
        
        form.addRow("Nombre Configuración:", self.txt_nombre)
        form.addRow("Formato XML (.xml):", self.txt_xml)
        form.addRow("Formato PDF (.pdf):", self.txt_pdf)
        form.addRow("Formato CUV JSON (.json):", self.txt_cuv)
        form.addRow("Formato JSON Factura (.json):", self.txt_json)
        layout.addLayout(form)

        # botones
        actions = QHBoxLayout()
        self.btn_guardar = ElegantButton("💾 Guardar")
        self.btn_activar = ElegantButton("✅ Activar")
        self.btn_eliminar = ElegantButton("🗑️ Eliminar")
        self.btn_preview = ElegantButton("🔍 Previsualizar")
        actions.addWidget(self.btn_guardar); actions.addWidget(self.btn_activar)
        actions.addWidget(self.btn_eliminar); actions.addWidget(self.btn_preview)
        layout.addLayout(actions)

        # conexiones
        self.btn_guardar.clicked.connect(self.guardar_config)
        self.btn_activar.clicked.connect(self.activar_config)
        self.btn_eliminar.clicked.connect(self.eliminar_config)
        self.btn_preview.clicked.connect(self.previsualizar)

    def aplicar_filtro_tiempo_real(self):
        """Aplicar filtro en tiempo real mientras se escribe"""
        self.busqueda_actual = self.txt_buscar.text().strip()
        self.pagina = 0
        self.cargar_lista()

    def buscar(self):
        """Buscar configuraciones"""
        self.busqueda_actual = self.txt_buscar.text().strip()
        self.pagina = 0
        self.cargar_lista()

    def cargar_lista(self):
        """Cargar lista de configuraciones con filtro y paginación"""
        self.tabla.clear()
        try:
            configs = list_configs()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la lista: {e}")
            configs = []
        
        # Aplicar filtro si hay búsqueda
        if self.busqueda_actual:
            configs = [c for c in configs if self.busqueda_actual.lower() in (c.get('nombre') or "").lower()]
        
        # Paginación
        inicio = self.pagina * self.page_size
        paginados = configs[inicio:inicio+self.page_size]
        
        for c in paginados:
            texto = f"{c['id']:03d} - {c.get('nombre')}"
            item = QListWidgetItem(texto)
            if c.get('activa'):
                item.setIcon(QIcon.fromTheme("dialog-ok"))
            self.tabla.addItem(item)
        
        self.btn_prev.setEnabled(self.pagina > 0)
        self.btn_next.setEnabled(len(configs) > inicio + self.page_size)

    def siguiente_pagina(self):
        """Ir a la siguiente página"""
        self.pagina += 1
        self.cargar_lista()

    def anterior_pagina(self):
        """Ir a la página anterior"""
        if self.pagina > 0:
            self.pagina -= 1
            self.cargar_lista()

    def _item_id(self):
        """Obtener ID del item seleccionado"""
        item = self.tabla.currentItem()
        if not item:
            return None
        try:
            return int(item.text().split("-")[0])
        except:
            return None

    def seleccionar_item(self):
        """Cargar datos de la configuración seleccionada"""
        id_ = self._item_id()
        if not id_:
            return
        try:
            cfg = get_config_by_id(id_)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer la config: {e}")
            return
        if cfg:
            self.txt_nombre.setText(cfg.get('nombre') or "")
            self.txt_xml.setText(cfg.get('formato_xml') or "")
            self.txt_pdf.setText(cfg.get('formato_pdf') or "")
            self.txt_cuv.setText(cfg.get('formato_cuv') or "")
            self.txt_json.setText(cfg.get('formato_json') or "")

    def validar_formatos(self):
        """Valida que los formatos tengan extensiones correctas"""
        formatos = {
            'XML': self.txt_xml.text().strip(),
            'PDF': self.txt_pdf.text().strip(), 
            'CUV': self.txt_cuv.text().strip(),
            'JSON Factura': self.txt_json.text().strip()
        }
        
        errores = []
        for tipo, formato in formatos.items():
            if formato:  # Si el campo no está vacío
                if tipo == 'XML' and not formato.endswith('.xml'):
                    errores.append(f"Formato XML debe terminar en .xml: {formato}")
                elif tipo == 'PDF' and not formato.endswith('.pdf'):
                    errores.append(f"Formato PDF debe terminar en .pdf: {formato}")
                elif tipo in ['CUV', 'JSON Factura'] and not formato.endswith('.json'):
                    errores.append(f"Formato {tipo} debe terminar en .json: {formato}")
        
        return errores

    def guardar_config(self):
        """Guardar configuración"""
        id_ = self._item_id()
        nombre = self.txt_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Validación", "Nombre obligatorio")
            return
        
        # Validar extensiones
        errores = self.validar_formatos()
        if errores:
            QMessageBox.warning(self, "Validación de formatos", "\n".join(errores))
            return
        
        try:
            if id_:
                update_config(id_, nombre=nombre,
                              formato_xml=self.txt_xml.text(),
                              formato_pdf=self.txt_pdf.text(),
                              formato_cuv=self.txt_cuv.text(),
                              formato_json=self.txt_json.text())
            else:
                create_config(nombre,
                              formato_xml=self.txt_xml.text(),
                              formato_pdf=self.txt_pdf.text(),
                              formato_cuv=self.txt_cuv.text(),
                              formato_json=self.txt_json.text())
            self.cargar_lista()
            QMessageBox.information(self, "OK", "Configuración guardada correctamente")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")

    def activar_config(self):
        """Activar configuración seleccionada"""
        id_ = self._item_id()
        if not id_:
            QMessageBox.warning(self, "Validación", "Selecciona una configuración primero")
            return
        try:
            update_config(id_, activar=True)
            self.cargar_lista()
            QMessageBox.information(self, "OK", "Configuración activada")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo activar: {e}")

    def eliminar_config(self):
        """Eliminar configuración seleccionada"""
        id_ = self._item_id()
        if not id_:
            QMessageBox.warning(self, "Validación", "Selecciona una configuración primero")
            return
        try:
            delete_config(id_)
            self.cargar_lista()
            # Limpiar campos
            self.txt_nombre.clear()
            self.txt_xml.setText("")
            self.txt_pdf.setText("")
            self.txt_cuv.setText("")
            self.txt_json.setText("")
            QMessageBox.information(self, "OK", "Configuración eliminada")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar: {e}")

    def previsualizar(self):
        """Mostrar previsualización de los formatos"""
        # Obtener configuración REAL desde BD
        try:
            config_db = obtener_configuracion_db()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron obtener los datos de configuración: {e}")
            return
        
        contexto = {
            "numFactura": "12345",
            "ProcesoId": "999",
            "ips": config_db.get("codigo_ips", ""),
            "nit": config_db.get("nit", "")
        }
        
        # Validar formatos primero
        errores = self.validar_formatos()
        if errores:
            QMessageBox.warning(self, "Formatos incorrectos", "\n".join(errores))
            return
        
        xml = apply_format(self.txt_xml.text(), contexto) or "(no definido)"
        pdf = apply_format(self.txt_pdf.text(), contexto) or "(no definido)"
        cuv = apply_format(self.txt_cuv.text(), contexto) or "(no definido)"
        jsn = apply_format(self.txt_json.text(), contexto) or "(no definido)"
        
        mensaje = f"<b>Ejemplo con datos de prueba:</b><br/><br/>"
        mensaje += f"<b>XML:</b> {xml}<br/>"
        mensaje += f"<b>PDF:</b> {pdf}<br/>"
        mensaje += f"<b>CUV JSON:</b> {cuv}<br/>"
        mensaje += f"<b>Factura JSON:</b> {jsn}<br/><br/>"
        mensaje += f"<b>Contexto usado:</b><br/>"
        for k, v in contexto.items():
            mensaje += f"  {k}: {v}<br/>"
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Previsualización")
        msg.setTextFormat(Qt.RichText)
        msg.setText(mensaje)
        msg.exec_()

# -------------------------
# Renombrador (principal)
# -------------------------
class RenombradorCUVWidget(QWidget):
    progress_updated = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.carpetas = []
        self.last_context = None
        self.setAcceptDrops(True)  # Habilitar drops en el widget principal
        self.init_ui()

    def dragEnterEvent(self, event):  # Nombre corregido del método
        """Acepta el arrastre sobre el widget principal"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Maneja el soltar archivos en el widget principal"""
        self.procesar_arrastre(event)

    def procesar_arrastre(self, event):
        """Procesa el arrastre de carpetas"""
        urls = event.mimeData().urls()
        for url in urls:
            path = url.toLocalFile()
            if os.path.isdir(path) and path not in self.carpetas:
                self.carpetas.append(path)
                self.lista_carpetas.addItem(path)
        self.actualizar_boton_procesar()
        event.acceptProposedAction()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(12)

        lbl_titulo = QLabel("🔄 SERAF - Sistema de Renombrado de Archivos de Facturación")
        lbl_titulo.setFont(QFont("Segoe UI", 16, QFont.Bold))
        lbl_titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_titulo)

        lbl_sub = QLabel("Arrastra carpetas que contengan archivos CUV.json y facturas .json")
        lbl_sub.setFont(QFont("Segoe UI", 10))
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet("color:#666")
        layout.addWidget(lbl_sub)

        # botones quitar/limpiar
        frame_btns = QFrame()
        frame_btns.setStyleSheet("""
            QFrame {
                background:#fff;
                padding: 4px;  /* Reducido de 8px a 4px */
                border-radius: 4px;  /* Reducido de 6px a 4px */
                border: 1px solid #e6e6e6;
            }
        """)
        hbtn = QHBoxLayout(frame_btns)
        hbtn.setContentsMargins(4, 4, 4, 4)  # Reducir márgenes
        hbtn.setSpacing(6)  # Reducir espacio entre botones
        
        self.btn_quitar = ElegantButton("🗑️ Quitar")  # Texto más corto
        self.btn_limpiar = ElegantButton("🧹 Limpiar")  # Texto más corto
        hbtn.addWidget(self.btn_quitar)
        hbtn.addWidget(self.btn_limpiar)
        layout.addWidget(frame_btns)

        # lista carpetas
        grp = QGroupBox("📁 Carpetas seleccionadas")
        grp.setFont(QFont("Segoe UI", 11, QFont.Bold))
        vgrp = QVBoxLayout(grp)
        self.lista_carpetas = ElegantListWidget()
        self.lista_carpetas.setSelectionMode(QAbstractItemView.MultiSelection)
        self.lista_carpetas.setAcceptDrops(True)
        # Conectar eventos de arrastre directamente
        self.lista_carpetas.dragEnterEvent = lambda e: self.dragEnterEvent(e)
        self.lista_carpetas.dropEvent = lambda e: self.dropEvent(e)
        vgrp.addWidget(self.lista_carpetas)
        layout.addWidget(grp)

        # label arrastre
        self.lbl_arrastre = DragDropLabel("⬆️ Arrastra carpetas aquí o suelta en la lista de arriba")
        self.lbl_arrastre.setFont(QFont("Segoe UI", 9))
        self.lbl_arrastre.setAlignment(Qt.AlignCenter)
        self.lbl_arrastre.setStyleSheet("color:#888;padding:12px;border:2px dashed #e6e6e6;border-radius:6px")
        self.lbl_arrastre.dragEnterEvent = lambda e: self.dragEnterEvent(e)
        self.lbl_arrastre.dropEvent = lambda e: self.dropEvent(e)
        layout.addWidget(self.lbl_arrastre)

        # OPCIONES DE PROCESAMIENTO - CORREGIDAS Y CLARAS
        frame_opts = QFrame()
        frame_opts.setStyleSheet("QFrame{background:#fff;padding:10px;border-radius:6px;border:1px solid #e6e6e6}")
        vopts = QVBoxLayout(frame_opts)
        lbl_opts = QLabel("⚙️ Opciones de Procesamiento")
        lbl_opts.setFont(QFont("Segoe UI", 11, QFont.Bold))
        vopts.addWidget(lbl_opts)

        # OPCIÓN 1: Renombrar archivos (REQUIERE configuración seleccionada)
        self.chk_renombrar_archivos = QCheckBox("1. Renombrar archivos usando configuración seleccionada")
        self.chk_renombrar_archivos.setChecked(False)
        self.chk_renombrar_archivos.setToolTip("Obligatorio: debe tener una configuración seleccionada abajo")
        
        # OPCIÓN 2: Modificar archivos CUV (eliminar elementos)
        self.chk_modificar_cuv = QCheckBox("2. Modificar archivos CUV (eliminar elementos del array)")
        self.chk_modificar_cuv.setChecked(False)
        
        # Sub-opciones para modificación CUV
        self.radio_eliminar_rechazados = QCheckBox("   • Eliminar solo elementos con clase 'RECHAZADO'")
        self.radio_eliminar_rechazados.setEnabled(False)  # Inicialmente deshabilitado
        self.radio_eliminar_rechazados.setChecked(False)
        
        self.radio_eliminar_todo = QCheckBox("   • Eliminar todo el array ResultadosValidacion (vaciar)")
        self.radio_eliminar_todo.setEnabled(False)  # Inicialmente deshabilitado
        self.radio_eliminar_todo.setChecked(False)
        
        vopts.addWidget(self.chk_renombrar_archivos)
        vopts.addSpacing(10)
        vopts.addWidget(self.chk_modificar_cuv)
        vopts.addWidget(self.radio_eliminar_rechazados)
        vopts.addWidget(self.radio_eliminar_todo)

        # Configuración de nombres (OBLIGATORIA para renombrar)
        hcfg = QHBoxLayout()
        lbl_config = QLabel("📋 Configuración de nombres:")
        lbl_config.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.cmb_configs = QComboBox()
        self.cmb_configs.setMinimumWidth(300)
        self.btn_ref = ElegantButton("⟳")
        self.btn_ref.setMaximumWidth(40)
        hcfg.addWidget(lbl_config)
        hcfg.addWidget(self.cmb_configs)
        hcfg.addWidget(self.btn_ref)
        vopts.addLayout(hcfg)

        # Estado de la configuración
        self.lbl_estado_config = QLabel("ℹ️ Selecciona una configuración para renombrar archivos")
        self.lbl_estado_config.setStyleSheet("color: #666; font-size: 10px; padding: 5px;")
        vopts.addWidget(self.lbl_estado_config)

        vopts.addStretch()
        layout.addWidget(frame_opts)

        # PREVIEW label for selected configuration
        self.lbl_preview = QLabel("")
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setStyleSheet("color:#333;font-size:11px; background: #f0f8ff; padding: 8px; border-radius: 4px;")
        layout.addWidget(self.lbl_preview)

        # Progress + procesar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.btn_procesar = ElegantButton("🚀 Procesar Archivos")
        self.btn_procesar.setEnabled(False)
        layout.addWidget(self.btn_procesar)

        # Conexiones - CORREGIDO Y ACTUALIZADO
        self.btn_quitar.clicked.connect(self.quitar_seleccionados)
        self.btn_limpiar.clicked.connect(self.limpiar_lista)
        self.progress_updated.connect(self.progress_bar.setValue)
        self.btn_ref.clicked.connect(self.reload_configs_into_combo)
        self.cmb_configs.currentIndexChanged.connect(self.actualizar_estado_config)
        
        # Conexiones para las opciones CUV
        self.chk_modificar_cuv.stateChanged.connect(self.actualizar_opciones_cuv)
        self.radio_eliminar_rechazados.clicked.connect(lambda: self._mutual_check_cuv(self.radio_eliminar_rechazados))
        self.radio_eliminar_todo.clicked.connect(lambda: self._mutual_check_cuv(self.radio_eliminar_todo))
        
        # Conexiones para actualizar estado del botón procesar
        self.chk_renombrar_archivos.stateChanged.connect(self.actualizar_boton_procesar)
        self.chk_modificar_cuv.stateChanged.connect(self.actualizar_boton_procesar)
        self.lista_carpetas.model().rowsInserted.connect(self.actualizar_boton_procesar)
        self.lista_carpetas.model().rowsRemoved.connect(self.actualizar_boton_procesar)
        
        # Conexión del botón procesar
        self.btn_procesar.clicked.connect(self.procesar_archivos)

    def _mutual_check_cuv(self, clicked_checkbox):
        """Controla que solo una opción de modificación CUV esté activa"""
        if clicked_checkbox == self.radio_eliminar_rechazados:
            if clicked_checkbox.isChecked():
                self.radio_eliminar_todo.setChecked(False)
        else:  # clicked_checkbox == self.radio_eliminar_todo
            if clicked_checkbox.isChecked():
                self.radio_eliminar_rechazados.setChecked(False)

    def actualizar_opciones_cuv(self):
        """Habilita/deshabilita las opciones de modificación CUV"""
        enabled = self.chk_modificar_cuv.isChecked()
        self.radio_eliminar_rechazados.setEnabled(enabled)
        self.radio_eliminar_todo.setEnabled(enabled)
        
        # Si se desactiva la modificación CUV, desmarcar las sub-opciones
        if not enabled:
            self.radio_eliminar_rechazados.setChecked(False)
            self.radio_eliminar_todo.setChecked(False)

    def reload_configs_into_combo(self):
        self.cmb_configs.clear()
        try:
            configs = list_configs()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar las configuraciones: {e}")
            configs = []
        self.cmb_configs.addItem("-- Selecciona una configuración --", None)
        for c in configs:
            label = f"{c['id']:03d} - {c.get('nombre')}"
            if c.get('activa'):
                label += " (ACTIVA)"
            self.cmb_configs.addItem(label, c['id'])
        # seleccionar activa si hay y si no hay selección previa
        act = get_active_config()
        if act:
            for i in range(self.cmb_configs.count()):
                if self.cmb_configs.itemData(i) == act.get('id'):
                    self.cmb_configs.setCurrentIndex(i)
                    break
        self.actualizar_estado_config()

    def actualizar_estado_config(self):
        """Actualiza el estado de la configuración y el preview"""
        config_id = self.cmb_configs.currentData()
        renombrar_activado = self.chk_renombrar_archivos.isChecked()
        
        if config_id is None:
            # No hay configuración seleccionada
            self.lbl_estado_config.setText("❌ Debes seleccionar una configuración para renombrar archivos")
            self.lbl_estado_config.setStyleSheet("color: #d32f2f; font-size: 10px; padding: 5px; background: #ffebee;")
            if renombrar_activado:
                self.chk_renombrar_archivos.setChecked(False)
                QMessageBox.warning(self, "Configuración requerida", 
                                  "Para renombrar archivos debes seleccionar una configuración de nombres.")
        else:
            # Hay configuración seleccionada
            try:
                cfg = get_config_by_id(config_id)
                if cfg:
                    estado = "✅ Configuración seleccionada"
                    if cfg.get('activa'):
                        estado += " (ACTIVA)"
                    self.lbl_estado_config.setText(estado)
                    self.lbl_estado_config.setStyleSheet("color: #388e3c; font-size: 10px; padding: 5px; background: #e8f5e8;")
                    
                    # Mostrar preview
                    try:
                        config_db = obtener_configuracion_db()
                        contexto = {
                            "numFactura": "12345",
                            "ProcesoId": "999",
                            "fecha": datetime.datetime.now().strftime('%Y%m%d'),
                            "ano": datetime.datetime.now().strftime('%Y'),
                            "mes": datetime.datetime.now().strftime('%m'),
                            "dia": datetime.datetime.now().strftime('%d'),
                            "ips": config_db.get("codigo_ips", ""),
                            "nit": config_db.get("nit", ""),
                            "nombreCarpeta": "CarpetaEjemplo"
                        }
                        
                        xml = apply_format(cfg.get('formato_xml'), contexto) or "(no definido)"
                        pdf = apply_format(cfg.get('formato_pdf'), contexto) or "(no definido)"
                        cuv = apply_format(cfg.get('formato_cuv'), contexto) or "(no definido)"
                        jsn = apply_format(cfg.get('formato_json'), contexto) or "(no definido)"
                        
                        preview_text = f"📝 <b>Vista previa:</b> XML: <code>{xml}</code> | PDF: <code>{pdf}</code> | CUV: <code>{cuv}</code> | Factura: <code>{jsn}</code>"
                        self.lbl_preview.setText(preview_text)
                    except Exception as e:
                        self.lbl_preview.setText(f"⚠️ Error en vista previa: {str(e)}")
                else:
                    self.lbl_estado_config.setText("❌ Configuración no encontrada")
                    self.lbl_estado_config.setStyleSheet("color: #d32f2f; font-size: 10px; padding: 5px; background: #ffebee;")
            except Exception as e:
                self.lbl_estado_config.setText(f"❌ Error cargando configuración: {str(e)}")
                self.lbl_estado_config.setStyleSheet("color: #d32f2f; font-size: 10px; padding: 5px; background: #ffebee;")

    def quitar_seleccionados(self):
        """Quitar las carpetas seleccionadas de la lista"""
        items = self.lista_carpetas.selectedItems()
        for item in items:
            row = self.lista_carpetas.row(item)
            carpeta = item.text()
            self.lista_carpetas.takeItem(row)
            if carpeta in self.carpetas:
                self.carpetas.remove(carpeta)
        self.actualizar_boton_procesar()

    def limpiar_lista(self):
        """Limpiar toda la lista de carpetas"""
        self.lista_carpetas.clear()
        self.carpetas.clear()
        self.actualizar_boton_procesar()

    def actualizar_boton_procesar(self):
        """Habilita el botón procesar si hay carpetas y opciones seleccionadas"""
        tiene_carpetas = len(self.carpetas) > 0
        tiene_opciones = self.chk_renombrar_archivos.isChecked() or self.chk_modificar_cuv.isChecked()
        self.btn_procesar.setEnabled(tiene_carpetas and tiene_opciones)

    # ... (métodos drag & drop, quitar, limpiar iguales)

    def obtener_num_factura_desde_contenido(self, archivo_factura):
        try:
            with open(archivo_factura, 'r', encoding='utf-8') as f:
                d = json.load(f)
            nf = d.get("numFactura")
            return str(nf).strip() if nf is not None else None
        except Exception:
            return None

    def buscar_archivos_por_ext(self, carpeta, exts):
        """Busca archivos por extensión - MEJORADO"""
        encontrados = []
        for raiz, _, archivos in os.walk(carpeta):
            for a in archivos:
                nombre_lower = a.lower()
                if any(nombre_lower.endswith(e.lower()) for e in exts):
                    encontrados.append(os.path.join(raiz, a))
        return sorted(encontrados)  # Ordenar para procesar en orden consistente

    def _obtener_archivos_asociados(self, num_factura, archivos_xml, archivos_pdf, carpeta_actual):
        """Busca archivos XML y PDF asociados a una factura"""
        xml_asociado = None
        pdf_asociado = None
        
        # Buscar por número de factura en el nombre
        num_str = str(num_factura)
        for archivo_xml in archivos_xml:
            if num_str in os.path.basename(archivo_xml):
                xml_asociado = archivo_xml
                break
                
        for archivo_pdf in archivos_pdf:
            if num_str in os.path.basename(archivo_pdf):
                pdf_asociado = archivo_pdf
                break
        
        # Si no se encontró, buscar en la misma carpeta que la factura
        if not xml_asociado:
            xmls_carpeta = [x for x in archivos_xml if os.path.dirname(x) == carpeta_actual]
            if xmls_carpeta:
                xml_asociado = xmls_carpeta[0]
        
        if not pdf_asociado:
            pdfs_carpeta = [p for p in archivos_pdf if os.path.dirname(p) == carpeta_actual]
            if pdfs_carpeta:
                pdf_asociado = pdfs_carpeta[0]
                
        return xml_asociado, pdf_asociado

    def obtener_proceso_id_desde_cuv(self, archivo_cuv):
        """Obtiene el ProcesoId desde el archivo CUV"""
        try:
            with open(archivo_cuv, 'r', encoding='utf-8') as f:
                datos = json.load(f)
                return str(datos.get("ProcesoId", "")) if datos.get("ProcesoId") else ""
        except Exception as e:
            print(f"Error leyendo ProcesoId desde CUV {archivo_cuv}: {e}")
            return ""

    def procesar_archivos(self):
        print("DEBUG: Método procesar_archivos llamado")
        if not self.carpetas:
            QMessageBox.warning(self, "Advertencia", "No hay carpetas seleccionadas.")
            return

        # Validar opciones seleccionadas
        renombrar = self.chk_renombrar_archivos.isChecked()
        modificar_cuv = self.chk_modificar_cuv.isChecked()
        
        if not renombrar and not modificar_cuv:
            QMessageBox.warning(self, "Advertencia", "Debes seleccionar al menos una opción de procesamiento.")
            return
        
        if renombrar:
            config_id = self.cmb_configs.currentData()
            if config_id is None:
                QMessageBox.warning(self, "Configuración requerida", 
                                "Para renombrar archivos debes seleccionar una configuración de nombres.")
                return
            try:
                cfg = get_config_by_id(config_id)
                if not cfg:
                    QMessageBox.critical(self, "Error", "La configuración seleccionada no existe.")
                    return
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo cargar la configuración: {e}")
                return
        else:
            cfg = None

        if modificar_cuv:
            if not self.radio_eliminar_rechazados.isChecked() and not self.radio_eliminar_todo.isChecked():
                QMessageBox.warning(self, "Advertencia", 
                                "Para modificar archivos CUV debes seleccionar una opción: eliminar RECHAZADOS o vaciar el array.")
                return

        # Solicitar archivo de log
        archivo_log, _ = QFileDialog.getSaveFileName(self, "Guardar registro de procesamiento",
                                                    f"Registro_CUV_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                                                    "Archivos de texto (*.log);;Todos los archivos (*)")
        if not archivo_log:
            return

        # Preparar UI
        self.btn_procesar.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        QApplication.processEvents()

        # contadores
        renombrados = {'cuv':0, 'fact':0, 'xml':0, 'pdf':0}
        modificados_cuv = 0
        errores = []
        carpetas_procesadas = set()
        total = len(self.carpetas)

        # Obtener configuración REAL desde BD
        try:
            config_db = obtener_configuracion_db()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron obtener los datos de configuración: {e}")
            self.btn_procesar.setEnabled(True)
            self.progress_bar.setVisible(False)
            return

        # procesar cada carpeta
        for idx, carpeta in enumerate(self.carpetas):
            self.progress_updated.emit(int((idx / total) * 100))
            QApplication.processEvents()
            
            if not os.path.exists(carpeta):
                errores.append(f"Carpeta no existe: {carpeta}")
                continue
                
            carpeta_real = os.path.abspath(carpeta)
            if carpeta_real in carpetas_procesadas:
                continue
            carpetas_procesadas.add(carpeta_real)

            print(f"Procesando carpeta: {carpeta_real}")

            # buscar archivos CUV - MÉTODO MEJORADO
            archivos_cuv = self.buscar_archivos_cuv_mejorado(carpeta_real)
            print(f"  - Archivos CUV encontrados: {len(archivos_cuv)}")
            for cuv in archivos_cuv:
                print(f"    * {os.path.basename(cuv)}")

            # MODIFICAR ARCHIVOS CUV (si está activado)
            if modificar_cuv:
                for archivo_cuv in archivos_cuv:
                    try:
                        if self.modificar_archivo_cuv(archivo_cuv):
                            modificados_cuv += 1
                            print(f"  - Modificado: {os.path.basename(archivo_cuv)}")
                    except Exception as e:
                        errores.append(f"Error modificando CUV {archivo_cuv}: {e}")

            # RENOMBRAR ARCHIVOS (si está activado y hay configuración)
            if renombrar and cfg:
                # PRIMERO: Procesar archivos CUV para renombrarlos
                for archivo_cuv in archivos_cuv:
                    try:
                        # Extraer número de factura del nombre del archivo CUV
                        try:
                            with open(archivo_cuv, 'r', encoding='utf-8') as f:
                                datos_cuv = json.load(f)
                            num_factura = datos_cuv.get("NumFactura")  # Leer del campo "NumFactura" del JSON
                        except Exception as e:
                            print(f"Error leyendo CUV {archivo_cuv}: {e}")
                            continue
                        
                        if not num_factura:
                            print(f"  - No se pudo extraer número de factura de: {archivo_cuv}")
                            continue
                        
                         # Obtener ProcesoId desde el archivo CUV
                        proceso_id = self.obtener_proceso_id_desde_cuv(archivo_cuv)
                        
                        # Crear contexto para formateo
                        contexto = {
                            "numFactura": str(num_factura),
                            "ProcesoId": proceso_id,
                            "fecha": datetime.datetime.now().strftime('%Y%m%d'),
                            "ano": datetime.datetime.now().strftime('%Y'),
                            "mes": datetime.datetime.now().strftime('%m'),
                            "dia": datetime.datetime.now().strftime('%d'),
                            "ips": config_db.get("codigo_ips", ""),
                            "nit": config_db.get("nit", ""),
                            "nombreCarpeta": os.path.basename(carpeta_real)
                        }
                        
                        # Renombrar archivo CUV
                        if cfg.get('formato_cuv'):
                            nuevo_nombre_cuv = apply_format(cfg.get('formato_cuv'), contexto)
                            if nuevo_nombre_cuv:
                                dir_cuv = os.path.dirname(archivo_cuv)
                                nuevo_path_cuv = os.path.join(dir_cuv, nuevo_nombre_cuv)
                                
                                # Verificar si ya tiene el nombre correcto
                                if os.path.basename(archivo_cuv) != nuevo_nombre_cuv:
                                    if self._safe_move_or_write_json(archivo_cuv, nuevo_path_cuv):
                                        renombrados['cuv'] += 1
                                        print(f"  - Renombrado CUV: {os.path.basename(archivo_cuv)} -> {nuevo_nombre_cuv}")
                                    else:
                                        errores.append(f"Error renombrando CUV: {archivo_cuv}")
                                else:
                                    print(f"  - CUV ya tiene nombre correcto: {nuevo_nombre_cuv}")
                                    renombrados['cuv'] += 1  # Contar como renombrado
                        
                    except Exception as e:
                        errores.append(f"Error procesando CUV {archivo_cuv}: {e}")

                # SEGUNDO: Procesar otros archivos (facturas, XML, PDF)
                facturas = self.buscar_archivos_por_ext(carpeta_real, ['.json'])
                facturas = [f for f in facturas if not any(cuv in f.lower() for cuv in ['_cuv', '_cuv_renamed'])]
                
                archivos_xml = self.buscar_archivos_por_ext(carpeta_real, ['.xml'])
                archivos_pdf = self.buscar_archivos_por_ext(carpeta_real, ['.pdf'])

                for fact in facturas:
                    try:
                        with open(fact, 'r', encoding='utf-8') as f:
                            d = json.load(f)
                    except Exception as e:
                        errores.append(f"Error leyendo factura {fact}: {e}")
                        continue
                    
                    num_factura = d.get("numFactura")
                    if not num_factura:
                        errores.append(f"Factura sin numFactura: {fact}")
                        continue
                    
                    carpeta_actual = os.path.dirname(fact)
                    proceso_id = ""  # Para otros archivos, no necesitamos ProcesoId
                    
                    # Buscar archivos asociados
                    xml_asociado, pdf_asociado = self._obtener_archivos_asociados(
                        num_factura, archivos_xml, archivos_pdf, carpeta_actual)
                    
                    # contexto para formateo
                    contexto = {
                        "numFactura": str(num_factura),
                        "ProcesoId": proceso_id,
                        "fecha": datetime.datetime.now().strftime('%Y%m%d'),
                        "ano": datetime.datetime.now().strftime('%Y'),
                        "mes": datetime.datetime.now().strftime('%m'),
                        "dia": datetime.datetime.now().strftime('%d'),
                        "ips": config_db.get("codigo_ips", ""),
                        "nit": config_db.get("nit", ""),
                        "nombreCarpeta": os.path.basename(carpeta_real)
                    }
                    
                    # Renombrar factura JSON
                    fmt_fact = cfg.get('formato_json')
                    if fmt_fact:
                        nuevo_nombre_fact = apply_format(fmt_fact, contexto)
                        if nuevo_nombre_fact:
                            dir_fact = os.path.dirname(fact)
                            nuevo_path_fact = os.path.join(dir_fact, nuevo_nombre_fact)
                            if os.path.basename(fact) != nuevo_nombre_fact:
                                if self._safe_move_or_write_json(fact, nuevo_path_fact):
                                    renombrados['fact'] += 1
                                    print(f"  - Renombrada factura: {os.path.basename(fact)} -> {nuevo_nombre_fact}")
                                else:
                                    errores.append(f"Error renombrando factura: {fact}")
                            else:
                                print(f"  - Factura ya tiene nombre correcto: {nuevo_nombre_fact}")
                                renombrados['fact'] += 1

                    # Renombrar XML asociado si se encontró
                    if xml_asociado and cfg.get('formato_xml'):
                        nuevo_nombre_xml = apply_format(cfg.get('formato_xml'), contexto)
                        if nuevo_nombre_xml:
                            dir_xml = os.path.dirname(xml_asociado)
                            nuevo_path_xml = os.path.join(dir_xml, nuevo_nombre_xml)
                            if os.path.basename(xml_asociado) != nuevo_nombre_xml:
                                if self._safe_move_or_write_json(xml_asociado, nuevo_path_xml):
                                    renombrados['xml'] += 1
                                    print(f"  - Renombrado XML: {os.path.basename(xml_asociado)} -> {nuevo_nombre_xml}")
                                else:
                                    errores.append(f"Error renombrando XML: {xml_asociado}")
                            else:
                                print(f"  - XML ya tiene nombre correcto: {nuevo_nombre_xml}")
                                renombrados['xml'] += 1

                    # Renombrar PDF asociado si se encontró
                    if pdf_asociado and cfg.get('formato_pdf'):
                        nuevo_nombre_pdf = apply_format(cfg.get('formato_pdf'), contexto)
                        if nuevo_nombre_pdf:
                            dir_pdf = os.path.dirname(pdf_asociado)
                            nuevo_path_pdf = os.path.join(dir_pdf, nuevo_nombre_pdf)
                            if os.path.basename(pdf_asociado) != nuevo_nombre_pdf:
                                if self._safe_move_or_write_json(pdf_asociado, nuevo_path_pdf):
                                    renombrados['pdf'] += 1
                                    print(f"  - Renombrado PDF: {os.path.basename(pdf_asociado)} -> {nuevo_nombre_pdf}")
                                else:
                                    errores.append(f"Error renombrando PDF: {pdf_asociado}")
                            else:
                                print(f"  - PDF ya tiene nombre correcto: {nuevo_nombre_pdf}")
                                renombrados['pdf'] += 1

        # fin procesamiento
        self.progress_updated.emit(100)
        QApplication.processEvents()

        # escribir log
        try:
            with open(archivo_log, 'w', encoding='utf-8') as f:
                f.write(f"Registro de Procesamiento CUV - {datetime.datetime.now()}\n")
                f.write("=" * 50 + "\n")
                f.write(f"Carpetas procesadas: {len(carpetas_procesadas)}\n")
                f.write(f"Archivos CUV renombrados: {renombrados['cuv']}\n")
                f.write(f"Facturas JSON renombradas: {renombrados['fact']}\n")
                f.write(f"Archivos XML renombrados: {renombrados['xml']}\n")
                f.write(f"Archivos PDF renombrados: {renombrados['pdf']}\n")
                f.write(f"Archivos CUV modificados: {modificados_cuv}\n")
                f.write(f"Errores: {len(errores)}\n")
                if errores:
                    f.write("\n--- Errores ---\n")
                    for e in errores:
                        f.write(f"{e}\n")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el log: {e}")

        # resumen
        msg = QMessageBox(self)
        msg.setWindowTitle("Procesamiento Completado")
        msg.setTextFormat(Qt.RichText)
        msg.setText(
            f"<h3>✅ Procesamiento Finalizado</h3>"
            f"<b>Carpetas procesadas:</b> {len(carpetas_procesadas)}<br/>"
            f"<b>Archivos CUV renombrados:</b> {renombrados['cuv']}<br/>"
            f"<b>Facturas JSON renombradas:</b> {renombrados['fact']}<br/>"
            f"<b>Archivos XML renombrados:</b> {renombrados['xml']}<br/>"
            f"<b>Archivos PDF renombrados:</b> {renombrados['pdf']}<br/>"
            f"<b>Archivos CUV modificados:</b> {modificados_cuv}<br/>"
            f"<b>Errores:</b> {len(errores)}<br/>"
            f"<br/><b>Registro guardado en:</b><br/><code>{archivo_log}</code>"
        )
        msg.exec_()

        # reset UI
        self.btn_procesar.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def buscar_archivos_cuv_mejorado(self, carpeta):
        """Busca archivos CUV de manera más efectiva"""
        archivos_cuv = []
        for raiz, _, archivos in os.walk(carpeta):
            for archivo in archivos:
                nombre_lower = archivo.lower()
                # Buscar archivos que contengan 'cuv' y terminen en .json
                if 'cuv' in nombre_lower and nombre_lower.endswith('.json'):
                    archivos_cuv.append(os.path.join(raiz, archivo))
        return sorted(archivos_cuv)

    def extraer_num_factura_de_nombre(self, nombre_archivo):
        """Extrae el número de factura del nombre del archivo CUV"""
        try:
            # Patrones comunes en nombres de archivos CUV
            import re
            patrones = [
                r'(\d+)_cuv',           # 12345_cuv.json
                r'cuv_(\d+)',           # cuv_12345.json  
                r'(\d+)-cuv',           # 12345-cuv.json
                r'cuv-(\d+)',           # cuv-12345.json
                r'(\d+)\.',             # 12345.cuv.json
            ]
            
            for patron in patrones:
                match = re.search(patron, nombre_archivo.lower())
                if match:
                    return match.group(1)
            
            # Si no coincide con patrones, buscar cualquier número en el nombre
            numeros = re.findall(r'\d+', nombre_archivo)
            if numeros:
                # Devolver el número más largo (probablemente el de factura)
                return max(numeros, key=len)
                
            return None
        except Exception:
            return None
    def es_archivo_ya_procesado(self, archivo, contexto, fmt_cuv, fmt_fact, fmt_xml, fmt_pdf):
        """Verifica si un archivo ya tiene el nombre esperado (ya fue procesado)"""
        nombre_archivo = os.path.basename(archivo)
        
        # Generar los nombres esperados
        nombres_esperados = []
        if archivo.endswith('_cuv.json') or 'CUV' in archivo.upper():
            if fmt_cuv:
                nombre_esperado = apply_format(fmt_cuv, contexto)
                if nombre_esperado:
                    nombres_esperados.append(nombre_esperado.lower())
        elif archivo.endswith('.json') and not archivo.endswith('_cuv.json'):
            if fmt_fact:
                nombre_esperado = apply_format(fmt_fact, contexto)
                if nombre_esperado:
                    nombres_esperados.append(nombre_esperado.lower())
        elif archivo.endswith('.xml'):
            if fmt_xml:
                nombre_esperado = apply_format(fmt_xml, contexto)
                if nombre_esperado:
                    nombres_esperados.append(nombre_esperado.lower())
        elif archivo.endswith('.pdf'):
            if fmt_pdf:
                nombre_esperado = apply_format(fmt_pdf, contexto)
                if nombre_esperado:
                    nombres_esperados.append(nombre_esperado.lower())
        
        # Verificar si el archivo actual ya tiene uno de los nombres esperados
        return nombre_archivo.lower() in nombres_esperados

    def _safe_move_or_write_json(self, src_path, dest_path, json_obj=None):
        """Mover/renombrar archivo o escribir JSON de forma segura"""
        try:
            # Si el destino existe y es diferente al origen, eliminarlo
            if os.path.exists(dest_path) and os.path.abspath(src_path) != os.path.abspath(dest_path):
                try:
                    os.remove(dest_path)
                except Exception as e:
                    print(f"Error eliminando archivo destino existente: {e}")
                    return False
            
            if json_obj is not None:
                # escribir JSON
                with open(dest_path, 'w', encoding='utf-8') as fw:
                    json.dump(json_obj, fw, ensure_ascii=False, indent=2)
                
                # Eliminar original si es diferente al destino
                if (os.path.exists(src_path) and 
                    os.path.abspath(src_path) != os.path.abspath(dest_path) and
                    src_path != dest_path):
                    try:
                        os.remove(src_path)
                    except Exception as e:
                        print(f"Error eliminando archivo original: {e}")
            else:
                # mover/renombrar archivo
                if os.path.abspath(src_path) != os.path.abspath(dest_path):
                    try:
                        os.rename(src_path, dest_path)
                    except Exception:
                        # si rename falla (cross-device), hacer copy+remove
                        try:
                            with open(src_path, 'rb') as fr, open(dest_path, 'wb') as fw:
                                fw.write(fr.read())
                            if os.path.exists(src_path) and os.path.abspath(src_path) != os.path.abspath(dest_path):
                                os.remove(src_path)
                        except Exception as e:
                            print(f"Error en copia de archivo: {e}")
                            return False
            return True
        except Exception as e:
            print(f"Error en _safe_move_or_write_json: {e}")
            return False

    def modificar_archivo_cuv(self, archivo_cuv):
        """Modifica el archivo CUV según las opciones seleccionadas"""
        try:
            # Leer archivo CUV
            with open(archivo_cuv, 'r', encoding='utf-8') as f:
                datos_cuv = json.load(f)
            
            modificado = False
            
            if self.radio_eliminar_rechazados.isChecked():
                # Buscar elementos RECHAZADOS y el CUV
                cuv_encontrado = None
                validaciones_filtradas = []
                
                for r in datos_cuv.get('ResultadosValidacion', []):
                    if r.get('Clase') == 'RECHAZADO':
                        # Si es rechazado, buscar el CUV si es RVG02
                        if r.get('Codigo') == 'RVG02':
                            desc = r.get('Observaciones', '')
                            try:
                                cuv_start = desc.index("Ministerio de Salud; CUV ") + len("Ministerio de Salud; CUV ")
                                cuv_end = desc.index(" del Documento")
                                cuv_encontrado = desc[cuv_start:cuv_end].strip()
                            except ValueError:
                                pass
                    else:
                        # Mantener solo los no rechazados
                        validaciones_filtradas.append(r)
                
                # Actualizar validaciones sin los rechazados
                datos_cuv['ResultadosValidacion'] = validaciones_filtradas
                
                # Si encontramos CUV, actualizar estado
                if cuv_encontrado:
                    datos_cuv['CodigoUnicoValidacion'] = cuv_encontrado
                    datos_cuv['ResultState'] = True
                
                modificado = True
                
            elif self.radio_eliminar_todo.isChecked():
                # Vaciar array de validaciones y actualizar estado
                datos_cuv['ResultadosValidacion'] = []
                datos_cuv['ResultState'] = True
                modificado = True
            
            # Si hubo modificaciones, guardar archivo
            if modificado:
                with open(archivo_cuv, 'w', encoding='utf-8') as f:
                    json.dump(datos_cuv, f, indent=4, ensure_ascii=False)
                return True
                
            return False
            
        except Exception as e:
            print(f"Error procesando archivo CUV {archivo_cuv}: {e}")
            return False

def leer_version():
    """Lee la versión desde version.txt si existe"""
    try:
        if os.path.exists('version.txt'):
            with open('version.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('FileVersion='):
                        return line.split('=')[1].strip()
    except Exception:
        pass
    return "1.0.0.0"  # versión por defecto si no se puede leer el archivo

# -------------------------
# Ventana principal
# -------------------------
class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SERAF")
        self.setMinimumSize(700, 900)  # Reducido de 950 a 900
        self.setWindowIcon(QIcon.fromTheme("document-edit"))
        self.config_widget = None  # Referencia única a la pestaña de configuración
        self.init_ui()
        self.verificar_licencia()

    def init_ui(self):
        # barra menú
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar {
                min-height: 15px;
                font-size: 9pt;
            }
            QMenuBar::item {
                padding: 2px 6px;
            }
        """)
        menu_archivo = menu_bar.addMenu("📁 Archivo")
        act_salir = QAction("🚪 Salir", self)
        act_salir.setShortcut("Ctrl+Q")
        act_salir.triggered.connect(self.close)
        menu_archivo.addAction(act_salir)

        menu_herramientas = menu_bar.addMenu("🛠️ Herramientas")
        act_config = QAction("⚙️ Configuración", self)
        act_config.triggered.connect(self.mostrar_config)
        menu_herramientas.addAction(act_config)

        menu_ayuda = menu_bar.addMenu("❓ Ayuda")
        act_acerca = QAction("ℹ️ Acerca de", self)
        act_acerca.triggered.connect(self.mostrar_acerca)
        menu_ayuda.addAction(act_acerca)

        # Nuevo: estado de licencia
        act_licencia = QAction("📜 Estado Licencia", self)
        act_licencia.triggered.connect(self.mostrar_estado_licencia)
        menu_ayuda.addAction(act_licencia)
        
        # Nuevo: contacto
        act_contacto = QAction("📬 Contacto", self)
        act_contacto.triggered.connect(self.mostrar_contacto)
        menu_ayuda.addAction(act_contacto)

        # widget central con pestañas
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(False)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ccc; top:-1px; background: #f9f9f9; }
            QTabBar::tab { background: #e6e6e6; padding: 4px 8px; margin-right: 2px; border: 1px solid #ccc; border-bottom: none; border-radius: 4px 4px 0 0; }
            QTabBar::tab:selected { background: #fff; border-bottom: 1px solid white; }
            QTabBar::tab:hover { background: #f0f0f0; }
        """)
        self.renombrador = RenombradorCUVWidget()
        self.tabs.addTab(self.renombrador, "🔄 SERAF")
        self.setCentralWidget(self.tabs)

        # barra estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")

    def verificar_licencia(self):
        """Verifica licencia y muestra contacto si hay problemas"""
        try:
            lic_ok, msg = verificar_licencia_global()
            if not lic_ok:
                QMessageBox.critical(self, "Error de Licencia", 
                    f"Licencia inválida: {msg}\n\n"
                    "Se mostrará la información de contacto para obtener una licencia válida.")
                # Crear ventana temporal solo para mostrar el contacto
                temp = VentanaPrincipal()
                temp.mostrar_contacto()
                self.close()
            else:
                self.status_bar.showMessage(f"Licencia válida: {msg}")
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                f"Error verificando licencia: {e}\n\n"
                "Se mostrará la información de contacto para obtener soporte.")
            # Crear ventana temporal solo para mostrar el contacto
            temp = VentanaPrincipal()
            temp.mostrar_contacto()
            self.close()

    def mostrar_config(self):
        """Muestra la pestaña de configuración, evitando duplicados"""
        if self.config_widget is None:
            self.config_widget = ConfiguracionWidget()
            idx = self.tabs.addTab(self.config_widget, "⚙️ Configuración")
        else:
            # Si ya existe, buscar su índice y activarlo
            for i in range(self.tabs.count()):
                if self.tabs.widget(i) == self.config_widget:
                    idx = i
                    break
            else:
                # Si no se encuentra, agregarlo nuevamente
                idx = self.tabs.addTab(self.config_widget, "⚙️ Configuración")
        
        self.tabs.setCurrentIndex(idx)

    def mostrar_acerca(self):
        """Muestra información 'Acerca de' incluyendo la versión"""
        version = leer_version()
        QMessageBox.about(self, "Acerca de",
            f"<h3>SERAF - Sistema de Renombrado de Archivos de Facturación</h3>"
            f"<p>Versión {version}</p>"
            "<p>Herramienta para renombrar archivos CUV, facturas PDF, XML y JSON RIPS, "
            "con opciones de filtrado y configuración de formatos.</p>"
            "<p><b>Nueva característica:</b> Selector visual de variables para facilitar la configuración.</p>")

    def mostrar_estado_licencia(self):
        """Muestra el estado de la licencia y contacto si hay problemas"""
        try:
            lic_ok, msg = verificar_licencia_global()
            if lic_ok:
                QMessageBox.information(self, "Estado de Licencia", f"✅ Licencia válida\n\n{msg}")
            else:
                QMessageBox.warning(self, "Estado de Licencia", 
                    f"❌ Licencia no válida\n\n{msg}\n\n"
                    "Se mostrará la información de contacto para obtener una licencia válida.")
                self.mostrar_contacto()
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                f"Error verificando licencia: {e}\n\n"
                "Se mostrará la información de contacto para obtener soporte.")
            self.mostrar_contacto()

    def mostrar_contacto(self):
        """Muestra la información de contacto del soporte con link funcional"""
        contacto = (
            "Contacto Soporte SERAF<br><br>"
            "Email: lozanoliceth60@gmail.com<br>"
            "Email: ripsjson2275@gmail.com<br>"
            "Web: <a href='https://www.rips2275.com'>www.rips2275.com</a><br>"
        )
        msg = QMessageBox(self)
        msg.setWindowTitle("Contacto")
        msg.setTextFormat(Qt.TextFormat.RichText)  # ¡Importante!
        msg.setText(contacto)
        msg.exec()

    def closeEvent(self, event):
        """Cerrar conexión a BD al salir"""
        from database_manager import DatabaseManager
        db = DatabaseManager()
        db.close_connection()
        event.accept()

# -------------------------
# Punto de entrada
# -------------------------
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont("Segoe UI", 10))

    # Verificar licencia una sola vez antes de todo
    try:
        lic_ok, msg = verificar_licencia_global()
        if not lic_ok:
            # Mostrar mensaje y contacto en una sola ventana
            mensaje = (
                f"Licencia inválida: {msg}\n\n"
                "Para obtener una licencia válida, contacte a:\n\n"
                "Email: lozanoliceth60@gmail.com\n"
                "Email: ripsjson2275@gmail.com\n"
                "Web: www.rips2275.com"
            )
            QMessageBox.critical(None, "Error de Licencia", mensaje)
            sys.exit(1)
    except Exception as e:
        # Mostrar error y contacto en una sola ventana
        mensaje = (
            f"Error verificando licencia: {e}\n\n"
            "Para obtener soporte, contacte a:\n\n"
            "Email: lozanoliceth60@gmail.com\n"
            "Email: ripsjson2275@gmail.com\n"
            "Web: www.rips2275.com"
        )
        QMessageBox.critical(None, "Error", mensaje)
        sys.exit(1)

    # Verificar conexión a BD con firebirdsql - NUEVA IMPLEMENTACIÓN
    try:
        print("🔍 Iniciando verificación de conexión a BD...")
        
        # Test de conexión simple usando DatabaseManager
        from database_manager import DatabaseManager
        db = DatabaseManager()
        conn = db.get_connection()
        
        # Test de consulta simple para verificar que funciona
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM RDB$DATABASE")
        resultado = cur.fetchone()
        cur.close()
        
        print(f"✅ Conexión a BD verificada correctamente. Resultado test: {resultado}")
        
        # Verificar también que config_manager funciona
        from config_manager import list_configs
        configs = list_configs()
        print(f"✅ Config Manager funciona. Configuraciones encontradas: {len(configs)}")
        
        _CONFIG_MANAGER_OK = True
        _CONFIG_MANAGER_ERROR_MSG = ""
        
    except Exception as e:
        _CONFIG_MANAGER_OK = False
        _CONFIG_MANAGER_ERROR_MSG = str(e)
        print(f"❌ Error de conexión a BD: {_CONFIG_MANAGER_ERROR_MSG}")
        
        # Extraer información específica del error de Firebird
        error_message = str(e)
        full_error_lower = error_message.lower()
        
        print(f"DEBUG - Error completo: {error_message}")
        
        # 1. ERRORES DE HOST/CONEXIÓN (PRIMERO)
        conexion_patterns = [
            '335544721',  # Código específico Firebird para errores de red
            'unable to complete network request',
            'no se puede completar la solicitud de red',
            'failed to establish a connection', 
            'no se pudo establecer la conexión',
            'network request',
            'solicitud de red',
            'connection refused',
            'conexión rechazada',
            'timeout',
            'timed out',
            'no route to host',
            'host unreachable',
            'cannot connect to database'
        ]
        
        is_conexion_error = any(pattern in full_error_lower for pattern in conexion_patterns)
        
        if is_conexion_error:
            # Extraer dirección IP/hostname del error
            problematic_host = None
            import re
            
            host_patterns = [
                r'host "([^"]+)"',
                r'to host ([^\s.,]+)', 
                r'host ([^\s.,]+)',
                r'request to ([^\s]+)',
                r'connecting to ([^\s]+)',
                r"database '([^']+)'",
            ]
            
            for pattern in host_patterns:
                matches = re.findall(pattern, error_message, re.IGNORECASE)
                if matches:
                    problematic_host = matches[0]
                    # Filtrar hosts inválidos
                    if problematic_host and problematic_host not in ['database:', 'database', 'n-']:
                        break
                    else:
                        problematic_host = None
            
            # Buscar IPs si no encontramos hostname
            if not problematic_host:
                ip_matches = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', error_message)
                if ip_matches:
                    problematic_host = ip_matches[0]
            
            titulo = "Error de Conexión al Servidor"
            
            if problematic_host:
                mensaje = (
                    f"No se puede conectar al servidor de base de datos\n\n"
                    f"El servidor '{problematic_host}' no está accesible:\n\n"
                    "Posibles causas:\n"
                    f"• La dirección {problematic_host} es incorrecta\n"
                    "• El servidor Firebird no está ejecutándose\n" 
                    "• El puerto 3050 está bloqueado por firewall\n"
                    "• Problemas de red entre este equipo y el servidor\n\n"
                    "Sugerencias:\n"
                    f"• Verifique la dirección '{problematic_host}' en database.ini\n"
                    "• Confirme que el servidor Firebird esté en ejecución\n"
                    f"• Pruebe hacer ping a {problematic_host}\n"
                    "• Verifique la configuración de firewall\n"
                    "• Contacte al administrador de red\n\n"
                )
            else:
                mensaje = (
                    "No se puede conectar al servidor de base de datos\n\n"
                    "Problema de conectividad de red:\n\n"
                    "Sugerencias:\n"
                    "• Verifique la configuración en database.ini\n"
                    "• Confirme que el servidor Firebird esté en ejecución\n"
                    "• Verifique la configuración de firewall\n"
                    "• Contacte al administrador de red\n\n"
                )
        
        # 2. ERRORES DE ARCHIVO/BD NO ENCONTRADA (SEGUNDO)
        elif any(phrase in full_error_lower for phrase in [
            '335544344', '335544345',  # Códigos Firebird para archivo no encontrado
            'file not found',
            'archivo no encontrado',
            'no such file',
            'no existe el archivo',
            'database file not found',
            'archivo de base de datos no encontrado',
            'unavailable database'
        ]):
            titulo = "Base de Datos No Encontrada"
            mensaje = (
                "Archivo de base de datos no disponible\n\n"
                "No se puede localizar o acceder al archivo de base de datos.\n\n"
                "Sugerencias:\n"
                "• Verifique la ruta de la base de datos en database.ini\n"
                "• Confirme que el archivo .FDB existe en esa ubicación\n"
                "• Verifique los permisos de acceso al archivo\n"
                "• Contacte al administrador del sistema\n\n"
            )
        
        # 3. ERRORES DE CREDENCIALES (TERCERO)
        elif any(phrase in full_error_lower for phrase in [
            '335544472',  # Código específico de Firebird para credenciales
            'your user name and password are not defined',
            'usuario y contraseña no están definidos', 
            'wrong username or password',
            'usuario o contraseña incorrectos',
            'login incorrecto',
            'not defined',
            'no están definidos',
            'missing password',
            'password not set'
        ]):
            
            titulo = "Error de Autenticación"
            mensaje = (
                "Credenciales incorrectas\n\n"
                "El usuario o contraseña proporcionados no son válidos.\n\n"
                "Sugerencias:\n"
                "• Verifique el usuario y contraseña en database.ini\n"
                "• Asegúrese de que las mayúsculas/minúsculas sean correctas\n"
                "• Contacte al administrador de la base de datos\n"
                "• El administrador debe crear el usuario en Firebird\n\n"
            )
        
        # 4. ERRORES DE CHARSET/PARÁMETROS
        elif any(phrase in full_error_lower for phrase in [
            'unsupported on-disk structure',
            'estructura de disco no soportada',
            'character set',
            'charset',
            'codepage'
        ]):
            titulo = "Error de Configuración"
            mensaje = (
                "Problema de configuración de caracteres\n\n"
                "Hay un problema con la configuración del charset/codificación.\n\n"
                "Sugerencias:\n"
                "• Verifique el parámetro 'charset' en database.ini\n"
                "• Use 'WIN1252' para bases de datos latinas\n"
                "• Use 'UTF8' para bases de datos Unicode\n"
                "• Contacte al administrador de la base de datos\n\n"
            )
        
        # 5. OTROS ERRORES DE FIREBIRD
        elif '335544' in error_message:
            titulo = "Error de Base de Datos Firebird"
            # Extraer código de error Firebird
            codigo_match = re.search(r'335544\d+', error_message)
            codigo = codigo_match.group(0) if codigo_match else "Desconocido"
            
            mensaje = (
                "Error específico de Firebird\n\n"
                f"Código de error: {codigo}\n"
                f"Detalle: {error_message}\n\n"
                "Contacte al administrador de la base de datos\n\n"
            )
        
        # 6. ERROR GENÉRICO
        else:
            titulo = "Error de Base de Datos"
            mensaje = f"Error al conectar con la base de datos:\n\n{error_message}\n\n"
        
        # Mensaje final
        mensaje_final = (
            f"{mensaje}"
            "Para soporte técnico:\n\n"
            "Email: lozanoliceth60@gmail.com\n"
            "Email: ripsjson2275@gmail.com\n"
            "Web: www.rips2275.com"
        )
        
        QMessageBox.critical(None, titulo, mensaje_final)
        sys.exit(1)

    # Si llegamos aquí, la conexión es exitosa - Crear ventana principal
    try:
        ventana = VentanaPrincipal()
        ventana.show()
        
        # Cargar configuraciones en el combobox del renombrador
        ventana.renombrador.reload_configs_into_combo()
        
        print("🚀 Aplicación iniciada correctamente")
        
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Error iniciando aplicación: {e}")
        QMessageBox.critical(None, "Error Inesperado", 
                           f"Error al iniciar la aplicación:\n\n{str(e)}\n\n"
                           "Por favor, contacte al soporte técnico.")
        sys.exit(1)

if __name__ == "__main__":
    main()

#pyinstaller --onefile --icon=icono.ico --name="SERAF" --noconsole --version-file=version.txt cuv.py
# SERAF SERAF - Sistema de Renombrado de Archivos de Facturación
