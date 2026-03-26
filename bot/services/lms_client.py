"""
LMS API client.

Handles HTTP requests to the LMS backend with Bearer token authentication.
"""

import httpx


class LMSClient:
    """Client for the LMS backend API."""

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the LMS client.

        Args:
            base_url: Base URL of the LMS backend (e.g., http://localhost:42002)
            api_key: API key for Bearer authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10.0,
            follow_redirects=True,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def get_health(self) -> dict:
        """
        Check backend health by fetching items.

        Returns:
            Dict with 'healthy' bool and 'items_count' or 'error' message.
        """
        try:
            response = await self._client.get("/items/")
            response.raise_for_status()
            items = response.json()
            return {"healthy": True, "items_count": len(items)}
        except httpx.ConnectError as e:
            return {"healthy": False, "error": f"connection refused ({self.base_url})"}
        except httpx.HTTPStatusError as e:
            return {
                "healthy": False,
                "error": f"HTTP {e.response.status_code} {e.response.reason_phrase}",
            }
        except httpx.HTTPError as e:
            return {"healthy": False, "error": str(e)}
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    async def get_labs(self) -> dict:
        """
        Get list of available labs.

        Returns:
            Dict with 'labs' list or 'error' message.
        """
        try:
            response = await self._client.get("/items/")
            response.raise_for_status()
            items = response.json()

            # Extract unique labs from items
            # API returns: {"id": 1, "title": "Lab 01 – ...", "type": "lab"}
            labs = {}
            for item in items:
                if item.get("type") == "lab":
                    lab_id = item.get("id")
                    lab_name = item.get("title", f"Lab {lab_id}")
                    if lab_id and lab_id not in labs:
                        labs[lab_id] = lab_name

            labs_list = [
                {"id": f"lab-{lab_id}", "name": name}
                for lab_id, name in sorted(labs.items())
            ]
            return {"labs": labs_list}
        except httpx.ConnectError as e:
            return {"error": f"connection refused ({self.base_url})"}
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP {e.response.status_code} {e.response.reason_phrase}"
            }
        except httpx.HTTPError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}

    async def get_pass_rates(self, lab: str) -> dict:
        """
        Get per-task pass rates for a lab.

        Args:
            lab: Lab ID (e.g., "lab-04")

        Returns:
            Dict with 'pass_rates' list or 'error' message.
        """
        try:
            response = await self._client.get(
                "/analytics/pass-rates/",
                params={"lab": lab},
            )
            response.raise_for_status()
            data = response.json()
            return {"pass_rates": data}
        except httpx.ConnectError as e:
            return {"error": f"connection refused ({self.base_url})"}
        except httpx.HTTPStatusError as e:
            return {
                "error": f"HTTP {e.response.status_code} {e.response.reason_phrase}"
            }
        except httpx.HTTPError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": str(e)}
