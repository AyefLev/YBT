# Runtime Modes

## 1. Institution Deployment

Recommended for real use.

```text
Desktop clients / browser
        |
        v
Institution server
        |
        +-- PostgreSQL
        +-- Redis
        +-- Qdrant
        +-- File storage
```

Traits:

- Shared users and classes.
- Centralized public resources and knowledge base.
- Centralized model/API configuration.
- Real audit logs and cost tracking.
- Backup and upgrade procedures are server-side.

## 2. Desktop Client Only

Recommended for installed user experience.

The desktop app connects to an existing institution server. It does not include
the database or AI provider secrets.

Traits:

- Easy installation for teachers and students.
- No local database maintenance.
- Works like a native client for a server product.

## 3. Local Demo

Recommended only for demos and offline evaluation.

```text
Desktop app
        |
        v
Local API process
        |
        +-- SQLite
        +-- local file storage
        +-- optional local vector store
```

Traits:

- Easy to demonstrate.
- Not suitable for multi-user institutional use.
- Data can be reset or seeded.

## Deployment Rule

If more than one person needs to share data, use institution deployment. Local
demo mode is only for demonstration, development, or single-user trial.
