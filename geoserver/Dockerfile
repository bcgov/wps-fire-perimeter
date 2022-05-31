# FROM ubuntu-base
# geoserver is not compatible with tomcat 9
FROM tomcat:9

RUN apt-get update --fix-missing && apt-get -y install unzip
RUN wget -q http://sourceforge.net/projects/geoserver/files/GeoServer/2.21.0/geoserver-2.21.0-war.zip -O /tmp/geoserver.zip
RUN unzip -q /tmp/geoserver.zip -d /tmp
# RUN mv /tmp/geoserver.war /opt/tomcat/webapps/geoserver.war
RUN mv /tmp/geoserver.war /usr/local/tomcat/webapps/geoserver.war

# CMD /opt/tomcat/bin/deploy-and-run.sh
# CMD /usr/local/tomcat/bin/catalina.sh run
CMD ["catalina.sh", "run"]