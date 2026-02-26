# Migraciones (Alembic)

Para el MVP, se usa `Base.metadata.create_all()` en startup para simplificar.

En la siguiente iteración:
1. Inicializa Alembic (`alembic init app/migrations`).
2. Configura `sqlalchemy.url` desde `.env`.
3. Genera la migración inicial con autogenerate.
