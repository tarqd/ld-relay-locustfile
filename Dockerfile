FROM locustio/locust:1.5.3



COPY locust/ /opt/locust/
USER root
RUN pip install -r /opt/locust/requirements.txt
USER locust
ENV LOCUST_LOCUSTFILE /opt/locust/locustfile.py


