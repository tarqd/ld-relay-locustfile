FROM locustio/locust:0.13.5



COPY locust/ /opt/locust/
USER root
RUN pip install -r /opt/locust/requirements.txt
USER locust
ENV LOCUSTFILE_PATH /opt/locust/locustfile.py


