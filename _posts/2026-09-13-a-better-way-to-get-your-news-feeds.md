---
layout: post
title: "A Better Way to Get Your News Feeds: Self-Hosting FreshRSS"
date: 2026-09-13
tags: [RSS, FreshRSS, Self-Hosted, Homelab, Proxmox, LXC]
excerpt: "I got tired of letting algorithms decide what tech news I saw. So I self-hosted an RSS reader and sorted my own sources into categories - here's why, and how I built it."
---

I don't want a news feed. I want a reading list.

Twitter, LinkedIn, Google's own news app - every "For You" tab I've used is optimizing for time-on-app, not for keeping me informed. That's just how the incentives work. So a few months back I went back to the thing that solved this problem 20 years ago and never actually stopped working: RSS. My version of it needed to be self-hosted, and curated by me instead of an algorithm.

## Why FreshRSS over Feedly or Inoreader

I didn't want my reading list living on someone else's server, feeding an ad profile, or disappearing behind a paywall the day the company changes its business model. FreshRSS is open-source and self-hosted, and it speaks a couple of standard protocols - its own API and a Google Reader-compatible one - that most RSS clients already know how to talk to. That compatibility mattered to me more than any single feature in the app itself; it meant I wasn't locking my subscriptions into one company's ecosystem.

## How I actually deployed it

FreshRSS runs in its own unprivileged Debian LXC on Proxmox, not a Docker stack. I used the community Proxmox VE helper script - the same `bash -c "$(wget -qLO - .../ct/freshrss.sh)"` pattern I use for a handful of other single-purpose services - which handles the nginx, PHP-FPM, and FreshRSS install in one shot and drops the app at `/opt/freshrss`. One container, one job. I'd rather a misbehaving app take down nothing but itself, and a dedicated LXC costs almost nothing on a hypervisor that already has the headroom.

It doesn't sit behind a Cloudflare Tunnel like most of my public-facing apps do. A CNAME points at my apex domain, which lands on Nginx Proxy Manager, and NPM reverse-proxies the rest of the way to the LXC's internal address. Different plumbing, same result: HTTPS in front of an internal service.

Updating it means `git pull` inside the container instead of `docker compose pull`, which caught me off guard the first time - the base LXC template doesn't ship with `git`. My first update attempt just returned `git: command not found`. Installed git, ran the normal fetch/reset/checkout/pull sequence, and it's been fine ever since.

## Curating feeds into categories instead of one big pile

Everything gets sorted into a handful of categories:

| Category | What's in it |
|---|---|
| IT News Sites | BleepingComputer, Krebs on Security, The Hacker News, The Register |
| Hacking Writeups | Security research blogs, CTF writeups |
| Reddit | A handful of specific subreddits, added via their `.rss` suffix |
| News Sites | General/non-tech sources |

IT News Sites is the one doing the real work. A typical pull might put a Cisco Catalyst SD-WAN zero-day writeup next to a BleepingComputer piece on Google's privacy controls and a Register story about a school district leaving its network wide open. Three outlets, one unread count, nothing deciding for me which of the three matters more.

The category split also means my unread counts stay honest. I can clear News Sites without touching the IT backlog, and a quiet week for security writeups doesn't get buried under general news volume.

FreshRSS also exposes that Google Reader-compatible API I mentioned - the same protocol most of the RSS client world was originally built against, back when Google Reader was the standard everyone integrated with. Any client that speaks it can authenticate and pull my subscriptions with no custom integration work on my end, on whatever device I happen to be reading from.

## A 403 that wasn't what it looked like

At some point FreshRSS started throwing a `403 Login is invalid` on the web login, out of nowhere. Reads like a bad password. Wasn't one. Sitting behind a reverse proxy, the failure almost never traces back to FreshRSS's actual auth logic - it's the handshake between FreshRSS and whatever's in front of it.

Two things can cause the exact same error here. FreshRSS's `trusted_proxies` setting decides whether it trusts the `X-Forwarded-For`/`X-Forwarded-Proto` headers coming from the proxy; if it doesn't, every login attempt looks like it's coming from the same single IP, and that can trip the built-in rate limiter into rejecting good logins. Separately, FreshRSS checks the `Referer` and `base_url` on login as a CSRF guard - if the proxy strips that header, or `base_url` in `config.php` doesn't exactly match the public hostname and scheme, that check fails too, with the identical 403.

No way to tell which one you're looking at from the error message alone. The actual diagnostic path was pulling `trusted_proxies` and `base_url` straight out of `config.php` and comparing them against what the proxy was actually sending, rather than flipping settings and hoping. Worth remembering for any reverse-proxied app with its own trust settings: when it looks like a credentials problem, check whether the app and the proxy agree on what "the real client" even looks like. The config file is where that answer lives, not the login form.

## Where it stands now

FreshRSS runs quietly in the background, sorted into categories I actually chose instead of ones an algorithm guessed at. No ranking, no "recommended for you," no engagement bait - just headlines from sources I picked, in the order they were published. Twenty years on, it's still the format where the reading list is actually mine.
