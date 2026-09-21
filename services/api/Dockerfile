FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
RUN python -c "import tomllib, pathlib; deps = tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['dependencies']; print('\n'.join(deps))" > /tmp/requirements.txt \
 && pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r /tmp/requirements.txt
COPY main.py ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ . --no-deps

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
