---
layout: post
title: "Why I Ditched My Traditional VPN for Tailscale"
date: 2026-08-28
tags: [networking, security, homelab, tailscale, wireguard]
excerpt: "Traditional site-to-site and remote-access VPNs solve connectivity, but they cost you in attack surface and admin overhead. Here's why I moved my homelab to Tailscale's WireGuard mesh, and how I set it up."
---

For years my remote access setup looked like every other homelab and small-business network: a firewall rule forwarding a UDP port to an OpenVPN or WireGuard server, a cert or PSK to manage, and a hub-and-spoke tunnel that dumped remote clients onto my LAN subnet. It worked, but every time I opened that inbound port I was accepting a tradeoff I didn't love — an internet-facing listener that's one misconfigured firewall rule or unpatched VPN daemon away from being someone else's way in.

Tailscale flips that model. It's still WireGuard under the hood, so the crypto and performance story is the same one I already trusted, but the architecture around it is different in ways that actually matter for a home network with multiple sites, mixed OSes, and gear I don't want babysitting a port-forward for.

## Traditional VPN vs. Tailscale: what actually changes

| | Traditional VPN (OpenVPN / IPsec / stock WireGuard) | Tailscale |
|---|---|---|
| Topology | Hub-and-spoke — everything routes through one VPN server/concentrator | Mesh — every node builds a direct peer-to-peer tunnel to every other node it's authorized to reach |
| Inbound exposure | Requires a forwarded port (UDP 1194, 51820, etc.) reachable from the internet | No inbound ports required — NAT traversal via Tailscale's DERP relay infrastructure and STUN-like coordination, falling back to relay only when a direct path can't be negotiated |
| Auth model | Static certs or pre-shared keys you provision and rotate manually | Identity-based — ties into your existing SSO/IdP (Google, Microsoft Entra ID, GitHub, etc.), device approval, and key expiry/rotation handled automatically |
| Access control | Usually all-or-nothing once you're on the tunnel, unless you hand-roll firewall rules per subnet | ACLs (tailnet policy file, JSON/HuJSON) define exactly which nodes can talk to which nodes, on which ports — real least-privilege segmentation |
| DNS | Split-tunnel DNS config is fiddly, especially cross-platform | MagicDNS gives every node a stable hostname.tailnet-name.ts.net name, no manual DNS server config on clients |
| Client experience | Manual profile import, reconnect logic varies by platform | Native clients for Windows/macOS/Linux/iOS/Android/routers, auto-reconnect, sits in the tray |
| Non-Tailscale devices | N/A — everything needs a client | Subnet routers advertise entire LAN ranges so legacy devices (NAS, IoT, printers) are reachable without installing anything on them |
| Management overhead | You are the PKI. Cert expiry, revocation, and key distribution are on you | Key expiry, device approval, and ACL changes are centralized in the admin console; scriptable via API/Terraform |
The honest caveat: Tailscale is a coordination-plane dependency. The control plane (key distribution, ACL sync, NAT traversal coordination) is Tailscale's cloud by default, and even though the actual data plane traffic between your nodes is end-to-end encrypted WireGuard and doesn't transit their servers except when relayed through DERP, you're trusting their infrastructure for coordination. If that's a dealbreaker for your threat model, Headscale (the open-source, self-hosted control-plane reimplementation) gets you the same client experience without depending on Tailscale's cloud. For my use case — a home lab, not a regulated environment — the tradeoff is worth it for the operational simplicity.

## How I set it up

### 1. Bootstrap the tailnet

Installed the client on my primary jump host first:

curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh

The --ssh flag enables Tailscale SSH, which layers your tailnet identity and ACLs on top of SSH access — no separate key management needed for hosts you're already trusting inside the tailnet.

### 2. Advertise subnet routes instead of joining every device individually

Installing the client on every VM, IoT device, and network appliance isn't realistic. Instead I picked one always-on host on my LAN (a lightweight VM) to act as a subnet router:

sudo tailscale up --advertise-routes=10.x.x.0/24 --accept-routes

Then approved the advertised route in the admin console (Machines → the node → Edit route settings). This exposes the entire LAN segment to authorized tailnet members without touching every device on it — your NAS, printers, and any legacy gear just work.

### 3. Exit node for full-tunnel roadwarrior access

For remote access where I want *all* traffic — not just LAN-bound traffic — routed home (useful on untrusted Wi-Fi):

sudo tailscale up --advertise-exit-node

Approved in the console, then on the client side: tailscale up --exit-node=<hostname>. This gets you the "traditional VPN" full-tunnel behavior when you actually want it, without it being the default for every connection.

### 4. Lock down ACLs — don't leave the default allow-all

Tailscale's default tailnet policy is permissive (anyone-to-anyone). That's fine for a five-minute test, not for production. I moved to an explicit ACL model in the policy file:

{
  "acls": [
    {
      "action": "accept",
      "src": ["group:admin"],
      "dst": ["tag:server:22", "tag:server:443"]
    },
    {
      "action": "accept",
      "src": ["group:family"],
      "dst": ["tag:media:*"]
    }
  ],
  "tagOwners": {
    "tag:server": ["group:admin"],
    "tag:media": ["group:admin"]
  }
}

Tags replace hostnames as the ACL target so rules survive host rebuilds. This is the piece that actually gets you past "VPN = flat network" — my monitoring stack, media stack, and management hosts are all reachable only by the groups and ports that need them, enforced at the tailnet layer regardless of what the underlying host firewall is doing.

### 5. MagicDNS

Turned on in DNS settings in the admin console. Every node gets a stable name (vault.tailnet-name.ts.net) instead of memorized IPs, and it survives DHCP lease changes on the LAN side since it's resolved through Tailscale's coordination, not your local DNS server.

## The gotcha worth knowing about

One thing that bit me during setup: Tailscale will, by default, route *all* DNS queries through the tailnet once MagicDNS or a subnet route touching your LAN's CIDR is accepted — including on networks where you didn't expect it. If you've got local DNS infrastructure doing split-horizon resolution (I run AdGuard Home + Unbound), an unapproved or overly broad subnet route can silently hijack DNS resolution for clients that shouldn't be affected, breaking local-only lookups in a way that's confusing to troubleshoot because the client still shows "connected." Worth checking tailscale status and the accepted routes list first if DNS starts behaving strangely after a route change — it's almost always a routing/DNS override you didn't intend to accept, not a broken
DNS server.

## Where this leaves the old VPN

I haven't fully decommissioned my WireGuard server — there's still a case for a dumb, dependency-free tunnel as a break-glass path if the tailnet control plane is ever unreachable. But for day-to-day remote access, cross-device management, and reaching services without opening a single inbound port, Tailscale has replaced it as the default. The ACL model alone is worth the switch if your current VPN gives every connected client the same blast radius as a device sitting on your LAN.
