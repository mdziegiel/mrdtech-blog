---
layout: default
title: All Posts
og_image: /assets/og/site-default.png
image:
  path: /assets/og/site-default.png
  width: 1200
  height: 630
  alt: MRDTech Blog branded social preview image
---

<section class="hero" aria-labelledby="blog-title">
  <p class="eyebrow">MRDTech Blog</p>
  <h1 id="blog-title">Infrastructure notes without the ceremony.</h1>
  <p class="hero-copy">Practical writing on endpoint management, automation, security, and the operational mess hiding behind most “simple” deployments.</p>
</section>

<section class="post-list" aria-label="Blog posts">
  {% for post in site.posts %}
    {% assign words = post.content | number_of_words %}
    {% assign read_time = words | divided_by: 180 | at_least: 1 %}
    <article class="post-card">
      {% if post.og_image %}
        <a class="post-thumb" href="{{ post.url | relative_url }}" aria-label="Read {{ post.title }}">
          <img src="{{ post.og_image | relative_url }}" alt="{{ post.title }} thumbnail" loading="lazy">
        </a>
      {% endif %}
      <div class="post-card-meta">
        <time datetime="{{ post.date | date_to_xmlschema }}">{{ post.date | date: "%B %-d, %Y" }}</time>
        <span aria-hidden="true">·</span>
        <span>{{ read_time }} min read</span>
      </div>
      <h2>{{ post.title }}</h2>
      <p>{{ post.excerpt | strip_html | normalize_whitespace | truncate: 190 }}</p>
      {% if post.tags %}
        <ul class="tag-list" aria-label="Tags for {{ post.title }}">
          {% for tag in post.tags %}
            <li>{{ tag }}</li>
          {% endfor %}
        </ul>
      {% endif %}
      <a class="read-link" href="{{ post.url | relative_url }}">Read the post</a>
    </article>
  {% endfor %}
</section>
