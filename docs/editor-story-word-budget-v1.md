# Editor Story Word-Budget Product Authority V1

All generated Editor stories use the versioned `STANDARD` profile:

- editorial target: 150 words;
- deterministic hard maximum: 170 words.

The target guides prompt planning but is not a validation threshold. Total story
content through 170 words is valid; 171 words produces `word_budget_exceeded`.
Retry guidance reports the observed count and the minimum reduction required to
reach 170 or fewer words.

The authority is independent of ranking score and source count. Canonically
merged events retain their approved facts, while one, two, or many contributing
sources use the same target and ceiling. Historical outputs produced under the
older score-derived policy remain unchanged historical evidence.

The deterministic target allocation is a drafting aid, not component-level
validation: 37 words for factual summary, 85 for commentary blocks, and 28 for
the ending. Only the combined story has the 170-word hard ceiling.

At a conversational Romanian delivery of roughly 130–160 words per minute, a
150-word story is about 56–69 seconds. Story content alone is therefore about
4.7–5.8 minutes for five stories, 6.6–8.1 minutes for seven, or 9.4–11.5 minutes
for ten. Openings, transitions, closings, and calls to action remain separate
components and are not included in these estimates.
