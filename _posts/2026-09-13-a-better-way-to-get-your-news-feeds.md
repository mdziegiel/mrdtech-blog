---
layout: post
title: "A Better Way to Get Your News Feeds: Self-Hosting FreshRSS"
date: 2026-09-13
tags: [RSS, FreshRSS, Self-Hosted, Homelab, Docker, Automation]
excerpt: "I got tired of letting algorithms decide what tech news I saw, so I self-hosted an RSS reader, curated my own sources into categories, and wired it directly into my homelab dashboard - here's how the whole thing fits together."
---

I don't want a news feed. I want a reading list.

Every "For You" tab I've used - Twitter, LinkedIn, even Google's own news app - is optimizing for time-on-app, not for keeping me informed. That's not a conspiracy theory, it's just the incentive structure. So a few months back I stopped fighting it and went back to the thing that solved this problem 20 years ago and never actually stopped working: RSS. I just wanted my version of it to be self-hosted, curated, and sitting directly on the dashboard I already look at every morning instead of living in yet another app.

## What I built

Two pieces, not one:

1. **FreshRSS** - a self-hosted RSS/Atom aggregator that pulls from every site and subreddit I actually care about, sorted into categories instead of one undifferentiated firehose.
2. **A dashboard card** on my homelab's [[daily-command-portal]] (DCP) that pulls the top unread headlines out of FreshRSS and puts them in front of me without making me open a separate app.

FreshRSS does the aggregating. My dashboard does the surfacing. Neither one is trying to maximize my engagement.

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

Each category is its own unread count, its own read/unread state, and - more importantly for the second half of this build - its own queryable feed of items. That per-category granularity is what makes the dashboard integration below actually useful instead of just dumping every subscription into one card.

## Getting data out of FreshRSS programmatically

This is where the project got more interesting than "click subscribe a bunch of times."

I wanted my dashboard to show the latest unread items from the IT News Sites category specifically - not a link to go check FreshRSS, an actual list of headlines rendered on the card. FreshRSS's web UI doesn't expose a simple "here's your export URL" button per category, which sent me down a path of clicking through Subscription Management, category gear icons, and the Sharing panel looking for something that wasn't there. None of it was the right answer - the Sharing panel is for pushing individual articles out to services like archive.is, not for exporting a feed, and category settings are read/sort configuration, not an export endpoint.

The actual answer was to stop looking for an export button and use the API instead. FreshRSS ships a **Google Reader-compatible API** - the same interface protocol that half the RSS client ecosystem was originally built against, back when Google Reader was still the de facto standard everyone integrated with. That API supports authenticated, scriptable pulls of unread items filtered by category/tag, which is exactly what a dashboard card needs: a stable, authenticated endpoint instead of scraping HTML.

Getting to a working call meant:

1. Confirming an API password was enabled for my account (separate from the account login password - FreshRSS treats API auth as its own credential you have to explicitly turn on).
2. Authenticating against the Reader API's login endpoint to get an auth token.
3. Calling the stream-items endpoint scoped to the specific category tag, not the whole account.

Conceptually, the flow looks like this:

```text
POST /api/greader.php/accounts/ClientLogin
  -> returns Auth token

GET /api/greader.php/reader/api/0/stream/contents/user/-/label/IT%20News%20Sites
  Authorization: GoogleLogin auth=<token>
  -> returns JSON: unread items in that category
```

That single authenticated GET is the entire integration point. Everything downstream of it is just formatting.

## The dashboard card: server-side fetch, not client-side

My first instinct was to have the dashboard's frontend JavaScript call the FreshRSS API directly from the browser. That's the wrong layer for this. A few reasons:

- The API auth token would have to live in client-side code, visible to anyone poking at the page source.
- Every page load would trigger a fresh authenticated call to FreshRSS, which is unnecessary load for data that doesn't change minute-to-minute.
- CORS and reverse-proxy header behavior get involved for no good reason when the server hosting the dashboard can just make the call itself.

So the fetch lives entirely server-side, in the DCP backend, with a simple in-memory cache:

```js
let cache = { items: null, fetchedAt: 0 };
const CACHE_TTL_MS = 15 * 60 * 1000; // 15 minutes

async function getItNews() {
  const now = Date.now();
  if (cache.items && (now - cache.fetchedAt) < CACHE_TTL_MS) {
    return cache.items;
  }

  const token = await authenticateToFreshRSS();
  const items = await fetchCategoryItems(token, 'IT News Sites');

  cache = { items, fetchedAt: now };
  return items;
}
```

Fifteen minutes is deliberately not real-time. IT news doesn't need per-second freshness, and I'd rather have one authenticated call every 15 minutes serving every page load in that window than one call per page load hammering FreshRSS every time I glance at the dashboard.

The frontend just asks its own backend for `/api/it-news` and renders whatever comes back - title, source, link. It has no idea FreshRSS exists.

## The gotcha that actually cost me time: reverse proxy headers

Weeks after this was working, FreshRSS started returning a `403 Login is invalid` error on the *web login* (unrelated to the API integration, but same box). Root cause was the reverse proxy path, not FreshRSS itself:

- FreshRSS sits behind an Nginx-based reverse proxy over HTTPS.
- FreshRSS's own `trusted_proxies` setting determines whether it trusts `X-Forwarded-For`/`X-Forwarded-Proto` headers from the proxy.
- If that's misconfigured, FreshRSS can either misidentify client IPs (breaking its own rate limiter) or fail a Referer/Origin check because the scheme it sees internally doesn't match the externally-facing HTTPS URL.

The fix was making sure `trusted_proxies` in FreshRSS's config actually included the proxy's internal address, and that the proxy was forwarding `X-Forwarded-Proto: https` correctly so FreshRSS's own CSRF/base-URL logic didn't think it was being accessed over plain HTTP. Anything self-hosted behind a reverse proxy with its own app-level trust settings will bite you the same way eventually - the app has to agree with the proxy about what "the real client" looks like, or its own security checks turn into false positives against you.

## Where it stands now

FreshRSS runs quietly in the background, sorted into categories I actually curated instead of an algorithm's guess at my interests. The IT News Sites category feeds straight into a dashboard card via the Google Reader-compatible API, refreshed every 15 minutes, with zero client-side exposure of the API credential. No feed ranking, no "recommended for you," no engagement bait - just headlines from sources I picked, in the order they were published.

That's the whole pitch for self-hosted RSS in 2026: it's not a nostalgia project, it's the last format where the reading list is actually yours.
