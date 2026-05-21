import logging
from api import ApiClient
from models.character import Character
from functools import wraps

logger = logging.getLogger(__name__)


def sync_character(func):
    @wraps(func)
    async def wrapper(self, character, *args, **kwargs):
        name = character.name if isinstance(character, Character) else character

        response_data = await func(self, name, *args, **kwargs)

        if not isinstance(character, Character):
            return response_data

        data = response_data.get("data", {})

        drops_logger = logging.getLogger("✅")

        details = data.get("details", {}) if isinstance(data, dict) else {}
        items = details.get("items", [])
        xp = details.get("xp", 0)
        if items:
            drops_str = " | ".join(f"{i['quantity']}x {i['code']}" for i in items)
            xp_str = f"{xp:>4} xp"
            drops_logger.info(f"{character.name:<10} — {xp_str:<8} — {drops_str}")

        # --- Format 1 : data.character ---
        if isinstance(data, dict) and "character" in data:
            character.update_from_dto({"data": data["character"]})
            return response_data

        # --- Format 2 : data.characters (liste) ---
        if isinstance(data, dict) and "characters" in data:
            for c in data["characters"]:
                if c.get("name") == character.name:
                    character.update_from_dto({"data": c})
                    break
            return response_data

        # --- Format 3 : data = personnage directement ---
        if isinstance(data, dict) and "name" in data:
            character.update_from_dto({"data": data})
            return response_data

        # --- Format 4 : aucun personnage ---
        return response_data

    return wrapper


class ArtifactsGateway:
    def __init__(self, api_client: ApiClient):
        self.api_client = api_client
        self.drops_logger = logging.getLogger("⚙️")

    async def _get_all_pages(self, endpoint: str) -> list[dict]:
        results = []
        page = 1

        while True:
            response = await self.api_client.get(
                endpoint, params={"page": page, "size": 50}
            )
            data = response.json()
            results.extend(data["data"])

            if page >= data["pages"]:
                break
            page += 1

        self.drops_logger.debug("%s — %d entrées chargées", endpoint, len(results))
        return results

    # --- Méthodes pour récupérer les données de base (maps, ressources, items, monstres, bank) ---
    async def get_maps(self) -> list[dict]:
        return await self._get_all_pages("/maps")

    async def get_resources(self) -> list[dict]:
        return await self._get_all_pages("/resources")

    async def get_items(self) -> list[dict]:
        return await self._get_all_pages("/items")

    async def get_monsters(self) -> list[dict]:
        return await self._get_all_pages("/monsters")

    async def get_bank_items(self) -> list[dict]:
        return await self._get_all_pages("/my/bank/items")

    async def get_bank(self) -> dict:
        response = await self.api_client.get(f"/my/bank")
        return response.json()

    async def get_account_characters(self, account: str) -> list[Character]:
        response = await self.api_client.get(f"/accounts/{account}/characters")
        data = response.json()
        return [Character.from_dto({"data": c}) for c in data["data"]]

    async def get_all_characters(self, names: list[str]) -> list[Character]:
        characters = []
        for name in names:
            character = await self.get_character(name)
            characters.append(character)
        return characters

    async def get_character(self, character_name: str) -> Character:
        response = await self.api_client.get(f"/characters/{character_name}")
        return response.json()

    @sync_character
    async def move(self, character, x: int, y: int):
        response = await self.api_client.post(
            f"/my/{character}/action/move", json={"x": x, "y": y}
        )
        return response.json()

    @sync_character
    async def transition(self, character) -> dict:
        response = await self.api_client.post(f"/my/{character}/action/transition")
        return response.json()

    @sync_character
    async def gather(self, character):
        response = await self.api_client.post(f"/my/{character}/action/gathering")
        return response.json()

    @sync_character
    async def craft(self, character: str, item_id: int, quantity: int) -> dict:
        response = await self.api_client.post(
            f"/my/{character}/action/crafting",
            json={"code": item_id, "quantity": quantity},
        )
        return response.json()

    @sync_character
    async def deposit_items(self, character: str, items: list[dict]) -> dict:
        response = await self.api_client.post(
            f"/my/{character}/action/bank/deposit/item",
            json=items,
        )
        return response.json()

    @sync_character
    async def withdraw_items(self, character: str, items: list[dict]) -> dict:
        response = await self.api_client.post(
            f"/my/{character}/action/bank/withdraw/item",
            json=items,
        )
        return response.json()

    @sync_character
    async def fight(self, character) -> dict:
        response = await self.api_client.post(f"/my/{character}/action/fight")
        return response.json()

    @sync_character
    async def rest(self, character) -> dict:
        response = await self.api_client.post(f"/my/{character}/action/rest")
        return response.json()

    @sync_character
    async def accept_quest(self, character) -> dict:
        response = await self.api_client.post(f"/my/{character}/action/task/new")
        return response.json()

    @sync_character
    async def complete_quest(self, character) -> dict:
        response = await self.api_client.post(f"/my/{character}/action/task/complete")
        return response.json()

    @sync_character
    async def trade_quest(self, character, item_code: str, quantity: int) -> dict:

        response = await self.api_client.post(
            f"/my/{character}/action/task/trade",
            json={"code": item_code, "quantity": quantity},
        )
        return response.json()
