# generar_licencia.py
from licencia import ControlLicencia, get_machine_uuid
import argparse

def main():
    parser = argparse.ArgumentParser(description="Generar archivo de licencia (.key)")
    parser.add_argument("nombre_aplicativo", help="Nombre del aplicativo (ej: ValidadorRips)")
    parser.add_argument("dias", nargs="?", type=int, default=90,
                        help="Días de validez (default: 90)")
    parser.add_argument("-u", "--uuid", dest="uuid", help="UUID del equipo (opcional). Si se pasa, la licencia se generará atada a este UUID.")
    parser.add_argument("--auto-uuid", action="store_true",
                        help="Intentar detectar el UUID del equipo automáticamente (usa WMIC o PowerShell en Windows).")
    parser.add_argument("--show-commands", action="store_true",
                        help="Mostrar comandos útiles para obtener el UUID en CMD / PowerShell.")
    args = parser.parse_args()

    if args.show_commands:
        print("Comandos útiles para obtener UUID del equipo:")
        print("\nCMD (legacy WMIC):")
        print("  wmic csproduct get uuid")
        print("\nPowerShell (recomendado en Windows modernos):")
        print("  powershell -NoProfile -Command \"(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID\"")
        print("  # o fallback:")
        print("  powershell -NoProfile -Command \"Get-WmiObject -Class Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID\"")
        print("\nLinux:")
        print("  cat /sys/class/dmi/id/product_uuid")
        print("\nmacOS:")
        print("  ioreg -rd1 -c IOPlatformExpertDevice | awk '/IOPlatformUUID/ { print $3; }' | tr -d '\"'")
        # si solo quería ver comandos, salir
        if not args.auto_uuid and not args.uuid:
            return

    # si se solicita auto-uuid, intentar obtenerlo
    if args.auto_uuid and not args.uuid:
        uuid_auto = get_machine_uuid()
        if uuid_auto:
            print(f"UUID detectado automáticamente: {uuid_auto}")
            args.uuid = uuid_auto
        else:
            print("No se pudo detectar el UUID automáticamente. Usa --show-commands o pase --uuid manualmente.")
            # continuar para permitir que usuario pase --uuid manualmente
    control = ControlLicencia(args.nombre_aplicativo)
    resultado = control.generar_licencia(dias_validez=args.dias, uuid_equipo=args.uuid)
    print(resultado)

    valido, mensaje = control.verificar_licencia()
    print(f"\nEstado: {mensaje}")

if __name__ == "__main__":
    main()
