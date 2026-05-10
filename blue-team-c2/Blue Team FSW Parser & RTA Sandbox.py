import krpc
import time
from datetime import datetime

# --- CONFIGURATION ---
HEARTBEAT_INTERVAL = 1.0  # 1Hz Monitoring Frequency
AUTO_RECOVERY = True      # Enable Autonomous Healing

print("-" * 50)
print("[*] OPERATION PHOENIX VANGUARD: Blue Team FSW Parser")
print("[*] Initializing Real-Time Analytics (RTA) Sandbox...")
print("-" * 50)

def run_blue_team():
    try:
        # 1. Establish C2 Handshake
        conn = krpc.connect(name='BlueTeam_Vanguard_C2')
        vessel = conn.space_center.active_vessel
        print(f"[+] C2 Link Established. Monitoring Asset: {vessel.name}")
        print("[*] Status: STEADY STATE. Waiting for telemetry...")
        print("-" * 50)

        # 2. Main Monitoring Loop
        while True:
            # Pull Telemetry
            current_sas = vessel.control.sas
            alt = vessel.flight().mean_altitude
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Logic Gate: Check for Anomaly (e.g., SAS Disengaged)
            if current_sas:
                # Nominal Operation Heartbeat
                status = "NOMINAL"
                print(f"[{timestamp}] | Alt: {alt:>10.2f}m | SAS: {str(current_sas):>5} | Status: {status}")
            else:
                # ANOMALY DETECTED
                status = "!!! ANOMALY DETECTED !!!"
                print(f"\n[!] ALERT: {timestamp} | UNEXPECTED STATE CHANGE | Status: {status}")
                
                if AUTO_RECOVERY:
                    print("[*] RTA SANDBOX: Executing Autonomous Recovery Protocol...")
                    
                    # Action: Force Stability Restoration
                    vessel.control.sas = True
                    
                    # Verification Phase
                    time.sleep(0.2) # Wait for hardware response
                    if vessel.control.sas:
                        print("[+] RECOVERY SUCCESSFUL: Integrity Restored.\n")
                    else:
                        print("[!] CRITICAL: Recovery Failed. Control Environment Contested.\n")

            time.sleep(HEARTBEAT_INTERVAL)

    except krpc.error.NetworkError:
        print("\n[!] ERROR: Connection Refused. Ensure kRPC server is 'Started' in KSP.")
    except KeyboardInterrupt:
        print("\n[*] Blue Team: Manual Shutdown Initiated. Terminating C2 Link.")
    except Exception as e:
        print(f"\n[!] SYSTEM CRITICAL: Unexpected failure: {e}")

if __name__ == "__main__":
    run_blue_team()