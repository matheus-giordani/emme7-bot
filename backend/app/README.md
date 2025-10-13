# Instructions to run the backend API.

*Disclaimer: this readme is intended solely for testing purposes and is designed for developers who wish to test the backend API outside of Docker.*

Install dependencies:

```
pip install -r requirements.txt
```

Also install dotenv:
```
pip install python-dotenv==1.0.1
```

Make sure you have the .env file with the credentials in the root of the repository. Change all of the variables containing "HOST" to localhost.

The backend now expects the following Evolution API variables to be configured:

- `EVOLUTION_API_URL`: URL base do Evolution (ex.: `http://localhost:8080`).
- `EVOLUTION_API_KEY`: chave `apikey` global configurada no Evolution.
- `EVOLUTION_INSTANCE_NAME`: nome da instância/sessão usada para enviar mensagens.
- `EVOLUTION_DEFAULT_DENTIST_PHONE` (opcional): número padrão vinculado à instância, usado para agrupar conversas.
- `EVOLUTION_SESSION_PHONE_MAP` (opcional): mapeamento `sessao=numero` separado por vírgula para suportar múltiplas instâncias.

Then,

```
python3 app.py --host 0.0.0.0 --port 8000
```

The api will be available at http://localhost:8000/docs
