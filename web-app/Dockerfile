
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg

COPY . .

RUN pip install pipenv

RUN pipenv install --system --deploy

EXPOSE 5001

CMD ["python", "app.py"]
