---
layout: post
title: "RustDesk: A Self-Hosted TeamViewer Alternative"
date: 2026-08-26
excerpt: "Why I moved off the public RustDesk rendezvous/relay infrastructure and stood up my own hbbs/hbbr stack, plus the architecture, key handling, and verification steps to prove it actually works."
og_image: /assets/og/self-hosted-rustdesk-relay-server.png
og_slug: self-hosted-rustdesk-relay-server
image:
  path: /assets/og/self-hosted-rustdesk-relay-server.png
  width: 1200
  height: 630
  alt: RustDesk self-hosted TeamViewer alternative branded social preview image
tags:
  - RustDesk
  - Remote Access
  - Docker
  - Self-Hosted
  - Homelab
---

Remote desktop tools are one of those categories where "free" quietly means "someone else's server sits in the middle of your session."

TeamViewer, AnyDesk, Chrome Remote Desktop — pick one, and by design your traffic is brokered through infrastructure you don't control, under licensing terms that can change under you. RustDesk is interesting because it flips that by default: it's open source, the protocol is documented, and nothing stops you from running the exact same server software the public instance runs, except this time you own it.

So that's what I did.

## 1. How RustDesk's server side actually works

RustDesk splits its backend into two services, not one:

- hbbs (ID/rendezvous server) — handles client registration, ID lookup, and NAT traversal negotiation. This is how two peers find each other.
- hbbr (relay server) — handles the actual relayed traffic when a direct peer-to-peer connection can't be established (which, behind most home/office NAT, is most of the time).

Both ship as a single Rust binary, rustdesk-server, that runs in two modes. In practice you run two containers or two processes from the same image.

```text
RustDesk client (controller)
  -> ID lookup/rendezvous
  -> hbbs
  -> connection negotiated
  -> hbbr (relay, if P2P fails)
  -> RustDesk client (controlled machine)
```

The important part: hbbs never sees your screen or session data. It brokers the handshake. hbbr only sees traffic when direct P2P fails, and it's carrying an already end-to-end encrypted stream — it can't decrypt it, it's just moving bytes.

References: RustDesk server GitHub repo (github.com/rustdesk/rustdesk-server), RustDesk self-hosting docs (rustdesk.com/docs/en/self-host/)

## 2. Why self-host instead of using the public relay

The public rendezvous server works fine for casual use. I moved off it for a few concrete reasons: session metadata visibility (broker sees connection attempts vs you control the logs), bandwidth/availability (shared/rate-limited vs dedicated), key ownership (public key infra vs you generate and control the keypair), network fit (generic vs behind your own firewall rules, fail2ban/CrowdSec), cost (free vs a small VM).

None of these are dramatic on their own. Together, for a tool that has full remote-control access to machines on my network, "I own the broker" was worth the VM.

## 3. Example addressing

Placeholder values for this post — substitute your own: hbbs/hbbr host 203.0.113.10 (public IP of the relay VM), hbbs port 21115-21116 TCP and 21116 UDP (ID/rendezvous), hbbr port 21117 TCP (relay data), web console 21114 optional Pro only (not used in this OSS setup).

Don't cargo-cult the IP. Do get the ports right — this is the part people get wrong most often.

## 4. Docker Compose deployment
The official server image runs both services from docker-compose:

```yaml
services:
  hbbs:
    image: rustdesk/rustdesk-server:latest
    container_name: hbbs
    network_mode: host
    volumes:
      - ./data:/root
    command: hbbs
    restart: unless-stopped
  hbbr:
    image: rustdesk/rustdesk-server:latest
    container_name: hbbr
    network_mode: host
    volumes:
      - ./data:/root
    command: hbbr
    restart: unless-stopped
```

Two things I'd flag if you're building this fresh: network_mode: host is the path of least resistance here since RustDesk's port set doesn't map cleanly to Docker's default bridge NAT for every client scenario, and host networking removes a whole category of "why can't clients see my server" debugging. Shared volume — both containers need to read the same keypair, so they mount the same ./data directory; hbbs generates the keypair on first run if one doesn't exist.

Run:

```bash
docker compose up -d
docker compose logs -f hbbs
```

On first boot, hbbs logs the generated public key. That key is what every client needs to trust this server instead of the public one.

## 5. Firewall rules

```text
21115/tcp (NAT type test)
21116/tcp and 21116/udp (ID registration/heartbeat)
21117/tcp (relay)
```

That's it for the base stack. I did not open 21114 — that's the Pro web console port, and I'm not running Pro.

## 6. Key handling

This is the part that actually matters for trust, and it's easy to treat as an afterthought. hbbs generates an ed25519 keypair on first launch and stores it in the mounted data directory:

```text
./data/id_ed25519
./data/id_ed25519.pub
```

The public key is what you paste into every client's server settings. The private key never leaves the server, and it's the thing that actually matters for backup — lose it, and every client needs to be re-pointed with a new public key. Treat that private key the way you'd treat any other host key material: back it up somewhere outside the VM itself, don't regenerate it casually since every existing client configuration breaks the moment you do, and if you ever suspect the VM is compromised, rotating this key is not optional.

## 7. Pointing clients at your server

On each RustDesk client — controller and controlled machine both — under Settings then Network, set:

```text
ID Server:    203.0.113.10:21116
Relay Server: 203.0.113.10:21117
Key:          <the public key from id_ed25519.pub>
```

Every client that needs to see each other has to point at the same server with the same key. Mixed configurations — one client on the public relay, one pointed at yours — simply won't find each other. That's obvious in hindsight and still the first thing to check when a connection silently fails.

## 8. Verification

Don't take "it deployed" as proof it works. Confirm each layer.

Containers are actually up:

```bash
docker compose ps
```

hbbs is listening on the expected ports:

```bash
ss -tulpn | grep -E '21115|21116|21117'
```

A client can register with the server by checking hbbs logs while a client starts up; you should see a registration/heartbeat entry tied to that client's ID, not silence.

End-to-end session test from a second machine, connect to the first client's ID through the RustDesk app, with both pointed at your server and key — if it connects, watch docker compose logs -f hbbr during the session.

```bash
docker compose logs -f hbbr
```

If the connection relayed you'll see traffic there, if it went direct P2P hbbr logs stay quiet and that's also correct since hbbr is only in the path when NAT traversal fails.

That last distinction trips people up: a quiet hbbr log doesn't mean the relay is broken. It can mean the connection didn't need it.

## 9. What I'd flag before you copy this

This gets you a working self-hosted relay. It does not get you a browser-based client for free — the official RustDesk web client has real build/compatibility gaps against current server versions, and most of the actively maintained forks don't speak protocol cleanly with a stock hbbs/hbbr stack either.
If browser access without installing the desktop client is a hard requirement, budget real time for it — it's a separate, harder problem than standing up the relay. Put this behind something that isn't just open ports to the internet — a reverse proxy or tunnel in front of it, plus normal host hardening like fail2ban/CrowdSec-style enforcement, key-only SSH, unattended security updates, is the same baseline I'd want on any internet-facing service, since RustDesk doesn't get a pass just because the session payload is encrypted. Version-pin deliberately — rustdesk-server:latest is fine to get started, but for anything you depend on, pin to a known-good tag and upgrade on your schedule, not Docker Hub's.

## 10. Closing

The self-hosted RustDesk relay is genuinely simple once you separate what hbbs and hbbr each do: one brokers the handshake, one moves bytes when direct P2P isn't possible. Two containers, a shared keypair, four ports, and you've replaced a public-infrastructure dependency with something you control end to end.

It's not flashy. It's the kind of infrastructure that's supposed to be boring — and for a tool with full remote-control access to machines on my network, boring and observable is exactly the point.
