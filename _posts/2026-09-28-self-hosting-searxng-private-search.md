---
layout: post
title: "Replacing Google and Bing Search: Self-Hosting SearXNG"
date: 2026-09-28
excerpt: "Chrome and Edge are really front ends for Google and Bing. I couldn't swap the browser with one container, but I could swap what sits behind the address bar - here's how I built it and what it actually buys you."
og_image: /assets/og/self-hosting-searxng-private-search.svg
og_slug: self-hosting-searxng-private-search
image:
  path: /assets/og/self-hosting-searxng-private-search.svg
  width: 1200
  height: 630
  alt: Replacing Google and Bing Search - Self-Hosting SearXNG branded social preview image
tags:
  - SearXNG
  - Privacy
  - Self-Hosted
  - Docker
  - Homelab
---

Let's get the terminology out of the way first, because it matters.

SearXNG is not a browser. It cannot replace Chrome or Edge, and anyone who tells you a single container does is selling something.

What it replaces is the part of those browsers that most people never think about: the default search engine. Chrome points the address bar at Google. Edge points it at Bing. Every query you type goes to a company whose business is knowing what you typed. The browser is the delivery mechanism. The search box is the product.

SearXNG lets me keep that box and swap out everything behind it.

## 1. What SearXNG actually is

SearXNG is a self-hosted metasearch engine. When you run a query, it fans that query out to multiple upstream engines, strips out the tracking, merges and de-duplicates the results, and hands you one clean page.

- No account, no search history tied to an identity.
- No ads, no sponsored results injected into the first page.
- Results aggregated from several engines instead of one company's ranking.
- Outbound requests come from the SearXNG server, not from your device.
- A JSON output mode, which turns out to be the sleeper feature. More on that below.

It is open source, actively maintained, and it runs comfortably in a single Docker container.

Useful references:

- [SearXNG documentation](https://docs.searxng.org/)
- [SearXNG container install notes](https://docs.searxng.org/admin/installation-docker.html)

## 2. Why I built my own instead of using a public instance

There are public SearXNG instances. They are fine for a quick test. They are not what I want as a default.

| Option | Upside | Downside |
|---|---|---|
| Public instance | Zero setup | You trust an unknown operator with every query, and uptime and quality vary wildly |
| Self-hosted, LAN only | Full control, no third-party operator, scriptable | You own the patching and upstream breakage |
| Self-hosted, exposed behind auth | Works away from home | More attack surface, needs a real access layer in front |

Using a public instance just moves the diary from Google to a stranger. Running my own means the only party who sees my queries is me, plus the upstream engines, which I'll get to in the tradeoffs section because it's the part people gloss over.

## 3. The build

The whole thing is one container on my Docker host. Addresses below are placeholders, not my real network.

```text
Client devices / scripts
        |
        | HTTP (LAN only)
        v
SearXNG container
10.0.0.20:8088
        |
        | outbound queries, tracking stripped
        v
Upstream search engines
```

### Config file

I keep the settings file on the host and mount it read-only. Container config that lives inside the container is config you lose the next time you recreate it.

```yaml
use_default_settings: true

server:
  secret_key: "generate-a-long-random-value"
  limiter: false
  bind_address: "0.0.0.0"

search:
  formats:
    - html
    - json
```

Notes on that file:

- `use_default_settings: true` inherits the maintained defaults so I only override what I care about.
- The `secret_key` must be changed from the default. Generate it, don't invent it.
- `limiter: false` is acceptable here only because the instance is LAN-only. If you ever expose it, turn the limiter on and put authentication in front.
- `json` under `formats` is what enables the API mode. It is off by default, and requests for it will return a 403 until you enable it.

### Run it

```bash
docker run -d \
  --name searxng \
  --restart unless-stopped \
  -p 10.0.0.20:8088:8080 \
  -v /opt/searxng/settings.yml:/etc/searxng/settings.yml:ro \
  searxng/searxng:latest
```

The detail worth calling out is the port binding. I bind to the LAN interface address explicitly instead of publishing on every interface. My first deployment was bound to `127.0.0.1` only, which is the safe starting point, and I widened it to the LAN address once I had confirmed it worked and knew exactly which hosts needed to reach it.

### Verify it

```bash
docker ps --format '{{.Names}} {{.Ports}}' | grep searx
curl -sS 'http://10.0.0.20:8088/search?q=test&format=json' | head -c 500
```

If the JSON call returns results, the container, the port, and the format setting are all correct. If it returns a 403, you forgot `json` in the formats list.

## 4. Making it the default in a browser

This is where Chrome and Edge come back in. You are not replacing them, you are pointing them somewhere else.

Both browsers let you add a custom search engine and set it as default. Use this URL template:

```text
http://10.0.0.20:8088/search?q=%s
```

In Chrome and Edge that lives under the search engine management settings. Add a new site search entry, paste the URL, and set it as default. In managed environments, both browsers also support policy-based default search provider settings, which is the right approach if you're doing this at scale through Intune or Group Policy rather than clicking through settings on each machine.

That gives you a second decision to make:

| Browser | What it still does |
|---|---|
| Chrome / Edge with SearXNG as default | Search queries stay off Google/Bing, but the browser keeps its own sync, telemetry, and account features |
| A privacy-focused browser with SearXNG as default | Removes the browser-level telemetry too, at the cost of losing some ecosystem integration |

That first row is the honest limit. Changing the search engine does not stop Chrome from being Chrome. If your goal is to stop feeding Google, the search box is one channel. Sync, safe browsing lookups, and telemetry are others.

## 5. The feature nobody markets: it's an API

The reason SearXNG stayed in my stack is not the browser use. It's the JSON output.

I run a voice assistant and a set of lookup scripts on my homelab, and they need web search. The obvious options are commercial search APIs that want an account, an API key, and a billing relationship, or scraping a search page and hoping the markup doesn't change.

SearXNG gives me a third option. My scripts send a request, they get structured JSON back, and there's no key to manage, rotate, or leak.

```bash
curl -sS 'http://10.0.0.20:8088/search?q=your+query&format=json'
```

In practice my voice assistant uses SearXNG as the primary search path and falls back to DuckDuckGo only if SearXNG errors, times out, or returns nothing. That fallback logic needs one thing that is easy to get wrong: log when the fallback fires. A bare `except: pass` around the primary call means SearXNG can be completely broken while everything looks fine, because the fallback quietly answers every query. If you build a fallback, make the failure visible.

## 6. The benefits, stated honestly

What you actually get:

- **No query profile tied to your identity.** There is no account and no history stored against you.
- **No ads or sponsored placement** in the results you see.
- **Multiple sources merged**, instead of one company's ranking deciding what page one looks like.
- **Your IP is not what upstream engines see.** They see the server.
- **Automation-friendly.** Structured JSON, no API key, no vendor billing.
- **You control retention.** Logging is whatever you configure it to be.
- **It fits the rest of the stack.** DNS filtering, access control, and monitoring all apply to it like any other service.

## 7. The tradeoffs, also stated honestly

This is the section that separates a useful post from marketing.

| Tradeoff | Reality |
|---|---|
| Upstream engines still see the query | SearXNG hides *you*, not the query. Google or Bing still receives the search terms from your server. You've removed the link to you, not the search itself. |
| Result quality varies | Aggregation helps, but it is not always as good as Google for niche or local queries |
| Upstream engines can block you | Engines rate-limit or CAPTCHA automated traffic, and results from a blocked engine silently disappear |
| You own the maintenance | Patching the container and fixing engines that change their markup is now your job |
| It only covers search | The browser's other data flows are untouched |
| Exposure risk | A public search proxy attracts abuse, so LAN-only or authenticated access is the safe default |

If you need the full privacy story, pair it with a browser you trust and a DNS layer that filters at the network level. SearXNG is one layer, not the whole answer.

## 8. Closing

SearXNG doesn't replace Chrome or Edge, and I'd rather say that up front than let the title imply otherwise.

What it does is take back the one thing those browsers are quietly designed to route through somebody else: the question you're asking.

One container, one config file, a LAN-bound port. In exchange, no ads, no search history attached to me, and a search API my own tooling can use without a key.

Boring. Controlled. Mine.
