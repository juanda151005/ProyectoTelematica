FROM python:3.12-slim

WORKDIR /service

COPY libs/shared /libs/shared
COPY proto /proto

COPY services/presence-notifications-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV PROTO_DIR=/proto
RUN python -m groupsapp_shared.grpc_codegen

COPY services/presence-notifications-service/app ./app

EXPOSE 8000

CMD ["python", "-m", "app.main"]
