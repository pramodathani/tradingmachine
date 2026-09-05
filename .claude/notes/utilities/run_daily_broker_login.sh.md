# utilities/run_daily_broker_login.sh

A thin cron wrapper around `python3 -m utilities.broker_login`. It activates the virtual environment, changes into the project directory so the module path resolves, and appends both streams to a monthly log file under `logs/`.

It is a deliberate copy of the shape of `data/instruments/run_daily_download.sh` rather than a shared or parameterised runner. The two jobs have nothing in common but four lines of boilerplate, and a reader of either one can see the whole thing without opening the other.

`logs/` is gitignored. The script creates the directory rather than the repository committing it, so a fresh clone needs no setup step.

## Timing

The crontab line documented in the README runs it at 07:00 on weekdays, half an hour ahead of the instrument download at 07:30.

The ordering is not arbitrary. IND Money's instrument master is the one download of the ten that needs an access token, so the login has to have happened before that job runs. Half an hour is generous for a run that takes about thirty seconds, and the margin is there because three of the logins drive a real browser against a real login page, which is the part most likely to be slow or to need a retry.

Weekdays only, because the tokens exist to trade with and the market is shut at the weekend. Indian market holidays are not handled: the job runs, the tokens are issued, and nothing uses them.

## Failure is meant to be loud

`set -euo pipefail` means the wrapper exits non-zero when the module does, and the module exits 1 when any broker failed to log in. Cron then reports the failure through its usual channel rather than the job failing silently and the first sign being an authentication error hours later.

That is also why the module collects failures rather than stopping at the first one. A single broker being down should still leave the other nine with working tokens, while the exit status makes sure the failure is not missed.

## Why the crontab entry is documented as well as installed

The README carries the line to paste, following the same convention as the instruments job: a repository should not silently change the scheduled work of whoever clones it. The entry was installed on this machine separately, at the user's request, which is a change to this machine rather than to the project.
