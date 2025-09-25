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
    body = json.loads(event.get("body", "{}"))
    user_id, name, email = body.get("userId"), body.get("name"), body.get("email")

    if not user_id:
        return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Campo 'userId' obrigatório"})}

    update_expr, expr_attr = [], {}
    if name: 
        update_expr.append("name = :n")
        expr_attr[":n"] = name
    if email: 
        update_expr.append("email = :e")
        expr_attr[":e"] = email

    if not update_expr:
        return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Nada para atualizar"})}

    table.update_item(
        Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
        UpdateExpression="SET " + ", ".join(update_expr),
        ExpressionAttributeValues=expr_attr
    )

    return {"statusCode": 200, "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Usuário atualizado"})}

def delete_user(event):
    params = event.get("queryStringParameters") or {}
    user_id = params.get("id")
    if not user_id:
        return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Parametro 'id' é obrigatório"})}

    table.delete_item(Key={"PK": f"USER#{user_id}", "SK": "PROFILE"})
    return {"statusCode": 200, "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Usuário deletado"})}