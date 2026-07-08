# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# ---- serve stage ----
FROM node:20-alpine
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/vite.config.ts ./vite.config.ts
COPY --from=build /app/package.json ./package.json
RUN npm install --omit=dev
EXPOSE 5173
# Serve the built SPA. Vite preview honors the /api proxy from vite.config.ts.
CMD ["npx", "vite", "preview", "--host", "--port", "5173"]
