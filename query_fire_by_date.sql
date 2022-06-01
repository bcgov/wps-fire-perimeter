
CREATE OR REPLACE FUNCTION postgisftw.fire_by_date(
	date_of_interest date)
RETURNS TABLE(id integer, geom geometry, date_range integer, cloud_cover double precision,
			  fire_number character varying,
			 latitude double precision, longitude double precision,
			  rgb_raster character varying, create_date timestamp with time zone, update_date timestamp with time zone)
AS $$
BEGIN
	RETURN QUERY
		SELECT t.id, t.geom, t.date_range, t.cloud_cover,
		t.fire_number,
		t.latitude, t.longitude,
		t.rgb_raster, t.create_date, t.update_date
    FROM public.featureserv t
    WHERE t.date_of_interest = fire_by_date.date_of_interest;
END;
$$

LANGUAGE 'plpgsql' STABLE PARALLEL SAFE;

COMMENT ON FUNCTION postgisftw.fire_by_date IS 'Filters the featureserv table by date of interest ';