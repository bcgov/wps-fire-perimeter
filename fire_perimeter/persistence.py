from urllib.parse import quote_plus as urlquote
import psycopg
from decouple import config


def persist_polygon(filename: str, identifier: str):
    """
    filename: geojson file
    identifier: fire identifier
    """
    print(f'persist ${filename} to postgresql')

    user = config('user')
    password = config('password')
    port = config('port')
    host = config('host')
    dbname = config('dbname')

    db_string = f'postgresql://{user}:{urlquote(password)}@{host}:{port}/{dbname}'

    with open(filename) as f:
        # f.write(json.dumps(polygon))
        pass