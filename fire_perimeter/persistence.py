import json
from datetime import datetime, date
from urllib.parse import quote_plus as urlquote
from shapely.geometry import shape, MultiPolygon, Point
from shapely import wkb
from sqlalchemy import UniqueConstraint, create_engine, MetaData, Table, Column, Integer, DATE, TIMESTAMP, String, Float
from geoalchemy2.types import Geometry
from decouple import config


def create_table_schema(meta_data: MetaData, table_name: str, srid: int) -> Table:
    """
    Create a table schema.
    geom_type: geometry type (e.g. POLYGON or MULTIPOLYGON)
    srid: spatial reference id (e.g. 4326)
    """
    return Table(table_name, meta_data,
                 Column('id', Integer(), primary_key=True, nullable=False),
                 Column('geom', Geometry(geometry_type='MULTIPOLYGON', srid=srid, spatial_index=True,
                        from_text='ST_GeomFromEWKT', name='geometry'), nullable=False),                 
                 Column('date_range', Integer(), nullable=False,
                        comment='Number of days used to generate the fire perimeter'),
                 Column('fire_number', String(), nullable=False),
                 Column('latitude', Float(), nullable=False, comment='Latitude of the fire'),
                 Column('longitude', Float(), nullable=False, comment='Longitude of the fire'),
                 Column('date_of_interest', DATE(), nullable=False),
                 Column('create_date', TIMESTAMP(
                     timezone=True), nullable=False),
                 Column('update_date', TIMESTAMP(
                     timezone=True), nullable=False),
                 UniqueConstraint('fire_number', 'date_of_interest', name='uix_fire_number_date_of_interest'),
                 schema=None)


def construct_multipolygon(filename: str):
    with open(filename) as f:
        # the geojson is a bunch of polygons, we want a multipolygon
        js = json.load(f)
    polygons = [shape(feature['geometry']) for feature in js['features']]
    print(f'{len(polygons)} polygons found')
    if len(polygons) > 0:
        return MultiPolygon(polygons)
    return None


def persist_polygon(filename: str, identifier: str, date_of_interest: date, coordinate: Point, date_range: int):
    """
    filename: geojson file
    identifier: fire identifier
    """
    print(f'persist {filename} to postgresql')

    multi_polygon = construct_multipolygon(filename)
    if multi_polygon is None:
        print('failed to generate multipolygon')
        return

    user = config('user')
    password = config('password')
    port = config('port')
    host = config('host')
    dbname = config('dbname')
    table = config('table')

    db_string = f'postgresql://{user}:{urlquote(password)}@{host}:{port}/{dbname}'

    srid = 4326
    meta_data = MetaData()
    table_schema = create_table_schema(meta_data, table, srid)
    
    engine = create_engine(db_string, connect_args={
                        'options': '-c timezone=utc'})

    with engine.connect() as connection:
        if not engine.dialect.has_table(connection, table):
            table_schema.create(engine)
        
        wkt = wkb.dumps(multi_polygon, hex=True, srid=srid)

        result = connection.execute(table_schema.select().where(
            table_schema.c.fire_number == identifier).where(
                table_schema.c.date_of_interest == date_of_interest)).first()
        
        now = datetime.now()

        if result:
            connection.execute(table_schema.update().where(
                table_schema.c.fire_number == identifier).where(
                    table_schema.c.date_of_interest == date_of_interest).values(
                        geom=wkt,
                        latitude=coordinate.y,
                        longitude=coordinate.x,
                        date_range=date_range,
                        update_date=now))
        else:
            values = {
                'geom': wkt,
                'latitude': coordinate.y,
                'longitude': coordinate.x,
                'date_range': date_range,
                'fire_number': identifier,
                'date_of_interest': date_of_interest,
                'create_date': now,
                'update_date': now,
            }
            connection.execute(table_schema.insert().values(values))



        