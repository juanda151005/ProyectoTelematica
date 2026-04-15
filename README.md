# GroupsApp — Sistema de Mensajería Distribuida

> **ST0263 Tópicos Especiales en Telemática / SI3007 Sistemas Distribuidos (2026-1)**  
> Proyecto 1 — WhatsApp/Telegram-like messaging sobre arquitectura de microservicios.

GroupsApp entrega **dos implementaciones coordinadas**, una por cada uno de los primeros dos criterios de la rúbrica:

1. **Monolito** (criterio 1, 20 %) — FastAPI original en [`app/`](app/), desplegable en una sola EC2 con [`scripts/deploy_ec2.sh`](scripts/deploy_ec2.sh).
2. **Microservicios distribuidos** (criterios 2–6, 80 %) — cuatro servicios en [`services/`](services/) conectados con REST + gRPC + RabbitMQ, detrás de un API Gateway (Traefik) y desplegables en AWS EKS.

---

## 1. Arquitectura

```
Browser ──HTTP/WS──► Traefik (API Gateway / AWS ALB Ingress)
                         │
         ┌───────────────┼───────────────┬────────────────────┐
         ▼               ▼               ▼                    ▼
  users-auth-svc   groups-svc   messages-files-svc   presence-notif-svc
  (FastAPI+gRPC)  (FastAPI+gRPC)   (FastAPI+gRPC cli)   (FastAPI+WS)
         │               │               │                    │
         ▼               ▼               ▼                    ▼
   users_auth pg    groups pg      messages pg           presence pg

         ── RabbitMQ topic exchange `groupsapp.events` ──
          message.created · message.read · group.member.added ·
          group.member.removed · presence.changed · user.created

         ── Consul (service discovery + KV config + health) ──
```

### Microservicios

| Servicio | Responsabilidad | BD propia | Puertos |
|---|---|---|---|
| `users-auth-service` | Registro, login, JWT, perfiles | `users_auth` | HTTP 8000 · gRPC 50051 |
| `groups-service` | Grupos, membresías, DMs | `groups` | HTTP 8000 · gRPC 50052 |
| `messages-files-service` | Mensajes, receipts, archivos | `messages` | HTTP 8000 |
| `presence-notifications-service` | Presencia + WebSocket fan-out | `presence` | HTTP 8000 (+ WS) |

### Comunicaciones (criterio 4 — 20 %)

| Tipo | Tecnología | Uso |
|---|---|---|
| **REST** | FastAPI | APIs externas (cliente → gateway → servicio) |
| **gRPC** | grpc.io | `IsMember`, `GetGroupMembers`, `ValidateToken`, `GetUser`, `FindByUsername`, `GetUsersBatch` |
| **MOM** | RabbitMQ (topic `groupsapp.events`) | `message.created`, `message.read`, `group.member.added/removed`, `presence.changed`, `user.created` |
| **WebSocket** | FastAPI/websockets | Push tiempo real: nuevos mensajes, notificaciones, presencia |

### Otros aspectos de sistema distribuido (criterio 5 — 20 %)

- **Service discovery / coordinación**: Consul (auto-registro + health-check HTTP) + DNS de Kubernetes en EKS.
- **Configuración**: env vars en compose, `ConfigMap` + `Secret` en k8s.
- **Escalabilidad / HA**: HPA por servicio (CPU 70 %, 2–8 réplicas), servicios stateless, `aio-pika` `RobustConnection`, `readiness`/`liveness` probes.
- **Pruebas**: [`tests/test_integration_microservices.py`](tests/test_integration_microservices.py) smoke end-to-end.
- **Seguridad**: JWT HS256 stateless (verificado localmente en cada servicio), bcrypt para contraseñas, validación de membresía por gRPC en cada envío.
- **Logs/métricas**: logging estructurado por servicio, endpoints `/health`, Traefik access logs + dashboard.

---

## 2. Correr localmente

### Requisitos

- **Docker Desktop** corriendo (con al menos 4 GB de RAM asignados). En macOS: `brew install --cask docker-desktop && open -a Docker`.
- Puertos libres en el host: `80`, `5432`, `5672`, `8080`, `8500`, `15672`.

### Instalación

```bash
git clone -b feature/microservices-refactor https://github.com/juanda151005/ProyectoTelematica.git
cd ProyectoTelematica
chmod +x deploy/postgres/init-multiple-dbs.sh
docker compose -f deploy/docker-compose.yml up -d --build
```

La primera vez tarda 3–5 min mientras construye las imágenes. Luego el stack queda corriendo en segundo plano.

### Acceso

| Endpoint | URL |
|---|---|
| **App web** | <http://localhost> |
| API Gateway | <http://localhost/api/v1/...> |
| Traefik Dashboard | <http://localhost:8080> |
| RabbitMQ UI | <http://localhost:15672> (`guest` / `guest`) |
| Consul UI | <http://localhost:8500> |

Abre <http://localhost>, regístrate con usuario y contraseña, crea un grupo y empieza a chatear.

### Comandos útiles

```bash
# Estado de los 9 contenedores
docker compose -f deploy/docker-compose.yml ps

# Logs en vivo de un servicio
docker compose -f deploy/docker-compose.yml logs -f users-auth-service

# Detener manteniendo los datos
docker compose -f deploy/docker-compose.yml down

# Empezar de cero (borra BDs y uploads)
docker compose -f deploy/docker-compose.yml down -v
```

### Smoke test

```bash
pip install httpx pytest
pytest tests/test_integration_microservices.py -v
```

---

## 3. Desplegar en AWS

### Monolito (criterio 1 — 20 %)

```bash
scp -r . ec2-user@<ec2>:/opt/groupsapp
ssh ec2-user@<ec2> 'cd /opt/groupsapp && chmod +x scripts/deploy_ec2.sh && sudo ./scripts/deploy_ec2.sh /opt/groupsapp'
```

### Microservicios en EKS

```bash
export REGISTRY=<account>.dkr.ecr.<region>.amazonaws.com
for svc in users-auth groups messages-files presence-notifications; do
  docker build -t $REGISTRY/groupsapp-$svc:latest -f services/$svc-service/Dockerfile .
  docker push $REGISTRY/groupsapp-$svc:latest
done

# Sustituye REGISTRY/ en deploy/k8s/40-services.yaml y aplica:
kubectl apply -f deploy/k8s/
```

`deploy/k8s/50-ingress.yaml` crea un **AWS ALB** (ingress class `alb`) satisfaciendo "Ingress con balanceador de cargas". HPAs y réplicas cubren "Autoescalado y HA".

---

## 4. Layout del repositorio

```
ProyectoTelematica/
├── app/                                  Monolito FastAPI (criterio 1)
├── static/                               Frontend estático (servido por Nginx detrás del gateway)
├── services/
│   ├── users-auth-service/
│   ├── groups-service/
│   ├── messages-files-service/
│   └── presence-notifications-service/
├── libs/shared/groupsapp_shared/         Lib común (eventos, JWT, logging, Consul, codegen gRPC)
├── proto/                                Contratos gRPC (.proto)
├── gateway/traefik/                      Configuración Traefik
├── deploy/
│   ├── docker-compose.yml                Stack local completo
│   ├── postgres/init-multiple-dbs.sh     Crea las 4 BDs al arrancar Postgres
│   └── k8s/                              Manifests para EKS
├── tests/                                Tests end-to-end
├── scripts/deploy_ec2.sh                 Despliegue monolito EC2
└── README.md
```

---

## 5. Mapeo a la rúbrica

| # | Criterio | Peso | Cómo lo cumplimos |
|---|---|---|---|
| 1 | Aplicación monolítica funcional en AWS | 20 % | [`app/`](app/) + [`scripts/deploy_ec2.sh`](scripts/deploy_ec2.sh) |
| 2 | Diseño arquitectónico escalable + despliegue | 20 % | [`deploy/k8s/`](deploy/k8s/) + HPA + Traefik/ALB Ingress |
| 3 | Diseño e implementación de datos | 20 % | 4 BDs Postgres independientes por servicio, volúmenes persistentes, archivos en PVC/S3 |
| 4 | Comunicaciones remotas REST + gRPC + MOM | 20 % | FastAPI (REST), [`proto/*.proto`](proto/) (gRPC), [`groupsapp_shared.events`](libs/shared/groupsapp_shared/events.py) (RabbitMQ topic) |
| 5 | Otros aspectos SD | 20 % | Consul (coordinación+discovery), ConfigMap+Secret (config), HPA (escalabilidad), tests, JWT+bcrypt |
| 6 | App distribuida escalable funcional | 20 % | 4 servicios, ≥2 réplicas c/u, HPA, LB, HA |

## 6. Endpoints del API (via gateway)

- `POST /api/v1/auth/register` · `POST /api/v1/auth/login` · `POST /api/v1/auth/token`
- `GET  /api/v1/users/me` · `GET /api/v1/users/{id}` · `GET /api/v1/users?q=`
- `POST /api/v1/groups` · `GET /api/v1/groups` · `POST /api/v1/groups/dm`
- `POST /api/v1/groups/{id}/members` · `GET /api/v1/groups/{id}/members` · `DELETE /api/v1/groups/{id}/members/{uid}` · `PUT /api/v1/groups/{id}/members/{uid}/role`
- `POST /api/v1/groups/{id}/messages` · `GET /api/v1/groups/{id}/messages`
- `POST /api/v1/messages/file` · `GET /api/v1/messages/unread-counts`
- `GET  /api/v1/users/{id}/presence` · `GET /api/v1/presence/{id}`
- `WS   /ws/groups/{id}?token=<JWT>` · `WS /ws/notifications?token=<JWT>`
- `GET  /uploads/{file}`

---

## 7. Entregables

1. **Informe técnico (PDF)** — `GroupsApp_Arquitectura.pdf`.
2. **Repositorio GitHub** — este repo.
3. **Video demo** — por grabar (10–15 min).
4. **Aplicación desplegada en nube** — ver sección 3.
