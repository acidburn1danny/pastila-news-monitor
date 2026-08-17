# Editor Story Word-Budget Product Authority V2

New Editor story generation uses the versioned `STANDARD` profile with an
editorial target of 190 words and a deterministic hard maximum of 210 words.
The target is planning guidance, not a minimum or validation threshold. Total
story content through 210 words is valid; 211 words produces
`word_budget_exceeded`. Retry guidance reports only the minimum reduction needed
to reach 210 or fewer words.

The authority is independent of ranking or relevance score, provider, model,
and source or article count. Canonically merged events retain their approved
facts while using the same STANDARD 190/210 authority.

The V1 planning proportions are applied deterministically: floor one quarter of
the target for the factual summary, floor three sixteenths for the ending, and
the exact remainder for commentary. At 190 words this gives 47 words for the
factual summary, 108 for commentary blocks, and 35 for the ending. These are
drafting allocations only; only the combined story has the 210-word ceiling.

At a non-binding conversational Romanian delivery range of 130–160 words per
minute, a 190-word story is about 71–88 seconds. Story content alone is about
5.9–7.3 minutes for five stories, 8.3–10.2 minutes for seven, and 11.9–14.6
minutes for ten. Openings, transitions, closings, and calls to action remain
separate.

Historical `story-word-budget-v1` 150/170 data remains readable and unchanged;
new generation identifies its authority as `story-word-budget-v2`.
