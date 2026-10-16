# PersonaFlux

Adaptive customer personalization for e-commerce.
Long-term preferences + recent intent = recommendations that adapt.

## Run it

```
cp .env.example .env
# set JWT_SECRET_KEY in .env (32+ chars)
docker compose up --build
```

- API: http://localhost:8000/health, docs at /docs (dev only)
- Storefront: http://localhost:5173

Local dev without compose:

```
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

```
cd frontend
npm ci
npm run dev
```

## Tests

```
cd backend
python -m pytest -q
```

```
cd frontend
npm test
npm run build
```

## ML

Retailrocket data, chronological splits. Results in `ml/reports/test_eval.csv`,
writeup in `docs/MODEL_CARD.md`. Session-KNN beats popularity on new-item
discovery; long-term blend helps a little for returning visitors.

## Docs

`docs/API.md` is the contract. `docs/MODEL_CARD.md` is what was actually
measured. No revenue claims — offline metrics only.
