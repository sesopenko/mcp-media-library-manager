"""Queue-based file move system for TV episode ingestion.

This module provides a thread-safe queue for managing file moves asynchronously,
allowing ingest operations to return immediately while moves happen in the background.
"""

import queue
import shutil
import threading
import uuid
from dataclasses import dataclass
from typing import Any

from mcp_media_library_manager.logging import Logger


@dataclass
class QueuedJob:
    """A queued TV episode ingest job.

    Attributes:
        job_id: Unique identifier for this job (UUID4 string).
        show_name: The TV show name.
        first_air_year: The year the show first aired.
        season_number: The season number (1-based).
        episode_number: The episode number (1-based).
        source_path: Fully-resolved source file path.
        destination_path: Computed destination path.
    """

    job_id: str
    show_name: str
    first_air_year: int
    season_number: int
    episode_number: int
    source_path: str
    destination_path: str


class IngestQueue:
    """Thread-safe queue for managing TV episode file moves.

    This queue accepts ingest jobs and stores them for sequential processing.
    Provides thread-safe add and list operations for querying job state,
    and runs a background worker thread to execute file moves sequentially.
    """

    def __init__(
        self,
        logger: Logger,
        move_fn: Any = None,
    ) -> None:
        """Initialize the ingest queue.

        Args:
            logger: Logger instance for structured logging.
            move_fn: Function to move files (defaults to shutil.move).
                     Takes (source_path, dest_path) as arguments.
        """
        self._logger = logger
        self._jobs: list[QueuedJob] = []
        self._lock = threading.Lock()
        self._queue: queue.Queue[QueuedJob] = queue.Queue()
        self._shutdown_event = threading.Event()
        self._is_processing = False
        self._worker_thread: threading.Thread | None = None

        if move_fn is None:
            self._move_fn = shutil.move
        else:
            self._move_fn = move_fn

    def add_job(
        self,
        show_name: str,
        first_air_year: int,
        season_number: int,
        episode_number: int,
        source_path: str,
        destination_path: str,
    ) -> str:
        """Add a new ingest job to the queue.

        Args:
            show_name: The TV show name.
            first_air_year: The year the show first aired.
            season_number: The season number (1-based).
            episode_number: The episode number (1-based).
            source_path: Fully-resolved source file path.
            destination_path: Computed destination path.

        Returns:
            The job ID (UUID4 string) of the newly added job.
        """
        job_id = str(uuid.uuid4())
        job = QueuedJob(
            job_id=job_id,
            show_name=show_name,
            first_air_year=first_air_year,
            season_number=season_number,
            episode_number=episode_number,
            source_path=source_path,
            destination_path=destination_path,
        )

        with self._lock:
            self._jobs.append(job)
        self._queue.put(job)

        return job_id

    def list_jobs(self) -> list[QueuedJob]:
        """Return a snapshot of all currently queued jobs.

        Returns:
            A shallow copy of the jobs list (safe for callers to iterate).
            Jobs are returned in FIFO order.
        """
        with self._lock:
            return list(self._jobs)

    def start(self) -> None:
        """Start the background worker thread."""
        self._worker_thread = threading.Thread(target=self._run_worker, daemon=False)
        self._worker_thread.start()

    def shutdown(self) -> None:
        """Shutdown the queue and wait for the worker thread to finish.

        Sets the shutdown event, logs any in-progress operations, and waits
        for the worker thread to exit cleanly.
        """
        self._shutdown_event.set()
        if self._is_processing:
            self._logger.warning("Ingest job in progress during shutdown, waiting for completion")
        if self._worker_thread is not None:
            self._worker_thread.join()

    def _run_worker(self) -> None:
        """Background worker loop that processes queued ingest jobs sequentially."""
        while True:
            # Check if we should exit: shutdown signal set AND queue empty AND not processing
            if self._shutdown_event.is_set() and self._queue.empty() and not self._is_processing:
                break

            try:
                job = self._queue.get(timeout=1.0)
            except queue.Empty:
                if self._shutdown_event.is_set():
                    break
                continue

            self._is_processing = True
            try:
                # Remove job from jobs list under lock
                with self._lock:
                    self._jobs = [j for j in self._jobs if j.job_id != job.job_id]

                self._logger.info(
                    "Starting ingest job",
                    job_id=job.job_id,
                    show_name=job.show_name,
                    season_number=job.season_number,
                    episode_number=job.episode_number,
                )

                # Execute the move
                self._move_fn(job.source_path, job.destination_path)

                self._logger.info("Completed ingest job", job_id=job.job_id)
            except OSError as e:
                self._logger.error(
                    "Failed ingest job",
                    job_id=job.job_id,
                    error=str(e),
                )
            finally:
                self._is_processing = False
                self._queue.task_done()
