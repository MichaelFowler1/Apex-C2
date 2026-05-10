import time
import krpc
from datetime import datetime

# --- FSW CONFIGURATION ---
POLL_RATE_HZ = 1.0  # System tick rate
ENABLE_AUTONOMOUS_RECOVERY = True

def execute_hums_monitoring():
    """Health and Usage Monitoring System (HUMS) edge node."""
    print("[*] Initializing Vanguard FSW Node...")
    
    try:
        # Bind to the local KSP instance
        conn = krpc.connect(name='Vanguard_FSW_Core')
        vessel = conn.space_center.active_vessel
        
        print(f"[+] C2 Link Established. Bound to asset: {vessel.name}")
        print(f"[*] Operational Mode: {'ACTIVE HEALING' if ENABLE_AUTONOMOUS_RECOVERY else 'MONITOR ONLY'}")
        print("-" * 50)

        # State tracking to prevent log spam during sustained faults
        was_nominal = True 

        while True:
            # 1. Poll Telemetry (Simulating reading from the avionics bus)
            is_sas_active = vessel.control.sas
            altitude = vessel.flight().mean_altitude
            timestamp = datetime.now().strftime("%H:%M:%S")

            # 2. State Evaluation Logic
            if is_sas_active:
                if not was_nominal:
                    # Only print this transition once when we recover
                    print(f"[{timestamp}] [SYS] Stability has been re-established. Resuming nominal operations.")
                    was_nominal = True
                    
                # Standard quiet heartbeat
                print(f"[{timestamp}] [NOMINAL] Alt: {altitude:.0f}m | SAS: ONLINE")
                
            else:
                was_nominal = False
                print(f"\n[{timestamp}] [WARN] FAULT DETECTED: Primary attitude control (SAS) is offline.")
                
                if ENABLE_AUTONOMOUS_RECOVERY:
                    print("[*] Vanguard RTA: Initiating autonomous override...")
                    
                    # Action: Attempt to force the hardware back on
                    vessel.control.sas = True
                    
                    # Wait a fraction of a second for the physical actuators to respond
                    time.sleep(0.2) 
                    
                    # Verification Phase
                    if vessel.control.sas:
                        print("[+] Override successful. Hardware secured.\n")
                    else:
                        print("[!] OVERRIDE FAILED: Contested link or hardware failure. Retrying next cycle...\n")

            # Sleep to maintain the target Hz rate dynamically
            time.sleep(1.0 / POLL_RATE_HZ)

    except krpc.error.NetworkError:
        print("\n[!] FATAL: Could not bind to kRPC server. Is the telemetry bus active?")
    except KeyboardInterrupt:
        print("\n[*] FSW node terminated by operator. Safing system...")
    except Exception as e:
        print(f"\n[!] UNHANDLED EXCEPTION: {e}")

if __name__ == "__main__":
    execute_hums_monitoring()