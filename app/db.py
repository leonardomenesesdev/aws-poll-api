import boto3
from app.config import AWS_REGION, DYNAMODB_ENDPOINT_URL, POLLS_TABLE_NAME

_resource = None


def get_dynamodb_resource():
    global _resource
    if _resource is None:
        kwargs = {"region_name": AWS_REGION}
        if DYNAMODB_ENDPOINT_URL:
            kwargs["endpoint_url"] = DYNAMODB_ENDPOINT_URL
            # boto3 requer credenciais, mesmo que o DynamoDB Local as ignore
            kwargs["aws_access_key_id"] = "local" #access_key_id fake
            kwargs["aws_secret_access_key"] = "local"
        _resource = boto3.resource("dynamodb", **kwargs)
    return _resource

#retorna a referência da tabela 'Polls' do dynamodb
def get_polls_table():
    return get_dynamodb_resource().Table(POLLS_TABLE_NAME)


def ensure_table_exists():
    #Cria a tabela Polls se ela não existir ainda,
    #destinado apenas para desenvolvimento local contra o dynamo local. Na AWS, a tabela é provisionada via IaC 
    client = get_dynamodb_resource().meta.client
    existing = client.list_tables()["TableNames"]
    if POLLS_TABLE_NAME in existing:
        return

    client.create_table(
        TableName=POLLS_TABLE_NAME,
        KeySchema=[{"AttributeName": "poll_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "poll_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    client.get_waiter("table_exists").wait(TableName=POLLS_TABLE_NAME)
