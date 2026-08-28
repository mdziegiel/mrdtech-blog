---
layout: post
title: "Job Watch: The App I Built to Automate My Own Job Search"
date: 2026-08-28
tags: [homelab, automation, self-hosted, docker, ai]
excerpt: "Job hunting is a data problem disguised as an emotional one. I built a self-hosted aggregator that scored every listing against my resume and told me the ones worth my time - here's how it worked."
---

Job hunting has a volume problem. Between LinkedIn, Indeed, company career pages, and a half-dozen niche boards, the actual signal - the two or three roles a week worth a real application - gets buried under a firehose of postings that don't match your experience, your comp floor, or even your field. I was manually triaging dozens of listings a day and losing time I needed for actually applying. So I built something to do the triage for me.

## What Job Watch does

Job Watch is a self-hosted job aggregation and scoring app I ran throughout my search that eventually landed me the Systems Administrator role at Jeanne D'Arc Credit Union. At a high level:

1. Aggregation - pulls job postings via the JSearch API on RapidAPI, which itself aggregates listings from LinkedIn, Indeed, Glassdoor, and others into a single queryable feed. One API integration instead of scraping five sites badly.
2. AI match scoring - every incoming listing gets scored against my actual resume (hosted at a dedicated resume URL) using an LLM-driven comparison, not keyword matching. The scoring model reads the job description and my experience and produces a fit score, so a listing asking for "5+ years Kubernetes" doesn't rank the same as one that actually overlaps with my AD/GPO/VMware/network background.
3. Alerting - every scored job, regardless of score, triggered a Telegram notification through a dedicated bot. I ran with alert_min_score=0 intentionally - I wanted visibility into the full scoring range, not just a filtered "good matches only" feed, so I could sanity-check the model's judgment against my own.
4. Dashboard - a running board of everything ingested and scored, so I had a single place to see search coverage over time instead of relying on memory or a spreadsheet.

## Why self-host this instead of just using job board alerts

The built-in alert features on LinkedIn/Indeed are keyword-and-title matching - they don't understand fit, they understand string overlap. I wanted something that actually read a posting the way a hiring manager reads a resume: does the substance line up, not just the nouns. Self-hosting also meant the scoring logic and my resume data stayed on infrastructure I control, not fed into a third-party recommendation engine's black box.

## The stack

Runs as a Docker Compose deployment on my homelab:

```yaml
services:
  job-watch:
    image: job-watch:latest
    container_name: job-watch
    ports:
      - "8085:8085"
    volumes:
      - job-watch-data:/data
    restart: unless-stopped

volumes:
  job-watch-data:
    external: true
```

The external: true volume declaration was a deliberate choice - I rebuilt this container more than once while iterating on the scoring prompt and alert logic, and I didn't want a docker compose down to ever take my accumulated job history and scores with it. Losing the historical dataset would've meant losing the ability to see trend data across the whole search.

Telegram alerts ran through a dedicated bot rather than piggybacking on any of my existing infrastructure alert channels - deliberately isolated so a job alert and a "your backup job failed" alert never landed in the same noisy stream. That separation turned out to matter later for reasons that had nothing to do with job hunting (a routing misconfiguration in an unrelated automation briefly fired a message through this bot's channel months after alerting was already turned off - worth its own note on why alert-channel isolation pays for itself even after you think you're done with a tool).

## Where it stands now

I landed the role. The alerting layer is decommissioned - I don't need per-job Telegram pings anymore - but the dashboard stayed up. Historical scoring data across the whole search is still worth having: it's a record of what the market actually looked like for my background over that stretch, and if I'm ever back in the market, the aggregation and scoring pipeline is already built and just needs alerting flipped back on.

Building the tool that solves your own annoying, repetitive problem is one of the better uses of a homelab. This one paid for the time it took to build it several times over.
