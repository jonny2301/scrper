"""Pinterest scraper Actor that collects pin metadata from provided URLs."""

from __future__ import annotations

from urllib.parse import urljoin

from apify import Actor
from playwright.async_api import async_playwright

DEFAULT_START_URLS = [
    {'url': 'https://www.pinterest.com/search/pins/?q=pinterest%20trends'},
]


async def scrape_pins_from_url(page, url: str, max_pins: int) -> list[dict]:
    """Visit a Pinterest URL, scroll, and collect pin metadata."""
    await page.goto(url)

    seen_hrefs: set[str] = set()
    pins: list[dict] = []
    stagnant_scrolls = 0

    while len(pins) < max_pins and stagnant_scrolls < 4:
        cards = await page.locator('a[href^="/pin/"]').all()
        new_pins_found = False

        for card in cards:
            href = await card.get_attribute('href')
            if not href or href in seen_hrefs:
                continue

            seen_hrefs.add(href)
            pin_url = urljoin('https://www.pinterest.com', href)
            title = await card.get_attribute('aria-label') or (await card.text_content()) or ''

            image_locator = card.locator('img').first
            image_url = await image_locator.get_attribute('src') if await image_locator.count() else None

            pins.append({
                'pin_url': pin_url,
                'title': title.strip(),
                'image': image_url,
                'source_url': url,
            })
            new_pins_found = True

            if len(pins) >= max_pins:
                break

        if new_pins_found:
            stagnant_scrolls = 0
        else:
            stagnant_scrolls += 1

        await page.evaluate('window.scrollBy(0, document.body.scrollHeight)')
        await page.wait_for_timeout(1200)

    return pins[:max_pins]


async def main() -> None:  # type: ignore[func-returns-value]
    """Define the main entry point for the Apify Actor."""
    async with Actor:
        actor_input = await Actor.get_input() or {}
        start_urls = actor_input.get('start_urls', DEFAULT_START_URLS)
        max_pins = int(actor_input.get('max_pins', 50))

        if not start_urls:
            Actor.log.info('No start URLs specified in Actor input, exiting...')
            await Actor.exit()

        Actor.log.info('Launching Playwright...')

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=Actor.configuration.headless,
                args=['--disable-gpu'],
            )
            context = await browser.new_context()

            for start_url in start_urls:
                url = start_url.get('url')
                if not url:
                    Actor.log.warning('Skipping start URL with missing url field: %s', start_url)
                    continue

                Actor.log.info('Scraping pins from %s ...', url)
                page = await context.new_page()
                try:
                    pins = await scrape_pins_from_url(page, url, max_pins)
                    await Actor.push_data({
                        'url': url,
                        'pins': pins,
                        'pin_count': len(pins),
                    })
                except Exception:
                    Actor.log.exception('Failed to scrape pins from %s.', url)
                finally:
                    await page.close()

            await context.close()
            await browser.close()
