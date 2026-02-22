# llm-router

a simplified OpenRouter-style system where users can run the same prompt against multiple LLM providers, compare responses, and select preferred outputs. The system uses a clean adapter pattern, stores experiments and predictions in a relational database, and is designed with production-grade concerns like logging, indexing, and extensibility.

app/
├── **init**.py # create_app()
├── config.py
├── extensions.py # db, jwt
│
├── api/
│ ├── **init**.py
│ ├── auth.py
│ ├── predictions.py
│ ├── experiments.py
│
├── domain/
│ ├── model.py
│ ├── prediction.py
│ ├── comparison.py
│
├── services/
│ ├── auth_service.py
│ ├── prediction_service.py
│ ├── experiment_service.py
│
├── repositories/
│ ├── user_repo.py
│ ├── prediction_repo.py
│ ├── comparison_repo.py
│
├── adapters/
│ ├── base.py
│ ├── gpt_adapter.py
│ ├── gemini_adapter.py
│
├── schemas/
│ ├── auth.py
│ ├── prediction.py
│
└── utils/
├── hashing.py
├── errors.py
