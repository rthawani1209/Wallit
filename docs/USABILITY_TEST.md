# Usability test

A 15-minute test you can run with 5 people. Five people is the usual number to find most of the big problems. It gives you real numbers you can quote: task success, time on task, and a System Usability Scale (SUS) score. The tasks run on the demo, so nobody links a real bank.

## Before you start

- Send each person the demo link: `https://wallit-xi.vercel.app/demo`. Each person gets a fresh demo account with the same sample data.
- Ask them to think out loud. Don't help unless they're stuck for 2 minutes. That task then counts as a fail.
- Time each task from when you finish reading it until they say the answer. A phone stopwatch is fine.
- Write down where they hesitated or clicked the wrong thing. Those notes are what you fix.

## Tasks

Read each task out loud, exactly as written.

| # | Task | Correct when they… |
|---|---|---|
| 1 | "How much can you safely spend before your next paycheck?" | say the safe-to-spend amount |
| 2 | "Which bill is due next, and how much is it?" | name the next bill and its amount |
| 3 | "How much do your subscriptions cost per month?" | give the monthly subscription total |
| 4 | "Find a charge that looks unusual." | point to a flagged transaction |
| 5 | "Set a $300 monthly budget for Food." | save the budget |
| 6 | "Ask the assistant how much you spent on dining last month." | get an answer from the assistant |

## SUS questionnaire

After the tasks, ask them to rate each statement from 1 (strongly disagree) to 5 (strongly agree).

1. I think that I would like to use this app frequently.
2. I found the app unnecessarily complex.
3. I thought the app was easy to use.
4. I think that I would need the support of a technical person to be able to use this app.
5. I found the various functions in this app were well integrated.
6. I thought there was too much inconsistency in this app.
7. I would imagine that most people would learn to use this app very quickly.
8. I found the app very cumbersome to use.
9. I felt very confident using the app.
10. I needed to learn a lot of things before I could get going with this app.

**Scoring** (per person):
- For odd-numbered items, subtract 1 from the rating.
- For even-numbered items, subtract the rating from 5.
- Add the ten results and multiply the total by 2.5.

That gives 0 to 100. Average across people. About 68 is the usual average for software, and above 80 is good.

## Results sheet

Copy this table and fill in one row per person.

| Person | T1 s / ✓ | T2 | T3 | T4 | T5 | T6 | SUS | Notes |
|---|---|---|---|---|---|---|---|---|
| P1 | | | | | | | | |

Then report:
- **Task success rate:** tasks completed ÷ tasks attempted.
- **Median time per task.**
- **Mean SUS.**

## Before and after

To show that a change helped, run the same tasks with different people before and after the change. People who have already seen the app are faster the second time, so don't reuse them.

This is where the redesign comes in. Run the test on today's app, ship the new design, then run it again with 5 new people. Comparing the time on tasks 1 to 3 gives you a fair before and after.
