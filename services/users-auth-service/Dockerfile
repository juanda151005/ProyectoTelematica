FROM python:3.12-slim

WORKDIR /service

# Copy shared lib first so Docker cache is stable
COPY libs/shared /libs/shared
COPY proto /proto

COPY services/users-auth-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Generate gRPC stubs
ENV PROTO_DIR=/proto
RUN python -m groupsapp_shared.grpc_codegen

COPY services/users-auth-service/app ./app

EXPOSE 8000 50051

CMD ["python", "-m", "app.main"]
