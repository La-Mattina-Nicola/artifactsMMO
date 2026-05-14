import asyncio
import os

from dotenv import load_dotenv
from api import ApiClient
from api import ArtifactsGateway
from game.game_manager import GameManager
from services.movement import MovementService

load_dotenv()
ARTIFACTS_TOKEN = os.getenv("ARTIFACTS_TOKEN")
API_URL = os.getenv("ARTIFACTS_URL")
ACCOUNT = os.getenv("ACCOUNT")


async def main():
    client = ApiClient(token=ARTIFACTS_TOKEN, base_url=API_URL)
    artifacts_gateway = ArtifactsGateway(client)

    characters = await artifacts_gateway.get_account_characters(ACCOUNT)

    movement_service = MovementService(artifacts_gateway)
    manager = GameManager(characters, movement_service)

    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
