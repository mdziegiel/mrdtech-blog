# MRDTech Blog

Standalone Jekyll blog scaffold for `blog.mrdtech.me`.

## Proposed publishing model

- Repository: `mrdtech-blog`
- GitHub Pages source: native Jekyll build from `main`
- Custom domain: `blog.mrdtech.me`
- Publish workflow after review: add Markdown files under `_posts/`, commit, push. No GitHub Actions required.

This repo is intentionally separate from the portfolio site. The portfolio homepage and project navigation are not part of this blog.

## Local preview

When Ruby is available:

```bash
bundle install
bundle exec jekyll serve
```

GitHub Pages references:

- https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/about-github-pages-and-jekyll
- https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/creating-a-github-pages-site-with-jekyll
- https://jekyllrb.com/docs/posts/
- https://jekyllrb.com/docs/front-matter/

## OG image generation

Post thumbnails/social cards are generated from post front matter:

```bash
python3 scripts/generate_og_images.py
```

The script reads `_posts/*.md` and writes matching `assets/og/*.svg` and `assets/og/*.png` files. Use the PNG path in post front matter as `og_image`.
