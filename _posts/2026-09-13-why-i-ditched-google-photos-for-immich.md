---
layout: post
title: "Why I Ditched Google Photos for Immich"
date: 2026-09-13
tags: [Immich, Self-Hosted, Homelab, Docker, Privacy, Photos]
excerpt: "Google Photos is a great product with a bad tradeoff attached to it. Here's why I moved my entire photo library to a self-hosted Immich instance, how I built it out, and how I pulled years of history over from Google without losing metadata or creating a duplicate mess."
---

Google Photos is genuinely good software. Search works, backup is automatic, and the interface doesn't get in your way. None of that changes the actual arrangement: every photo of my kids, my house, and my life was living on someone else's infrastructure, getting scanned for ad targeting and product training data as a condition of "free" unlimited backup. I didn't want to keep making that trade just because the alternative required setting up my own server. So I set up my own server.

## What I moved to

[Immich](https://immich.app/) - a self-hosted photo and video backup solution that's explicitly built to be a drop-in Google Photos replacement, not just a dumb file store. It gets you:

- Automatic background backup from the mobile app, same as Google Photos
- ML-powered face recognition and object/scene detection, run locally against my own hardware instead of a cloud API
- CLIP-based semantic search - I can type "dog on a beach" and get relevant photos back without ever having tagged anything
- Albums, shared libraries, and a timeline view that doesn't feel like a downgrade from what I was used to
- An actual data format I control - Postgres database plus files on disk, not a black box

## The stack

Four containers, deployed together:

```yaml
services:
  immich-server:
    image: ghcr.io/immich-app/immich-server:release
    volumes:
      - /data/gallery/immich:/usr/src/app/upload
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "2283:2283"
    depends_on:
      - database
      - redis

  immich-machine-learning:
    image: ghcr.io/immich-app/immich-machine-learning:release
    volumes:
      - /data/immich-ml:/cache

  redis:
    image: redis:latest
    volumes:
      - /data/immich-redis:/data

  database:
    image: tensorchord/pgvecto-rs:pg14-v0.2.0
    volumes:
      - /data/immich-db:/var/lib/postgresql/data
```

`immich-server` handles the API, upload ingestion, and web/mobile-facing app. `immich-machine-learning` runs the CLIP embeddings and facial recognition models against uploaded assets - the part that makes search and face-grouping work without a cloud dependency. Postgres (with the `pgvecto-rs` extension for vector similarity search) backs the metadata and embeddings; Redis handles job queuing between the server and ML workers. All four volumes are bind-mounted to paths I control, not named Docker volumes buried in `/var/lib/docker` - if I ever need to move this to different hardware, the data walks with me by just copying those directories.

## Getting the mobile app talking to it safely

Immich's real value only shows up if your phone backs up to it automatically, the same way Google Photos does. That means the mobile app needs to reach the server from outside your LAN - which means it's internet-facing, which means it needs to be locked down properly, not just port-forwarded and hoped for.

My instance sits behind Cloudflare Zero Trust Access, same as most of my other self-hosted apps. The wrinkle: Access's normal browser-based email OTP challenge works fine for me logging in from a laptop, but the Immich mobile app can't complete an interactive login challenge in the background when it wakes up to backup a new photo. Immich's developers actually solved this one for me - the app has native support for **custom proxy headers**, so instead of trying to make the mobile client behave like a browser, I gave it its own machine-to-machine credential:

1. Created a Cloudflare Access **Service Token** (Access → Service Auth → Service Tokens) scoped to the Immich application - generates a Client ID and Client Secret.
2. Added a second policy to the existing Immich Access application: `Service Token` → Allow, alongside the existing `Email` → Allow policy used for browser logins.
3. In the Immich mobile app: Settings → Advanced → Custom Proxy Headers, and added `CF-Access-Client-Id` and `CF-Access-Client-Secret` as header/value pairs.

Now the phone authenticates with a long-lived service credential instead of a human login flow, browser access still goes through the normal email challenge, and I never had to stand up a second Access application or punch a hole for a "public API path" the way some self-hosted apps force you to.

## Migrating years of Google Photos history in

Standing up Immich for new photos going forward was the easy part. The harder problem was getting everything already sitting in Google Photos over without ending up with either gaps or a duplicate mess.

**Why not just re-upload everything?** Two reasons that would've wrecked a naive import:

1. Google re-encodes some photos on upload (historically anything sent at "Storage saver" quality), so the file coming back out of Google Photos isn't always byte-identical to what may already be sitting in Immich from a direct-from-phone backup. A checksum-only dedup misses these.
2. Google Takeout - the official export tool - strips capture timestamps, GPS, and other metadata out of the actual media files and drops them into separate per-asset `.json` sidecar files instead. Anything that just uploads the media files and ignores the sidecars ends up with every photo dated "whenever I ran the import," which quietly destroys your actual timeline.

I skipped Immich's built-in Google Photos importer and used **[immich-go](https://github.com/simulot/immich-go)**, a third-party CLI purpose-built for this migration. It correctly parses the Takeout JSON sidecars and reattaches the real capture date, GPS, and description metadata Google split out; it queries the Immich API for existing checksums before uploading so exact duplicates are skipped client-side instead of wasting transfer time; and it has specific handling for edited-photo pairs and Google's partitioned zip exports (large libraries get split across multiple archives, and albums can straddle that boundary if you're not careful).

The actual migration:

1. **Export via Google Takeout**, Google Photos only, with a large per-archive size cap to minimize a single album getting split across multiple zip files.
2. **Extract every zip into one flat staging directory** before running anything against it - if albums span archive boundaries, you want them merged back into one filesystem view first.
3. **Run immich-go in dry-run mode first**, pointed at the Immich API URL and an API key, to see the projected counts: new imports, skipped-as-duplicate, and errors, before committing to anything.
4. **Run it for real**, then let Immich's background **Duplicate Detection** job (Utilities → Duplicates, in the admin panel) do the second pass - this uses perceptual hashing on top of the ML embeddings to catch the re-encoded near-duplicates that checksum comparison can't, and surfaces them for a manual merge/review instead of silently auto-deleting anything.
5. **Spot-check a sample of imported albums** for correct dates and GPS data - this is exactly where a sidecar-parsing failure would show up if something had gone wrong.

That admin-reviewed duplicate step is deliberate on Immich's part, not a missing feature. Perceptual similarity has real false positives - burst shots, near-identical framing, genuinely different photos that just look alike - so Immich flags candidates instead of auto-merging them. I'd rather spend twenty minutes confirming matches in batches than trust a fully automatic pass to make that call for me.

## Where it stands now

My phone backs up to my own server the same way it used to back up to Google's, Google Takeout got everything historical pulled over with real dates and locations intact, and searching my library by describing what's in the photo works without me ever running a tagging pass. The tradeoff I was making with Google Photos - convenience for control - is gone. I kept the convenience and took the control back.
