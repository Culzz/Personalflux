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
- Two-stage view on the validation window (ml/reports/stage_eval.csv): candidate
  recall next to Recall@K, so a miss can be read as retrieval or as ordering.

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

## Where the recommendation is lost (validation window)

Recall@10 says a model missed; it does not say whether the item was never a
candidate or was a candidate that got ranked too low. `ml/reports/stage_eval.csv`
splits every session into hits, items the generator never proposed, and items it
proposed but ranked below the cut. Candidate recall is the ceiling the ranking
step works against, so a model using little of it has an ordering problem and a
model with a low ceiling has a retrieval problem.

NEW variant, 311 sessions, k = 10, validation window:

| Model | candidates/session | candidate recall | Recall@10 | of that ceiling | misses that are retrieval | misses that are ranking |
|---|---|---|---|---|---|---|
| popularity (14d) | 500 | 0.136 | 0.015 | 0.11 | 88% | 12% |
| session-KNN | 197 | 0.296 | 0.103 | 0.35 | 84% | 16% |
| session hybrid | 688 | 0.368 | 0.093 | 0.25 | 74% | 26% |

- The generator is the bottleneck, not the ordering: 77% of sessions have at
  least one relevant item the generator never proposed at all, so a better ranker
  alone cannot fix most misses.
- Adding popularity to the candidates raises the ceiling from 0.296 to 0.368, but
  recall@10 falls from 0.103 to 0.093. The extra candidates are mostly
  irrelevant, and the ranking step spends more of its budget on them (26% of
  misses are ordering, against 16% for session-KNN). A wider candidate set is
  only worth it with a ranker that can demote popularity fillers.
- These are item-level counts of what was lost, not a claim that any single
  change to the ranker would recover them.

## Findings
- Item co-occurrence from the current session clearly beats popularity at
  discovering new items.
- Most misses are retrieval misses, not ordering misses: the generator never
  proposes the item. Widening the candidate set without improving the ranking
  step can lower Recall@10 (see the stage breakdown above).
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