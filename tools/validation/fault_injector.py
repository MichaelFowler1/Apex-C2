import time
import csv
import krpc

# --- TEST CAMPAIGN CONFIGURATION ---
BASELINE_DURATION = 10  # Seconds of clean data collection
FAULT_DURATION = 15     # Seconds of anomalous data collection
YAW_TORQUE = 0.3        # 30% power to prevent violent structural disassembly

def run_fault_injection_campaign():
    print("[*] Initializing Phoenix Vanguard Fault Injector (Test Vector: Gyro Override)")
    
    try:
        # 1. Establish C2 link and target the asset
        conn = krpc.connect(name='Fault_Injection_Harness')
        vessel = conn.space_center.active_vessel
        
        # 2. Setup telemetry streams (reduces kRPC latency vs polling directly)
        ut = conn.add_stream(getattr, conn.space_center, 'ut')
        charge_stream = conn.add_stream(vessel.resources.amount, 'ElectricCharge')

        # 3. Secure a known-good starting state
        print("[*] Pre-test check: Forcing panels open and SAS on...")
        vessel.control.set_action_group(1, True)
        vessel.control.sas = True
        time.sleep(2) # Give the physical game engine a moment to settle

        with open('power_fault_data.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Time_Offset', 'Charge_Level', 'Fault_Label']) 
            start_time = ut()
            
            # --- PHASE 1: BASELINE COLLECTION ---
            print(f"[*] Phase 1: Recording {BASELINE_DURATION}s of nominal telemetry...")
            for _ in range(BASELINE_DURATION):
                writer.writerow([round(ut() - start_time, 1), round(charge_stream(), 2), 0])
                time.sleep(1)
                
            # --- PHASE 2: FAULT INJECTION ---
            print("\n[!] EXECUTING TEST VECTOR: Hard-Fault Initiation [!]")
            print(f"[!] Retracting solar arrays and inducing {YAW_TORQUE*100}% yaw spin...")
            
            vessel.control.set_action_group(1, False) 
            vessel.control.sas = False 
            
            # Isolate the fault to a single axis for cleaner data
            vessel.control.yaw = YAW_TORQUE 
            vessel.control.pitch = 0.0
            vessel.control.roll = 0.0
            
            # --- PHASE 3: ANOMALY COLLECTION ---
            print(f"[*] Phase 3: Recording {FAULT_DURATION}s of anomaly decay curve...")
            for _ in range(FAULT_DURATION):
                writer.writerow([round(ut() - start_time, 1), round(charge_stream(), 2), 1])
                time.sleep(1)

            print("\n[*] Data collection complete. Dataset saved to 'power_fault_data.csv'.")

    except Exception as e:
        print(f"\n[!] HARNESS CRASH: Unexpected failure during testing: {e}")
        
    finally:
        # --- PHASE 4: SAFE MODE (CRITICAL) ---
        # This guarantees the hardware is reset even if the user hits Ctrl+C 
        # or the script crashes during the spin phase.
        print("\n[*] Securing hardware: Resetting controls to nominal state...")
        try:
            vessel.control.yaw = 0.0 
            vessel.control.pitch = 0.0
            vessel.control.roll = 0.0
            vessel.control.sas = True 
            vessel.control.set_action_group(1, True) 
            print("[+] Asset secured.")
        except NameError:
            # Failsafe if the script crashed before 'vessel' was even defined
            pass 

if __name__ == "__main__":
    run_fault_injection_campaign()