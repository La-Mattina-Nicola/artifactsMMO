import asyncio
import json
import logging
from pathlib import Path
from models import (
    MapTile,
    Resource,
    ResourceDrop,
    Item,
    ItemEffect,
    ItemCraft,
    CraftIngredient,
    Monster,
    MonsterDrop,
)

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class World:
    def __init__(self):
        self.maps: dict[str, MapTile] = {}  # clé: "x,y,layer"
        self.resources: dict[str, Resource] = {}  # clé: resource.code
        self.items: dict[str, Item] = {}  # clé: item.code
        self.monsters: dict[str, Monster] = {}  # clé: monster.code
        self.banks: list[tuple[int, int, list]] = []  # chargé depuis les maps
        self.workshops: dict[str, tuple[int, int]] = {}  # chargé depuis les maps

    async def load(self, gateway, force_refresh: bool = False):
        await asyncio.gather(
            self._load_maps(gateway, force_refresh),
            self._load_resources(gateway, force_refresh),
            self._load_items(gateway, force_refresh),
            self._load_monsters(gateway, force_refresh),
        )
        logger.info(
            "World chargé — %d maps, %d ressources, %d items, %d monstres",
            len(self.maps),
            len(self.resources),
            len(self.items),
            len(self.monsters),
        )

    async def _load_maps(self, gateway, force_refresh: bool = False):
        raw = await self._fetch_or_cache("maps", gateway.get_maps, force_refresh)
        self.maps = {}
        self.banks = []
        self.workshops = {}

        for d in raw:
            content = d.get("interactions", {}).get("content") or {}
            transition = d.get("interactions", {}).get("transition") or {}
            content_type = content.get("type")
            content_code = content.get("code")

            tile = MapTile(
                map_id=d["map_id"],
                name=d["name"],
                x=d["x"],
                y=d["y"],
                layer=d["layer"],
                content_type=content.get("type"),
                content_code=content.get("code"),
                transition_x=transition.get("x"),
                transition_y=transition.get("y"),
                transition_layer=transition.get("layer"),
                transition_conditions=transition.get("conditions", []),
            )
            self.maps[f"{d['x']},{d['y']},{d['layer']}"] = tile

            if content_type == "bank":
                conditions = d.get("access", {}).get("conditions", [])
                self.banks.append((d["x"], d["y"], conditions))
            if content_type == "workshop":
                self.workshops[content_code] = (d["x"], d["y"])

    async def _load_resources(self, gateway, force_refresh: bool = False):
        raw = await self._fetch_or_cache(
            "resources", gateway.get_resources, force_refresh
        )
        self.resources = {}
        for d in raw:
            self.resources[d["code"]] = Resource(
                name=d["name"],
                code=d["code"],
                skill=d["skill"],
                level=d["level"],
                drops=[
                    ResourceDrop(
                        code=drop["code"],
                        rate=drop["rate"],
                        min_quantity=drop["min_quantity"],
                        max_quantity=drop["max_quantity"],
                    )
                    for drop in d.get("drops", [])
                ],
            )

    async def _load_items(self, gateway, force_refresh: bool = False):
        raw = await self._fetch_or_cache("items", gateway.get_items, force_refresh)
        self.items = {}
        for d in raw:
            craft_data = d.get("craft")
            craft = None
            if craft_data:
                craft = ItemCraft(
                    skill=craft_data["skill"],
                    level=craft_data["level"],
                    items=[
                        CraftIngredient(code=i["code"], quantity=i["quantity"])
                        for i in craft_data.get("items", [])
                    ],
                    quantity=craft_data["quantity"],
                )
            self.items[d["code"]] = Item(
                name=d["name"],
                code=d["code"],
                level=d["level"],
                type=d["type"],
                subtype=d.get("subtype", ""),
                conditions=d.get("conditions", []),
                effects=[
                    ItemEffect(code=e["code"], value=e["value"])
                    for e in d.get("effects", [])
                ],
                craft=craft,
                tradeable=d.get("tradeable", False),
            )

    async def _load_monsters(self, gateway, force_refresh: bool = False):
        raw = await self._fetch_or_cache(
            "monsters", gateway.get_monsters, force_refresh
        )
        self.monsters = {}
        for d in raw:
            self.monsters[d["code"]] = Monster(
                name=d["name"],
                code=d["code"],
                level=d["level"],
                type=d.get("type", ""),
                hp=d["hp"],
                attack_fire=d.get("attack_fire", 0),
                attack_earth=d.get("attack_earth", 0),
                attack_water=d.get("attack_water", 0),
                attack_air=d.get("attack_air", 0),
                res_fire=d.get("res_fire", 0),
                res_earth=d.get("res_earth", 0),
                res_water=d.get("res_water", 0),
                res_air=d.get("res_air", 0),
                critical_strike=d.get("critical_strike", 0),
                initiative=d.get("initiative", 0),
                effects=d.get("effects", []),
                drops=[
                    MonsterDrop(
                        code=drop["code"],
                        rate=drop["rate"],
                        min_quantity=drop["min_quantity"],
                        max_quantity=drop["max_quantity"],
                    )
                    for drop in d.get("drops", [])
                ],
            )

    async def _fetch_or_cache(
        self, name: str, fetch_fn, force_refresh: bool = False
    ) -> list[dict]:
        cache_file = CACHE_DIR / f"{name}.json"

        if not force_refresh and cache_file.exists():
            logger.debug("Cache hit : %s", name)
            return json.loads(cache_file.read_text())

        try:
            fresh = await fetch_fn()
            cache_file.write_text(json.dumps(fresh, indent=2, ensure_ascii=False))
            logger.debug("Cache mis à jour : %s (%d entrées)", name, len(fresh))
            return fresh
        except Exception as e:
            logger.warning("Fetch %s échoué : %s — utilisation du cache", name, e)
            if cache_file.exists():
                return json.loads(cache_file.read_text())
            raise RuntimeError(f"Pas de cache disponible pour {name}") from e

    def find_nodes_for_drop(self, drop_code: str) -> list[MapTile]:
        """Trouve toutes les maps qui contiennent une ressource droppant drop_code."""
        resource_codes = {
            resource.code
            for resource in self.resources.values()
            if any(drop.code == drop_code for drop in resource.drops)
        }
        return [
            tile for tile in self.maps.values() if tile.content_code in resource_codes
        ]

    def closest_node(self, drop_code: str, x: int, y: int) -> MapTile | None:
        """Retourne le node le plus proche via distance Manhattan."""
        nodes = self.find_nodes_for_drop(drop_code)
        if not nodes:
            return None
        return min(nodes, key=lambda t: abs(t.x - x) + abs(t.y - y))

    def closest_monster_tile(self, monster_code: str, x: int, y: int) -> MapTile | None:
        monster_positions = [
            tile
            for tile in self.maps.values()
            if tile.content_type == "monster" and tile.content_code == monster_code
        ]
        if not monster_positions:
            return None
        return min(monster_positions, key=lambda t: abs(t.x - x) + abs(t.y - y))
