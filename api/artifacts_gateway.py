from datetime import datetime

from api import ApiClient
from models.character import Character

from functools import wraps
from api import ApiClient
from models.character import Character


def sync_character(func):
    @wraps(func)
    async def wrapper(self, character, *args, **kwargs):
        # Nom du personnage (string)
        name = character.name if isinstance(character, Character) else character

        # Appel API
        response_data = await func(self, name, *args, **kwargs)

        if not isinstance(character, Character):
            return response_data

        data = response_data.get("data", {})

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

    @sync_character
    async def _handle_response(self, response) -> dict:
        data = response.json()

        if "error" in data:
            code = data["error"]["code"]
            message = data["error"]["message"]

            raise Exception(f"API error {code}: {message}")
        return data

    @sync_character
    async def get_account_characters(self, account: str) -> list[Character]:
        response = await self.api_client.get(f"/accounts/{account}/characters")
        data = response.json()
        return [Character.from_dto({"data": c}) for c in data["data"]]

    @sync_character
    async def get_all_characters(self, names: list[str]) -> list[Character]:
        characters = []
        for name in names:
            character = await self.get_character(name)
            characters.append(character)
        return characters

    @sync_character
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
    async def gather(self, character):
        response = await self.api_client.post(f"/my/{character}/action/gathering")
        return response.json()
