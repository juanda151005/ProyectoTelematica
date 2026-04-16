FROM python:3.12-slim

WORKDIR /service

COPY libs/shared /libs/shared
COPY proto /proto

COPY services/groups-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV PROTO_DIR=/proto
RUN python -m groupsapp_shared.grpc_codegen

COPY services/groups-service/app ./app

EXPOSE 8000 50052

CMD ["python", "-m", "app.main"]
