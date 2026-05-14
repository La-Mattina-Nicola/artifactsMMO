from api import ApiClient
from models.character import Character


class ArtifactsGateway:
    def __init__(self, api_client: ApiClient):
        self.api_client = api_client

    async def _handle_response(self, response) -> dict:
        data = response.json()

        if "error" in data:
            code = data["error"]["code"]
            message = data["error"]["message"]

            raise Exception(f"API error {code}: {message}")

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
        data = response.json()
        return Character.from_dto(data)

    async def move(self, name, x: int, y: int):
        response = await self.api_client.post(
            f"/my/{name}/action/move", json={"x": x, "y": y}
        )
        data = response.json()
        return data

    async def gather(self, name):
        response = await self.api_client.post(f"/my/{name}/action/gathering")
        data = response.json()
        return data
