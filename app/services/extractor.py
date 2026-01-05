# app/services/extractor.py
from __future__ import annotations

import logging
import time
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests
from trafilatura import extract

logger = logging.getLogger(__name__)

# Domains known to require special handling
CLOUDFLARE_PROTECTED_DOMAINS = {
    "timesofindia.indiatimes.com",
    "www.theverge.com",
    "techcrunch.com",
    "www.anthropic.com",
}

GOOGLE_NEWS_DOMAINS = {"news.google.com"}

# Browser-like headers to avoid bot detection
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}


def resolve_google_news_redirect(url: str, timeout: int = 10) -> Tuple[Optional[str], str]:
    """
    Resolve Google News redirect URL to the actual article URL.

    Google News URLs like https://news.google.com/rss/articles/... redirect to the actual article.
    Returns: (actual_url, status_message)
    """
    try:
        # Use GET instead of HEAD because some servers don't handle HEAD properly
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True,
            stream=True,  # Don't download full content, just headers
        )

        # Close the connection immediately after getting headers
        response.close()

        # The final URL after redirects
        actual_url = response.url

        # Make sure we actually got redirected to a different domain
        if actual_url != url and "news.google.com" not in actual_url:
            logger.info(f"Resolved Google News redirect: {urlparse(actual_url).netloc}")
            return actual_url, "resolved"
        else:
            return None, "Google News redirect did not resolve to external article"

    except Exception as e:
        return None, f"Failed to resolve redirect: {type(e).__name__}"


def try_cloudscraper_fetch(url: str, timeout: int = 10) -> Tuple[Optional[str], str]:
    """
    Try to fetch using cloudscraper for Cloudflare-protected sites.

    Returns: (html_content, status_message)
    """
    try:
        import cloudscraper

        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )

        response = scraper.get(url, timeout=timeout)

        if response.status_code == 200:
            return response.text, "cloudscraper_success"
        else:
            return None, f"Cloudscraper HTTP {response.status_code}"

    except ImportError:
        logger.warning("cloudscraper not installed, skipping Cloudflare bypass")
        return None, "cloudscraper_not_available"
    except Exception as e:
        return None, f"Cloudscraper error: {type(e).__name__}"


def extract_article_text(
    url: str,
    min_length: int = 100,  # Lowered from 200 for debugging
    max_retries: int = 3,
    timeout: int = 10,
) -> Tuple[Optional[str], str]:
    """
    Extract article text from URL with robust error handling.

    Handles:
    - Google News redirects (resolves to actual article URL)
    - Cloudflare-protected sites (uses cloudscraper if available)
    - Regular sites (standard requests + trafilatura)

    Returns:
        Tuple of (extracted_text, status_message)
        - extracted_text: The article content or None
        - status_message: Description of what happened (for logging/debugging)
    """
    domain = urlparse(url).netloc

    # Step 1: Handle Google News redirects
    if domain in GOOGLE_NEWS_DOMAINS:
        logger.info(f"Resolving Google News redirect: {url[:80]}...")
        resolved_url, status = resolve_google_news_redirect(url, timeout)
        if resolved_url:
            url = resolved_url
            domain = urlparse(url).netloc
            logger.info(f"  → Redirected to: {domain}")
        else:
            logger.warning(f"  → {status}")
            return None, f"Google News redirect failed: {status}"

    # Step 2: Attempt extraction with retries
    html = None
    fetch_method = "requests"

    for attempt in range(max_retries):
        try:
            # Try cloudscraper first for known Cloudflare domains or on final attempt
            should_try_cloudscraper = (
                (domain in CLOUDFLARE_PROTECTED_DOMAINS and attempt == 0) or
                (attempt == max_retries - 1)  # Last resort fallback
            )

            if should_try_cloudscraper:
                logger.info(f"Trying cloudscraper for {domain} (attempt {attempt + 1})")
                html, status = try_cloudscraper_fetch(url, timeout)
                if html:
                    fetch_method = "cloudscraper"
                    break
                elif status == "cloudscraper_not_available":
                    logger.info("Cloudscraper not available, falling back to requests")
                # If cloudscraper failed for other reasons, continue to regular requests

            # Regular fetch with browser-like headers and timeout
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=timeout,
                allow_redirects=True,
            )

            # Check HTTP status
            if response.status_code != 200:
                status_msg = f"HTTP {response.status_code} from {domain}"
                if attempt < max_retries - 1:
                    logger.warning(f"{status_msg}, retrying... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    logger.error(f"{status_msg}, all retries exhausted")
                    return None, status_msg

            html = response.text
            break  # Success, exit retry loop

        except requests.exceptions.Timeout:
            status_msg = f"Timeout ({timeout}s) from {domain}"
            if attempt < max_retries - 1:
                logger.warning(f"{status_msg}, retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)
                continue
            else:
                logger.error(f"{status_msg}, all retries exhausted")
                return None, status_msg

        except requests.exceptions.RequestException as e:
            status_msg = f"Request error from {domain}: {type(e).__name__}"
            if attempt < max_retries - 1:
                logger.warning(f"{status_msg}, retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)
                continue
            else:
                logger.error(f"{status_msg}, all retries exhausted: {e}")
                return None, status_msg

        except Exception as e:
            status_msg = f"Unexpected error from {domain}: {type(e).__name__}: {e}"
            logger.error(status_msg)
            return None, status_msg

    # Step 3: Validate HTML
    if not html or len(html) < 100:
        status_msg = f"Empty/tiny HTML ({len(html) if html else 0} bytes) from {domain}"
        logger.warning(status_msg)
        return None, status_msg

    # Step 4: Extract with Trafilatura
    text = extract(
        html,
        favor_precision=True,
        include_comments=False,
        include_tables=False,
    )

    if not text:
        status_msg = f"Trafilatura extraction failed for {domain} (HTML size: {len(html)}, method: {fetch_method})"
        logger.warning(status_msg)
        return None, status_msg

    text = text.strip()

    # Step 5: Check minimum length
    if len(text) < min_length:
        status_msg = f"Text too short ({len(text)} < {min_length}) from {domain}"
        logger.warning(status_msg)
        return None, status_msg

    # Success!
    logger.info(f"✓ Extracted {len(text)} chars from {domain} (method: {fetch_method})")
    return text, "ok"
