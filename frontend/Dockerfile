# ── Build stage ────────────────────────────────────────────────────────────
FROM node:24-alpine AS build

WORKDIR /app

# Copy frontend package files and install dependencies
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

# Create the output directory that vite.config.js targets
RUN mkdir -p backend/static

# Copy frontend source
COPY frontend/ ./frontend/

ENV VITE_API_BASE=

# Build — vite.config.js outputs to ../backend/static/dist relative to frontend/
RUN cd frontend && npm run build

# ── Production stage ────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Security: run as non-root
RUN chown -R nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

# Copy built assets from build stage
COPY --from=build /app/backend/static/dist /usr/share/nginx/html

# Copy nginx configuration
COPY frontend/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

USER nginx
CMD ["nginx", "-g", "daemon off;"]