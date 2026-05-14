from dotenv.main import logger
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
        response = await self.client.get(endpoint, params=params)

        if response.status_code != 200:
            data = response.json()
            code = data["error"]["code"]
            message = data["error"]["message"]
            logger.debug("API GET %s — %s", endpoint)
            raise ApiError(code, message)

        return response

    async def post(self, endpoint: str, json: dict = None) -> httpx.Response:
        response = await self.client.post(endpoint, json=json)

        if response.status_code != 200:
            data = response.json()
            code = data["error"]["code"]
            message = data["error"]["message"]
            logger.debug("API POST %s — %s", endpoint)
            raise ApiError(code, message)

        return response
