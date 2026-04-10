# ── Build stage ────────────────────────────────────────────────────────────
FROM node:24-alpine AS build

WORKDIR /app

# Install dependencies with a clean, reproducible install
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

# Create the directory tree that vite.config.js resolves outDir to:
#   resolve(__dirname, '../backend/static/dist')
#   __dirname = /app/frontend  →  outDir = /app/backend/static/dist
RUN mkdir -p backend/static

# Copy the rest of the frontend source
COPY frontend/ ./frontend/

ENV VITE_API_BASE=

# Build Vite bundles → /app/backend/static/dist/{assets/…, .vite/manifest.json}
RUN cd frontend && npm run build

# ── Production stage ────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Minimal permission setup for non-root nginx
RUN chown -R nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

COPY --from=build /app/backend/static/dist /usr/share/nginx/html/static/dist

COPY frontend/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/api/health || exit 1

USER nginx
CMD ["nginx", "-g", "daemon off;"]