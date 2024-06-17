FROM node:20-slim 
WORKDIR /app

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

COPY . .

RUN pnpm install
RUN pnpm run build
RUN pnpm i -g serve


CMD [ "serve", "dist" ]
