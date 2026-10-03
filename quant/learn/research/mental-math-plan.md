# Mental-math plan: 12 days to the PFRDA Phase I exam (3 Oct to 14 Oct 2026; exam 15 Oct 2026)

Scope: study-skill advice only. No diagnosis, no medical claims. Every claim below comes from a page fetched in this session (URL given) or is marked UNVERIFIED / general advice.

## 1. What the exam allows (rough work)

- Official PFRDA notification (fetched, text extracted): Phase I is an on-line exam on 15 Oct 2026. Paper 1 has 90 questions in 60 minutes, including Quantitative Aptitude (20 questions, 25 marks). There is 1/4 negative marking. https://pfrda.org.in/documents/33652/212847/Recruitment+of+Officer+Grade+A+(Assistant+Manager)-2026.pdf
- Rough sheet, scratch pad or on-screen calculator for PFRDA: **UNVERIFIED.** I searched that 32-page notification for "calculator", "rough", "scratch" and "sheet", and none of these appear in an exam-rules sense. Check the call letter and the exam-day instruction page.
- Other exams (not PFRDA, so only a hint): an NMIMS online-exam page (search result only, page not fetched) says its on-screen Notepad and Calculator are provided, and physical A4 sheets are allowed only under webcam rules. I did not fetch IBPS pages successfully (503 on the official PDF), so IBPS rules are UNVERIFIED as well.
- Plan for both cases: practise on paper now. Before the exam, also practise typing steps into any on-screen notepad if one is offered. If neither exists, use the methods that keep fewer numbers in your head (section 3).

## 2. What fetched pages say

- Working memory and maths: children "have to hold on to information, like a formula, an answer from a previous step, or the steps of the problem itself," and "can get lost in the problem" when working memory is weak; disorganised scratch work makes this worse. Source (Understood.org): https://www.understood.org/en/articles/ways-executive-functioning-challenges-can-impact-math . (It addresses children, so use it as general context.)
- Left-to-right addition: a K5 Learning page describes the front-end strategy as "subtracting from left to right: subtract the hundreds, then the tens and then the ones." It also lists compensation, equal additions, compatible numbers and counting on. https://www.k5learning.com/blog/using-mental-math-tricks-subtraction
- Manitoba Education mental-math guide (PDF, text extracted): compatible/friendly numbers and compensation, for example 850 - 375 = 850 - 350 - 25 = 475, and 1250 - 753 = 1250 - 750 - 3 = 497. The guide says this avoids regrouping and keeps place value. It also has estimation strategies: compatible numbers, common rounding, front-end rounding. https://www.edu.gov.mb.ca/k12/framework/publications/math/mm_gr8/docs/strategies.pdf
- Spacing and retrieval: the Australian Education Research Office guide says spacing "allows students to remember more in the long term," that separating learning by at least one day beats massed practice, that "any delayed review of learning is better than none," and that retrieval works best as low-risk, high-challenge recall rather than restudying. https://www.edresearch.edu.au/guides-resources/practice-guides/spacing-and-retrieval-practice-guide-full-publication
- Short blocks and structure: the NHS ADHD page (written for children and young people) suggests splitting tasks into "15 to 20 minute slots with a break in between," writing a to-do list "somewhere easy to see," regular physical activity and regular sleep. https://www.nhs.uk/conditions/attention-deficit-hyperactivity-disorder-adhd/living-with/
- CDC: follow "the same schedule every day"; "for long tasks, starting early and taking breaks may help limit stress." https://www.cdc.gov/adhd/treatment/index.html
- Not verified: timers and body-doubling. I fetched no page on them, so treat them as optional personal experiments. A phone timer is simply how you do the 15-20 minute slot above.
- Chunking, number bonds, complement subtraction: I fetched no ADHD-specific evidence for these. The methods are described in the Manitoba and K5 pages above. Complement subtraction (100 - 37 = 63) is a standard method I checked in Python, with no fetched source for the method.
- I did not find a fetched page showing that any of these methods improves calculation in adults with ADHD. Treat the plan as a reasonable practice routine, not a proven treatment.

General advice (no fetched source specific to maths): if a sudden or significant decline in mental maths or memory is new and worrying, talking to a doctor is reasonable. An NHS hospital page says to speak to a doctor if memory "has changed significantly from what is usual for you." https://www.cuh.nhs.uk/patient-information/managing-memory-problems/

## 3. Methods (all verified in Python, 20,000 random cases each: `mental_math_verify.py`)

1. **Left-to-right addition, writing partial sums.** 348 + 735: write 348, +700 = 1048, +30 = 1078, +5 = 1083. One number is written down at each step.
2. **Friendly-number (compensation) subtraction and addition.** 621 - 49 = 621 - 50 + 1 = 572. Write the rounded step and the fix-up.
3. **Complement from 100 or 1000** (nines rule: all digits from 9, last non-zero digit from 10; trailing zeros stay zero). 1000 - 372: 6, 2, 8 = 628. 100 - 40 = 60.
4. **Count up.** 812 - 575: 575 to 600 is 25, 600 to 800 is 200, 800 to 812 is 12; total 237. Write each hop.
5. **Estimate then check (add and subtract only).** Round to the leading digit, work it out, then see if the exact answer is close. I did not verify estimation for multiplication: rounding can be off by about 78% (Python check, two-digit pairs). Use a rough size check only.
6. **Number bonds**: pairs that make 10 and 100 (3+7, 38+62). Use them inside methods 2 and 3. There is no separate drill.

## 4. Daily routine (10-20 minutes, same time each day)

1. Pen and paper. Write down your plan: "Today: methods X and Y."
2. Warm-up recall, 2 minutes, from memory, no peeking: write the method names and one worked example from an earlier day (spaced retrieval).
3. Today's drills (below), timer set for 12 minutes max. Write every step. Cover the answer key and check it after each block.
4. Mark each error: wrong method step, slip, or skipped writing. Put each missed question on a "redo tomorrow" list (retrieval plus a gap of at least one day).
5. Stop at the timer. Short break or a walk. If it was a hard day, finish; do not add extra.

Wrong answers are normal: they only mean a step needs to be written down more clearly.

## 5. 12-day plan

| Day | Date | Focus | Time |
|---|---|---|---|
| 1 | 3 Oct | Left-to-right addition | 10 min |
| 2 | 4 Oct | Left-to-right add + friendly subtraction | 15 |
| 3 | 5 Oct | Friendly subtraction + complements | 15 |
| 4 | 6 Oct | Complements + count up | 15 |
| 5 | 7 Oct | Mixed (add, friendly, complement); redo day 1-2 misses | 15 |
| 6 | 8 Oct | Count up + estimate-then-check | 15 |
| 7 | 9 Oct | Mixed review, all four methods; redo misses | 20 |
| 8 | 10 Oct | Estimate-then-check + addition | 15 |
| 9 | 11 Oct | Friendly + complements + count up | 15 |
| 10 | 12 Oct | Mixed with estimates | 15 |
| 11 | 13 Oct | Full mix, 4 methods; redo misses | 20 |
| 12 | 14 Oct | Light review (about 10 min), then rest, sleep, check exam logistics | 10 |

Exam day tip (general, not sourced): on a calculation question, write the method steps down, skipping nothing. If a question is taking too long, skip it. Remember that Paper 1 has negative marking (1/4).

## 6. Drills (generated and checked by `gen_drills.py`; the answer key is auto-verified against the method)

**Day 1 drills** (write each step on paper)
- ltr:
  1. 241 + 447
  2. 634 + 644
  3. 782 + 225
  4. 348 + 735
  5. 756 + 689
  6. 550 + 706
- Answer key (check AFTER): 1=688, 2=1278, 3=1007, 4=1083, 5=1445, 6=1256

**Day 2 drills** (write each step on paper)
- ltr:
  1. 680 + 868
  2. 622 + 889
  3. 720 + 571
  4. 365 + 122
  5. 748 + 202
  6. 233 + 414
- friendly:
  7. 838 - 38
  8. 650 - 29
  9. 837 - 99
  10. 671 - 99
  11. 580 - 49
  12. 623 - 58
- Answer key (check AFTER): 1=1548, 2=1511, 3=1291, 4=487, 5=950, 6=647, 7=800, 8=621, 9=738, 10=572, 11=531, 12=565

**Day 3 drills** (write each step on paper)
- friendly:
  1. 598 - 67
  2. 832 - 69
  3. 801 - 87
  4. 746 - 38
  5. 790 - 67
  6. 465 - 87
- comp:
  7. 1000 - 305
  8. 1000 - 155
  9. 1000 - 36
  10. 1000 - 383
  11. 1000 - 443
  12. 100 - 62
- Answer key (check AFTER): 1=531, 2=763, 3=714, 4=708, 5=723, 6=378, 7=695, 8=845, 9=964, 10=617, 11=557, 12=38

**Day 4 drills** (write each step on paper)
- comp:
  1. 1000 - 899
  2. 100 - 65
  3. 1000 - 418
  4. 1000 - 875
  5. 1000 - 588
  6. 1000 - 536
- countup:
  7. 765 - 125
  8. 794 - 329
  9. 892 - 232
  10. 918 - 150
  11. 992 - 821
  12. 767 - 205
- Answer key (check AFTER): 1=101, 2=35, 3=582, 4=125, 5=412, 6=464, 7=640, 8=465, 9=660, 10=768, 11=171, 12=562

**Day 5 drills** (write each step on paper)
- ltr:
  1. 854 + 757
  2. 559 + 601
  3. 265 + 613
  4. 354 + 244
- friendly:
  5. 740 - 197
  6. 653 - 99
  7. 660 - 197
  8. 895 - 87
- comp:
  9. 1000 - 584
  10. 1000 - 696
  11. 1000 - 572
  12. 1000 - 835
- Answer key (check AFTER): 1=1611, 2=1160, 3=878, 4=598, 5=543, 6=554, 7=463, 8=808, 9=416, 10=304, 11=428, 12=165

**Day 6 drills** (write each step on paper)
- countup:
  1. 952 - 511
  2. 721 - 307
  3. 650 - 525
  4. 637 - 104
  5. 516 - 176
  6. 835 - 711
- est:
  7. 735 - 669  (estimate first, then exact)
  8. 568 - 404  (estimate first, then exact)
  9. 909 - 697  (estimate first, then exact)
  10. 985 - 723  (estimate first, then exact)
  11. 644 + 771  (estimate first, then exact)
  12. 524 - 497  (estimate first, then exact)
- Answer key (check AFTER): 1=441, 2=414, 3=125, 4=533, 5=340, 6=124, 7=66, 8=164, 9=212, 10=262, 11=1415, 12=27

**Day 7 drills** (write each step on paper)
- ltr:
  1. 220 + 568
  2. 825 + 853
  3. 647 + 385
  4. 583 + 307
- friendly:
  5. 637 - 396
  6. 792 - 78
  7. 452 - 99
  8. 556 - 78
- comp:
  9. 1000 - 109
  10. 100 - 63
  11. 100 - 68
  12. 100 - 22
- countup:
  13. 500 - 331
  14. 797 - 659
  15. 977 - 185
  16. 812 - 303
- Answer key (check AFTER): 1=788, 2=1678, 3=1032, 4=890, 5=241, 6=714, 7=353, 8=478, 9=891, 10=37, 11=32, 12=78, 13=169, 14=138, 15=792, 16=509

**Day 8 drills** (write each step on paper)
- est:
  1. 453 + 323  (estimate first, then exact)
  2. 969 - 759  (estimate first, then exact)
  3. 975 - 884  (estimate first, then exact)
  4. 358 - 205  (estimate first, then exact)
  5. 880 - 797  (estimate first, then exact)
  6. 906 + 937  (estimate first, then exact)
- ltr:
  7. 678 + 348
  8. 604 + 722
  9. 254 + 732
  10. 829 + 636
  11. 417 + 206
  12. 547 + 804
- Answer key (check AFTER): 1=776, 2=210, 3=91, 4=153, 5=83, 6=1843, 7=1026, 8=1326, 9=986, 10=1465, 11=623, 12=1351

**Day 9 drills** (write each step on paper)
- friendly:
  1. 501 - 47
  2. 821 - 298
  3. 888 - 98
  4. 576 - 87
- comp:
  5. 1000 - 410
  6. 100 - 77
  7. 100 - 59
  8. 100 - 24
- countup:
  9. 699 - 175
  10. 526 - 277
  11. 830 - 461
  12. 978 - 888
- Answer key (check AFTER): 1=454, 2=523, 3=790, 4=489, 5=590, 6=23, 7=41, 8=76, 9=524, 10=249, 11=369, 12=90

**Day 10 drills** (write each step on paper)
- ltr:
  1. 146 + 146
  2. 642 + 607
  3. 455 + 819
  4. 430 + 580
- friendly:
  5. 586 - 38
  6. 674 - 78
  7. 712 - 98
  8. 832 - 47
- est:
  9. 357 + 805  (estimate first, then exact)
  10. 838 - 644  (estimate first, then exact)
  11. 669 + 812  (estimate first, then exact)
  12. 894 + 927  (estimate first, then exact)
- Answer key (check AFTER): 1=292, 2=1249, 3=1274, 4=1010, 5=548, 6=596, 7=614, 8=785, 9=1162, 10=194, 11=1481, 12=1821

**Day 11 drills** (write each step on paper)
- comp:
  1. 1000 - 45
  2. 100 - 93
  3. 100 - 16
  4. 100 - 68
- countup:
  5. 944 - 872
  6. 828 - 293
  7. 747 - 120
  8. 566 - 430
- est:
  9. 742 + 423  (estimate first, then exact)
  10. 364 + 877  (estimate first, then exact)
  11. 599 - 479  (estimate first, then exact)
  12. 745 + 624  (estimate first, then exact)
- ltr:
  13. 512 + 432
  14. 311 + 472
  15. 298 + 389
  16. 595 + 629
- Answer key (check AFTER): 1=955, 2=7, 3=84, 4=32, 5=72, 6=535, 7=627, 8=136, 9=1165, 10=1241, 11=120, 12=1369, 13=944, 14=783, 15=687, 16=1224

**Day 12 drills** (write each step on paper)
- ltr:
  1. 545 + 414
  2. 598 + 301
  3. 453 + 651
  4. 613 + 575
- friendly:
  5. 481 - 87
  6. 827 - 87
  7. 827 - 58
  8. 837 - 38
- comp:
  9. 100 - 40
  10. 100 - 22
  11. 1000 - 672
  12. 1000 - 428
- Answer key (check AFTER): 1=959, 2=899, 3=1104, 4=1188, 5=394, 6=740, 7=769, 8=799, 9=60, 10=78, 11=328, 12=572

