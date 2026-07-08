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
COPY --from=build /app/tsconfig.json ./tsconfig.json
COPY --from=build /app/tsconfig.node.json ./tsconfig.node.json
COPY --from=build /app/package.json ./package.json
# `vite preview` (which serves dist and honors the /api proxy in vite.config.ts)
# needs vite + the config's plugins, which live in devDependencies — install all.
RUN npm install
EXPOSE 5173
CMD ["npx", "vite", "preview", "--host", "--port", "5173"]
