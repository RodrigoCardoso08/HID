import os
import datetime
import boto3
import psycopg2


def get_parameter(parameter):
    client = boto3.client('ssm', 'us-east-1')
    response = client.get_parameter(Name=parameter)
    return response['Parameter']['Value']


def get_connection():
    key_name = f'{os.environ.get("SERVICE_NAME")}-{os.environ.get("STAGE")}-database'
    print(key_name)
    conn_string = get_parameter(key_name)
    return psycopg2.connect(conn_string)


def insert(obj, table_name, connection, cursor, pk="id"):
    keys = obj.keys()
    query = f"""
        insert into {table_name} ("{'","'.join(keys)}")
        values ({",".join(["%s"] * len(keys))})
        returning {pk};
    """
    cursor.execute(query, [obj[key] for key in keys])
    connection.commit()
    return cursor.fetchone()[0]


def insert_multiple(arr, table_name, connection, cursor, pk="id"):
    if len(arr) == 0:
        return []
    keys = arr[0].keys()
    query = f"""
        insert into {table_name} ("{'","'.join(keys)}")
        values {",".join(["(" + ",".join(["%s"] * len(keys)) + ")"] * len(arr))}
        returning "{pk}";
    """
    cursor.execute(query, sum([[obj[key] for key in keys] for obj in arr], []))
    connection.commit()
    ids = cursor.fetchall()
    return [id[0] for id in ids]


def update(obj, table_name, pk_value, connection, cursor, pk='id'):
    keys = obj.keys()
    query = f"""
        update {table_name}
        set {",".join([f'"{key}"=%s' for key in keys])}
        where "{pk}"=%s;
    """
    cursor.execute(query, [obj[key] for key in keys] + [pk_value])
    connection.commit()


def delete(table_name, conditions, connection, cursor):
    cond_keys = conditions.keys()
    query = f"""
        delete from {table_name}
        where {" and ".join([f'"{cond_key}"=%s' for cond_key in cond_keys])};
    """
    cursor.execute(query, [conditions[key] for key in conditions])
    connection.commit()


def build_select_query(fields, table_name, conditions):
    cond_keys = conditions.keys()
    where_clausule = f"""where {" and ".join([f'"{cond_key}"=%s' for cond_key in cond_keys])}"""
    return f"""
        select "{'","'.join(fields)}"
        from {table_name}
        {where_clausule if len(cond_keys) else ""}
    """

def select(fields, table_name, conditions, cursor):
    query = build_select_query(fields, table_name, conditions)
    cursor.execute(query, [conditions[key] for key in conditions])
    return cursor.fetchall()

def exists(table_name, conditions, cursor, pk="id"):
    query = f"""
        select exists(
            {build_select_query([pk], table_name, conditions)}
        )
    """
    cursor.execute(query, [conditions[key] for key in conditions])
    return cursor.fetchone()[0]

def set_to_cache(key, value, expires_in, connection, cursor):
    exp = (datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)).replace(microsecond=0)
    obj = {
        'cache_key': key,
        'value': value,
        'expires': exp
    }
    query = f"""
        select exists(
            select cache_key
            from cache
            where cache_key = '{key}'
        )
    """
    cursor.execute(query)
    if cursor.fetchone()[0]:
        update(obj, "cache", key, connection, cursor, pk="cache_key")
    else:
        insert(obj, "cache", connection, cursor, pk = "cache_key")


def get_from_cache(key, connection, cursor):
    cursor.execute(f"""
        select value, expires
        from cache where cache_key='{key}'
    """)
    data = cursor.fetchone()
    if data is None:
        return None
    if datetime.datetime.now().astimezone() > data[1]:
        cursor.execute(f"""
            delete from cache
            where cache_key='{key}'
        """)
        connection.commit()
        return None
    return data[0]
