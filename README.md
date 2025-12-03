# scrper

Apify Actor that scrapes Pinterest pages with Playwright, scrolling to collect pin metadata (title, image, URL) from the supplied search, board, or pin feed URLs.

## Running locally

```bash
pip install -r requirements.txt
python -m compileall main.py  # quick syntax check
```

## Configuration

- `start_urls`: list of objects with a `url` key pointing to Pinterest search, board, or feed pages (default: trending search feed).
- `max_pins`: maximum pins to capture per URL (default: `50`).