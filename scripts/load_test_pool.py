#!/usr/bin/env python3
"""
Load Testing Script for Connection Pool Performance

This script tests database connection pool performance under various load scenarios.
It supports concurrent and burst load tests, and provides detailed statistics.
"""

import argparse
import logging
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ConnectionPoolLoadTester:
    """
    Load tester for database connection pooling.
    Provides methods for running concurrent and burst load tests,
    analyzing results, and printing statistics.
    """

    def __init__(
        self,
        db_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 10,
    ):
        """
        Initialize load tester.

        Args:
            db_url: Database connection URL
            pool_size: SQLAlchemy pool size
            max_overflow: Max overflow connections
            pool_timeout: Pool checkout timeout
        """
        self.db_url = db_url
        self.engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=True,
            echo_pool=False,
        )

        self.results: list[dict[str, Any]] = []

    def simple_query(self, query_id: int) -> dict[str, Any]:
        """
        Execute a simple SELECT query to test connection and response time.
        Args:
            query_id: Unique identifier for this query
        Returns:
            Dictionary with timing and status information
        """
        start_time = time.time()
        success = False
        error = None

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                success = True

        except Exception as e:
            error = str(e)
            logger.error(f"Query {query_id} failed: {error}")

        finally:
            duration = time.time() - start_time

        return {
            "query_id": query_id,
            "success": success,
            "duration": duration,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

    def complex_query(self, query_id: int) -> dict[str, Any]:
        """
        Execute a more complex query (simulated with pg_sleep and generate_series).
        Args:
            query_id: Unique identifier for this query
        Returns:
            Dictionary with timing and status information
        """
        start_time = time.time()
        success = False
        error = None

        try:
            with self.engine.connect() as conn:
                # Simulate a complex query with sleep
                result = conn.execute(text("SELECT pg_sleep(0.1), generate_series(1, 100)"))
                result.fetchall()
                success = True

        except Exception as e:
            error = str(e)
            logger.error(f"Query {query_id} failed: {error}")

        finally:
            duration = time.time() - start_time

        return {
            "query_id": query_id,
            "success": success,
            "duration": duration,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

    def run_concurrent_load(
        self, num_queries: int, num_workers: int, query_type: str = "simple"
    ) -> list[dict[str, Any]]:
        """
        Run concurrent load test using ThreadPoolExecutor.
        Args:
            num_queries: Total number of queries to execute
            num_workers: Number of concurrent workers
            query_type: Type of query ("simple" or "complex")
        Returns:
            List of result dictionaries
        """
        logger.info(
            f"Starting load test: {num_queries} {query_type} queries with {num_workers} workers"
        )

        query_func = self.simple_query if query_type == "simple" else self.complex_query

        results = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(query_func, i) for i in range(num_queries)]

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)

                    # Progress logging
                    if len(results) % 100 == 0:
                        logger.info(f"Completed {len(results)}/{num_queries} queries")

                except Exception as e:
                    logger.error(f"Future failed: {e}")

        total_duration = time.time() - start_time

        logger.info(f"Load test completed in {total_duration:.2f} seconds")

        return results

    def run_burst_load(
        self,
        burst_size: int,
        num_bursts: int,
        burst_interval: float = 1.0,
        query_type: str = "simple",
    ) -> list[dict[str, Any]]:
        """
        Run burst load test (periodic spikes of traffic).
        Args:
            burst_size: Number of queries per burst
            num_bursts: Number of bursts to execute
            burst_interval: Time between bursts (seconds)
            query_type: Type of query ("simple" or "complex")
        Returns:
            List of result dictionaries
        """
        logger.info(
            f"Starting burst load test: {num_bursts} bursts of {burst_size} {query_type} queries "
            f"(interval: {burst_interval}s)"
        )

        query_func = self.simple_query if query_type == "simple" else self.complex_query

        all_results = []
        query_counter = 0

        for burst_num in range(num_bursts):
            logger.info(f"Executing burst {burst_num + 1}/{num_bursts}")

            burst_start = time.time()

            with ThreadPoolExecutor(max_workers=burst_size) as executor:
                futures = [
                    executor.submit(query_func, query_counter + i) for i in range(burst_size)
                ]

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        all_results.append(result)
                    except Exception as e:
                        logger.error(f"Future failed: {e}")

            query_counter += burst_size
            burst_duration = time.time() - burst_start

            logger.info(f"Burst {burst_num + 1} completed in {burst_duration:.2f}s")

            # Wait before next burst (except after last burst)
            if burst_num < num_bursts - 1:
                time.sleep(burst_interval)

        return all_results

    def analyze_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze load test results and generate statistics.
        Args:
            results: List of query results
        Returns:
            Dictionary with statistical analysis (success rate, duration stats, etc.)
        """
        if not results:
            logger.warning("No results to analyze")
            return {}

        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        durations = [r["duration"] for r in successful]

        if not durations:
            logger.warning("No successful queries to analyze")
            return {
                "total_queries": len(results),
                "successful": 0,
                "failed": len(failed),
                "success_rate": 0.0,
            }

        analysis = {
            "total_queries": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) * 100,
            "duration_stats": {
                "min": min(durations),
                "max": max(durations),
                "mean": statistics.mean(durations),
                "median": statistics.median(durations),
                "stdev": statistics.stdev(durations) if len(durations) > 1 else 0,
                "p95": (
                    statistics.quantiles(durations, n=20)[18]
                    if len(durations) >= 20
                    else max(durations)
                ),
                "p99": (
                    statistics.quantiles(durations, n=100)[98]
                    if len(durations) >= 100
                    else max(durations)
                ),
            },
        }

        return analysis

    def print_analysis(self, analysis: dict[str, Any]):
        """
        Print analysis results in a readable format.
        Args:
            analysis: Dictionary with analysis statistics
        """
        print("\n" + "=" * 60)
        print("LOAD TEST RESULTS")
        print("=" * 60)

        print(f"\nTotal Queries:    {analysis['total_queries']}")
        print(f"Successful:       {analysis['successful']}")
        print(f"Failed:           {analysis['failed']}")
        print(f"Success Rate:     {analysis['success_rate']:.2f}%")

        if "duration_stats" in analysis:
            stats = analysis["duration_stats"]
            print("\nQuery Duration Statistics (seconds):")
            print(f"  Min:            {stats['min']:.4f}")
            print(f"  Max:            {stats['max']:.4f}")
            print(f"  Mean:           {stats['mean']:.4f}")
            print(f"  Median:         {stats['median']:.4f}")
            print(f"  Std Dev:        {stats['stdev']:.4f}")
            print(f"  P95:            {stats['p95']:.4f}")
            print(f"  P99:            {stats['p99']:.4f}")

        print("\n" + "=" * 60 + "\n")

    def cleanup(self):
        """Clean up resources."""
        self.engine.dispose()
        logger.info("Connection pool disposed")


def main() -> None:
    """
    Main entry point for the load test script.
    Parses command-line arguments, runs the selected test, and prints results.
    """
    parser = argparse.ArgumentParser(description="Connection Pool Load Tester")

    parser.add_argument(
        "--db-url",
        default="postgresql://trader:trader123@localhost:6432/mt5_trading",
        help="Database connection URL (default: via PgBouncer on port 6432)",
    )

    parser.add_argument(
        "--test-type",
        choices=["concurrent", "burst"],
        default="concurrent",
        help="Type of load test to run",
    )

    parser.add_argument(
        "--query-type",
        choices=["simple", "complex"],
        default="simple",
        help="Type of queries to execute",
    )

    parser.add_argument(
        "--num-queries",
        type=int,
        default=1000,
        help="Total number of queries (for concurrent test)",
    )

    parser.add_argument(
        "--num-workers",
        type=int,
        default=50,
        help="Number of concurrent workers (for concurrent test)",
    )

    parser.add_argument(
        "--burst-size",
        type=int,
        default=100,
        help="Number of queries per burst (for burst test)",
    )

    parser.add_argument(
        "--num-bursts", type=int, default=10, help="Number of bursts (for burst test)"
    )

    parser.add_argument(
        "--burst-interval",
        type=float,
        default=1.0,
        help="Interval between bursts in seconds (for burst test)",
    )

    parser.add_argument("--pool-size", type=int, default=5, help="SQLAlchemy pool size")

    parser.add_argument("--max-overflow", type=int, default=10, help="SQLAlchemy max overflow")

    args = parser.parse_args()

    # Create load tester
    tester = ConnectionPoolLoadTester(
        db_url=args.db_url, pool_size=args.pool_size, max_overflow=args.max_overflow
    )

    try:
        # Run load test
        if args.test_type == "concurrent":
            results = tester.run_concurrent_load(
                num_queries=args.num_queries,
                num_workers=args.num_workers,
                query_type=args.query_type,
            )
        else:  # burst
            results = tester.run_burst_load(
                burst_size=args.burst_size,
                num_bursts=args.num_bursts,
                burst_interval=args.burst_interval,
                query_type=args.query_type,
            )

        # Analyze and print results
        analysis = tester.analyze_results(results)
        tester.print_analysis(analysis)

        # Exit with error code if too many failures
        if analysis.get("success_rate", 0) < 95:
            logger.error("Success rate below 95% - test FAILED")
            sys.exit(1)
        else:
            logger.info("Test PASSED")
            sys.exit(0)

    finally:
        tester.cleanup()


# Entry point for script execution
if __name__ == "__main__":
    main()
