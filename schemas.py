from pydantic import BaseModel
from typing import Optional

# Modelo para recibir los datos de una nueva matrícula
class MatriculaRequest(BaseModel):
    id_alumno: int
    id_curso: int
    monto_inicial: float
    metodo_pago: str

# Modelo para recibir los datos de un alumno (CRUD)
class AlumnoRequest(BaseModel):
    dni: str
    nombres: str
    apellidos: str
    correo: Optional[str] = None
    estado: Optional[str] = "A"

class LoginRequest(BaseModel):
    username: str
    password: str
    
class ProfesorRequest(BaseModel):
    dni: str
    nombres: str
    apellidos: str
    especialidad: Optional[str] = None
    correo: Optional[str] = None
    estado: Optional[str] = "A"

class CursoRequest(BaseModel):
    nombre_curso: str
    precio: float
    vacantes: int
    id_profesor: int
    estado: Optional[str] = "A"