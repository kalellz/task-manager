import json
import uuid
import time
import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = "AppData"
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    try:
        method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")

        if method == "POST":
            return create_task(event)
        elif method == "GET":
            return get_tasks(event)
        elif method == "PUT":
            return update_task(event)
        elif method == "DELETE":
            return delete_task(event)
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

# -------------------- TASK METHODS -------------------- #
def create_task(event):
    body = json.loads(event.get("body", "{}"))
    user_id, title, description = body.get("userId"), body.get("title"), body.get("description")

    if not all([user_id, title]):
        return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Campos obrigatórios: userId e title"})}

    task_id = str(uuid.uuid4())
    item = {
        "PK": f"USER#{user_id}",
        "SK": f"TASK#{task_id}",
        "taskId": task_id,
        "title": title,
        "description": description or "",
        "done": False,
        "createdAt": int(time.time() * 1000),
    }
    table.put_item(Item=item)
    return {"statusCode": 201, "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"taskId": task_id, "title": title, "description": description, "done": False})}

def get_tasks(event):
    params = event.get("queryStringParameters") or {}
    user_id = params.get("userId")
    
    if not user_id:
        return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Parametro 'userId' é obrigatório"})}

    resp = table.query(
        KeyConditionExpression="PK = :u AND begins_with(SK, :t)",
        ExpressionAttributeValues={":u": f"USER#{user_id}", ":t": "TASK#"}
    )
    tasks = resp.get("Items", [])
    return {"statusCode": 200, "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"tasks": tasks}, default=str)}

def update_task(event):
    try:
        body = json.loads(event.get("body", "{}"))
        user_id, task_id, title, description, done = (
            body.get("userId"), body.get("taskId"), 
            body.get("title"), body.get("description"), body.get("done")
        )

        if not user_id or not task_id:
            return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Campos obrigatórios: userId e taskId"})}

        # Pega a task atual
        key = {"PK": f"USER#{user_id}", "SK": f"TASK#{task_id}"}
        resp = table.get_item(Key=key)
        if "Item" not in resp:
            return {"statusCode": 404, "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Task não encontrada"})}
        
        current_task = resp["Item"]

        # Só atualiza se algum valor for diferente
        update_expr, expr_attr_values, expr_attr_names = [], {}, {}
        if title and title != current_task.get("title"):
            update_expr.append("#t = :t")
            expr_attr_values[":t"] = title
            expr_attr_names["#t"] = "title"
        if description and description != current_task.get("description"):
            update_expr.append("#d = :d")
            expr_attr_values[":d"] = description
            expr_attr_names["#d"] = "description"
        if done is not None and done != current_task.get("done"):
            update_expr.append("#s = :s")
            expr_attr_values[":s"] = done
            expr_attr_names["#s"] = "done"

        if not update_expr:
            return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Nada para atualizar"})}

        table.update_item(
            Key=key,
            UpdateExpression="SET " + ", ".join(update_expr),
            ExpressionAttributeValues=expr_attr_values,
            ExpressionAttributeNames=expr_attr_names
        )

        return {"statusCode": 200, "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": "Task atualizada com sucesso"})}
    except Exception as e:
        return {"statusCode": 500, "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(e)})}

def delete_task(event):
    params = event.get("queryStringParameters") or {}
    user_id, task_id = params.get("userId"), params.get("taskId")

    if not user_id or not task_id:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Parametros obrigatórios: userId e taskId"})
        }

    key = {"PK": f"USER#{user_id}", "SK": f"TASK#{task_id}"}

    # Tenta deletar e pede que o Dynamo retorne o item antigo
    resp = table.delete_item(
        Key=key,
        ReturnValues="ALL_OLD"
    )

    # Se o item não existia, "Attributes" estará vazio
    if "Attributes" not in resp:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Task não encontrada ou já deletada"})
        }

    # Caso contrário, deletou com sucesso
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "Task deletada com sucesso"})
    }