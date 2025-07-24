import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from tembo_pgmq_python.async_queue import PGMQueue
from tembo_pgmq_python.messages import Message

logger = logging.getLogger(__name__)


class SupabaseQueue:
    """
    Queue implementation using PGMQueue as the backend storage.
    Uses PostgreSQL tables to implement a reliable job queue system.
    """

    def __init__(
        self,
        host: str,
        port: str,
        user: str,
        password: str,
        db_name: str,
        table_name: str = "processing_job",
    ):
        """
        Initialize PGMQueue client

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            user: PostgreSQL username
            password: PostgreSQL password
            db_name: PostgreSQL database name
            table_name: Name of the queue to use for job storage
        """
        self.queue = PGMQueue(
            host=host,
            port=port,
            username=user,
            password=password,
            database=db_name,
        )
        self.table_name = table_name
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure the queue is initialized"""
        if not self._initialized:
            try:
                await self.queue.init()
            except Exception as e:
                logger.error(f"Failed to initialize queue: {str(e)}")
                raise e

            self._initialized = True

    async def enqueue(
        self,
        queue_name: str,
        payload: Dict[str, Any],
        priority: int = 1,
        job_type: str = "context_creation",
        user_id: str = None,
        delay_seconds: int = 0,
    ) -> str:
        """
        Add a job to the queue

        Args:
            queue_name: Name of the queue (used for routing)
            payload: Job payload data
            priority: Job priority (higher = more important)
            job_type: Type of job for categorization
            user_id: User who initiated the job
            delay_seconds: Delay before job becomes available
            **kwargs: Additional job metadata

        Returns:
            str: Job ID
        """
        try:
            await self._ensure_initialized()

            job_data = payload
            base_time = datetime.now(timezone.utc)

            scheduled_time = (
                base_time + timedelta(seconds=delay_seconds)
                if delay_seconds > 0
                else base_time
            )

            # Send job to queue with delay if specified
            if delay_seconds > 0:
                job_data["scheduled_at"] = scheduled_time
                result: int = await self.queue.send_delay(
                    queue_name, job_data, delay_seconds
                )
            else:
                result: int = await self.queue.send(queue_name, job_data)

            job_id = str(result)
            logger.info(
                f"Job {job_id} enqueued successfully",
                extra={
                    "job_id": job_id,
                    "job_type": job_type,
                    "queue_name": queue_name,
                    "priority": priority,
                    "user_id": user_id,
                },
            )
            return job_id

        except Exception as e:
            logger.error(
                f"Failed to enqueue job: {str(e)}",
                extra={"queue_name": queue_name, "job_type": job_type, "error": str(e)},
            )
            raise

    async def complete_job(
        self, job_data: Dict[str, Any], result: Dict[str, Any] = None
    ) -> bool:
        """
        Mark a job as completed

        Args:
            job_data: Job data returned from dequeue (contains pgmq_msg_id and queue_name)
            result: Optional result data to store

        Returns:
            bool: True if job was successfully marked as completed
        """
        try:
            await self._ensure_initialized()
            msg_id = job_data.get("pgmq_msg_id")
            queue_name = job_data.get("queue_name", self.table_name)

            if not msg_id:
                logger.error("No pgmq_msg_id found in job data")
                return False

            # Delete the message from the queue (marks as completed)
            success = await self.queue.delete(queue_name, msg_id)

            if success:
                logger.info(f"Job {job_data.get('id')} marked as completed")
                return True
            else:
                logger.error(f"Failed to mark job {job_data.get('id')} as completed")
                return False

        except Exception as e:
            logger.error(f"Failed to complete job {job_data.get('id')}: {str(e)}")
            return False

    async def fail_job(
        self,
        job_data: Dict[str, Any],
        error: str,
        error_trace: str = None,
        retry: bool = True,
    ) -> bool:
        """
        Mark a job as failed

        Args:
            job_data: Job data returned from dequeue
            error: Error message
            error_trace: Full error traceback
            retry: Whether to retry the job if attempts remain

        Returns:
            bool: True if job was successfully handled
        """
        try:
            await self._ensure_initialized()

            msg_id = job_data.get("pgmq_msg_id")
            queue_name = job_data.get("queue_name", self.table_name)
            attempts = job_data.get("attempts", 1)
            max_attempts = job_data.get("max_attempts", self.max_retries)

            if not msg_id:
                logger.error("No pgmq_msg_id found in job data")
                return False

            # Determine if job should be retried
            if retry and attempts < max_attempts:
                # Calculate retry delay with exponential backoff
                retry_delay = min(300, 2 ** (attempts - 1) * 10)  # Max 5 minutes

                # Update job data for retry
                updated_job_data = (
                    job_data["payload"]
                    if isinstance(job_data.get("payload"), dict)
                    else {}
                )
                if isinstance(updated_job_data, str):
                    try:
                        updated_job_data = json.loads(updated_job_data)
                    except json.JSONDecodeError:
                        updated_job_data = {}

                # Add retry information
                retry_job_data = {
                    **job_data,
                    "attempts": attempts,
                    "error_message": error,
                    "last_error_trace": error_trace,
                    "retry_count": attempts,
                }

                # Remove PGMQueue specific fields before re-queuing
                retry_job_data.pop("pgmq_msg_id", None)
                retry_job_data.pop("id", None)

                # Delete current message and re-queue with delay
                await self.queue.delete(queue_name, msg_id)
                await self.queue.send_delay(queue_name, retry_job_data, retry_delay)

                logger.info(
                    f"Job {job_data.get('id')} scheduled for retry {attempts}/{max_attempts} in {retry_delay}s"
                )
                return True
            else:
                # Archive the job as permanently failed
                success = await self.queue.archive(queue_name, msg_id)

                if success:
                    logger.error(
                        f"Job {job_data.get('id')} permanently failed after {attempts} attempts"
                    )
                    return True
                else:
                    logger.error(
                        f"Failed to archive permanently failed job {job_data.get('id')}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Failed to fail job {job_data.get('id')}: {str(e)}")
            return False

    async def get_queue_stats(self, queue_name: str = None) -> Dict[str, int]:
        """
        Get queue statistics

        Args:
            queue_name: Queue name to get stats for (uses table_name if None)

        Returns:
            Dict with queue statistics
        """
        try:
            await self._ensure_initialized()

            effective_queue_name = queue_name or self.table_name

            # Get queue metrics from PGMQueue
            metrics = await self.queue.metrics(effective_queue_name)

            stats = {
                "queued": metrics.queue_length,
                "total": metrics.total_messages,
                "newest_msg_age_sec": metrics.newest_msg_age_sec,
                "oldest_msg_age_sec": metrics.oldest_msg_age_sec,
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get queue stats: {str(e)}")
            return {}

    async def close(self):
        """Close the queue connection"""
        if self._initialized and self.queue:
            await self.queue.close()
            self._initialized = False
