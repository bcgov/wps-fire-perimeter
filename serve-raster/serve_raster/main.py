from fastapi import FastAPI
from starlette.responses import RedirectResponse
from decouple import config
from aiobotocore.session import get_session


app = FastAPI()


@app.get('/ready')
async def ready():
    return {'status': 'ok'}


@app.get("/{fire}/{filename}")
async def read_root(fire, filename):
    server = config('OBJECT_STORE_SERVER')
    user_id = config('OBJECT_STORE_USER_ID')
    secret_key = config('OBJECT_STORE_SECRET')

    session = get_session()
    async with session.create_client('s3',
                                     endpoint_url=f'https://{server}',
                                     aws_secret_access_key=secret_key,
                                     aws_access_key_id=user_id) as client:

        fire = fire.strip('.')
        filename = filename.strip('.')
        key = f'fire_perimeter/{fire}/{filename}'
        bucket = config('OBJECT_STORE_BUCKET')

        response = await client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key})
    return RedirectResponse(url=response)
