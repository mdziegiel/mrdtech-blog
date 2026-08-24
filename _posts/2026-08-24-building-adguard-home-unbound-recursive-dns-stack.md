---
layout: post
title: "Building an AdGuard Home + Unbound Recursive DNS Stack"
date: 2026-08-24
excerpt: "A practical walkthrough for using AdGuard Home as the filtering layer and Unbound as a dedicated recursive resolver instead of forwarding everything to public DNS."
og_image: /assets/og/adguard-unbound-recursive-dns-stack.png
og_slug: adguard-unbound-recursive-dns-stack
image:
  path: /assets/og/adguard-unbound-recursive-dns-stack.png
  width: 1200
  height: 630
  alt: AdGuard Home and Unbound recursive DNS stack branded social preview image
tags:
  - AdGuard Home
  - Unbound
  - DNSSEC
  - Homelab
---

I used to point everything at public DNS and call it good enough.

Cloudflare, Google, Quad9 — pick your flavor. They're fast, they're reliable, and they make DNS someone else's problem. Which is attractive right up until you remember that DNS is one of the best visibility points in a network, and outsourcing all of it means handing someone else a clean little diary of what your clients are trying to resolve.

That doesn't mean public resolvers are evil. It means I don't want them to be the default answer when I can run the boring plumbing myself.

The stack I like is simple:

- **AdGuard Home** handles filtering, client policy, blocklists, allowlists, rewrites, and local DNS behavior.
- **Unbound** handles recursive resolution directly against the DNS hierarchy.
- Clients only talk to AdGuard.
- AdGuard only forwards normal recursive lookups to Unbound.

No magic. No DNS over-marketing. Just a clean split between policy and resolution.

## 1. Why recursive DNS instead of forwarding

Forwarding is the easy button.

A client asks AdGuard for `example.com`, AdGuard forwards that question to a public resolver, and the public resolver does the recursive work. That is fine for a lot of networks. It is also not really self-hosted DNS. It is self-hosted filtering bolted onto someone else's resolver.

Recursive resolution changes the chain.

Instead of asking a public resolver to go find the answer, Unbound walks the DNS hierarchy itself:

1. Ask the root servers where `.com` lives.
2. Ask the `.com` servers where `example.com` lives.
3. Ask the authoritative nameservers for the actual record.
4. Cache the answer locally for the next client that asks.

That gives me a few things I care about:

- I am not sending every lookup to one upstream company by default.
- I can validate DNSSEC locally.
- I can keep filtering policy in AdGuard without making AdGuard responsible for recursion.
- I can tune privacy settings like QNAME minimization and ECS behavior at the resolver.

There are tradeoffs. First lookup latency can be a little higher until cache warms up. You also have to maintain the resolver properly, because apparently infrastructure does not maintain itself no matter how many dashboards you give it.

Still worth it.

Useful references:

- [Unbound documentation](https://unbound.docs.nlnetlabs.nl/en/latest/)
- [AdGuard Home upstream DNS servers](https://github.com/AdguardTeam/AdGuardHome/wiki/Configuration#upstreams)
- [Root Servers](https://www.iana.org/domains/root/servers)

## 2. The architecture

I do not put filtering and recursion in the same mental bucket.

Filtering is policy. Recursion is resolution. Mixing those responsibilities makes troubleshooting annoying, and annoying DNS is how you end up staring at packet captures at midnight like a cursed raccoon.

This Jekyll site is using kramdown/Rouge and does not advertise diagram-renderer support, so plain text wins.

```text
Client devices
     |
     | DNS queries
     v
AdGuard Home
10.0.0.10:53
     |
     | upstream DNS
     v
Unbound recursive resolver
10.0.0.20:5335
     |
     | iterative resolution
     v
Root servers -> TLD servers -> authoritative servers
```

The important part is the direction of trust:

- Clients trust AdGuard for DNS.
- AdGuard trusts Unbound for recursive answers.
- Unbound does not forward normal lookups to Cloudflare, Google, or some other public resolver.
- Internal-only names can be answered locally before they ever leave the network.

That last point matters. Internal DNS leakage is sloppy. Sloppy is how future-you ends up apologizing to present-you.

## 3. Example addressing

Use whatever addressing makes sense in your environment. For this post, I am using fake lab addresses:

| Component | Example address | Purpose |
|---|---:|---|
| AdGuard Home | `10.0.0.10:53` | Client-facing DNS and filtering |
| Unbound | `10.0.0.20:5335` | Recursive resolver for AdGuard |
| Internal zone | `home.arpa` | Placeholder split-DNS zone |

Those are placeholders. Do not cargo-cult them into production unless your network actually matches them. Even then, maybe don't. Think first. It's free.

## 4. Unbound as the recursive resolver

Unbound is the resolver. It should listen on an address AdGuard can reach, and it should recurse directly instead of forwarding to a public resolver.

A minimal conceptual Unbound configuration looks like this:

```conf
server:
  interface: 0.0.0.0
  port: 5335

  access-control: 10.0.0.0/24 allow

  do-ip4: yes
  do-ip6: no
  do-udp: yes
  do-tcp: yes

  # Privacy and correctness
  qname-minimisation: yes
  harden-glue: yes
  harden-dnssec-stripped: yes
  use-caps-for-id: no

  # DNSSEC validation
  auto-trust-anchor-file: "/var/lib/unbound/root.key"

  # Do not leak client subnet data upstream
  send-client-subnet: 0.0.0.0/0
```

The exact file path depends on how you install Unbound. Package install, container, jail, VM — pick your poison. The logic is the same.

The settings I care about most:

| Setting | Why it matters |
|---|---|
| `port: 5335` | Keeps Unbound separate from AdGuard's client-facing port 53 |
| `qname-minimisation: yes` | Sends the minimum necessary query name at each step of recursion |
| `auto-trust-anchor-file` | Enables DNSSEC trust anchor management |
| `send-client-subnet: 0.0.0.0/0` | Prevents ECS from being sent upstream |
| no `forward-zone` for `.` | Keeps Unbound recursive instead of turning it into a forwarding resolver |

That last one is the big one. If you configure Unbound to forward `.` to a public resolver, you built a forwarder. Not a recursive stack. Different thing.

## 5. DNSSEC validation

DNSSEC is not encryption. It does not hide the query. It validates that the answer is authentic according to the DNSSEC chain of trust.

That distinction matters because people routinely treat DNSSEC like it is privacy pixie dust. It isn't. It is integrity.

For Unbound, I want the root trust anchor initialized and maintained. Depending on the platform, that may be handled by the package or by a command like this:

```bash
unbound-anchor -a /var/lib/unbound/root.key
```

Then I verify DNSSEC behavior with known test domains:

```bash
dig @10.0.0.20 -p 5335 dnssec.works A
```

For a deliberately broken DNSSEC domain, I expect failure:

```bash
dig @10.0.0.20 -p 5335 dnssec-failed.org A
```

If the broken domain resolves cleanly, DNSSEC validation is not doing what you think it is doing. DNS will happily let you be wrong with confidence. It has a gift for that.

Useful references:

- [Unbound DNSSEC howto](https://unbound.docs.nlnetlabs.nl/en/latest/topics/core/dnssec.html)
- [DNSSEC Failed test domain](https://dnssec-failed.org/)

## 6. ECS disabled

ECS means EDNS Client Subnet.

The idea is that a resolver can include part of the client subnet in upstream queries so large providers can return geographically optimized answers. That can help CDNs. It can also leak more client-network context than I want leaving the resolver.

For a small self-hosted stack, my default is simple:

```conf
send-client-subnet: 0.0.0.0/0
```

That says: do not send ECS upstream.

Will this occasionally make CDN routing slightly less perfect? Maybe. Will I survive? Somehow, yes.

## 7. QNAME minimization

QNAME minimization is one of those settings that sounds academic until you think about what recursive DNS actually does.

Without minimization, more of the full query name can be exposed to more of the DNS hierarchy than necessary. With minimization, the resolver asks only what each layer needs to know.

Example:

```text
Instead of exposing:
very-specific-hostname.service.example.com

to every step, the resolver walks down only as needed:
. -> com -> example.com -> service.example.com
```

In Unbound:

```conf
qname-minimisation: yes
```

It is not a silver bullet. It is just less sloppy. I like less sloppy.

## 8. AdGuard upstream DNS pointed at Unbound

AdGuard Home should be the only DNS server your clients know about.

In AdGuard, set the upstream DNS server to Unbound:

```text
10.0.0.20:5335
```

Then set the bootstrap DNS servers only if your upstream uses hostnames. In this design, the upstream is an IP and port, so bootstrap is not the interesting part.

The flow should be:

```text
client -> 10.0.0.10:53 -> 10.0.0.20:5335 -> recursive DNS hierarchy
```

What I do not want:

```text
client -> AdGuard -> Cloudflare
client -> AdGuard -> Google
client -> random fallback resolver because someone clicked a checkbox at 1:00 AM
```

AdGuard is excellent at filtering and visibility. Let it do that. Let Unbound do recursion. Division of labor. Civilization depends on it.

## 9. Split-DNS for internal hostnames

Internal names should resolve internally.

If I have a local-only zone like `home.arpa`, I do not want those queries wandering out to the public DNS hierarchy where the answer is either nonexistent or embarrassing.

There are two common ways I handle it:

| Method | Best for |
|---|---|
| AdGuard DNS rewrites | Simple hostnames and a small number of records |
| Unbound local zones | Larger local zones or resolver-side authority |

For small environments, AdGuard rewrites are easy:

```text
service.home.arpa -> 10.0.0.50
nas.home.arpa     -> 10.0.0.60
```

For Unbound-side local zones, the shape is more like this:

```conf
server:
  local-zone: "home.arpa." static
  local-data: "service.home.arpa. 300 IN A 10.0.0.50"
  local-data: "nas.home.arpa. 300 IN A 10.0.0.60"
```

Pick one place to own the records. Do not create split-brain DNS inside your split-DNS design. That is not architecture. That is a haunted house.

## 10. Client configuration

Clients should point to AdGuard, not Unbound.

That usually means DHCP hands out:

```text
DNS server: 10.0.0.10
```

Not both AdGuard and Unbound. Not AdGuard plus a public resolver as a backup. That “backup” becomes a bypass the first time a client decides to use it.

If I want redundancy, I build a second AdGuard/Unbound pair and hand out both filtering endpoints:

```text
DNS server 1: 10.0.0.10
DNS server 2: 10.0.0.11
```

Each filtering endpoint should still send recursive lookups to a controlled resolver. The goal is resilient policy, not an accidental escape hatch.

## 11. Verification with dig

Once the stack is wired, I test each layer separately.

### Test Unbound directly

```bash
dig @10.0.0.20 -p 5335 example.com A
```

I want a valid answer from Unbound.

### Test AdGuard path

```bash
dig @10.0.0.10 example.com A
```

I want the same general resolution path, but now through the filtering layer.

### Test DNSSEC validation

```bash
dig @10.0.0.20 -p 5335 dnssec-failed.org A
```

I expect this to fail when validation is working.

### Test internal split-DNS

```bash
dig @10.0.0.10 service.home.arpa A
```

Expected placeholder answer:

```text
service.home.arpa. 300 IN A 10.0.0.50
```

### Test that clients are using AdGuard

From a client:

```bash
nslookup example.com 10.0.0.10
```

Then check AdGuard's query log. If the client is not visible there, it is not using the path you think it is using. DNS clients lie by omission. Routers lie by default. Operating systems lie because they can.

## 12. Common mistakes

A few ways this stack gets screwed up:

| Mistake | Why it is bad |
|---|---|
| AdGuard forwards to public DNS | You lose the recursive design and centralize lookup visibility upstream |
| Clients get Unbound directly | They bypass filtering and policy |
| Clients get public DNS as secondary | They bypass filtering whenever they feel like it |
| ECS left enabled accidentally | More client-network context leaks upstream |
| No split-DNS plan | Internal names leak or fail inconsistently |
| DNSSEC assumed but not tested | Integrity validation becomes decorative |

The secondary DNS mistake is especially common. People put a public resolver in there as a fallback and then act surprised when filtering is inconsistent.

It is not a fallback. It is a bypass.

## 13. Closing

AdGuard Home plus Unbound is not complicated, which is why I like it.

AdGuard owns the policy:

- filtering
- client visibility
- local rewrites
- blocklists and allowlists

Unbound owns the recursion:

- root/TLD/authoritative resolution
- DNSSEC validation
- QNAME minimization
- no ECS leakage
- local cache

That separation keeps the design understandable. More importantly, it keeps troubleshooting from becoming interpretive dance.

If I am building DNS for a homelab or small environment, this is the pattern I reach for first: clients talk to the filter, the filter talks to the resolver, and the resolver does the actual recursive work.

Boring. Controlled. Observable.

Exactly how DNS should be.
