import numpy as np
import time

def generate_synthetic_ew_environment(nominal_signal, jammer_active, attack_type="barrage"):
    """
    Simulates the RF environment at the satellite's receiver array.
    """
    noise_floor = np.random.normal(0, 0.5) # Natural cosmic background noise
    
    if not jammer_active:
        return nominal_signal + noise_floor
        
    if attack_type == "barrage":
        # High-amplitude white noise to drown out the C2 link
        jamming_signal = np.random.normal(0, 50.0) 
        return nominal_signal + jamming_signal
        
    elif attack_type == "spoofing":
        # Injecting a synthetic sine wave to mimic a rhythmic thruster misfire
        synthetic_anomaly = 20 * np.sin(time.time())
        return nominal_signal + synthetic_anomaly