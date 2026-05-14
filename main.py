import asyncio
import logging
import os
from dotenv import load_dotenv
from api import ApiClient
from api import ArtifactsGateway
from game import GameManager

load_dotenv()

ARTIFACTS_TOKEN = os.getenv("ARTIFACTS_TOKEN")
API_URL = os.getenv("ARTIFACTS_URL")
ACCOUNT = os.getenv("ACCOUNT")


async def main():
    # logging.basicConfig(level=0)
    client = ApiClient(token=ARTIFACTS_TOKEN, base_url=API_URL)
    artifacts_gateway = ArtifactsGateway(client)

    characters = await artifacts_gateway.get_account_characters(ACCOUNT)
    await artifacts_gateway.get_all_characters([c.name for c in characters])
    # --- SYNC INITIAL ---
    for c in characters:
        await artifacts_gateway.get_character(c)  # <-- IMPORTANT

    manager = GameManager(characters, artifacts_gateway)

    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
