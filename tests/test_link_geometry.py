"""The LOS/AOS gatekeeper's authority comes from get_link_metrics: if the
geometry is wrong, the 5-degree elevation mask gates on garbage. These tests
check it against closed-form cases where the answer is known exactly."""
import math

from conftest import load_module

pp = load_module("physical-range/physical pipeline.py", "physical_pipeline")

# Kerbin-like body: the exact radius doesn't matter, only the geometry.
R = 600_000.0


def test_zenith_pass_is_90_degrees():
    # Satellite directly over the station: elevation 90 deg, slant range is
    # exactly the altitude, latency = altitude / c.
    alt = 985_000.0
    elevation, slant, latency = pp.get_link_metrics(
        R, alt, pp.STATION_LAT, pp.STATION_LON)
    assert abs(elevation - 90.0) < 0.1
    assert abs(slant - alt) < 1.0
    assert abs(latency - alt / pp.C) < 1e-9


def test_horizon_geometry_is_zero_elevation():
    # Elevation crosses zero when the station-satellite angle reaches
    # psi = acos(R / (R + alt)): the satellite sits exactly on the horizon.
    alt = 985_000.0
    psi = math.degrees(math.acos(R / (R + alt)))
    elevation, _, _ = pp.get_link_metrics(
        R, alt, pp.STATION_LAT, pp.STATION_LON + psi)
    assert abs(elevation) < 0.05


def test_far_side_is_masked():
    # A satellite over the far side of the body must report negative
    # elevation — LOS BLOCKED under any mask.
    elevation, _, _ = pp.get_link_metrics(
        R, 985_000.0, pp.STATION_LAT, pp.STATION_LON + 180.0)
    assert elevation < 0
    assert elevation < pp.ELEVATION_MASK_DEG


def test_elevation_decreases_as_satellite_moves_away():
    alt = 985_000.0
    seps = [0.0, 5.0, 15.0, 30.0, 60.0]
    elevations = [
        pp.get_link_metrics(R, alt, pp.STATION_LAT, pp.STATION_LON + s)[0]
        for s in seps
    ]
    assert elevations == sorted(elevations, reverse=True)


def test_slant_range_never_below_altitude():
    alt = 985_000.0
    for sep in (0.0, 10.0, 45.0, 90.0):
        _, slant, _ = pp.get_link_metrics(
            R, alt, pp.STATION_LAT, pp.STATION_LON + sep)
        assert slant >= alt - 1.0
