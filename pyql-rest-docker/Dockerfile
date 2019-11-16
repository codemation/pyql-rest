FROM joshjamison/uwsgi-flask

RUN pip install pyql

# Pyql rest endpoint repo
RUN git clone  https://github.com/codemation/pyql-rest

#pyql rest endpoint
WORKDIR /pyql-rest

CMD ["python", "server.py"]