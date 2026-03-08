"""Unit tests for the ingest queue module."""

import concurrent.futures
import time
from unittest.mock import MagicMock
from uuid import UUID

from mcp_media_library_manager.ingest_queue import IngestQueue, QueuedJob
from mcp_media_library_manager.logging import make_logger


class TestQueuedJob:
    """Tests for QueuedJob dataclass."""

    def test_queued_job_has_all_fields(self) -> None:
        """QueuedJob contains all required fields."""
        job = QueuedJob(
            job_id="test-id",
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E01.mkv",
        )
        assert job.job_id == "test-id"
        assert job.show_name == "Breaking Bad"
        assert job.first_air_year == 2008
        assert job.season_number == 1
        assert job.episode_number == 1
        assert job.source_path == "/tmp/source.mkv"
        assert job.destination_path == "/media/Breaking Bad (2008)/Season 01/S01E01.mkv"


class TestIngestQueue:
    """Tests for IngestQueue."""

    def test_add_job_returns_uuid_string(self) -> None:
        """add_job returns a non-empty UUID string."""
        queue = IngestQueue(logger=make_logger("info"))
        job_id = queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E01.mkv",
        )
        assert isinstance(job_id, str)
        assert len(job_id) > 0
        # Verify it's a valid UUID
        UUID(job_id)

    def test_add_job_returns_unique_uuids(self) -> None:
        """add_job called twice returns two different UUIDs."""
        queue = IngestQueue(logger=make_logger("info"))
        job_id_1 = queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source1.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E01.mkv",
        )
        job_id_2 = queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=2,
            source_path="/tmp/source2.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E02.mkv",
        )
        assert job_id_1 != job_id_2

    def test_list_jobs_returns_all_added_jobs_in_fifo_order(self) -> None:
        """list_jobs returns all added jobs in FIFO order."""
        queue = IngestQueue(logger=make_logger("info"))

        # Add jobs in order
        job_id_1 = queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source1.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E01.mkv",
        )
        job_id_2 = queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=2,
            source_path="/tmp/source2.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E02.mkv",
        )

        jobs = queue.list_jobs()
        assert len(jobs) == 2
        assert jobs[0].job_id == job_id_1
        assert jobs[1].job_id == job_id_2
        assert jobs[0].episode_number == 1
        assert jobs[1].episode_number == 2

    def test_list_jobs_on_empty_queue_returns_empty_list(self) -> None:
        """list_jobs on empty queue returns empty list."""
        queue = IngestQueue(logger=make_logger("info"))
        jobs = queue.list_jobs()
        assert jobs == []

    def test_concurrent_add_job_produces_consistent_list_jobs(self) -> None:
        """Concurrent add_job calls from multiple threads produce consistent list_jobs output."""
        queue = IngestQueue(logger=make_logger("info"))
        num_threads = 5
        jobs_per_thread = 4

        def add_jobs(thread_id: int) -> list[str]:
            job_ids = []
            for i in range(jobs_per_thread):
                job_id = queue.add_job(
                    show_name=f"Show-{thread_id}",
                    first_air_year=2020 + i,
                    season_number=1,
                    episode_number=i + 1,
                    source_path=f"/tmp/source-{thread_id}-{i}.mkv",
                    destination_path=f"/media/Show-{thread_id}/Season 01/S01E{i + 1:02d}.mkv",
                )
                job_ids.append(job_id)
            return job_ids

        # Execute add_job from multiple threads concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(add_jobs, i) for i in range(num_threads)]
            all_job_ids = []
            for future in concurrent.futures.as_completed(futures):
                all_job_ids.extend(future.result())

        # Verify list_jobs returns all jobs
        jobs = queue.list_jobs()
        assert len(jobs) == num_threads * jobs_per_thread
        listed_job_ids = [job.job_id for job in jobs]
        assert set(listed_job_ids) == set(all_job_ids)

    def test_list_jobs_returns_shallow_copy(self) -> None:
        """list_jobs returns a shallow copy that doesn't affect internal state."""
        queue = IngestQueue(logger=make_logger("info"))
        queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E01.mkv",
        )

        # Get a copy and try to modify it
        jobs_copy = queue.list_jobs()
        jobs_copy.clear()

        # Verify internal state is unchanged
        assert len(queue.list_jobs()) == 1


class TestIngestQueueWorker:
    """Tests for IngestQueue worker thread behavior."""

    def test_worker_calls_move_fn_with_correct_paths(self) -> None:
        """Worker thread calls move_fn with correct source and destination paths."""
        mock_move_fn = MagicMock()
        logger = make_logger("info")
        queue = IngestQueue(logger=logger, move_fn=mock_move_fn)
        queue.start()

        queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E01.mkv",
        )

        queue.shutdown()
        mock_move_fn.assert_called_once_with("/tmp/source.mkv", "/media/Breaking Bad (2008)/Season 01/S01E01.mkv")

    def test_worker_processes_multiple_jobs_sequentially(self) -> None:
        """Worker processes multiple jobs sequentially (one at a time)."""
        move_calls = []

        def tracking_move_fn(src: str, dst: str) -> None:
            move_calls.append((src, dst))

        logger = make_logger("info")
        queue = IngestQueue(logger=logger, move_fn=tracking_move_fn)
        queue.start()

        # Add multiple jobs
        queue.add_job(
            show_name="Show1",
            first_air_year=2020,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source1.mkv",
            destination_path="/media/Show1/Season 01/S01E01.mkv",
        )
        queue.add_job(
            show_name="Show2",
            first_air_year=2021,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source2.mkv",
            destination_path="/media/Show2/Season 01/S01E01.mkv",
        )

        queue.shutdown()
        assert len(move_calls) == 2
        assert move_calls[0] == ("/tmp/source1.mkv", "/media/Show1/Season 01/S01E01.mkv")
        assert move_calls[1] == ("/tmp/source2.mkv", "/media/Show2/Season 01/S01E01.mkv")

    def test_worker_logs_job_start_and_completion(self) -> None:
        """Worker logs info on job start and completion."""
        mock_move_fn = MagicMock()
        mock_logger = MagicMock()
        queue = IngestQueue(logger=mock_logger, move_fn=mock_move_fn)
        queue.start()

        queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E01.mkv",
        )

        queue.shutdown()

        # Check that start and completion logs were called
        assert mock_logger.info.call_count >= 2
        info_calls = mock_logger.info.call_args_list
        # First call should be "Starting ingest job"
        assert info_calls[0][0][0] == "Starting ingest job"
        # Last call should be "Completed ingest job"
        assert info_calls[-1][0][0] == "Completed ingest job"

    def test_worker_logs_error_when_move_fn_raises(self) -> None:
        """Worker logs error when move_fn raises OSError."""

        def failing_move_fn(src: str, dst: str) -> None:
            raise OSError("Disk full")

        mock_logger = MagicMock()
        queue = IngestQueue(logger=mock_logger, move_fn=failing_move_fn)
        queue.start()

        queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E01.mkv",
        )

        queue.shutdown()

        # Check that error was logged
        error_calls = list(mock_logger.error.call_args_list)
        assert len(error_calls) >= 1
        assert error_calls[0][0][0] == "Failed ingest job"

    def test_shutdown_with_empty_queue_exits_quickly(self) -> None:
        """shutdown() with empty queue exits quickly."""
        logger = make_logger("info")
        queue = IngestQueue(logger=logger)
        queue.start()

        start = time.time()
        queue.shutdown()
        elapsed = time.time() - start

        # Should exit quickly (within 2 seconds)
        assert elapsed < 2.0

    def test_shutdown_waits_for_in_progress_job(self) -> None:
        """shutdown() waits for an in-progress job before returning."""
        job_started = False
        job_can_finish = False

        def slow_move_fn(src: str, dst: str) -> None:
            nonlocal job_started, job_can_finish
            job_started = True
            # Wait for signal to finish
            while not job_can_finish:
                time.sleep(0.01)

        logger = make_logger("info")
        queue = IngestQueue(logger=logger, move_fn=slow_move_fn)
        queue.start()

        queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E01.mkv",
        )

        # Give the worker thread time to start processing
        time.sleep(0.1)
        assert job_started

        # Now signal shutdown and allow the job to finish
        job_can_finish = True
        queue.shutdown()

        # If we get here, shutdown waited for the job to complete
        assert job_started and job_can_finish

    def test_shutdown_logs_warning_when_job_in_progress(self) -> None:
        """shutdown() logs warning when an ingest job is in progress."""
        job_can_finish = False

        def slow_move_fn(src: str, dst: str) -> None:
            nonlocal job_can_finish
            while not job_can_finish:
                time.sleep(0.01)

        mock_logger = MagicMock()
        queue = IngestQueue(logger=mock_logger, move_fn=slow_move_fn)
        queue.start()

        queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E01.mkv",
        )

        # Give the worker thread time to start processing
        time.sleep(0.1)

        # Allow job to finish before checking warning
        job_can_finish = True
        queue.shutdown()

        # Check that warning was logged
        warning_calls = list(mock_logger.warning.call_args_list)
        if len(warning_calls) > 0:
            assert warning_calls[0][0][0] == "Ingest job in progress during shutdown, waiting for completion"

    def test_worker_removes_job_from_list_after_processing(self) -> None:
        """Worker removes job from list after it starts processing."""
        job_can_finish = False

        def slow_move_fn(src: str, dst: str) -> None:
            nonlocal job_can_finish
            while not job_can_finish:
                time.sleep(0.01)

        logger = make_logger("info")
        queue = IngestQueue(logger=logger, move_fn=slow_move_fn)
        queue.start()

        queue.add_job(
            show_name="Breaking Bad",
            first_air_year=2008,
            season_number=1,
            episode_number=1,
            source_path="/tmp/source.mkv",
            destination_path="/media/Breaking Bad (2008)/Season 01/S01E01.mkv",
        )

        # Give worker time to start processing
        time.sleep(0.1)

        # Job should be removed from the list once processing starts
        jobs = queue.list_jobs()
        assert len(jobs) == 0

        # Allow job to finish
        job_can_finish = True
        queue.shutdown()
