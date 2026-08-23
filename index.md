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

<section class="blog-intro" aria-labelledby="blog-title">
  <p class="eyebrow">MRDTech Blog</p>
  <h1 id="blog-title">Infrastructure notes without the ceremony.</h1>
  <p>Practical writing on endpoint management, automation, security, and hybrid cloud infrastructure.</p>
</section>

<section class="article-index" aria-labelledby="article-index-title">
  <h2 id="article-index-title">Articles</h2>
  <ol class="article-list">
  {% for post in site.posts %}
    <li>
      <a class="article-row" href="{{ post.url | relative_url }}">
        <span class="article-row-inner">
          <span class="article-title">{{ post.title }}</span>
          <span class="article-excerpt">{{ post.excerpt | strip_html | normalize_whitespace }}</span>
        </span>
        <time class="article-meta" datetime="{{ post.date | date_to_xmlschema }}">{{ post.date | date: "%b %-d, %Y" }}</time>
      </a>
    </li>
  {% endfor %}
  </ol>
</section>
