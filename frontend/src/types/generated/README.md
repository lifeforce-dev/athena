# Generated Types

This directory holds TypeScript types auto-generated from the FastAPI OpenAPI spec.

To regenerate:

```sh
# 1. Start the API server
uvicorn app.main:app

# 2. Generate types
npm run generate:types
```

Files in this directory are overwritten on each generation. Do not edit manually.
