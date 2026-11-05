import optimizer
from optimizer import PerformanceOptimizer, PerfConfig


def test_short_baseline_segment_is_not_discarded(monkeypatch):
    ticks = iter([100.0, 100.5])
    monkeypatch.setattr(optimizer.time, "perf_counter", lambda: next(ticks))

    subject = PerformanceOptimizer("test-machine")
    baseline = subject.get_next_config()
    assert baseline == PerfConfig(4, 4, 0.0)

    subject.start_segment(baseline)
    subject.record_file()
    assert subject.end_segment() is True
    assert subject.is_baseline_tested is True
    assert subject.current_best.throughput == 2.0

    next_config = subject.get_next_config()
    assert next_config.to_key() == (4, 6)


def test_invalid_historical_settings_are_sanitized():
    subject = PerformanceOptimizer(
        "test-machine",
        {"historical_best": {
            "workers": "invalid",
            "sub_workers": 0,
            "throughput": float("nan"),
        }},
    )

    assert subject.historical_best.workers == 4
    assert subject.historical_best.sub_workers == 1
    assert subject.historical_best.throughput == 0.0


def test_optimizer_accepts_legacy_settings():
    subject = PerformanceOptimizer(
        "test-machine",
        {"workers": 6, "sub_workers": 3, "throughput": 12.5},
    )

    assert subject.historical_best.to_key() == (6, 3)
    assert subject.historical_best.throughput == 12.5


def test_empty_segment_does_not_mark_baseline_tested(monkeypatch):
    ticks = iter([10.0, 10.25])
    monkeypatch.setattr(optimizer.time, "perf_counter", lambda: next(ticks))

    subject = PerformanceOptimizer("test-machine")
    subject.start_segment(subject.get_next_config())

    assert subject.end_segment() is False
    assert subject.is_baseline_tested is False
