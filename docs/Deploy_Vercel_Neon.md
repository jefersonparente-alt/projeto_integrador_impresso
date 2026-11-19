# Deploy Simplificado: Vercel + Neon (Apenas 1 Variável!)

O projeto foi simplificado para exigir **apenas UMA única variável** na Vercel: a conexão do banco do Neon. Todo o resto (`DEBUG`, `ALLOWED_HOSTS`, `SECRET_KEY`, `CSRF`) é configurado automaticamente pelo código.

---

## Passo 1: Pegar a URL no Neon
1. No [neon.tech](https://neon.tech/), copie a **Connection String**:
   ```text
   postgresql://neondb_owner:SENHA@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

---

## Passo 2: Rodar as tabelas no Neon (uma única vez pelo terminal)
No seu PowerShell:
```powershell
$env:DATABASE_URL="sua_string_do_neon_aqui"
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py seed_data
```

---

## Passo 3: Configurar na Vercel (Apenas 1 Chave!)
No painel da Vercel (**Settings** $\rightarrow$ **Environment Variables**), adicione apenas:

| Nome da Variável | Valor |
| :--- | :--- |
| **`DATABASE_URL`** | `postgresql://neondb_owner:SENHA@ep-xyz...neon.tech/neondb?sslmode=require` |

*(Não precisa preencher mais nada: `DEBUG`, `ALLOWED_HOSTS` e `SECRET_KEY` já têm valores automáticos prontos).*

---

## Passo 4: Subir para o GitHub e Deploy
```bash
git add .
git commit -m "chore: simplificar configuracao para exigir apenas DATABASE_URL"
git push origin main
```
Pronto! A Vercel fará o deploy automático e o site estará no ar.
