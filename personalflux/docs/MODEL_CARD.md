# PersonaFlux Model Card (offline evaluation, v0.1)

## Intended use
Rank products for an e-commerce session or returning visitor, to support
"similar items" and "for you" feeds. Offline research prototype. Not validated
on live customers, and no claim is made about revenue or satisfaction.

## Data
Retailrocket e-commerce dataset (Kaggle). License: [verify on the Kaggle page and
fill in; to my understanding non-commercial, share-alike].
- 2,755,641 events after removing 460 duplicates, 2015-05-03 to 2015-09-18
- About 1.4M visitors and 235k items. Event types: view, addtocart, transaction.
- NOT present: clicks, saves, dismissals, titles, descriptions, demographics.
- Chronological split: train to 2015-08-21, validation 14 days, test 14 days.
- Item categories (root level) known for 78.9% of train items and 81.7% of
  validation items. The category table is a snapshot at the train cutoff.

## Models
1. Popularity (last 14 days, weighted view=1, cart=4, purchase=5)
2. Item-to-item collaborative filtering (cosine similarity, users with more than
   50 items excluded as likely bots)
3. Session-KNN: item-KNN scored from the items viewed in the current session
4. Long-term blend: session score + 0.5 x user's history score (fixed weight)
5. Shift-aware weighting: long-term weight x (1 - shift score). Instrumented, not validated.

## Evaluation protocol
- Fit on train + validation, evaluated once on the test window (pre-declared;
  results saved in ml/reports/test_eval.csv).
- Session examples: items viewed before the first cart/purchase are the context;
  later carted/bought items are the targets.
- NEW variant: targets the visitor had not viewed in the session (real discovery).
  ALL variant: includes already-viewed items (mostly re-surfacing).
- Metrics: Recall@K, NDCG@K, MRR, catalog coverage. 95% CIs from bootstrap
  resampling of visitors.

## Results (test window, Recall@10)
| Set | Model | Recall@10 | Notes |
|---|---|---|---|
| NEW, all visitors (305 sessions) | popularity | 0.003 | |
| | session-KNN | 0.099 | +0.096, 95% CI [+0.064, +0.133] |
| NEW, visitors with history (101 sessions, 55 visitors) | popularity | 0.006 | |
| | session-KNN | 0.040 | |
| | + long-term blend | 0.055 | +0.015 vs session-KNN, CI [+0.003, +0.035] |
| | shift-aware blend | 0.055 | identical to fixed blend |
| ALL targets (983 sessions) | re-show viewed items | 0.779 | reference |
| | session-KNN | 0.175 | |

Validation results agreed on session-KNN vs popularity (+0.088, CI [+0.054, +0.127]).

## Findings
- Item co-occurrence from the current session clearly beats popularity at
  discovering new items.
- A long-term profile gives a small gain (about 1.5 recall points), but the
  evidence is weak: it was not distinguishable on validation and only just clear
  on test, with few visitors.
- Shift-aware weighting had no measurable effect. Adaptation is untested here.
- About 18% of relevant user-level pairs are repeat items. Most carts are of
  items already viewed in the session.

## Limitations
- Implicit feedback only. A missing interaction does not mean disinterest.
- Most visitors are anonymous one-time browsers. Only 27% of carting sessions
  come from visitors with training history.
- Small evaluation slices for returning visitors; wide uncertainty.
- Items first seen after the training period have no similarity scores (cold items).
- Category metadata is a train-time snapshot, with about 20% of items uncategorised.
- Data is from 2015 and one retailer. Generalisation is unknown.
- Offline metrics do not measure business outcomes. Live experiments are required.
- Several comparisons were run. Isolated "clear" results should be treated cautiously.

## Risks and safeguards
- Popularity bias: tracked via coverage (the popularity baseline recommends about 20 items).
- Explanations must reflect signals that actually fired.
- Customers must be able to reset inferred preferences (SRS FR-04).