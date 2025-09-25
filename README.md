# 📝 Task Manager

Gerenciador de Tarefas simples com autenticação de usuários.
Este projeto é "fullstack + infra" e tem como objetivo estudar **Angular, Python (AWS Lambda), API Gateway, DynamoDB, OpenAPI/Swagger e Terraform**.

---

## 🚀 Tecnologias Utilizadas

### Frontend
- Angular
- Node.js
- TypeScript
- HTML & CSS

### Backend
- Python (AWS Lambda)
- API REST (API Gateway)
- Lambda Authorizer (middleware JWT)
- OpenAPI & Swagger (documentação interativa via Swagger UI)

### Infraestrutura
- Terraform (Infra as Code)
- AWS API Gateway
- AWS Lambda
- DynamoDB
- IAM (roles & permissions)
- CloudWatch (logs e monitoramento)
- Pipelines (CI/CD)

---

## 📌 Funcionalidades

- **Usuários**
  - Cadastro (signup)
  - Login (gera JWT válido)
  - Reset de senha (request, validate, confirm)
  - CRUD de usuário (GET/POST/PUT/DELETE)
- **Tarefas**
  - Criar
  - Listar
  - Editar
  - Excluir
- **Autenticação & Segurança**
  - JWT Token (gerado no login)
  - Lambda Authorizer → protege rotas (`/users`, `/tasks`)
  - Apenas `/auth/login` e `/auth/reset/*` são públicas
- **Documentação**
  - Swagger UI integrado (`docs/ui/index.html`)
  - Especificação OpenAPI (`docs/swagger.yaml`)

---

## 🛠 Estrutura do Projeto

```
TASK-MANAGER/
 ┣ auth/               # Lambda de autenticação
 ┃ ┣ lambda_function.py
 ┃ ┗ deploy.ps1
 ┣ user-service/       # CRUD de usuários
 ┃ ┣ lambda_function.py
 ┃ ┗ deploy.ps1
 ┣ task-service/       # CRUD de tarefas
 ┃ ┣ lambda_function.py
 ┃ ┗ deploy.ps1
 ┣ docs/               # Documentação da API
 ┃ ┣ swagger.yaml      # Especificação OpenAPI
 ┃ ┗ ui/               # Swagger UI (executar index.html)
 ┃   ┗ index.html
 ┗ README.md
```

---

## 🔐 Fluxo de Autenticação

1. `POST /auth/login` → recebe email/senha → retorna JWT.
2. `Authorization: Bearer <jwt>` → obrigatório para `/users` e `/tasks`.
3. API Gateway bloqueia automaticamente chamadas sem ou com token inválido (`401/403`).
4. Reset de senha:
   - `POST /auth/reset/request` → envia código
   - `POST /auth/reset/validate` → valida código
   - `POST /auth/reset/confirm` → troca senha

---

## 📖 Swagger (Documentação)

### Como acessar:
1. Vá até a pasta `docs/ui`:
   ```bash
   cd docs/ui
   python -m http.server 8080
   ```

2. Acesse no navegador:
   👉 [http://localhost:8080/index.html](http://localhost:8080/index.html)

A API será carregada usando a especificação do `swagger.yaml`.

---

## 🚀 Deploy dos serviços

Cada serviço (auth, user, task) possui seu script `deploy.ps1` para automatizar o upload da Lambda:

```powershell
# Exemplo: deployar User Service
cd user-service
.\deploy.ps1
```

### Pré-requisitos:
- AWS CLI configurada (`aws configure`)
- Python 3.9+
- PowerShell (Windows) ou bash (Linux/Mac com `deploy.sh`)