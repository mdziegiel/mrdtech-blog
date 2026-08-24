---
layout: post
title: "Building a Technical Portfolio as a Modern Job Search Tool"
date: 2026-08-24
excerpt: "A practical look at why a self-hosted technical portfolio, real project writeups, and a blog can do more for infrastructure job searches than a resume alone."
og_image: /assets/og/building-technical-portfolio-modern-job-search-tool.png
og_slug: building-technical-portfolio-modern-job-search-tool
image:
  path: /assets/og/building-technical-portfolio-modern-job-search-tool.png
  width: 1200
  height: 630
  alt: Technical portfolio as a modern job search tool branded social preview image
tags:
  - Portfolio
  - Career
  - GitHub Pages
  - Job Search
---

I still think resumes matter. Unfortunately.

They are the PDF-shaped business card of the job search. Recruiters expect them, applicant tracking systems chew on them, and everyone pretends that a few bullet points can accurately represent twenty years of infrastructure work without turning into fiction.

The problem is not that resumes are useless. The problem is that resumes are mostly claims.

A technical portfolio gives you something better: proof.

Not perfect proof. Not a magic job machine. Just a public body of work that says, “I have actually built things, documented the tradeoffs, and can explain what I did without hiding behind buzzwords.”

That matters more than people admit.

## 1. The problem with resume-only job searching

A resume is compressed evidence.

You get a title, a timeline, a few tools, and maybe some carefully sanded-down accomplishment bullets. If the person writing it is honest, it is incomplete. If they are not honest, it is marketing with dates attached.

For technical roles, that is a weak signal.

A hiring manager might see:

- “managed hybrid infrastructure”
- “implemented automation”
- “supported endpoint management”
- “secured cloud services”
- “improved monitoring and alerting”

Fine. But what does that actually mean?

Did you build the thing, inherit the thing, click through a wizard, or sit in meetings while someone else built the thing? The resume usually cannot answer that. It is not designed to.

A portfolio can.

## 2. Show, do not just tell

The best technical portfolios are not vanity pages. They are evidence lockers.

When I look at a good project writeup, I want to see the shape of the work:

| Resume claim | Portfolio proof |
|---|---|
| “Built secure infrastructure” | Architecture diagram, threat model, implementation notes, tradeoffs |
| “Automated workflows” | Scripts, screenshots, repo links, before/after process description |
| “Managed endpoint migration” | Deployment approach, tooling choices, lessons learned |
| “Improved monitoring” | Dashboard screenshots, alert flow, failure modes, operational notes |

That does not mean publishing secrets, internal configs, or private topology. Please do not turn your portfolio into a breach disclosure speedrun.

It means showing enough of the work that someone technical can tell you understand it.

That is the difference between “I know automation” and “here is the automation project, here is what it does, here is why I built it this way, and here is what I would change next time.”

One of those is a sentence. The other is evidence.

## 3. Why this works for infrastructure roles

Infrastructure work is hard to explain from a resume alone because the interesting parts are usually buried under maintenance language.

The job is full of invisible work:

- cleaning up brittle systems
- replacing manual processes
- making monitoring less useless
- untangling identity and access
- documenting the thing nobody documented
- building recovery paths before the outage arrives

That work matters. It also sounds boring if you flatten it into a bullet.

A portfolio gives the work room to breathe.

Instead of trying to cram an entire migration, automation project, or security design into one line, you can give it a page. You can explain the problem, the constraints, the design, the tools, and the outcome without pretending everything was clean and cinematic.

Hiring managers do not need a novel. They need enough signal to know whether the person behind the resume can think through real systems.

## 4. What actually belongs on the portfolio

A technical portfolio does not need to be huge. It needs to be real.

The core pages I care about:

| Section | Purpose |
|---|---|
| Home page | Short positioning statement and quick links |
| Projects | Real work samples with enough technical detail to matter |
| Blog / field notes | Deeper explanations, guides, and opinionated technical writing |
| Resume link | The traditional artifact, because HR still exists |
| GitHub link | Source, scripts, templates, and public repos where appropriate |
| Contact link | Make it easy to reach you without turning the site into a scavenger hunt |

The project section is the important part.

A generic “About Me” page is fine, but it is not the payload. The payload is the work. If the portfolio is mostly adjectives about being passionate, motivated, and detail-oriented, congratulations, you rebuilt LinkedIn with extra hosting steps.

I would rather see five strong project pages than thirty vague cards.

## 5. What a good project writeup looks like

A useful project writeup answers the questions a technical interviewer is probably going to ask anyway:

1. What problem were you solving?
2. What constraints did you have?
3. What did you build or change?
4. What tools did you use?
5. What tradeoffs did you make?
6. How did you verify it worked?
7. What would you improve next?

That structure matters because it shows judgment, not just tool exposure.

Anyone can list technologies. The better signal is explaining why those technologies were chosen, where they were annoying, and what operational problem they solved.

For my own portfolio, that means project pages around infrastructure, endpoint management, automation, and security patterns. The goal is not to make every project look perfect. The goal is to make the thinking visible.

Perfect projects are suspicious anyway. Real systems have scars.

## 6. Where the blog fits

The portfolio is the map. The blog is the long-form explanation.

A project page should be skimmable. A blog post can go deeper.

That is why I like linking the two together:

```text
Portfolio project page
     |
     | deeper technical explanation
     v
Blog post / field note
     |
     | supporting source or examples
     v
GitHub repo or script
```

For example, a portfolio project might summarize a migration or architecture pattern. The blog can then explain the messy middle: why one approach was cleaner than another, what broke, what I would avoid next time, and where the official guidance is useful versus where it becomes vendor incense.

This blog exists for exactly that reason. It lets me write the practical notes that do not belong on a resume but absolutely matter in an interview.

## 7. GitHub Pages and a custom domain are enough

You do not need to become a full-time web developer to build a useful technical portfolio.

GitHub Pages is more than enough for most people:

- static HTML or Jekyll
- version-controlled content
- free hosting for public repos
- custom domain support
- simple deployment by pushing to a branch

That is the model I like because it keeps the site close to the work. If the portfolio is mostly technical writing and project pages, a static site is a feature, not a limitation.

The custom domain matters too.

A GitHub Pages URL is fine. A real domain looks more intentional. It says you treated the portfolio like an actual professional surface, not a weekend README that escaped containment.

My own split is simple:

- `portfolio.mrdtech.me` for the portfolio and project surface
- `blog.mrdtech.me` for longer technical posts and field notes
- GitHub for public source, scripts, and repos where sharing makes sense

That is not the only way to do it. It is just a clean way to separate “here is the work” from “here is the deeper writeup.”

## 8. How it helps in interviews

A portfolio does not replace interviewing. It improves the conversation.

Instead of answering every question from memory, you have concrete examples to point at:

- “Here is how I structured that project.”
- “Here is the writeup that explains the tradeoffs.”
- “Here is the repo with the script or template.”
- “Here is the part I would do differently now.”

That last one matters. Being able to explain what you would improve is usually a better signal than pretending the original version was flawless.

The portfolio gives the interviewer a trail. If they care about endpoint management, they can read those pages. If they care about automation, they can follow the repos. If they care about infrastructure design, they can look at architecture-focused writeups.

It turns the interview from pure claims into a review of actual work.

No, it does not guarantee a job offer. Nothing does. Anyone promising that is selling a course with too many emojis.

But it gives you something concrete to bring into the room.

## 9. What not to publish

A portfolio should show judgment. That includes knowing what not to put online.

Do not publish:

- internal IP ranges
- private hostnames
- credentials or token-shaped strings
- employer names where they are not appropriate
- customer-specific diagrams
- screenshots with sensitive tenant or user data
- configs copied straight from production

Sanitize aggressively.

The point is to show the pattern, the thinking, and the technical depth. It is not to publish a lovingly formatted attacker handbook.

For infrastructure people especially, this is not optional. If the portfolio leaks private topology, it does not prove competence. It proves you are one copy-paste away from an incident review.

## 10. My practical advice

If I were building one from scratch, I would keep it simple:

1. Buy or use a domain you control.
2. Put the portfolio on GitHub Pages.
3. Start with three strong project pages.
4. Add one deeper blog post for each major project area.
5. Link the portfolio, blog, resume, and GitHub together.
6. Keep the writing direct and specific.
7. Sanitize everything before it goes public.

Do not wait until the portfolio is perfect. Perfect is how projects stay unpublished.

Start with the work you can explain well. Then keep adding pages as the body of work grows.

The site should make the interview easier. It should give someone a clear path from resume bullet to project page to deeper technical writeup.

That is the whole point.

## 11. Closing

A resume tells people what you claim to have done.

A portfolio shows them how you think.

For technical roles, that distinction matters. Infrastructure, endpoint management, automation, and security work all involve judgment under constraints. A decent portfolio gives that judgment somewhere to live.

It does not need to be flashy. It does not need animation. It does not need a heroic stock photo of a laptop next to coffee.

It needs real projects, honest writeups, clean navigation, and enough technical depth that the right person can tell you know what you are doing.

That is the job-search advantage.

Not magic. Evidence.
