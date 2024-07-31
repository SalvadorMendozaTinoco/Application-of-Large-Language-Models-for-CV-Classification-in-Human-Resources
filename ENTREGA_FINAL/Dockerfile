FROM python:3.10.14-bullseye

WORKDIR /resumeparser

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN apt-get update && \
    apt-get install -y poppler-utils && \
    apt install -y libgl1-mesa-glx && \
    apt install -y tesseract-ocr-eng && \
    apt install -y tesseract-ocr-spa && \
    apt-get install -y libreoffice --no-install-recommends  --no-install-suggests

CMD ["/bin/bash"]