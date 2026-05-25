"""Async service fixture for event-loop and queue patterns."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class AsyncService:
    queue: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    processed: list[str] = field(default_factory=list)
    running: bool = False

    async def observe_queue(self) -> int:
        return self.queue.qsize()

    async def dispatch(self) -> None:
        item = await self.queue.get()
        self.processed.append(item.upper())
        self.queue.task_done()

    async def run_once(self) -> bool:
        self.running = True
        if await self.observe_queue() == 0:
            self.running = False
            return False
        await self.dispatch()
        self.running = False
        return True


async def demo() -> list[str]:
    service = AsyncService()
    await service.queue.put("alpha")
    await service.run_once()
    return service.processed
