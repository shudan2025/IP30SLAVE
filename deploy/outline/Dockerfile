ARG APP_PATH=/opt/outline
ARG OUTLINE_TAG=v1.12.0
ARG OUTLINE_COMMIT=09f11188b87b0220fa318dfa6fdd0fa9772195dd

FROM node:26.12.1 AS build

ARG APP_PATH
ARG OUTLINE_TAG
ARG OUTLINE_COMMIT
WORKDIR ${APP_PATH}

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates cmake git \
    && rm -rf /var/lib/apt/lists/*

RUN git init . \
    && git remote add origin https://github.com/outline/outline.git \
    && git fetch --depth 1 origin "refs/tags/${OUTLINE_TAG}" \
    && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "${OUTLINE_COMMIT}"

COPY patch-outline-base-path.mjs /tmp/patch-outline-base-path.mjs
RUN node /tmp/patch-outline-base-path.mjs ${APP_PATH}/app/utils/history.ts

ENV NODE_OPTIONS="--max-old-space-size=24000"

RUN npm install -g corepack \
    && corepack enable \
    && yarn install --immutable --network-timeout 1000000 \
    && yarn build \
    && yarn workspaces focus --production \
    && yarn cache clean

FROM node:26.12.1-slim AS runner

ARG APP_PATH
WORKDIR ${APP_PATH}

ENV NODE_ENV=production
ENV MALLOC_ARENA_MAX=2
ENV FILE_STORAGE_LOCAL_ROOT_DIR=/var/lib/outline/data

RUN addgroup --gid 1001 nodejs \
    && adduser --uid 1001 --ingroup nodejs nodejs \
    && mkdir -p /var/lib/outline \
    && chown -R nodejs:nodejs /var/lib/outline \
    && chown -R nodejs:nodejs ${APP_PATH} \
    && apt-get update \
    && apt-get install -y --no-install-recommends wget \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build --chown=nodejs:nodejs ${APP_PATH}/build ./build
COPY --from=build --chown=nodejs:nodejs ${APP_PATH}/server ./server
COPY --from=build --chown=nodejs:nodejs ${APP_PATH}/public ./public
COPY --from=build --chown=nodejs:nodejs ${APP_PATH}/.sequelizerc ./.sequelizerc
COPY --from=build --chown=nodejs:nodejs ${APP_PATH}/node_modules ./node_modules
COPY --from=build --chown=nodejs:nodejs ${APP_PATH}/package.json ./package.json
COPY --from=build --chown=nodejs:nodejs ${APP_PATH}/LICENSE ./LICENSE

RUN mkdir -p "$FILE_STORAGE_LOCAL_ROOT_DIR" \
    && chown -R nodejs:nodejs "$FILE_STORAGE_LOCAL_ROOT_DIR" \
    && chmod 1777 "$FILE_STORAGE_LOCAL_ROOT_DIR"

VOLUME /var/lib/outline/data

USER nodejs

HEALTHCHECK --interval=1m CMD wget -qO- "http://localhost:${PORT:-3000}/_health" | grep -q "OK" || exit 1

EXPOSE 3000
CMD ["node", "build/server/index.js"]
