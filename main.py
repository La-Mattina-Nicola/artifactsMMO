import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from api import ApiClient, ArtifactsGateway
from data.world import World
from game import GameManager

load_dotenv()

ARTIFACTS_TOKEN = os.getenv("ARTIFACTS_TOKEN")
API_URL = os.getenv("ARTIFACTS_URL")
ACCOUNT = os.getenv("ACCOUNT")


async def main():
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    client = ApiClient(token=ARTIFACTS_TOKEN, base_url=API_URL)
    gateway = ArtifactsGateway(client)

    force_refresh = "--refresh" in sys.argv
    world = World()
    await world.load(gateway, force_refresh=force_refresh)

    characters = await gateway.get_account_characters(ACCOUNT)

    manager = GameManager(characters, gateway, world)
    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
