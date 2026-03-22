# 🚀 MEUCT Manager API

API para gerenciamento de alunos e check-ins de academia de luta.

---

## 🧱 Tecnologias

* FastAPI
* SQLAlchemy
* Alembic (migrations)
* PostgreSQL / SQLite
* Docker

---

## 📦 Estrutura do projeto

```
app/
├── models/
├── schemas/
├── services/
├── routes/
├── db/
├── core/
├── scripts/
│   └── create_admin.py
```

---

## ⚙️ Configuração de ambiente

Crie um arquivo `.env`:

```
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=meuct-secret
ALGORITHM=HS256

ADMIN_EMAIL=admin@meuct.com
ADMIN_PASSWORD=admin123
```

---

## ▶️ Rodando localmente

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Acesse:

👉 http://localhost:8000/docs

---

## 🐳 Rodando com Docker

```bash
docker compose up --build
```

---

## 🧠 Migrations com Alembic

Este projeto utiliza **Alembic** para versionamento do banco de dados.

### 🔹 O que são migrations?

Migrations são scripts que controlam a evolução do banco de dados ao longo do tempo.

---

### 🔹 Criar uma migration

Sempre que alterar um model:

```bash
alembic revision --autogenerate -m "descrição da mudança"
```

---

### 🔹 Aplicar migrations

```bash
alembic upgrade head
```

---

### 🔹 Voltar versão (rollback)

```bash
alembic downgrade -1
```

---

### 🔹 Fluxo recomendado

1. Alterar model
2. Gerar migration
3. Revisar o arquivo gerado
4. Aplicar migration

---

### ⚠️ Importante

* Nunca usar `Base.metadata.create_all()` em produção
* Sempre usar Alembic para manter consistência do banco
* Sempre rodar migrations antes de subir a aplicação

---

## 🌱 Seed automático

O sistema cria automaticamente um usuário admin ao iniciar:

```bash
python -m app.scripts.create_admin
```

Ou via Docker (automático).

---

## 🔐 Autenticação

* JWT Token
* Verificação de email
* Reset de senha

---

## 📌 Endpoints principais

* `/auth`
* `/students`
* `/checkin`

---

## 🚀 Deploy

Este projeto está preparado para deploy com Docker.

Exemplo (VPS):

```bash
docker compose up -d --build
```

---

## ⚙️ CI/CD (GitHub Actions)

A pipeline executa:

* Instala dependências
* Valida código
* Prepara build

Arquivo:

```bash
.github/workflows/ci.yml
```

---

## 👊 Autor

Projeto desenvolvido para evolução de arquitetura backend profissional.
