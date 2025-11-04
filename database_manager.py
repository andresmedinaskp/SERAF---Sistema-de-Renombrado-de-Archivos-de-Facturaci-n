import configparser
import os
import firebirdsql  # CAMBIAR fdb por firebirdsql
import datetime
from pathlib import Path

class DatabaseManager:
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def get_db_params(self):
        """Obtiene parámetros de conexión desde database.ini"""
        config = configparser.ConfigParser()
        
        if not os.path.exists('database.ini'):
            raise Exception("Archivo database.ini no encontrado")
        
        config.read('database.ini')
        
        if 'database' not in config:
            raise Exception("Sección [database] no encontrada en database.ini")
        
        db_config = config['database']
        
        return {
            'host': db_config.get('host', '127.0.0.1'),
            'database': db_config.get('database', ''),
            'user': db_config.get('user', 'SYSDBA'),
            'password': db_config.get('password', ''),
            'charset': db_config.get('charset', 'WIN1252')  # CAMBIAR A WIN1252
        }
    
    def get_connection(self):
        """Obtiene conexión singleton a la BD"""
        if self._connection is None:
            params = self.get_db_params()
            
            if not params['database']:
                raise Exception("Ruta de base de datos no especificada en database.ini")
            
            try:
                # USAR FIREBIRDSQL EN LUGAR DE FDB
                self._connection = firebirdsql.connect(
                    host=params['host'],
                    database=params['database'],
                    user=params['user'],
                    password=params['password'],
                    charset=params['charset']
                )
                print(f"Conexión exitosa a {params['host']}:{params['database']}")
            except firebirdsql.OperationalError as e:
                # Manejar errores específicos de Firebird
                error_msg = f"Error de Firebird: {str(e)}"
                if '335544721' in str(e) or '335544722' in str(e):
                    error_msg += "\n\nPosible problema de conexión de red. Verifique:\n- Dirección IP del servidor\n- Servicio Firebird ejecutándose\n- Firewall/puerto 3050"
                elif '335544344' in str(e) or '335544345' in str(e):
                    error_msg += "\n\nArchivo de base de datos no encontrado. Verifique la ruta."
                elif '335544472' in str(e):
                    error_msg += "\n\nCredenciales incorrectas. Verifique usuario y contraseña."
                raise Exception(error_msg)
            except Exception as e:
                raise Exception(f"Error conectando a la base de datos: {str(e)}")
        
        return self._connection
    
    def close_connection(self):
        """Cierra la conexión a la BD"""
        if self._connection:
            self._connection.close()
            self._connection = None

def obtener_datos_ips():
    """Obtiene los datos de IPS desde la tabla LST_IPS"""
    db = DatabaseManager()
    conn = None
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        
        # Consulta CORREGIDA - solo usa LST_IPS
        cur.execute("""
            SELECT FIRST 1 cod_ips, nro_ident 
            FROM LST_IPS
        """)
        
        resultado = cur.fetchone()
        cur.close()
        
        if resultado:
            return {
                'codigo_ips': str(resultado[0]) if resultado[0] is not None else "",
                'nit': str(resultado[1]) if resultado[1] is not None else ""
            }
        else:
            # Si no encuentra datos en LST_IPS, retornar valores por defecto
            return {
                'codigo_ips': "890000000",
                'nit': "900000000"
            }
            
    except Exception as e:
        print(f"Error obteniendo datos IPS desde LST_IPS: {e}")
        # En caso de error, retornar valores por defecto
        return {
            'codigo_ips': "890000000",
            'nit': "900000000"
        }