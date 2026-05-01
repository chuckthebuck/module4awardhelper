# Four Award Helper Module

Cron-backed Buckbot module for conservatively reviewing and processing [[Wikipedia:Four Award]] nominations on English Wikipedia.

This repository is intended to be loaded by the Buckbot module framework using `modules/four_award/module.toml`.

## Safety model

The module is dry-run by default. Live actions require explicit environment flags:

```bash
FOUR_AWARD_DRY_RUN=0
FOUR_AWARD_ENABLE_REPLIES=1
FOUR_AWARD_ENABLE_RECORDS=1
FOUR_AWARD_ENABLE_REMOVAL=1
FOUR_AWARD_ENABLE_TALK_NOTICES=1
FOUR_AWARD_ENABLE_ARTICLE_HISTORY=1
```

Recommended rollout:

1. Run dry-run only.
2. Enable nomination replies while keeping records/removal disabled.
3. Enable records after verifying table rebuilds.
4. Enable nomination removal, talk notices, and article-history updates last.

## Behavior

* Records table rows are rebuilt in canonical order: username A-Z, then award date/time.
* Each wikitable entry is emitted as a single line.
* The bot replies to nominations with hidden markers to avoid duplicate replies.
* Ambiguous judgment calls become `manual_review_needed`; the bot only approves with clear evidence and only fails on objective problems.

## Development

```bash
PYTHONPATH=. python -m py_compile modules/four_award/*.py
PYTHONPATH=. python -m pytest -q
```
