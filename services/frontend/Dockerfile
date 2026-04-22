# ---- Frontend Dockerfile ----
# Build the GroupsApp static frontend into an Nginx container.
# Place this file at: services/frontend/Dockerfile
# Build context must be the repo root:
#   docker build -t REGISTRY/groupsapp-frontend:latest -f services/frontend/Dockerfile .

FROM nginx:1.27-alpine

# Copy static assets
COPY static/ /usr/share/nginx/html/static/
COPY static/index.html /usr/share/nginx/html/index.html

# Custom nginx config: serve static, proxy nothing (API goes through ALB)
COPY services/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
