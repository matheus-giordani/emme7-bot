## Executar com Docker Compose

1. Ajuste as variáveis no arquivo `.env` (credenciais do Evolution API e os números `STORE_INFO_FORWARD_NUMBER`/`STORE_RESPONSIBLE_NUMBER` usados pelo atendimento da loja).
2. Construa e suba os serviços:

   ```bash
   docker compose up --build
   ```

   Isso inicia:
   - `evolution_api`: container oficial do Evolution API exposto em `http://localhost:8080`.
   - `backend`: nossa API FastAPI disponível em `http://localhost:8000` (recebe webhooks em `/evolution/webhook`).
   - `consumer`: worker que lê mensagens do Redis e encaminha para o backend.
   - `redis` e `evolution-postgres`: dependências de dados.

3. Após o primeiro start, acesse o Evolution Manager (`http://localhost:8080/manager`) para criar/configurar a instância `giordani` (ou o nome que definir em `EVOLUTION_INSTANCE_NAME`).
4. Tudo pronto: mensagens recebidas pelo Evolution API serão encaminhadas para o backend e processadas via Redis/consumidor.

Use `docker compose down` para encerrar os serviços.
