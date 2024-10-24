# Blog API

This is a simple API built for managing blog posts and comments, featuring automatic moderation and responses using AI. The API supports user registration, post creation, comment moderation, and analytics.

## Features
- **User Management**: Register new users and log in with jwt tokens authentication.
- **Post and Comment Management**: Create posts and comments.
- **Moderation**: Automatic moderation of posts and comments.
- **Automatic Responses**: The system provides AI-generated replies to comments with configurable delays.
- **Analytics**: View statistics on comment creation and blocked comments.

## Tech Stack
- **FastAPI**: The core framework for building the API.
- **Pydantic**: Used for data validation and serialization.
- **Docker**: Containerization for easy deployment and development.
- **PostgreSQL**: A robust relational database used to store and manage users, posts, comments, and moderation logs.
- **Celery**: A task queue for handling background tasks, such as delayed comment replies and moderation processing.
- **Redis**: An in-memory data store used as a message broker for Celery, enabling efficient communication and task management.


## Getting Started

### Requirements
- Docker
- Dokcer-compose
  
### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/AndrewwSSS/Blog.git
   cd Blog
   ```

### Configuration

create .env file:
```shell
cat .env.template > .env
```

Provide all required variables.
Test data(api keys can be expired):
```shell
   POSTGRES_USER=test
   POSTGRES_PASSWORD=test
   POSTGRES_DB=test
   POSTGRES_HOST=localhost
   
   SECRET_KEY=4fdsm4f782mdreDssknmf38ss02dltdSD
   
   OPENAI_API_KEY=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
   GROQ_API_KEY=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
   
   TEST_DB_PORT=6000
   TEST_DB_USER=test_user
   TEST_DB_PASSWORD=test_password
   TEST_DB_HOST=test_db
   TEST_DB_NAME=test
```

To obtain GROQ_API_KEY You can visit https://console.groq.com/keys. OPENAI_API_KEY - https://platform.openai.com/api-keys


### Running

```bash
docker-compose up --build -d
```

### Testing

Before running test you should run docker services(described in Running section)

```bash
docker exec api pytest tests/  
```

