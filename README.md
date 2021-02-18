# ytarchive-ui
Web UI for ytarchive

## Dependencies
- python3
- falcon (python3 package)

### Windows
- waitress (python3 package)

### Linux
- gunicorn (python3 package)

## Usage
Put `ytarchive.exe` in the dir (`ytarchive.py` if not Windows OS, don't forget to give it a executable permission), also `cookie.txt` if needed (optional).

run `run.bat` (Windows) or `run.sh` (\*nix).

```
Serving on <URL>
```

Simply open the URL and enjoy!

The status on the Web UI is stored at the backend part, so feel free to refresh or close the webpage at anytime!

Click on the status (Success or Failed one) to see the log.
