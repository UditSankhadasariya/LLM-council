import asyncio
import logging
from dataclasses import dataclass, field

from .base_interactor import BaseInteractor

logger = logging.getLogger(__name__)

QUEUE_MAXSIZE = 50


@dataclass
class BrowserRequest:
    prompt: str
    temporary_chat: bool = True
    future: asyncio.Future = field(default=None, repr=False)

    def __post_init__(self):
        if self.future is None:
            self.future = asyncio.get_running_loop().create_future()


class QueueManager:
    def __init__(self, interactor: BaseInteractor):
        self.interactor = interactor
        self.queue: asyncio.Queue[BrowserRequest] = asyncio.Queue(
            maxsize=QUEUE_MAXSIZE
        )
        self._worker_task: asyncio.Task | None = None

    def start(self):
        """Start the worker task."""
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("Queue worker started.")

    async def stop(self):
        """Stop the worker task."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            logger.info("Queue worker stopped.")

    async def enqueue(self, request: BrowserRequest):
        """Add a request to the queue. Raises if full."""
        self.queue.put_nowait(request)
        logger.debug(f"Enqueued request. Queue size: {self.queue.qsize()}")

    @property
    def size(self) -> int:
        return self.queue.qsize()

    async def _worker(self):
        """Process requests one at a time from the queue."""
        logger.info("Worker ready, waiting for requests...")
        while True:
            request = await self.queue.get()
            try:
                logger.info(f"Processing browser request ({len(request.prompt)} chars)")

                response_text = await self.interactor.process_message(
                    request.prompt, temporary_chat=request.temporary_chat
                )
                if not request.future.done():
                    request.future.set_result(response_text)

            except Exception as e:
                logger.error(f"Error processing request: {e}", exc_info=True)
                if not request.future.done():
                    request.future.set_exception(e)
            finally:
                self.queue.task_done()
