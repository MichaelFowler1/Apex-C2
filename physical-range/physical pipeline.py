import math
import time
from datetime import datetime
import krpc

# --- RANGE CONFIGURATION ---
STATION_LAT = -0.000000495  # Mesa South Target (Zenith Overlap)
STATION_LON = 68.15246
ELEVATION_MASK_DEG = 5.0    # Minimum horizon angle for AOS
C = 299792458               # Speed of light (m/s)
POLL_RATE_HZ = 1.0

def get_link_metrics(planet_radius, sat_alt, sat_lat, sat_lon):
    """Calculates instantaneous elevation and latency between the ground station and asset."""
    lat1, lon1 = math.radians(STATION_LAT), math.radians(STATION_LON)
    lat2, lon2 = math.radians(sat_lat), math.radians(sat_lon)
    
    # Haversine angular separation (psi)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    psi = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Orbital geometry
    rs = planet_radius + sat_alt
    
    elevation = math.degrees(math.atan2(rs * math.cos(psi) - planet_radius, rs * math.sin(psi)))
    slant_range = math.sqrt(planet_radius**2 + rs**2 - 2 * planet_radius * rs * math.cos(psi))
    latency = slant_range / C
    
    return elevation, slant_range, latency

def monitor_physical_pipeline():
    print("[*] Initializing Physical Pipeline (LOS/AOS Gatekeeper)...")
    
    try:
        # 1. Establish the C2 Link
        conn = krpc.connect(name='Physical_Range_Tracker')
        vessel = conn.space_center.active_vessel
        body = vessel.orbit.body
        planet_radius = body.equatorial_radius
        
        print(f"[+] RF Link Established. Tracking target: {vessel.name}")
        print(f"[*] Ground Station locked at coords: {STATION_LAT}, {STATION_LON}")
        print("-" * 70)
        
        # 2. Establish Telemetry Streams (Reduces RPC overhead)
        flight = vessel.flight(body.reference_frame)
        lat_stream = conn.add_stream(getattr, flight, 'latitude')
        lon_stream = conn.add_stream(getattr, flight, 'longitude')
        alt_stream = conn.add_stream(getattr, flight, 'mean_altitude')

        # Print a clean table header
        print(f" {'SYS TIME':<10} | {'ELEVATION':<11} | {'SLANT RANGE':<12} | {'LATENCY':<10} | {'LINK STATUS'}")
        
        # 3. Main Tracking Loop
        while True:
            elevation, slant_range, latency = get_link_metrics(
                planet_radius, 
                alt_stream(), 
                lat_stream(), 
                lon_stream()
            )
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if elevation >= ELEVATION_MASK_DEG:
                status = "[ ACTIVE AOS ]"
            else:
                status = "[ LOS BLOCKED ]"

            # Formatted syslog for a clean, non-jittery terminal display
            print(f" {timestamp:<10} |  {elevation:>6.2f} deg  |  {slant_range/1000:>7.2f} km  |  {latency:>6.4f} s  | {status}")
            
            time.sleep(1.0 / POLL_RATE_HZ)

    except krpc.error.NetworkError:
        print("\n[!] FATAL: Could not connect to telemetry bus. Is kRPC running?")
    except KeyboardInterrupt:
        print("\n[*] Range Tracker offline. Link severed by operator.")
    except Exception as e:
        print(f"\n[!] SYSTEM CRITICAL: Pipeline collapsed: {e}")
    finally:
        # 4. Graceful Cleanup
        # Prevents ghost streams from lingering on the KSP server and causing memory leaks
        try:
            lat_stream.remove()
            lon_stream.remove()
            alt_stream.remove()
            conn.close()
        except NameError:
            pass

if __name__ == "__main__":
    monitor_physical_pipeline()