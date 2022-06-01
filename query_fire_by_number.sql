
CREATE OR REPLACE FUNCTION postgisftw.fire_by_number(
	fire_number text)
RETURNS TABLE(id integer, geom geometry, date_range integer, cloud_cover double precision,
			 latitude double precision, longitude double precision,
			  date_of_interest date,
			  rgb_raster character varying, create_date timestamp with time zone, update_date timestamp with time zone)
AS $$
BEGIN
	RETURN QUERY
		SELECT t.id, t.geom, t.date_range, t.cloud_cover,
		t.latitude, t.longitude,
		t.date_of_interest,
		t.rgb_raster, t.create_date, t.update_date
    FROM public.featureserv t
    WHERE t.fire_number LIKE fire_by_number.fire_number;
END;
$$

LANGUAGE 'plpgsql' STABLE PARALLEL SAFE;

COMMENT ON FUNCTION postgisftw.fire_by_number IS 'Filters the featureserv table by fire_number ';