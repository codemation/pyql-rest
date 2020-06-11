FROM joshjamison/uwsgi_python37

ENV PATH="$V_ENV/bin:$PATH"

# Add Dependencies
#COPY /requirements.txt .

RUN git clone https://github.com/codemation/pyql-rest.git

RUN pip install -r pyql-rest/requirements.txt

WORKDIR /pyql-rest/pyql-rest/

RUN cp /pyql-rest/pyql-rest/sites-available-pyql-rest /etc/nginx/sites-available/ && \
    ln -s /etc/nginx/sites-available/sites-available-pyql-rest /etc/nginx/sites-enabled

ENV PYQL_VOLUME_PATH="/mnt/pyql-rest"
ENV PYQL_TYPE=K8S

EXPOSE 80

CMD ["./startserver.sh"]