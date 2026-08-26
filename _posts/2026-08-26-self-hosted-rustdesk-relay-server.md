---
layout: post
title: "Self-Hosting RustDesk: Running Your Own Relay Server"
date: 2026-08-26
excerpt: "Why I moved off the public RustDesk rendezvous/relay infrastructure and stood up my own hbbs/hbbr stack, plus the architecture, key handling, and verification steps to prove it actually works."
og_image: /assets/og/self-hosted-rustdesk-relay-server.png
og_slug: self-hosted-rustdesk-relay-server
image:
  path: /assets/og/self-hosted-rustdesk-relay-server.png
  width: 1200
  height: 630
  alt: Self-hosted RustDesk relay server branded social preview image
tags:
  - RustDesk
  - Remote Access
  - Docker
  - Self-Hosted
  - Homelab
---

Remote desktop tools are one of those categories where "free" quietly means "someone else's server sits in the middle of your session."

TeamViewer, AnyDesk, Chrome Remote Desktop — pick one, and by design your traffic is brokered through infrastructure you don't control, under licensing terms that can change under you. RustDesk is interesting because it flips that default on its head: the clients are open source, the server components are available, and nothing stops you from running the same rendezvous and relay stack yourself.

So I did. Not the browser client science project. Just the part that matters first: a working self-hosted RustDesk relay stack on a small Linode VM, using RustDesk's `hbbs` and `hbbr` services instead of the public infrastructure.

## 1. RustDesk's server side is two jobs, not one

RustDesk's backend is split into two services:

- `hbbs` — the ID/rendezvous server. Clients register here, look up each other's IDs, and negotiate how they should connect.
- `hbbr` — the relay server. This moves traffic when a direct peer-to-peer connection cannot be established.

That distinction matters. `hbbs` is the broker. It helps two clients find each other. It is not supposed to be in the middle of the remote-control stream. `hbbr` is the fallback path when NAT traversal does what NAT traversal usually does: disappoint everyone involved.

The flow looks roughly like this:

```text
RustDesk client A
        |
        | 1. Register / look up peer ID
        v
      hbbs
        |
        | 2. Negotiate direct path if possible
        v
RustDesk client B

If direct P2P fails:

RustDesk client A  <---- encrypted relay traffic ---->  hbbr  <---- encrypted relay traffic ---->  RustDesk client B
```

The relay is not there to decrypt your desktop session. It is there to move encrypted bytes when the clients cannot talk directly. That's still a sensitive position, because metadata and availability matter, but it is not the same thing as handing the server plaintext screen data.

## 2. Why bother self-hosting it

The public RustDesk servers are convenient. Convenience is usually where the bill shows up later.

For occasional use, the public rendezvous and relay infrastructure may be fine. For something I rely on to reach my own systems, I wanted the boring version where I control the broker, the relay, the logs, the firewall, and the key material.

| Concern | Public infrastructure | Self-hosted relay |
|---|---|---|
| Metadata | Someone else's server brokers your IDs | You control the logs and retention |
| Bandwidth | Shared relay capacity | Dedicated to your own clients |
| Availability | Best effort | Your VM, your monitoring, your outage |
| Key ownership | Public service defaults | You generate and distribute your own server key |
| Network policy | Generic | Fits your firewall, hardening, and monitoring model |

None of that is dramatic on its own. Together, for a remote access tool, it was enough. If a service can control machines on my network, I would rather not depend on public rendezvous infrastructure unless I have to.

## 3. The Docker Compose shape

The deployment is simple: one image, two services, shared data.

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

I used `network_mode: host` because this is one of those cases where Docker bridge networking buys you very little and creates several new ways to be wrong. RustDesk uses a small set of TCP and UDP ports, and host networking keeps the packet path obvious.

The shared `./data:/root` volume is not decorative. `hbbs` generates the server keypair there on first run, and both services need access to that same material. If you split the volumes, you are inventing a failure mode for no reward. Very entrepreneurial. Very stupid.

Start it like any other Compose stack:

```bash
docker compose up -d
docker compose logs -f hbbs
```

On first boot, `hbbs` logs the public key. That key is what your RustDesk clients need in their server settings.

## 4. Firewall ports

For the base open-source RustDesk server stack, the important ports are:

```text
21115/tcp   NAT type test
21116/tcp   ID registration and heartbeat
21116/udp   ID registration and heartbeat
21117/tcp   Relay traffic
```

Using a documentation address, the mental model is:

```text
203.0.113.10:21115/tcp
203.0.113.10:21116/tcp
203.0.113.10:21116/udp
203.0.113.10:21117/tcp
```

I did not open `21114` because that is for the Pro web console. This setup is the standard self-hosted relay path, not the paid web console and not the browser client experiment.

## 5. Key handling is the part people underthink

On first launch, `hbbs` creates an ed25519 keypair in the mounted data directory:

```text
./data/id_ed25519
./data/id_ed25519.pub
```

The public key goes into every RustDesk client. The private key stays on the server. If that sounds obvious, congratulations, you have cleared the floor-level bar that the internet keeps tripping over.

That private key matters because it defines the trust relationship between your clients and your server. If you lose it, your clients need to be repointed to a new key. If it is stolen, you rotate it and assume the old trust boundary is dead.

My handling rule is simple:

- Back up the private key somewhere that is not just the relay VM itself.
- Do not casually delete or regenerate `./data` during container cleanup.
- Treat key rotation as a real change, because every configured client depends on it.
- If compromise is suspected, rotate the key and reconfigure clients. Do not negotiate with entropy.

## 6. Pointing clients at the self-hosted server

Every RustDesk client that should use your infrastructure needs the same three settings.

Using placeholder addressing:

```text
ID Server:     203.0.113.10:21116
Relay Server:  203.0.113.10:21117
Key:           <contents of ./data/id_ed25519.pub>
```

Set that on both sides: the machine you are controlling from and the machine being controlled.

Mixed configurations are the easy way to waste an hour. If one client is still using the public RustDesk infrastructure and the other is pointed at your server, they will not find each other the way you expect. When a connection fails silently, check the server fields and key before blaming the firewall, the client, the phase of the moon, or systemd.

## 7. Verifying it actually works

`docker compose ps` proving that containers are running is not the same thing as proving remote access works. It proves Docker can keep a process alive. A houseplant can do that.

Start with the basics:

```bash
docker compose ps
ss -tulpn | grep -E '21115|21116|21117'
docker compose logs -f hbbs
```

Then start a RustDesk client that is configured to use your server. In the `hbbs` logs, you should see registration or heartbeat activity for that client ID. That proves the client is talking to your rendezvous server, not the public one.

After that, test from a second machine. Configure both clients with the same ID server, relay server, and key. Connect from one to the other through the normal RustDesk app.

While the session is starting, watch the relay logs:

```bash
docker compose logs -f hbbr
```

If the connection has to relay, `hbbr` should show activity. If the clients manage a direct peer-to-peer path, `hbbr` may stay quiet. That is not automatically a failure. It may mean the relay was not needed.

That detail matters because it is easy to stare at quiet relay logs and conclude the relay is broken when the better answer is: the clients successfully avoided using it. Rare, but beautiful. Like a printer working on the first try.

## 8. What this does not solve

This gets the RustDesk relay working. It does not magically give you a reliable browser-based RustDesk client.

The web client path is a separate, harder problem. The official RustDesk web client and various forks have real compatibility and build gaps depending on server/client versions. If browser access is a hard requirement, budget time for that as its own project. Do not treat it as an afterthought bolted onto the relay deployment.

A few other things I would not skip:

- Pin `rustdesk/rustdesk-server` to a known-good version once the setup is stable. `latest` is fine for a first boot, not for something you depend on.
- Put the VM behind normal host hardening: key-only SSH, unattended security updates, firewall rules, log monitoring, and something like fail2ban or CrowdSec where appropriate.
- Monitor the service from the outside. If remote access is your break-glass path, you want to know it is broken before you need it.

The end result is boring in the best possible way: two containers, one shared keypair, four exposed ports, and a remote access broker you control.

For infrastructure that can put hands on keyboards across your environment, boring is not an insult. Boring is the design goal.
