FROM python:3.12.6-slim

WORKDIR /app

COPY . . 

RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 libsm6 libxext6 libxrender1 && rm -rf /var/lib/apt/lists/*

RUN pip install -r torch-requirements.txt
RUN pip install -r requirements.txt

CMD ["python", "app.py"]