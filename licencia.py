# licencia.py
import datetime
import hashlib
import json
import os
import platform
import subprocess
import re

# =====================================================
# CONFIGURACIÓN DE SEGURIDAD (NO CAMBIAR)
# =====================================================
SECRET_KEY = "S3R4F-2026-LICENCIA-ULTRA-PRIVATE"

# =====================================================
# OBTENER UUID DEL EQUIPO
# =====================================================
def get_machine_uuid():
    """
    Obtiene un UUID estable del equipo.
    Si no se puede obtener → retorna None (licencia inválida).
    """

    # Permitir override SOLO para pruebas controladas
    env_uuid = os.environ.get("LICENSE_UUID")
    if env_uuid:
        return env_uuid.strip().upper()

    sistema = platform.system()

    try:
        if sistema == "Windows":
            ps_paths = [
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
            ]

            powershell = next((p for p in ps_paths if os.path.exists(p)), None)
            if not powershell:
                return None

            cmd = [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystemProduct).UUID"
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10, shell=False
            )

            uuid = result.stdout.strip().upper()
            return uuid if uuid else None

        elif sistema == "Linux":
            path = "/sys/class/dmi/id/product_uuid"
            if os.path.exists(path):
                with open(path, "r") as f:
                    return f.read().strip().upper()

        elif sistema == "Darwin":  # macOS
            cmd = ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "IOPlatformUUID" in line:
                    return line.split('"')[-2].upper()

    except Exception:
        return None

    return None


# =====================================================
# CONTROL DE LICENCIA
# =====================================================
class ControlLicencia:

    def __init__(self, nombre_aplicativo: str):
        self.nombre_aplicativo = nombre_aplicativo.upper()
        self.archivo_licencia = f"licencia_{self.nombre_aplicativo.lower()}.key"

    # -----------------------------
    # Normalizar UUID
    # -----------------------------
    def _normalizar_uuid(self, uuid: str) -> str | None:
        if not uuid:
            return None
        uuid = uuid.strip().upper()
        return re.sub(r"[^A-F0-9\-]", "", uuid)

    # -----------------------------
    # Firmar datos COMPLETOS
    # -----------------------------
    def _firmar_datos(self, datos: dict) -> str:
        copia = datos.copy()
        copia.pop("hash_verificacion", None)

        payload = json.dumps(copia, sort_keys=True, separators=(",", ":"))
        texto = payload + SECRET_KEY

        return hashlib.sha256(texto.encode("utf-8")).hexdigest()

    # =================================================
    # GENERAR LICENCIA
    # =================================================
    def generar_licencia(self, dias_validez: int, uuid_equipo: str | None = None):
        fecha_inicio = datetime.datetime.now()
        fecha_fin = fecha_inicio + datetime.timedelta(days=dias_validez)

        uuid = self._normalizar_uuid(uuid_equipo) if uuid_equipo else self._normalizar_uuid(get_machine_uuid())
        if not uuid:
            raise RuntimeError("No se pudo obtener UUID del equipo")

        datos = {
            "aplicativo": self.nombre_aplicativo,
            "uuid_equipo": uuid,
            "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
            "fecha_fin": fecha_fin.strftime("%Y-%m-%d"),
        }

        datos["hash_verificacion"] = self._firmar_datos(datos)

        with open(self.archivo_licencia, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4)

        return f"Licencia generada hasta {fecha_fin.strftime('%d/%m/%Y')}"

    # =================================================
    # VERIFICAR LICENCIA
    # =================================================
    def verificar_licencia(self):
        if not os.path.exists(self.archivo_licencia):
            return False, "❌ Archivo de licencia no encontrado"

        try:
            with open(self.archivo_licencia, "r", encoding="utf-8") as f:
                datos = json.load(f)

            if datos.get("aplicativo") != self.nombre_aplicativo:
                return False, "❌ Licencia no corresponde a este aplicativo"

            uuid_sistema = self._normalizar_uuid(get_machine_uuid())
            if not uuid_sistema:
                return False, "❌ No se pudo validar el equipo"

            if datos.get("uuid_equipo") != uuid_sistema:
                return False, "❌ Licencia no corresponde a este equipo"

            # Verificar integridad
            if datos.get("hash_verificacion") != self._firmar_datos(datos):
                return False, "❌ Licencia modificada o falsificada"

            fecha_inicio = datetime.datetime.strptime(datos["fecha_inicio"], "%Y-%m-%d")
            fecha_fin = datetime.datetime.strptime(datos["fecha_fin"], "%Y-%m-%d")
            ahora = datetime.datetime.now()

            if ahora < fecha_inicio:
                return False, f"❌ Licencia inicia el {fecha_inicio:%d/%m/%Y}"

            if ahora > fecha_fin:
                return False, f"❌ Licencia vencida el {fecha_fin:%d/%m/%Y}"

            dias_restantes = (fecha_fin - ahora).days
            return True, f"✅ Licencia válida ({dias_restantes} días restantes)"

        except Exception as e:
            return False, f"❌ Error en licencia: {str(e)}"


# =====================================================
# FUNCIÓN GLOBAL
# =====================================================
def verificar_licencia_global(nombre_aplicativo="SERAF"):
    return ControlLicencia(nombre_aplicativo).verificar_licencia()


# =====================================================
# DIAGNÓSTICO LOCAL
# =====================================================
if __name__ == "__main__":
    print("=== DIAGNÓSTICO DE LICENCIA ===")
    control = ControlLicencia("SERAF")
    ok, msg = control.verificar_licencia()
    print(msg)
