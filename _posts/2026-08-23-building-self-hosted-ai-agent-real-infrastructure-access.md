---
layout: post
title: "Building a Self-Hosted AI Agent with Real Infrastructure Access"
date: 2026-08-23
excerpt: "How I built a self-hosted AI agent with scoped infrastructure visibility, a read-only tool gateway, Obsidian-backed retrieval, delegated coding runtimes, and hard lessons from a real bind-mount incident."
og_image: /assets/og/building-self-hosted-ai-agent-real-infrastructure-access.png
og_slug: building-self-hosted-ai-agent-real-infrastructure-access
image:
  path: /assets/og/building-self-hosted-ai-agent-real-infrastructure-access.png
  width: 1200
  height: 630
  alt: Self-hosted AI agent infrastructure access branded social preview image
tags:
  - AI Agents
  - Infrastructure
  - Security
  - Automation
---

A chat window is fine if all you want is text.

That was not what I wanted.

I wanted an agent that could look at the real environment, read the actual documentation, check live state, run controlled diagnostics, update repos, maintain notes, and tell me what it found without pretending a guess was evidence. By agent, I mean software that can use tools and follow a workflow, not just a chatbot that replies with advice. Basically: less "AI assistant" and more junior infrastructure operator with enough supervision to avoid becoming an incident report.

I call the agent Gilfoyle, after the *Silicon Valley* character: deadpan, technically excellent, allergic to bullshit. The name stuck because it fits the personality I gave it better than any actual AI product name would.

That became the system this post is about: a self-hosted Hermes agent wired into a real homelab, with real infrastructure visibility and a deliberately boring security model.

The public-safe build notes live in [`mdziegiel/mrdtech-hermes-stack`](https://github.com/mdziegiel/mrdtech-hermes-stack). The most useful docs are the numbered ones:

- [`01-hermes-setup.md`](https://github.com/mdziegiel/mrdtech-hermes-stack/blob/main/docs/01-hermes-setup.md)
- [`02-obsidian-vault.md`](https://github.com/mdziegiel/mrdtech-hermes-stack/blob/main/docs/02-obsidian-vault.md)
- [`03-mcp-gateway.md`](https://github.com/mdziegiel/mrdtech-hermes-stack/blob/main/docs/03-mcp-gateway.md)
- [`04-rag-pipeline.md`](https://github.com/mdziegiel/mrdtech-hermes-stack/blob/main/docs/04-rag-pipeline.md)
- [`05-telegram.md`](https://github.com/mdziegiel/mrdtech-hermes-stack/blob/main/docs/05-telegram.md)
- [`06-dual-model-delegation.md`](https://github.com/mdziegiel/mrdtech-hermes-stack/blob/main/docs/06-dual-model-delegation.md)
- [`07-gbrain.md`](https://github.com/mdziegiel/mrdtech-hermes-stack/blob/main/docs/07-gbrain.md)

Those docs are not a marketing diagram. They were built from live config, service state, code on disk, and retained session history. Where something was not fully proven, the docs say so. A radical concept.

## 1. Why not just use a chat window?

Because chat windows are usually disconnected from the things I actually need to operate.

If I ask, "why is this service down," I do not want a confident paragraph about common causes. I want the agent to check the service, read the logs, compare the current config to the documented config, inspect the last deployment, and tell me exactly where the failure is.

That is the difference between an LLM, meaning the language model generating the reasoning and text, and an operator workflow, meaning the surrounding tools and guardrails that let it inspect real systems.

The Hermes/Gilfoyle setup gives the model tools, memory, scheduled jobs, skills, shell access, GitHub workflows, and retrieval over internal documentation. Retrieval means it can search written notes and docs before answering instead of relying on whatever context is still in the chat. The local Obsidian note `Wiki/hermes.md` describes Hermes as the operational agent layer for MRDTech: it runs terminal and file operations, manages cron jobs, queries infrastructure APIs, updates GitHub repositories, maintains WikiDocs and Obsidian notes, and executes scripted monitoring jobs.

That is the actual motivation. Not novelty. Not "AI because AI." I wanted a controllable operational layer that could do the boring work and cite what it touched.

## 2. Architecture overview: the MCP gateway

The most important part of the architecture is the read-only MCP gateway. MCP is the Model Context Protocol: a standard way to expose tools and data sources to an AI agent. In this setup, the gateway is the controlled broker between Gilfoyle and infrastructure systems, not a free-for-all admin socket. See [`03-mcp-gateway.md`](https://github.com/mdziegiel/mrdtech-hermes-stack/blob/main/docs/03-mcp-gateway.md).

Gilfoyle reaches a Docker MCP gateway through a local SSH tunnel. The gateway itself binds only to loopback on the infrastructure side, so it listens only on the local machine instead of the whole network. There is no general LAN-exposed "please automate my production network" endpoint sitting there like a piñata full of credentials.

The gateway currently fronts six read-only backends:

| Backend | Purpose | Tool count documented |
|---|---:|---:|
| Portainer | Stack, stack status, and container inventory visibility | 3 |
| GitHub | Repo, issue, PR, Actions, and context visibility | 28 |
| Filesystem | Read-only approved filesystem paths | 9 |
| Proxmox | VE read/list/get/status visibility | 153 |
| PBS | Datastore, snapshot, verification, GC, and task-log visibility | 7 |
| Vault search | Vault search and document retrieval | 2 |
| **Total** |  | **202** |

That gives Gilfoyle visibility across Docker, source control, hypervisor state, backup state, and documentation retrieval without giving it a generic write surface. In plain terms: it can inspect a lot, but it cannot casually mutate everything it can see.

The public docs intentionally use placeholders like `[HERMES_HOST]` and `[INFRA_HOST]`. That is not coy. It is hygiene. Internal IPs and hostnames do not need to be in a public repo so someone can understand the architecture.

## 3. Security model: boring on purpose

The security model is layered.

First, transport is narrow. Hermes talks to the gateway through a local-forwarded loopback endpoint. The gateway binds to loopback on the infrastructure host. If you are not on the agent host with the SSH tunnel, you do not have a path to the gateway.

Second, every backend is scoped read-only where possible:

- Portainer is a minimal custom wrapper with only a few read-oriented tools.
- GitHub runs with read-only mode and limited toolsets.
- Filesystem visibility is constrained to approved paths and mounted read-only.
- Proxmox uses restricted API/token posture plus tool allowlisting.
- PBS uses a custom GET-only wrapper.
- Vault RAG exposes search/get behavior, not mutation.

Third, the containers themselves are hardened. The gateway docs call out the important flags:

```yaml
read_only: true
cap_drop:
  - ALL
security_opt:
  - no-new-privileges:true
```

And for backend containers:

```yaml
read_only: true
cap_drop:
  - ALL
security_opt:
  - no-new-privileges:true
```

The exact Compose files in the private live stack obviously are not pasted into this blog. The public point is the posture: loopback-only transport, SSH tunnel, read-only tool surfaces, dropped Linux capabilities, no privilege escalation, and secrets kept on the gateway side instead of scattered through the agent config.

None of that makes it magic. It makes it less stupid.

## 4. RAG pipeline and Obsidian vault integration

The second important part is retrieval.

A useful infrastructure agent needs memory, but not the mystical kind. It needs searchable documentation that was written down when things happened.

The Obsidian vault is the working knowledge space. [`02-obsidian-vault.md`](https://github.com/mdziegiel/mrdtech-hermes-stack/blob/main/docs/02-obsidian-vault.md) separates the private vault from the public WikiDocs surface and documents how Gilfoyle uses the vault for running memory, session notes, and mirrored documentation.

The standing rule in the Gilfoyle configuration is simple: before answering questions about past incidents, fixes, configurations, or homelab history, search the vault and ground the answer in results.

The RAG side is documented in [`04-rag-pipeline.md`](https://github.com/mdziegiel/mrdtech-hermes-stack/blob/main/docs/04-rag-pipeline.md). RAG means retrieval-augmented generation: search the docs first, then use the model to answer with that retrieved context. The pipeline is:

1. collect source Markdown from the vault,
2. stage and redact it,
3. embed through Ollama using `nomic-embed-text`,
4. upsert into Qdrant with deterministic UUID5 chunk IDs,
5. query with `vault_search.py`, returning `source_path` with results.

The redaction layer matters. Internal host details and RFC1918 addresses are tokenized before public-safe publication. The docs also call out `gitleaks detect --no-git` as part of the safety check.

This is what changes the agent from "guess what I probably did last month" to "search the note from last month and cite the source path." It still needs judgment. It just starts from evidence instead of vibes.

## 5. Dual-model delegation

Gilfoyle is not just one model trying to do everything.

Dual-model delegation means Hermes can route different work to different AI runtimes instead of pretending one model is the correct hammer for every nail. Some tasks are better handled by a coding-focused runtime. Some are better handled by the main agent staying in control and using tools directly.

[`06-dual-model-delegation.md`](https://github.com/mdziegiel/mrdtech-hermes-stack/blob/main/docs/06-dual-model-delegation.md) documents the current state carefully:

- Claude Code is installed and authenticated in the environment.
- A standalone Codex CLI binary was not provable during that documentation pass.
- Hermes itself contains Codex runtime support code.
- Historical config snapshots showed `openai-codex` as a model provider.
- Current delegation config keeps explicit controls such as `subagent_auto_approve: false`, limited spawn depth, and bounded concurrent children. In normal English: helper agents do not get automatic approval to run wild.

So the honest version is this: Claude Code and Codex are both part of the larger workflow story, but not in the same way.

Claude Code is the locally installed external coding runtime. Codex support exists inside Hermes core and has historical provider evidence. Delegation is intentionally not treated as "always send X to Y." Different tasks benefit from different runtimes. Code-heavy work, review-heavy work, long-running implementation, and quick diagnostics do not all need the same execution path.

The important part is not brand loyalty. The important part is routing work to the runtime that can do it best while keeping approval and sandbox behavior explicit.

## 6. The incident: `/data/compose` and the problem with scope-blind approval

This is the part I would rather not have learned the hard way.

A helper container was run with a bind mount of the compose root into the container:

```bash
docker run --rm --entrypoint sh \
  -v /data/compose:/target \
  -v /tmp/source-tree:/src:ro \
  alpine -c 'for id in ...; do rm -rf /target/$id; mkdir -p /target/$id; cp -a /src/. /target/$id/; done'
```

That is the sanitized shape. The real command used a root compose mount and a loop variable. The variable collapsed in the wrong shell context. The effective target became the parent path, not the intended stack directory.

That is how you turn a helper container into a data-loss machine.

The operational lesson was not "be more careful." That is what people say right before they repeat the same failure.

The real root cause was that the dangerous-command guard understood destructive verbs better than destructive scope. It could recognize things like recursive delete, but the specific disaster class was a helper container mounting a parent directory that contained many stacks. The danger was not just `rm -rf`. The danger was `docker run -v /data/compose:/target ...` combined with any write path inside the helper container.

The fix was structural.

Hermes now has a dangerous-command pattern that catches `docker run` commands bind-mounting the compose parent instead of a specific stack subdirectory:

```python
DANGEROUS_PATTERNS = [
    (r'\brm\s+(-[^\s]*\s+)*/', "delete in root path"),
    (r'\brm\s+-[^\s]*r', "recursive delete"),
    (r'\brm\s+--recursive\b', "recursive delete (long flag)"),
    (r'docker\s+run\b[^\n]*-v\s+/data/compose(?::|\s)(?!/data/compose/[A-Za-z0-9_.-]+[:\s])', "unsafe compose bind mount (root/parent, not a specific stack subdirectory)"),
]
```

That pattern was tested both ways.

The bad parent mount now prompts for approval:

```text
command : docker run --rm -u 0 -v /data/compose:/target --entrypoint sh alpine -c "cp /src /target/docker-compose.yml"
verdict : ask-approval
rule    : unsafe compose bind mount (root/parent, not a specific stack subdirectory)
```

A specific stack subdirectory is allowed:

```text
command : docker run --rm -u 0 -v /data/compose/26:/target --entrypoint sh alpine -c "cp /src /target/docker-compose.yml"
verdict : allow
```

There is also now a durable operating rule: no helper container gets the compose root or any multi-stack parent. Every compose bind mount must target one exact stack directory. Before any `docker run` with a bind mount under that tree, print the resolved literal target as a separate preflight step. Any destructive path built from a loop variable has to validate the variable first:

```bash
: "${id:?id is unset}"
```

That is the difference between "I promise I will be careful" and "the command fails before the variable can collapse into a parent path."

Satan respects preflight checks. Barely.

## 7. The skills catalog

The skills catalog is the part of the system that makes Gilfoyle less dependent on whatever context happens to be in the current chat. A skill is a reusable procedure the agent can load for a specific class of work, like GitHub operations, infrastructure verification, or public-safe documentation.

The catalog lives at [`docs/skills/README.md`](https://github.com/mdziegiel/mrdtech-hermes-stack/blob/main/docs/skills/README.md). It tracks installed Hermes skills and plugin-provided skills with evidence notes, source provenance, install-date confidence, and gaps.

There is a documentation wrinkle worth calling out because it is exactly the kind of thing that should not be hidden: the catalog refresh hit a documented 488-row scale, then the review removed offensive/exploitation-oriented skills in two passes. The commit history shows:

```text
Refresh skills catalog: 450 -> 488 rows
Remove 40 offensive/exploitation skills, refresh catalog: 488 -> 448 rows
Remove 6 more offensive skills found in second review pass: 448 -> 442 rows
```

The current `docs/skills/README.md` header still says `Total rows: 488`, while the actual table count in the checked file is lower after the removal commits. That is documentation drift, and it should be fixed in the repo.

The security decision is the more interesting part: not every available skill belongs in an infrastructure operator's working set. A skill catalog is power. Power includes bad ideas with nice YAML front matter.

Some offensive-security skills are useful in the right authorized context. Some do not belong preloaded into an agent that has real operational access to a production-style environment. Removing them was not anti-security. It was security.

## 8. What is next

The open items are mostly boring, which means they are probably the right ones.

- Clean up the skills catalog count drift so the header and actual inventory agree.
- Rename or document the MCP gateway stack naming drift; it started life as a Portainer read-only gateway and grew into a six-backend gateway.
- Keep reducing broad backend risk, especially where third-party MCP servers are wider than the exact use case.
- Finish tightening public/private documentation boundaries between Obsidian, WikiDocs, and public GitHub repos.
- Keep the approval system focused on scope, not just verbs.
- Decide how much of the dual-model delegation story should be public once the Codex side is fully proven in the current runtime. [NEEDS INPUT: confirm whether to publish a follow-up with live Codex configuration details after that state is re-verified.]

The bigger direction is simple: make Gilfoyle more useful without making it more dangerous.

That means better retrieval, better scoping, better preflight checks, better source-backed documentation, and fewer places where a model can do the wrong thing quickly.

Which is, unfortunately, what infrastructure has always been about.
