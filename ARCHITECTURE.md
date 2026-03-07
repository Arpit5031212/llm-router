# llm-router: Architecture and Design Rationale

This document explains the codebase architecture, how components work, and why design decisions were made. It is aimed at developers who need to understand, extend, or maintain the system.

---

## 1. Purpose

llm-router is a simplified OpenRouter-style system: users run the same prompt against multiple LLM providers, compare responses, and select preferred outputs. The design emphasizes:

- **Provider agnosticism** — Swap GPT, Gemini, or other providers without changing core logic
- **Caching and deduplication** — Avoid redundant API calls for identical inputs
- **Experiment tracking** — Group predictions by comparison so users can evaluate side-by-side
- **Production readiness** — Logging, indexing, and extensibility from the start

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HTTP Request                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  API Layer (predictions.py)                                                  │
│  - Parses JSON, validates UUIDs, returns HTTP responses                      │
│  - Why: Keeps HTTP concerns (status codes, headers) separate from business   │
│    logic                                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Service Layer (prediction_service.py)                                       │
│  - Orchestrates: hash → check cache → call adapter → persist → return        │
│  - Why: Central place for prediction flow; API stays thin, repo stays dumb   │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                                    │
                    ▼                                    ▼
┌──────────────────────────────┐     ┌─────────────────────────────────────────┐
│  Repository                   │     │  Adapter Factory + Adapters             │
│  - Abstract interface in      │     │  - Factory returns adapter per model    │
│    prediction_repo.py         │     │  - Adapters encapsulate provider APIs   │
│  - SQLAlchemy impl in         │     │  - Why: Add new providers without       │
│    SQLAlchemyPredictionRepo   │     │    touching service or API code         │
│  - Why: Swap storage (e.g.    │     └─────────────────────────────────────────┘
│    Postgres, test doubles)    │
└──────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Models (models.py)                                                          │
│  - SQLAlchemy ORM entities: User, LLMModel, ModelVersion, Comparison,        │
│    Prediction                                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Request Flow: Create Prediction

### Step-by-step

1. **Client** sends `POST /api/v1/predictions` with `{ model_version_id, input, comparison_id? }`.

2. **Flask** routes to `create_prediction()`. `before_request` has already attached a DB session to `g.db`.

3. **API layer** validates JSON, extracts `model_version_id`, `input`, and optional `comparison_id`, and returns 400 on parse errors.  
   **Why:** Fail fast on bad input; don’t pass invalid data into services.

4. **API** constructs a `PredictionService` per request using:
   - `g.db` (request-scoped session)
   - A new `SQLAlchemyPredictionRepository(session)`
   - Shared `adapter_factory` from app extensions  
   **Why:** Each request gets its own session for correct transaction boundaries; the factory is stateless and can be shared.

5. **PredictionService.predict()**:
   - **Hash input** — `json.dumps(payload, sort_keys=True) + SHA256`  
     **Why:** Stable, compact key for cache lookup; `sort_keys` ensures `{"a":1,"b":2}` and `{"b":2,"a":1}` collide.
   - **Check cache** — `find_latest_by_hash(input_hash, model_version_id)`  
     **Why:** Avoid repeated LLM calls for the same prompt/model; faster and cheaper.
   - If found, return existing prediction.
   - Otherwise, **get adapter** — `adapter_factory.get_adapter(model_version_id)`  
     **Why:** Model version controls which provider/API is used.
   - **Call adapter** — `adapter.predict(input_payload)` with latency timing.  
     **Why:** Adapters handle provider-specific request/response formats; service sees a uniform interface.
   - **Create Prediction** — store id, model_version_id, user_id, comparison_id, hashes, payloads, latency.
   - **Commit** session. On exception, **rollback**.  
   **Why:** All-or-nothing writes; no partial state.

6. **API** returns 201 with `id`, `output`, `latency_ms`, `created_at`.

---

## 4. Component Details

### 4.1 API Layer (`app/api/predictions.py`)

| Endpoint | Purpose | Design choice |
|----------|---------|---------------|
| `GET /api/v1/predictions/<id>` | Fetch a prediction by ID | UUID in path; returns 404 if missing |
| `POST /api/v1/predictions` | Create a prediction | Accepts `input` as arbitrary JSON for flexibility across providers |

`get_prediction_service()` builds the service on demand rather than reusing `app.extensions["prediction_service"]`.  
**Why:** The stored service uses a startup session; request handlers need a session scoped to the current request (`g.db`). Building the service per request ensures correct transaction scope.

`user_id=1` is hardcoded.  
**Why:** Auth is planned; this keeps the prediction flow working until JWT/user resolution is implemented.

---

### 4.2 Service Layer (`app/services/prediction_service.py`)

**Dependencies:** `PredictionRepository`, `ModelAdapterFactory`, `Session`.

**Core flow:** hash → cache lookup → adapter call → persist → commit.

**Input hashing:**

```python
json.dumps(input_payload, sort_keys=True, default=str)
hashlib.sha256(serialized.encode()).hexdigest()
```

- `sort_keys=True` — deterministic output regardless of dict key order.
- `default=str` — handle non-JSON types (e.g. `datetime`) instead of raising.
- SHA256 — fast and collision-resistant enough for cache keys.

**Commit/rollback:** Service explicitly commits after a successful write and rolls back on exception.  
**Why:** API and teardown handlers should not drive transaction boundaries; the service owns the write semantics.

---

### 4.3 Repository Layer

**Interface** (`app/repositories/prediction_repo.py`): abstract `PredictionRepository` with `create`, `get_by_id`, `find_latest_by_hash`, `find_by_comparison`.

**Why abstract:** Enables in-memory or mock implementations for tests; production uses SQLAlchemy without coupling services to ORM details.

**Implementation** (`app/repositories/SQLAlchemyPredictionRepository.py`):

- `create` — `session.add` + `flush`, no commit.  
  **Why:** Commit is done by the service; flush assigns IDs and checks constraints inside the same transaction.

- `find_latest_by_hash` — `ORDER BY created_at DESC LIMIT 1`.  
  **Why:** If model or adapter changes, newer predictions take precedence.

- `find_by_comparison` — returns all predictions for a comparison, ordered by creation.  
  **Why:** Supports listing predictions in an experiment for comparison.

---

### 4.4 Adapters

**Base** (`app/adapters/base.py`): `BaseModelAdapter` with abstract `predict(input_payload) -> Dict[str, Any]`.

**Why:** Forces each provider to expose the same interface: input and output are plain dicts. Provider-specific API shapes stay inside adapters.

**Factory** (`app/adapters/factory.py`): `ModelAdapterFactory.get_adapter(model_version_id)` returns the adapter for that model version.  
**Why:** Model versions are the stable identifier; the factory decides which concrete adapter (and which provider) to use.

**DummyAdapter** (`app/adapters/dummy_adapter.py`): Returns a synthetic response (echo, analysis, confidence).  
**Why:** Allows testing the full flow without real LLM calls or API keys.

Right now the factory always returns `DummyAdapter`. Future work: map `model_version_id` to `ModelVersion.config_json` (e.g. provider, endpoint) and return GPT, Gemini, or other adapters accordingly.

---

### 4.5 Models (`app/models/models.py`)

| Model | Role |
|-------|------|
| `User` | Owner of experiments; used for auth and ownership. |
| `LLMModel` | Logical model (e.g. "GPT-4"). |
| `ModelVersion` | Concrete version (e.g. "gpt-4-turbo"); `config_json` holds provider-specific settings. |
| `Comparison` | One experiment: same input, multiple models; `preferred_prediction_id` records the user’s choice. |
| `Prediction` | Single run: model_version, input/output, latency; optionally linked to a comparison. |

**Indexes:**

- `idx_predictions_dedupe` — `(input_hash, model_version_id, created_at)` for fast cache lookup.
- `idx_predictions_comparison` — for `find_by_comparison`.
- `idx_predictions_model_version_created`, `idx_predictions_user_created` — for common query patterns (model/user history).
- `idx_comparisons_user_created` — for listing a user’s comparisons.

**Why these indexes:** Predictions will dominate writes; these indexes support deduplication, comparison listing, and user history without full table scans.

---

### 4.6 App Factory (`app/__init__.py`)

**Setup order:**

1. Create engine with `pool_pre_ping=True` — validates connections before use.
2. Create `SessionLocal` (session factory).
3. Register `before_request` to set `g.db = session_factory()`.
4. Register `teardown_request` to commit (or rollback) and close `g.db`.
5. Instantiate repository, adapter factory, and service (the service instance uses a startup session; request handlers use `g.db` via `get_prediction_service()`).
6. Store `session_factory`, `adapter_factory`, and `prediction_service` in `app.extensions`.

**Why per-request sessions:** Ensures one transaction per request, avoids connection leaks, and keeps requests isolated.

---

## 5. Design Principles

| Principle | How it’s applied |
|-----------|------------------|
| **Layered architecture** | API → service → repository/adapters; each layer has a clear responsibility. |
| **Dependency injection** | Services receive repo and factory; swapping implementations does not require service changes. |
| **Adapter pattern** | Providers are behind `BaseModelAdapter`; adding GPT, Gemini, etc. is a new adapter class. |
| **Repository pattern** | Persistence is behind an interface; services do not depend on SQLAlchemy directly. |
| **Request-scoped DB sessions** | Each request gets its own session; teardown commits or rolls back and closes connections. |

---

## 6. Current Limitations and Planned Work

- **Auth** — `user_id` is hardcoded; JWT and user resolution are planned.
- **config.py** — DB URL is hardcoded; should be loaded from environment.
- **Adapters** — Factory always returns `DummyAdapter`; needs mapping from `model_version_id` to real providers.
- **Experiments API** — Comparisons exist in the model but there is no API yet to create them or set `preferred_prediction_id`.
- **extensions.py, schemas/** — Planned for production hardening and validation.
