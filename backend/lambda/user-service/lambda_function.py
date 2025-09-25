import json
import uuid
import time
import boto3
import hashlib

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = "AppData"
s3 = boto3.client("s3")
BUCKET_NAME = "task-manager-user-images"
REGION = "sa-east-1"
table = dynamodb.Table(TABLE_NAME)

def generate_upload_url(event):
    body = json.loads(event.get("body", "{}"))
    user_id = body.get("userId")

    if not user_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Parametro 'userId' obrigatório"})
        }

    # Nome único para o arquivo no S3
    key = f"users/{user_id}_{int(time.time())}.png"

    # URL temporária (PUT) para upload
    presigned_url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET_NAME, "Key": key},
        ExpiresIn=300  # 5 minutos
    )

    # URL final pública para leitura
    image_url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{key}"

    # Atualiza DynamoDB para salvar a referência
    table.update_item(
        Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
        UpdateExpression="SET #img = :img",
        ExpressionAttributeNames={"#img": "imageUrl"},
        ExpressionAttributeValues={":img": image_url}
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "uploadUrl": presigned_url,
            "imageUrl": image_url
        })
    }

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def lambda_handler(event, context):
    try:
        method = event.get("httpMethod")
        path = event.get("path") or ""
        resource = event.get("resource") or ""

        if method == "POST" and resource == "/users/uploadUrl":
            return generate_upload_url(event)

        elif method == "POST" and (resource == "/users" or path.endswith("/users")):
            return create_user(event)

        elif method == "GET":
            return get_user(event)

        elif method == "PUT":
            return update_user(event)

        elif method == "DELETE":
            return delete_user(event)

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

    user_id = params.get("id") if params else None
    if user_id:  # Buscar só um usuário
        resp = table.get_item(Key={"PK": f"USER#{user_id}", "SK": "PROFILE"})
        if "Item" not in resp:
            return {"statusCode": 404, "body": json.dumps({"error": "Usuário não encontrado"})}
        return {"statusCode": 200, "body": json.dumps(resp["Item"], default=str)}

    # Buscar todos (scan com filtro por SK = PROFILE)
    resp = table.scan(
        FilterExpression="SK = :sk",
        ExpressionAttributeValues={":sk": "PROFILE"}
    )
    users = resp.get("Items", [])
    return {"statusCode": 200, "body": json.dumps({"users": users}, default=str)}

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