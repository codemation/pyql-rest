FROM joshjamison/uwsgi_python37

ENV PATH="$V_ENV/bin:$PATH"

# Add Dependencies
COPY /requirements.txt .

RUN pip install -r requirements.txt

RUN git clone https://github.com/codemation/pyql-rest.git

WORKDIR /pyql-rest/pyql-rest/

RUN cp /pyql-rest/pyql-rest/sites-available-pyql-rest /etc/nginx/sites-available/ && \
    ln -s /etc/nginx/sites-available/sites-available-pyql-rest /etc/nginx/sites-enabled

EXPOSE 80

CMD ["./startserver.sh"]