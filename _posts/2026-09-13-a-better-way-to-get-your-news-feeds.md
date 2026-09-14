---
layout: post
title: "A Better Way to Get Your News Feeds: Self-Hosting FreshRSS"
date: 2026-09-13
excerpt: "I got tired of letting algorithms decide what articles and videos I saw, so I built my own reading and watching list instead - here's why, and how I built it."
og_image: /assets/og/a-better-way-to-get-your-news-feeds.png
og_slug: a-better-way-to-get-your-news-feeds
image:
  path: /assets/og/a-better-way-to-get-your-news-feeds.png
  width: 1200
  height: 630
  alt: A Better Way to Get Your News Feeds - Self-Hosting FreshRSS branded social preview image
tags:
  - RSS
  - FreshRSS
  - Self-Hosted
  - Homelab
  - Proxmox
  - LXC
---

I don't want a news feed. I want a reading list - and a watch list I control.

Twitter, LinkedIn, YouTube's homepage, Google's own news app: none of them are optimizing for keeping me informed, they're optimizing for time-on-app. So a few months back I went back to RSS, self-hosted, built to cover both halves of what I actually consume - articles and YouTube channels - sorted by me instead of a recommendation engine.

## Why FreshRSS

Open-source and self-hosted - no ad profile, no paywall risk if the company changes its model. It speaks two protocols, its own API and a Google Reader-compatible one, that most RSS clients already know how to talk to. That compatibility mattered more than any feature in the app itself - it meant I wasn't locking my subscriptions into one company's ecosystem.

## Deployment

FreshRSS runs in its own unprivileged Debian LXC on Proxmox, not a Docker stack. Community Proxmox VE helper script - same bash -c "$(wget -qLO - .../ct/freshrss.sh)" pattern I use for a handful of other single-purpose services - handles nginx, PHP-FPM, and the FreshRSS install in one shot, drops the app at /opt/freshrss. One container, one job.

It's not behind a Cloudflare Tunnel like most of my public apps. A CNAME on my apex domain lands on Nginx Proxy Manager, which reverse-proxies to the LXC's internal address.

Updating it is git pull inside the container instead of docker compose pull - caught me off guard the first time, since the base LXC template doesn't ship with git. apt install -y git, then the normal fetch/reset/checkout/pull sequence, fixed it for good.

## YouTube without the algorithm

Every YouTube channel exposes a plain RSS/Atom feed, even though Google doesn't advertise it:

https://www.youtube.com/feeds/videos.xml?channel_id=<CHANNEL_ID>

Grab the channel ID from the page source or the about URL, add it as a subscription, and it behaves like any other feed - new video, new unread item, no autoplay, no "up next" picking what I watch after.

## Categories

Everything's sorted into IT News Sites, News Sites, Reddit, YouTube, Entertainment, and Hardware.

IT News Sites:

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

YouTube covers homelab, networking, and hardware channels.

Reddit is r/homelab and r/linux, added by their .rss suffix - the only two subreddits I actually read regularly. News Sites is general non-tech (Boston.com, NPR, WCVB) that I want in one place but nowhere near the IT backlog.

Unread count across everything is north of 5,800.

## Reading it on phone and tablet

FreshRSS speaks that Google Reader-compatible API alongside its own native one, so any client that talks it - Reeder, FeedMe, NetNewsWire, whatever - logs in and syncs straight from the app, no browser needed. freshrss.mrdtech.me reaches the LXC through a plain CNAME to Nginx Proxy Manager instead of a Cloudflare Tunnel, so there's no Access/email-login wall in front of it.
Auth happens at FreshRSS's own login, and the same account works from any of those apps on any network, home or not.

Same unread counts, same read state, whether I'm at my desk or on my phone on the train.
