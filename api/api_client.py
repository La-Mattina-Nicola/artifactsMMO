import httpx

from api.exception import ApiError


class ApiClient:
    def __init__(self, token: str, base_url: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(headers=self.headers, base_url=base_url)

    async def get(self, endpoint: str, params: dict = None):
        return await self.client.get(endpoint, params=params)

    async def post(self, endpoint: str, json: dict = None) -> httpx.Response:
        response = await self.client.post(endpoint, json=json)

        if response.status_code == 499:
            data = response.json()
            code = data["error"]["code"]
            message = data["error"]["message"]
            raise ApiError(code, message)

        response.raise_for_status()
        return response
