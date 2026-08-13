# Build the React+TS+Arco app, then serve the static bundle behind nginx which
# also reverse-proxies /api to the backend container (production integration,
# replacing the Vite dev proxy used locally).
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
