"""Tests for the optimizer rules engine."""

import pytest
from src.optimizer.analyzer import (
    AnalysisResult,
    FilterStats,
    OperatorStats,
    EdgeStats,
)
from src.optimizer.rules import (
    PredicatePushdownRule,
    OperatorFusionRule,
    AutoParallelRule,
    BufferInsertionRule,
    WindowOptimizationRule,
    evaluate_all_rules,
    OptimizationType,
)


# ---- Predicate Pushdown ----


class TestPredicatePushdown:
    def test_aggressive_filter_triggers_pushdown(self):
        """Filter with low selectivity before an expensive op -> pushdown."""
        analysis = AnalysisResult(
            pipeline_id="test",
            filter_stats={
                "f1": FilterStats(node_id="f1", total_seen=1000, total_passed=100),
            },
            pushdown_candidates=[("f1", "join1")],
        )
        rule = PredicatePushdownRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 1
        assert actions[0].optimization_type == OptimizationType.PREDICATE_PUSHDOWN
        assert actions[0].target_nodes == ["f1", "join1"]
        assert "f1" in actions[0].params["filter_node_id"]
        assert "join1" in actions[0].params["swap_with_node_id"]

    def test_high_selectivity_no_pushdown(self):
        """Filter that passes most events -> no pushdown."""
        analysis = AnalysisResult(
            pipeline_id="test",
            filter_stats={
                "f1": FilterStats(node_id="f1", total_seen=1000, total_passed=800),
            },
            pushdown_candidates=[],  # Analyzer wouldn't flag this
        )
        rule = PredicatePushdownRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 0

    def test_estimated_gain_calculation(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            filter_stats={
                "f1": FilterStats(node_id="f1", total_seen=1000, total_passed=50),
            },
            pushdown_candidates=[("f1", "agg1")],
        )
        rule = PredicatePushdownRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 1
        # selectivity = 0.05, so gain should be ~20x
        assert "20x" in actions[0].estimated_gain

    def test_multiple_pushdown_candidates(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            filter_stats={
                "f1": FilterStats(node_id="f1", total_seen=1000, total_passed=100),
                "f2": FilterStats(node_id="f2", total_seen=1000, total_passed=200),
            },
            pushdown_candidates=[("f1", "join1"), ("f2", "agg1")],
        )
        rule = PredicatePushdownRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 2


# ---- Operator Fusion ----


class TestOperatorFusion:
    def test_consecutive_maps_fused(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            fusion_candidates=[("map1", "map2")],
        )
        rule = OperatorFusionRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 1
        assert actions[0].optimization_type == OptimizationType.OPERATOR_FUSION
        assert actions[0].target_nodes == ["map1", "map2"]

    def test_no_fusion_candidates(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            fusion_candidates=[],
        )
        rule = OperatorFusionRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 0

    def test_fusion_priority(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            fusion_candidates=[("m1", "m2")],
        )
        rule = OperatorFusionRule()
        actions = rule.evaluate(analysis)
        assert actions[0].priority == 50  # Medium priority


# ---- Auto-Parallel ----


class TestAutoParallel:
    def test_high_cpu_triggers_parallel(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            operator_stats={
                "f1": OperatorStats(
                    node_id="f1", operator_type="filter",
                    avg_cpu_percent=85,
                ),
            },
            parallel_candidates=["f1"],
        )
        rule = AutoParallelRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 1
        assert actions[0].optimization_type == OptimizationType.AUTO_PARALLEL
        assert actions[0].params["target_parallelism"] == 3  # 80-90% -> 3x

    def test_very_high_cpu_scales_to_4(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            operator_stats={
                "f1": OperatorStats(
                    node_id="f1", operator_type="filter",
                    avg_cpu_percent=95,
                ),
            },
            parallel_candidates=["f1"],
        )
        rule = AutoParallelRule()
        actions = rule.evaluate(analysis)
        assert actions[0].params["target_parallelism"] == 4  # >90% -> 4x

    def test_no_bottleneck_no_action(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            parallel_candidates=[],
        )
        rule = AutoParallelRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 0


# ---- Buffer Insertion ----


class TestBufferInsertion:
    def test_backpressure_triggers_buffer(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            edge_stats={
                "src->flt": EdgeStats(
                    source_id="src", target_id="flt",
                    events_per_second=1000,
                    backpressure_detected=True,
                ),
            },
        )
        rule = BufferInsertionRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 1
        assert actions[0].optimization_type == OptimizationType.BUFFER_INSERTION
        assert actions[0].params["source_id"] == "src"
        assert actions[0].params["target_id"] == "flt"

    def test_no_backpressure_no_buffer(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            edge_stats={
                "src->flt": EdgeStats(
                    source_id="src", target_id="flt",
                    events_per_second=1000,
                    backpressure_detected=False,
                ),
            },
        )
        rule = BufferInsertionRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 0


# ---- Combined Rule Evaluation ----


# ---- Window Optimization ----


class TestWindowOptimization:
    def test_high_memory_and_latency_triggers(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            operator_stats={
                "w1": OperatorStats(
                    node_id="w1", operator_type="window",
                    avg_memory_percent=80, avg_latency_ms=250,
                ),
            },
        )
        rule = WindowOptimizationRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 1
        assert actions[0].optimization_type == OptimizationType.WINDOW_OPTIMIZATION
        assert actions[0].params["suggested_window_type"] == "tumbling"

    def test_high_latency_only_suggests_session(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            operator_stats={
                "w1": OperatorStats(
                    node_id="w1", operator_type="window",
                    avg_memory_percent=40, avg_latency_ms=400,
                ),
            },
        )
        rule = WindowOptimizationRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 1
        assert actions[0].params["suggested_window_type"] == "session"

    def test_healthy_window_no_action(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            operator_stats={
                "w1": OperatorStats(
                    node_id="w1", operator_type="window",
                    avg_memory_percent=40, avg_latency_ms=50,
                ),
            },
        )
        rule = WindowOptimizationRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 0

    def test_non_window_operator_ignored(self):
        analysis = AnalysisResult(
            pipeline_id="test",
            operator_stats={
                "f1": OperatorStats(
                    node_id="f1", operator_type="filter",
                    avg_memory_percent=90, avg_latency_ms=500,
                ),
            },
        )
        rule = WindowOptimizationRule()
        actions = rule.evaluate(analysis)
        assert len(actions) == 0


# ---- Combined Rule Evaluation ----


class TestEvaluateAllRules:
    def test_sorts_by_priority(self):
        """Higher priority actions should come first."""
        analysis = AnalysisResult(
            pipeline_id="test",
            filter_stats={
                "f1": FilterStats(node_id="f1", total_seen=1000, total_passed=100),
            },
            operator_stats={
                "m1": OperatorStats(
                    node_id="m1", operator_type="map",
                    avg_cpu_percent=85,
                ),
            },
            pushdown_candidates=[("f1", "join1")],
            fusion_candidates=[("m1", "m2")],
            parallel_candidates=["m1"],
        )
        actions = evaluate_all_rules(analysis)
        # Pushdown (90) > AutoParallel (80) > BufferInsertion (70) > Fusion (50)
        priorities = [a.priority for a in actions]
        assert priorities == sorted(priorities, reverse=True)

    def test_empty_analysis_no_actions(self):
        analysis = AnalysisResult(pipeline_id="test")
        actions = evaluate_all_rules(analysis)
        assert actions == []
