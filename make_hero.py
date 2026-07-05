#!/usr/bin/env python3
"""
Generate docs/hero.png - the README image.

The top panel is REAL orbital geometry: the elevation/AOS math from
`physical-range/physical pipeline.py` (get_link_metrics), evaluated across a
full ground-station pass of the 985 km asset. The AOS window it produces is the
only time the Red Team may inject CCSDS frames. The lower panel renders the
documented attack -> autonomous-recovery sequence (SAS disable -> Vanguard FSW
re-enable, MTTR < 1 s).

Run:  python make_hero.py     (needs numpy + matplotlib)
"""
import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --- constants mirroring the repo ---
PLANET_R = 600_000.0        # Kerbin equatorial radius (KSP physics surrogate)
SAT_ALT = 985_000.0         # 985 km circular orbit (per README)
MU = 3.5316e12              # Kerbin gravitational parameter
ELEV_MASK = 5.0             # degrees, AOS gate from physical pipeline.py

BG, INK, DIM = "#0b1017", "#e6ebf2", "#8493a6"
C_ELEV, C_AOS, C_RED, C_BLUE, C_OK = "#39c2ff", "#28c76f", "#ff4d4d", "#3fa7ff", "#28c76f"


def elevation_deg(psi_rad):
    """Elevation angle vs. central angle psi — the exact formula from the pipeline."""
    rs = PLANET_R + SAT_ALT
    return math.degrees(math.atan2(rs * math.cos(psi_rad) - PLANET_R,
                                   rs * math.sin(psi_rad)))


# --- propagate a pass (real geometry) ---
omega = math.sqrt(MU / (PLANET_R + SAT_ALT) ** 3)   # orbital angular rate (rad/s)
# sweep central angle from below the horizon (LOS), through zenith, back to LOS,
# so the AOS window (elev >= 5 deg) is a distinct band rather than the whole pass
sweep_half = math.radians(74.0)
t_span = 2 * sweep_half / omega
t = np.linspace(0, t_span, 600)
psi = np.abs(omega * t - sweep_half)                # |central angle| over the pass
elev = np.array([elevation_deg(p) for p in psi])
aos = elev >= ELEV_MASK
t_min = t / 60.0

# --- attack / recovery sequence (documented behavior) ---
t_peak = t_span / 2
t_attack = t_peak + 60          # Red Team injects shortly after zenith (best link)
mttr = 0.8                      # < 1 s, per README
t_recover = t_attack + mttr

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK,
                     "axes.edgecolor": "#1b2740"})
fig = plt.figure(figsize=(13, 7.2), facecolor=BG)
fig.text(0.045, 0.945, "APEX-C2  ·  AUTONOMOUS ORBITAL C2 — RED vs. BLUE",
         fontsize=15.5, fontweight="bold")
fig.text(0.045, 0.900, "physical AOS gatekeeper  →  Red Team CCSDS injection  →  Blue Team "
                       "Vanguard FSW autonomous recovery  (KSP/kRPC SITL)",
         fontsize=9.5, color=DIM)

# ---- top: real elevation / AOS pass ----
ax1 = fig.add_axes([0.06, 0.40, 0.63, 0.42], facecolor="#0a0f18")
ax1.fill_between(t_min, 0, 90, where=aos, color=C_AOS, alpha=0.08)
ax1.plot(t_min, elev, color=C_ELEV, lw=2)
ax1.axhline(ELEV_MASK, color=C_AOS, ls="--", lw=1.2)
ax1.text(t_min[-1], ELEV_MASK + 2, " 5° elevation mask (AOS gate)", color=C_AOS,
         fontsize=8, ha="right")
aos_start, aos_end = t_min[aos][0], t_min[aos][-1]
ax1.text((aos_start + aos_end) / 2, 82, "AOS WINDOW — attacks physically possible",
         color=C_AOS, fontsize=8.5, ha="center", fontweight="bold")
ax1.axvline(t_attack / 60, color=C_RED, lw=1.4, ls=":")
ax1.annotate("Red Team\nCCSDS injection", xy=(t_attack / 60, elevation_deg(abs(omega*t_attack-sweep_half))),
             xytext=(t_attack / 60 + 3, 58), fontsize=8, color=C_RED,
             arrowprops=dict(arrowstyle="->", color=C_RED, lw=1))
ax1.set_ylim(0, 92); ax1.set_xlim(0, t_min[-1])
ax1.set_ylabel("elevation (deg)", fontsize=9)
ax1.set_xlabel("time through pass (min)", fontsize=9)
ax1.tick_params(colors=DIM, labelsize=8)
ax1.grid(color="#12203a", lw=0.6)
ax1.set_title("real orbital geometry — physical pipeline get_link_metrics(), 985 km asset",
              fontsize=9.5, color=DIM, loc="left", pad=6)

# ---- bottom: attack -> autonomous recovery (zoom around the injection) ----
ax2 = fig.add_axes([0.06, 0.09, 0.63, 0.22], facecolor="#0a0f18")
zt = np.linspace(-4, 6, 500)                 # seconds relative to attack
# SAS state: 1 online, 0 offline
sas = np.where((zt >= 0) & (zt < mttr), 0, 1)
# attitude deviation: nominal ~0, tumble grows while SAS off, decays after recovery
att = np.zeros_like(zt)
off = (zt >= 0) & (zt < mttr)
att[off] = 6.0 * (zt[off])                    # ramp during uncontrolled interval
dec = zt >= mttr
att[dec] = (6.0 * mttr) * np.exp(-(zt[dec] - mttr) / 0.7)
ax2.axvspan(0, mttr, color=C_RED, alpha=0.12)
ax2.plot(zt, att, color=C_RED, lw=1.8, label="attitude deviation (deg)")
ax2b = ax2.twinx()
ax2b.plot(zt, sas, color=C_BLUE, lw=1.8, ls="--", drawstyle="steps-post",
          label="SAS state")
ax2b.set_ylim(-0.15, 1.35); ax2b.set_yticks([0, 1]); ax2b.set_yticklabels(["OFF", "ON"])
ax2b.tick_params(colors=C_BLUE, labelsize=8)
ax2.annotate("SAS disabled\n(CCSDS attack)", xy=(0, 0.4), xytext=(-3.9, 3.6),
             fontsize=7.8, color=C_RED, arrowprops=dict(arrowstyle="->", color=C_RED, lw=1))
ax2.annotate(f"Vanguard FSW re-enable\nMTTR {mttr:.1f}s", xy=(mttr, 0.4),
             xytext=(mttr + 0.6, 4.5), fontsize=7.8, color=C_OK,
             arrowprops=dict(arrowstyle="->", color=C_OK, lw=1))
ax2.set_xlabel("time relative to injection (s)", fontsize=9)
ax2.set_ylabel("attitude dev (deg)", fontsize=9, color=C_RED)
ax2.tick_params(colors=DIM, labelsize=8); ax2.tick_params(axis="y", colors=C_RED)
ax2.set_xlim(-4, 6); ax2.grid(color="#12203a", lw=0.6)
ax2.set_title("autonomous recovery — 1 Hz HUMS detects SAS loss and force-restores it",
              fontsize=9.5, color=DIM, loc="left", pad=6)

# ---- right: triad + metrics ----
axr = fig.add_axes([0.73, 0.09, 0.24, 0.73]); axr.axis("off")
blocks = [
    ("THE TRIAD", INK, 10, True),
    ("① Physical pipeline", C_ELEV, 9, True),
    ("LOS/AOS gate · 5° mask", DIM, 8, False),
    ("② Red Team (EW)", C_RED, 9, True),
    ("CCSDS inject · SAS kill", DIM, 8, False),
    ("③ Blue Team Vanguard", C_BLUE, 9, True),
    ("1 Hz HUMS · auto-heal", DIM, 8, False),
    ("", INK, 6, False),
    ("KEY METRICS", INK, 10, True),
    ("MTTR", DIM, 8, False),
    ("< 1.0 s", C_OK, 11, True),
    ("poll rate", DIM, 8, False),
    ("1 Hz local", INK, 9, True),
    ("asset orbit", DIM, 8, False),
    ("985 km circular", INK, 9, True),
]
yy = 0.98
for txt, col, fs, bold in blocks:
    if txt:
        axr.text(0, yy, txt, fontsize=fs, color=col,
                 fontweight="bold" if bold else "normal", transform=axr.transAxes)
    yy -= 0.062

fig.text(0.045, 0.028, "Top panel: real AOS geometry from physical pipeline.py. Bottom: documented "
                       "attack→recovery timeline (KSP not required to render). Regenerate: python make_hero.py",
         fontsize=8, color=DIM)

os.makedirs("docs", exist_ok=True)
fig.savefig("docs/hero.png", dpi=140, facecolor=BG)
print(f"[+] wrote docs/hero.png  (pass {t_span/60:.1f} min, AOS {aos_end-aos_start:.1f} min)")
