# Adversarial fact-check brief (one chapter per checker)
You are a hostile reviewer. Assume the writer made errors. Chapter file: chapters/NN-*.html (reasoning).
1. Extract EVERY: formula, definition, numerical worked example, quiz question+answer+explanation, drill item, table value, threshold, exam fact, past-paper count.
2. Re-derive each numeric item independently in Python (do not reuse the writer's scripts). Check each quiz: exactly one correct option, correct index matches `a`, `t` array aligned to options with "" at index `a`, explanation consistent.
3. Check each formula/definition against a page you WebFetch (cite URL). If you cannot find a source, keep it only if it is a mathematical identity you proved/verified in Python, and label it 'derived, Python-checked' in the lesson Sources line; otherwise delete it and list in UNVERIFIED.
4. Check exam facts vs SPEC.md verified block (Reasoning 30Q/25 marks (0.8333 each), -1/4 (flat -0.25 per wrong, user-directed), 60-min shared paper, 15 Oct 2026). Past-paper counts must say 'reported in memory-based exam analyses'. Remove any claim not backed by SPEC or a fetched page.
5. Check ambiguity: any question with two defensible answers, or unclear wording -> rewrite.
6. Fix errors IN PLACE in the chapter file (keep structure, ids, classes). Do not touch other files. Re-validate: html.parser balanced, JSON parses, ids unique & chNN- prefixed, node --check on inline scripts.
7. Report (<150 words): errors found (count + one-line each), what you fixed, items removed, remaining UNVERIFIED, single-source claims.
