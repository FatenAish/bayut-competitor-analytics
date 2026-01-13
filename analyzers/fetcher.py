import requests


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def fetch_html(url: str, timeout: int = 20) -> dict:
    """
    Returns:
      {
        ok: bool,
        html: str,
        status: int | None,
        error: str,
        final_url: str
      }
    """
    url = (url or "").strip()
    if not url:
        return {"ok": False, "html": "", "status": None, "error": "Empty URL", "final_url": ""}

    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
        final_url = resp.url or url
        status = resp.status_code

        if status >= 400:
            return {
                "ok": False,
                "html": resp.text or "",
                "status": status,
                "error": f"HTTP {status}",
                "final_url": final_url,
            }

        return {
            "ok": True,
            "html": resp.text or "",
            "status": status,
            "error": "",
            "final_url": final_url,
        }

    except requests.exceptions.Timeout:
        return {"ok": False, "html": "", "status": None, "error": "Timeout", "final_url": url}
    except Exception as e:
        return {"ok": False, "html": "", "status": None, "error": str(e), "final_url": url}
