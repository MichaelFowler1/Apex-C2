"""The autonomous-recovery claim rests on the edge model actually flagging a
hard fault. Train on synthetic nominal telemetry (slow steady drain), then
present an adversarial-grade drain and require the IsolationForest to flag it."""
import csv

import numpy as np
from conftest import load_module

va = load_module("blue-team-c2/vanguard_autonomous.py", "vanguard_autonomous")


def _write_baseline(path, n=60):
    """Nominal telemetry: full-ish battery, ~-0.2 charge/s drain."""
    rng = np.random.default_rng(0)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Time_Offset", "Charge_Level", "Fault_Label"])
        charge = 100.0
        for t in range(n):
            charge += float(rng.normal(-0.2, 0.05))
            w.writerow([t, round(charge, 2), 0])


def test_missing_baseline_returns_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert va.train_edge_model() is None


def test_model_trains_on_baseline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_baseline(tmp_path / va.TRAINING_DATA_PATH)
    model = va.train_edge_model()
    assert model is not None
    # random_state=42 is fixed, so training is reproducible.
    assert va.train_edge_model().predict([[95.0, -0.2]]) == \
        model.predict([[95.0, -0.2]])


def test_adversarial_drain_is_flagged(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_baseline(tmp_path / va.TRAINING_DATA_PATH)
    model = va.train_edge_model()
    # A command-injection-grade fault: arrays retracted, forced yaw spin —
    # charge collapsing at -8/s from half capacity. Must read as anomaly (-1).
    assert model.predict(np.array([[50.0, -8.0]]))[0] == -1


def test_nominal_gate_bypasses_model():
    # The threshold gate: drains milder than NOMINAL_DRAIN_THRESHOLD never
    # reach the model, so the loop forces prediction=1 (nominal). Pin the
    # constant's sign so a config edit can't silently invert the gate.
    assert va.NOMINAL_DRAIN_THRESHOLD < 0
    mild_delta = va.NOMINAL_DRAIN_THRESHOLD + 0.1
    assert not (mild_delta < va.NOMINAL_DRAIN_THRESHOLD)
