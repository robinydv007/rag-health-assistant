Explore any idea through structured dialogue before committing to anything.

Use this to think through a concept, technical direction, product decision, or architecture question. Nothing gets written to disk. The output is a clear, structured summary you can act on.

## When to use

- You have a vague idea and want to think it through
- You're weighing technical options and need to reason carefully
- You want to explore a product direction before committing to building it
- You're considering a significant architecture or process change

When you're ready to turn the result into a project, run `/start-project`.

---

## Steps

1. Ask one question at a time to understand the idea:
   - What is the core problem or opportunity?
   - Who is this for? (user, system, team)
   - What are the 2–3 options or directions worth exploring?
   - What constraints matter most? (time, cost, complexity, reversibility)
   - What does success look like?

2. After understanding the idea, reflect back a structured summary:

   ```
   ## Idea Summary

   **Problem**: ...
   **Options explored**: ...
   **Key constraints**: ...
   **Recommendation**: ...
   **Open questions**: ...
   ```

3. Ask: "Does this capture it? Anything to refine?"

4. Iterate until the idea is clear.

5. Close with one of:
   - "Ready to build this? Run `/start-project` to scaffold it as a project."
   - "Want to explore further before committing? Ask away."
   - "This is a decision, not a project — want to log it as an ADR with `/log`?"

## Key Principles

- One question at a time — don't overwhelm
- No files written during brainstorming — this is thinking, not building
- The summary is the deliverable — concise, clear, actionable
- Stay generic — works for software, process, product, or architecture ideas
