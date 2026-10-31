from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import oracledb
from database import get_db_connection
from schemas import MatriculaRequest, AlumnoRequest, LoginRequest, ProfesorRequest, CursoRequest

app = FastAPI(title="Sistema de Matrículas - BD Oracle")

# Configuración del Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # El asterisco permite que cualquier página (Vercel, Netlify, localhost) se conecte.
    allow_credentials=True,
    allow_methods=["*"], # Permite todos los métodos (GET, POST, PUT, DELETE)
    allow_headers=["*"],
)

# Exponer la carpeta estática para la página web HTML
app.mount("/web", StaticFiles(directory="static", html=True), name="static")

# ==========================================
# CONEXIÓN A LA BASE DE DATOS
# ==========================================
def get_db_connection():
    try:
        # Ruta donde estará la carpeta wallet en el servidor
        wallet_dir = os.path.join(os.path.dirname(__file__), "wallet")
        
        # Conexión usando wallet y las credenciales de Oracle Cloud
        connection = oracledb.connect(
            user="ADMIN",
            password="TuContraseñaSeguraDeOracle",
            dsn="edusysdb_high", # Verifica que este nombre coincida con tu tnsnames.ora
            config_dir=wallet_dir,
            wallet_location=wallet_dir,
            wallet_password="ContraseñaDelWallet"
        )
        return connection
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

# 1. Montar la carpeta 'static' para mostrar tu frontend (index.html)
app.mount("/web", StaticFiles(directory="static", html=True), name="static")

# ==========================================
# MÓDULO AUTENTICACIÓN (LOGIN)
# ==========================================
@app.post("/api/login")
def iniciar_sesion(req: LoginRequest):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de base de datos")
    
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT rol, password_hash FROM USUARIOS WHERE username = :1 AND estado = 'A'", [req.username])
        row = cursor.fetchone()
        
        if row:
            rol, password_hash = row
            if req.password == password_hash:
                nombre_mostrar = req.username
                
                # Si es alumno, buscamos su nombre real por su DNI (username)
                if rol == 'ALUMNO':
                    cursor.execute("SELECT nombres, apellidos FROM ALUMNOS WHERE dni = :1", [req.username])
                    alum = cursor.fetchone()
                    if alum:
                        # alum[0] son nombres, alum[1] son apellidos
                        # Usamos .split()[0] para sacar solo el primer nombre y primer apellido
                        primer_nombre = alum[0].split()[0]
                        primer_apellido = alum[1].split()[0]
                        nombre_mostrar = f"{primer_nombre} {primer_apellido}"
                elif rol == 'ADMIN':
                    nombre_mostrar = "Admin"

                return {
                    "success": True, 
                    "username": req.username, 
                    "nombre_mostrar": nombre_mostrar, 
                    "rol": rol
                }
                
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    except oracledb.DatabaseError as e:
        error, = e.args
        raise HTTPException(status_code=500, detail=error.message)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# MÓDULO ALUMNOS (CRUD)
# ==========================================
@app.get("/api/alumnos")
def listar_alumnos():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_alumno, dni, nombres, apellidos, correo, estado FROM ALUMNOS")
    columnas = [col[0].lower() for col in cursor.description]
    alumnos = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
    cursor.close()
    conn.close()
    return alumnos

@app.post("/api/alumnos")
def crear_alumno(req: AlumnoRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO ALUMNOS (dni, nombres, apellidos, correo, estado) 
            VALUES (:1, :2, :3, :4, :5)
        """, [req.dni, req.nombres, req.apellidos, req.correo, req.estado])
        conn.commit()
        return {"mensaje": "Alumno registrado exitosamente"}
    except oracledb.DatabaseError as e:
        conn.rollback()
        error, = e.args
        raise HTTPException(status_code=400, detail=error.message)
    finally:
        cursor.close()
        conn.close()

@app.put("/api/alumnos/{id_alumno}")
def actualizar_alumno(id_alumno: int, req: AlumnoRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE ALUMNOS 
            SET dni = :1, nombres = :2, apellidos = :3, correo = :4, estado = :5
            WHERE id_alumno = :6
        """, [req.dni, req.nombres, req.apellidos, req.correo, req.estado, id_alumno])
        conn.commit()
        return {"mensaje": "Alumno actualizado"}
    except oracledb.DatabaseError as e:
        conn.rollback()
        error, = e.args
        raise HTTPException(status_code=400, detail=error.message)
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/alumnos/{id_alumno}")
def eliminar_alumno(id_alumno: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM ALUMNOS WHERE id_alumno = :1", [id_alumno])
        conn.commit()
        return {"mensaje": "Alumno eliminado"}
    except oracledb.DatabaseError as e:
        conn.rollback()
        error, = e.args
        raise HTTPException(status_code=400, detail=error.message)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# MÓDULO PROFESORES
# ==========================================
@app.get("/api/profesores")
def listar_profesores():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Consulta a la tabla PROFESORES de Oracle
    cursor.execute("SELECT id_profesor, dni, nombres, apellidos, especialidad, correo, estado FROM PROFESORES")
    
    # Transformar resultado a JSON
    columnas = [col[0].lower() for col in cursor.description]
    profesores = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    return profesores
@app.post("/api/profesores")
def crear_profesor(req: ProfesorRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO PROFESORES (dni, nombres, apellidos, especialidad, correo, estado) 
            VALUES (:1, :2, :3, :4, :5, :6)
        """, [req.dni, req.nombres, req.apellidos, req.especialidad, req.correo, req.estado])
        conn.commit()
        return {"mensaje": "Profesor registrado correctamente"}
    except oracledb.DatabaseError as e:
        conn.rollback()
        error, = e.args
        raise HTTPException(status_code=400, detail=error.message)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# MÓDULO CURSOS
# ==========================================
@app.get("/api/cursos")
def listar_cursos():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_curso, nombre_curso, precio, vacantes, estado FROM CURSOS")
    columnas = [col[0].lower() for col in cursor.description]
    cursos = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
    cursor.close()
    conn.close()
    return cursos
@app.post("/api/cursos")
def crear_curso(req: CursoRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO CURSOS (nombre_curso, precio, vacantes, id_profesor, estado) 
            VALUES (:1, :2, :3, :4, :5)
        """, [req.nombre_curso, req.precio, req.vacantes, req.id_profesor, req.estado])
        conn.commit()
        return {"mensaje": "Curso registrado correctamente"}
    except oracledb.DatabaseError as e:
        conn.rollback()
        error, = e.args
        raise HTTPException(status_code=400, detail=error.message)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# MÓDULO MATRÍCULAS
# ==========================================
@app.get("/api/matriculas/resumen")
def obtener_resumen_matriculas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM v_res_matricula")
    columnas = [col[0].lower() for col in cursor.description]
    resultado = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
    cursor.close()
    conn.close()
    return resultado

@app.post("/api/matriculas/registrar")
def registrar_matricula(req: MatriculaRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        var_resultado = cursor.var(str)
        cursor.callproc(
            "registrar_matricula",
            [req.id_alumno, req.id_curso, req.monto_inicial, req.metodo_pago, var_resultado]
        )
        mensaje = var_resultado.getvalue()
        
        if mensaje.startswith("Error"):
            raise HTTPException(status_code=400, detail=mensaje)
            
        return {"mensaje": mensaje}
    except oracledb.DatabaseError as e:
        error, = e.args
        raise HTTPException(status_code=500, detail=error.message)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# MÓDULO MIS CURSOS (Vista para el Alumno)
# ==========================================
@app.get("/api/matriculas/mis-cursos/{username}")
def obtener_mis_cursos(username: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Filtramos la vista usando el DNI del alumno (username)
        cursor.execute("SELECT * FROM v_res_matricula WHERE dni_alumno = :1", [username])
        columnas = [col[0].lower() for col in cursor.description]
        resultado = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
        return resultado
    except oracledb.DatabaseError as e:
        error, = e.args
        raise HTTPException(status_code=500, detail=error.message)
    finally:
        cursor.close()
        conn.close()  
  
# ==========================================
# MÓDULO AUDITORÍA (Monitoreo de Triggers)
# ==========================================
@app.get("/api/auditoria")
def obtener_auditoria():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")
        
    cursor = conn.cursor()
    try:
        # Consultamos la tabla generada por el Trigger
        cursor.execute("""
            SELECT 
                id_auditoria, 
                id_matricula, 
                accion, 
                usuario_bd, 
                TO_CHAR(fecha, 'DD/MM/YYYY HH24:MI:SS') AS fecha, 
                detalle_anterior 
            FROM AUDITORIA_MATRICULAS 
            ORDER BY id_auditoria DESC
        """)
        
        # Convertimos el resultado de Oracle a un formato de Diccionario (JSON)
        columnas = [col[0].lower() for col in cursor.description]
        resultado = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
        
        return resultado
        
    except oracledb.DatabaseError as e:
        error, = e.args
        raise HTTPException(status_code=500, detail=error.message)
    finally:
        cursor.close()
        conn.close()

# ==========================================
# RUTAS PARA EDITAR Y ELIMINAR (SOLO ADMIN)
# ==========================================

# --- ALUMNOS ---
@app.put("/api/alumnos/{id}")
def editar_alumno(id: int, req: AlumnoRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE ALUMNOS SET dni=:1, nombres=:2, apellidos=:3, correo=:4 WHERE id_alumno=:5", 
                       [req.dni, req.nombres, req.apellidos, req.correo, id])
        conn.commit()
        return {"mensaje": "Alumno actualizado"}
    except oracledb.DatabaseError as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=e.args[0].message)
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/alumnos/{id}")
def eliminar_alumno(id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM ALUMNOS WHERE id_alumno=:1", [id])
        conn.commit()
        return {"mensaje": "Alumno eliminado"}
    except oracledb.DatabaseError as e:
        conn.rollback()
        if "ORA-02292" in e.args[0].message:
            raise HTTPException(status_code=400, detail="No se puede eliminar: El alumno ya tiene matrículas registradas.")
        raise HTTPException(status_code=400, detail=e.args[0].message)
    finally:
        cursor.close()
        conn.close()

# --- PROFESORES ---
@app.put("/api/profesores/{id}")
def editar_profesor(id: int, req: ProfesorRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE PROFESORES SET dni=:1, nombres=:2, apellidos=:3, especialidad=:4, correo=:5 WHERE id_profesor=:6", 
                       [req.dni, req.nombres, req.apellidos, req.especialidad, req.correo, id])
        conn.commit()
        return {"mensaje": "Profesor actualizado"}
    except oracledb.DatabaseError as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=e.args[0].message)
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/profesores/{id}")
def eliminar_profesor(id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM PROFESORES WHERE id_profesor=:1", [id])
        conn.commit()
        return {"mensaje": "Profesor eliminado"}
    except oracledb.DatabaseError as e:
        conn.rollback()
        if "ORA-02292" in e.args[0].message:
            raise HTTPException(status_code=400, detail="No se puede eliminar: El profesor tiene cursos asignados.")
        raise HTTPException(status_code=400, detail=e.args[0].message)
    finally:
        cursor.close()
        conn.close()

# --- CURSOS ---
@app.put("/api/cursos/{id}")
def editar_curso(id: int, req: CursoRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE CURSOS SET nombre_curso=:1, precio=:2, vacantes=:3, id_profesor=:4 WHERE id_curso=:5", 
                       [req.nombre_curso, req.precio, req.vacantes, req.id_profesor, id])
        conn.commit()
        return {"mensaje": "Curso actualizado"}
    except oracledb.DatabaseError as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=e.args[0].message)
    finally:
        cursor.close()
        conn.close()

@app.delete("/api/cursos/{id}")
def eliminar_curso(id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM CURSOS WHERE id_curso=:1", [id])
        conn.commit()
        return {"mensaje": "Curso eliminado"}
    except oracledb.DatabaseError as e:
        conn.rollback()
        if "ORA-02292" in e.args[0].message:
            raise HTTPException(status_code=400, detail="No se puede eliminar: Existen matrículas en este curso.")
        raise HTTPException(status_code=400, detail=e.args[0].message)
    finally:
        cursor.close()
        conn.close()
# ==========================================
# BUSCADORES POR DNI (CORRECCIÓN DE FORMATO JSON)
# ==========================================
@app.get("/api/alumnos/buscar/{dni}")
def buscar_alumno_por_dni(dni: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        parametro_busqueda = f"{dni}%"
        cursor.execute("SELECT * FROM ALUMNOS WHERE dni LIKE :1", [parametro_busqueda])
        
        # 1. Fuerza a que todas las columnas de Oracle estén en minúsculas
        columnas = [col[0].lower() for col in cursor.description]
        filas = cursor.fetchall()
        
        # 2. Empareja las columnas con los datos creando una lista de diccionarios (JSON válido)
        if filas:
            return [dict(zip(columnas, fila)) for fila in filas]
        return []
    except oracledb.DatabaseError as e:
        error, = e.args
        raise HTTPException(status_code=500, detail=error.message)
    finally:
        cursor.close()
        conn.close()

@app.get("/api/profesores/buscar/{dni}")
def buscar_profesor_por_dni(dni: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        parametro_busqueda = f"{dni}%"
        cursor.execute("SELECT * FROM PROFESORES WHERE dni LIKE :1", [parametro_busqueda])
        
        columnas = [col[0].lower() for col in cursor.description]
        filas = cursor.fetchall()
        
        if filas:
            return [dict(zip(columnas, fila)) for fila in filas]
        return []
    except oracledb.DatabaseError as e:
        error, = e.args
        raise HTTPException(status_code=500, detail=error.message)
    finally:
        cursor.close()
        conn.close()
# ==========================================
# AUTOCOMPLETADO (SUGERENCIAS EN TIEMPO REAL)
# ==========================================
@app.get("/api/alumnos/sugerencias/{parcial}")
def sugerencias_alumnos(parcial: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Busca DNI que comiencen con lo que el usuario está escribiendo (Máximo 5 resultados)
        cursor.execute("""
            SELECT dni, nombres, apellidos 
            FROM ALUMNOS 
            WHERE dni LIKE :1 || '%' AND estado = 'A'
            FETCH FIRST 5 ROWS ONLY
        """, [parcial])
        
        # Devuelve el DNI y el nombre concatenado para mostrarlo bonito en la lista
        resultados = [{"dni": row[0], "nombre": f"{row[1]} {row[2]}"} for row in cursor.fetchall()]
        return resultados
    finally:
        cursor.close()
        conn.close()

@app.get("/api/profesores/sugerencias/{parcial}")
def sugerencias_profesores(parcial: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT dni, nombres, apellidos 
            FROM PROFESORES 
            WHERE dni LIKE :1 || '%' AND estado = 'A'
            FETCH FIRST 5 ROWS ONLY
        """, [parcial])
        
        resultados = [{"dni": row[0], "nombre": f"{row[1]} {row[2]}"} for row in cursor.fetchall()]
        return resultados
    finally:
        cursor.close()
        conn.close()