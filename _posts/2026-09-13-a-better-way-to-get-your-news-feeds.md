---
layout: post
title: "A Better Way to Get Your News Feeds: Self-Hosting FreshRSS"
date: 2026-09-13
tags: [RSS, FreshRSS, Self-Hosted, Homelab, Proxmox, LXC]
excerpt: "I got tired of letting algorithms decide what articles and videos I saw, so I built my own reading and watching list instead - here's why, and how I built it."
---

I don't want a news feed. I want a reading list - and a watch list I actually control.

Twitter, LinkedIn, YouTube's homepage, Google's own news app - every algorithmic feed I've used is optimizing for time-on-app, not for showing me what I actually asked to follow. That's not a conspiracy theory, it's just the incentive. So a few months back I went back to the thing that solved this exact problem 20 years ago and never actually stopped working: RSS. My version of it needed to cover both halves of what I consume - articles and YouTube channels - and it needed to be mine: self-hosted, and sorted by me instead of a recommendation engine.

## Why FreshRSS over Feedly or Inoreader

I didn't want my reading list living on someone else's server, feeding an ad profile, or disappearing behind a paywall the day the company changes its business model. FreshRSS is open-source and self-hosted, and it speaks a couple of standard protocols - its own API and a Google Reader-compatible one - that most RSS clients already know how to talk to. That compatibility mattered to me more than any single feature in the app itself; it meant I wasn't locking my subscriptions into one company's ecosystem.

## How I actually deployed it

FreshRSS runs in its own unprivileged Debian LXC on Proxmox, not a Docker stack. I used the community Proxmox VE helper script - the same `bash -c "$(wget -qLO - .../ct/freshrss.sh)"` pattern I use for a handful of other single-purpose services - which handles the nginx, PHP-FPM, and FreshRSS install in one shot and drops the app at `/opt/freshrss`. One container, one job. I'd rather a misbehaving app take down nothing but itself, and a dedicated LXC costs almost nothing on a hypervisor that already has the headroom.

It doesn't sit behind a Cloudflare Tunnel like most of my public-facing apps do. A CNAME points at my apex domain, which lands on Nginx Proxy Manager, and NPM reverse-proxies the rest of the way to the LXC's internal address. Different plumbing, same result: HTTPS in front of an internal service.

Updating it means `git pull` inside the container instead of `docker compose pull`, which caught me off guard the first time - the base LXC template doesn't ship with `git`. My first update attempt just returned `git: command not found`. Installed git, ran the normal fetch/reset/checkout/pull sequence, and it's been fine ever since.

## Getting YouTube in without the algorithm

The article side of this was the easy half. The part I actually wanted most was pulling specific YouTube channels in the same way - new uploads showing up as unread items, no recommendation feed, no autoplay, no "up next" deciding what I watch after.

YouTube doesn't advertise this, but every channel still exposes a plain RSS/Atom feed:

```text
https://www.youtube.com/feeds/videos.xml?channel_id=<CHANNEL_ID>
```

Grab the channel ID from the channel's page source or the `about` page URL, drop that feed URL into FreshRSS like any other subscription, and it behaves exactly like a blog: new video goes up, it shows up as an unread item with the title and a link, nothing more. Sorted into its own category alongside the article feeds, so a channel I follow for long-form content doesn't compete for attention with a five-minute BleepingComputer headline in the same list.

## Curating everything into categories instead of one big pile

Between articles and channels, everything gets sorted into a handful of categories: IT News Sites, News Sites, Reddit, YouTube, plus a couple of non-work categories (Entertainment, Hardware) for the feeds that have nothing to do with the homelab.

IT News Sites is the one doing the real work day to day:

| Feed |
|---|
| BleepingComputer |
| Krebs on Security |
| The Hacker News |
| The Register |
| Cisco Talos Blog |
| TechCrunch |
| Techdirt |
| How-To Geek |
| Lifehacker |
| Threatpost |

A typical pull might put a BleepingComputer piece on Google's privacy controls next to a Krebs writeup and a Register story about a school district leaving its network wide open. Ten sources, one unread count, nothing deciding for me which of them matters more.

YouTube ended up being the bigger category than I expected - it's almost entirely homelab, networking, and hardware channels: Jeff Geerling, NetworkChuck, Linus Tech Tips, Lawrence Systems, Crosstalk Solutions, Techdox, NASCompares, DB Tech, Hardware Haven, Christian Lempa, Lon.TV, Mactelecom Networks, Raid Owl, Shannon Morse, Smart Home Solver, and a few more. A handful of those show a warning icon in the sidebar right now, which in my experience usually just means the channel's feed hiccuped on a fetch - a channel rename or a format change on YouTube's end - not something that needs a real fix, just a requeue.

Reddit is a couple of specific subreddits added by their `.rss` suffix - r/homelab and r/linux are the two that actually get read regularly. News Sites is general non-tech stuff (Boston.com, NPR, WCVB Channel 5, and a couple of others) that I still want in one place but don't want anywhere near the IT backlog.

None of this stopped me from ending up with an unread count north of 5,800 across everything, which is its own kind of honesty - a real reading list has a backlog, an algorithm-curated feed never tells you that.

FreshRSS also exposes that Google Reader-compatible API - the same protocol most of the RSS client world was originally built against, back when Google Reader was the standard everyone integrated with. Any client that speaks it can authenticate and pull my subscriptions with no custom integration work on my end, on whatever device I happen to be reading or watching from.

## A 403 that wasn't what it looked like

At some point FreshRSS started throwing a `403 Login is invalid` on the web login, out of nowhere. Reads like a bad password. Wasn't one. Sitting behind a reverse proxy, the failure almost never traces back to FreshRSS's actual auth logic - it's the handshake between FreshRSS and whatever's in front of it.

Two things can cause the exact same error here. FreshRSS's `trusted_proxies` setting decides whether it trusts the `X-Forwarded-For`/`X-Forwarded-Proto` headers coming from the proxy; if it doesn't, every login attempt looks like it's coming from the same single IP, and that can trip the built-in rate limiter into rejecting good logins. Separately, FreshRSS checks the `Referer` and `base_url` on login as a CSRF guard - if the proxy strips that header, or `base_url` in `config.php` doesn't exactly match the public hostname and scheme, that check fails too, with the identical 403.

No way to tell which one you're looking at from the error message alone. The actual diagnostic path was pulling `trusted_proxies` and `base_url` straight out of `config.php` and comparing them against what the proxy was actually sending, rather than flipping settings and hoping. Worth remembering for any reverse-proxied app with its own trust settings: when it looks like a credentials problem, check whether the app and the proxy agree on what "the real client" even looks like. The config file is where that answer lives, not the login form.

## Where it stands now

FreshRSS runs quietly in the background, sorted into categories I actually chose instead of ones an algorithm guessed at - articles and video channels both. No ranking, no "recommended for you," no autoplay - just the things I actually subscribed to, in the order they were published.
