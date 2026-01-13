import time
import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch_html(url: str, timeout: int = 20) -> dict:
    """
    Fetch a URL and return HTML + metadata.
    Used for Bayut and competitor pages.
    """
    start = time.time()
    try:
        response = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )

        elapsed_ms = int((time.time() - start) * 1000)
        content_type = response.headers.get("Content-Type", "")

        if "text/html" not in content_type:
            return {
                "ok": False,
                "url": url,
                "final_url": response.url,
                "status": response.status_code,
                "elapsed_ms": elapsed_ms,
                "html": "",
                "error": f"Not HTML: {content_type}",
            }

        return {
            "ok": response.status_code < 400,
            "url": url,
            "final_url": response.url,
            "status": response.status_code,
            "elapsed_ms": elapsed_ms,
            "html": response.text,
            "error": "",
        }

    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "ok": False,
            "url": url,
            "final_url": url,
            "status": None,
            "elapsed_ms": elapsed_ms,
            "html": "",
            "error": str(e),
        }
