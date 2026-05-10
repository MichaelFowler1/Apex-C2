import krpc
import time
import pandas as pd
from sklearn.ensemble import IsolationForest
import warnings

# Suppress sklearn terminal spam for a clean C2 interface
warnings.filterwarnings('ignore')

print("[*] Phoenix Vanguard: Autonomous C2 Initializing...")

# 1. Quick-train the AI on your exact hardware baseline
print("[*] Loading training data and compiling ML model...")
try:
    df = pd.read_csv('power_fault_data.csv')
except FileNotFoundError:
    print("[!] ERROR: 'power_fault_data.csv' not found. Please run the fault injector first.")
    exit()

df['Charge_Delta'] = df['Charge_Level'].diff().fillna(0)

# Train the model locally
X_train = df[['Charge_Level', 'Charge_Delta']]
model = IsolationForest(n_estimators=100, contamination=0.4, random_state=42)
model.fit(X_train)
print("[+] AI Edge Model Compiled and Ready.")

# 2. Connect to Hardware
print("\n[*] Establishing live telemetry streams...")
try:
    conn = krpc.connect(name='Vanguard_Auto_C2')
except krpc.error.NetworkError:
    print("[!] ERROR: Could not connect to KSP. Is the kRPC server running in-game?")
    exit()

vessel = conn.space_center.active_vessel
charge_stream = conn.add_stream(vessel.resources.amount, 'ElectricCharge')

# Ensure we start in a safe baseline state
vessel.control.sas = True
vessel.control.set_action_group(1, True)

# 3. The Live C2 Loop
print("\n[================ LIVE TELEMETRY FEED ================]")
print("  T-MET  |  CHARGE  |  DELTA  |  AI STATUS")

previous_charge = charge_stream()
start_time = time.time()

try:
    while True:
        time.sleep(1) # 1Hz telemetry loop
        current_charge = round(charge_stream(), 2)
        delta = round(current_charge - previous_charge, 2)
        
        # --- THE THRESHOLD GATE ---
        # Only ask the AI if the power is actively draining
        # beyond normal probe core usage (worse than -0.5 per sec)
        if delta < -0.5:
            live_data = pd.DataFrame([[current_charge, delta]], columns=['Charge_Level', 'Charge_Delta'])
            prediction = model.predict(live_data)[0]
        else:
            prediction = 1 # Force a "Nominal" state for normal noise and solar recharging
            
        if prediction == 1:
            status = "[ NOMINAL ]"
            print(f"  {round(time.time()-start_time,1):>5}  |  {current_charge:>6}  |  {delta:>5}  |  {status}")
        else:
            status = "[! ANOMALY DETECTED !]"
            print(f"  {round(time.time()-start_time,1):>5}  |  {current_charge:>6}  |  {delta:>5}  |  {status}")
            
            # --- AUTONOMOUS RESCUE PROTOCOL ---
            print("\n[!] CRITICAL FAULT: Autonomous Healing Protocol Engaged!")
            
            # 1. Kill any phantom gyro spin
            vessel.control.yaw = 0.0
            vessel.control.pitch = 0.0
            vessel.control.roll = 0.0
            
            # 2. Re-engage Stability Augmentation
            vessel.control.sas = True
            
            # 3. Ensure solar arrays are deployed to catch the sun
            vessel.control.set_action_group(1, True)
            
            print("[+] Satellite secured. Returning to nominal operations.\n")
            
            # Give the hardware a few seconds to stabilize before resuming monitoring
            time.sleep(3)
            previous_charge = charge_stream() # Reset baseline
            continue
            
        previous_charge = current_charge

except KeyboardInterrupt:
    print("\n[*] C2 Link Terminated by Operator.")