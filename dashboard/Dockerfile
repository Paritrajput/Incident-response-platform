FROM node:20-alpine

WORKDIR /app

COPY dashboard/package*.json ./
RUN npm install

COPY dashboard .

RUN npm run build

EXPOSE 80
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "80"]
