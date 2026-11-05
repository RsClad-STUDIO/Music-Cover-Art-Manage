import logging
import math
import time
from dataclasses import asdict, dataclass

LOGGER = logging.getLogger(__name__)
MIN_IMPROVEMENT = 0.05
MAX_WORKERS = 8
MAX_SUB_WORKERS = 8


@dataclass
class PerfConfig:
    workers: int
    sub_workers: int
    throughput: float = 0.0

    def to_key(self):
        return self.workers, self.sub_workers


class PerformanceOptimizer:
    def __init__(self, env_id, initial_data=None):
        self.env_id = env_id
        self.tested_configs = set()
        self.historical_best = self._parse_initial_data(initial_data)
        self.current_baseline = None
        self.current_best = None
        self.is_searching = True
        self.is_baseline_tested = False
        self.search_steps = [(4, 4), (4, 6), (4, 8), (6, 8), (8, 8)]
        self.step_index = 0
        self.segment_start_time = 0.0
        self.segment_file_count = 0
        self.current_config = None

        self.mode = "Warm Start" if self.historical_best.throughput > 0 else "Cold Start"
        LOGGER.info(
            "Optimizer environment=%s mode=%s historical=%s/%s @ %.2f files/sec",
            self.env_id, self.mode, self.historical_best.workers,
            self.historical_best.sub_workers, self.historical_best.throughput,
        )

    @staticmethod
    def _positive_int(value, default, maximum):
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        return max(1, min(maximum, parsed))

    def _parse_initial_data(self, data):
        """Read both legacy and current optimizer settings defensively."""
        if not isinstance(data, dict):
            data = {}
        candidate = data.get("historical_best", data)
        if not isinstance(candidate, dict):
            candidate = {}
        workers = self._positive_int(candidate.get("workers", 4), 4, MAX_WORKERS)
        sub_workers = self._positive_int(candidate.get("sub_workers", 4), 4, MAX_SUB_WORKERS)
        try:
            throughput = float(candidate.get("throughput", 0.0))
            if not math.isfinite(throughput) or throughput < 0:
                throughput = 0.0
        except (TypeError, ValueError):
            throughput = 0.0
        return PerfConfig(workers, sub_workers, throughput)

    def get_next_config(self):
        if not self.is_searching:
            return self.current_best or self.historical_best

        if not self.is_baseline_tested:
            return self.historical_best

        while self.step_index < len(self.search_steps):
            workers, sub_workers = self.search_steps[self.step_index]
            self.step_index += 1
            if (workers, sub_workers) not in self.tested_configs:
                return PerfConfig(workers, sub_workers, 0.0)

        self.is_searching = False
        return self.current_best or self.historical_best

    def start_segment(self, config):
        self.current_config = config
        self.tested_configs.add(config.to_key())
        self.segment_start_time = time.perf_counter()
        self.segment_file_count = 0
        LOGGER.info("Optimizer testing configuration %s/%s", config.workers, config.sub_workers)

    def record_file(self):
        self.segment_file_count += 1

    def end_segment(self):
        duration = time.perf_counter() - self.segment_start_time
        if self.current_config is None or self.segment_file_count <= 0 or duration <= 0:
            LOGGER.warning("Optimizer skipped an empty or invalid measurement segment")
            return False

        # Do not discard sub-second segments: doing so left the baseline unset
        # and caused the optimizer to request the same baseline indefinitely.
        throughput = self.segment_file_count / duration
        if not math.isfinite(throughput) or throughput <= 0:
            return False

        LOGGER.info(
            "Optimizer result %s/%s: %.2f files/sec",
            self.current_config.workers, self.current_config.sub_workers, throughput,
        )

        if not self.is_baseline_tested:
            self.current_baseline = PerfConfig(
                self.current_config.workers, self.current_config.sub_workers, throughput
            )
            self.current_best = self.current_baseline
            self.is_baseline_tested = True
            return True

        if self.current_best and self.current_best.throughput > 0:
            improvement = (throughput - self.current_best.throughput) / self.current_best.throughput
        else:
            improvement = float("inf")

        if improvement >= MIN_IMPROVEMENT:
            self.current_best = PerfConfig(
                self.current_config.workers, self.current_config.sub_workers, throughput
            )
            LOGGER.info("Optimizer accepted configuration (improvement %.1f%%)", improvement * 100)
        else:
            LOGGER.info("Optimizer retained current best (change %.1f%%)", improvement * 100)
        return True

    def save_result(self, config_data):
        if not self.current_best or self.current_best.throughput <= 0:
            return False

        if not isinstance(config_data.get("optimized_results"), dict):
            config_data["optimized_results"] = {}

        historical = self.historical_best
        if self.current_best.throughput > historical.throughput * (1 + MIN_IMPROVEMENT):
            historical = self.current_best
            self.historical_best = historical

        config_data["optimized_results"][self.env_id] = {
            "historical_best": asdict(historical),
            "last_result": asdict(self.current_best),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return True
