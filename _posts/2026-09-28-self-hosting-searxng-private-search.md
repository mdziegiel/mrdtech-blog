---
layout: post
title: "Self-hosting SearXNG for Private, Ad‑free Search"
date: 2026-09-28 09:00:00 -0400
categories: homelab privacy
tags: [searxng, search, docker, self-hosted]
description: How to deploy SearXNG — a metasearch engine — behind your reverse proxy for fast, private, ad‑free search.
image: /assets/og/self-hosting-searxng-private-search.png
---

Running someone else’s ad farm isn’t a hobby. SearXNG lets you aggregate results from many engines while keeping your queries and clicks out of their profiles.

What we’ll cover:
- Why SearXNG over “free” search
- One‑file Docker Compose deployment
- Hardening: TLS, auth, abuse protection
- Tuning result backends for speed and signal

Quick start (Docker Compose):

```yaml
version: '3.8'
services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng
    restart: unless-stopped
    environment:
      - SEARXNG_BASE_URL=https://search.example.com/
      - SEARXNG_PORT=8080
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - ./searxng:/etc/searxng:ro
```

Put Nginx/Traefik/Caddy in front with TLS. Rate‑limit POST /search. If you open it to the world, expect bots — pair with CrowdSec or at least sane limits.

Tuning tips:
- Disable slow/low‑signal engines
- Keep a short timeout so lagging engines don’t drag every query
- Prefer text/html engines; fall back to images/videos on demand

Satan approves: you own your search, not the other way around.
