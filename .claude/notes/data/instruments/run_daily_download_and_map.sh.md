# data/instruments/run_daily_download_and_map.sh

A thin cron wrapper. It activates the virtual environment, changes into the project directory so that `python3 -m data.instruments.download_and_map` resolves, and appends both streams to a monthly log file under `logs/`.

It runs one command, not two. Downloading and mapping were briefly two lines here; folding them into one entry point put the broker list, the failure handling and the stage order in one place, and left this file with nothing to decide.

`logs/` is gitignored. The directory is created by the script rather than committed, so a fresh clone needs no setup step.

## Timing

The crontab line documented in the README runs it at 07:30 on weekdays. It must run on the day whose files it wants, because Kotak's URL is stamped with the current date and serves only that day. Running before the market opens also means the day's master reflects the contracts actually tradeable that session.

## Why the crontab entry is documented rather than installed

Installing a crontab entry silently changes the machine's scheduled work, which is not something a repository should do to whoever clones it. The README carries the line to paste.
