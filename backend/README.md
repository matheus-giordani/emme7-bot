## Atendimento da loja de móveis

O backend agora foi adaptado para atuar como recepção virtual de uma loja de móveis. O objetivo é coletar dados do cliente, registrar o interesse e avisar imediatamente a equipe interna pelo WhatsApp através do Evolution API.

### 1. Variáveis de ambiente principais
Configure o arquivo `.env` (ou variáveis do container) com:

- `EVOLUTION_API_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE_NAME`: credenciais da instância Evolution responsável por enviar as mensagens.
- `STORE_NAME`: nome exibido pelo assistente virtual (ex.: *Emme7 Móveis Planejados*).
- `STORE_INFO_FORWARD_NUMBER`: número que receberá o resumo do lead (apenas dígitos, com DDI/DDI).
- `STORE_RESPONSIBLE_NUMBER`: número do consultor responsável que deverá contatar o cliente.
- `STORE_INFO_FORWARD_NUMBER` e `STORE_RESPONSIBLE_NUMBER` devem estar autorizados na instância do Evolution API configurada.
- `DATABASE_URL`, `REDIS_HOST`, `REDIS_PASSWORD` e demais variáveis já existentes no projeto continuam necessárias para persistência e filas.

### 2. Subir os serviços
Após ajustar as variáveis, execute normalmente (`make run`, `python -m app.app`, ou via Docker Compose). O seed automático cria alguns exemplos de leads em `customer_leads` apenas para ambiente local.

### 3. Fluxo de atendimento
1. O cliente envia mensagem para o WhatsApp da loja (instância Evolution).
2. O webhook grava a interação no Redis e o consumidor encaminha o lote ao backend.
3. O agente "sales" conduz a conversa, coleta nome, telefone, cidade/bairro, produto desejado, orçamento e melhor horário para contato.
4. Quando os dados essenciais estão completos, o agente chama a tool `register_lead`, que:
   - Persiste as informações no banco (`customer_leads`).
   - Envia um resumo formatado ao número configurado em `STORE_INFO_FORWARD_NUMBER`.
   - Notifica o responsável configurado em `STORE_RESPONSIBLE_NUMBER` para assumir o atendimento.
5. O assistente confirma ao cliente que o consultor entrará em contato e pode compartilhar o telefone do responsável, disponível no contexto.

### 4. Tabelas relevantes
- `customer_leads`: registro dos interessados (nome, telefone, e-mail, cidade, interesse, observações, etc.).
- `chats` e `chats_messages`: histórico das conversas para dar contexto às próximas interações.

### 5. Ajustes adicionais
- Atualize o prompt ou o tom de voz editando `src/agents/prompts/sales_prompt.toml`.
- Novos campos desejados no lead podem ser adicionados ao schema `CustomerLead` e à tool `register_lead`.
