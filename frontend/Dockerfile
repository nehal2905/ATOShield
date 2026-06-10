# --- build stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
# Use npm install (no committed lockfile is required for this portfolio build).
RUN npm install
COPY . .
RUN npm run build

# --- serve stage ---
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# SPA fallback so client-side routes (React Router) resolve to index.html
RUN printf 'server {\n  listen 80;\n  root /usr/share/nginx/html;\n  location / {\n    try_files $uri $uri/ /index.html;\n  }\n}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
