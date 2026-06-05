FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install --frozen-lockfile || npm install

COPY . .

ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ARG VITE_WS_URL=ws://localhost:8888

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_URL=$VITE_WS_URL

RUN npm run build

# Production stage — nginx serving static files
FROM nginx:1.25-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
