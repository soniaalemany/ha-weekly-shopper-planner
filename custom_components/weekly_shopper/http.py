"""Vista HTTP para importar ficheros (pueden ser grandes para un mensaje WS)."""
from __future__ import annotations

import json

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN, IMPORT_URL
from .storage import WeeklyShopperError

MAX_IMPORT_BYTES = 20 * 1024 * 1024


class ImportView(HomeAssistantView):
    url = IMPORT_URL
    name = f"api:{DOMAIN}:import"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        hass = request.app["hass"]
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries or not hasattr(entries[0], "runtime_data"):
            return self.json_message("Integration not loaded", 503, "not_loaded")
        data = entries[0].runtime_data
        origin = request.query.get("client_id")

        if not request.content_type.startswith("multipart/"):
            return self.json_message("multipart/form-data expected", 400, "invalid_format")
        filename, raw = "", b""
        reader = await request.multipart()
        while (part := await reader.next()) is not None:
            if part.name == "file":
                filename = part.filename or ""
                raw = await part.read(decode=False)
                break
        if not raw or len(raw) > MAX_IMPORT_BYTES:
            return self.json_message("A file between 1 byte and 20 MB is required", 400, "invalid_format")
        try:
            text = raw.decode("utf-8-sig")
            if filename.lower().endswith((".md", ".markdown")):
                result = data.import_markdown(text, origin)
            else:
                payload = json.loads(text)
                if not isinstance(payload, dict):
                    return self.json_message("JSON object expected", 400, "invalid_format")
                result = data.import_payload(payload, origin)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self.json_message("Invalid file", 400, "invalid_format")
        except WeeklyShopperError as err:
            return self.json_message(str(err), 400, err.code)
        return self.json(result)
