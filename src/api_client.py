import time
import requests  # pyright: ignore[reportMissingModuleSource]


from src.config import API_BASE_URL, API_TOKEN


class APIClient:

    def __init__(self):
        self.base_url = API_BASE_URL.rstrip("/")  # Remove trailing slash if present
        self.session = requests.Session()

        self.session.headers.update({
            "Authorization": f"Bearer {API_TOKEN}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
    def get(self, endpoint, params=None):
        """Make a GET request to the API."""

        url = f"{self.base_url}/{endpoint.lstrip('/')}"  # Ensure no double slashes

        for attempt in range(5):
            try:
                response = self.session.get(url, params=params, timeout=30)

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        sleep_time = int(retry_after) if retry_after is not None else 5
                    except (ValueError, TypeError):
                        sleep_time = 5
                    if attempt == 4:
                        response.raise_for_status()
                    time.sleep(sleep_time)
                    continue

                response.raise_for_status()
                return response.json()
            except (requests.Timeout, requests.ConnectionError):
                if attempt == 4:
                    raise
                time.sleep(min(10, max(2, 2**attempt)))

        raise requests.ConnectionError("Request failed after retries")

    def close(self):
        """Close the session."""
        self.session.close()