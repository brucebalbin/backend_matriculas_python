import oracledb

# Configura tus credenciales reales aquí
DB_USER = "bd_matriculas"
DB_PASSWORD = "123456"
DB_DSN = "localhost:1521/XEPDB1"

def get_db_connection():
    """Crea y retorna la conexión a la base de datos Oracle."""
    try:
        connection = oracledb.connect(
            user=DB_USER, 
            password=DB_PASSWORD, 
            dsn=DB_DSN
        )
        return connection
    except oracledb.DatabaseError as e:
        error, = e.args
        print(f"Error crítico conectando a Oracle: {error.message}")
        return None