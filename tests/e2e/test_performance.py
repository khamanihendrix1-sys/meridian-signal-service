import asyncio
import os
import statistics
import time
from typing import Any

import psutil
import pytest

from tests.e2e.test_end_to_end import WebhookSimulator


class PerformanceMetrics:
    """Collect and analyze performance metrics."""

    def __init__(self) -> None:
        self.response_times: list[float] = []
        self.memory_usage: list[float] = []
        self.cpu_usage: list[float] = []
        self.error_count = 0
        self.start_time: float | None = None
        self.end_time: float | None = None

    def start_measurement(self) -> None:
        """Start performance measurement."""
        self.start_time = time.time()

    def end_measurement(self) -> None:
        """End performance measurement."""
        self.end_time = time.time()

    def add_response_time(self, response_time: float) -> None:
        """Add a response time measurement."""
        self.response_times.append(response_time)

    def add_memory_usage(self, memory_mb: float) -> None:
        """Add memory usage measurement."""
        self.memory_usage.append(memory_mb)

    def add_cpu_usage(self, cpu_percent: float) -> None:
        """Add CPU usage measurement."""
        self.cpu_usage.append(cpu_percent)

    def increment_error_count(self) -> None:
        """Increment error count."""
        self.error_count += 1

    def get_summary(self) -> dict[str, Any]:
        """Get performance summary statistics."""
        if not self.response_times:
            return {"error": "No measurements collected"}

        total_duration = (
            self.end_time - self.start_time
            if self.start_time is not None and self.end_time is not None
            else 0.0
        )

        summary: dict[str, Any] = {
            "total_duration": total_duration,
            "total_requests": len(self.response_times),
            "response_time": {
                "min": min(self.response_times),
                "max": max(self.response_times),
                "mean": statistics.mean(self.response_times),
                "median": statistics.median(self.response_times),
                "p95": statistics.quantiles(self.response_times, n=20)[
                    18
                ],  # 95th percentile
                "p99": (
                    statistics.quantiles(self.response_times, n=100)[98]
                    if len(self.response_times) >= 100
                    else max(self.response_times)
                ),
            },
            "throughput": {
                "requests_per_second": (
                    len(self.response_times) / total_duration
                    if total_duration > 0
                    else 0.0
                )
            },
            "memory_usage": {
                "avg_mb": (
                    statistics.mean(self.memory_usage) if self.memory_usage else 0.0
                ),
                "max_mb": max(self.memory_usage) if self.memory_usage else 0.0,
            },
            "cpu_usage": {
                "avg_percent": (
                    statistics.mean(self.cpu_usage) if self.cpu_usage else 0.0
                ),
                "max_percent": max(self.cpu_usage) if self.cpu_usage else 0.0,
            },
            "error_rate": self.error_count / len(self.response_times),
        }

        return summary


class LoadGenerator:
    """Generate various types of load for performance testing."""

    def __init__(self, simulator: WebhookSimulator) -> None:
        self.simulator = simulator

    async def generate_constant_load(
        self, rate_per_second: int, duration_seconds: int
    ) -> PerformanceMetrics:
        """Generate constant load at specified rate."""
        metrics = PerformanceMetrics()
        metrics.start_measurement()

        end_time = time.time() + duration_seconds
        request_count = 0

        while time.time() < end_time:
            batch_start = time.time()

            # Generate batch of requests
            tasks = []
            for _ in range(rate_per_second):
                task = self._single_webhook_request()
                tasks.append(task)

            # Execute batch
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Record metrics
            batch_end = time.time()
            batch_duration = batch_end - batch_start

            for result in results:
                if isinstance(result, float):
                    metrics.add_response_time(result)
                else:
                    metrics.increment_error_count()

            request_count += len(tasks)

            # Monitor system resources
            metrics.add_memory_usage(self._get_memory_usage())
            metrics.add_cpu_usage(self._get_cpu_usage())

            # Wait for next batch
            remaining_time = 1.0 - batch_duration
            if remaining_time > 0:
                await asyncio.sleep(remaining_time)

        metrics.end_measurement()
        return metrics

    async def generate_burst_load(
        self, burst_size: int, burst_count: int, delay_between_bursts: float
    ) -> PerformanceMetrics:
        """Generate burst load patterns."""
        metrics = PerformanceMetrics()
        metrics.start_measurement()

        for burst in range(burst_count):
            # Generate burst of requests simultaneously
            tasks = [self._single_webhook_request() for _ in range(burst_size)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Record metrics
            for result in results:
                if isinstance(result, float):
                    metrics.add_response_time(result)
                else:
                    metrics.increment_error_count()

            # Monitor resources
            metrics.add_memory_usage(self._get_memory_usage())
            metrics.add_cpu_usage(self._get_cpu_usage())

            # Delay between bursts
            if burst < burst_count - 1:
                await asyncio.sleep(delay_between_bursts)

        metrics.end_measurement()
        return metrics

    async def generate_ramp_load(
        self, start_rate: int, end_rate: int, ramp_duration: int
    ) -> PerformanceMetrics:
        """Generate load that ramps up over time."""
        metrics = PerformanceMetrics()
        metrics.start_measurement()

        total_duration = ramp_duration
        steps = 10
        step_duration = total_duration / steps

        for step in range(steps):
            # Calculate current rate for this step
            progress = step / (steps - 1)
            current_rate = int(start_rate + (end_rate - start_rate) * progress)

            # Generate load at current rate for step duration
            step_start = time.time()
            requests_in_step = 0

            while (
                time.time() - step_start < step_duration
                and requests_in_step < current_rate
            ):
                tasks = [
                    self._single_webhook_request()
                    for _ in range(min(10, current_rate - requests_in_step))
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, float):
                        metrics.add_response_time(result)
                    else:
                        metrics.increment_error_count()

                requests_in_step += len(tasks)

                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)

            # Monitor resources
            metrics.add_memory_usage(self._get_memory_usage())
            metrics.add_cpu_usage(self._get_cpu_usage())

        metrics.end_measurement()
        return metrics

    async def _single_webhook_request(self) -> float:
        """Execute a single webhook request and return response time."""
        start_time = time.time()

        try:
            # Create webhook payload
            payload = self.simulator.create_signal_webhook_payload()

            # Simulate processing (this would normally be an HTTP request)
            self.simulator.simulate_wix_webhook_processing(payload)

            # Simulate some processing delay (mimic real API call)
            await asyncio.sleep(0.001)  # 1ms simulated processing

            response_time = time.time() - start_time
            return response_time

        except Exception:
            # Return negative response time to indicate error
            return -1.0

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return float(process.memory_info().rss) / 1024 / 1024

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return float(psutil.cpu_percent(interval=0.1))


@pytest.mark.asyncio
class TestWebhookPerformance:
    """Test webhook processing performance."""

    @pytest.fixture
    async def load_generator(self) -> LoadGenerator:
        """Create load generator."""
        simulator = WebhookSimulator()
        return LoadGenerator(simulator)

    async def test_constant_load_performance(
        self, load_generator: LoadGenerator
    ) -> None:
        """Test performance under constant load."""
        # Test with 10 requests per second for 5 seconds
        metrics = await load_generator.generate_constant_load(
            rate_per_second=10, duration_seconds=5
        )

        summary = metrics.get_summary()

        # Performance assertions
        assert summary["response_time"]["mean"] < 0.1  # Average response time < 100ms
        assert summary["response_time"]["p95"] < 0.2  # 95th percentile < 200ms
        assert summary["error_rate"] < 0.05  # Error rate < 5%
        assert summary["throughput"]["requests_per_second"] >= 8  # At least 8 req/sec

        print(f"Constant load test results: {summary}")

    async def test_burst_load_performance(self, load_generator: LoadGenerator) -> None:
        """Test performance under burst load."""
        # Test with bursts of 20 requests, 5 bursts, 1 second delay
        metrics = await load_generator.generate_burst_load(
            burst_size=20, burst_count=5, delay_between_bursts=1.0
        )

        summary = metrics.get_summary()

        # Performance assertions for burst scenarios
        assert summary["response_time"]["max"] < 0.5  # Max response time < 500ms
        assert summary["error_rate"] < 0.1  # Error rate < 10% under burst

        print(f"Burst load test results: {summary}")

    async def test_ramp_load_performance(self, load_generator: LoadGenerator) -> None:
        """Test performance under ramping load."""
        # Ramp from 5 to 50 requests per step over 10 seconds
        metrics = await load_generator.generate_ramp_load(
            start_rate=5, end_rate=50, ramp_duration=10
        )

        summary = metrics.get_summary()

        # Performance assertions for ramp scenarios
        assert (
            summary["response_time"]["p95"] < 0.3
        )  # 95th percentile < 300ms under ramp
        assert (
            summary["throughput"]["requests_per_second"] >= 20
        )  # Maintain reasonable throughput

        print(f"Ramp load test results: {summary}")

    async def test_memory_usage_under_load(self, load_generator: LoadGenerator) -> None:
        """Test memory usage patterns under load."""
        initial_memory = load_generator._get_memory_usage()

        # Generate sustained load
        metrics = await load_generator.generate_constant_load(
            rate_per_second=15, duration_seconds=10
        )

        summary = metrics.get_summary()

        # Memory assertions
        memory_increase = summary["memory_usage"]["max_mb"] - initial_memory
        assert memory_increase < 50  # Memory increase < 50MB during test
        assert (
            summary["memory_usage"]["avg_mb"] < 200
        )  # Average memory usage reasonable

        print(
            f"Memory usage test - Initial: {initial_memory:.1f}MB, "
            f"Peak: {summary['memory_usage']['max_mb']:.1f}MB, "
            f"Increase: {memory_increase:.1f}MB"
        )

    async def test_cpu_usage_under_load(self, load_generator: LoadGenerator) -> None:
        """Test CPU usage patterns under load."""
        # Generate load
        metrics = await load_generator.generate_constant_load(
            rate_per_second=20, duration_seconds=8
        )

        summary = metrics.get_summary()

        # CPU assertions (these will vary based on system capabilities)
        assert summary["cpu_usage"]["avg_percent"] < 80  # Average CPU < 80%
        assert summary["cpu_usage"]["max_percent"] < 95  # Peak CPU < 95%

        print(
            f"CPU usage test - Avg: {summary['cpu_usage']['avg_percent']:.1f}%, "
            f"Peak: {summary['cpu_usage']['max_percent']:.1f}%"
        )


@pytest.mark.asyncio
class TestSystemPerformance:
    """Test overall system performance characteristics."""

    async def test_concurrent_user_simulation(self) -> None:
        """Simulate multiple concurrent users."""
        simulator = WebhookSimulator()

        # Simulate 5 concurrent users, each sending 10 requests over 30 seconds
        async def user_simulation(user_id: int) -> list[float]:
            response_times: list[float] = []
            for _ in range(10):
                start_time = time.time()
                try:
                    payload = simulator.create_signal_webhook_payload()
                    simulator.simulate_wix_webhook_processing(payload)
                    await asyncio.sleep(0.01)  # Simulate network delay
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                except Exception:
                    response_times.append(-1.0)  # Error

                # Random delay between requests (0.5-2 seconds)
                await asyncio.sleep(0.5 + (user_id * 0.1))

            return response_times

        # Run concurrent user simulations
        tasks = [user_simulation(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Analyze results
        all_response_times: list[float] = []
        error_count = 0

        for user_results in results:
            for response_time in user_results:
                if response_time < 0:
                    error_count += 1
                else:
                    all_response_times.append(response_time)

        total_requests = sum(len(user_results) for user_results in results)
        error_rate = error_count / total_requests if total_requests > 0 else 0

        # Performance assertions
        assert len(all_response_times) > 0
        assert statistics.mean(all_response_times) < 0.2  # Average < 200ms
        assert error_rate < 0.1  # Error rate < 10%

        print(
            f"Concurrent user simulation - Users: 5, Requests: {total_requests}, "
            f"Avg Response: {statistics.mean(all_response_times):.3f}s, "
            f"Error Rate: {error_rate:.1%}"
        )

    async def test_peak_load_handling(self) -> None:
        """Test system behavior under peak load conditions."""
        simulator = WebhookSimulator()
        load_gen = LoadGenerator(simulator)

        # Generate peak load: 50 requests/second for 10 seconds
        metrics = await load_gen.generate_constant_load(
            rate_per_second=50, duration_seconds=10
        )

        summary = metrics.get_summary()

        # Under peak load, we expect some degradation but system should remain stable
        assert summary["error_rate"] < 0.2  # Error rate < 20% under peak load
        assert summary["response_time"]["p99"] < 1.0  # 99th percentile < 1 second

        # System should maintain some throughput even under peak load
        assert summary["throughput"]["requests_per_second"] >= 20

        print(
            f"Peak load test - Throughput: {summary['throughput']['requests_per_second']:.1f} req/sec, "
            f"P99 Latency: {summary['response_time']['p99']:.3f}s, "
            f"Error Rate: {summary['error_rate']:.1%}"
        )

    async def test_recovery_after_load(self) -> None:
        """Test system recovery after high load periods."""
        simulator = WebhookSimulator()
        load_gen = LoadGenerator(simulator)

        # Phase 1: High load
        print("Phase 1: High load period")
        high_load_metrics = await load_gen.generate_constant_load(30, 5)
        high_load_summary = high_load_metrics.get_summary()

        # Phase 2: Recovery period with normal load
        print("Phase 2: Recovery period")
        recovery_metrics = await load_gen.generate_constant_load(10, 5)
        recovery_summary = recovery_metrics.get_summary()

        # Recovery assertions
        assert (
            recovery_summary["response_time"]["mean"]
            <= high_load_summary["response_time"]["mean"] * 1.5
        )
        assert recovery_summary["error_rate"] <= high_load_summary["error_rate"] * 2

        print(
            f"Recovery test - High load avg: {high_load_summary['response_time']['mean']:.3f}s, "
            f"Recovery avg: {recovery_summary['response_time']['mean']:.3f}s"
        )


# Performance benchmark tests
@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Performance benchmark tests for continuous monitoring."""

    async def test_webhook_processing_benchmark(self) -> None:
        """Benchmark webhook processing performance."""
        simulator = WebhookSimulator()

        # Benchmark processing 1000 webhooks
        start_time = time.time()

        for i in range(1000):
            payload = simulator.create_signal_webhook_payload()
            simulator.simulate_wix_webhook_processing(payload)

        end_time = time.time()
        total_time = end_time - start_time

        throughput = 1000 / total_time  # requests per second

        # Benchmark assertions
        assert throughput > 500  # Should handle at least 500 req/sec
        assert total_time < 5.0  # Should complete within 5 seconds

        print(
            f"Webhook processing benchmark: {throughput:.0f} req/sec, "
            f"Total time: {total_time:.2f}s"
        )

    async def test_memory_efficiency_benchmark(self) -> None:
        """Benchmark memory efficiency."""
        simulator = WebhookSimulator()

        initial_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

        # Process many webhooks
        for i in range(5000):
            payload = simulator.create_signal_webhook_payload()
            simulator.simulate_wix_webhook_processing(payload)

        final_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory

        # Memory efficiency assertions
        assert memory_increase < 10  # Memory increase < 10MB for 5000 requests

        print(
            f"Memory efficiency benchmark: {memory_increase:.1f}MB increase for 5000 requests"
        )
