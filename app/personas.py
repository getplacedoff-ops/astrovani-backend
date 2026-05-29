import random
import hashlib

# Curated arrays representing traditional regional identities
PREFIXES = ["Pandit", "Siddhanti", "Panthulu", "Purohit", "Acharya"]

FIRST_NAMES = [
    "Rama Rao", "Krishna Prasad", "Venkatraman", "Srinivasa Murthy", 
    "Satyanarayana", "Narayana Sastry", "Viswanatha", "Gopala Krishna", 
    "Subrahmanyam", "Raghavendra", "Anantha Ram", "Adinarayana", 
    "Venkateswara", "Ramachandra", "Sridhara", "Madhusudhana"
]

SURNAMES = [
    "Sharma", "Sastry", "Somayajulu", "Avadhani", "Josyula", 
    "Bhatla", "Siddhanta", "Raju", "Vyas", "Charyulu"
]

def generate_astrologer_pool():
    """
    Generates a deterministic pool of 99 realistic, culturally aligned Telugu astrologer personas.
    Applies exclusions (e.g. Acharya + Siddhanta title clashes).
    """
    pool = []
    # Use deterministic logic to fill exactly 99 spots without duplicates
    random_gen = random.Random(42) # Fixed seed for consistency across backend instantiations
    
    while len(pool) < 99:
        prefix = random_gen.choice(PREFIXES)
        first_name = random_gen.choice(FIRST_NAMES)
        surname = random_gen.choice(SURNAMES)
        
        # Rule Exclusions:
        # Avoid title conflicts (e.g., Acharya as prefix and Siddhanta/Charyulu title suffixes)
        if prefix == "Acharya" and surname in ["Siddhanta", "Charyulu"]:
            continue
        if prefix == "Siddhanti" and surname == "Siddhanta":
            continue
        if "Sastry" in first_name and surname == "Sastry":
            continue

        full_name = f"{first_name} {surname}"
        persona = {"name": full_name, "title": prefix}
        
        if persona not in pool:
            pool.append(persona)
            
    return pool

ASTROLOGER_POOL = generate_astrologer_pool()

def get_persona_for_session(session_id_str: str) -> dict:
    """
    Returns a consistent persona for a given chat session UUID string.
    Ensures that the same chat session always talks to the same astrologer.
    """
    # Hash session_id to get a numeric offset into the 99-element pool
    hash_val = int(hashlib.md5(session_id_str.encode("utf-8")).hexdigest(), 16)
    idx = hash_val % len(ASTROLOGER_POOL)
    return ASTROLOGER_POOL[idx]
