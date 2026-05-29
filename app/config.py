import os

# --- Render and Database Configuration ---
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:[YOUR-PASSWORD]@db.eathyedcvnfhfybuejks.supabase.co:5432/postgres"
)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://eathyedcvnfhfybuejks.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_eQOf60_7U44uPjLMjkYojw_ldus4Oor")

# --- Cloudflare R2 Credentials ---
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "c3a459d4c21803b57736174da69b27c4")
CLOUDFLARE_R2_ACCESS_KEY = os.getenv("CLOUDFLARE_R2_ACCESS_KEY", "11b34043b4a3d7114c9d5f6824208196")
CLOUDFLARE_R2_SECRET_KEY = os.getenv("CLOUDFLARE_R2_SECRET_KEY", "44e75ba72d557749a19365b0f1f411f5a0792e2a563213c9830e0db292afa49f")
CLOUDFLARE_R2_BUCKET_NAME = os.getenv("CLOUDFLARE_R2_BUCKET_NAME", "astrovani-premium")

# --- AI APIs Keys ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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.")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyA0FeaBF5qMvtHVprLZUKMc0iDALCIf3Uk")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "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")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

# --- Bypass Secrets ---
# Master bypass key that validates strictly server-side
CEO_BYPASS_CODE = "CEO-25-07-desk"
