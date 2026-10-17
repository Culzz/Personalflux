# Data dictionary

PostgreSQL. App entities use UUID primary keys; source dataset ids are kept
separately. Times are `timestamptz` and default to `now()`. Money is
`numeric(12,2)`, never a float. `RESTRICT` on `product_id` means a product with
history cannot be deleted while that history exists; `CASCADE` on `user_id`
means deleting an account removes that user's rows.

## users

| column | type | notes |
|---|---|---|
| id | uuid | PK |
| email | varchar(320) | unique |
| password_hash | text | Argon2id; never the password |
| role | varchar(20) | `customer` \| `analyst` \| `admin` \| `ml_engineer`, default `customer` |
| is_active | bool | default true |
| tracking_consent | bool | default false; tracking is off until opt-in |
| profile_reset_at | timestamptz | null; signals and recommendations ignore events before this time |
| created_at | timestamptz | |

## products

| column | type | notes |
|---|---|---|
| id | uuid | PK |
| source_item_id | bigint | unique, null; the dataset's own id |
| catalog_source | varchar(30) | default `retailrocket`; marks demo rows so they are not mistaken for real ones |
| title | varchar(300) | |
| description | text | null |
| category | varchar(100) | indexed, null |
| price | numeric(12,2) | null |
| image_url | varchar(500) | null |
| is_active | bool | default true; inactive products are never recommended |
| created_at / updated_at | timestamptz | |

## interactions

Append-only behavioural events.

| column | type | notes |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK users, cascade, null |
| session_id | varchar(64) | null; anonymous visitor |
| product_id | uuid | FK products, restrict, null (a `search` has no product) |
| event_type | varchar(20) | `view` \| `click` \| `search` \| `compare` \| `add_to_cart` \| `purchase` \| `save` \| `dismiss` |
| context | jsonb | null; e.g. search category |
| idempotency_key | varchar(64) | unique, null; a retried request is not stored twice |
| occurred_at | timestamptz | client time |
| created_at | timestamptz | server time |

Constraints: a row must name a `user_id` or a `session_id`; a non-`search`
event must name a `product_id`. Indexed by (user, time), (session, time),
product, and event_type.

## recommendation_impressions

What was actually shown, and where in the list. Feeds live-activity analytics.

| column | type | notes |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK users, cascade, null |
| session_id | varchar(64) | null |
| product_id | uuid | FK products, restrict |
| request_id | varchar(64) | ties an impression to one recommendation response |
| model_version | varchar(100) | null; which model produced the slot |
| position | int | rank in the list, 1-based |
| created_at | timestamptz | |

## saved_items

| column | type | notes |
|---|---|---|
| user_id | uuid | FK users, cascade, PK |
| product_id | uuid | FK products, restrict, PK |
| created_at | timestamptz | |

## preferences

Explicitly stated only. Inferred interests are computed per request, never stored.

| column | type | notes |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK users, cascade |
| preference_type | varchar(40) | `liked_categories` \| `blocked_categories` \| `price_range` |
| preference_value | jsonb | list, or `{min,max}` for price |
| source | varchar(10) | `explicit` \| `inferred`, default `explicit` |
| updated_at | timestamptz | |

Unique on (user_id, preference_type).

## refresh_tokens

| column | type | notes |
|---|---|---|
| id | uuid | PK |
| user_id | uuid | FK users, cascade, indexed |
| token_hash | varchar(64) | unique; only the hash is stored, the raw token is the cookie |
| expires_at | timestamptz | |
| revoked_at | timestamptz | null; set on logout or on reuse of a rotated token |
| created_at | timestamptz | |

## model_versions

| column | type | notes |
|---|---|---|
| id | uuid | PK |
| version | varchar(100) | unique; artifact folder name |
| artifact_uri | varchar(500) | |
| status | varchar(20) | `candidate` \| `serving` \| `retired` \| `failed_validation` |
| details | jsonb | null; validation summary |
| created_at | timestamptz | |
| promoted_at | timestamptz | null |

## experiments / evaluation_runs

Offline evaluation. Kept apart from live engagement on purpose.

| experiments | |
|---|---|
| id | uuid PK |
| name | varchar(200) unique |
| configuration | jsonb null |
| created_at | timestamptz |

| evaluation_runs | |
|---|---|
| id | uuid PK |
| experiment_id | FK experiments, cascade, indexed |
| model_version | varchar(100) null |
| metrics | jsonb (recall, k, and friends) |
| created_at | timestamptz |

## audit_logs

Security-relevant admin actions. Survives deletion of the acting user.

| column | type | notes |
|---|---|---|
| id | uuid | PK |
| actor_user_id | uuid | FK users, set null on delete |
| action | varchar(60) | e.g. `product.update`, `model.promote` |
| target_type | varchar(40) | |
| target_id | varchar(100) | null |
| details | jsonb | null |
| created_at | timestamptz | indexed |
