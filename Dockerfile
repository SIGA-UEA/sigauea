# Site do SIGA UEA (Next.js).
# API_URL entra no build porque os rewrites de next.config.ts são lidos nessa hora.
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG API_URL=http://api:8000
ENV API_URL=$API_URL
RUN npm run build

FROM node:24-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/package.json /app/package-lock.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next
COPY --from=build /app/next.config.ts ./
EXPOSE 3000
CMD ["npm", "start"]
