import re
from fastapi import HTTPException, status

# Profanity word lists across languages (English, Telugu, and phonetic Tenglish)
PROFANITY_PATTERNS = re.compile(
    r"\b(bastard|bitch|fucking|fuck|asshole|loda|luda|chutiya|randi|dengu|lanja|puku|modda|sulla|gudha|dengey|dengay|dengali|lanjodka)\b",
    re.IGNORECASE
)

# Crisis keywords mapping (suicide, self-harm, terminal illness, critical illness, and depression)
CRISIS_PATTERNS = re.compile(
    r"(chavali|chastanu|kill myself|suicide|chavu|atmahathya|die|cancer outcome|die of disease|harm myself|end my life|slash wrists|hanging|critical illness|terminal|kill me|depressed|depression|mental crisis|heart attack|illness outcome|hospitalize)",
    re.IGNORECASE
)

# Legal outcome prediction prevention
LEGAL_PATTERNS = re.compile(
    r"\b(lawsuit|court verdict|judge decision|litigation|criminal case|jail term|prison sentence|court case|hearing result|legal outcome|litigate|sue page|suing)\b",
    re.IGNORECASE
)

# Financial gambling ticker restrictions
TICKER_PATTERNS = re.compile(
    r"\b(buy stock|exact ticker|btc price|dogecoin|lottery numbers|jackpot numbers|gamble option|which stock to buy|crypto investment|lottery ticket|stock tips|stock advice|shares|portfolio|gamble tips|invest in)\b",
    re.IGNORECASE
)

def run_security_pipeline(raw_message: str) -> str:
    """
    Verifies that the user input is clean and compliant with ethical boundaries.
    Throws HTTPException if safety filters are triggered.
    """
    message_lower = raw_message.lower()

    # 1. Profanity Filter Check
    if PROFANITY_PATTERNS.search(message_lower):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AstroVani maintains a respectful, spiritual consulting environment. Please refrain from using offensive language."
        )

    # 2. Medical & Psychological Crisis Check
    if CRISIS_PATTERNS.search(message_lower):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "AstroVani offers spiritual astrological guidance, which must never replace professional medical diagnostics or psychological care. "
                "If you are experiencing distress, please reach out to: Tele MANAS (14416 / 1800-891-4416) or the National Emergency Number (112) for immediate support."
            )
        )

    # 3. Legal Action Outcome Checks
    if LEGAL_PATTERNS.search(message_lower):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Astrological transits indicate planetary cycles of stability and challenge, but AstroVani cannot predict judicial rulings, "
                "lawsuit verdicts, or active litigation cases. Please consult a qualified legal professional."
            )
        )

    # 4. Financial Gambling spec blocks
    if TICKER_PATTERNS.search(message_lower):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "AstroVani does not provide specific stock ticker tips, crypto forecasts, or lottery predictions. "
                "You may inquire generally about career transition windows, wealth transits, or favorable planetary financial cycles."
            )
        )

    return raw_message
