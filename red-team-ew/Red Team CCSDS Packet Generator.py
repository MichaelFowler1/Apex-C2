import time
import numpy as np

def apply_ew_environment(nominal_signal, is_jammed=False, attack_profile="barrage"):
    """
    Mixes nominal telemetry with simulated RF interference at the receiver.
    """
    # Always apply baseline cosmic/thermal noise floor
    noise_floor = np.random.normal(0, 0.5)
    
    if not is_jammed:
        return nominal_signal + noise_floor

    # --- ACTIVE JAMMER LOGIC ---
    
    if attack_profile == "barrage":
        # Sledgehammer approach: high-amplitude white noise to crush the SNR
        barrage_noise = np.random.normal(0, 50.0)
        return nominal_signal + barrage_noise
        
    elif attack_profile == "spoofing":
        # Finesse approach: smooth sine wave to mimic a rhythmic hardware fault (e.g., gyro spin)
        spoof_wave = 20 * np.sin(time.time())
        return nominal_signal + spoof_wave
        
    else:
        # Catch-all just in case we pass a typo during testing
        print(f"[!] WARNING: EW profile '{attack_profile}' not recognized. Defaulting to standard noise.")
        return nominal_signal + noise_floor