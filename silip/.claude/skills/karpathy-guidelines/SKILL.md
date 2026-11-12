---
name: karpathy-guidelines
description: Apply before any code change to avoid wrong assumptions, overengineering, unrelated edits and unverified work.
---
Adapted from the MIT-licensed `multica-ai/andrej-karpathy-skills`, based on Andrej Karpathy's notes on LLM coding pitfalls. Rules in order; each gates the next.

1. **Think first.** Restate the task, list assumptions, name the main tradeoff. Ask only when a wrong guess is costly.
2. **Simplicity.** Least code that meets today's goal. No speculative options or layers.
3. **Surgical.** Touch only needed lines. No drive-by refactors or reformatting.
4. **Goal-driven.** Define a runnable check, loop until it passes, report the real output.
