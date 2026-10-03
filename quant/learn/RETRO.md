# Retro: PFRDA Quant Lab
## What worked
- Arena-style fan-out on the exemplar (3 candidates, judged, best parts grafted) gave a template that scaled to 27 chapters.
- Adversarial fact-check (opus, one per chapter) found roughly 140 issues. Most were wrong or meaningless wrong-option explanations, ambiguous questions with two correct answers, and unsourced claims. Some were real: a lab that froze the page in an endless loop (ch02), a false claim about radar-chart areas (ch20), a wrong partnership explanation (ch05), wrong figures in my own priority chapter (01b).
- Research agents refused to guess: PFRDA has only two usable years of counts, and they said so. A coaching page (Oliveboard mixture) printed a wrong ratio; Python caught it.
- Automated checks: 346 quiz questions structurally valid, 551 arithmetic statements scanned, 27 chapters swept at 375px light and dark with 0 failures, 40,000 generated practice questions recomputed.
## What did not work
- Writers reported their own checks as passing; independent checkers still found errors. Never skip the second pair of eyes.
- The student-review pass added arithmetic checked by hand only. The later arithmetic scan found no errors, but it only covers simple a-op-b=c statements.
- First session lost its files (Windows paths not visible in the cloud). Costed time and left the user's own notes unused.
- 20-subagent cap forced batching. Shared scratchpad caused one script overwrite.
- Stop-hook warnings about unpushed commits were stale local tracking refs; git ls-remote showed the remote was current.
## Next time
- Get the user's notes into the repo first. Run a real-browser test on every lab before the fact-check, not after.
