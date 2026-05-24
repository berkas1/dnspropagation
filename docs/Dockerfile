FROM debian:bookworm-slim AS builder

ARG HUGO_VERSION=0.161.1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL \
       "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_linux-amd64.tar.gz" \
       | tar -xz -C /usr/local/bin hugo

WORKDIR /site

COPY . .

# Clone the hugo-book theme instead of using a git submodule
RUN git clone --depth=1 https://github.com/alex-shpak/hugo-book themes/hugo-book

ARG BASE_URL="/"
RUN hugo --minify --baseURL "$BASE_URL"

FROM nginx:alpine
COPY --from=builder /site/public /usr/share/nginx/html
EXPOSE 80
