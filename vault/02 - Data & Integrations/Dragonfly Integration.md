---
title: Dragonfly Integration
tags:
  - prd
  - dragonfly
  - docker
status: draft
---

# Dragonfly Integration

> [!note] Part of [[Orochi PRD]] · stores the [[Data Model]]

Run Dragonfly as a local container and talk to it via `redis-py`.

## Docker Compose (conceptual)

```yaml
version: "3.8"
services:
  dragonfly:
    image: dragonflydb/dragonfly
    ports:
      - "6379:6379"
    command: ["--logtostderr"]
  app:
    build: .
    depends_on:
      - dragonfly
    environment:
      DRAGONFLY_URL: redis://dragonfly:6379
```

## Python client

```python
import os
import redis

DRAGONFLY_URL = os.getenv("DRAGONFLY_URL", "redis://localhost:6379")
db = redis.Redis.from_url(DRAGONFLY_URL)

def create_or_get_patient(phone: str, name: str) -> str:
    # naive example: key lookup by phone
    patient_uuid = db.get(f"phone:{phone}")
    if patient_uuid:
        return patient_uuid.decode()

    import uuid
    patient_uuid = str(uuid.uuid4())
    pipe = db.pipeline()
    pipe.hset(f"patient:{patient_uuid}", mapping={"name": name, "phone": phone})
    pipe.set(f"phone:{phone}", patient_uuid)
    pipe.execute()
    return patient_uuid
```

> [!reference]
> - [Dragonfly SDKs](https://www.dragonflydb.io/docs/development/sdks)
> - [dragonfly-examples](https://github.com/dragonflydb/dragonfly-examples)
