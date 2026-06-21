FROM node:20-alpine

WORKDIR /app

# Copy package configurations
COPY package*.json ./
RUN npm install

# Copy application files
COPY . .

# Disable Next.js anonymous telemetry
ENV NEXT_TELEMETRY_DISABLED=1

EXPOSE 3000

# Start in development mode for faster hot-reloading
CMD ["npm", "run", "dev"]
