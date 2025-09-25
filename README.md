# 📝 Task Manager

Gerenciador de Tarefas simples com autenticação de usuários.  
Este projeto é "fullstack + infra" e tem como objetivo estudar **Angular, Node, Python, DynamoDB, AWS (Lambda + API Gateway), OpenAPI/Swagger e Terraform**.

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
- OpenAPI & Swagger (documentação)

### Infraestrutura
- Terraform (Infra as Code)
- AWS API Gateway
- AWS Lambda
- DynamoDB
- Pipelines (CI/CD)

---

## 📌 Funcionalidades

- Cadastro de usuário (signup)
- Login de usuário (jwt token)
- CRUD de tarefas:
  - Criar
  - Listar
  - Editar
  - Excluir
- Configuração de perfil de usuário
- Logout

---

## 🛠 Estrutura do Projeto

# User Service - AWS Lambda + DynamoDB + API Gateway

```markdown
# User Service - AWS Lambda + DynamoDB + API Gateway

## Estrutura do projeto
- `lambda_function.py` → função Lambda (POST/GET/PUT/DELETE de usuários)
- `deploy.ps1` → script de deploy automático via AWS CLI

## Como fazer deploy
1. Ajuste seu código no `lambda_function.py`.
2. Rode o script de deploy: .\deploy.ps1
   
3. A função `UserServiceLambda` será atualizada na AWS automaticamente.

## Pré-requisitos
- AWS CLI configurada (`aws configure`)
- Python 3.9+
- PowerShell (Windows) ou bash (Linux/Mac com `deploy.sh`)
```
