"""Perfis de acesso (valor em users.role)."""

ADMIN_SISTEMA = "ADMIN_SISTEMA"
ADMIN_ACADEMIA = "ADMIN_ACADEMIA"
PROFESSOR = "PROFESSOR"
ALUNO = "ALUNO"

# Legado (migração e tokens antigos)
_LEGACY_ADMIN = "ADMIN"

ALL_ROLES = frozenset(
    {ADMIN_SISTEMA, ADMIN_ACADEMIA, PROFESSOR, ALUNO, _LEGACY_ADMIN}
)


def normalize_role(role: str | None) -> str:
    if not role:
        return ALUNO
    r = role.strip().upper()
    if r == _LEGACY_ADMIN:
        return ADMIN_ACADEMIA
    return r


def is_system_admin(role: str | None) -> bool:
    return normalize_role(role) == ADMIN_SISTEMA


def is_academy_admin(role: str | None) -> bool:
    return normalize_role(role) in (ADMIN_SISTEMA, ADMIN_ACADEMIA)


def is_staff(role: str | None) -> bool:
    """Admin sistema, admin academia ou professor (equipe da academia)."""
    return normalize_role(role) in (ADMIN_SISTEMA, ADMIN_ACADEMIA, PROFESSOR)


def can_manage_academy_entity(role: str | None) -> bool:
    """Criar/editar feed, apagar aluno/usuário, post em nome da academia."""
    return is_academy_admin(role)
