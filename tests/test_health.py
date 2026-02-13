"""Tests for health score computation."""

from datetime import datetime, timedelta

from src.models.events import Heartbeat
from src.models.worker import WorkerHealth, WorkerStatus
from src.health.monitor import HealthMonitor


def make_heartbeat(
    cpu: float = 30.0,
    memory: float = 40.0,
    eps: float = 1000.0,
    latency: float = 20.0,
    errors: int = 0,
    worker_id: str = "w1",
) -> Heartbeat:
    return Heartbeat(
        worker_id=worker_id,
        pipeline_id="test-pipeline",
        node_id="n1",
        cpu_percent=cpu,
        memory_percent=memory,
        events_per_second=eps,
        events_processed=10000,
        avg_latency_ms=latency,
        errors=errors,
    )


def make_monitor() -> HealthMonitor:
    """Create a HealthMonitor without starting Redis connections."""
    return HealthMonitor(
        redis_host="localhost",
        redis_port=6379,
        runtime_manager=None,
    )


class TestHealthScoring:
    def test_healthy_worker(self):
        """Low CPU, low memory, fast latency -> high score."""
        monitor = make_monitor()
        hb = make_heartbeat(cpu=30, memory=40, latency=20)
        monitor._heartbeats["w1"] = hb
        monitor._last_heartbeat_time["w1"] = datetime.utcnow()

        health = monitor._compute_health("w1")
        assert health.score >= 70
        assert health.status == WorkerStatus.RUNNING
        assert health.issues == []

    def test_high_cpu_degrades_score(self):
        """High CPU should lower the score and flag an issue."""
        monitor = make_monitor()
        hb = make_heartbeat(cpu=90, memory=40, latency=20)
        monitor._heartbeats["w1"] = hb
        monitor._last_heartbeat_time["w1"] = datetime.utcnow()

        health = monitor._compute_health("w1")
        assert health.cpu_score <= 20
        assert any("CPU" in issue for issue in health.issues)

    def test_high_memory_degrades_score(self):
        """High memory should lower the score."""
        monitor = make_monitor()
        hb = make_heartbeat(cpu=30, memory=85, latency=20)
        monitor._heartbeats["w1"] = hb
        monitor._last_heartbeat_time["w1"] = datetime.utcnow()

        health = monitor._compute_health("w1")
        assert health.memory_score < 50
        assert any("memory" in issue.lower() for issue in health.issues)

    def test_high_latency_degrades_score(self):
        """High latency should lower the score."""
        monitor = make_monitor()
        hb = make_heartbeat(cpu=30, memory=40, latency=400)
        monitor._heartbeats["w1"] = hb
        monitor._last_heartbeat_time["w1"] = datetime.utcnow()

        health = monitor._compute_health("w1")
        assert health.latency_score < 30
        assert any("latency" in issue.lower() for issue in health.issues)

    def test_extreme_latency_zero_score(self):
        """500ms+ latency should get 0 latency score."""
        monitor = make_monitor()
        hb = make_heartbeat(cpu=30, memory=40, latency=600)
        monitor._heartbeats["w1"] = hb
        monitor._last_heartbeat_time["w1"] = datetime.utcnow()

        health = monitor._compute_health("w1")
        assert health.latency_score == 0.0

    def test_no_heartbeat_data_is_dead(self):
        """No heartbeat data should return score 0 and DEAD status."""
        monitor = make_monitor()
        health = monitor._compute_health("nonexistent")
        assert health.score == 0
        assert health.status == WorkerStatus.DEAD

    def test_degraded_threshold(self):
        """Score between 30-70 should be DEGRADED."""
        monitor = make_monitor()
        # High CPU + high memory = low combined score
        hb = make_heartbeat(cpu=80, memory=80, latency=100)
        monitor._heartbeats["w1"] = hb
        monitor._last_heartbeat_time["w1"] = datetime.utcnow()

        health = monitor._compute_health("w1")
        assert health.score < 70
        assert health.status == WorkerStatus.DEGRADED

    def test_score_weights(self):
        """Verify the weighting formula: CPU 30%, Memory 30%, Throughput 20%, Latency 20%."""
        monitor = make_monitor()
        # Perfect metrics -> all sub-scores 100 -> total 100
        hb = make_heartbeat(cpu=0, memory=0, latency=0)
        monitor._heartbeats["w1"] = hb
        monitor._last_heartbeat_time["w1"] = datetime.utcnow()

        health = monitor._compute_health("w1")
        assert health.cpu_score == 100.0
        assert health.memory_score == 100.0
        assert health.latency_score == 100.0
        assert health.score == 100.0

    def test_memory_score_cliff(self):
        """Memory below 60% should be score 100, then drops after 60%."""
        monitor = make_monitor()

        # 50% memory -> 100 score
        hb = make_heartbeat(memory=50)
        monitor._heartbeats["w1"] = hb
        health = monitor._compute_health("w1")
        assert health.memory_score == 100.0

        # 70% memory -> score drops
        hb = make_heartbeat(memory=70)
        monitor._heartbeats["w1"] = hb
        health = monitor._compute_health("w1")
        assert health.memory_score == 75.0

        # 100% memory -> 0
        hb = make_heartbeat(memory=100)
        monitor._heartbeats["w1"] = hb
        health = monitor._compute_health("w1")
        assert health.memory_score == 0.0


class TestThroughputScoring:
    def test_insufficient_data_is_perfect(self):
        """Less than 3 data points -> assume healthy."""
        monitor = make_monitor()
        hb = make_heartbeat(cpu=30, memory=40, latency=20)
        monitor._heartbeats["w1"] = hb
        # Only 1 data point
        now = datetime.utcnow()
        monitor._throughput_history["w1"] = [(now, 1000)]

        score = monitor._compute_throughput_score("w1")
        assert score == 100.0

    def test_stable_throughput_is_perfect(self):
        """Consistent throughput -> score 100."""
        monitor = make_monitor()
        now = datetime.utcnow()
        monitor._throughput_history["w1"] = [
            (now - timedelta(seconds=i), 1000) for i in range(10, 0, -1)
        ]
        score = monitor._compute_throughput_score("w1")
        assert score == 100.0

    def test_throughput_drop_degrades_score(self):
        """Current throughput < 50% of average -> low score."""
        monitor = make_monitor()
        now = datetime.utcnow()
        # 9 samples at 1000, then current at 200 (80% drop)
        history = [(now - timedelta(seconds=i), 1000) for i in range(10, 1, -1)]
        history.append((now, 200))
        monitor._throughput_history["w1"] = history

        score = monitor._compute_throughput_score("w1")
        assert score == 30.0

    def test_moderate_throughput_drop(self):
        """Current throughput 50-70% of average -> moderate score."""
        monitor = make_monitor()
        now = datetime.utcnow()
        history = [(now - timedelta(seconds=i), 1000) for i in range(10, 1, -1)]
        history.append((now, 600))  # 40% drop
        monitor._throughput_history["w1"] = history

        score = monitor._compute_throughput_score("w1")
        assert score == 60.0


class TestWorkerHealthModel:
    def test_is_healthy(self):
        health = WorkerHealth(score=80)
        assert health.is_healthy is True
        assert health.is_critical is False

    def test_is_critical(self):
        health = WorkerHealth(score=20)
        assert health.is_healthy is False
        assert health.is_critical is True

    def test_boundary_values(self):
        assert WorkerHealth(score=70).is_healthy is True
        assert WorkerHealth(score=69).is_healthy is False
        assert WorkerHealth(score=30).is_critical is False
        assert WorkerHealth(score=29).is_critical is True
