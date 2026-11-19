# agent-issue-pipeline

![CI](https://github.com/tmoreiradev/agent-issue-pipeline/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![License](https://img.shields.io/badge/license-MIT-green)

An issue-to-deploy pipeline for coding agents. Coding agents write the code; the pipeline decides what counts as done.

It takes one issue at a time from a queue and runs it through these steps:

1. **Gate.** Only well-specified issues get in.
2. **Worker.** A coding agent (Claude Code by default) implements the issue in its own git worktree.
3. **Checks.** The pipeline runs the tests itself.
4. **Review.** An agent from a different vendor (Codex by default) reviews the diff.
5. **Integrate.** The pipeline merges the change.
6. **Deploy.** It deploys with a health check and rolls back automatically if the check fails.

People decide what to build and approve what the agents could not settle. The agents do the rest.

This is a cleaned-up, generic version of a pipeline I run every day on personal projects. Most of the failure modes listed below happened in real use.

> **PT-BR:** pipeline que leva uma issue até o deploy usando agentes de código. Ela só aceita issues bem especificadas, roda o worker isolado numa worktree, executa os testes ela mesma, pede revisão a um agente de outro fornecedor e faz deploy com rollback automático. As pessoas decidem o que construir e o que fazer quando a pipeline trava.

## How an issue moves

```mermaid
flowchart LR
    Q[Queue<br/>ready-for-agent] --> G{Gate<br/>task label,<br/>Evals,<br/>Acceptance criteria}
    G -- missing --> NI[needs-info<br/>+ comment]
    G -- ok --> W[Worker agent<br/>own worktree + branch<br/>no docker / sudo / push]
    W --> C[Checks run by<br/>the pipeline]
    C --> R{Reviewer<br/>other vendor<br/>VERDICT}
    R -- REJECTED --> E{BLOCKED or<br/>REPEATED?}
    E -- no, rounds left --> W
    E -- yes --> H[ready-for-human]
    R -- APPROVED --> I[Rebase + ff push]
    I --> D[Deploy<br/>backup, snapshot,<br/>build, health check]
    D -- unhealthy --> RB[Rollback to<br/>previous version]
    D -- healthy --> DONE[Done<br/>report + webhook]
```

| Step | What the agent does | Who decides |
|---|---|---|
| Gate | nothing yet | issues without `## Evals` and `## Acceptance criteria` never reach an agent |
| Worker | implements and commits in an isolated worktree, one branch per issue | it cannot run docker, sudo or `git push` |
| Checks | — | the pipeline runs tests, lint and build; the agent saying "tests pass" counts for nothing |
| Review | a second agent from another vendor reads the diff and the real check output | strict verdict rule: only CRITICAL/HIGH findings or unmet criteria reject |
| Integrate | — | rebase plus fast-forward push; anything unusual stops and goes to a human |
| Deploy | — | a failed build or health check never counts as success, and the pipeline rolls back on its own |

## Try it in 30 seconds (no API keys)

The demo replaces both agents with deterministic mocks.

```bash
python3 examples/setup_demo.py /tmp/demo
python3 pipeline.py --config /tmp/demo/pipeline.toml --all
```

```text
DEMO-1 started (default model) in <demo>/.pipeline/wt/DEMO-1
DEMO-1 round 1: checks pass, mock reviewer: APPROVED
DEMO-1 finished: approved and merged (`8517f21`); deployed, health check ok
DEMO-2 stopped at the gate: ['section `## Evals` with content', 'section `## Acceptance criteria` with content']
DEMO-3 started (default model) in <demo>/.pipeline/wt/DEMO-3
DEMO-3 finished: escalated after 1 round(s)
DEMO-4 started (default model) in <demo>/.pipeline/wt/DEMO-4
DEMO-4 round 1: checks fail, mock reviewer: REJECTED
DEMO-4 round 2: checks pass, mock reviewer: APPROVED
DEMO-4 finished: approved and merged (`a778210`); deployed, health check ok
```

The four demo issues cover four paths:

- **DEMO-1** is the happy path.
- **DEMO-2** is too vague and is stopped at the gate.
- **DEMO-3** has a spec the worker cannot meet. The worker says so with `BLOCKED:` and the issue goes to a human without spending a review.
- **DEMO-4** ships a bug in round 1. The real test output and the review go back to the worker, which fixes the bug in round 2.

`tests/test_pipeline.py` runs this same demo end to end in CI.

## Running it with real agents

1. Copy `pipeline.example.toml` to `pipeline.toml` and point `repo.path` at a clone of your project.
2. Write your issues as Markdown files in `issues/` (see `tracker.py` for the format). Add the `task` and `ready-for-agent` labels, plus the `## Evals` and `## Acceptance criteria` sections.
3. Run `python3 pipeline.py` for a polling loop, `--once` for a single issue, `--issue ID` for a specific issue, or `--dry-run` to run only the gate.

To run it as a service, a systemd user unit with `Restart=on-failure` is enough. The pipeline handles exhausted quota and expired agent logins on its own: it pauses, sends one webhook message and retries every 30 minutes.

The tracker is a folder of Markdown files on purpose. Replacing it with GitHub Issues, Linear or Jira means implementing five methods: `list`, `get`, `set_state`, `label` and `comment`.

## Failure modes it handles

Most rows come from incidents in real use. The rest are guards the design needed from day one.

| Failure | What happened | What the pipeline does | Covered by |
|---|---|---|---|
| Vague issue | The agent fills the gaps with guesses, and the review cannot tell right from wrong | The gate requires non-empty evals and acceptance criteria; otherwise `needs-info` plus a comment listing what is missing | `test_gate`, DEMO-2 |
| Impossible spec | The worker faked a field that the external API did not provide | The worker must write `BLOCKED: <reason>`; the pipeline escalates immediately, even if the reviewer approved the rest | `test_marks`, DEMO-3 |
| `main` moved meanwhile | A rebase can apply cleanly and still break behaviour | After a rebase that changed anything, the checks run again before the push | — |
| Resumed issue | A pause in the middle of an issue must not discard work | An existing worktree or branch for the issue is reused, never reset | — |
| Review loop | One issue was rejected 4 times for the same finding, burning quota | The reviewer marks unresolved findings `REPEATED:`; one repeat escalates to a human | `test_marks` |
| Worker commits nothing | Checks and review ran on an empty diff | An empty diff skips checks and review and returns to the worker | e2e |
| "Tests pass" (they didn't) | The agent's summary disagreed with reality | The pipeline runs the checks itself, and failing checks force `REJECTED` whatever the reviewer says | DEMO-4 |
| Reviewer ignores the format or hangs | No parseable verdict | The last `VERDICT:` line wins; with no verdict or a timeout, a fallback reviewer runs, and a stale result file from the first reviewer is never read | `test_verdict_takes_the_last_line`, `test_reviewer_fallback_ignores_stale_result` |
| Build fails during deploy | The old container stayed up and passed the health check, which looked like success | A failed build is a failure; production stays on the previous version | `test_deploy_build_failure_keeps_old_version` |
| New version unhealthy | Bad migration, crash on start, or a half-applied `up` | Backup and snapshot first, then automatic rollback; a rollback that fails is reported loudly, never as success | `test_deploy_rolls_back_on_bad_health_check`, `test_deploy_failed_up_rolls_back_and_failed_rollback_is_reported` |
| Main clone was dirty | Someone was editing on the deploy machine | The push still happens, but the deploy stops and is handed to a human | — |
| Quota or login expired | The agent CLI exited in the middle of an issue | Pause and retry every 30 min with a single notification; the issue resumes as In Progress | — |

## Design decisions and trade-offs

- **A reviewer from a different vendor.** The same model reviewing its own diff tends to agree with itself. A second vendor catches a different class of mistakes, and having a fallback avoids depending on a single provider.
- **The reviewer sees files, not the repo.** It gets `REVIEW.md`, `diff.patch` and `checks.txt` in an empty folder. It cannot edit the change, and it judges real test output rather than the worker's claims.
- **A strict verdict rule.** Only CRITICAL/HIGH findings or unmet criteria reject a change. MEDIUM/LOW findings become follow-ups. Without this rule, reviewers reject on taste and the loop never converges.
- **One issue at a time.** Throughput is lower, but there are no merge races, quota use is predictable, and each report reads as a single story.
- **Plain files and git.** There is no database, no queue server and no framework. The whole orchestrator fits in one file you can read in one sitting.

## Limitations

- **A worktree is not a sandbox.** Disallowing `docker`, `sudo` and `git push` is a tool-level policy, not process isolation. Run the worker as a user without deploy credentials, or inside a container or VM, and keep secrets out of its environment. The pipeline holds the push and deploy steps for this reason.
- **The deploy step runs shell commands from your config**, with the same trust level as a Makefile.
- **No cost accounting yet.** Agent CLIs report usage differently, so the reports record rounds and verdicts but not dollars.

## What I would change next

- A benchmark: 20 issues with known outcomes, including ambiguous and impossible ones, measuring correct gate decisions, first-round approval, escalations, cost and duration. It would also compare worker alone against worker plus reviewer.
- Run the worker in a throwaway container instead of a worktree on the host.
- Per-issue cost and token reports from the agents' JSON output.
- A GitHub Issues tracker adapter.

## License

MIT
