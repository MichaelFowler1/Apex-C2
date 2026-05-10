import krpc
import time
import csv

print("[*] Initializing Phoenix Vanguard Fault Injector (Gyro Override)...")
conn = krpc.connect(name='Fault_Node')
vessel = conn.space_center.active_vessel

ut = conn.add_stream(getattr, conn.space_center, 'ut')
charge_stream = conn.add_stream(vessel.resources.amount, 'ElectricCharge')

# Ensure panels are open and SAS is holding us still
vessel.control.set_action_group(1, True)
vessel.control.sas = True
time.sleep(2) 

with open('power_fault_data.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Time_Offset', 'Charge_Level', 'Fault_Label']) 
    start_time = ut()
    
    # --- PHASE 1: BASELINE (10 Seconds) ---
    print("[*] Phase 1: Recording stable baseline...")
    for _ in range(10):
        writer.writerow([round(ut() - start_time, 1), round(charge_stream(), 2), 0])
        time.sleep(1)
        
# --- PHASE 2: FAULT INJECTION (Controlled Spin) ---
    print("\n[!] CRITICAL: INJECTING HARDWARE FAULT [!]")
    print("[!] Retracting Panels & Initiating Gentle Power Drain...")
    
    vessel.control.set_action_group(1, False) 
    vessel.control.sas = False 
    
    # Only spin on ONE axis, and only at 30% power
    vessel.control.yaw = 0.3 
    vessel.control.pitch = 0.0
    vessel.control.roll = 0.0
    
    # --- PHASE 3: ANOMALY RECORDING (15 Seconds) ---
    print("[*] Phase 3: Recording anomaly decay curve...")
    for _ in range(15):
        writer.writerow([round(ut() - start_time, 1), round(charge_stream(), 2), 1])
        time.sleep(1)

# --- PHASE 4: RESCUE ---
print("\n[*] Test Complete. Securing hardware...")
# Stop the spin commands
vessel.control.yaw = 0.0 
vessel.control.pitch = 0.0
vessel.control.roll = 0.0

# Turn auto-stabilization back on and deploy panels
vessel.control.sas = True 
vessel.control.set_action_group(1, True) 
print("[*] Dataset saved to 'power_fault_data.csv'.")