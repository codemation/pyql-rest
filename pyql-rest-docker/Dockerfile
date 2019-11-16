FROM joshjamison/uwsgi-flask

RUN pip install pyql

RUN git clone  https://github.com/codemation/pyql-rest

#pyql rest endpoint
WORKDIR /pyql-rest

CMD ["python", "server.py"]