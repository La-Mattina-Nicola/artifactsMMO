import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from api import ApiClient, ArtifactsGateway
from data.world import World
from game import GameManager
from services.banking import BankService

load_dotenv()

ARTIFACTS_TOKEN = os.getenv("ARTIFACTS_TOKEN")
API_URL = os.getenv("ARTIFACTS_URL")
ACCOUNT = os.getenv("ACCOUNT")


async def main():
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.basicConfig(
        level=logging.CRITICAL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("bot.log", encoding="utf-8"),
        ],
    )

    client = ApiClient(token=ARTIFACTS_TOKEN, base_url=API_URL)
    gateway = ArtifactsGateway(client)

    force_refresh = "--refresh" in sys.argv
    world = World()
    await world.load(gateway, force_refresh=force_refresh)

    bank_service = BankService(gateway, world)
    await bank_service.load()

    characters = await gateway.get_account_characters(ACCOUNT)

    manager = GameManager(characters, gateway, world, bank_service)
    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
