# Endurecimento de Deploy (Seguranca e Escala)

## 1. Rate limit na borda (NGINX)

Exemplo simples de limitacao de requests por IP para a API FastAPI:

```nginx
http {
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    server {
        listen 80;
        server_name exemplo.com;

        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;

            proxy_pass http://127.0.0.1:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
```

Ajuste `rate` e `burst` conforme o volume esperado.

## 2. Migracao planejada para PostgreSQL

Passos recomendados:

1. **Criar banco PostgreSQL** (local ou gerenciado) e usuario dedicado.
2. **Gerar esquema** a partir do SQLite atual:
   - Use uma ferramenta como `sqlite3` + `pgloader` ou escreva scripts `CREATE TABLE` equivalentes.
3. **Adaptar a camada de conexao**:
   - Criar uma nova classe `PostgresConnection` com `psycopg2` ou `asyncpg`.
   - Manter interface semelhante a `SQLiteConnection` (`execute`, `fetch_one`, `fetch_all`).
4. **Tornar o backend configuravel** por variavel de ambiente:
   - Ex.: `DB_BACKEND=sqlite|postgres` e `POSTGRES_DSN=...`.
5. **Migrar dados**:
   - Exportar tabelas do SQLite para CSV e importar no Postgres.
6. **Testar em staging** com o bot apontando para Postgres antes de migrar producao.

## 3. Segredos e webhooks

- Definir `ADMIN_API_KEY` e `PAYMENT_WEBHOOK_SECRET` apenas em variaveis de ambiente do servidor.
- No gateway de pagamento, configurar o envio do header `X-Webhook-Signature` com HMAC-SHA256 do corpo usando o mesmo segredo.

Este arquivo e apenas um guia operacional; a logica de autenticacao e HMAC ja esta implementada no codigo da API.