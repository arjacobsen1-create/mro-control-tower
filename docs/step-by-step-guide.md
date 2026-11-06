# How This Project Was Built — Step by Step

**Plain-language guide. Every step, in order, exactly as it happened.**
If you follow this from the top, you can rebuild the whole project, or check
any part of it. Written 1 November 2026.

---

## First, the big picture in one paragraph

We built a small pretend company: an aircraft repair company with 3 hangars.
We made up all its data (parts, stock, orders, repair jobs). Then we built a
"checker" — a small set of rules in code — that says whether a repair job has
all the parts it needs. Then we connected an AI (Claude) to the checker. The
AI reads the checker's answers and writes a clear recommendation for a human.
The human always decides. The AI never acts on its own, and it never does
maths — the code does all the maths.

## The accounts you need (your real ones)

| Service | Your username | What it holds |
|---|---|---|
| Hugging Face | **Anahitarj** | The dataset (the made-up data) |
| GitHub | **arjacobsen1-create** | The code (the application) |
| Anthropic Console | Anahita Jacobsen (Individual) | The AI key and the $5 credit |

⚠️ **Important, learned the hard way:** on **GitHub**, the name "Anahitarj"
belongs to a *different person*. It is only your name on Hugging Face.
Your GitHub name is **arjacobsen1-create**, tied to arjacobsen1@gmail.com.

---

## Part 1 — Start with rules, not code

1. Pick ONE problem, not ten. Ours: "a repair job is missing a part."
2. Write the safety rules down before building anything:
   - All data is made up. No real company data, ever.
   - The computer code does all the counting. The AI only explains.
   - The system can only *look*. It cannot change anything.
   - A human approves or rejects every recommendation.
3. Pick a pretend "today" and never change it in tests: **2 Nov 2026**.
   Every test uses that date, so results are the same every time.

## Part 2 — Make the data

1. We looked for a ready-made dataset first. None existed for this.
   So we wrote a script that *makes* the data: `generate_dataset.py`.
2. The script creates 8 small tables (spreadsheets):
   - **parts** — the 24 parts, with price and how long a new one takes to arrive.
   - **inventory** — how many of each part sit at each hangar, and how many
     are already promised to another job ("reserved" — they do not count).
   - **purchase_orders** — parts already ordered, and when they will arrive.
   - **maintenance_events** — the 6 repair jobs, and when each one starts.
   - **demand** — which parts each job needs, and how many.
   - **maintenance_history** — old repair records.
   - **knowledge_notes** — 12 short policy notes the AI can look up.
   - **eval_scenarios** — 10 test questions with the correct answers written
     down *in advance*. This is the exam the AI sits later.
3. The 10 test questions cover every possible answer: OK, covered by an
   order, covered by moving stock from another hangar, covered by an
   approved substitute part, truly short, and "we don't know — a human must
   go and count."
4. We planted traps on purpose: an order that arrives *after* the job
   starts, reserved stock that *looks* available, a substitute part with
   zero stock.
5. Later we made it realistic (version 1.1): real engine parts take 12 to
   24 **months** to arrive, not days. A turbine blade set takes 540 days.
   The test answers did not change — only the timing checks did.

## Part 3 — Put the data on Hugging Face

Hugging Face is a website where people publish datasets for free.

1. Go to **huggingface.co** and sign in (your account: **Anahitarj**).
2. Click your picture → **New Dataset**.
3. Name it `synthetic-mro-supply-chain`. Choose **Public**. Create it.
4. Open the **Files** tab → **Add file → Upload files**.
5. Upload the 8 tables (CSV files) into a folder called `data`, plus the
   two scripts `generate_dataset.py` and `validate_dataset.py`.
6. Add a file called **README.md** — this is the "dataset card." It explains
   what the data is, says clearly that it is 100% made up, and lists the
   licence (CC0 — anyone may use it). Write a short commit message
   (for example "Dataset v1.0") and save.
7. Open the dataset page. After a short wait, a **viewer** appears: you can
   click each table and see the rows. This proves the upload worked.
8. To update it later (we did, for v1.1): upload the changed files the same
   way, with a new message ("v1.1 realistic lead times"). The old version
   stays in the history.
9. If you open "Data Studio" and see *"Failed to initialize DuckDB"* —
   ignore it. That is a broken extra tool on their side. The tables
   themselves are fine, and our project never uses Data Studio.

🔗 Your dataset: https://huggingface.co/datasets/Anahitarj/synthetic-mro-supply-chain

## Part 4 — Check the data is right (before any AI)

1. Run `python3 validate_dataset.py`.
   This recomputes all 10 test answers from the raw tables.
   **You should see: "10/10 scenarios match ground truth."**
   (The first time, we saw 9/10. One table was pinned wrong. We fixed the
   script, ran it again, and got 10/10. This is normal — the check exists
   to catch exactly this.)
2. Run `python3 ingest/ingest.py`.
   This loads the tables into a small database and runs 7 safety checks
   (for example: no negative stock; orders never show more received than
   ordered). **You should see: "All integrity checks passed."**
3. Run `python3 ingest/test_retrieval.py`.
   This tests the note search: 9 real questions must find the right note,
   and 1 silly question ("catering menu") must find **nothing**. Finding
   nothing is the correct answer — it means the AI will say "I don't know"
   instead of guessing. **You should see: "10/10 retrieval tests passed."**

## Part 5 — Connect the AI (Anthropic)

1. Go to **platform.claude.com** and create an account. Choose
   **Individual** (not Organization).
2. Buy a small amount of credit: **$5**. It lasts a year.
3. You will be offered "auto-reload." Choose **Skip for now** — otherwise
   it charges your card automatically when the balance gets low.
4. Create an **API key** (ours is named `aj-api-key`). A key is like a
   password for a program. Ours expires after 30 days (1 Dec 2026); when
   it stops working, make a new one the same way.
5. **Never** type a key into a chat, a document, or the code. Ours is
   stored in a secure vault. The program fetches it when it runs.
6. Run one test: `python3 app/agent.py E001 P001`
   (That means: "job E001, part P001 — will it be there?")
7. The AI uses 5 tools, all read-only: look up the job, look up the parts
   list, look up the part, **run the checker**, search the notes.
   The checker is a rule list in code (`app/availability.py`):
   - No stock record and no orders at all → **INSUFFICIENT_DATA** (a human
     must go and count).
   - Usable stock = on hand − reserved.
   - An order only counts if it arrives **on or before** the job start
     date, at the right hangar.
   - Then, in order: **OK** → **COVERED_BY_PO** → **COVERED_BY_TRANSFER**
     → **COVERED_BY_ALTERNATE** → **SHORT_UNCOVERED**.
   - Dates like "order by" and "too late to order" are also worked out by
     the code, never by the AI.
8. Our first 3 live runs all matched the exam answers. Total cost: about
   **3 cents** of the $5.
9. One mistake we caught and fixed: the AI once wrote "order by 18 Oct" as
   advice, when 18 Oct had already passed. Now the **code** works out the
   dates and tells the AI "this date has already passed," and the AI must
   say so. Lesson: if the AI says a number or a date, the code should have
   produced it.

## Part 6 — Put the code on GitHub

GitHub is where the *code* lives. The data does **not** go here — it stays
on Hugging Face, and GitHub links to it. One home for data, one for code.

### 6a. Your account and password

1. Your GitHub account came from clicking **Continue with Google** with
   arjacobsen1@gmail.com. That gave you the name **arjacobsen1-create**.
   A Google-made account has **no GitHub password** at first — if GitHub
   says "this account does not support password sign-in," that is why.
2. To give it a real password: on the GitHub sign-in page, click
   **Forgot password**, type arjacobsen1@gmail.com, and open the email
   GitHub sends you. Follow the link and set a new password.
3. Save that password in the secure vault — never in a chat or a file.
   From then on, sign-in is just username + password.
4. Sometimes GitHub asks for a **device verification code** (it does not
   recognise a new browser). Choose "send a code by email," type in the
   code from the email, done. The code only lasts about an hour.

### 6b. Create the repository (a "repo" = a project folder)

1. Sign in at **github.com**. Click **+** (top right) → **New repository**.
2. Name: `mro-control-tower`. Write the description.
3. Choose **Public**.
4. Do **NOT** tick the README, .gitignore, or licence boxes. We upload
   our own files, and ticking them causes clashes.
5. Click **Create repository**.

### 6c. Upload the files

1. On the empty repo page, click **uploading an existing file**.
2. Add the files in small batches (the root files first, then each
   folder: `docs`, `ingest`, `app`). In each batch, write the commit
   message — ours was:
   *"Stages 1-3: synthetic dataset, ingestion + retrieval, Claude agent workflow"*
   A "commit" is just a saved snapshot with a label.
3. **Do not upload:** the CSV data files (they live on Hugging Face), the
   local database (`mro.db`), run logs, or any key or password.
4. Our README file was named `repo_README.md` on the computer. After
   uploading, click it → the **pencil icon** → change its name at the top
   to **README.md** → commit. That is why the history shows one extra
   commit called "Rename repo_READM
E.md to README.md." It must be called exactly
   README.md or GitHub will not display it on the front page.

### 6d. Check the front page

1. Open the repo: https://github.com/arjacobsen1-create/mro-control-tower
2. You should see: the README written out like a web page (starting with
   the **Data Source** section, which states the data is synthetic and
   links to Hugging Face), the folders `app`, `docs`, `ingest`, and
   **no** `data` folder.
3. If you cannot see it in the GitHub phone app: tap your picture →
   **Repositories**. And do not search "Anahitarj" — that is the other
   person's account.

## Part 7 — Run everything, in order (the full checklist)

```
python3 generate_dataset.py        # rebuild the made-up data
python3 validate_dataset.py        # expect: 10/10 scenarios match ground truth
python3 ingest/ingest.py           # expect: All integrity checks passed
python3 ingest/test_retrieval.py   # expect: 10/10 retrieval tests passed
python3 app/test_tools.py          # expect: 13/13 tool-layer tests passed
python3 app/agent.py E001 P001     # one live AI assessment (needs the key)
```
All five checks above were re-run and passed on 1 Nov 2026
(Python 3.12.3). The account steps in Parts 3, 5 and 6 were done by
Anahita herself and confirmed by the live pages and GitHub's own emails.

## Part 8 — If something goes wrong (the traps we actually hit)

- **"This account does not support password sign-in"** → the account was
  made with Google. Either use Continue with Google, or set a password
  with Forgot password (Part 6a).
- **"Incorrect username or password"** → check *which* account you mean.
  Anahitarj on GitHub is a stranger. Yours is arjacobsen1-create.
- **Two accounts with similar names** → Hugging Face = Anahitarj.
  GitHub = arjacobsen1-create. The table at the top of this guide is the
  source of truth.
- **Hugging Face viewer not showing yet** → wait a few minutes; it
  re-indexes after every upload. The files are already there.
- **"Failed to initialize DuckDB"** → ignore (Part 3, step 9).
- **The AI states a date that already passed** → the code must compute
  dates, not the AI (Part 5, step 9).
- **Test says 9/10 instead of 10/10** → the data script has a mistake.
  Fix the script, regenerate, re-run. Never edit the expected answers
  to make a test pass.

## Part 9 — What is left to build

*(All three are now done — see Part 10.)*

- **Stage 4 — the planner screen.** A simple page where the human sees
  the recommendation and decides on the recommended action. Every
  decision is written down.
- **Stage 5 — the full exam.** Run all 10 test questions through the AI,
  count the score, and write down the misses honestly (we already know
  the wording around dates needs checking — the answers themselves have
  been exact).
- **Stage 6 — the report.** Run history, costs, and an honest write-up
  of what the prototype does and does not prove.

## Part 10 — What happened next (Stages 4 and 6, finished 1 Nov 2026)

1. **The planner screen (Stage 4).** There are two copies of the same
   screen: one on the web, and one that lives with the code, in a file
   called `app/planner.py`. Since 2 Nov 2026 there is also a version that
   opens straight from GitHub Pages, like the dashboard:
   https://arjacobsen1-create.github.io/mro-control-tower/planner.html
   (decisions there are saved in your browser only, with an Export button). To open the code copy:
   - Run `python3 app/planner.py`
   - Open **http://127.0.0.1:8765** in your browser.
   You see the 6 jobs. Click one, and you see every part it needs. The 10
   parts the AI was examined on show its answer and its recommendation,
   with buttons that match the answer: approve the coverage action,
   acknowledge, or escalate. **Gate fix (6 Nov 2026):** the first version
   offered Approve/Reject on every line — but a shortage cannot be
   accepted. Short and insufficient-data lines now offer escalation only
   (expedite / emergency source, defer the event, or investigate); there
   is no Accept button on them. Your choice is saved
   in a small file on this computer only (`monitoring/planner_decisions.json`),
   with the time you clicked. You can undo or change any decision. The
   screen cannot change the data — it can only record *your* decisions.
   That is the whole point: the AI recommends, the human decides.
2. **Fix 1 — the AI may not invent day-counts (Stage 6).** In the exam,
   the AI once wrote "missing the event by 227 days." The real numbers
   were 265 and 256 — it had done maths in its head and got it wrong.
   Now the checker works out "how many days late or early" for every
   order and every "if we ordered today" date, and hands the AI the
   numbers. The AI is only allowed to repeat numbers it was handed.
3. **Fix 2 — the AI must show its sources (Stage 6).** When the answer
   depends on a policy note (for example "escalate" or "you may use the
   substitute part"), the program now checks: did the AI name the note?
   If the list is empty, the AI is sent back once to fetch the note and
   name it. No empty source lists for policy answers.
4. **The exam was run again after the fixes.** Still **10/10**. The
   "227 days" sentence is now "265 days after the event start" — the
   checker's own number. Every policy answer named its note. Cost of the
   re-run: about **12 cents**.
5. **The report page (Stage 6).** Run `python3 monitoring/summarize_runs.py`.
   It reads the run diary and your decision file and writes
   `monitoring/summary.md`: how many runs, the latest score, what it all
   cost (about 27 cents in total so far), and how many decisions are
   decided, escalated, or still waiting for you (10 waiting, until you
   click).

---

*Companion documents: `README.md` (the short public version),
`docs/data_dictionary.md` (every table and the checker rule, precisely),
`docs/process-and-roadmap.md` (the decision log). This guide is the
plain-language path through all of it.*
