---
layout: post
title: "Building a Zero-Trust Homelab: Cloudflare Access, Tunnel, and the Real DNS/Routing Picture"
date: 2026-08-23
excerpt: "A practical look at how I use Cloudflare Access, Tunnel, WAF, DNS Gateway, Nginx Proxy Manager, and static-site routing without pretending every service belongs behind the same ingress path."
og_image: /assets/og/building-zero-trust-homelab-cloudflare-access-tunnel-dns-routing.png
og_slug: building-zero-trust-homelab-cloudflare-access-tunnel-dns-routing
image:
  path: /assets/og/building-zero-trust-homelab-cloudflare-access-tunnel-dns-routing.png
  width: 1200
  height: 630
  alt: Zero Trust homelab Cloudflare routing branded social preview image
tags:
  - Zero Trust
  - Cloudflare
  - Networking
  - Security
---

Zero Trust is a useful phrase that has been abused into a motivational poster.

For a homelab, I do not care about the poster. I care about the operational problem: I have self-hosted services under a personal domain, some of them are useful from outside the house, and I do not want "public DNS record exists" to mean "the internet gets a login prompt and a prayer."

That is the real reason I built this setup.

The public-safe architecture repo is [`mdziegiel/zero-trust-homelab`](https://github.com/mdziegiel/zero-trust-homelab). It documents the high-level model: Cloudflare Access, Cloudflare Tunnel, WAF, Tailscale, reverse proxying, and network segmentation. The internal routing map has more detail, but the literal destinations, route table, IDs, and home public IP are intentionally not repeated here. Some things are documentation. Some things are free recon. Try not to confuse them.

## 1. Why Zero Trust for a homelab?

My motivation was not to build a perfect enterprise Zero Trust reference architecture in miniature. That would be a good way to spend weekends creating diagrams nobody asked for.

The motivation was simpler:

- keep self-hosted apps reachable under a real domain;
- avoid unnecessary direct inbound exposure;
- put identity-aware access in front of administrative or semi-private apps;
- keep trusted-device access separate from public browser access;
- keep break-glass remote administration from depending on the same control plane as the normal path;
- make the routing map explicit enough that I can troubleshoot it later.

The repo README says the environment is built around "no direct inbound access from the internet," identity-aware access controls, segmented internal networking, and multiple secure access paths using Cloudflare and Tailscale. That matches the actual reason I wanted this: not theoretical purity, just fewer ugly edges.

The most useful sentence in the whole model is this one from the design principles: use layered controls instead of a single boundary. A tunnel alone is not a security model. A reverse proxy alone is not a security model. DNS alone is definitely not a security model. Put them together carefully and you get something that is at least harder to casually ruin.

## 2. Architecture overview: how requests flow

At the public edge, Cloudflare handles the first decision point:

```text
Internet
  -> Cloudflare DNS / WAF / DDoS protection
  -> Cloudflare Access, when the app is protected
  -> Cloudflare Tunnel or DNS/reverse-proxy path
  -> Nginx Proxy Manager, when that path is used
  -> internal service
```

The public repo's traffic-flow section reduces this to:

```text
External user -> Cloudflare -> Access Authentication -> Reverse Proxy -> Service
Internal trusted user -> Tailscale -> Internal Service
```

That is accurate, but the real environment has a split behind it.

Cloudflare Tunnel is used for selected application exposure without relying on a public inbound port to the service itself. The architecture diagram in the repo shows Cloudflare WAF, Zero Trust Access, DDoS protection, and Cloudflare Tunnel as the perimeter layer before traffic reaches Nginx Proxy Manager and service categories.

Tailscale is a separate private-access path for trusted devices. The README also documents a self-hosted WireGuard fallback for break-glass access, deliberately not gated behind Cloudflare Access. That matters. If Cloudflare, an identity edge, or a third-party coordination layer is degraded, remote administration should not become a locked door with a nice dashboard.

## 3. The routing split: Tunnel vs. CNAME to NPM

This is the part that gets messy if you pretend every hostname should work the same way.

The internal routing map separates the environment into three practical groups:

| Route class | What it means | Why it exists |
|---|---|---|
| Cloudflare Tunnel routes | Selected self-hosted applications are published through Cloudflare Tunnel and may also have Access policies attached. | Avoid unnecessary inbound exposure and let Cloudflare apply edge controls before the request reaches the service path. |
| DNS/CNAME-to-reverse-proxy routes | Some hostnames resolve toward the home edge and are handled by Nginx Proxy Manager. | These fit the existing reverse-proxy/certificate/routing model better than direct tunnel publication, or they are part of the older public ingress design. |
| GitHub Pages routes | Static public sites, like the portfolio and resume, point to GitHub Pages. | Static sites do not need to traverse the homelab at all. Sending them through a tunnel would be architecture cosplay. |

The literal routing table includes internal host:port destinations. I am not publishing those. The useful public lesson is the split itself: not every hostname has the same risk profile, authentication model, or operational dependency.

Some browser-facing tools belong behind Cloudflare Access. Some services rely on their native authentication and reverse-proxy handling. Static sites should stay static. If GitHub can serve the portfolio and resume directly, there is no reason to drag that traffic through the house just so the diagram looks symmetrical.

## 4. Access policies: IP bypass plus email allow

For the Access-protected apps, the internal map documents a reusable pattern: an IP-based bypass policy plus an email-based allow policy.

Sanitized, the structure looks like this:

```yaml
access_application:
  type: self_hosted
  domain: app.example.com
  policies:
    - name: Trusted location bypass
      decision: bypass
      include:
        - ip_range: trusted-public-egress
    - name: Approved user email
      decision: allow
      include:
        - email: approved-user@example.com
```

The point is not that this exact YAML is copied from Cloudflare. It is the policy shape.

The trusted-location bypass avoids forcing an identity challenge when the request already comes from the known trusted egress path. The email allow policy keeps the same app reachable when I am not on that path, but still requires identity-aware authentication. That gives me a practical day-to-day workflow without turning remote access into "anyone with the URL can try the app login page."

It is not glamorous. It is just useful.

## 5. Defense in depth beyond Access

Cloudflare Access is only one layer.

The internal documentation for Cloudflare Zero Trust lists the Cloudflare roles in the environment as DNS, WAF, Zero Trust / Access, Tunnels, and CrowdSec-driven edge blocking. The operating principles are blunt: no unnecessary direct inbound exposure, protect administrative apps with identity-aware access or LAN/VPN-only exposure, use WAF and bouncer decisions as edge controls, and keep DNS/tunnel credentials out of repositories and docs.

That last one should not need to be written down. It does, because entropy is undefeated.

The routing map also documents DNS Gateway block policies and WAF custom-rule categories. Sanitized, the idea is:

```text
DNS Gateway
  - block known malware categories
  - block adult-content categories where appropriate
  - block security-risk categories

WAF custom rules
  - skip trusted home/admin traffic
  - skip known good bots
  - managed-challenge aggressive crawlers
  - managed-challenge broad provider/country patterns that produce noisy traffic
  - block hosting-provider abuse, suspicious paths, and Tor-origin traffic
```

That gives me several places to stop dumb traffic before it gets near an app:

1. DNS filtering for clients using the protected resolver path.
2. Cloudflare WAF rules at the edge.
3. Cloudflare Access for selected apps.
4. Nginx Proxy Manager and app-native auth deeper in the stack.
5. Tailscale or WireGuard for private administrative access.

None of those layers is perfect. That is why there is more than one.

## 6. What's not proxied, and why

The routing map explicitly calls out things that should not go through the tunnel path.

The apex DNS-only record points at the home public IP so the existing reverse-proxy path can serve the hostnames that belong behind Nginx Proxy Manager. I am not printing the IP address. Not even a redacted-looking version. The sentence "home public IP" is enough.

The portfolio and resume hostnames point to GitHub Pages. They are static sites. There is no internal app to protect, no container to wake up, no origin service to keep warm, and no reason to introduce Cloudflare Tunnel or NPM into that path.

That is a general lesson: the safest homelab route is often the route that does not enter the homelab.

## 7. Lessons learned and gotchas

The first gotcha was that the routing map needs to be treated as a real artifact, not tribal memory. The internal Cloudflare routing-map page records DNS, tunnel, WAF, Access, email routing, and route reconciliation state. That is the kind of boring inventory that saves time when something breaks.

The second gotcha was stale route cleanup. The routing map originally had a reconciliation note for routes tied to services that were being decommissioned. Those routes were later removed and the decommission was marked closed. That is the right lifecycle: find drift, document it, clean it up, then update the document. Stunningly rare behavior in infrastructure, apparently.

The third gotcha was Cloudflare API scope. A vault note from earlier dashboard work records that zone-level analytics were accessible, but WAF/firewall analytics required more specific GraphQL dataset permissions. The token could be valid and still not authorized for the dataset being queried. This is the kind of issue that makes people say "the API is broken" when the actual answer is "your token is scoped like a decorative key."

The fourth gotcha was telemetry quality. Another internal note records CrowdSec/Cloudflare bouncer work where the important lesson was not "is the service running," but "is it reading the right logs." A running parser pointed at low-value logs is not monitoring. It is process theater.

## 8. Where this goes next

The public repo already lists future improvements:

- add CrowdSec for adaptive blocking;
- add centralized logging and alerting;
- add service-level authentication;
- add policy-based device access controls.

Based on the internal notes, I would sharpen that into a few practical next steps:

1. Keep the Cloudflare routing map current after every route add/remove.
2. Reconcile which apps should have Access in front of them versus native auth only.
3. Verify Cloudflare token scopes before building dashboards around WAF or Gateway analytics.
4. Keep CrowdSec ingestion tied to the logs where real public traffic lands.
5. Periodically review whether anything still needs the older NPM path or should move behind Tunnel/Access.

The goal is not to make the homelab look like a vendor diagram. The goal is to make the public edge boring, explainable, and hard to accidentally expose.

That is a better standard.

## Sources reviewed

- [`mdziegiel/zero-trust-homelab`](https://github.com/mdziegiel/zero-trust-homelab) — README and architecture diagram.
- Private Obsidian notes covering Cloudflare Zero Trust, Access, Tunnel, WAF scope, and Cloudflare/CrowdSec operations.
- Internal documentation covering the Cloudflare routing map, Zero Trust setup, and high-level architecture overview.

## Public-safety note

The source routing map contains exact tunnel metadata, hostnames, internal destinations, a home public IP, and email-routing details. This article intentionally generalizes those details into route classes and policy patterns. The public lesson is the architecture. The private table stays private.
