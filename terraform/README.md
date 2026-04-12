# Terraform (GCP)

## Mídia por tenant (academia)

- **Um bucket por ambiente** (`meuct-api-media-<env>-…`), compartilhado por todas as academias.
- **Isolamento lógico**: objetos sob `gs://<bucket>/<gcs_tenant_prefix>/<gym_id>/…` (padrão `tenants/42/students/...`).
- A API grava fotos de alunos e feed com esse prefixo; caminhos antigos sem prefixo continuam válidos se já estiverem no banco.
- **`GCS_PROVISION_TENANT_ON_CREATE`**: ao criar um gym (`POST /gyms`), a API pode criar marcadores (`students/.keep`, `feed_items/.keep`, `marketplace/.keep`) para materializar a árvore no GCS ou no disco local.

Variáveis: `gcs_tenant_prefix`, `gcs_provision_tenant_on_create` em `envs/*/variables.tf`.

### Bucket dedicado por academia (opcional)

O Terraform **não** cria buckets dinamicamente por ID de gym (IDs vêm da aplicação em runtime). Para um bucket por cliente você pode:

1. **Módulo + `for_each`** com uma lista fixa de `gym_id` conhecidos no momento do apply, ou  
2. **Provisionamento fora do Terraform**: Cloud Function / job que chama a API de Storage com uma service account com `storage.buckets.create`, e gravar o nome do bucket na tabela `gyms` (exige migração e mudanças na API de upload).

Evite conceder `roles/storage.admin` no projeto inteiro à SA do Cloud Run salvo estratégia clara de hardening.

## Banco de dados por tenant

Hoje a aplicação usa **um único `DATABASE_URL`** (ex.: Neon) com multitenancy por `gym_id`.  
Criar **schema ou instância por academia** implica: roteamento de conexão por request, migrações por tenant e secrets por URL — isso fica fora deste Terraform até haver desenho de produto.

Opções comuns: **Neon branches** (uma URL por academia na tabela `gyms`), **Cloud SQL** com DB por cliente + connection pooler, ou **RLS no Postgres** mantendo um único banco.
