# PFRDA Grade A Phase 1 — Quant Learning Guide: SPEC (shared by all writers)

## Verified exam facts (source: official PFRDA notification, pfrda.org.in/documents/33652/212847/Recruitment+of+Officer+Grade+A+(Assistant+Manager)-2026.pdf, pp.6-7)
- Phase I online exam: 15 Oct 2026 (Thursday). Paper 1 (all streams), 60 minutes TOTAL for 4 sections:
  English 20 Q/25 marks; **Quantitative Aptitude 20 Q/25 marks**; Reasoning 30 Q/25 marks; General Awareness 20 Q/25 marks. Total 90 Q/100.
- So each Quant question = 1.25 marks. Negative marking = 1/4 of marks assigned = 0.3125 per wrong answer.
- Separate cut-off in each paper + aggregate cut-off. Phase I marks only shortlist for Phase II.
- The official notification gives NO topic-level Quant syllabus (Annexure covers Paper 2 only). Topic lists come from coaching sites
  (Oliveboard, Edutap) — label them "third-party topic list, not official". Never claim the topic list is official.
- Sources differ: one search snippet said "25 questions/20 marks" for English/Quant; official PDF says 20 Q/25 marks. Official wins.
## Past-paper evidence (label every use: "reported in memory-based exam analyses")
- 2025 (6 Sep): DI 8 (5+3), Quadratic Eq 5, Partnership 1, SI/CI 1, Trains 1, Time&Work 1, Rectangle 1, Ages 1, Average 1 (=20). "easy to do 7-8 questions", "10+ good attempt". (edutap.in/pfrda-grade-a/exam-analysis/)
- 2022 (5 Nov): Number Series 5, DI 5, Averages 3, TSD 2, P&L 1, Partnership 1, Time&Work 1, Interest 1 (edutap; sums 19) ; practicemock adds Percentage 1. Easy-moderate.
- Third-party topic list (Oliveboard): DI (bar, line, table, caselet, radar, pie), Inequalities (quadratic), Number Series, Approximation & Simplification, Data Sufficiency, Misc Arithmetic (HCF/LCM, P&L, SI&CI, Ages, Time&Work, TSD, Probability, Mensuration, P&C, Average, Ratio, Partnership, Boats&Stream, Trains, Mixture&Alligation, Pipes&Cisterns).
- Edutap list adds: Percentage, Quantity Comparisons, Mathematical Inequalities.

## HARD RULES
1. No hallucination. Maths facts must be standard & verified: every worked example's arithmetic MUST be checked by running Python (put the check in your report). Every definition/formula must be one you can cite to a page you actually fetched (e.g. NCERT, Khan Academy, Wikipedia-for-definitions, a standard textbook page) — give URL in the lesson's "Sources" line. If you cannot verify something, omit it and list under UNVERIFIED.
2. Learner: zero background, ADHD (short chunks, one next action), poor mental math, goal = full marks (20/20 attempted correctly). Wants speed + accuracy under 60-min paper (~ 12 min for quant is the budget; label that as a suggested plan, not official).
3. Output = ONE self-contained HTML FRAGMENT per lesson (no <html>/<head>): a <section class="lesson" id="..."> using only classes defined in the shared CSS (see TEMPLATE once chosen). Mobile-first (375px), light+dark safe (use CSS variables only, no hard-coded colours), no external scripts. Small vanilla JS allowed inside <script> only for quiz/lab; scope with IIFE and ids.
## LESSON FORMAT (all required, in this order)
1. One plain-English line ("In one line: ...")
2. "Picture this" — an everyday Indian-context scenario
3. The idea in small steps (numbered, each ≤ 2 sentences)
4. Formula/rule ONLY after intuition (box)
5. Worked example, stepped (reveal-next-step button or numbered)
6. The trap (common wrong move, shown with the wrong number)
7. Mental-math shortcut for this topic (precompute table / trick, with a practice drill)
8. How the examiner asks (typical wording; mark as typical-style, not a claim about a specific paper unless sourced)
9. Quiz: ≥4 MCQs, correct answer position varied across A-D, each with explained answer, instant feedback
10. Cover-and-recall box ("Cover the page, say it out loud") + "Memorise this" box (≤5 lines)
11. Sources line + UNVERIFIED line (may be "none")
Numerical topics get a small interactive lab (sliders/inputs). Conceptual ones get tables/diagrams.
