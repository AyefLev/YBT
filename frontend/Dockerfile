FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY index.html tsconfig.json vite.config.ts ./
COPY src ./src

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
