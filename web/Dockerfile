# syntax=docker/dockerfile:1

# Build: Node nur hier; das finale Image enthält nur nginx und die statischen Dateien.
FROM node:24.14-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-fund --no-audit
COPY . .
RUN npm run build

# Runtime: nginx als Non-Root-User (UID 101) auf Port 8080.
FROM nginxinc/nginx-unprivileged:1.30-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 8080
