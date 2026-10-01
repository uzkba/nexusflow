FROM node:20-alpine

WORKDIR /app

# Copia os arquivos de configuração
COPY package.json ./

# Como você já rodou o npm install no Windows, copiamos a pasta inteira já pronta
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]