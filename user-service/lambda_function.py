import json
import uuid
import time
import boto3
import hashlib

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = "AppData"
table = dynamodb.Table(TABLE_NAME)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def lambda_handler(event, context):
    try:
        method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")

        if method == "POST":
            return create_user(event)
        elif method == "GET":
            return get_user(event)
        elif method == "PUT":
            return update_user(event)
        elif method == "DELETE":
            return delete_user(event)
        else:
            return {
                "statusCode": 405,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Método {method} não permitido"})
            }

    except Exception as e:
        print("Erro geral:", str(e))
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Erro interno do servidor"})
        }

# -------------------- Métodos -------------------- #
def create_user(event):
    body = json.loads(event.get("body", "{}"))
    name, email, password = body.get("name"), body.get("email"), body.get("password")

    if not all([name, email, password]):
        return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Campos obrigatórios: name, email e password"})}

    user_id = str(uuid.uuid4())
    item = {
        "PK": f"USER#{user_id}",
        "SK": "PROFILE",
        "name": name,
        "email": email,
        "password": hash_password(password),
        "createdAt": int(time.time() * 1000),
    }
    table.put_item(Item=item)
    return {"statusCode": 201, "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"userId": user_id, "name": name, "email": email})}

def get_user(event):
    params = event.get("queryStringParameters") or {}
    user_id = params.get("id")
    if not user_id:
        return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Parametro 'id' é obrigatório"})}

    resp = table.get_item(Key={"PK": f"USER#{user_id}", "SK": "PROFILE"})
    if "Item" not in resp:
        return {"statusCode": 404, "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Usuário não encontrado"})}

    user = resp["Item"]
    return {"statusCode": 200, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(user)}

def update_user(event):
    try:
        body = json.loads(event.get("body", "{}"))
        user_id, name, email = body.get("userId"), body.get("name"), body.get("email")

        if not user_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Campo 'userId' obrigatório"})}

        # Pega o usuário atual
        key = {"PK": f"USER#{user_id}", "SK": "PROFILE"}
        resp = table.get_item(Key=key)
        if "Item" not in resp:
            return {"statusCode": 404, "body": json.dumps({"error": "Usuário não encontrado"})}
        
        current_user = resp["Item"]

        # Só atualiza se algum valor for diferente
        update_expr, expr_attr_values, expr_attr_names = [], {}, {}
        if name and name != current_user.get("name"):
            update_expr.append("#n = :n")
            expr_attr_values[":n"] = name
            expr_attr_names["#n"] = "name"
        if email and email != current_user.get("email"):
            update_expr.append("#e = :e")
            expr_attr_values[":e"] = email
            expr_attr_names["#e"] = "email"

        if not update_expr:
            return {"statusCode": 400, "body": json.dumps({"error": "Nada para atualizar"})}

        table.update_item(
            Key=key,
            UpdateExpression="SET " + ", ".join(update_expr),
            ExpressionAttributeValues=expr_attr_values,
            ExpressionAttributeNames=expr_attr_names
        )

        return {"statusCode": 200, "body": json.dumps({"message": "Usuário atualizado com sucesso"})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

def delete_user(event):
    params = event.get("queryStringParameters") or {}
    user_id = params.get("id")

    if not user_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Parametro 'id' é obrigatório"})
        }

    key = {"PK": f"USER#{user_id}", "SK": "PROFILE"}

    # 1️ tenta deletar e pede que o Dynamo retorne o item antigo
    resp = table.delete_item(
        Key=key,
        ReturnValues="ALL_OLD"
    )

    # 2️ se o item não existia, "Attributes" estará vazio
    if "Attributes" not in resp:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Usuário não encontrado ou já deletado"})
        }

    # 3️ caso contrário, deletou com sucesso
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "Usuário deletado com sucesso"})
    }