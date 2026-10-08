# auditoria.py
import argparse
import sys
import json
import os
import traceback
from datetime import datetime, timezone

try:
    from jsonschema import validate
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

# Validación pre-importación de los archivos de módulos
modulos_esperados = [
    "dns_recon.py", "osint.py", "discovery.py", "scanning.py",
    "banner_grabber.py", "smb_enumerator.py", "bruteforce_ftp.py", "bruteforce_web.py"
]
directorio_modulos = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modulos")

for modulo in modulos_esperados:
    if not os.path.isfile(os.path.join(directorio_modulos, modulo)):
        print(f"\n[!] ERROR CRÍTICO: Falta el archivo '{modulo}' en la carpeta 'modulos/'.")
        print("    Recuerda la 'Regla de Oro': Los scripts de los grupos deben mantener sus")
        print("    nombres originales (dns_recon.py, osint.py, discovery.py, scanning.py).")
        print("    Por favor, verifica que no haya sido renombrado o eliminado.\n")
        sys.exit(1)

from modulos import dns_recon   # Grupo 1
from modulos import osint       # Grupo 2
from modulos import discovery   # Grupo 3
from modulos import scanning    # Grupo 4
from modulos import banner_grabber  # Grupo 1 (Fase II)
from modulos import smb_enumerator  # Grupo 2 (Fase II)
from modulos import bruteforce_ftp  # Grupo 3 (Fase II)
from modulos import bruteforce_web  # Grupo 4 (Fase II)

# --- Funciones adaptadoras para instanciar las clases de la Fase II ---
def wrapper_banner_grabbing(target):
    instancia = banner_grabber.BannerGrabber(target)
    return instancia.run()

def wrapper_smb_enumeration(target):
    instancia = smb_enumerator.SMBEnumerator(target)
    return instancia.run()

def wrapper_ftp_bruteforce(target):
    instancia = bruteforce_ftp.FTPBruteForcer(target)
    # Cargar diccionarios básicos de prueba para la integración
    instancia.load_dictionaries(["admin", "root", "anonymous"], ["12345", "admin", "password", ""])
    return instancia.run()

def wrapper_web_bruteforce(target):
    # Definir URL por defecto si el target es solo una IP/dominio
    url = target if target.startswith("http") else f"http://{target}/login.php"
    # Plantilla genérica para pruebas de integración
    instancia = bruteforce_web.WebBruteForcer(url, {"username": "", "password": ""}, "Bienvenido")
    instancia.load_dictionaries(["admin"], ["12345", "password"])
    return instancia.run()

def validar_resultado(resultado):
    """
    Verifica si el diccionario retornado por un modulo cumple con el esquema oficial.
    """
    if resultado is None:
        return False

    if not HAS_JSONSCHEMA:
        print("  [!] Aviso: Libreria 'jsonschema' no encontrada. Omitiendo validacion estricta.")
        print("      Instale con: pip install jsonschema")
        return False

    schema_path = os.path.join(os.path.dirname(__file__), "docs/schema_resultados.json")
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        validate(instance=resultado, schema=schema)
        print(f"  [OK] Validacion de esquema exitosa para: {resultado.get('modulo')} (Estudiante: {resultado.get('estudiante')})")
        return True
    except Exception as e:
        print(f"  [X] ERROR DE CONTRATO en modulo '{resultado.get('modulo', 'Desconocido')}':")
        print(f"      Detalle: {str(e)}")
        return False

def ejecutar_modulo(func, *args, **kwargs):
    """
    Ejecuta una funcion de modulo de forma segura y valida su resultado.
    """
    try:
        resultado = func(*args, **kwargs)
        if resultado:
            if not validar_resultado(resultado):
                raise ValueError("El módulo devolvió un resultado que no cumple el contrato JSON.")
            return resultado
    except NotImplementedError as e:
        print(f"\n[!] Característica en desarrollo: {e}")
    except Exception as e:
        print(f"\n[!] Error inesperado en {func.__name__}: {e}")
        
        # Extraer el traceback completo y construir el registro de error
        tb_str = traceback.format_exc()
        modulo_nombre = func.__module__.split('.')[-1].upper() if hasattr(func, '__module__') else "Desconocido"
        return {
            "modulo": modulo_nombre,
            "grupo": 0,
            "estudiante": "Fallo en ejecución",
            "target": args[0] if args else "Desconocido",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error_message": tb_str,
            "data": {"funcion_fallida": func.__name__}
        }
    return None

def guardar_historial(resultados):
    """
    Guarda la lista de resultados en un archivo JSON para mantener un historial.
    """
    if not resultados:
        return

    archivo_historial = os.path.join(os.path.dirname(os.path.abspath(__file__)), "historial_auditoria.json")
    from history import append_history
    append_history(archivo_historial, resultados)
    print(f"\n[*] Historial guardado exitosamente. Se agregaron {len(resultados)} registro(s) a 'historial_auditoria.json'.")

def main():
    parser = argparse.ArgumentParser(
        description="Suite de Auditoria de Seguridad Informatica - Python",
        epilog="Uso: python auditoria.py target.com --dns-all"
    )
    
    parser.add_argument("target", help="Dominio o IP objetivo")

    # Grupo para Recopilacion de Informacion
    recon_group = parser.add_argument_group('Recopilacion de Informacion')
    recon_group.add_argument("--dns-all", action="store_true", help="Ejecuta todos los checks DNS/WHOIS")
    recon_group.add_argument("--dns-a", action="store_true", help="Registros A/AAAA (G1-E1)")
    recon_group.add_argument("--dns-mxns", action="store_true", help="Registros MX/NS (G1-E2)")
    recon_group.add_argument("--dns-txtsoa", action="store_true", help="Registros TXT/SOA (G1-E3)")
    
    # Grupo OSINT (Grupo 2)
    osint_group = parser.add_argument_group('OSINT y Huella Digital')
    osint_group.add_argument("--whois", action="store_true", help="Consulta WHOIS (G2-E1)")
    osint_group.add_argument("--dorks", action="store_true", help="Búsqueda de subdominios/dorks (G2-E2/E3)")

    # Grupo para Escaneo
    scan_group = parser.add_argument_group('Escaneo de Puertos')
    scan_group.add_argument("--scan", metavar="PUERTOS", help="Escaneo TCP/UDP (Grupo 4)")
    scan_group.add_argument("--ping-sweep", action="store_true", help="Descubrimiento de hosts (Grupo 3)")

    # Grupo Fase II: Enumeración y Ataques
    fase2_group = parser.add_argument_group('Enumeración y Ataques (Fase II)')
    fase2_group.add_argument("--banner", action="store_true", help="Banner Grabbing en puertos comunes (Grupo 1)")
    fase2_group.add_argument("--smb", action="store_true", help="Enumeración de sesiones nulas SMB (Grupo 2)")
    fase2_group.add_argument("--brute-ftp", action="store_true", help="Ataque de fuerza bruta a FTP (Grupo 3)")
    fase2_group.add_argument("--brute-web", action="store_true", help="Ataque de fuerza bruta a Web (Grupo 4)")

    args = parser.parse_args()

    print("\n" + "="*65)
    print(" ⚠️  ADVERTENCIA ÉTICA Y LEGAL")
    print(" Esta suite de auditoría ha sido desarrollada con fines")
    print(" estrictamente académicos. El uso de estos módulos contra")
    print(" servidores sin autorización explícita es un delito.")
    print("="*65)

    print(f"\n[*] Iniciando auditoria para: {args.target}")

    resultados_totales = []

    # Ejecución modular con manejo de errores individual
    try:
        if args.dns_all or args.dns_a:
            res = ejecutar_modulo(dns_recon.get_a_records, args.target)
            if res: resultados_totales.append(res)
        
        if args.dns_all or args.dns_mxns:
            res = ejecutar_modulo(dns_recon.get_mx_ns_records, args.target)
            if res: resultados_totales.append(res)
            
        if args.dns_all or args.dns_txtsoa:
            res = ejecutar_modulo(dns_recon.get_txt_soa_records, args.target)
            if res: resultados_totales.append(res)

        if args.whois:
            res = ejecutar_modulo(osint.get_whois_data, args.target)
            if res: resultados_totales.append(res)

        if args.dorks:
            # Ejecuta la función del Estudiante 2 (Subdominios)
            res_dorks = ejecutar_modulo(osint.get_subdomains_via_dorks, args.target)
            if res_dorks: resultados_totales.append(res_dorks)
            # Ejecuta la función del Estudiante 3 (Archivos expuestos)
            res_archivos = ejecutar_modulo(osint.check_archivos_expuestos, args.target)
            if res_archivos: resultados_totales.append(res_archivos)

        if args.ping_sweep:
            res = ejecutar_modulo(discovery.ping_sweep, args.target)
            if res: resultados_totales.append(res)

        if args.scan:
            res = ejecutar_modulo(scanning.scan_ports_dispatcher, args.target, args.scan)
            if res: resultados_totales.append(res)
            
        # --- Ejecución Integrada de la Fase II ---
        if args.banner:
            res = ejecutar_modulo(wrapper_banner_grabbing, args.target)
            if res: resultados_totales.append(res)
        if args.smb:
            res = ejecutar_modulo(wrapper_smb_enumeration, args.target)
            if res: resultados_totales.append(res)
        if args.brute_ftp:
            res = ejecutar_modulo(wrapper_ftp_bruteforce, args.target)
            if res: resultados_totales.append(res)
        if args.brute_web:
            res = ejecutar_modulo(wrapper_web_bruteforce, args.target)
            if res: resultados_totales.append(res)

        guardar_historial(resultados_totales)
    except AttributeError as e:
        print(f"\n[!] Error en la estructura de los módulos: {e}")
        return 1

    except (OSError, ValueError):
        print("\n[!] No se pudo guardar el historial. El archivo existente se conserva; revise su formato y permisos.")
        return 1

    except KeyboardInterrupt:
        print("\n[!] Auditoria interrumpida por el usuario.")
        sys.exit(1)

if __name__ == "__main__":
    raise SystemExit(main())
