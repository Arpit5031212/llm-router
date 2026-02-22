# llm-router Task Tracker

## Phase 1: Fix Blockers and Configuration

- [x] PredictionService implemented
- [x] PredictionRepository + SQLAlchemy impl
- [x] Predictions API (GET, POST)
- [x] SQLAlchemy models (User, LLMModel, ModelVersion, Comparison, Prediction)
- [x] ModelAdapterFactory + BaseModelAdapter
- [x] Dummy adapter (working adapter for dev)
- [ ] GPT adapter
- [ ] config.py (DB URL still hardcoded in app/__init__.py)
- [x] Fix is_acive typo in ModelVersion

## Phase 2: Auth and User Management

- [ ] utils/hashing.py
- [ ] utils/errors.py
- [ ] user_repo.py
- [ ] auth_service.py
- [ ] api/auth.py
- [ ] Integrate auth (JWT, replace hardcoded user_id)

## Phase 3: Experiments and Comparisons

- [ ] comparison_repo.py
- [ ] experiment_service.py
- [ ] api/experiments.py
- [ ] Wire experiments into prediction flow

## Phase 4: Production Hardening

- [ ] extensions.py
- [ ] schemas/
- [ ] Gemini adapter
- [ ] requirements.txt
- [ ] Logging and error handling
