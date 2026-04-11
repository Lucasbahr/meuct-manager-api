"""XP sources and badge keys (stored in DB / xp_logs)."""

XP_PER_TRAINING = 10
XP_PER_GRADUATION = 100

XP_SOURCE_TRAINING = "training"
XP_SOURCE_GRADUATION = "graduation"
XP_SOURCE_STREAK = "streak"

BADGE_FIRST_GRADUATION = "FIRST_GRADUATION"
BADGE_STREAK_7 = "STREAK_7"
BADGE_WARRIOR_100 = "WARRIOR_100"

LEVEL_XP_DIVISOR = 100


def calculate_level(total_xp: int) -> int:
    return max(0, total_xp // LEVEL_XP_DIVISOR)
