# Test Credentials - EstateWise

## Admin Account (seed automatico)
- **Email**: `admin@estatewise.it`
- **Password**: `admin123`
- **Ruolo**: supervisore
- **Login endpoint**: `POST /api/v1/auth/login` (form-urlencoded, campo `username` = email)

## API Key Esterne
- **EMERGENT_LLM_KEY** in `/app/backend/.env` (universal key per OpenAI/Anthropic/Gemini)
- **OLLAMA_URL** = `http://localhost:11434` (in dev locale Ollama non avviato; in produzione gira nel container Docker)

## Note testing
- Tutti gli endpoint API sono prefissati con `/api/v1`
- Le date sono in formato ISO `YYYY-MM-DD`
- Il login restituisce `access_token` e `refresh_token`
