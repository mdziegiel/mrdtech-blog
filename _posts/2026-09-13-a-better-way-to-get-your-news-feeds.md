---
layout: post
title: "A Better Way to Get Your News Feeds: Self-Hosting FreshRSS"
date: 2026-09-13
tags: [RSS, FreshRSS, Self-Hosted, Homelab, Docker, Automation]
excerpt: "I got tired of letting algorithms decide what tech news I saw, so I self-hosted an RSS reader and curated my own sources into categories instead of trusting a feed algorithm - here's why, and how I built it."
---

I don't want a news feed. I want a reading list.

Every "For You" tab I've used - Twitter, LinkedIn, even Google's own news app - is optimizing for time-on-app, not for keeping me informed. That's not a conspiracy theory, it's just the incentive structure. So a few months back I stopped fighting it and went back to the thing that solved this problem 20 years ago and never actually stopped working: RSS. I just wanted my version of it to be self-hosted and curated by me, not an algorithm.

## Why FreshRSS instead of Feedly/Inoreader

I didn't want my reading list living on someone else's server, being used to build an ad profile, or disappearing behind a paywall the day the company pivots to a subscription model. FreshRSS is open-source, self-hosted, and speaks a handful of standard protocols (its own API plus a Google Reader-compatible API) that basically every RSS client on the planet already knows how to talk to. That compatibility mattered more than any single feature - it meant I wasn't locking myself into one reader's ecosystem to get data out later.

## The stack

FreshRSS runs as a container behind my existing reverse proxy, reachable at a dedicated subdomain rather than a raw port:

```yaml
services:
  freshrss:
    image: freshrss/freshrss:latest
    container_name: freshrss
    environment:
      - TZ=America/New_York
    volumes:
      - freshrss-data:/var/www/FreshRSS/data
      - freshrss-extensions:/var/www/FreshRSS/extensions
    restart: unless-stopped

volumes:
  freshrss-data:
    external: true
  freshrss-extensions:
    external: true
```

No exposed host port - it sits on the internal Docker network, and Nginx Proxy Manager routes `rss.example.com` to the container by name. That's the same pattern I use for most internal web apps: nothing gets a host port unless something outside Docker needs to reach it directly.

## Curating feeds into categories, not one big pile

The entire point of self-hosting this was to stop treating "news" as one undifferentiated stream. Inside FreshRSS, subscriptions get sorted into categories:

| Category | What's in it |
|---|---|
| IT News Sites | BleepingComputer, Krebs on Security, The Hacker News |
| Hacking Writeups | Security research blogs, CTF writeups |
| Reddit | A handful of specific subreddits, added via their `.rss` suffix |
| News Sites | General/non-tech sources |

Each category is its own unread count and its own read/unread state, which is the entire point - I can clear "News Sites" without touching my "IT News Sites" backlog, and a slow week for security writeups doesn't get buried under general news volume.

FreshRSS also ships a **Google Reader-compatible API** alongside its own native API - the same interface protocol that most of the RSS client ecosystem was originally built against, back when Google Reader was still the de facto standard everyone integrated with. That compatibility is part of why I picked it: any client that speaks that protocol (and most do) can authenticate and pull my subscriptions without me writing custom integration code for every device I read on.

## The gotcha that actually cost me time: reverse proxy headers

Weeks after this was working, FreshRSS started returning a `403 Login is invalid` error on the web login. Root cause was the reverse proxy path, not FreshRSS itself:

- FreshRSS sits behind an Nginx-based reverse proxy over HTTPS.
- FreshRSS's own `trusted_proxies` setting determines whether it trusts `X-Forwarded-For`/`X-Forwarded-Proto` headers from the proxy.
- If that's misconfigured, FreshRSS can either misidentify client IPs (breaking its own rate limiter) or fail a Referer/Origin check because the scheme it sees internally doesn't match the externally-facing HTTPS URL.

The fix was making sure `trusted_proxies` in FreshRSS's config actually included the proxy's internal address, and that the proxy was forwarding `X-Forwarded-Proto: https` correctly so FreshRSS's own CSRF/base-URL logic didn't think it was being accessed over plain HTTP. Anything self-hosted behind a reverse proxy with its own app-level trust settings will bite you the same way eventually - the app has to agree with the proxy about what "the real client" looks like, or its own security checks turn into false positives against you.

## Where it stands now

FreshRSS runs quietly in the background, sorted into categories I actually curated instead of an algorithm's guess at my interests. No feed ranking, no "recommended for you," no engagement bait - just headlines from sources I picked, in the order they were published.

That's the whole pitch for self-hosted RSS in 2026: it's not a nostalgia project, it's the last format where the reading list is actually yours.
