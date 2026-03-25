"""
failure_rate_analysis.py — Preuve de Concept : Taux d'Échec de Déchiffrement
=============================================================================
Problématique centrale de la cryptographie post-quantique.

CHOIX MÉTHODOLOGIQUE :
  Pour observer des échecs avec des paramètres réels (n=256, q=3329),
  on encode n=256 bits simultanément (un bit par coefficient du polynôme)
  et on génère clé ET chiffrement avec le même η.
  Un seul coefficient erroné = bloc entier perdu.

  Variance du bruit résiduel ε : Var(ε) = η·(n·η + 1)/2
  Seuil d'échec d'un coefficient : |ε[i]| > q/4 ≈ 832
  Transition visible expérimentalement pour η ∈ [14, 26].

Référence : D'Anvers et al. — "Failure is not an Option" EUROCRYPT 2018.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from math import erfc, sqrt

from ring_lwe import N, Q, ETA, RqPolynomial, cbd_sample, random_poly

NUM_TRIALS = 500
ETA_VALUES = list(range(2, 32, 2))
SEED       = 42


def keygen_eta(eta, rng):
    a = random_poly(N, Q, rng)
    s = cbd_sample(eta, N, Q, rng)
    e = cbd_sample(eta, N, Q, rng)
    b = a * s + e
    return (a, b), s


def encrypt_poly(message_bits, pub_key, eta, rng):
    """Chiffrement d'un polynôme-message : n bits, un par coefficient."""
    a, b = pub_key
    q_half = Q // 2
    r  = cbd_sample(eta, N, Q, rng)
    e1 = cbd_sample(eta, N, Q, rng)
    e2 = cbd_sample(eta, N, Q, rng)
    u  = a * r + e1
    msg_poly = RqPolynomial((message_bits * q_half % Q).astype(np.int64), N, Q)
    v  = b * r + e2 + msg_poly
    return u, v


def decrypt_poly(ct, priv_key):
    """Déchiffrement : décision coefficient par coefficient."""
    u, v = ct
    w = v - priv_key * u
    c = w.coeffs.astype(np.int64)
    c = np.where(c > Q // 2, c - Q, c)
    return (np.round(2 * c / Q).astype(int) % 2)


def analytical_dfr(eta, n=N, q=Q):
    """Taux d'échec théorique par approximation gaussienne."""
    var   = eta * (n * eta + 1) / 2
    sigma = sqrt(var)
    p_coeff = erfc((q // 4) / (sigma * sqrt(2)))
    return 1.0 - (1.0 - p_coeff) ** n


# ── Test de cohérence ─────────────────────────────────────────────────

def sanity_check(num_trials=200):
    print("=" * 62)
    print(f"  PARTIE 1 : Test de cohérence — η = {ETA} (Kyber-512), {num_trials} blocs")
    print("=" * 62)
    rng = np.random.default_rng(SEED)
    failures = 0
    for _ in range(num_trials):
        msg = rng.integers(0, 2, size=N, dtype=np.int64)
        pk, sk = keygen_eta(ETA, rng)
        ct  = encrypt_poly(msg, pk, ETA, rng)
        dec = decrypt_poly(ct, sk)
        if not np.array_equal(dec, msg):
            failures += 1
    rate = failures / num_trials
    print(f"  → Blocs testés : {num_trials}  |  Échecs : {failures}  |  Taux d'échec : {rate:.4%}")
    print(f"  {'✅  Taux = 0. Le taux théorique pour η=2 est < 2^-139.' if failures == 0 else '⚠️  Échecs inattendus.'}\n")
    return rate


# ── Analyse Taux d'échec vs η ────────────────────────────────────────

def failure_rate_vs_eta(eta_values, num_trials=NUM_TRIALS):
    print("=" * 62)
    print(f"  PARTIE 2 : Taux d'échec expérimental selon η ({num_trials} blocs/η)")
    print("=" * 62)
    print(f"  {'η':>4}  {'Échecs':>8}  {'Taux exp.':>10}  {'Taux théo.':>10}")
    print("  " + "-" * 42)
    results = {}
    for eta in eta_values:
        rng = np.random.default_rng(SEED + eta * 17)
        failures = 0
        for _ in range(num_trials):
            msg = rng.integers(0, 2, size=N, dtype=np.int64)
            pk, sk = keygen_eta(eta, rng)
            ct  = encrypt_poly(msg, pk, eta, rng)
            dec = decrypt_poly(ct, sk)
            if not np.array_equal(dec, msg):
                failures += 1
        rate_exp  = failures / num_trials
        rate_theo = analytical_dfr(eta)
        results[eta] = rate_exp
        m = "✅" if rate_exp == 0 else ("⚠️ " if rate_exp < 0.2 else "❌")
        print(f"  {eta:>4}  {failures:>8}  {rate_exp:>9.2%}  {rate_theo:>9.2%}  {m}")
    print()
    return results


# ── Visualisation ─────────────────────────────────────────────────────

def plot_results(failure_rates, save_path="taux_echec_dechiffrement.png"):
    etas      = list(failure_rates.keys())
    rates_exp = [failure_rates[e] for e in etas]
    rates_theo= [analytical_dfr(e) for e in etas]

    BG=("#161b22"); BG2="#0d1117"; TEXT="#e6edf3"; GRID="#30363d"
    BLUE="#58a6ff"; ORANGE="#f0883e"; GREEN="#3fb950"
    RED="#f85149"; PURPLE="#bc8cff"

    fig = plt.figure(figsize=(15, 6.5), dpi=130, facecolor=BG2)
    gs  = gridspec.GridSpec(1, 2, figure=fig, wspace=0.38)

    def style(ax):
        ax.set_facecolor(BG)
        ax.tick_params(colors=TEXT, labelsize=9)
        for sp in ax.spines.values(): sp.set_edgecolor(GRID)
        ax.xaxis.label.set_color(TEXT)
        ax.yaxis.label.set_color(TEXT)
        ax.title.set_color(TEXT)
        ax.grid(True, color=GRID, linestyle="--", linewidth=0.55, alpha=0.65)

    # Panneau A : courbe du Taux d'échec
    ax1 = fig.add_subplot(gs[0])
    style(ax1)
    ax1.plot(etas, rates_theo, color=BLUE, lw=2.2, label="Taux théorique (approx. gaussienne)", zorder=3)
    ax1.scatter(etas, rates_exp, color=ORANGE, s=55, zorder=5,
                label=f"Taux expérimental ({NUM_TRIALS} essais/η)", edgecolors=BG, lw=0.8)
    ax1.axvline(2, color=PURPLE, ls=":", lw=1.8, label="η = 2 (Kyber-512, Taux < 2⁻¹³⁹)", alpha=0.85)
    ax1.axhline(0.01, color=RED, ls="--", lw=1.1, alpha=0.6, label="Seuil 1%")
    ax1.set_xlabel("Paramètre de bruit η", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Taux d'échec de déchiffrement", fontsize=11, fontweight="bold")
    ax1.set_title(
        "(A) Taux d'Échec de Déchiffrement selon η\n"
        r"$R_q=\mathbb{Z}_{3329}[X]/(X^{256}+1)$, encodage "+f"{N} bits/bloc",
        fontsize=10.5, fontweight="bold", pad=10)
    ax1.set_xticks(etas)
    ax1.set_ylim(-0.04, 1.07)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax1.legend(facecolor=BG, edgecolor=GRID, labelcolor=TEXT, fontsize=8.2, loc="upper left")

    # Panneau B : distribution du bruit résiduel
    ax2 = fig.add_subplot(gs[1])
    style(ax2)
    q4 = Q / 4

    for eta_d, col, lbl in [(2, GREEN, "η = 2 (Kyber, Taux ≈ 0)"),
                             (14, BLUE, "η = 14 (transition)"),
                             (24, RED,  "η = 24 (Taux élevé)")]:
        rng_d = np.random.default_rng(eta_d + 100)
        res = []
        for _ in range(300):
            pk_d, sk_d = keygen_eta(eta_d, rng_d)
            msg_d = np.zeros(N, dtype=np.int64)
            ct_d  = encrypt_poly(msg_d, pk_d, eta_d, rng_d)
            u_d, v_d = ct_d
            w_d = v_d - sk_d * u_d
            c = w_d.coeffs.astype(np.int64)
            c = np.where(c > Q//2, c-Q, c)
            res.extend(c.tolist())
        ax2.hist(res, bins=80, alpha=0.5, color=col, label=lbl, edgecolor="none", density=True)

    for sgn in [1, -1]:
        ax2.axvline(sgn*q4, color=TEXT, ls=":", lw=1.4, alpha=0.7)
    ax2.text(q4+25, ax2.get_ylim()[1]*0.85, f"+q/4≈{int(q4)}", color=TEXT, fontsize=7.5)
    ax2.text(-q4-25, ax2.get_ylim()[1]*0.85, f"−q/4", color=TEXT, fontsize=7.5, ha="right")
    ax2.set_xlabel(r"Bruit résiduel $\varepsilon[i]$ (centré)", fontsize=10.5)
    ax2.set_ylabel(f"Densité (n={N} coefficients/bloc)", fontsize=10.5)
    ax2.set_title(
        r"(B) Distribution de $\varepsilon = e\cdot r + e_2 - e_1\cdot s$" + "\n"
        r"Échec si $|\varepsilon[i]| > q/4 \approx 832$",
        fontsize=10.5, fontweight="bold", pad=10)
    ax2.legend(facecolor=BG, edgecolor=GRID, labelcolor=TEXT, fontsize=8.5)

    fig.suptitle(
        "Démo Ring-LWE — Analyse du Taux d'Échec de Déchiffrement\n"
        f"n={N}, q={Q}  |  {N} bits/bloc  |  {NUM_TRIALS} essais/η  |  Inspiré de ML-KEM (NIST FIPS 203)",
        color=TEXT, fontsize=11, fontweight="bold", y=1.02)

    plt.savefig(save_path, dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"  📊  Figure sauvegardée → {save_path}")
    plt.show()


# ── Main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "═"*62)
    print("  Démo Ring-LWE — Analyse du Taux d'Échec de Déchiffrement")
    print(f"  n={N}, q={Q}, η_Kyber={ETA}")
    print("═"*62 + "\n")

    sanity_check(200)
    failure_rates = failure_rate_vs_eta(ETA_VALUES, NUM_TRIALS)
    plot_results(failure_rates)

    print("─"*62)
    print("  INTERPRÉTATION ACADÉMIQUE")
    print("─"*62)
    safe = [e for e,r in failure_rates.items() if r==0]
    bad  = [e for e,r in failure_rates.items() if r>0.05]
    if safe: print(f"  • Taux d'échec = 0 pour η ≤ {max(safe)} (sur {NUM_TRIALS} essais)")
    if bad:  print(f"  • Taux d'échec > 5% à partir de η = {min(bad)}")
    print(f"  • Pour Kyber-512 (η=2) : Taux théorique < 2^-139")
    print(f"  • σ_résiduel(η=2) ≈ {(ETA*(N*ETA+1)/2)**0.5:.1f}  <<  q/4 = {Q//4}")
    print(f"  • L'équipe CASCADE calcule le taux d'échec exact via la FFT de β_η")
    print("═"*62 + "\n")