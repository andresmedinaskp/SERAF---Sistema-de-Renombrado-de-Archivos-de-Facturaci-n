# licencia.py
import datetime
import hashlib
import json
import os
import platform
import subprocess

def get_machine_uuid():
    """Intenta obtener un identificador estable del equipo (UUID).
    Orden de comprobación:
      1) Variable de entorno LICENSE_UUID o MACHINE_UUID
      2) Windows: WMIC
      3) Windows: PowerShell (Get-CimInstance o Get-WmiObject)
      4) Linux: /sys/class/dmi/id/product_uuid
      5) macOS: ioreg
    Devuelve cadena o None.
    """
    # 1) permitir override vía variable de entorno (útil para pruebas y shells)
    env_uuid = os.environ.get('LICENSE_UUID') or os.environ.get('MACHINE_UUID')
    if env_uuid:
        return env_uuid.strip()

    sistema = platform.system()

    try:
        if sistema == "Windows":
            # 2) Intentar WMIC
            try:
                result = subprocess.run(["wmic", "csproduct", "get", "uuid"], capture_output=True, text=True, shell=False)
                out = result.stdout.strip().splitlines()
                # buscar la línea que no sea "UUID"
                for line in out:
                    line = line.strip()
                    if line and line.upper() != "UUID":
                        return line
            except Exception:
                pass

            # 3) Intentar PowerShell (Get-CimInstance), luego Get-WmiObject como fallback
            try:
                # Get-CimInstance (más moderno)
                cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                       '-Command', '(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID']
                result = subprocess.run(cmd, capture_output=True, text=True)
                out = result.stdout.strip()
                if out:
                    # puede venir con líneas, tomar última no vacía
                    for line in out.splitlines()[::-1]:
                        if line.strip():
                            return line.strip()
            except Exception:
                pass

            try:
                # Fallback a Get-WmiObject (antiguo)
                cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                       '-Command', 'Get-WmiObject -Class Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID']
                result = subprocess.run(cmd, capture_output=True, text=True)
                out = result.stdout.strip()
                if out:
                    return out.splitlines()[-1].strip()
            except Exception:
                pass

            return None

        elif sistema == "Linux":
            path = "/sys/class/dmi/id/product_uuid"
            try:
                with open(path, "r") as f:
                    return f.read().strip()
            except Exception:
                return None

        elif sistema == "Darwin":  # macOS
            try:
                result = subprocess.run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    if "IOPlatformUUID" in line:
                        parts = line.split('"')
                        if len(parts) >= 4:
                            return parts[-2]
            except Exception:
                return None
        else:
            return None

    except Exception:
        return None


class ControlLicencia:
    def __init__(self, nombre_aplicativo):
        self.nombre_aplicativo = nombre_aplicativo
        self.archivo_licencia = f"licencia_{nombre_aplicativo.lower()}.key"

    def generar_licencia(self, dias_validez=90, uuid_equipo=None):
        """
        GENERA un nuevo archivo de licencia.
        Si se pasa uuid_equipo se ata a ese UUID; si no, intenta obtener el UUID local.
        """
        fecha_fin = datetime.datetime.now() + datetime.timedelta(days=dias_validez)
        uuid_equipo = uuid_equipo or get_machine_uuid() or "UUID_DESCONOCIDO"

        datos_licencia = {
            'aplicativo': self.nombre_aplicativo,
            'uuid_equipo': uuid_equipo,
            'fecha_inicio': datetime.datetime.now().strftime('%Y-%m-%d'),
            'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
            'hash_verificacion': self._generar_hash(fecha_fin, uuid_equipo)
        }

        with open(self.archivo_licencia, 'w') as f:
            json.dump(datos_licencia, f, indent=4)

        return f"Licencia para '{self.nombre_aplicativo}' generada hasta: {fecha_fin.strftime('%d/%m/%Y')} (UUID: {uuid_equipo})"

    def _generar_hash(self, fecha_fin, uuid_equipo):
        texto = f"LICENCIA_{self.nombre_aplicativo.upper()}_{fecha_fin.strftime('%Y%m%d')}_{uuid_equipo}"
        return hashlib.sha256(texto.encode()).hexdigest()

    def verificar_licencia(self):
        if not os.path.exists(self.archivo_licencia):
            return False, (f"⚠️ No se encontró archivo de licencia para '{self.nombre_aplicativo}'.\n\n"
                           "¿Necesita ayuda? Contacte al administrador.")
        try:
            with open(self.archivo_licencia, 'r') as f:
                datos = json.load(f)

            if datos.get('aplicativo') != self.nombre_aplicativo:
                return False, f"❌ Licencia no válida para '{self.nombre_aplicativo}'"

            uuid_actual = get_machine_uuid() or "UUID_DESCONOCIDO"
            if datos.get('uuid_equipo') != uuid_actual:
                return False, "❌ Licencia inválida: no corresponde a este equipo"

            fecha_fin = datetime.datetime.strptime(datos['fecha_fin'], '%Y-%m-%d')
            hash_correcto = self._generar_hash(fecha_fin, datos.get('uuid_equipo'))

            if datos.get('hash_verificacion') != hash_correcto:
                return False, "❌ Licencia alterada. Contacte al proveedor."

            fecha_inicio = datetime.datetime.strptime(datos['fecha_inicio'], '%Y-%m-%d')
            return self._verificar_fechas(fecha_inicio, fecha_fin)

        except Exception as e:
            return False, f"❌ Error leyendo licencia: {str(e)}"

    def _verificar_fechas(self, fecha_inicio, fecha_fin):
        ahora = datetime.datetime.now()
        if ahora < fecha_inicio:
            dias_faltantes = (fecha_inicio - ahora).days
            return False, f"Licencia no activa. Inicia: {fecha_inicio.strftime('%d/%m/%Y')}"
        elif ahora > fecha_fin:
            return False, f"Licencia vencida: {fecha_fin.strftime('%d/%m/%Y')}"
        else:
            dias_restantes = (fecha_fin - ahora).days
            return True, f"Aplicativo: {self.nombre_aplicativo}\nFecha Inicio: {fecha_inicio.strftime('%d/%m/%Y')}\nFecha Fin: {fecha_fin.strftime('%d/%m/%Y')}\nDías Restantes: {dias_restantes}"
    def obtener_dias_restantes(self):
        if not os.path.exists(self.archivo_licencia):
            return 0
        try:
            with open(self.archivo_licencia, 'r') as f:
                datos = json.load(f)
            if datos.get('aplicativo') != self.nombre_aplicativo:
                return 0
            fecha_fin = datetime.datetime.strptime(datos['fecha_fin'], '%Y-%m-%d')
            ahora = datetime.datetime.now()
            if ahora > fecha_fin:
                return 0
            return (fecha_fin - ahora).days
        except:
            return 0

def verificar_licencia_global(nombre_aplicativo="SERAF"):
    control = ControlLicencia(nombre_aplicativo)
    return control.verificar_licencia()
