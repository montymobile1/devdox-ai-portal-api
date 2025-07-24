import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.supabase_queue import SupabaseQueue


class MockPGMQueue:
    """Mock PGMQueue for testing"""

    def __init__(self):
        self.initialized = False
        self.sent_messages = []
        self.deleted_messages = []
        self.archived_messages = []

    async def init(self):
        self.initialized = True

    async def send(self, queue_name: str, message: dict) -> int:
        msg_id = len(self.sent_messages) + 1
        self.sent_messages.append(
            {"id": msg_id, "queue_name": queue_name, "message": message, "delay": 0}
        )
        return msg_id

    async def send_delay(
        self, queue_name: str, message: dict, delay_seconds: int
    ) -> int:
        msg_id = len(self.sent_messages) + 1
        self.sent_messages.append(
            {
                "id": msg_id,
                "queue_name": queue_name,
                "message": message,
                "delay": delay_seconds,
            }
        )
        return msg_id

    async def delete(self, queue_name: str, msg_id: int) -> bool:
        self.deleted_messages.append({"queue_name": queue_name, "msg_id": msg_id})
        return True

    async def archive(self, queue_name: str, msg_id: int) -> bool:
        self.archived_messages.append({"queue_name": queue_name, "msg_id": msg_id})
        return True

    async def metrics(self, queue_name: str):
        return MagicMock(
            queue_length=5,
            total_messages=100,
            newest_msg_age_sec=30,
            oldest_msg_age_sec=3600,
        )

    async def close(self):
        self.initialized = False


class TestSupabaseQueueInitialization:
    """Test SupabaseQueue initialization"""

    def test_init_with_valid_parameters(self):
        """Test successful initialization with valid parameters"""
        queue = SupabaseQueue(
            host="localhost",
            port="5432",
            user="test_user",
            password="test_pass",
            db_name="test_db",
        )

        assert queue.table_name == "processing_job"
        assert queue.max_retries == 3
        assert queue.retry_delay == 5
        assert queue._initialized is False

    def test_init_with_custom_table_name(self):
        """Test initialization with custom table name"""
        queue = SupabaseQueue(
            host="localhost",
            port="5432",
            user="test_user",
            password="test_pass",
            db_name="test_db",
            table_name="custom_queue",
        )

        assert queue.table_name == "custom_queue"

    @pytest.mark.asyncio
    @patch("app.services.supabase_queue.PGMQueue")
    async def test_ensure_initialized_success(self, mock_pgmqueue_class):
        """Test successful queue initialization"""
        mock_queue = MockPGMQueue()
        mock_pgmqueue_class.return_value = mock_queue

        queue = SupabaseQueue(
            host="localhost",
            port="5432",
            user="test_user",
            password="test_pass",
            db_name="test_db",
        )

        await queue._ensure_initialized()

        assert queue._initialized is True
        assert mock_queue.initialized is True

    @pytest.mark.asyncio
    @patch("app.services.supabase_queue.PGMQueue")
    async def test_ensure_initialized_failure(self, mock_pgmqueue_class):
        """Test queue initialization failure"""
        mock_queue = AsyncMock()
        mock_queue.init.side_effect = Exception("Connection failed")
        mock_pgmqueue_class.return_value = mock_queue

        queue = SupabaseQueue(
            host="localhost",
            port="5432",
            user="test_user",
            password="test_pass",
            db_name="test_db",
        )

        with pytest.raises(Exception, match="Connection failed"):
            await queue._ensure_initialized()

        assert queue._initialized is False


class TestSupabaseQueueEnqueue:
    """Test SupabaseQueue enqueue functionality"""

    @pytest.fixture
    def mock_queue(self):
        """Create a mock queue for testing"""
        with patch("app.services.supabase_queue.PGMQueue") as mock_pgmqueue_class:
            mock_queue_instance = MockPGMQueue()
            mock_pgmqueue_class.return_value = mock_queue_instance

            queue = SupabaseQueue(
                host="localhost",
                port="5432",
                user="test_user",
                password="test_pass",
                db_name="test_db",
            )
            queue.queue = mock_queue_instance
            yield queue, mock_queue_instance

    @pytest.mark.asyncio
    async def test_enqueue_success_basic(self, mock_queue):
        """Test successful basic enqueue operation"""
        queue, mock_queue_instance = mock_queue

        payload = {
            "job_type": "analyze",
            "payload": {"repo_id": "123", "user_id": "user-456"},
        }

        job_id = await queue.enqueue(
            queue_name="processing",
            payload=payload,
            priority=1,
            job_type="analyze",
            user_id="user-456",
        )

        assert job_id == "1"
        assert len(mock_queue_instance.sent_messages) == 1
        sent_msg = mock_queue_instance.sent_messages[0]
        assert sent_msg["queue_name"] == "processing"
        assert sent_msg["message"] == payload
        assert sent_msg["delay"] == 0

    @pytest.mark.asyncio
    async def test_enqueue_with_delay(self, mock_queue):
        """Test enqueue with delay"""
        queue, mock_queue_instance = mock_queue

        payload = {"job_type": "analyze", "data": "test"}
        delay_seconds = 60

        job_id = await queue.enqueue(
            queue_name="processing", payload=payload, delay_seconds=delay_seconds
        )

        assert job_id == "1"
        assert len(mock_queue_instance.sent_messages) == 1
        sent_msg = mock_queue_instance.sent_messages[0]
        assert sent_msg["delay"] == delay_seconds
        assert "scheduled_at" in sent_msg["message"]

    @pytest.mark.asyncio
    async def test_enqueue_with_all_parameters(self, mock_queue):
        """Test enqueue with all parameters"""
        queue, mock_queue_instance = mock_queue

        payload = {
            "job_type": "analyze",
            "payload": {"repo_id": "repo-123", "user_id": "user-456", "branch": "main"},
        }

        job_id = await queue.enqueue(
            queue_name="processing",
            payload=payload,
            priority=5,
            job_type="repository_analysis",
            user_id="user-456",
            delay_seconds=30,
        )

        assert job_id == "1"
        sent_msg = mock_queue_instance.sent_messages[0]
        assert sent_msg["queue_name"] == "processing"
        assert sent_msg["delay"] == 30
        assert "scheduled_at" in sent_msg["message"]

    @pytest.mark.asyncio
    async def test_enqueue_initialization_error(self):
        """Test enqueue when initialization fails"""
        with patch("app.services.supabase_queue.PGMQueue") as mock_pgmqueue_class:
            mock_queue_instance = AsyncMock()
            mock_queue_instance.init.side_effect = Exception("DB connection failed")
            mock_pgmqueue_class.return_value = mock_queue_instance

            queue = SupabaseQueue(
                host="localhost",
                port="5432",
                user="test_user",
                password="test_pass",
                db_name="test_db",
            )

            with pytest.raises(Exception):
                await queue.enqueue("processing", {"test": "data"})

    @pytest.mark.asyncio
    async def test_enqueue_send_error(self, mock_queue):
        """Test enqueue when send operation fails"""
        queue, mock_queue_instance = mock_queue

        # Mock send to raise an exception
        async def mock_send_error(*args, **kwargs):
            raise Exception("Queue send failed")

        mock_queue_instance.send = mock_send_error

        with pytest.raises(Exception, match="Queue send failed"):
            await queue.enqueue("processing", {"test": "data"})


class TestSupabaseQueueCompleteJob:
    """Test SupabaseQueue complete_job functionality"""

    @pytest.fixture
    def mock_queue(self):
        """Create a mock queue for testing"""
        with patch("app.services.supabase_queue.PGMQueue") as mock_pgmqueue_class:
            mock_queue_instance = MockPGMQueue()
            mock_pgmqueue_class.return_value = mock_queue_instance

            queue = SupabaseQueue(
                host="localhost",
                port="5432",
                user="test_user",
                password="test_pass",
                db_name="test_db",
            )
            queue.queue = mock_queue_instance
            queue._initialized = True
            yield queue, mock_queue_instance

    @pytest.mark.asyncio
    async def test_complete_job_success(self, mock_queue):
        """Test successful job completion"""
        queue, mock_queue_instance = mock_queue

        job_data = {
            "id": "job-123",
            "pgmq_msg_id": 42,
            "queue_name": "processing",
            "payload": {"repo_id": "repo-456"},
        }

        result = await queue.complete_job(job_data)

        assert result is True
        assert len(mock_queue_instance.deleted_messages) == 1
        deleted_msg = mock_queue_instance.deleted_messages[0]
        assert deleted_msg["queue_name"] == "processing"
        assert deleted_msg["msg_id"] == 42

    @pytest.mark.asyncio
    async def test_complete_job_with_result(self, mock_queue):
        """Test job completion with result data"""
        queue, mock_queue_instance = mock_queue

        job_data = {"id": "job-123", "pgmq_msg_id": 42, "queue_name": "processing"}

        result_data = {"success": True, "chunks_created": 150, "processing_time": 45.2}

        result = await queue.complete_job(job_data, result_data)

        assert result is True
        assert len(mock_queue_instance.deleted_messages) == 1

    @pytest.mark.asyncio
    async def test_complete_job_missing_msg_id(self, mock_queue):
        """Test job completion with missing message ID"""
        queue, mock_queue_instance = mock_queue

        job_data = {
            "id": "job-123",
            "queue_name": "processing",
            # Missing pgmq_msg_id
        }

        result = await queue.complete_job(job_data)

        assert result is False
        assert len(mock_queue_instance.deleted_messages) == 0

    @pytest.mark.asyncio
    async def test_complete_job_default_queue_name(self, mock_queue):
        """Test job completion with default queue name"""
        queue, mock_queue_instance = mock_queue

        job_data = {
            "id": "job-123",
            "pgmq_msg_id": 42,
            # Missing queue_name - should use table_name
        }

        result = await queue.complete_job(job_data)

        assert result is True
        deleted_msg = mock_queue_instance.deleted_messages[0]
        assert deleted_msg["queue_name"] == "processing_job"  # table_name


class TestSupabaseQueueStats:
    """Test SupabaseQueue statistics functionality"""

    @pytest.fixture
    def mock_queue(self):
        """Create a mock queue for testing"""
        with patch("app.services.supabase_queue.PGMQueue") as mock_pgmqueue_class:
            mock_queue_instance = MockPGMQueue()
            mock_pgmqueue_class.return_value = mock_queue_instance

            queue = SupabaseQueue(
                host="localhost",
                port="5432",
                user="test_user",
                password="test_pass",
                db_name="test_db",
            )
            queue.queue = mock_queue_instance
            queue._initialized = True
            yield queue, mock_queue_instance

    @pytest.mark.asyncio
    async def test_get_queue_stats_success(self, mock_queue):
        """Test successful queue statistics retrieval"""
        queue, mock_queue_instance = mock_queue

        stats = await queue.get_queue_stats("processing")

        expected_stats = {
            "queued": 5,
            "total": 100,
            "newest_msg_age_sec": 30,
            "oldest_msg_age_sec": 3600,
        }

        assert stats == expected_stats

    @pytest.mark.asyncio
    async def test_get_queue_stats_default_queue_name(self, mock_queue):
        """Test queue statistics with default queue name"""
        queue, mock_queue_instance = mock_queue

        stats = await queue.get_queue_stats()  # No queue_name provided

        assert isinstance(stats, dict)
        assert "queued" in stats
        assert "total" in stats

    @pytest.mark.asyncio
    async def test_get_queue_stats_error(self, mock_queue):
        """Test queue statistics when metrics call fails"""
        queue, mock_queue_instance = mock_queue

        async def mock_metrics_error(*args, **kwargs):
            raise Exception("Metrics failed")

        mock_queue_instance.metrics = mock_metrics_error

        stats = await queue.get_queue_stats("processing")

        assert stats == {}


class TestSupabaseQueueClose:
    """Test SupabaseQueue close functionality"""

    @pytest.mark.asyncio
    async def test_close_initialized_queue(self):
        """Test closing an initialized queue"""
        with patch("app.services.supabase_queue.PGMQueue") as mock_pgmqueue_class:
            mock_queue_instance = MockPGMQueue()
            mock_pgmqueue_class.return_value = mock_queue_instance

            queue = SupabaseQueue(
                host="localhost",
                port="5432",
                user="test_user",
                password="test_pass",
                db_name="test_db",
            )
            queue._initialized = True
            queue.queue = mock_queue_instance

            await queue.close()

            assert queue._initialized is False
            assert mock_queue_instance.initialized is False

    @pytest.mark.asyncio
    async def test_close_uninitialized_queue(self):
        """Test closing an uninitialized queue"""
        queue = SupabaseQueue(
            host="localhost",
            port="5432",
            user="test_user",
            password="test_pass",
            db_name="test_db",
        )

        # Should not raise an exception
        await queue.close()

        assert queue._initialized is False


class TestSupabaseQueueIntegration:
    """Integration tests for SupabaseQueue"""

    @pytest.mark.asyncio
    async def test_full_job_lifecycle(self):
        """Test complete job lifecycle: enqueue -> complete"""
        with patch("app.services.supabase_queue.PGMQueue") as mock_pgmqueue_class:
            mock_queue_instance = MockPGMQueue()
            mock_pgmqueue_class.return_value = mock_queue_instance

            queue = SupabaseQueue(
                host="localhost",
                port="5432",
                user="test_user",
                password="test_pass",
                db_name="test_db",
            )

            # Enqueue job
            payload = {"repo_id": "repo-123", "user_id": "user-456"}
            job_id = await queue.enqueue("processing", payload)

            # Complete job
            job_data = {
                "id": job_id,
                "pgmq_msg_id": int(job_id),
                "queue_name": "processing",
            }

            result = await queue.complete_job(job_data)

            assert job_id == "1"
            assert result is True
            assert len(mock_queue_instance.sent_messages) == 1
            assert len(mock_queue_instance.deleted_messages) == 1
