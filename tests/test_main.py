"""Tests for QuantumHall-Lab: Landau levels, exact plateaus, toy
transport model, Hofstadter spectra, labelled fractional book,
classifier, HOLD gates, determinism."""
import subprocess
import sys
from fractions import Fraction

import pytest

import main as m


# ---- constants + Landau levels
def test_rk_from_constants():
    assert abs(m.von_klitzing_ohm() - m.R_K_LABELLED) / m.R_K_LABELLED < 1e-5


def test_landau_spacing_linear():
    assert m.cyclotron_energy_mev(10.0) == pytest.approx(
        2.0 * m.cyclotron_energy_mev(5.0), rel=1e-12)


def test_landau_ladder():
    s = m.cyclotron_energy_mev(10.0)
    assert m.landau_level_mev(0, 10.0) == pytest.approx(0.5 * s)
    assert m.landau_level_mev(3, 10.0) == pytest.approx(3.5 * s)


def test_gaas_spacing_sane():
    assert 17.0 < m.cyclotron_energy_mev(10.0) < 17.6


def test_degeneracy_scales_with_b():
    assert m.degeneracy_per_cm2(10.0) == pytest.approx(
        2.0 * m.degeneracy_per_cm2(5.0), rel=1e-12)
    assert m.degeneracy_per_cm2(10.0) == pytest.approx(2.418e11, rel=1e-3)


def test_filling_roundtrip():
    for nu in (1, 2, 3, 6):
        b = m.field_for_filling(m.DEMO_DENSITY_M2, nu)
        assert m.filling_factor(m.DEMO_DENSITY_M2, b) == pytest.approx(nu)


def test_magnetic_length():
    assert m.magnetic_length_nm(10.0) == pytest.approx(8.11, abs=0.05)
    assert m.magnetic_length_nm(4.0) > m.magnetic_length_nm(10.0)


def test_zeeman_below_cyclotron():
    assert m.zeeman_energy_mev(10.0) < m.cyclotron_energy_mev(10.0)


def test_fan_table():
    fan = m.landau_fan()
    assert len(fan) == 6
    assert fan[0]["nu_at_demo_density"] > fan[-1]["nu_at_demo_density"]


# ---- exact plateau arithmetic
def test_sigma_xy_exact():
    for n in range(1, 7):
        val = m.sigma_xy_exact_e2h(n)
        assert isinstance(val, Fraction)
        assert val == n


def test_hall_resistance_exact():
    assert m.hall_resistance_rk(1) == 1
    assert m.hall_resistance_rk(2) == Fraction(1, 2)
    assert m.hall_resistance_rk(3) == Fraction(1, 3)
    assert m.hall_resistance_rk(6) == Fraction(1, 6)


def test_hall_resistance_ohm():
    assert m.hall_resistance_ohm(2) == pytest.approx(
        m.R_K_LABELLED / 2.0, abs=0.01)


def test_plateau_table_ordering():
    table = m.plateau_table()
    assert len(table) == 6
    assert table[0]["B_centre_T"] > table[-1]["B_centre_T"]
    assert table[1]["R_xy_RK_exact"] == "1/2"


# ---- transport toy model
def test_sigma_xy_plateau_centres():
    for n in (1, 2, 3, 4):
        assert m.sigma_xy_curve(float(n)) == pytest.approx(n, abs=1e-3)


def test_sigma_xy_midpoints():
    for k in (1, 2, 3):
        assert m.sigma_xy_curve(k - 0.5) == pytest.approx(k - 0.5, abs=1e-9)


def test_sigma_xx_shape():
    assert m.sigma_xx_curve(2.0) < 1e-6
    assert m.sigma_xx_curve(2.5) == pytest.approx(m.XX_PEAK)
    assert m.sigma_xx_curve(2.5) > m.sigma_xx_curve(2.2) > m.sigma_xx_curve(2.0)


def test_sigma_xy_monotone():
    xs = [0.2 + 0.05 * i for i in range(100)]
    ys = [m.sigma_xy_curve(x) for x in xs]
    assert all(b >= a - 1e-12 for a, b in zip(ys, ys[1:]))


def test_plateau_width():
    w = m.plateau_width(2)
    assert 0.3 < w["width_nu"] < 1.0
    assert w["width_T"] > 0
    assert w["nu_lo"] < 2.0 < w["nu_hi"]


# ---- Jacobi + Hofstadter
def test_jacobi_known():
    vals = m.jacobi_eigenvalues([[2.0, 1.0], [1.0, 2.0]])
    assert vals == pytest.approx([1.0, 3.0], abs=1e-9)


def test_jacobi_diagonal():
    vals = m.jacobi_eigenvalues([[3.0, 0.0], [0.0, -1.0]])
    assert vals == pytest.approx([-1.0, 3.0], abs=1e-12)


def test_harper_band_count():
    assert len(m.harper_eigenvalues(1, 3, 0.0, 0.0)) == 3
    assert len(m.hofstadter_spectrum(1, 2)) == 2 * 16


def test_hofstadter_half_band_edge():
    spec = m.hofstadter_spectrum(1, 2)
    assert max(abs(e) for e in spec) == pytest.approx(
        2.0 * (2.0 ** 0.5), abs=0.05)


def test_hofstadter_trace_zero():
    assert sum(m.hofstadter_spectrum(1, 2)) == pytest.approx(0.0, abs=1e-6)


def test_hofstadter_symmetry():
    spec = m.hofstadter_spectrum(1, 3)
    for i in range(len(spec)):
        assert spec[i] == pytest.approx(-spec[-1 - i], abs=1e-6)


def test_hofstadter_mirror():
    a = m.hofstadter_spectrum(1, 3)
    b = m.hofstadter_spectrum(2, 3)
    assert a == pytest.approx(b, abs=1e-6)


def test_gap_labels():
    assert m.gap_label(1, 3, 1) == (0, 1)
    assert m.gap_label(1, 3, 2) == (1, -1)
    assert m.gap_label(1, 2, 1) == (0, 1)
    assert m.gap_label(1, 4, 3) == (1, -1)


def test_hofstadter_report():
    rep = m.hofstadter_report()
    assert rep["rationals"] == 17
    assert rep["total_eigenvalues"] > 500


# ---- fractional section (labelled)
def test_coulomb_scale():
    assert m.coulomb_scale_mev(10.0) == pytest.approx(13.76, abs=0.1)
    assert m.coulomb_scale_mev(12.0) > m.coulomb_scale_mev(6.0)


def test_fractional_report_labelled():
    rep = m.fractional_report()
    assert "LABELLED" in rep["state"]
    assert rep["gap_estimate_meV_labelled"][1] < rep[
        "coulomb_scale_meV_computed"]
    assert rep["B_for_nu_1_3_at_demo_density_T"] == pytest.approx(
        37.221, abs=0.01)


def test_pair_counting():
    sk = m.pair_counting_sketch(6)
    assert sk["pairs"] == 15
    assert sk["laughlin_min_pair_m"] == 3
    assert "no Hamiltonian" in sk["note"]


# ---- classifier
def test_classifier_probes():
    rep = m.classifier_report()
    assert rep["nu_3.00_B8_T0.3"] == "plateau"
    assert rep["nu_3.50_B8_T0.3"] == "transition"
    assert rep["nu_2.65_B8_T0.3"] == "insulating"
    assert rep["nu_3.02_B2_T40"] == "transition"


def test_classifier_matches_model():
    for nu, b, t in [(3.0, 8.0, 0.3), (2.65, 8.0, 0.3), (3.5, 8.0, 0.3)]:
        assert m.classify_regime(nu, b, t) == m.model_label(
            *m.regime_features(nu, b, t))


# ---- gates + seats
def test_hold_gates_14():
    assert len(m.HOLD_GATES) == 14
    assert all(v.startswith("HOLD") for v in m.HOLD_GATES.values())


def test_specific_gates():
    assert m.gate("metrology_standard_claim") == "HOLD"
    assert m.gate("fabricated_exact_diagonalization") == "HOLD"
    assert m.gate("measured_device_data_claim") == "HOLD"
    assert m.gate("run_simulation") == "PROCEED"


def test_seats_cannot_override():
    brains = m.brains_report()
    assert brains["decider"]["can_override_hold"] is False
    assert brains["decider"]["seat"] == "Gemini Argon 4 Extended Thinking"
    assert brains["advisor"]["can_override_hold"] is False
    assert brains["flow"]["rendered"] is False
    assert brains["flow"]["live"] == 0


def test_checks_all_pass():
    checks = m.run_checks()
    assert all(ok for _, ok in checks), [n for n, ok in checks if not ok]
    assert len(checks) >= 50


def test_hold_demo_exit_2():
    proc = subprocess.run([sys.executable, "main.py", "hold-demo"],
                          capture_output=True, text=True)
    assert proc.returncode == 2


def test_demo_deterministic():
    a = subprocess.run([sys.executable, "main.py", "demo"],
                       capture_output=True, text=True)
    b = subprocess.run([sys.executable, "main.py", "demo"],
                       capture_output=True, text=True)
    assert a.returncode == 0 and b.returncode == 0
    assert a.stdout == b.stdout
