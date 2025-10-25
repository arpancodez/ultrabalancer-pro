# UltraBalancer Pro - Docker Image
FROM node:18-alpine AS base

# Set working directory
WORKDIR /app

# Install dependencies
FROM base AS dependencies
COPY package*.json ./
RUN npm ci --only=production

# Build stage
FROM base AS build
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM base AS production

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S ultrabalancer -u 1001

# Copy dependencies and built application
COPY --from=dependencies --chown=ultrabalancer:nodejs /app/node_modules ./node_modules
COPY --from=build --chown=ultrabalancer:nodejs /app/dist ./dist
COPY --chown=ultrabalancer:nodejs package*.json ./

# Switch to non-root user
USER ultrabalancer

# Expose the default port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => { process.exit(r.statusCode === 200 ? 0 : 1) })"

# Start the application
CMD ["node", "dist/index.js"]
