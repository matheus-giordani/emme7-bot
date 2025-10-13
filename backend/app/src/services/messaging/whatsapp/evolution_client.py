"""HTTP client for interacting with the Evolution API."""

from __future__ import annotations

import logging
from typing import Any, Dict

import requests


class EvolutionClient:
    """Thin wrapper around the Evolution API send message endpoints."""

    def __init__(self, base_url: str, api_key: str, instance_name: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.instance_name = instance_name
        self.logger = logging.getLogger("evolution.client")

    def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        """Send a plain text message via Evolution."""

        url = f"{self.base_url}/message/sendText/{self.instance_name}"
        payload = {"number": phone, "text": message}
        headers = {"apikey": self.api_key}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except requests.exceptions.HTTPError as http_err:
            self.logger.error(
                "Evolution API retornou erro HTTP ao enviar mensagem: %s", http_err
            )
            status = getattr(http_err.response, "status_code", None) if hasattr(http_err, "response") else None
            return {"error": f"HTTP error: {http_err}", "status": status}
        except requests.exceptions.ConnectionError as conn_err:
            self.logger.error("Erro de conexão com Evolution API: %s", conn_err)
            return {"error": f"Connection error: {conn_err}"}
        except requests.exceptions.Timeout as timeout_err:
            self.logger.error("Timeout ao enviar mensagem via Evolution API: %s", timeout_err)
            return {"error": f"Timeout error: {timeout_err}"}
        except requests.exceptions.RequestException as req_err:
            self.logger.error("Erro inesperado ao enviar mensagem via Evolution API: %s", req_err)
            return {"error": f"Request error: {req_err}"}

