import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from api import ApiClient, ArtifactsGateway
from data.world import World
from services.banking import BankService

load_dotenv()

ARTIFACTS_TOKEN = os.getenv("ARTIFACTS_TOKEN")
API_URL = os.getenv("ARTIFACTS_URL")
ACCOUNT = os.getenv("ACCOUNT")


def setup_logging(headless: bool):
    handlers = []

    if headless:
        # En headless : log dans un fichier aussi
        handlers.append(logging.StreamHandler(sys.stdout))
        handlers.append(logging.FileHandler("bot.log", encoding="utf-8"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers if handlers else [logging.NullHandler()],
    )

    # Réduire le bruit des libs HTTP
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


async def main():
    headless = "--headless" in sys.argv or not sys.stdout.isatty()
    setup_logging(headless)

    logger = logging.getLogger(__name__)
    logger.info("Démarrage — mode %s", "headless" if headless else "UI")
    # Infrastructure
    client = ApiClient(token=ARTIFACTS_TOKEN, base_url=API_URL)
    gateway = ArtifactsGateway(client)

    # World
    force_refresh = "--refresh" in sys.argv
    world = World()
    await world.load(gateway, force_refresh=force_refresh)

    # Bank
    bank_service = BankService(gateway, world)
    await bank_service.load()

    # Characters
    characters = await gateway.get_account_characters(ACCOUNT)

    # Manager
    if headless:
        from game.headless_manager import HeadlessManager

        manager = HeadlessManager(characters, gateway, world, bank_service)
    else:
        from game.game_manager import GameManager

        manager = GameManager(characters, gateway, world, bank_service)

    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
