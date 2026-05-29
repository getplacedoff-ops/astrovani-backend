import os

# --- Render and Database Configuration ---
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:[YOUR-PASSWORD]@db.eathyedcvnfhfybuejks.supabase.co:5432/postgres"
)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://eathyedcvnfhfybuejks.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_eQOf60_7U44uPjLMjkYojw_ldus4Oor")

# --- Cloudflare R2 Credentials ---
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "CF_ACCOUNT_ID_PLACEHOLDER")
CLOUDFLARE_R2_ACCESS_KEY = os.getenv("CLOUDFLARE_R2_ACCESS_KEY", "CF_ACCESS_KEY_PLACEHOLDER")
CLOUDFLARE_R2_SECRET_KEY = os.getenv("CLOUDFLARE_R2_SECRET_KEY", "CF_SECRET_KEY_PLACEHOLDER")
CLOUDFLARE_R2_BUCKET_NAME = os.getenv("CLOUDFLARE_R2_BUCKET_NAME", "astrovani-premium")

# --- AI APIs Keys ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "GROQ_API_KEY_PLACEHOLDER")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "GEMINI_API_KEY_PLACEHOLDER")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "NVIDIA_API_KEY_PLACEHOLDER")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "OPENROUTER_API_KEY_PLACEHOLDER")

# --- Bypass Secrets ---
# Master bypass key that validates strictly server-side
CEO_BYPASS_CODE = "CEO-25-07-desk"
