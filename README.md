# Blog API

This is a simple API built for managing blog posts and comments, featuring automatic moderation and responses using AI. The API supports user registration, CRUD operations with post, comment moderation, and analytics.

## Features
- **User Management**: Register new users and log in with jwt tokens authentication.
- **Post and Comment Management**: Create, update, delete posts and comments.
- **Moderation**: Automatic moderation of posts and comments.
- **Automatic Responses**: The system provides AI-generated replies to comments with configurable delays.
- **Analytics**: View statistics on comment creation and blocked comments.

## Tech Stack
- **FastAPI**: The core framework for building the API.
- **Pydantic**: Used for data validation and serialization.
- **Docker**: Containerization for easy deployment and development.
- **PostgreSQL**: A robust relational database used to store and manage users, posts, comments, and moderation logs.
- **Celery**: A task queue for handling background tasks, such as delayed comment replies and moderation processing.
- **Redis**: An in-memory data store used as a message broker for Celery and cache storage, enabling efficient communication and task management.
- **ElasticSearch**: NoSQL database, provides posts full text search 
- **Kafka**: Message broker for notification service


## Getting Started

### Requirements
- Docker with Docker Compose v2
- make
  
### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/AndrewwSSS/Blog.git
   cd Blog
   ```

### Configuration

Create the .env file (it never overwrites an existing one):
```shell
make env
```

Fill in all required variables. Optional ones can stay empty to use their defaults.
Example values for local development:
```shell
   POSTGRES_USER=test
   POSTGRES_PASSWORD=test
   POSTGRES_DB=test
   POSTGRES_HOST=db

   SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_urlsafe(32))">
   EMAIL_TOKEN_SALT=<another random string>

   KAFKA_URL=kafka:9092

   SMTP_USER=<your-smtp-login>
   SMTP_USER_PASSWORD=<your-smtp-app-password>

   GROQ_API_KEY=<your-groq-api-key>
```

To obtain GROQ_API_KEY You can visit https://console.groq.com/keys.
OPENAI_API_KEY - https://platform.openai.com/api-keys


### Running

```bash
make up         # start the stack in the background
make up-debug   # also start Flower (http://localhost:5555) and Kibana (http://localhost:5601)
make logs s=api # follow the logs of one service
make down       # stop everything (data volumes are kept)
```

The API is available at http://localhost:8000/docs. All ports are bound to localhost only.

### Production (HTTPS with Traefik)

`docker-compose.prod.yaml` puts [Traefik](https://doc.traefik.io/traefik/) in front of the API:
it gets and renews a Let's Encrypt certificate, redirects HTTP to HTTPS, and adds a per-IP rate
limit, a 1 MiB request body limit and security headers. The API port is no longer published, and
the API runs without `--reload` or the source mount.

1. Point the DNS record of your domain to the server and open ports 80 and 443.
2. Set `DOMAIN` in `.env` (for example `DOMAIN=blog.example.com`).
3. Start it:

```bash
make up-prod    # start the stack behind Traefik
make down-prod  # stop it (data volumes and the certificate are kept)
```

Routes, limits and headers are in `traefik/dynamic.yml`. Traefik reads them from that file and has
no access to the Docker socket. Certificates are stored in the `traefik_acme` volume.

### Testing and linting

Tests use SQLite and fake Redis, so they need no running services:

```bash
make test-local  # run tests with Poetry
make lint        # check code with ruff
make format      # format code with ruff
```

Or run the tests inside the running API container:

```bash
make test
```

Run `make` to see all commands.

