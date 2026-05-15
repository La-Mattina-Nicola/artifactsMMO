from __future__ import annotations
import asyncio
import logging
import signal
from typing import TYPE_CHECKING

from game.base_manager import BaseManager

if TYPE_CHECKING:
    from data.world import World
    from services.banking import BankService

logger = logging.getLogger(__name__)


class HeadlessManager(BaseManager):
    def __init__(self, characters, gateway, world: World, bank_service: BankService):
        super().__init__(characters, gateway, world, bank_service)
        self._stop_event = asyncio.Event()

    def _setup_signals(self):
        """Gère Ctrl+C et SIGTERM proprement."""
        loop = asyncio.get_event_loop()

        def _handle_signal():
            logger.info("Signal reçu — arrêt en cours...")
            self._stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _handle_signal)
            except NotImplementedError:
                # Windows ne supporte pas add_signal_handler
                pass

    async def start(self):
        self._setup_signals()
        logger.info("Démarrage en mode headless")

        await asyncio.sleep(0.5)
        await self.load_defaults()

        # Lancer les boucles — s'arrête quand _stop_event est set
        await asyncio.gather(
            self._controllers_loop(),
            self._watch_stop(),
        )
        logger.info("Bot arrêté proprement")

    async def _watch_stop(self):
        await self._stop_event.wait()
        # Annuler toutes les tâches en cours
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
