"""
Migração legada: `students.modalidade` / `students.graduacao` → `student_modalities`.

O caminho recomendado é **Alembic** (inclui criação de tabelas, seed e remoção das colunas):

    alembic upgrade head

Este módulo existe para documentação e para ambientes onde se prefere inspecionar o estado
antes de aplicar a revisão `h8i9j0k1l2m3`.
"""

from sqlalchemy import inspect, text

from app.db.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        bind = db.get_bind()
        insp = inspect(bind)
        if not insp.has_table("students"):
            print("Tabela students não existe; nada a fazer.")
            return
        cols = {c["name"] for c in insp.get_columns("students")}
        if "modalidade" not in cols:
            print(
                "Colunas legadas já removidas. Use apenas `alembic upgrade head` "
                "para manter o schema atualizado."
            )
            return
        print(
            "Detectadas colunas `modalidade` / `graduacao` em students.\n"
            "Execute: alembic upgrade head\n"
            "(revisão h8i9j0k1l2m3 — modalidades relacionais)"
        )
        # Contagem opcional
        n = db.execute(text("SELECT COUNT(*) FROM students")).scalar()
        print(f"Alunos na base: {n}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
