---
layout: post
title: "Building a Self-Hosted NOC Dashboard for My Homelab"
date: 2026-08-25
excerpt: "Why I got tired of checking a dozen different admin panels and built a single-pane-of-glass dashboard instead — with real multi-user auth and TOTP, not the usual LAN-only shortcut."
og_image: /assets/og/self-hosted-noc-dashboard.png
og_slug: self-hosted-noc-dashboard
image:
  path: /assets/og/self-hosted-noc-dashboard.png
  width: 1200
  height: 630
  alt: Self-hosted NOC dashboard branded social preview image
tags:
  - NOC Dashboard
  - Homelab
  - Python
  - Self-Hosted
---

At some point my homelab stopped being a handful of services I could keep in my head and turned into an actual small enterprise: a Proxmox cluster, two Docker hosts, three NAS units, a SIEM, an AI agent running its own VM, DNS resolvers, backup targets, VPN, reverse proxy — the list kept growing every time I solved a problem by standing up one more thing.

Every one of those services has its own admin panel. Proxmox has one. Portainer has one. UniFi has one. Wazuh has one. That's fine when you're actively working in one of them. It's not fine when you just want to know, at a glance, whether everything is up before you go do something else — and you end up with fifteen browser tabs open just to answer "is anything on fire right now."

So I built a NOC dashboard. One page, one glance, everything that matters.

## 1. Why not just use existing dashboard tools

There's no shortage of homelab dashboard projects — link aggregators, bookmark walls, status pages. I looked at a few before deciding to build my own, for two reasons that mattered more than saving myself the work.

First, most of them are link launchers, not monitors. They show you a pretty grid of icons that take you to the real dashboards. That's not what I wanted. I wanted the actual state — CPU, disk, service health, backup status — rendered right there, no click-through required.

Second, and the bigger one: almost none of them take multi-user auth seriously. My homelab runs on a "LAN-only, no per-app login" policy for most services, because the network boundary is the actual security control. But a NOC dashboard is different — it's a single page that summarizes the health of everything, which makes it a higher-value target than any individual service it's reporting on. If someone gets access to the dashboard, they get a map of my entire infrastructure. That's the one deliberate exception to my no-auth-on-LAN rule, and I wanted real auth behind it: accounts, roles, TOTP, session management — not a .htpasswd file from 2004.

Nothing I found combined "render actual live state" with "auth model I'd trust." So I wrote it.

## 2. What it actually does

The dashboard polls the APIs of whatever infrastructure you point it at and renders a static HTML page from the results. No client-side framework, no build step — it's two Python files and one external dependency (bcrypt). Everything else — the HTTP server, TOTP (RFC 6238), sessions, HTML rendering — is standard library.

The integration list grew organically, one card at a time, as I added a new service to the homelab and wanted it on the board:

- Proxmox VE and Proxmox Backup Server
- UniFi
- AdGuard Home
- CrowdSec
- Wazuh (manager and indexer)
- LimaCharlie
- Portainer / Docker
- UrBackup
- Uptime Kuma
- QNAP
- Hyper-V
- Cloudflare
- Tailscale
- WireGuard (WGDashboard)
- Nginx Proxy Manager
- Home Assistant
- SMART drive health
- Media stack (Plex, Tautulli, Sonarr, Radarr, Prowlarr, SABnzbd, Overseerr)
- Malware-source intel feeds
- Speed tests and custom URL checks

Each integration is configured through environment variables, and each one shows up as a card on the dashboard only if it's configured. Nothing to comment out, no dead cards for services you don't run — unconfigured integrations are simply invisible.

## 3. Architecture

The whole thing is deliberately boring:

```text
docker-compose.yml
└─ server.py            stdlib ThreadingHTTPServer
   ├─ auth: bcrypt + TOTP + sessions   (/api/login, /api/users, /api/sessions)
   ├─ periodically invokes ↓
   └─ generate_dashboard.py            polls integration APIs, renders static
      └─ /app/output                   HTML served by server.py
```

`server.py` handles the HTTP layer and everything auth-related. `generate_dashboard.py` is the part that actually knows how to talk to each integration's API, pull the relevant numbers, and render them into a static HTML page. The server periodically re-runs the generator in the background and serves whatever it produced — visitors are always looking at server-rendered HTML, not a live API round-trip on every page load.

That separation matters more than it looks. Auth and session handling stay simple and auditable because they don't have to worry about the complexity of two dozen different integration polling routines, and the polling routines don't need to know anything about who's logged in. If an integration's API times out or misbehaves, it can only break its own card, not the login page.

## 4. The auth model

This is the part I spent the most time on, because it's the part that actually matters given what this dashboard exposes.

- Multi-user accounts with admin and viewer roles — not everyone who can see the board needs to be able to change it.
- TOTP two-factor, using the standard RFC 6238 algorithm, so it works with any normal authenticator app.
- Account lockout after five failed attempts, with an admin unlock path — no infinite-guess login form.
- Forced password change and password aging.
- Session management with per-session revocation, so a compromised session doesn't require a global logout.
- bcrypt for password hashing, HttpOnly cookies for sessions.

None of this is exotic. It's the same baseline you'd expect from any properly built multi-user web app. The point isn't novelty — it's that a dashboard aggregating the health of an entire infrastructure deserves the same auth rigor as the infrastructure itself, even inside a LAN boundary I otherwise trust for everything else.

## 5. Themes and the rendering layer

Because the whole page is server-rendered static HTML, theming is just swapping a YAML file. I built a handful — dark NOC (the daily driver), Nord, Dracula, midnight blue, a light theme for anyone who prefers that — and the layout, clock format, and card arrangement persist to a state volume so a container rebuild doesn't reset your board back to defaults.

Keeping this server-rendered instead of reaching for React or Vue was a deliberate choice. A NOC board doesn't need client-side interactivity for the common case — it needs to load fast, look right on a wall-mounted display, and not need a build pipeline every time I touch it. Static HTML does all three without asking anything else of me.

## 6. Running it

```bash
git clone https://github.com/mdziegiel/noc-dashboard.git
cd noc-dashboard
cp .env.example .env    # fill in the integrations you use; leave the rest unset
docker compose up -d --build
```

First run prompts you to create the initial admin account, and TOTP can be enabled right after from account settings. Everything else — which cards show up, what they poll, how often — comes from the `.env` file.

## 7. Open-sourcing it

The dashboard now runs two ways in parallel: a production instance behind my actual environment variables and integration endpoints, and a public build on GitHub that anyone can clone and point at their own homelab. Getting from "script that only works with my exact setup" to "something a stranger can actually run" meant a sanitization pass — scrubbing hardcoded IP defaults, writing a real `.env.example`, stripping state and auth data that should never leave a machine, and dropping legacy code paths that only made sense in my environment.

That's also why every example address in the public repo uses the RFC 5737 documentation range (192.0.2.0/24) instead of anything resembling a real subnet. If you're publishing infrastructure tooling, that's a small habit worth building early — it's much easier to default to placeholder addressing from the start than to go back and scrub real IPs out of a repo's history later.

## 8. What I'd tell someone building their own

If your homelab is small — a couple of services, one host — you probably don't need this. A bookmark page is fine.

Once you cross into "I have to remember which admin panel tells me what," a real dashboard starts paying for itself immediately. The two decisions I'd stand behind for anyone doing the same:

- Server-render it. You don't need a frontend framework for a board that mostly gets glanced at, not interacted with.
- Don't skip auth because it's LAN-only. A single page that summarizes your entire infrastructure's health is worth more to an attacker than any one service it's reporting on. Treat it accordingly, even behind a boundary you otherwise trust.

Repo's public if you want to see the whole thing or run it yourself: [github.com/mdziegiel/noc-dashboard](https://github.com/mdziegiel/noc-dashboard)
