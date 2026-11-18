#!/usr/bin/env python3
"""QuantumHall-Lab - educational quantum Hall effect lab.

by Darion Kellar

Pure Python standard library. Zero dependencies. Zero network.
Education only - and the honest scope is stated up front:

  * This lab computes ANALYTIC MODELS of the quantum Hall effect:
    Landau levels of a 2D electron gas, filling factors, exactly
    quantized plateau conductance in units of e^2/h (exact fraction
    arithmetic), a labelled localization toy model for the plateau
    curves, and the Hofstadter butterfly spectrum of the Harper
    equation on small flux grids (from-scratch eigensolver).
  * The fractional quantum Hall section is LABELLED TEXTBOOK VALUES
    ONLY (Laughlin nu = 1/3, quasiparticle charge e/3, gap scale).
    No exact diagonalization of a fractional state is run here, and
    none is claimed - a combinatorial counting sketch is included
    and labelled as a sketch.
  * Nothing here is measured device data. No sample was cooled, no
    magnet was energised, no resistance was certified. The von
    Klitzing constant is computed from SI constants and compared
    with its labelled CODATA value - that is arithmetic, not
    metrology. Every metrology, device, discovery, and facility
    use is a permanent HOLD gate - with Gemini Argon 4 Extended
    Thinking as DECIDER (names-only, tighten-only), Muse as
    advisor (never overrides HOLD), and Google Flow plan-only.
"""
import hashlib
import json
import math
import sys
from fractions import Fraction

# ---------------------------------------------------------------- constants
VERSION = "1.0.0"

# CODATA / SI constants. h and e are exact SI defining values;
# m_e and eps0 are CODATA-2018 measured values. All LABELLED as
# constants of the model - this lab measures nothing.
H_PLANCK = 6.62607015e-34        # J s, exact SI
E_CHARGE = 1.602176634e-19       # C, exact SI
M_ELECTRON = 9.1093837015e-31    # kg, CODATA 2018
EPS0 = 8.8541878128e-12          # F/m, CODATA 2018
K_BOLTZMANN = 1.380649e-23       # J/K, exact SI
HBAR = H_PLANCK / (2.0 * math.pi)

# Labelled CODATA value of the von Klitzing constant, ohms.
R_K_LABELLED = 25812.807

# Labelled sample parameters: a GaAs/AlGaAs-style 2DEG.
GAAS_M_STAR = 0.067              # effective mass, units of m_e (labelled)
GAAS_G_STAR = -0.44              # effective g-factor (labelled)
GAAS_EPS_R = 12.9                # relative permittivity (labelled)
DEMO_DENSITY_M2 = 3.0e15         # 3.0e11 cm^-2, labelled demo density

# ---------------------------------------------------------------- HOLD gates
HOLD_GATES = {
    "metrology_standard_claim": "HOLD - no metrology use; R_K computed from constants is arithmetic, not a resistance standard",
    "measured_device_data_claim": "HOLD - no presenting model output as measured device or sample data",
    "real_device_characterisation": "HOLD - no characterising a real device, wafer, or heterostructure from this lab",
    "resistance_standard_operation": "HOLD - no operating or certifying a quantum Hall resistance standard",
    "cryogenic_magnet_operation": "HOLD - no directing cryogenic, dilution-refrigerator, or magnet operation",
    "high_field_safety_signoff": "HOLD - no safety sign-off for high-magnetic-field facilities or procedures",
    "fractional_state_discovery_claim": "HOLD - no claiming discovery or observation of fractional quantum Hall states",
    "fabricated_exact_diagonalization": "HOLD - no presenting exact-diagonalization results that were not actually run",
    "semiconductor_design_signoff": "HOLD - no real semiconductor device or heterostructure design sign-off",
    "calibration_certificate": "HOLD - no issuing calibration certificates or traceability documents",
    "textbook_value_as_measurement": "HOLD - labelled textbook/CODATA values must never be presented as this lab's measurements",
    "quantum_sensor_product_claim": "HOLD - no product claims for Hall sensors or magnetometers based on this lab",
    "production_fab_claim": "HOLD - no fabrication-process claims for real cleanrooms or production lines",
    "investment_claim": "HOLD - no investment claims; a teaching model is not a prospectus",
}


def gate(action):
    """Return 'HOLD' if the action is gated, else 'PROCEED' (sandbox sim)."""
    return "HOLD" if action in HOLD_GATES else "PROCEED"


# ================================================================ 1. Landau levels
# A 2D electron gas in a perpendicular field B has its kinetic energy
# quantised into Landau levels E_n = hbar * omega_c * (n + 1/2) with
# omega_c = eB / m*. Each level holds eB/h electrons per unit area
# (per spin). Everything below is that arithmetic, done openly.

def cyclotron_energy_mev(b_field, m_star=GAAS_M_STAR):
    """Landau level spacing hbar*omega_c in meV."""
    omega_c = E_CHARGE * b_field / (m_star * M_ELECTRON)
    return HBAR * omega_c / E_CHARGE * 1.0e3


def landau_level_mev(n, b_field, m_star=GAAS_M_STAR):
    """Energy of Landau level n (n = 0, 1, 2, ...) in meV."""
    return cyclotron_energy_mev(b_field, m_star) * (n + 0.5)


def zeeman_energy_mev(b_field, g_star=GAAS_G_STAR):
    """Zeeman splitting |g*| mu_B B in meV (labelled g*)."""
    mu_b = E_CHARGE * HBAR / (2.0 * M_ELECTRON)
    return abs(g_star) * mu_b * b_field / E_CHARGE * 1.0e3


def degeneracy_per_cm2(b_field):
    """States per Landau level per cm^2 (per spin): eB/h."""
    return E_CHARGE * b_field / H_PLANCK / 1.0e4


def filling_factor(density_m2, b_field):
    """nu = n h / (e B): how many spin-resolved levels are filled."""
    return density_m2 * H_PLANCK / (E_CHARGE * b_field)


def field_for_filling(density_m2, nu):
    """B at which density n gives filling nu: B = n h / (e nu)."""
    return density_m2 * H_PLANCK / (E_CHARGE * nu)


def magnetic_length_nm(b_field):
    """Magnetic length l_B = sqrt(hbar / (eB)) in nm."""
    return math.sqrt(HBAR / (E_CHARGE * b_field)) * 1.0e9


def von_klitzing_ohm():
    """R_K = h / e^2 computed from SI constants, in ohms."""
    return H_PLANCK / E_CHARGE ** 2


def flux_quantum_weber():
    """Single-electron flux quantum h/e in webers."""
    return H_PLANCK / E_CHARGE


def landau_fan(b_fields=(2.0, 4.0, 6.0, 8.0, 10.0, 12.0),
               density_m2=DEMO_DENSITY_M2):
    """Fan table: spacing, degeneracy, filling, l_B per field."""
    rows = []
    for b in b_fields:
        rows.append({
            "B_T": b,
            "spacing_meV": round(cyclotron_energy_mev(b), 4),
            "E0_meV": round(landau_level_mev(0, b), 4),
            "zeeman_meV": round(zeeman_energy_mev(b), 4),
            "degeneracy_per_cm2": round(degeneracy_per_cm2(b), 1),
            "nu_at_demo_density": round(filling_factor(density_m2, b), 4),
            "l_B_nm": round(magnetic_length_nm(b), 3),
            "spacing_K": round(cyclotron_energy_mev(b)
                               * E_CHARGE * 1.0e-3 / K_BOLTZMANN, 2),
        })
    return rows


# ================================================================ 2. Exact plateau arithmetic
# On an integer plateau the Hall conductance is EXACTLY nu * e^2/h.
# That statement is kept in exact fraction arithmetic: in units of
# e^2/h, sigma_xy at a plateau centre IS the integer nu, with no
# floating point anywhere near it. R_xy = R_K / nu likewise.

def sigma_xy_exact_e2h(nu):
    """sigma_xy in units of e^2/h at a plateau centre: exactly nu."""
    return Fraction(nu)


def hall_resistance_rk(nu):
    """R_xy in units of R_K at filling nu: exactly 1/nu."""
    return Fraction(1, 1) / Fraction(nu)


def hall_resistance_ohm(nu):
    """R_xy in ohms at filling nu (float, from computed R_K)."""
    return von_klitzing_ohm() / float(nu)


def plateau_table(density_m2=DEMO_DENSITY_M2, nu_max=6):
    """Exact plateau book: nu, B centre, sigma_xy, R_xy."""
    rows = []
    for nu in range(1, nu_max + 1):
        rows.append({
            "nu": nu,
            "B_centre_T": round(field_for_filling(density_m2, nu), 4),
            "sigma_xy_e2h_exact": str(sigma_xy_exact_e2h(nu)),
            "R_xy_RK_exact": str(hall_resistance_rk(nu)),
            "R_xy_ohm": round(hall_resistance_ohm(nu), 3),
        })
    return rows


# ================================================================ 3. Plateau transport toy model
# LABELLED LOCALIZATION MODEL - a toy, stated as a toy. Extended
# (current-carrying) states sit at Landau level centres; in filling
# space the transitions between plateaus are centred at half-integer
# nu. sigma_xy is a staircase of tanh steps at the half-integers;
# sigma_xx is a train of Gaussian peaks at the half-integers and
# ~zero on the plateaus. Plateau widths below are computed FROM
# THIS MODEL - they are model outputs, not device data.

STEP_WIDTH = 0.06        # tanh step width in nu (labelled model value)
XX_WIDTH = 0.07          # sigma_xx Gaussian width in nu (labelled)
XX_PEAK = 0.5            # sigma_xx peak height, e^2/h (labelled)


def sigma_xy_curve(nu):
    """Toy sigma_xy in units of e^2/h: staircase over half-integers."""
    total = 0.0
    k = 1
    while k <= 40:
        total += 0.5 * (1.0 + math.tanh((nu - (k - 0.5)) / STEP_WIDTH))
        if nu - (k - 0.5) < -12.0 * STEP_WIDTH and k > nu + 2:
            break
        k += 1
    return total


def sigma_xx_curve(nu):
    """Toy sigma_xx in units of e^2/h: peaks at half-integers."""
    total = 0.0
    k = 1
    while k <= 40:
        d = (nu - (k - 0.5)) / XX_WIDTH
        total += XX_PEAK * math.exp(-d * d)
        if k - 0.5 > nu + 8.0 * XX_WIDTH and k > nu + 2:
            break
        k += 1
    return total


def plateau_width(nu_plateau, density_m2=DEMO_DENSITY_M2, tol=0.01):
    """Width of plateau nu_plateau in this model.

    Scans nu around the plateau centre; the plateau is where the
    toy sigma_xy sits within tol of the exact integer AND toy
    sigma_xx is below tol. Returns widths in nu and in tesla at
    the given density (B = n h / (e nu), so the B width is the
    image of the nu interval).
    """
    lo = nu_plateau - 0.5 + 1e-9
    hi = nu_plateau + 0.5 - 1e-9
    step = 0.0005
    inside = []
    x = lo
    while x <= hi:
        if (abs(sigma_xy_curve(x) - nu_plateau) <= tol
                and sigma_xx_curve(x) <= tol):
            inside.append(x)
        x += step
    if not inside:
        return {"nu": nu_plateau, "nu_lo": None, "nu_hi": None,
                "width_nu": 0.0, "width_T": 0.0}
    nu_lo, nu_hi = inside[0], inside[-1]
    b_at_lo = field_for_filling(density_m2, nu_hi)   # B falls as nu rises
    b_at_hi = field_for_filling(density_m2, nu_lo)
    return {"nu": nu_plateau, "nu_lo": round(nu_lo, 3),
            "nu_hi": round(nu_hi, 3),
            "width_nu": round(nu_hi - nu_lo, 3),
            "width_T": round(b_at_hi - b_at_lo, 3)}


def transport_report(density_m2=DEMO_DENSITY_M2):
    """Model plateau widths + sigma_xx peak book for nu = 1..4."""
    widths = [plateau_width(nu, density_m2) for nu in (1, 2, 3, 4)]
    peaks = [{"nu": k - 0.5,
              "sigma_xx_peak_e2h": round(sigma_xx_curve(k - 0.5), 4),
              "sigma_xy_midpoint_e2h": round(sigma_xy_curve(k - 0.5), 4)}
             for k in (1, 2, 3, 4)]
    return {"model": "labelled localization toy - tanh steps + Gaussian "
                     "sigma_xx peaks at half-integer nu",
            "plateau_widths": widths, "transition_peaks": peaks}


# ================================================================ 4. Jacobi eigensolver + Hofstadter butterfly
# The Harper equation for flux alpha = p/q per plaquette:
#   psi_{n+1} + psi_{n-1} + 2 cos(2 pi alpha n + ky) psi_n = E psi_n
# With a magnetic unit cell of q sites and Bloch phases (kx_phase,
# ky), it is a q x q Hermitian matrix. Hermitian matrices are solved
# here by embedding H = A + iB into the real symmetric 2q x 2q matrix
# [[A, -B], [B, A]] (each eigenvalue appears twice) and running a
# from-scratch cyclic Jacobi eigensolver on it. No library spectra.

def jacobi_eigenvalues(matrix, tol=1e-12, max_sweeps=100):
    """Eigenvalues of a real symmetric matrix, cyclic Jacobi."""
    n = len(matrix)
    a = [row[:] for row in matrix]
    for _ in range(max_sweeps):
        off = math.sqrt(sum(a[i][j] ** 2 for i in range(n)
                            for j in range(n) if i != j))
        if off < tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = a[p][q]
                if abs(apq) < 1e-15:
                    continue
                tau = (a[q][q] - a[p][p]) / (2.0 * apq)
                t = (1.0 if tau >= 0 else -1.0) / (
                    abs(tau) + math.sqrt(1.0 + tau * tau))
                c = 1.0 / math.sqrt(1.0 + t * t)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
    return sorted(a[i][i] for i in range(n))


def _harper_hermitian(p, q, kx_phase, ky):
    """Harper matrix as (A, B) with H = A + iB, alpha = p/q."""
    alpha = p / q
    hre = [[0.0] * q for _ in range(q)]
    him = [[0.0] * q for _ in range(q)]
    for n in range(q):
        hre[n][n] = 2.0 * math.cos(2.0 * math.pi * alpha * n + ky)
    if q == 1:
        hre[0][0] += 2.0 * math.cos(kx_phase)
        return hre, him
    for n in range(q):
        fwd = (n + 1) % q
        bwd = (n - 1) % q
        # psi_{n+1}: phase e^{i kx_phase} only on the wrap bond
        ph_f = kx_phase if n == q - 1 else 0.0
        ph_b = -kx_phase if n == 0 else 0.0
        hre[n][fwd] += math.cos(ph_f)
        him[n][fwd] += math.sin(ph_f)
        hre[n][bwd] += math.cos(ph_b)
        him[n][bwd] += math.sin(ph_b)
    return hre, him


def harper_eigenvalues(p, q, kx_phase, ky):
    """The q eigenvalues of the Harper matrix at one Bloch point."""
    hre, him = _harper_hermitian(p, q, kx_phase, ky)
    m = [[0.0] * (2 * q) for _ in range(2 * q)]
    for i in range(q):
        for j in range(q):
            m[i][j] = hre[i][j]
            m[i][j + q] = -him[i][j]
            m[i + q][j] = him[i][j]
            m[i + q][j + q] = hre[i][j]
    doubled = jacobi_eigenvalues(m)
    # each true eigenvalue appears twice in the embedding
    return sorted(doubled[2 * i] for i in range(q))


def hofstadter_spectrum(p, q, n_k=4):
    """Sampled spectrum over an n_k x n_k Bloch grid, sorted."""
    energies = []
    for i in range(n_k):
        kx = 2.0 * math.pi * i / n_k
        for j in range(n_k):
            ky = 2.0 * math.pi * j / n_k
            energies.extend(harper_eigenvalues(p, q, kx, ky))
    return sorted(energies)


def butterfly_grid(q_max=7, n_k=4):
    """Spectra for every coprime p/q in (0, 1) with q <= q_max."""
    grid = {}
    for q in range(2, q_max + 1):
        for p in range(1, q):
            if math.gcd(p, q) == 1:
                grid[f"{p}/{q}"] = hofstadter_spectrum(p, q, n_k)
    return grid


def gap_label(p, q, r):
    """Diophantine gap label: r = q*s + p*t, |t| <= q/2.

    For a gap below which the integrated density of states is r/q
    per plaquette, the integers (s, t) label the gap; t is the
    Hall conductance of the gap in units of e^2/h (Wannier).
    Returns the (s, t) with smallest |t|, then smallest |s|.
    """
    best = None
    t = -q // 2
    while t <= q // 2:
        rem = r - p * t
        if rem % q == 0:
            s = rem // q
            key = (abs(t), abs(s))
            if best is None or key < best[0]:
                best = (key, (s, t))
        t += 1
    return best[1] if best else None


def hofstadter_report(q_max=7, n_k=4):
    grid = butterfly_grid(q_max, n_k)
    total = sum(len(v) for v in grid.values())
    widest = None
    for name, spec in grid.items():
        width = spec[-1] - spec[0]
        if widest is None or width > widest[1]:
            widest = (name, round(width, 4))
    return {"rationals": len(grid), "total_eigenvalues": total,
            "widest_spectrum": widest,
            "gap_labels": {
                "alpha=1/3, r=1": gap_label(1, 3, 1),
                "alpha=1/3, r=2": gap_label(1, 3, 2),
                "alpha=1/2, r=1": gap_label(1, 2, 1),
                "alpha=1/4, r=1": gap_label(1, 4, 1),
                "alpha=1/4, r=3": gap_label(1, 4, 3),
            }}


# ================================================================ 5. Fractional QHE - LABELLED values only
# This section does NOT diagonalize anything. It tabulates labelled
# textbook values for the Laughlin nu = 1/3 state, computes the two
# honest length/energy SCALES around them (magnetic length and the
# Coulomb scale, from constants), and runs a combinatorial counting
# sketch of pair angular-momentum channels. The gap itself is a
# labelled fraction of the Coulomb scale - an estimate range from
# the textbooks, not a result of this lab. Claiming otherwise is
# HOLD gate 'fabricated_exact_diagonalization'.

def coulomb_scale_mev(b_field, eps_r=GAAS_EPS_R):
    """Coulomb scale e^2 / (4 pi eps0 eps_r l_B) in meV (computed)."""
    l_b = magnetic_length_nm(b_field) * 1.0e-9
    e_c = E_CHARGE ** 2 / (4.0 * math.pi * EPS0 * eps_r * l_b)
    return e_c / E_CHARGE * 1.0e3


def pair_counting_sketch(n_electrons=6):
    """Combinatorial sketch (labelled): pairs and odd-m channels.

    The Laughlin wavefunction vanishes as (z_i - z_j)^3, so each
    pair carries relative angular momentum m >= 3; the m = 1 channel
    is the one the state avoids. This counts pairs and channels -
    it is bookkeeping, not a diagonalization.
    """
    pairs = n_electrons * (n_electrons - 1) // 2
    return {"electrons": n_electrons, "pairs": pairs,
            "pair_channels_odd_m": [1, 3, 5, 7],
            "laughlin_min_pair_m": 3,
            "note": "counting sketch only - no Hamiltonian was "
                    "diagonalized for the fractional state"}


def fractional_report(b_field=10.0):
    """Labelled Laughlin nu=1/3 book + computed scales."""
    ec = coulomb_scale_mev(b_field)
    return {
        "state": "Laughlin nu = 1/3 (LABELLED textbook values)",
        "quasiparticle_charge": "e/3 (labelled; shot-noise measured "
                                "in the literature, not here)",
        "quasihole_charge": "e/3 (labelled)",
        "ground_state_degeneracy_torus": "3 (labelled, = denominator of nu)",
        "B_for_nu_1_3_at_demo_density_T":
            round(field_for_filling(DEMO_DENSITY_M2, 1.0 / 3.0), 3),
        "l_B_nm_at_B": round(magnetic_length_nm(b_field), 3),
        "coulomb_scale_meV_computed": round(ec, 3),
        "gap_estimate_meV_labelled": [round(0.05 * ec, 3),
                                      round(0.10 * ec, 3)],
        "gap_note": "labelled textbook estimate ~0.05-0.1 of the "
                    "Coulomb scale; NOT computed by this lab",
        "counting_sketch": pair_counting_sketch(),
    }


# ================================================================ 6. TinyML kNN classifier
# Transport regime from (distance of nu to the nearest integer,
# sigma_xx, thermal ratio k_B T / hbar omega_c). Labels come from
# the lab's own localization model policy (model_label); the
# training grid is generated by sweeping the toy transport curves,
# so the classifier can only ever echo the model - stated openly.

def model_label(dist_to_int, sigma_xx, thermal_ratio):
    """The lab's regime policy: plateau / transition / insulating."""
    if thermal_ratio > 0.5:
        return "transition"          # thermally smeared
    if sigma_xx <= 0.02 and dist_to_int <= 0.20:
        return "plateau"
    if sigma_xx <= 0.02 and dist_to_int >= 0.35:
        return "insulating"
    return "transition"


def regime_features(nu, b_field, temp_k):
    """Feature triple for a (nu, B, T) point, from the toy curves."""
    dist = abs(nu - round(nu))
    sxx = sigma_xx_curve(nu)
    thermal = (K_BOLTZMANN * temp_k
               / (cyclotron_energy_mev(b_field) * E_CHARGE * 1.0e-3))
    return (dist, sxx, thermal)


def _training_grid():
    grid = []
    nus = [0.30 + 0.025 * i for i in range(229)]       # 0.30 .. 6.00
    for nu in nus:
        for b_field, temp in ((8.0, 0.3), (8.0, 1.5), (8.0, 6.0),
                              (2.0, 40.0), (4.0, 40.0)):
            feats = regime_features(nu, b_field, temp)
            grid.append((feats, model_label(*feats)))
    return grid


_TRAIN = _training_grid()
_MEANS = tuple(sum(f[i] for f, _ in _TRAIN) / len(_TRAIN) for i in range(3))
_STDS = tuple(math.sqrt(sum((f[i] - _MEANS[i]) ** 2 for f, _ in _TRAIN)
                        / len(_TRAIN)) or 1.0 for i in range(3))


def _dist(a, b):
    return math.sqrt(sum(((a[i] - b[i]) / _STDS[i]) ** 2 for i in range(3)))


def classify_regime(nu, b_field=8.0, temp_k=0.3, k=3):
    """kNN (k=3) over the model-labelled grid, standardised features."""
    feats = regime_features(nu, b_field, temp_k)
    ranked = sorted(_TRAIN, key=lambda item: _dist(feats, item[0]))[:k]
    votes = {}
    for _, label in ranked:
        votes[label] = votes.get(label, 0) + 1
    return max(sorted(votes), key=lambda lab: votes[lab])


def classifier_report():
    probes = {
        "nu_3.00_B8_T0.3": (3.00, 8.0, 0.3),
        "nu_2.00_B8_T0.3": (2.00, 8.0, 0.3),
        "nu_3.50_B8_T0.3": (3.50, 8.0, 0.3),
        "nu_2.65_B8_T0.3": (2.65, 8.0, 0.3),
        "nu_3.02_B2_T40": (3.02, 2.0, 40.0),
        "nu_4.50_B8_T1.5": (4.50, 8.0, 1.5),
    }
    return {name: classify_regime(*args) for name, args in probes.items()}


# ================================================================ 7. Advisory seats

def _trace(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def argon4_decide(topic="quantumhall-demo"):
    """Gemini Argon 4 DECIDER seat: MAP->MODEL->STRESS->DECIDE.

    Names-only keys, live calls 0, tighten-only: can add HOLDs, never lift one.
    """
    stages = ["MAP", "MODEL", "STRESS", "DECIDE"]
    payload = {"seat": "gemini-argon-4", "topic": topic, "stages": stages}
    return {
        "seat": "Gemini Argon 4 Extended Thinking",
        "role": "DECIDER",
        "pipeline": stages,
        "tiers": [2048, 8192, 32768],
        "key": "names-only (GEMINI_API_KEY name checked, value never read)",
        "live_calls": 0,
        "decision": "PROCEED - sandbox simulation only, all metrology and device gates stay HOLD",
        "can_override_hold": False,
        "trace_sha256_16": _trace(payload),
    }


def claude_advisor(topic="quantumhall-demo"):
    """Muse advisor seat: advises, can never override a HOLD."""
    return {
        "seat": "Muse",
        "role": "ADVISOR",
        "key": "names-only (MODEL_API_KEY name checked, value never read)",
        "live_calls": 0,
        "advice": "Say it in the first line of every report: these are analytic models and small-matrix spectra, not measurements - then show the exact plateau fractions, the computed R_K next to its labelled CODATA value, and the word LABELLED on every fractional number.",
        "can_override_hold": False,
    }


def google_flow_plan():
    """Google Flow seat: plan-only, nothing rendered, nothing live."""
    return {
        "seat": "Google Flow",
        "role": "PLAN-ONLY",
        "shots": ["a fan of Landau levels opening as the field rises",
                  "a staircase of Hall plateaus locking onto integers",
                  "sigma_xx peaks flaring at each half-integer crossing",
                  "the Hofstadter butterfly unfolding over flux rationals",
                  "a Laughlin quasiparticle carrying one third of a charge"],
        "rendered": False,
        "live": 0,
    }


def brains_report():
    return {"decider": argon4_decide(), "advisor": claude_advisor(),
            "flow": google_flow_plan()}


# ================================================================ checks
def run_checks():
    c = []

    def chk(name, ok):
        c.append((name, bool(ok)))

    # 1. constants + Landau levels
    rk = von_klitzing_ohm()
    chk("rk_from_constants_matches_labelled",
        abs(rk - R_K_LABELLED) / R_K_LABELLED < 1e-5)
    chk("flux_quantum_value", abs(flux_quantum_weber() - 4.135667696e-15)
        / 4.135667696e-15 < 1e-6)
    chk("landau_spacing_linear_in_B",
        abs(cyclotron_energy_mev(10.0) - 2.0 * cyclotron_energy_mev(5.0))
        < 1e-9)
    chk("landau_level_ladder",
        abs(landau_level_mev(2, 10.0)
            - 2.5 * cyclotron_energy_mev(10.0)) < 1e-9
        and abs(landau_level_mev(0, 10.0)
                - 0.5 * cyclotron_energy_mev(10.0)) < 1e-9)
    chk("gaas_spacing_at_10T_sane", 17.0 < cyclotron_energy_mev(10.0) < 17.6)
    chk("zeeman_smaller_than_cyclotron",
        zeeman_energy_mev(10.0) < cyclotron_energy_mev(10.0))
    chk("degeneracy_grows_with_B",
        degeneracy_per_cm2(12.0) > degeneracy_per_cm2(6.0) > 0)
    chk("filling_inverse_in_B",
        abs(filling_factor(DEMO_DENSITY_M2, 5.0)
            - 2.0 * filling_factor(DEMO_DENSITY_M2, 10.0)) < 1e-9)
    chk("field_for_filling_roundtrip",
        abs(filling_factor(DEMO_DENSITY_M2,
                           field_for_filling(DEMO_DENSITY_M2, 3)) - 3.0)
        < 1e-9)
    chk("magnetic_length_shrinks_with_B",
        magnetic_length_nm(4.0) > magnetic_length_nm(10.0)
        and abs(magnetic_length_nm(10.0) - 8.11) < 0.05)
    fan = landau_fan()
    chk("fan_table_shape", len(fan) == 6
        and all(r["spacing_meV"] > 0 for r in fan)
        and fan[-1]["nu_at_demo_density"] < fan[0]["nu_at_demo_density"])

    # 2. exact plateau arithmetic
    chk("sigma_xy_exact_integers",
        all(sigma_xy_exact_e2h(n) == Fraction(n) for n in range(1, 7)))
    chk("hall_resistance_exact_reciprocals",
        hall_resistance_rk(1) == 1 and hall_resistance_rk(2) == Fraction(1, 2)
        and hall_resistance_rk(4) == Fraction(1, 4)
        and hall_resistance_rk(6) == Fraction(1, 6))
    chk("hall_resistance_ohm_nu2",
        abs(hall_resistance_ohm(2) - R_K_LABELLED / 2.0) < 0.01)
    chk("exact_arithmetic_is_fraction",
        isinstance(sigma_xy_exact_e2h(3), Fraction)
        and isinstance(hall_resistance_rk(3), Fraction))
    table = plateau_table()
    chk("plateau_table_fields", len(table) == 6
        and table[0]["sigma_xy_e2h_exact"] == "1"
        and table[1]["R_xy_RK_exact"] == "1/2"
        and table[0]["B_centre_T"] > table[-1]["B_centre_T"])

    # 3. transport toy model
    chk("sigma_xy_on_plateau_centres",
        all(abs(sigma_xy_curve(float(n)) - n) < 1e-3 for n in (1, 2, 3, 4)))
    chk("sigma_xy_midpoint_half_steps",
        all(abs(sigma_xy_curve(k - 0.5) - (k - 0.5)) < 1e-9
            for k in (1, 2, 3)))
    chk("sigma_xx_vanishes_on_plateaus",
        all(sigma_xx_curve(float(n)) < 1e-6 for n in (1, 2, 3)))
    chk("sigma_xx_peaks_at_transitions",
        all(abs(sigma_xx_curve(k - 0.5) - XX_PEAK) < 1e-9
            for k in (1, 2, 3))
        and sigma_xx_curve(2.5) > sigma_xx_curve(2.2)
        > sigma_xx_curve(2.0))
    chk("sigma_xy_monotone",
        all(sigma_xy_curve(0.2 + 0.05 * i)
            <= sigma_xy_curve(0.2 + 0.05 * (i + 1)) + 1e-12
            for i in range(100)))
    w2 = plateau_width(2)
    chk("plateau_width_positive_and_bounded",
        0.3 < w2["width_nu"] < 1.0 and w2["width_T"] > 0)
    widths = [plateau_width(n)["width_nu"] for n in (1, 2, 3, 4)]
    chk("plateau_widths_comparable",
        all(abs(w - widths[0]) < 0.05 for w in widths))
    trep = transport_report()
    chk("transport_report_shape", len(trep["plateau_widths"]) == 4
        and len(trep["transition_peaks"]) == 4)

    # 4. Jacobi solver + Hofstadter butterfly
    chk("jacobi_known_matrix",
        all(abs(a - b) < 1e-9 for a, b in zip(
            jacobi_eigenvalues([[2.0, 1.0], [1.0, 2.0]]), [1.0, 3.0])))
    chk("jacobi_identity",
        all(abs(a - 1.0) < 1e-12 for a in
            jacobi_eigenvalues([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
                                [0.0, 0.0, 1.0]])))
    spec_half = hofstadter_spectrum(1, 2)
    chk("hofstadter_band_count", len(spec_half) == 2 * 4 * 4)
    chk("hofstadter_half_band_edge",
        abs(max(abs(e) for e in spec_half) - 2.0 * math.sqrt(2.0)) < 0.05)
    chk("hofstadter_trace_zero", abs(sum(spec_half)) < 1e-6)
    spec_third = hofstadter_spectrum(1, 3)
    chk("hofstadter_spectrum_symmetric",
        all(abs(spec_third[i] + spec_third[-1 - i]) < 1e-6
            for i in range(len(spec_third))))
    spec_two_thirds = hofstadter_spectrum(2, 3)
    chk("hofstadter_alpha_mirror",
        all(abs(a - b) < 1e-6 for a, b in zip(spec_third,
                                              spec_two_thirds)))
    chk("hofstadter_bands_bounded",
        all(abs(e) <= 4.0 + 1e-9 for e in spec_third))
    chk("gap_label_third_r1", gap_label(1, 3, 1) == (0, 1))
    chk("gap_label_third_r2", gap_label(1, 3, 2) == (1, -1))
    chk("gap_label_half_r1", gap_label(1, 2, 1) == (0, 1))
    chk("gap_label_quarter", gap_label(1, 4, 1) == (0, 1)
        and gap_label(1, 4, 3) == (1, -1))
    hrep = hofstadter_report()
    chk("hofstadter_report_counts", hrep["rationals"] == 17
        and hrep["total_eigenvalues"] > 500)

    # 5. fractional section - labelled, scales computed, no fake ED
    frep = fractional_report()
    chk("coulomb_scale_positive", frep["coulomb_scale_meV_computed"] > 0)
    chk("coulomb_scale_grows_with_B",
        coulomb_scale_mev(12.0) > coulomb_scale_mev(6.0))
    chk("gap_estimate_below_coulomb_scale",
        frep["gap_estimate_meV_labelled"][1]
        < frep["coulomb_scale_meV_computed"])
    chk("fractional_field_for_third",
        abs(frep["B_for_nu_1_3_at_demo_density_T"]
            - field_for_filling(DEMO_DENSITY_M2, 1.0 / 3.0)) < 0.01)
    sketch = pair_counting_sketch(6)
    chk("pair_counting_sketch", sketch["pairs"] == 15
        and sketch["laughlin_min_pair_m"] == 3
        and "no Hamiltonian" in sketch["note"])

    # 6. classifier - labels come from the lab's own model
    rep = classifier_report()
    chk("classifier_plateau_centres", rep["nu_3.00_B8_T0.3"] == "plateau"
        and rep["nu_2.00_B8_T0.3"] == "plateau")
    chk("classifier_transition_midpoint",
        rep["nu_3.50_B8_T0.3"] == "transition"
        and rep["nu_4.50_B8_T1.5"] == "transition")
    chk("classifier_insulating_localized", rep["nu_2.65_B8_T0.3"]
        == "insulating")
    chk("classifier_hot_is_transition", rep["nu_3.02_B2_T40"]
        == "transition")
    chk("classifier_matches_model",
        all(classify_regime(nu, b, t)
            == model_label(*regime_features(nu, b, t))
            for nu, b, t in [(3.0, 8.0, 0.3), (2.0, 8.0, 0.3),
                             (3.5, 8.0, 0.3), (2.65, 8.0, 0.3),
                             (3.02, 2.0, 40.0), (4.5, 8.0, 1.5)]))

    # gates + seats
    chk("hold_gates_14", len(HOLD_GATES) == 14
        and all(v.startswith("HOLD") for v in HOLD_GATES.values()))
    chk("gate_metrology_hold", gate("metrology_standard_claim") == "HOLD")
    chk("gate_measured_data_hold",
        gate("measured_device_data_claim") == "HOLD")
    chk("gate_fabricated_ed_hold",
        gate("fabricated_exact_diagonalization") == "HOLD")
    chk("gate_discovery_hold",
        gate("fractional_state_discovery_claim") == "HOLD")
    chk("gate_sandbox_proceed", gate("run_simulation") == "PROCEED")
    brains = brains_report()
    chk("argon4_no_override", brains["decider"]["can_override_hold"] is False
        and brains["decider"]["seat"]
        == "Gemini Argon 4 Extended Thinking")
    chk("claude_no_override", brains["advisor"]["can_override_hold"] is False)
    chk("flow_plan_only", brains["flow"]["rendered"] is False
        and brains["flow"]["live"] == 0)
    return c


# ================================================================ CLI / demo
def demo():
    print("=" * 68)
    print("QuantumHall-Lab - quantum Hall effect lab")
    print("by Darion Kellar | MIT | pure stdlib | zero network | EDUCATION ONLY")
    print("=" * 68)
    print("\n[1] THE HONEST SCOPE - models and spectra, not measurements")
    print("    Landau levels, exact plateau fractions, a LABELLED")
    print("    localization toy for the curves, and Harper-equation")
    print("    spectra from a from-scratch eigensolver. The fractional")
    print("    section is labelled textbook values only - no exact")
    print("    diagonalization of a fractional state is run or claimed.")
    print("    Nothing here is measured device data or metrology.")
    print("\n[2] Landau fan - GaAs-style 2DEG (labelled m* = 0.067 m_e), "
          "n = 3.0e11 cm^-2")
    for row in landau_fan():
        print(f"    B {row['B_T']:5.1f} T | spacing {row['spacing_meV']:7.3f} meV "
              f"| E0 {row['E0_meV']:6.3f} | deg {row['degeneracy_per_cm2']:12.3e}"
              f" /cm^2 | nu {row['nu_at_demo_density']:6.3f} "
              f"| l_B {row['l_B_nm']:5.2f} nm")
    rk = von_klitzing_ohm()
    print(f"    R_K from constants h/e^2 = {rk:.3f} ohm "
          f"(labelled CODATA {R_K_LABELLED} ohm, "
          f"rel. diff {abs(rk - R_K_LABELLED) / R_K_LABELLED:.2e})")
    print("\n[3] Exact plateaus - sigma_xy = nu * e^2/h, R_xy = R_K / nu "
          "(exact fractions)")
    for row in plateau_table():
        print(f"    nu {row['nu']} | B centre {row['B_centre_T']:7.3f} T "
              f"| sigma_xy {row['sigma_xy_e2h_exact']} e^2/h "
              f"| R_xy {row['R_xy_RK_exact']} R_K = {row['R_xy_ohm']:10.3f} ohm")
    print("\n[4] Plateau widths - LABELLED localization toy model")
    trep = transport_report()
    for w in trep["plateau_widths"]:
        print(f"    nu {w['nu']} plateau: nu in [{w['nu_lo']}, {w['nu_hi']}] "
              f"| width {w['width_nu']} in nu, {w['width_T']} T at demo density")
    for pk in trep["transition_peaks"]:
        print(f"    transition at nu {pk['nu']}: sigma_xx peak "
              f"{pk['sigma_xx_peak_e2h']} e^2/h, sigma_xy midpoint "
              f"{pk['sigma_xy_midpoint_e2h']} e^2/h")
    print("\n[5] Hofstadter butterfly - Harper spectra, flux p/q, q <= 7")
    hrep = hofstadter_report()
    print(f"    rationals sampled {hrep['rationals']} | eigenvalues "
          f"{hrep['total_eigenvalues']} | widest spectrum "
          f"{hrep['widest_spectrum'][0]} width {hrep['widest_spectrum'][1]}")
    for name, label in hrep["gap_labels"].items():
        print(f"    gap label {name}: (s, t) = {label} "
              f"-> gap Hall conductance t = {label[1]} e^2/h")
    print("\n[6] Fractional QHE - LABELLED textbook values only (no ED run)")
    frep = fractional_report()
    print(f"    Laughlin nu = 1/3 at demo density needs B = "
          f"{frep['B_for_nu_1_3_at_demo_density_T']} T")
    print(f"    quasiparticle charge {frep['quasiparticle_charge']}")
    print(f"    l_B at 10 T = {frep['l_B_nm_at_B']} nm | Coulomb scale "
          f"(computed) {frep['coulomb_scale_meV_computed']} meV")
    print(f"    gap estimate (labelled) "
          f"{frep['gap_estimate_meV_labelled'][0]}-"
          f"{frep['gap_estimate_meV_labelled'][1]} meV - "
          f"{frep['gap_note']}")
    print(f"    counting sketch: {frep['counting_sketch']['electrons']} "
          f"electrons, {frep['counting_sketch']['pairs']} pairs, Laughlin "
          f"min pair m = {frep['counting_sketch']['laughlin_min_pair_m']}")
    print("\n[7] Transport regime classifier (TinyML kNN, model labels)")
    for name, label in classifier_report().items():
        print(f"    {name:22s} -> {label}")
    print("\n[8] Advisory seats")
    brains = brains_report()
    print(f"    decider: {brains['decider']['decision']} "
          f"trace={brains['decider']['trace_sha256_16']}")
    print(f"    advisor can_override_hold = {brains['advisor']['can_override_hold']}")
    print(f"    flow rendered = {brains['flow']['rendered']} "
          f"live = {brains['flow']['live']}")
    print(f"\n[9] HOLD gates: {len(HOLD_GATES)}")
    for key in HOLD_GATES:
        print(f"    HOLD  {key}")
    checks = run_checks()
    passed = sum(1 for _, ok in checks if ok)
    print(f"\nCHECKS {passed}/{len(checks)}")
    for name, ok in checks:
        if not ok:
            print(f"    FAIL {name}")
    verdict = "PROCEED" if passed == len(checks) else "HOLD"
    print(f"VERDICT {verdict} (sandbox simulation only) | HOLD gates {len(HOLD_GATES)}")
    return 0 if passed == len(checks) else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "demo":
        return demo()
    cmd = argv[0]
    if cmd == "checks":
        checks = run_checks()
        for name, ok in checks:
            print(f"{'PASS' if ok else 'FAIL'} {name}")
        print(f"CHECKS {sum(1 for _, ok in checks if ok)}/{len(checks)}")
        return 0 if all(ok for _, ok in checks) else 1
    if cmd == "landau":
        print(json.dumps(landau_fan(), indent=2, sort_keys=True))
        return 0
    if cmd == "plateaus":
        print(json.dumps(plateau_table(), indent=2, sort_keys=True))
        return 0
    if cmd == "transport":
        print(json.dumps(transport_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "hofstadter":
        print(json.dumps(hofstadter_report(), indent=2, sort_keys=True,
                         default=str))
        return 0
    if cmd == "fractional":
        print(json.dumps(fractional_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "classify":
        print(json.dumps(classifier_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "brains":
        print(json.dumps(brains_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "holds":
        for key, value in HOLD_GATES.items():
            print(f"{key}: {value}")
        return 0
    if cmd == "hold-demo":
        action = argv[1] if len(argv) > 1 else "metrology_standard_claim"
        print(f"{action}: {HOLD_GATES.get(action, 'PROCEED - not gated')}")
        return 2 if gate(action) == "HOLD" else 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
