import krpc
import time
import math
from datetime import datetime

# --- GROUND STATION CONFIGURATION ---
# Using the Mesa South coordinates (Zenith Overlap)
STATION_LAT = -0.000000495  # Targeted Sub-Satellite Latitude
STATION_LON = 68.15246      # Targeted Sub-Satellite Longitude
ELEVATION_MASK = 5.0        # Degrees above horizon required for AOS
SPEED_OF_LIGHT = 299792458  # m/s for latency calculation

def calculate_link():
    try:
        conn = krpc.connect(name='Physical_Pipeline_Core')
        vessel = conn.space_center.active_vessel
        body = vessel.orbit.body
        
        print(f"[*] Pipeline established. Tracking: {vessel.name}")
        print(f"[*] Ground Station set to: {STATION_LAT}, {STATION_LON}")
        print("-" * 50)

        while True:
            # 1. Get Live Satellite Data
            # Note: flight(body.reference_frame) gives us coords relative to the planet center
            sat_lat = vessel.flight().latitude
            sat_lon = vessel.flight().longitude
            sat_alt = vessel.flight().mean_altitude
            
            # 2. Calculate Great Circle Distance (Central Angle)
            # This determines how far around the curve of the planet the sat is
            lat1, lon1 = math.radians(STATION_LAT), math.radians(STATION_LON)
            lat2, lon2 = math.radians(sat_lat), math.radians(sat_lon)
            
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            
            # Haversine formula for angular separation (psi)
            a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
            psi = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            # 3. Calculate Elevation Angle (El)
            # Re = Planet Radius, Rs = Radius to Satellite
            re = body.equatorial_radius
            rs = re + sat_alt
            
            # Geometric Elevation formula
            elevation = math.degrees(math.atan2(rs * math.cos(psi) - re, rs * math.sin(psi)))
            
            # 4. Calculate Range and Latency
            # Slant Range (Direct line-of-sight distance)
            slant_range = math.sqrt(re**2 + rs**2 - 2 * re * rs * math.cos(psi))
            latency = slant_range / SPEED_OF_LIGHT

            # 5. Output Status
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if elevation >= ELEVATION_MASK:
                status = "AOS (ACTIVE)"
                color_code = "[!] "
            else:
                status = "LOS (BLOCKED)"
                color_code = "[*] "

            print(f"{color_code}{timestamp} | El: {elevation:>6.2f} deg | Range: {slant_range/1000:>8.2f} km | Lat: {latency:>8.6f} s | {status}")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[*] Pipeline Terminated.")
    except Exception as e:
        print(f"[!] Pipeline Crash: {e}")

if __name__ == "__main__":
    calculate_link()