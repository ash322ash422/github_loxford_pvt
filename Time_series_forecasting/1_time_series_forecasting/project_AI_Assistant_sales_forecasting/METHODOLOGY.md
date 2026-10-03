# AI-Powered Sales Forecasting Assistant — What I Built and Why


---

## The one-paragraph version

I built a tool that does two things. First, it **forecasts** daily sales revenue for the next 90 days using machine learning. Second, it lets a user **ask questions about that forecast in plain English** — "how much should we expect next quarter?", "are promotions worth it?" — and get a written answer back from a language model.

The key design decision is that **these two halves are kept strictly separate**. The machine learning model produces the numbers. The language model only *explains* numbers that have already been calculated — it is never allowed to invent one. 

---

## The 10 steps, and why each one exists

### Step 1 — Setup
Imported pandas, numpy, matplotlib and scikit-learn, and fixed the random seed to 42.

**Why the seed matters:** it makes the results *reproducible*. Anyone who runs my notebook gets the exact same numbers I reported. Without it, the "random" data changes every run and my report wouldn't match my code.

### Step 2 — Generated realistic sample data
I don't have a real sales dataset, so I **simulated 4 years of daily revenue** (1,461 days) for a fictional online store. I want to be explicit that this data is synthetic — that's a deliberate choice, not a shortcut.

I built five real-world patterns into it on purpose:
- a slow **growth trend**
- **yearly seasonality** with a big November/December holiday lift
- **weekly seasonality** — weekends are busier
- **promotions** on ~10% of days, adding about 35%
- **random noise** — day-to-day chaos that nothing can predict

**Why simulate?** Because I know the ground truth. I baked in specific effects, so later I can check whether the model *rediscovered* them on its own. With real data you never get to check the answer key. This turns the project into a genuine test of the method.

### Step 3 — Explored the data before modelling
Plotted daily revenue, monthly totals, average by day of week, and promo vs non-promo days.

**Why:** you should always look at your data before you model it. I'm confirming with my own eyes that the patterns I expect are actually visible. If a human can't see a pattern in a chart, a model will struggle to find it too.

### Step 4 — Feature engineering
A model can't read a calendar date — it needs numbers. So I translated each day into 14 **features**:
- **Calendar clues:** day of week, month, is-it-a-weekend, is-it-Q4, a time counter for the trend, and sine/cosine of the day of year
- **Business clues:** was there a promotion
- **Recent-history clues (lags):** revenue 7, 14 and 28 days ago, plus rolling averages

**The sine/cosine trick is worth mentioning.** If I just numbered the days 1–365, the model would think Dec 31 (day 365) and Jan 1 (day 1) are as far apart as possible. Sine and cosine wrap the year into a circle, so the model correctly sees them as neighbours.

### Step 5 — Split the data by TIME, not randomly
I trained on everything except the last 90 days, and hid those final 90 days as a **test set**.

**This is the step to emphasise.** In most machine-learning problems you shuffle your rows and split randomly. **With time series you must never do that.** If you shuffle, the model trains on Friday and Sunday and then "predicts" Saturday — it is peeking at the future. Your accuracy score comes back beautifully and it is completely meaningless. This mistake is called **data leakage**, and it's the most common way forecasting projects fool themselves. Cutting the timeline in one place avoids it: the test set stands in for "the future," made of days the model has genuinely never seen.

### Step 6 — Trained three models, from dumbest to smartest
1. **Seasonal naive** — "next Tuesday will be like last Tuesday." No machine learning at all.
2. **Linear regression** — fits the best straight-line relationship between the features and revenue.
3. **Gradient boosting** — hundreds of small decision trees, each correcting the last one's mistakes.

**Why include a deliberately dumb baseline?** To keep myself honest. If my sophisticated model can't beat "just copy last week," then my sophisticated model is worthless and I've learned something important. A model with no baseline to compare against is an unsupported claim. *Always report a baseline.*

I scored all three three ways:
- **MAE** — average dollars off. Easy to explain to a human.
- **RMSE** — same idea, but punishes big misses much harder.
- **MAPE** — average error as a **percentage**. This is the one to quote to a business audience.

### Step 7 — Opened the model up to see WHY it decides what it decides
An accurate model nobody understands doesn't get used. Linear regression gives a **coefficient** per feature — literally "$X of revenue per unit of this thing." Gradient boosting gives **feature importances**.

The model learned, entirely on its own from the raw numbers, that a promotion is worth roughly **+$509/day**, Q4 roughly **+$333/day**, and a weekend roughly **+$182/day**. Those match the effects I baked in at Step 2 — **which means it rediscovered the truth.** That's my validation that the whole pipeline works.

### Step 8 — Forecast the next 90 days
Two things happened here:

**I retrained on all the data.** The test set had done its job (grading the model), so I let the final model learn from those 90 days too. Your deployed model should always have seen the most recent data.

**I handled the recursion problem.** To predict day 60 in the future, the model wants to know revenue 7 days earlier — day 53 — which hasn't happened yet. So I forecast **one day at a time**, feeding each prediction back in as the input for the next day. Predictions get built on top of predictions.

**This directly explains why long-range forecasts are untrustworthy:** errors compound. Day 3 is solid, day 90 is a stack of 90 guesses.

**I reported a range, not a single number.** I measured how wrong the model was on the unseen test data and used that spread to draw a 95% confidence band around the forecast. Saying "day 47 will be exactly $2,113.42" is false precision. Saying "$2,113, give or take $301" is honest.

### Step 9 — The AI assistant layer
This is what makes it an *assistant* rather than just a statistics script. It works in three moves:

1. **Package the verified facts** — the history, the accuracy scores, the forecast, the top drivers — into a compact text briefing.
2. **Send that briefing plus the user's plain-English question** to a language model (Claude).
3. **The language model writes the answer, grounded in the numbers I gave it.**


### Step 10 — Stated my own limitations
Covered below.

---

## The results

| Model | MAE | RMSE | MAPE |
|---|---|---|---|
| **Linear regression** | **$121** | **$154** | **6.40%** |
| Gradient boosting | $136 | $166 | 7.23% |
| Seasonal naive (baseline) | $313 | $419 | 16.15% |

**Read this out loud: the simple model beat the fancy one.**

This is the most interesting finding in the project, and you should present it as a finding rather than hide it. The reason is that I *built* the data out of straight-line ingredients — a linear trend, a fixed promo lift, a fixed weekend lift. So a straight-line model is exactly the right shape for the problem. Gradient boosting is more flexible, and that extra flexibility is wasted here, and slightly harmful.

**The lesson: the most complicated model is not automatically the best one.** Picking the model that matches the structure of your problem — and *proving* it with a baseline and a fair test — is the actual skill. Anyone can import a fancier algorithm.

Both models comfortably beat the naive baseline, so the machine learning is genuinely earning its keep.

**The forecast:** $151,829 over the next 90 days, versus $170,365 in the previous 90 days — a 10.9% drop. **That drop is not a problem, it's the model being right.** The previous 90 days were October–December (holiday season); the next 90 are January–March (the post-holiday slump). A model that *didn't* predict a Q1 decline would be the broken one. This is a great example to have ready, because it shows you can interpret an output rather than just generate it.

---

## Limitations

Naming your own weaknesses is what separates a B from an A.

- **The data is synthetic.** The model performs well partly because the patterns are cleaner than real life. Real sales data has stockouts, competitor moves, price changes and outliers.
- **Forecast error compounds.** Day 90 is far less reliable than day 3, because it's a prediction built on a stack of predictions.
- **The model can only see what it was given.** No competitor launch, no supply-chain break, no recession — because none of those are columns in my table. Models only know what's in the features.
- **It assumes the past repeats.** All forecasting rests on this. It's a fine assumption right up until it catastrophically isn't (see: any business in March 2020).
- **The confidence band is approximate.** It assumes errors are evenly sized across the whole horizon. They aren't — they grow the further out you go.
- **The language model can only explain, never calculate.** By design. But that means the assistant is only ever as good as the forecast underneath it.

**Next steps I'd take:** compare against Prophet or SARIMA; add real drivers (price, ad spend, weather); use rolling-origin cross-validation instead of one split; forecast each product line separately rather than one lump total.

---

## Questions

**"Why didn't you shuffle your train/test split?"**
Because it's a time series. Shuffling would let the model train on future days to predict past ones — data leakage. It would produce a great-looking accuracy score that means nothing. I split at a single point in time so the test set is genuinely unseen "future."

**"Is the AI making up the forecast?"**
No, and that's deliberate. scikit-learn produces every number. The language model receives those verified numbers and is instructed to explain them and never invent figures. It's an interpretation layer, not a prediction layer.

**"Why is a linear regression beating gradient boosting?"**
Because the underlying data has genuinely linear structure, so the simpler model is correctly specified and the extra flexibility of boosting is wasted. It's a reminder that model complexity should match problem complexity.

**"Why is your forecast lower than last quarter?"**
Seasonality. The comparison period is the Q4 holiday peak and the forecast period is the Q1 post-holiday slump. The model correctly learned the annual cycle.

**"How do you know the model is any good?"**
Two ways. It beats a naive baseline by a wide margin (6.4% error vs 16.2%), and its learned coefficients match the effects I deliberately built into the data — it rediscovered the ground truth on its own.

**"What's MAPE?"**
Mean Absolute Percentage Error — on average, how far off the prediction was as a percentage of the true value. Mine is 6.4%, so the model is typically within about 6% of the real number on days it had never seen.

---
