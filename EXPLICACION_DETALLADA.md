# 📚 Guía Detallada del Proyecto GroupsApp MVP

## 🎯 Qué es este proyecto

**GroupsApp** es un **MVP (Producto Mínimo Viable)** de una aplicación de **mensajería instantánea** para Sistemas Distribuidos. Es una plataforma donde:
- Los usuarios se **registran e inician sesión** con JWT
- Pueden **crear grupos** y agregarse entre sí
- Se **envían mensajes en tiempo real** dentro de los grupos
- **Se registra el estado online/offline** de cada usuario
- Se pueden **subir archivos** (fotos, documentos, etc.)
- Los mensajes tienen **estados de entrega y lectura**

---

## 🏗️ Arquitectura General

El proyecto está diseñado como un **monolito modular**, preparado para migrar a **microservicios** en el futuro.

```
app/
├── main.py                 # 🔴 Punto de entrada
├── api/                    # 🔴 Configuración HTTP
├── core/                   # 🔴 Configuración global
├── shared/                 # 🔴 Código compartido
└── modules/                # 🔴 Funcionalidades por dominio
    ├── auth/               # 📝 Registro/Login
    ├── users/              # 👤 Perfil de usuario
    ├── groups/             # 👥 Grupos
    ├── messages/           # 💬 Mensajes
    ├── files/              # 📁 Almacenamiento
    └── presence/           # 🟢 Online/Offline
```

---

## 📂 Explicación de Cada Carpeta y Archivo

### 1️⃣ **`app/main.py`** - El Punto de Entrada

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI(title="GroupsApp")
```

**Qué hace:**
- **Inicializa la aplicación FastAPI** (framework web para APIs)
- **Configura CORS** (permite que el frontend frontend acceda desde cualquier origen)
- **Monta el frontend estático** en `/static`
- **Registra todos los routers** (módulos de la API)
- **Crea la BD** al iniciar (gracias a `lifespan`)

**Conceptos clave:**
- **FastAPI**: Framework moderno y rápido para crear APIs REST
- **CORS**: Mecanismo que permite que navegadores accedan a la API
- **lifespan**: Ciclo de vida de la aplicación (startup/shutdown)

---

### 2️⃣ **`app/core/`** - Configuración Global

#### 📄 `app/core/config.py` - Variables de Entorno

```python
class Settings(BaseSettings):
    app_name: str = 'GroupsApp'
    api_prefix: str = '/api/v1'
    secret_key: str = 'change-this-in-production'
    database_url: str = 'sqlite:///./groupsapp.db'
    upload_dir: str = './uploads'
```

**Qué hace:**
- Lee el archivo `.env` con variables de configuración
- Define valores por defecto
- Las variables pueden ser:
  - `APP_NAME`: Nombre de la aplicación
  - `SECRET_KEY`: Clave para encriptar tokens JWT (¡IMPORTANTE!)
  - `DATABASE_URL`: Dónde se guarda la BD
  - `UPLOAD_DIR`: Dónde se guardan los archivos subidos
  - `ACCESS_TOKEN_EXPIRE_MINUTES`: Cuánto tiempo dura el login

**Dato importante:** El archivo `.env` es secreto (no va en Git) y contiene datos sensibles.

---

#### 🗄️ `app/core/database.py` - Conexión con la Base de Datos

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)
```

**Qué hace:**
- **SQLAlchemy**: Es un ORM (Object-Relational Mapping) que traduce Python ↔ SQL
- **`engine`**: Es la conexión con la BD (SQLite, PostgreSQL, etc.)
- **`SessionLocal`**: Crea sesiones para hacer queries a la BD
- **`get_db()`**: Función que proporciona una sesión a cada endpoint

**Analogía:**
- La BD es como una librería (los datos)
- SQLAlchemy es el bibliotecario
- Una `Session` es como ir a la librería y pedir un libro

---

#### 🔐 `app/core/security.py` - Autenticación y Encriptación

```python
def hash_password(password: str) -> str:
    """Encripta la contraseña de forma irreversible"""
    return bcrypt.hashpw(password.encode(), salt)

def create_access_token(user_id: UUID) -> str:
    """Crea un token JWT para 60 minutos"""
    payload = {'sub': str(user_id), 'exp': datetime.now() + timedelta(minutes=60)}
    return jwt.encode(payload, secret_key, algorithm='HS256')
```

**Qué hace:**
- **`hash_password`**: Transforma la contraseña en un hash (no se puede revertir)
- **`verify_password`**: Compara una contraseña con su hash
- **`create_access_token`**: Genera un JWT (token de acceso)
- **`decode_access_token`**: Extrae el `user_id` de un token JWT

**JWT (JSON Web Token):**
- Es como un "pase" que prueba que estás autenticado
- Tiene 3 partes: Header.Payload.Signature
- El payload contiene: `{"sub": "user_id", "exp": timestamp}`
- Sin este token, no puedes acceder a endpoints protegidos

---

#### 📊 `app/core/model_registry.py` - Registro de Modelos

```python
# Importa todos los modelos para que SQLAlchemy sepa qué tablas crear
from app.modules.users.models import User
from app.modules.groups.models import Group
from app.modules.messages.models import Message
# ... etc
```

**Qué hace:**
- Importa todos los modelos de la BD
- Esto hace que SQLAlchemy registre todas las tablas
- Sin esto, `Base.metadata.create_all()` no crearía las tablas

---

### 3️⃣ **`app/api/`** - Configuración HTTP

#### 🔗 `app/api/router.py` - Agregador de Rutas

```python
api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(groups_router)
api_router.include_router(messages_router)
# ... etc
```

**Qué hace:**
- Reúne todos los routers de los módulos
- Los registra bajo `/api/v1`
- Así los endpoints quedan como: `/api/v1/auth/register`, `/api/v1/groups`, etc.

#### 🔧 `app/api/deps.py` - Dependencias HTTP

```python
def get_current_user(token: str = Depends(HTTPBearer())) -> User:
    """Extrae el usuario del token JWT"""
    user_id = decode_access_token(token)
    if not user_id:
        raise UnauthorizedError("Token inválido")
    return get_user_from_db(user_id)
```

**Qué hace:**
- Define dependencias que se usan en múltiples endpoints
- La más importante: `get_current_user` (obtiene el usuario autenticado)
- Con `Depends()`, FastAPI inyecta automáticamente estas dependencias

**Concepto: Inyección de Dependencias**
- En lugar de que cada endpoint busque el usuario, FastAPI lo hace automáticamente
- Más limpio, menos código repetido

---

### 4️⃣ **`app/shared/`** - Código Compartido

#### 🏗️ `app/shared/base_model.py` - Base de Datos Declarativa

```python
from sqlalchemy.orm import declarative_base
Base = declarative_base()
```

**Qué hace:**
- Crea la clase base para todos los modelos
- Todos los modelos heredan de `Base`
- Así SQLAlchemy sabe cómo manejarlos

#### 📋 `app/shared/enums.py` - Tipos Enumerados

```python
class MessageStatusEnum(str, Enum):
    SENT = "sent"           # El servidor lo recibió
    DELIVERED = "delivered" # El usuario lo recibió
    READ = "read"           # El usuario lo leyó
```

**Qué hace:**
- Define valores fijos y validados
- Evita errores de tipografía
- SQLAlchemy los valida automáticamente

#### ⚠️ `app/shared/exceptions.py` - Excepciones Personalizadas

```python
class PermissionDeniedError(Exception):
    pass

class NotFoundError(Exception):
    pass
```

**Qué hace:**
- Define errores específicos del negocio
- FastAPI los convierte en respuestas HTTP automáticamente

---

## 🧩 Los Módulos (Funcionalidades)

Cada módulo sigue la misma estructura:

```
modules/auth/
├── models.py      # Tabla de BD
├── schemas.py     # Validación de datos (Pydantic)
├── repository.py  # Acceso a BD
├── service.py     # Lógica de negocio
└── router.py      # Endpoints HTTP
```

### 👤 **`modules/users/`** - Gestión de Usuarios

#### 📋 `users/models.py`

```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

**Qué hace:**
- Define la **tabla de base de datos**
- Cada atributo es una **columna**
- `Mapped[]` indica el tipo de dato

**Columnas:**
- `id`: Identificador único (UUID)
- `username`: Nombre de usuario (único, no pueden haber dos iguales)
- `password_hash`: Contraseña encriptada
- `created_at`: Timestamp de creación

#### 🔍 `users/repository.py`

```python
class UserRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_username(self, username: str) -> User:
        return self.db.query(User).filter(User.username == username).first()
    
    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
```

**Qué hace:**
- **Repository Pattern**: Aísla la lógica de acceso a datos
- Los métodos son simples queries SQL (pero en Python)
- Ejemplos:
  - `get_by_username`: Busca un usuario por username
  - `create`: Inserta un usuario nuevo
  - `delete`: Elimina un usuario

**Ventaja:** Si cambias de BD (SQLite → PostgreSQL), solo cambias aquí.

#### ⚙️ `users/service.py`

```python
class UsersService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
    
    def ensure_username_available(self, username: str):
        if self.repo.get_by_username(username):
            raise UserAlreadyExistsError()
```

**Qué hace:**
- **Service Layer**: Contiene la lógica de negocio
- Usa el repository para acceder a datos
- Valida reglas del negocio
- Ejemplos de reglas:
  - "El username debe ser único"
  - "La contraseña debe tener mínimo 6 caracteres"

#### 🛣️ `users/router.py`

```python
@router.get("/{user_id}/presence")
def get_presence(user_id: UUID, db: Session = Depends(get_db)):
    user = UserRepository(db).get(user_id)
    return {"user_id": user_id, "is_online": user.presence.is_online}
```

**Qué hace:**
- Define los **endpoints HTTP**
- `@router.get()`: Método GET
- Los parámetros en `{}` son variables
- `Depends()`: Inyecta dependencias (como `db`)

---

### 📝 **`modules/auth/`** - Autenticación

#### 📋 `auth/schemas.py`

```python
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
```

**Qué hace:**
- **Pydantic Models**: Validan los datos que llegan del frontend
- `Field()`: Define restricciones
- FastAPI valida automáticamente y devuelve errores si es necesario

#### ⚙️ `auth/service.py`

```python
def register(self, username: str, password: str) -> User:
    self.users_service.ensure_username_available(username)
    user = User(username=username, password_hash=hash_password(password))
    return self.users_repo.create(user)

def login(self, username: str, password: str) -> str:
    user = self.users_repo.get_by_username(username)
    if not user or not verify_password(password, user.password_hash):
        raise PermissionDeniedError('Credenciales inválidas')
    return create_access_token(user.id)
```

**Qué hace:**
- **`register()`**: Crea un nuevo usuario
  1. Valida que el username no exista
  2. Encripta la contraseña
  3. La guarda en la BD
- **`login()`**: Autentica un usuario
  1. Busca el usuario por username
  2. Verifica que la contraseña sea correcta
  3. Devuelve un JWT token

#### 🛣️ `auth/router.py`

```python
@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    user = AuthService(UserRepository(db)).register(req.username, req.password)
    return user

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    token = AuthService(UserRepository(db)).login(req.username, req.password)
    return TokenResponse(access_token=token)
```

**Endpoints:**
- `POST /api/v1/auth/register`: Registra un nuevo usuario
- `POST /api/v1/auth/login`: Devuelve un JWT token

---

### 👥 **`modules/groups/`** - Gestión de Grupos

#### 📋 `groups/models.py`

```python
class Group(Base):
    __tablename__ = "groups"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str]
    admin_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    admin: Mapped[User] = relationship("User")
    members: Mapped[list[GroupMember]] = relationship()
    created_at: Mapped[datetime]

class GroupMember(Base):
    __tablename__ = "group_members"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
```

**Qué hace:**
- **Group**: Tabla de grupos
  - `admin_id`: ID del usuario que creó el grupo
  - `members`: Lista de miembros (relación con GroupMember)
- **GroupMember**: Tabla de membresía (join table)
  - `group_id` + `user_id`: Vincula usuarios con grupos

**Concepto: Relaciones Many-to-Many**
```
User 1 ──────┐
             ├── Group 1
User 2 ──────┘

User 3 ──────┐
             ├── Group 2
User 4 ──────┘
```

#### ⚙️ `groups/service.py`

```python
def create_group(self, name: str, admin_id: UUID) -> Group:
    group = Group(name=name, admin_id=admin_id)
    created_group = self.repo.create(group)
    # El admin se agrega automáticamente al grupo
    self.add_member(created_group.id, admin_id)
    return created_group

def add_member(self, group_id: UUID, user_id: UUID):
    if not self.repo.is_member(group_id, user_id):
        self.repo.add_member(group_id, user_id)
```

**Qué hace:**
- Crear grupos
- Agregar/eliminar miembros
- Validar que el usuario sea admin para ciertas acciones

---

### 💬 **`modules/messages/`** - Mensajería

#### 📋 `messages/models.py`

```python
class Message(Base):
    __tablename__ = "messages"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("groups.id"))
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str]
    status: Mapped[MessageStatusEnum] = mapped_column(default=MessageStatusEnum.SENT)
    created_at: Mapped[datetime]

class MessageReceipt(Base):
    __tablename__ = "message_receipts"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(ForeignKey("messages.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ReceiptStatusEnum]  # "delivered" o "read"
```

**Qué hace:**
- **Message**: Los mensajes del grupo
  - `status`: SENT (enviado), DELIVERED (entregado), READ (leído)
- **MessageReceipt**: Registra cuándo cada usuario leyó el mensaje
  - Permite saber "Visto por: Usuario A a las 14:30, Usuario B a las 14:32"

#### 🌐 `messages/websocket.py` - Tiempo Real

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, group_id: str, websocket: WebSocket):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = []
        self.active_connections[group_id].append(websocket)
    
    async def broadcast(self, group_id: str, message: dict):
        # Envía el mensaje a todos en el grupo
        for connection in self.active_connections[group_id]:
            await connection.send_json(message)
```

**Qué hace:**
- **WebSocket**: Conexión permanente entre cliente y servidor
- Cuando se abre: Se guarda en `active_connections`
- Cuando se envía un mensaje: Se hace `broadcast` a todos
- Cuando se cierra: Se elimina de la lista

**HTTP vs WebSocket:**
- **HTTP**: Cliente envía request → Servidor responde (unidireccional)
- **WebSocket**: Cliente y servidor pueden enviarse mensajes en cualquier momento (bidireccional)

#### 🛣️ `messages/ws_router.py`

```python
@router.websocket("/ws/groups/{group_id}")
async def websocket_endpoint(websocket: WebSocket, group_id: str, token: str):
    user_id = decode_access_token(token)
    await manager.connect(group_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            # Procesar mensaje
            message = Message(
                group_id=group_id,
                sender_id=user_id,
                content=data['content']
            )
            db.add(message)
            db.commit()
            
            # Enviar a todos en el grupo
            await manager.broadcast(group_id, {...})
    except WebSocketDisconnect:
        manager.disconnect(group_id, websocket)
```

**Qué hace:**
- Abre un WebSocket en `/ws/groups/{group_id}?token=JWT_TOKEN`
- Autentifica el token
- Mientras esté conectado, recibe mensajes
- Los guarda en BD y hace broadcast

---

### 📁 **`modules/files/`** - Almacenamiento de Archivos

#### 🏗️ `files/storage_port.py` - Patrón Adapter

```python
class StoragePort(ABC):
    @abstractmethod
    async def upload(self, file: UploadFile) -> str:
        pass  # Devuelve URL del archivo
    
    @abstractmethod
    async def delete(self, file_key: str) -> bool:
        pass
```

**Qué hace:**
- Define una interfaz para almacenamiento
- Permite cambiar de "local" → "S3" sin cambiar el resto del código

#### 💾 `files/local_storage.py` - Implementación Local

```python
class LocalStorage(StoragePort):
    async def upload(self, file: UploadFile) -> str:
        file_path = Path(settings.upload_dir) / file.filename
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(await file.read())
        return f"/uploads/{file.filename}"
```

**Qué hace:**
- Guarda archivos en el servidor local
- En producción, normalmente usarías S3/CloudStorage

#### 🛣️ `files/router.py`

```python
@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    file_url = await storage.upload(file)
    file_record = File(
        filename=file.filename,
        file_url=file_url,
        uploader_id=current_user.id
    )
    return {"file_url": file_url}
```

**Qué hace:**
- `POST /api/v1/messages/file`: Sube un archivo
- Solo usuarios autenticados pueden subir
- Devuelve la URL del archivo

---

### 🟢 **`modules/presence/`** - Estado Online/Offline

#### 📋 `presence/models.py`

```python
class Presence(Base):
    __tablename__ = "presence"
    
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    is_online: Mapped[bool] = mapped_column(default=False)
    last_seen: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

**Qué hace:**
- Registra si un usuario está online o no
- `last_seen`: Última vez que fue visto

#### ⚙️ `presence/service.py`

```python
def set_online(self, user_id: UUID):
    presence = self.repo.get_or_create(user_id)
    presence.is_online = True
    self.repo.update(presence)

def set_offline(self, user_id: UUID):
    presence = self.repo.get_or_create(user_id)
    presence.is_online = False
    presence.last_seen = datetime.utcnow()
    self.repo.update(presence)
```

**Qué hace:**
- Marcar usuario como online (cuando se conecta)
- Marcar usuario como offline (cuando se desconecta)

---

## 🔄 Flujo de Datos Ejemplo: Registrar un Usuario

```
1. Cliente: POST /api/v1/auth/register
   { "username": "juan", "password": "12345" }
        ↓
2. FastAPI: Router recibe y valida (RegisterRequest)
        ↓
3. main.py: AuthRouter.register()
        ↓
4. auth/router.py: register() endpoint
        ↓
5. auth/service.py: AuthService.register()
        ↓
6. users/repository.py: UserRepository.create()
        ↓
7. database.py: SessionLocal -> engine.execute(INSERT)
        ↓
8. SQLite: Guarda en tabla "users"
        ↓
9. repository: Devuelve objeto User
        ↓
10. service: Valida reglas de negocio
        ↓
11. router: Convierte a JSON
        ↓
12. Cliente: 201 Created
    { "id": "uuid-123", "username": "juan" }
```

---

## 🌍 Flujo de Datos Ejemplo: Enviar un Mensaje

```
1. Cliente: WebSocket conecta a /ws/groups/group-123?token=JWT
        ↓
2. ws_router.py: websocket_endpoint() acepta conexión
        ↓
3. ConnectionManager: Se agrega a active_connections
        ↓
4. Cliente: Envía mensaje {"content": "Hola!"}
        ↓
5. ws_router.py: Recibe mensaje (await websocket.receive_json())
        ↓
6. messages/repository.py: Crea registro en BD
        ↓
7. messages/service.py: Valida permisos
        ↓
8. ConnectionManager.broadcast(): Envía a todos en el grupo
        ↓
9. Todos los usuarios en el grupo reciben el mensaje en tiempo real
```

---

## 🗄️ Estructura de la Base de Datos

```
┌─────────────────┐
│     users       │
├─────────────────┤
│ id (PK)         │ ←──┐
│ username (UQ)   │    │
│ password_hash   │    │
│ created_at      │    │
└─────────────────┘    │
         ↑              │
         │              │
         │         ┌────────────────┐
         │         │     groups     │
         │         ├────────────────┤
         │         │ id (PK)        │
         │──────── │ admin_id (FK)  │
         │         │ name           │
         │         │ created_at     │
         │         └────────────────┘
         │              ↑
         │              │
         │     ┌────────────────────┐
         │     │  group_members     │
         │     ├────────────────────┤
         │     │ id (PK)            │
         │     │ group_id (FK)      │
         │─────│ user_id (FK)       │
         │     └────────────────────┘
         │
         │     ┌────────────────────┐
         │     │    messages        │
         │     ├────────────────────┤
         │     │ id (PK)            │
         │     │ group_id (FK)      │
         │─────│ sender_id (FK)     │
         │     │ content            │
         │     │ status             │
         │     │ created_at         │
         │     └────────────────────┘
         │
         │     ┌────────────────────┐
         │     │  presence          │
         │     ├────────────────────┤
         │     │ id (PK)            │
         │─────│ user_id (FK)       │
         │     │ is_online          │
         │     │ last_seen          │
         │     └────────────────────┘
         │
         └─────┐
               │
         ┌─────────────────────┐
         │      files          │
         ├─────────────────────┤
         │ id (PK)             │
         │ uploader_id (FK)    │
         │ filename            │
         │ file_url            │
         │ created_at          │
         └─────────────────────┘
```

---

## 🔐 Autenticación: Cómo Funciona el JWT

```
1. Usuario hace login:
   POST /api/v1/auth/login
   { "username": "juan", "password": "12345" }

2. Backend:
   - Busca usuario
   - Verifica contraseña
   - Crea JWT: "eyJhbGc.eyJzdWI.SflKxwR"
   
3. Estructura del JWT:
   Header: {"alg": "HS256", "typ": "JWT"}
   Payload: {"sub": "user-id-123", "exp": 1735452221}
   Signature: HMACSHA256(Header + Payload, SECRET_KEY)

4. Cliente guarda token en localStorage

5. En cada request protegido:
   Authorization: Bearer eyJhbGc.eyJzdWI.SflKxwR
   
6. Backend:
   - Extrae token del header
   - Verifica firma (¿no fue modificado?)
   - Valida expiración (¿sigue siendo válido?)
   - Extrae user_id
   - Permite acceso
```

---

## 📊 Patrones de Diseño Usados

### 1. **Repository Pattern**
Abstrae la lógica de acceso a datos.
```
Controller → Service → Repository → Database
```

### 2. **Service Layer**
Contiene la lógica de negocio.
```
- Validaciones
- Conversiones
- Orquestación
```

### 3. **Dependency Injection**
FastAPI inyecta dependencias automáticamente.
```python
def get_groups(db: Session = Depends(get_db)):
    # db es inyectado automáticamente
```

### 4. **Adapter Pattern**
Permite cambiar implementaciones fácilmente.
```python
# Hoy: LocalStorage
# Mañana: S3Storage
# Solo cambias esta línea
```

---

## 🚀 Cómo Funciona el Proyecto

### 1. Instalación y Configuración
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Ejecutar
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Acceder
- **API**: http://localhost:8000/docs (Swagger interactivo)
- **Frontend**: http://localhost:8000 (HTML + JS)

---

## 🎯 Endpoints Disponibles

### Autenticación
- `POST /api/v1/auth/register` - Registrar
- `POST /api/v1/auth/login` - Login (devuelve JWT)

### Usuarios
- `GET /api/v1/users/{user_id}/presence` - Ver si está online

### Grupos
- `GET /api/v1/groups` - Listar grupos del usuario
- `POST /api/v1/groups` - Crear grupo
- `POST /api/v1/groups/{id}/members` - Agregar miembro
- `DELETE /api/v1/groups/{id}/members/{user_id}` - Eliminar miembro

### Mensajes
- `GET /api/v1/groups/{id}/messages` - Historial
- `POST /api/v1/groups/{id}/messages` - Enviar mensaje
- `POST /api/v1/messages/file` - Subir archivo

### WebSocket
- `WS /ws/groups/{group_id}?token=JWT` - Chat en tiempo real

---

## 📝 Resumen de Tecnologías

| Tecnología | Para Qué |
|-----------|----------|
| **FastAPI** | Framework web (APIs REST) |
| **SQLAlchemy** | ORM (mapeo BD → Python) |
| **Pydantic** | Validación de datos |
| **JWT** | Autenticación (tokens) |
| **bcrypt** | Encriptar contraseñas |
| **WebSocket** | Mensajería en tiempo real |
| **SQLite** | Base de datos (desarrollo) |

---

## 🔮 Plan de Migración a Microservicios

El código está diseñado para facilitar esta migración:

1. **Separar módulos en servicios**
   - `auth-service`
   - `groups-service`
   - `messages-service`
   - `files-service`

2. **Comunicación entre servicios**
   - HTTP REST
   - gRPC (para consultas rápidas)
   - Colas de mensajes (RabbitMQ/Kafka)

3. **Escala**
   - Cada servicio en su propio contenedor
   - Kubernetes para orquestación
   - Load balancer para distribuir carga

---

## 💡 Consejos para Entender Mejor

1. **Lee los archivos en este orden:**
   ```
   1. app/main.py
   2. app/core/config.py
   3. app/core/database.py
   4. app/api/router.py
   5. app/modules/auth/
   6. app/modules/users/
   ```

2. **Experimenta:**
   - Abre http://localhost:8000/docs
   - Prueba los endpoints
   - Verifica qué se guarda en `groupsapp.db`

3. **Sigue el código:**
   - Pon breakpoints en tu IDE
   - Ve cómo fluyen los datos
   - Entiende qué hace cada función

4. **Modifica y aprende:**
   - Añade un nuevo campo a User
   - Crea un nuevo endpoint
   - Guarda, mira cómo actualiza la BD

---

## ¿Preguntas Comunes?

**P: ¿Por qué SQLAlchemy y no SQL directo?**
R: SQLAlchemy abstrae la BD. Si cambias de SQLite a PostgreSQL, solo cambias una línea.

**P: ¿Por qué Pydantic y no validar manualmente?**
R: Pydantic lo hace automáticamente. Menos código, menos errores.

**P: ¿Cómo sé si un usuario está autenticado?**
R: FastAPI extrae el JWT del header `Authorization: Bearer TOKEN` y lo valida automáticamente.

**P: ¿Cómo funciona el WebSocket?**
R: Es una conexión persistente. El cliente se conecta, recibe un socket, y ambos pueden enviarse mensajes.

**P: ¿Dónde se guardan los archivos?**
R: En `./uploads` (configurable en `.env`). En producción usarías AWS S3.

---

¡Ahora tienes una visión clara de cómo funciona todo! 🎉
