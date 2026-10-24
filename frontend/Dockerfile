FROM node:22-alpine

WORKDIR /app

# Instala as dependências DENTRO do container (binários do Linux)
COPY package*.json ./
RUN npm install

# Copia o restante do código
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]