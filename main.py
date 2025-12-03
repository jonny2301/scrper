"""Main entry point for Apify Actor scraping with Playwright."""

from __future__ import annotations

from urllib.parse import urljoin

from apify import Actor, Request
from playwright.async_api import async_playwright


async def enqueue_start_urls(request_queue, start_urls: list[dict], max_depth: int) -> None:
    """Enqueue initial URLs with depth metadata."""
    for start_url in start_urls:
        url = start_url.get('url')
        if not url:
            Actor.log.warning('Skipping start URL with missing url field: %s', start_url)
            continue
        Actor.log.info('Enqueuing %s ...', url)
        new_request = Request.from_url(url, user_data={'depth': 0, 'max_depth': max_depth})
        await request_queue.add_request(new_request)


async def process_page(context, request_queue, request, max_depth: int) -> None:
    """Process a single page: navigate, extract links, and store data."""
    url = request.url

    if not isinstance(request.user_data.get('depth'), (str, int)):
        raise TypeError('Request.depth is an unexpected type.')

    depth = int(request.user_data['depth'])
    Actor.log.info('Scraping %s (depth=%s) ...', url, depth)

    page = await context.new_page()
    try:
        await page.goto(url)

        if depth < max_depth:
            for link in await page.locator('a').all():
                link_href = await link.get_attribute('href')
                if not link_href:
                    continue
                link_url = urljoin(url, link_href)

                if link_url.startswith(('http://', 'https://')):
                    Actor.log.info('Enqueuing %s ...', link_url)
                    new_request = Request.from_url(
                        link_url,
                        user_data={'depth': depth + 1, 'max_depth': max_depth},
                    )
                    await request_queue.add_request(new_request)

        data = {
            'url': url,
            'title': await page.title(),
        }
        await Actor.push_data(data)

    except Exception:
        Actor.log.exception('Cannot extract data from %s.', url)
    finally:
        await page.close()
        await request_queue.mark_request_as_handled(request)


async def main() -> None:  # type: ignore[func-returns-value]
    """Define the main entry point for the Apify Actor."""
    async with Actor:
        actor_input = await Actor.get_input() or {}
        start_urls = actor_input.get('start_urls', [{'url': 'https://apify.com'}])
        max_depth = int(actor_input.get('max_depth', 1))

        if not start_urls:
            Actor.log.info('No start URLs specified in Actor input, exiting...')
            await Actor.exit()

        request_queue = await Actor.open_request_queue()

        await enqueue_start_urls(request_queue, start_urls, max_depth)

        Actor.log.info('Launching Playwright...')

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=Actor.configuration.headless,
                args=['--disable-gpu'],
            )
            context = await browser.new_context()

            while request := await request_queue.fetch_next_request():
                await process_page(context, request_queue, request, max_depth)

            await context.close()
            await browser.close()
