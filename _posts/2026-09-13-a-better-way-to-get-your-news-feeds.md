---
layout: post
title: "A Better Way to Get Your News Feeds: Self-Hosting FreshRSS"
date: 2026-09-13
tags: [RSS, FreshRSS, Self-Hosted, Homelab, Proxmox, LXC]
excerpt: "I got tired of letting algorithms decide what tech news I saw, so I self-hosted an RSS reader and curated my own sources into categories instead of trusting a feed algorithm - here's why, and how I built it."
---

I don't want a news feed. I want a reading list.

Every "For You" tab I've used - Twitter, LinkedIn, even Google's own news app - is optimizing for time-on-app, not for keeping me informed. That's not a conspiracy theory, it's just the incentive structure. So a few months back I stopped fighting it and went back to the thing that solved this problem 20 years ago and never actually stopped working: RSS. I just wanted my version of it to be self-hosted and curated by me, not an algorithm.

## Why FreshRSS instead of Feedly/Inoreader

I didn't want my reading list living on someone else's server, being used to build an ad profile, or disappearing behind a paywall the day the company pivots to a subscription model. FreshRSS is open-source, self-hosted, and speaks a handful of standard protocols (its own API plus a Google Reader-compatible API) that basically every RSS client on the planet already knows how to talk to. That compatibility mattered more than any single feature - it meant I wasn't locking myself into one reader's ecosystem to get data out later.

## How I actually deployed it

FreshRSS runs as its own unprivileged Debian LXC container on Proxmox, not a Docker stack - I used the community Proxmox VE helper script (the same `bash -c "$(wget -qLO - .../ct/freshrss.sh)"` pattern I use for a handful of other single-purpose services) to spin up the container, which handles the nginx + PHP-FPM + FreshRSS install in one pass and drops the app in at `/opt/freshrss`. One LXC, one job - I don't want a misbehaving app taking down anything else sharing a host, and a dedicated container is cheap on a hypervisor that already has the headroom.

It's not reachable on a Cloudflare Tunnel like most of my other public-facing apps - it's a CNAME record pointed at my apex domain, which lands on Nginx Proxy Manager (also self-hosted) that reverse-proxies the request the rest of the way to the LXC's internal IP. Same outcome (HTTPS in front of an internal service), different plumbing than the tunnel-based apps.

Updating it is a `git pull` inside the container rather than a `docker compose pull` - which bit me once, because the base LXC template doesn't ship with `git` installed. First update attempt after standing it up just returned `git: command not found`. `apt install -y git`, then the normal fetch/reset/checkout/pull dance, fixed that permanently.

## Curating feeds into categories, not one big pile

The entire point of self-hosting this was to stop treating "news" as one undifferentiated stream. Inside FreshRSS, subscriptions get sorted into categories:

| Category | What's in it |
|---|---|
| IT News Sites | BleepingComputer, Krebs on Security, The Hacker News, The Register |
| Hacking Writeups | Security research blogs, CTF writeups |
| Reddit | A handful of specific subreddits, added via their `.rss` suffix |
| News Sites | General/non-tech sources |

On any given morning, "IT News Sites" is the category doing the actual work - a real pull from it looks like a Cisco Catalyst SD-WAN zero-day writeup next to a BleepingComputer piece on Google's new privacy controls, next to a Register story on a school district's network being left wide open. That's the whole value proposition in one glance: three different outlets, one unread count, zero ranking algorithm deciding which of those three I should care about first.

Each category is its own unread count and its own read/unread state, which is the entire point - I can clear "News Sites" without touching my "IT News Sites" backlog, and a slow week for security writeups doesn't get buried under general news volume.

FreshRSS also ships a **Google Reader-compatible API** alongside its own native API - the same interface protocol that most of the RSS client ecosystem was originally built against, back when Google Reader was still the de facto standard everyone integrated with. That compatibility is part of why I picked it: any client that speaks that protocol (and most do) can authenticate and pull my subscriptions without me writing custom integration code for every device I read on.

## The gotcha that cost me real time: a 403 that isn't what it looks like

FreshRSS started throwing a `403 Login is invalid` error on the web login out of nowhere - the kind of message that reads like a bad password, but wasn't. Since it sits behind a reverse proxy, the actual failure point is almost never FreshRSS's auth logic itself, it's the handshake between FreshRSS and the proxy in front of it:

- FreshRSS's own `trusted_proxies` setting controls whether it trusts the `X-Forwarded-For`/`X-Forwarded-Proto` headers coming from the proxy. If it doesn't, every login attempt looks like it's coming from one single IP (the proxy's), which can trip FreshRSS's own brute-force/rate-limit logic into rejecting valid logins as "invalid."
- Separately, FreshRSS checks the `Referer`/`base_url` on login POSTs as a CSRF guard. If the proxy strips or rewrites that header, or `base_url` in `config.php` doesn't exactly match the externally-facing hostname/scheme, that check fails too - and it produces the exact same generic 403.

Two different plausible causes, same error message, and no way to tell which one you're looking at from the error alone. The actual diagnostic path was pulling `trusted_proxies` and `base_url` straight out of `config.php` and cross-referencing them against the proxy's actual header behavior, rather than guessing and toggling settings one at a time. That's the real lesson here more than any specific fix: a reverse-proxied app with its own app-level trust settings can fail in a way that looks like a credentials problem but is really a "does the app agree with the proxy about what the real client looks like" problem, and the config file - not the login form - is where you go looking.

## Where it stands now

FreshRSS runs quietly in the background, sorted into categories I actually curated instead of an algorithm's guess at my interests. No feed ranking, no "recommended for you," no engagement bait - just headlines from sources I picked, in the order they were published.

That's the whole pitch for self-hosted RSS in 2026: it's not a nostalgia project, it's the last format where the reading list is actually yours.
