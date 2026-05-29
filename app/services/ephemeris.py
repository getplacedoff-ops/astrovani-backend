import datetime
import math

try:
    import swisseph as swe
    SWISSEPH_AVAILABLE = True
except ImportError:
    SWISSEPH_AVAILABLE = False
    print("[Ephemeris] swisseph C bindings not found locally. Running in Mock/Fallback calculation mode.")

# Traditional Name Mappings
TITHIS = [
    "Prathama", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashti", "Saptami", "Ashtami",
    "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Pournami",
    "Prathama", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashti", "Saptami", "Ashtami",
    "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya"
]

VARAS = ["Adivaram (Sunday)", "Somavaram (Monday)", "Mangalavaram (Tuesday)", "Budhavaram (Wednesday)", "Guruvaram (Thursday)", "Sukravaram (Friday)", "Sanivaram (Saturday)"]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha",
    "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Visakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

YOGAS = [
    "Vishkumbha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma", "Dhriti", "Shula",
    "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyan", "Parigha",
    "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti"
]

KARANAS = [
    "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti",
    "Shakuni", "Chatushpada", "Naga", "Kintughna"
]

def calculate_julian_day(dt: datetime.datetime) -> float:
    """Converts a standard datetime object into Julian Day."""
    if SWISSEPH_AVAILABLE:
        # Calculate Julian Day using Swiss Ephemeris
        utc_time = dt - dt.utcoffset() if dt.utcoffset() else dt
        # swe.julday takes (year, month, day, hour_decimal)
        hour_decimal = utc_time.hour + utc_time.minute/60.0 + utc_time.second/3600.0
        return swe.julday(utc_time.year, utc_time.month, utc_time.day, hour_decimal)
    else:
        # Fallback simplified Julian Day formula
        y, m, d = dt.year, dt.month, dt.day
        hour_decimal = dt.hour + dt.minute/60.0 + dt.second/3600.0
        if m <= 2:
            y -= 1
            m += 12
        A = math.floor(y / 100)
        B = 2 - A + math.floor(A / 4)
        jd = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + (hour_decimal / 24.0) + B - 1524.5
        return jd

def get_panchangam(birth_datetime: datetime.datetime, lat: float, lng: float) -> dict:
    """
    Computes Telugu Panchangam elements: Tithi, Vara, Nakshatra, Yoga, and Karana.
    Applies Lahiri Ayanamsa.
    """
    # 1. Determine Vara (Day of week is independent of ephemeris library)
    # python weekday() returns 0 for Monday, 6 for Sunday
    # Our VARAS list starts with Sunday (Vara index 0 = Sunday)
    weekday_idx = (birth_datetime.weekday() + 1) % 7
    vara = VARAS[weekday_idx]

    # Calculate Julian Day
    jd = calculate_julian_day(birth_datetime)

    if SWISSEPH_AVAILABLE:
        try:
            # Set sidereal mode using Lahiri Ayanamsa
            swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
            
            # Fetch ayanamsa offset value
            ayanamsa_offset = swe.get_ayanamsa_ut(jd)
            
            # Moon position calculation (sidereal)
            moon_res, _ = swe.calc_ut(jd, swe.MOON)
            moon_lon = (moon_res[0] - ayanamsa_offset) % 360.0
            
            # Sun position calculation (sidereal)
            sun_res, _ = swe.calc_ut(jd, swe.SUN)
            sun_lon = (sun_res[0] - ayanamsa_offset) % 360.0
            
        except Exception as e:
            print(f"[Ephemeris] Error calling swe.calc_ut: {e}. Falling back to geometric estimates.")
            moon_lon = (13.17639 * jd) % 360.0 # simplified moon movement
            sun_lon = (0.9856 * jd) % 360.0
    else:
        # Geometric estimation helper for environments without C-compilers (local testing)
        # Approximate positions based on cycles starting at a known J2000 epoch
        days_since_j2000 = jd - 2451545.0
        # Average movement speeds
        moon_lon = (125.08 + 13.176396 * days_since_j2000) % 360.0
        sun_lon = (280.46 + 0.985647 * days_since_j2000) % 360.0

    # 2. Compute Tithi: moon_lon - sun_lon relative distance (normalized)
    diff = (moon_lon - sun_lon) % 360.0
    tithi_index = int(diff // 12.0)
    tithi = TITHIS[min(tithi_index, 29)]

    # 3. Compute Nakshatra: Moon position along 27 segment division
    nakshatra_index = int(moon_lon // (360.0 / 27.0))
    nakshatra = NAKSHATRAS[min(nakshatra_index, 26)]

    # 4. Compute Yoga: (Moon longitude + Sun longitude)
    yoga_sum = (moon_lon + sun_lon) % 360.0
    yoga_index = int(yoga_sum // (360.0 / 27.0))
    yoga = YOGAS[min(yoga_index, 26)]

    # 5. Compute Karana (Half of a Tithi - 6 degrees)
    # Tithi goes from 0 to 30. Each tithi has 2 Karanas.
    # Total of 60 Karanas in a lunar month.
    karana_val = int(diff // 6.0)
    
    # Map karana val index into traditional names list
    if karana_val == 0:
        karana = "Kintughna"
    elif karana_val >= 57:
        # Final karanas are fixed
        fixed_karanas = {57: "Shakuni", 58: "Chatushpada", 59: "Naga"}
        karana = fixed_karanas.get(karana_val, "Bava")
    else:
        # Middle Karanas repeat in cycles of 7
        karana_idx = (karana_val - 1) % 7
        karana = KARANAS[karana_idx]

    # Calculate auspicious hours (Hora)
    auspicious_hours = {
        "amrit_vela": (birth_datetime.replace(hour=4, minute=30, second=0)).strftime("%H:%M"),
        "brahma_muhurta": (birth_datetime.replace(hour=5, minute=12, second=0)).strftime("%H:%M"),
        "rahu_kalam": "15:00 - 16:30", # Simplified baseline
        "yamagandam": "09:00 - 10:30"
    }

    return {
        "ayanamsa": "Lahiri",
        "positions": {
            "moon_longitude": round(moon_lon, 4),
            "sun_longitude": round(sun_lon, 4),
            "ayanamsa_value": round(swe.get_ayanamsa_ut(jd), 4) if SWISSEPH_AVAILABLE else 24.0
        },
        "panchangam": {
            "tithi": tithi,
            "vara": vara,
            "nakshatra": nakshatra,
            "yoga": yoga,
            "karana": karana
        },
        "auspicious_timings": auspicious_hours
    }
