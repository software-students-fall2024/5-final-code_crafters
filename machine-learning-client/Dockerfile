FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install pipenv

COPY Pipfile Pipfile.lock /app/
RUN pipenv install --system --deploy

CMD ["python", "speech_to_text.py"]
