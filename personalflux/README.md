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

## Catalog

Three optional sources fill the products table, and `products.catalog_source`
records where each row came from, so a demo row is never presented as a real
listing.

```
cd backend
python ..\scripts\seed_showcase.py                 # curated set with photos (demo)
python ..\scripts\import_catalog_provider.py 100   # DummyJSON demo store (demo)
python ..\scripts\import_affiliate_catalog.py "wireless headphones" "running shoes"
```

The first two are clearly labelled demo data: realistic photos, prices and stock,
but not real brands. The third imports a **live affiliate feed** from the eBay
Browse API and needs `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET` (optionally
`AFFILIATE_CAMPAIGN_ID` for your Partner Network campaign). Item ids are hashed
into their own namespace and rows are upserted by `source_item_id`, so re-running
refreshes price, image and availability instead of duplicating rows. With no
credentials the importer refuses and says what to set rather than inventing data.

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

| file | what it is |
|---|---|
| `docs/SRS.md` | scope, targets, non-goals |
| `docs/ARCHITECTURE.md` | request path, layers, capacity and scaling triggers |
| `docs/API.md` | endpoint contract |
| `docs/DATA_DICTIONARY.md` | tables and columns |
| `docs/MODEL_CARD.md` | offline evaluation writeup |
| `docs/PRIVACY_AND_SECURITY.md` | what is collected, sessions, access control |
| `docs/DEPLOYMENT.md` | compose and production notes |

`docs/MODEL_CARD.md` is what was actually measured. No revenue claims — offline
metrics only.
