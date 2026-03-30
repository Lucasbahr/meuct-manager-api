def normalize_email(email: str) -> str:
    return (email or "").strip().lower()

