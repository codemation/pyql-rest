FROM mysql:5.7

RUN apt-get update && \
    apt-get install -y python3 \ 
                        net-tools \
                        netcat
# Requires environment variables for 
# MYSQL_ROOT_PASSWORD
# MYSQL_USER
# MYSQL_PASSWORD <---for the user
# MYSQL_DATABSE <--name of database to be created on instance start