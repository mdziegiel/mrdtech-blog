---
layout: post
title: "Building a Self-Hosted Collaboration Board: Notes, Tasks, Places, and a Shared Calendar"
date: 2026-10-27
excerpt: "One shared board for notes, tasks, places, and a calendar, with real accounts, running on my own hardware - here's how it's built."
og_image: /assets/og/building-a-self-hosted-collaboration-board.png
og_slug: building-a-self-hosted-collaboration-board
image:
  path: /assets/og/building-a-self-hosted-collaboration-board.png
  width: 1200
  height: 630
  alt: Building a Self-Hosted Collaboration Board branded social preview image
tags:
  - Self-Hosted
  - Homelab
  - ASP.NET Core
  - Vue
  - Docker
---

I wanted one shared board for a small group: notes, a task list, places we want to try, and a calendar. It needed real accounts, so everything shows who added it, and it had to run on my own hardware. So I built it.

## What it does

Each board has three things people add to: Notes, Tasks, and Places. Places get a rating and a visited / want-to-go status. Every item carries a colored dot for whoever created it. A Calendar tab pulls in Google Calendar events, and a dashboard landing page pins the important items and shows who's online.

## The stack

ASP.NET Core Web API with EF Core on the back, Vue 3 with Vite on the front, SQLite for storage. It's two containers in a Docker Compose stack, deployed through Portainer on my Docker host. SQLite is plenty for a handful of users, and a single file is easy to back up.

## Auth: cookies, not JWTs

I went with HttpOnly session cookies instead of JWTs, because I wanted logout to actually revoke the session on the server. Passwords are hashed with Argon2id. The first account that registers becomes the admin.

Authorization comes only from board membership. A board's creator field is audit data and never grants access.

## Boards and invites
Nobody can browse boards. You either create one or join with an invite link. Invites are token-based and can be shared as a link or sent by email. A user with no board gets a simple choice screen: create one or join one. There's also an admin panel for managing users and boards, resetting passwords, and granting or revoking admin.

## The calendar

Google Calendar connects over OAuth. The Month, Week, Day, and Agenda views all read from the same query, so they can't disagree with each other. New events get written back to Google.

The app reads from my primary calendar plus any secondary calendars I enable, but it writes only to the primary one. That's deliberate. A bug in my code shouldn't be able to put events on a calendar I didn't pick.

## Two color systems that stay separate

Notes, Tasks, Places, and Events each have a category color. Every user also picks one identity color for their attribution dot. These two systems never share colors, so a dot always means a person and a color band always means a category.

The UI has 10 themes, ported from my NOC dashboard as CSS variables. I checked each one for WCAG AA contrast. The default theme uses the same palette as this blog.

## Pinning and reordering

The dashboard has a pinned zone with four independent rows: Notes, Tasks, Places, and Events. Each scrolls horizontally. Drag to reorder, and a Save / Discard bar appears so nothing changes until you confirm. Notes also have an emoji picker.

## Presence and notifications

The "Right Now" panel shows who's online, based on a heartbeat every 45 seconds and on window focus. Anyone seen in the last 2 minutes counts as online.

For notifications, there's an in-app bell with per-user read state, plus Web Push with VAPID keys, a service worker, and multiple devices per user. I skipped email. It would have meant sending from my personal Gmail or setting up a throwaway account just to send. Tasks can also be assigned to several people at once.

Source: github.com/mdziegiel/mrdtech-collab-hub
