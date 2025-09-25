import json
import boto3
import hashlib
import time
import random
import base64
import hmac

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = "AppData"
table = dynamodb.Table(TABLE_NAME)

SECRET = "sua-chave-secreta-superforte"

# -------------------- UTILs JWT -------------------- #
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def base64url_decode(data: str) -> dict:
    padding = "=" * (-len(data) % 4)
    return json.loads(base64.urlsafe_b64decode(data + padding).decode())

def generate_jwt(user_id: str, email: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600
    }

    header_b64 = base64url_encode(json.dumps(header).encode())
    payload_b64 = base64url_encode(json.dumps(payload).encode())
    signature = hmac.new(
        SECRET.encode(),
        f"{header_b64}.{payload_b64}".encode(),
        hashlib.sha256
    ).digest()

    signature_b64 = base64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def verify_jwt(token: str) -> dict:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        expected_sig = hmac.new(
            SECRET.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()

        if base64url_encode(expected_sig) != signature_b64:
            raise Exception("Assinatura inválida")

        payload = base64url_decode(payload_b64)
        if "exp" in payload and payload["exp"] < int(time.time()):
            raise Exception("Token expirado")
        return payload
    except Exception as e:
        print("Erro verify_jwt:", str(e))
        return None

# -------------------- AUTH METHODS -------------------- #
def login(event):
    body = json.loads(event.get("body", "{}"))
    email, password = body.get("email"), body.get("password")

    if not all([email, password]):
        return _response(400, {"error": "Campos obrigatórios: email e password"})

    resp = table.scan(
        FilterExpression="email = :email AND SK = :sk",
        ExpressionAttributeValues={":email": email, ":sk": "PROFILE"}
    )
    users = resp.get("Items", [])
    if not users:
        return _response(401, {"error": "Email ou senha inválidos"})

    user = users[0]
    hashed_input_password = hash_password(password)

    if user.get("password") != hashed_input_password:
        return _response(401, {"error": "Email ou senha inválidos"})

    user_id = user["PK"].replace("USER#", "")
    token = generate_jwt(user_id, email)

    return _response(200, {"accessToken": token, "userId": user_id})

def reset_password_request(event):
    body = json.loads(event.get("body", "{}"))
    email = body.get("email")

    if not email:
        return _response(400, {"error": "Campo 'email' obrigatório"})

    resp = table.scan(
        FilterExpression="email = :email AND SK = :sk",
        ExpressionAttributeValues={":email": email, ":sk": "PROFILE"}
    )
    users = resp.get("Items", [])
    if not users:
        return _response(404, {"error": "Usuário não encontrado"})

    user = users[0]
    user_id = user["PK"].replace("USER#", "")
    code = str(random.randint(100000, 999999))

    item = {
        "PK": f"USER#{user_id}",
        "SK": f"RESET#{code}",
        "email": email,
        "code": code,
        "createdAt": int(time.time()),
        "expiresAt": int(time.time()) + 600
    }
    table.put_item(Item=item)

    print(f"Reset code for {email}: {code}")

    return _response(200, {"message": "Verification code sent to email"})

def reset_password_validate(event):
    body = json.loads(event.get("body", "{}"))
    email, code = body.get("email"), body.get("code")

    if not all([email, code]):
        return _response(400, {"error": "Campos obrigatórios: email e code"})

    resp = table.scan(
        FilterExpression="email = :email AND SK = :sk",
        ExpressionAttributeValues={":email": email, ":sk": f"RESET#{code}"}
    )
    codes = resp.get("Items", [])
    
    if not codes:
        return _response(400, {"error": "Código inválido"})

    reset_entry = codes[0]
    if reset_entry["expiresAt"] < int(time.time()):
        return _response(400, {"error": "Código expirado"})

    return _response(200, {"message": "Code valid"})

def reset_password_confirm(event):
    body = json.loads(event.get("body", "{}"))
    email, new_password = body.get("email"), body.get("newPassword")

    if not all([email, new_password]):
        return _response(400, {"error": "Campos obrigatórios: email e newPassword"})

    resp = table.scan(
        FilterExpression="email = :email AND SK = :sk",
        ExpressionAttributeValues={":email": email, ":sk": "PROFILE"}
    )
    users = resp.get("Items", [])
    if not users:
        return _response(404, {"error": "Usuário não encontrado"})

    user = users[0]
    key = {"PK": user["PK"], "SK": "PROFILE"}

    hashed_pwd = hash_password(new_password)
    table.update_item(
        Key=key,
        UpdateExpression="SET #p = :p",
        ExpressionAttributeNames={"#p": "password"},
        ExpressionAttributeValues={":p": hashed_pwd}
    )

    return _response(200, {"message": "Password updated successfully"})

# -------------------- HELPER -------------------- #
def _response(status, body_dict):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_dict)
    }

# -------------------- DISPATCHER -------------------- #
def lambda_handler(event, context):
    try:
        method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
        path = event.get("path") or event.get("requestContext", {}).get("path", "")

        if method == "POST" and "/auth/login" in path:
            return login(event)
        elif method == "POST" and "/auth/reset/request" in path:
            return reset_password_request(event)
        elif method == "POST" and "/auth/reset/validate" in path:
            return reset_password_validate(event)
        elif method == "POST" and "/auth/reset/confirm" in path:
            return reset_password_confirm(event)

        return _response(404, {"error": "Endpoint não encontrado"})

    except Exception as e:
        print("Erro geral:", str(e))
        return _response(500, {"error": "Erro interno do servidor"})