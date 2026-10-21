#!/usr/bin/env python3
"""Run the bridge against explicitly configured development endpoints."""

import argparse
import asyncio
import logging
import os
from unittest.mock import MagicMock

import aiohttp
from dotenv import load_dotenv
from homeassistant.core import HomeAssistant

from custom_components.xiaozhi_mcp.coordinator import XiaozhiMCPCoordinator


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--debug", action="store_true", help="Log transport metadata, never payloads"
    )
    args = parser.parse_args()
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("custom_components.xiaozhi_mcp").setLevel(
        logging.DEBUG if args.debug else logging.INFO
    )
    required = ("XIAOZHI_ENDPOINT", "HA_ACCESS_TOKEN", "HA_MCP_ENDPOINT")
    if any(not os.getenv(key) for key in required):
        parser.error(
            "Set XIAOZHI_ENDPOINT, HA_ACCESS_TOKEN and HA_MCP_ENDPOINT in .env"
        )
    # A real HA core object supplies the event loop; this runner does not simulate HA setup.
    hass = HomeAssistant(os.getcwd())
    entry = MagicMock(data={"enable_logging": args.debug}, options={})
    coordinator = XiaozhiMCPCoordinator(
        hass,
        entry,
        "Local bridge",
        os.environ["XIAOZHI_ENDPOINT"],
        os.environ["HA_ACCESS_TOKEN"],
        30,
        os.environ["HA_MCP_ENDPOINT"],
    )
    async with aiohttp.ClientSession() as session:
        coordinator._mcp_client.session = session
        try:
            await coordinator.async_reconnect()
            await coordinator._connection_monitor_loop()
        finally:
            await coordinator.async_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as err:
        logging.error("Bridge stopped (%s)", type(err).__name__)
        raise SystemExit(1) from None
