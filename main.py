import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from api import ApiClient, ArtifactsGateway
from data.world import World
from services.banking import BankService
from logging.handlers import RotatingFileHandler

load_dotenv()

ARTIFACTS_TOKEN = os.getenv("ARTIFACTS_TOKEN")
API_URL = os.getenv("ARTIFACTS_URL")
ACCOUNT = os.getenv("ACCOUNT")


def setup_logging(headless: bool):
    handlers = []

    if headless:
        handlers.append(logging.StreamHandler(sys.stdout))
        handlers.append(
            RotatingFileHandler(
                "bot.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
        )

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers if handlers else [logging.NullHandler()],
    )

    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


async def main():
    headless = "--headless" in sys.argv or not sys.stdout.isatty()
    setup_logging(headless)

    logger = logging.getLogger(__name__)
    logger.info("Démarrage — mode %s", "headless" if headless else "UI")

    client = ApiClient(token=ARTIFACTS_TOKEN, base_url=API_URL)
    gateway = ArtifactsGateway(client)

    force_refresh = "--refresh" in sys.argv
    world = World()
    await world.load(gateway, force_refresh=force_refresh)

    bank_service = BankService(gateway, world)
    await bank_service.load()

    characters = await gateway.get_account_characters(ACCOUNT)

    if headless:
        from game.headless_manager import HeadlessManager

        manager = HeadlessManager(characters, gateway, world, bank_service)
    else:
        from game.game_manager import GameManager

        manager = GameManager(characters, gateway, world, bank_service)

    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
