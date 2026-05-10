import time
import warnings
import krpc
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

# Suppress sklearn terminal spam for a clean C2 interface
warnings.filterwarnings('ignore')

# --- SYSTEM CONFIGURATION ---
TRAINING_DATA_PATH = 'power_fault_data.csv'
MODEL_CONTAMINATION = 0.4
POLL_RATE_HZ = 1.0
NOMINAL_DRAIN_THRESHOLD = -0.5  # Max expected baseline drain per second

def train_edge_model():
    """Loads baseline telemetry and compiles the Isolation Forest ML model."""
    print(f"[*] Loading hardware baseline from '{TRAINING_DATA_PATH}'...")
    try:
        df = pd.read_csv(TRAINING_DATA_PATH)
    except FileNotFoundError:
        print(f"[!] FATAL: Baseline dataset missing. Run the fault injector first.")
        return None

    # Feature engineering: calculate rate of change
    df['Charge_Delta'] = df['Charge_Level'].diff().fillna(0)
    X_train = df[['Charge_Level', 'Charge_Delta']]

    print("[*] Compiling Machine Learning model for edge inference...")
    model = IsolationForest(n_estimators=100, contamination=MODEL_CONTAMINATION, random_state=42)
    model.fit(X_train)
    
    print("[+] Edge model compiled successfully.")
    return model

def execute_autonomous_c2():
    """Main C2 loop for real-time telemetry monitoring and autonomous recovery."""
    print("-" * 50)
    print("[*] VANGUARD SYSTEM: Autonomous ML Command & Control Initializing")
    print("-" * 50)

    # 1. Initialize the AI
    model = train_edge_model()
    if model is None:
        return

    # 2. Establish Hardware Link
    print("\n[*] Establishing telemetry link with flight hardware...")
    try:
        conn = krpc.connect(name='Vanguard_Auto_C2')
        vessel = conn.space_center.active_vessel
        
        # Stream limits kRPC polling overhead
        charge_stream = conn.add_stream(vessel.resources.amount, 'ElectricCharge')
        
        # Establish known-good starting state
        vessel.control.sas = True
        vessel.control.set_action_group(1, True)
        print(f"[+] Link Established. Asset: {vessel.name}")

    except krpc.error.NetworkError:
        print("[!] FATAL: Connection refused. Verify the telemetry bus (kRPC) is active.")
        return

    # 3. Live Telemetry Loop
    print("\n[================ LIVE TELEMETRY FEED ================]")
    print("  T-MET  |  CHARGE  |  DELTA  |  AI STATUS")

    start_time = time.time()
    previous_charge = charge_stream()

    try:
        while True:
            time.sleep(1.0 / POLL_RATE_HZ)
            
            current_charge = round(charge_stream(), 2)
            delta = round(current_charge - previous_charge, 2)
            t_met = round(time.time() - start_time, 1)
            
            # --- THRESHOLD GATE ---
            # Bypass the ML model if the power drain is within expected nominal ranges
            if delta < NOMINAL_DRAIN_THRESHOLD:
                # OPTIMIZATION: Pass a raw 2D numpy array instead of a slow DataFrame
                live_data = np.array([[current_charge, delta]])
                prediction = model.predict(live_data)[0]
            else:
                prediction = 1  # Force Nominal state 
                
            # --- STATE EVALUATION ---
            if prediction == 1:
                print(f"  {t_met:>5}  |  {current_charge:>6}  |  {delta:>5}  |  [ NOMINAL ]")
            else:
                print(f"  {t_met:>5}  |  {current_charge:>6}  |  {delta:>5}  |  [! ANOMALY DETECTED !]")
                
                # --- AUTONOMOUS RECOVERY PROTOCOL ---
                print("\n[!] CRITICAL FAULT DETECTED: Executing Autonomous Recovery...")
                
                # A. Null out malicious control inputs
                vessel.control.yaw = 0.0
                vessel.control.pitch = 0.0
                vessel.control.roll = 0.0
                
                # B. Re-establish stability and power generation
                vessel.control.sas = True
                vessel.control.set_action_group(1, True)
                
                print("[+] Asset secured. Hardware overrides applied.")
                print("[*] Re-baselining telemetry streams...\n")
                
                # Hardware stabilization debounce
                time.sleep(3)
                previous_charge = charge_stream()
                continue
                
            previous_charge = current_charge

    except KeyboardInterrupt:
        print("\n[*] C2 Link Terminated by Operator. Securing node.")
    except Exception as e:
        print(f"\n[!] UNHANDLED EXCEPTION IN C2 LOOP: {e}")
    finally:
        # Clean up the stream to prevent memory leaks on the kRPC server
        try:
            charge_stream.remove()
            conn.close()
        except NameError:
            pass

if __name__ == "__main__":
    execute_autonomous_c2()