# 🌈 BrainSprinkles

*A cozy little place for everything in your head.* 🦄☕🐶

BrainSprinkles is a local-first brain dump and thought-organizing desktop app. Capture first, organize later.

## Current starter features

- Blank-page writing experience
- Automatic local saving to SQLite
- Optional entry types: Thought, To-do, Idea, Memory, Project, Journal
- Search across titles, notes, and tags
- Tags (type a tag and press Enter)
- Favorites
- Connections between independent entries
- macOS one-click launcher script

## Run on macOS

1. Download or clone this repository.
2. Open the project folder.
3. Double-click `run.command`.
4. The first launch creates a Python virtual environment and installs Flask.
5. Your browser opens at http://127.0.0.1:5057.

If macOS blocks the script, open Terminal in the project folder and run:

```bash
chmod +x run.command
./run.command
```

Python 3 is required.

## Where your data lives

Your entries are stored locally in:

```text
data/brain_sprinkles.db
```

This database is intentionally excluded from Git by `.gitignore`. Back it up before moving computers or deleting the project folder.

## Roadmap

- [ ] Google Apps Script + Google Sheets synchronization
- [ ] Offline sync queue with safe retries and conflict handling
- [ ] Collections and richer relationship explorer
- [ ] Checklist items inside entries
- [ ] Customizable categories and themes
- [ ] Packaged macOS `.app` and Windows launcher
- [ ] Tests and first-run onboarding

## Architecture

- Python + Flask local server
- HTML/CSS/vanilla JavaScript interface
- SQLite as the source of truth
- Google Sheets planned as an optional cloud sync destination

**Local-first by design:** the app should remain useful without Wi-Fi. Cloud sync will never be required to create or read notes.
