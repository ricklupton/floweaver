"""Tests that the JS executor produces the same results as the Python executor."""

import json
import subprocess
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, strategies as st, settings, assume, note

from floweaver import (
    SankeyDefinition,
    ProcessGroup,
    Waypoint,
    Bundle,
    Partition,
    Dataset,
    Elsewhere,
)
from floweaver.weave import weave_compiled
from floweaver.compiler import compile_sankey_definition
from floweaver.compiler.execute import execute_weave

import hypothesis_strategies as fst
from helpers import assert_sankey_data_equivalent, sankey_data_from_json

JS_DIR = Path(__file__).resolve().parent.parent / "js"
RUN_SPEC = JS_DIR / "run_spec.js"


def _run_js(spec_json, flows_records):
    """Call the JS executor via node subprocess and return parsed result."""
    payload = json.dumps({"spec": spec_json, "flows": flows_records})
    result = subprocess.run(
        ["node", str(RUN_SPEC)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(JS_DIR),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"JS executor failed (rc={result.returncode}):\n{result.stderr}"
        )
    return json.loads(result.stdout)


def _flows_to_records(flows_df):
    """Convert a DataFrame to a list of dicts suitable for JSON serialization."""
    records = []
    for _, row in flows_df.iterrows():
        record = {}
        for col in flows_df.columns:
            val = row[col]
            # Convert numpy types to native Python for JSON
            if isinstance(val, (np.integer,)):
                val = int(val)
            elif isinstance(val, (np.floating,)):
                val = float(val)
            record[col] = val
        records.append(record)
    return records


def _create_explicit_palette(sdd, dataset):
    """Create an explicit color palette dict (same as in the equivalence tests)."""
    from palettable.colorbrewer.qualitative import Pastel1_8  # ty:ignore[unresolved-import]

    if hasattr(dataset, "_table"):
        flows_df = dataset._table
    else:
        flows_df = dataset

    if sdd.flow_partition is not None:
        partition_dim = None
        for group in sdd.flow_partition.groups:
            if group.query:
                partition_dim = group.query[0][0]
                break
        if partition_dim and partition_dim in flows_df.columns:
            type_values = sorted(flows_df[partition_dim].unique())
        else:
            type_values = (
                sorted(flows_df["type"].unique()) if "type" in flows_df.columns else []
            )
    else:
        type_values = (
            sorted(flows_df["type"].unique()) if "type" in flows_df.columns else []
        )

    type_values = list(type_values)
    for extra in ["_", "*"]:
        if extra not in type_values:
            type_values.append(extra)

    colors = Pastel1_8.hex_colors
    palette = {}
    for i, value in enumerate(type_values):
        palette[value] = colors[i % len(colors)]

    return palette


def _compare_results(py_result, js_result):
    """Compare Python SankeyData with JS result dict.

    Parses JS result into SankeyData and uses shared comparison logic.
    Uses slightly looser tolerance (rtol=1e-10) for cross-language comparison.
    """
    js_sankey_data = sankey_data_from_json(js_result)
    assert_sankey_data_equivalent(js_sankey_data, py_result, rtol=1e-10)


# =============================================================================
# Explicit hand-crafted tests
# =============================================================================


class TestExplicitSpecs:
    """Simple hand-crafted specs to verify basic equivalence."""

    def test_simple_two_nodes(self):
        """Two process groups with one bundle between them."""
        sdd = SankeyDefinition(
            nodes={
                "inputs": ProcessGroup(["a"]),
                "outputs": ProcessGroup(["b"]),
            },
            bundles=[Bundle("inputs", "outputs")],
            ordering=[["inputs"], ["outputs"]],
        )
        flows = pd.DataFrame.from_records(
            [("a", "b", "m", 5.0), ("a", "b", "m", 3.0)],
            columns=["source", "target", "material", "value"],
        )
        dataset = Dataset(flows)
        palette = {"*": "#aabbcc", "_": "#dddddd"}

        py_result = weave_compiled(sdd, dataset, palette=palette)
        spec = compile_sankey_definition(sdd, palette=palette)
        spec_json = spec.to_json()
        records = _flows_to_records(dataset._table)
        js_result = _run_js(spec_json, records)

        _compare_results(py_result, js_result)

    def test_with_partition(self):
        """Two nodes with a material partition."""
        sdd = SankeyDefinition(
            nodes={
                "inputs": ProcessGroup(["a"]),
                "outputs": ProcessGroup(["b"]),
            },
            bundles=[Bundle("inputs", "outputs")],
            ordering=[["inputs"], ["outputs"]],
            flow_partition=Partition.Simple("material", ["m", "n"]),
        )
        flows = pd.DataFrame.from_records(
            [
                ("a", "b", "m", 5.0),
                ("a", "b", "n", 3.0),
                ("a", "b", "m", 2.0),
            ],
            columns=["source", "target", "material", "value"],
        )
        dataset = Dataset(flows)
        palette = {"m": "#ff0000", "n": "#0000ff", "_": "#999999", "*": "#cccccc"}

        py_result = weave_compiled(sdd, dataset, palette=palette)
        spec = compile_sankey_definition(sdd, palette=palette)
        spec_json = spec.to_json()
        records = _flows_to_records(dataset._table)
        js_result = _run_js(spec_json, records)

        _compare_results(py_result, js_result)

    def test_with_waypoint(self):
        """Three nodes with a waypoint in the middle."""
        sdd = SankeyDefinition(
            nodes={
                "inputs": ProcessGroup(["a"]),
                "mid": Waypoint(),
                "outputs": ProcessGroup(["b"]),
            },
            bundles=[Bundle("inputs", "outputs", waypoints=("mid",))],
            ordering=[["inputs"], ["mid"], ["outputs"]],
        )
        flows = pd.DataFrame.from_records(
            [("a", "b", "m", 10.0)],
            columns=["source", "target", "material", "value"],
        )
        dataset = Dataset(flows)
        palette = {"*": "#aabbcc", "_": "#dddddd"}

        py_result = weave_compiled(sdd, dataset, palette=palette)
        spec = compile_sankey_definition(sdd, palette=palette)
        spec_json = spec.to_json()
        records = _flows_to_records(dataset._table)
        js_result = _run_js(spec_json, records)

        _compare_results(py_result, js_result)

    def test_elsewhere_bundle(self):
        """Bundle from Elsewhere."""
        sdd = SankeyDefinition(
            nodes={
                "inputs": ProcessGroup(["a"]),
                "outputs": ProcessGroup(["b"]),
            },
            bundles=[
                Bundle("inputs", "outputs"),
                Bundle(Elsewhere, "outputs"),
            ],
            ordering=[["inputs"], ["outputs"]],
        )
        flows = pd.DataFrame.from_records(
            [
                ("a", "b", "m", 5.0),
                ("x", "b", "m", 3.0),
            ],
            columns=["source", "target", "material", "value"],
        )
        dataset = Dataset(flows)
        palette = {"*": "#aabbcc", "_": "#dddddd"}

        py_result = weave_compiled(sdd, dataset, palette=palette)
        spec = compile_sankey_definition(sdd, palette=palette)
        spec_json = spec.to_json()
        records = _flows_to_records(dataset._table)
        js_result = _run_js(spec_json, records)

        _compare_results(py_result, js_result)


# =============================================================================
# Property-based tests: full SankeyDefinition → Dataset → SankeyData pipeline
# =============================================================================


@settings(print_blob=True, deadline=10000, max_examples=50)
@given(fst.sankey_definitions(), st.data())
def test_python_vs_js_equivalence(sdd, data):
    """Verify that compile in Python + execute in JS gives the same result
    as compile + execute entirely in Python.
    """
    dataset = data.draw(fst.datasets(sdd))

    palette = _create_explicit_palette(sdd, dataset)

    # Python: compile + execute
    py_result = weave_compiled(sdd, dataset, palette=palette)

    # Python compile → JS execute
    spec = compile_sankey_definition(sdd, palette=palette)
    spec_json = spec.to_json()
    records = _flows_to_records(dataset._table)

    js_result = _run_js(spec_json, records)

    _compare_results(py_result, js_result)
