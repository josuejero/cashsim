# Streamlit Secrets: Exact Format & Where to Put Them

This app reads Google Sheets via a **Google Cloud service account**.
Define your secrets locally at:

- **Project-specific**: `.streamlit/secrets.toml` (recommended for local dev)
- **Global (user)**: `~/.streamlit/secrets.toml` (macOS/Linux) or `%USERPROFILE%/.streamlit/secrets.toml` (Windows)

> Streamlit merges global + project secrets; project wins on key collisions. Do **not** commit secrets to git. Add `.streamlit/` to `.gitignore`.  
> Source: Streamlit secrets docs. :contentReference[oaicite:1]{index=1}

---

## Minimal working `secrets.toml`

```toml
# .streamlit/secrets.toml

# Optional: you can keep unrelated keys here too (e.g., OpenAI_key = "…")

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
# Keep the literal \n line breaks in the key value:
private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhki…\n-----END PRIVATE KEY-----\n"
client_email = "svc-account@your-project-id.iam.gserviceaccount.com"
client_id = "123456789012345678901"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/svc-account%40your-project-id.iam.gserviceaccount.com"
