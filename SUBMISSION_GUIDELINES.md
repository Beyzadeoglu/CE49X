# CE49X — Submission Guidelines

**Spring 2026 | Dr. Eyuphan Koc | Bogazici University**

---

## Overview

Each student maintains their **own repository** (a fork of the course repository) where they submit all weekly labs and the final project. This mirrors real-world software engineering workflows and gives you experience with Git.

---

## 1. Setting Up Your Repository

### Step 1 — Fork the Course Repository

1. Go to the course repository on GitHub (URL provided in class)
2. Click the **Fork** button (top-right corner)
3. This creates a copy of the repository under your own GitHub account

Your fork will live at: `https://github.com/<your-username>/CE49X.git`

### Step 2 — Clone Your Fork Locally

```bash
git clone https://github.com/<your-username>/CE49X.git
cd CE49X
```

### Step 3 — Add the Course Repo as an Upstream Remote

This lets you pull new materials (lectures, assignments) as they are released:

```bash
git remote add upstream <course-repository-url>
```

Verify your remotes:

```bash
git remote -v
# origin    https://github.com/<your-username>/CE49X.git (fetch)
# origin    https://github.com/<your-username>/CE49X.git (push)
# upstream  <course-repository-url> (fetch)
# upstream  <course-repository-url> (push)
```

### Step 4 — Pull New Course Materials

Before each class, pull the latest materials from the instructor's repository:

```bash
git fetch upstream
git merge upstream/main
```

If you haven't modified any of the instructor-provided files, this will work cleanly. If you see merge conflicts, it means you edited a file that the instructor also updated — resolve the conflict or ask for help.

---

## 2. Repository Structure

Keep your repository organized using this structure. Do **not** rename or reorganize the folders provided by the instructor.

```
CE49X/
├── Week01_Python_Fundamentals/
│   ├── Week01_Python_Fundamentals_Lecture.ipynb      ← instructor-provided
│   ├── Week01_Theory_Data_Science_Lifecycle.ipynb    ← instructor-provided
│   └── Week01_Lab_<YourName>.ipynb                   ← YOUR submission
├── Week02_Python_Modules_and_Data_Science/
│   ├── ...                                           ← instructor-provided
│   └── Week02_Lab_<YourName>.ipynb                   ← YOUR submission
├── ...
├── FinalProject/
│   ├── FinalProject_Report.ipynb                     ← YOUR submission
│   └── data/                                         ← any datasets you use
├── CE49X_Setup_Guide.ipynb
├── SUBMISSION_GUIDELINES.md
└── README.md
```

**Naming convention for submissions:**

```
WeekNN_Lab_FirstnameLastname.ipynb
```

Example: `Week03_Lab_AhmetYilmaz.ipynb`

---

## 3. Submitting Your Work

### Weekly Labs

1. Complete your lab notebook in the appropriate week folder
2. Make sure your notebook **runs from top to bottom** without errors (Kernel → Restart & Run All)
3. Stage, commit, and push:

```bash
git add Week03_NumPy_Pandas/Week03_Lab_AhmetYilmaz.ipynb
git commit -m "Submit Week 03 lab — NumPy and Pandas exercises"
git push origin main
```

4. Your submission is the state of your repository at the **deadline**. The instructor will check your fork at that time — there is nothing else to "hand in."

### Final Project

1. Create a `FinalProject/` folder in your repository (one per group — all group members should have the same folder in their individual forks)
2. Include your project notebook, any data files, and a brief README inside the folder
3. Push before the deadline

#### Final Presentation — Recorded Video

In place of a live demo day, each group submits a **recorded presentation video**:

- **Length:** 10–15 minutes (5–7 min findings & methodology, 3–5 min walkthrough/Q&A-style discussion, 1–2 min conclusions & future outlook)
- **Format:** screen recording with audio (slides and/or notebook walkthrough; show your dashboard)
- **Delivery:** email the video (or a shareable link — Google Drive, YouTube unlisted, WeTransfer) to **both**:
  - Dr. Eyuphan Koc — `eyuphan.koc@bogazici.edu.tr`
  - Mustafa Özçetin (TA) — `mustafa.ozcetin@std.bogazici.edu.tr`
- **Subject line:** `CE49X Final Project Video — <Group Member Names>`
- **Deadline:** same as the repository submission deadline

---

## 4. Commit Practices

Good commit habits will serve you throughout your career. Follow these guidelines:

**Commit frequently.** Each commit should represent a logical unit of work — not an entire week's worth of changes in one go.

**Write meaningful commit messages.** The message should describe *what* you did and *why*.

| Good | Bad |
|---|---|
| `Add scatter plot for cement vs strength analysis` | `update` |
| `Fix missing value handling in data cleaning step` | `changes` |
| `Complete Week 04 lab exercises 1-5` | `done` |
| `Add error handling for edge case in load calculator` | `stuff` |

**Commit structure:**

```bash
# Stage specific files (preferred)
git add Week03_NumPy_Pandas/Week03_Lab_AhmetYilmaz.ipynb
git commit -m "Complete Week 03 exercises on array slicing and DataFrame filtering"

# Push to your fork
git push origin main
```

Avoid `git add .` or `git add -A` — these can accidentally include large data files, temporary files, or system files. Stage specific files by name.

---

## 5. What NOT to Commit

Do not include these in your repository:

- **Large data files** (> 10 MB) — add them to `.gitignore`
- **Environment files** — `.env`, API keys, credentials
- **Python cache** — `__pycache__/`, `.pyc` files
- **OS files** — `.DS_Store` (macOS), `Thumbs.db` (Windows)
- **Notebook checkpoints** — `.ipynb_checkpoints/`

A `.gitignore` file is included in the course repository. Do not delete it.

---

## 6. Deadlines & Late Policy

- Labs are due at **the beginning of the next class session**
- The instructor checks the state of your fork at the deadline — your latest push before that time is your submission
- **Late submissions:** 10% penalty per day, maximum 3 days late
- If you push after the deadline, the late penalty applies based on the timestamp of the push

---

## 7. AI Tool Acknowledgment

If you used AI tools (Cursor AI, Claude Code, ChatGPT, GitHub Copilot, etc.) to help with your work, include a brief acknowledgment at the top of your notebook:

```python
# AI Assistance: Used Claude Code for debugging the data cleaning pipeline
# and Cursor AI for generating the initial matplotlib plot template.
# All code reviewed and understood by the author.
```

This is **required** — not to penalize you, but to build good professional habits. In industry and academia, transparent use of tools builds trust.

---

## 8. Troubleshooting

| Problem | Solution |
|---|---|
| `fatal: not a git repository` | You're not inside the cloned folder. `cd` into your CE49X directory. |
| `error: failed to push` | Someone (likely you from another machine) pushed changes you don't have locally. Run `git pull` first, then push again. |
| Merge conflicts when pulling from upstream | You edited an instructor-provided file. Open the conflicted file, resolve the conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`), then `git add` and `git commit`. |
| Notebook won't run top-to-bottom | Restart the kernel and run all cells. Fix any errors before submitting. Common cause: cells were run out of order during development. |
| Accidentally committed a large file | See [GitHub's guide to removing large files](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github). Ask for help if needed. |

---

## Quick Reference

```bash
# Pull new course materials
git fetch upstream && git merge upstream/main

# Submit your work
git add <your-file>
git commit -m "Meaningful message"
git push origin main

# Check status
git status
git log --oneline -5
```

---

**Questions?**

**Dr. Eyuphan Koc**
eyuphan.koc@bogazici.edu.tr
