import time
import platform
import os
import json
import hashlib
import logging
from dataclasses import dataclass, asdict

CACHE_FILE = "optimizer_cache.json"
MIN_IMPROVEMENT = 0.05  # 5% 以上の改善が必要
MAX_WORKERS = 8
MAX_SUB_WORKERS = 8

@dataclass
class PerfConfig:
    workers: int
    sub_workers: int
    throughput: float = 0.0

    def to_key(self):
        return (self.workers, self.sub_workers)

class PerformanceOptimizer:
    def __init__(self, env_id, initial_data=None):
        self.env_id = env_id
        self.tested_configs = set()
        
        # 1. データのロードと分離
        self.historical_best = self._parse_initial_data(initial_data)
        self.current_baseline = None
        self.current_best = None
        
        self.is_searching = True
        self.is_baseline_tested = False
        
        # 探索ステップの定義
        self.search_steps = [(4, 4), (4, 6), (4, 8), (6, 8), (8, 8)]
        self.step_index = 0
        
        self.segment_start_time = 0
        self.segment_file_count = 0

        # ログ出力
        print(f"[Optimizer] Environment: {self.env_id}")
        if self.historical_best.throughput > 0:
            self.mode = "Warm Start"
            print(f"[Optimizer] Mode: Warm Start")
            print(f"[Optimizer] Historical Best: {self.historical_best.workers}/{self.historical_best.sub_workers} @ {self.historical_best.throughput:.2f} files/sec")
        else:
            self.mode = "Cold Start"
            print(f"[Optimizer] Mode: Cold Start")
            print(f"[Optimizer] No previous optimization result found.")

    def _parse_initial_data(self, data):
        """既存の config 形式から Historical Best を抽出（後方互換性維持）"""
        if not data:
            return PerfConfig(4, 4, 0.0)
        
        # 新形式 (v1.2)
        if "historical_best" in data:
            hb = data["historical_best"]
            return PerfConfig(hb.get("workers", 4), hb.get("sub_workers", 4), hb.get("throughput", 0.0))
        
        # 旧形式 (v1.1)
        return PerfConfig(data.get("workers", 4), data.get("sub_workers", 4), data.get("throughput", 0.0))

    def get_next_config(self):
        """次に測定すべき設定を返す。"""
        if not self.is_searching:
            return self.current_best or self.historical_best

        # 1. 最初の測定（Baseline）
        if not self.is_baseline_tested:
            # Warm Start なら過去のベスト、Cold Start なら 4/4
            return self.historical_best

        # 2. 探索リストから未テストの設定を探す
        while self.step_index < len(self.search_steps):
            w, sw = self.search_steps[self.step_index]
            self.step_index += 1
            if (w, sw) not in self.tested_configs:
                return PerfConfig(w, sw, 0.0)

        # 3. 全てテスト済みの場合は探索終了
        self.is_searching = False
        return self.current_best

    def start_segment(self, config):
        self.current_config = config
        self.tested_configs.add(config.to_key())
        self.segment_start_time = time.time()
        self.segment_file_count = 0
        
        if not self.is_baseline_tested:
            print(f"\n[Optimizer] Testing baseline: {config.workers}/{config.sub_workers}")
        else:
            print(f"\n[Optimizer] Testing: {config.workers}/{config.sub_workers}")

    def record_file(self):
        self.segment_file_count += 1

    def end_segment(self):
        duration = time.time() - self.segment_start_time
        if duration < 1.0 or self.segment_file_count == 0:
            return
        
        tp = self.segment_file_count / duration
        print(f"[Optimizer] Result: {tp:.2f} files/sec")

        # 1. Baseline の確定
        if not self.is_baseline_tested:
            self.current_baseline = PerfConfig(self.current_config.workers, self.current_config.sub_workers, tp)
            self.current_best = self.current_baseline
            self.is_baseline_tested = True
            print(f"[Optimizer] Current Baseline: {self.current_best.workers}/{self.current_best.sub_workers} @ {tp:.2f} files/sec")
            return

        # 2. 改善判定（Current Best と比較）
        improvement = (tp - self.current_best.throughput) / self.current_best.throughput
        if improvement >= MIN_IMPROVEMENT:
            print(f"[Optimizer] Performance vs Current Best: +{improvement*100:.1f}% (Accepted)")
            self.current_best = PerfConfig(self.current_config.workers, self.current_config.sub_workers, tp)
            print(f"[Optimizer] New Current Best: {self.current_best.workers}/{self.current_best.sub_workers} @ {tp:.2f} files/sec")
        else:
            diff = improvement * 100
            print(f"[Optimizer] Performance vs Current Best: {diff:+.1f}% (No significant improvement)")
            print(f"[Optimizer] Keeping Current Best: {self.current_best.workers}/{self.current_best.sub_workers} @ {self.current_best.throughput:.2f} files/sec")

    def save_result(self, config_data):
        """最適化結果を config データ構造に反映する"""
        if not self.current_best or self.current_best.throughput == 0:
            return False

        if "optimized_results" not in config_data:
            config_data["optimized_results"] = {}
        
        # Historical Best の更新判定
        hb_updated = False
        if self.current_best.throughput > self.historical_best.throughput * (1 + MIN_IMPROVEMENT):
            self.historical_best = self.current_best
            hb_updated = True

        # 保存用データ構築
        config_data["optimized_results"][self.env_id] = {
            "historical_best": asdict(self.historical_best),
            "last_result": asdict(self.current_best),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        print(f"\n[Optimizer] Optimization completed")
        print(f"[Optimizer] Current Best: {self.current_best.workers}/{self.current_best.sub_workers} @ {self.current_best.throughput:.2f} files/sec")
        if hb_updated:
            print(f"[Optimizer] Historical Best updated! -> {self.historical_best.throughput:.2f} files/sec")
        else:
            print(f"[Optimizer] Historical Best unchanged: {self.historical_best.throughput:.2f} files/sec")
            
        return True