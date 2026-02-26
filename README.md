# GroupsApp MVP (Semana 7)

MVP de mensajería instantánea para Sistemas Distribuidos, construido como **monolito modular** preparado para migrar a microservicios.

## Stack
- FastAPI
- SQLAlchemy 2 + PostgreSQL/SQLite
- JWT (login/register)
- WebSocket (tiempo real)
- Storage local con adapter (migrable a S3)

## Estructura del proyecto

```txt
app/
  api/                 # Dependencias HTTP y router principal
  core/                # Configuración, seguridad, BD, logging
  shared/              # Base declarativa, enums, excepciones
  modules/
    auth/              # Registro y login
    users/             # Usuario y endpoint /users/me/presence
    groups/            # Grupos y membresías
    messages/          # Mensajes + receipts + websocket
    files/             # Subida de archivos (adapter local)
    presence/          # Estado online/offline
  migrations/          # Reserva para Alembic
scripts/
  run_dev.sh
  deploy_ec2.sh
```

## Requisitos
- Python 3.9+

## Instalación local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Documentación: `http://localhost:8000/docs`

## Endpoints del MVP

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/token` (interno para botón Authorize de Swagger)
- `POST /api/v1/groups`
- `POST /api/v1/groups/{group_id}/members`
- `POST /api/v1/groups/{group_id}/messages`
- `GET /api/v1/groups/{group_id}/messages`
- `POST /api/v1/messages/file`
- `GET /api/v1/users/me/presence`
- `WS /ws/groups/{group_id}?token=<JWT>`

## Flujo rápido de prueba

1. Registrar dos usuarios con `/auth/register`.
2. En Swagger, usar `Authorize` con username/password (usa `/auth/token` internamente).
3. Crear grupo con usuario admin en `/groups`.
4. Agregar segundo usuario en `/groups/{group_id}/members`.
5. Enviar mensajes por `/groups/{group_id}/messages`.
6. Consultar historial en `/groups/{group_id}/messages`.
7. Subir archivo por `/messages/file` (`multipart/form-data`).
8. Abrir WebSocket en `/ws/groups/{group_id}` con token del usuario.

## Variables de entorno

- `APP_NAME`
- `API_PREFIX`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `DATABASE_URL` (ej. `postgresql+psycopg://user:pass@localhost:5432/groupsapp`)
- `UPLOAD_DIR`

## Roadmap recomendado (entrega semana 7)

### Semana 5-6
- Registro/login JWT
- Creación de grupos
- Mensajes de texto en grupo

### Semana 6-7
- Historial persistente
- Upload de archivos/imágenes
- Estados entrega/lectura
- Presencia online/offline

## Plan de migración a microservicios (resumen)

1. Separar módulos en servicios independientes:
- `users-auth-service`
- `groups-service`
- `messages-files-service`

2. Mantener contratos HTTP actuales y extraerlos por dominio.

3. Incorporar mensajería asíncrona (RabbitMQ/Kafka):
- Evento `message_created`
- Evento `message_read`
- Evento `presence_changed`

4. gRPC interno para consultas entre servicios (ej. validación de membresía).

5. Migrar PostgreSQL local a RDS y archivos locales a S3.

6. Desplegar en Kubernetes (EKS) con API Gateway/Ingress.

## Despliegue simple en EC2

```bash
chmod +x scripts/deploy_ec2.sh
./scripts/deploy_ec2.sh /opt/groupsapp
```

El script instala Nginx, crea service systemd y levanta FastAPI con Gunicorn.
