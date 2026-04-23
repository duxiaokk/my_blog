# My Blog

Minimal FastAPI blog project with:

- authentication
- posts and likes
- comments
- Alembic migrations
- Ruff and pytest quality checks

## Local Setup

1. Create `.env` from [.env.example](/D:/Python/Personal%20Blog/my_blog/.env.example).
2. Install dependencies:

```bash
pip install -r requirements-dev.txt
```

3. Run migrations:

```bash
python tasks.py db-upgrade
```

4. Start the app:

```bash
python tasks.py run
```

## Quality Checks

```bash
python tasks.py lint
python tasks.py format --check
python tasks.py test
```

## Docker

Build the image:

```bash
docker build -t my-blog .
```

Run the container:

```bash
docker run --rm -p 8000:8000 --env-file .env my-blog
```

If you want SQLite data to persist across container restarts, mount a volume for `/app`.
