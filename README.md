# scrper

Apify Actor that crawls start URLs with Playwright, captures page titles, and optionally follows links up to a configurable depth.

## Running locally

```bash
pip install -r requirements.txt
python -m compileall main.py  # quick syntax check
```

## Configuration

- `start_urls`: list of objects with a `url` key to seed the crawl.
- `max_depth`: maximum link-follow depth (default: `1`).