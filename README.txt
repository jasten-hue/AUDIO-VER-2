HOW TO BUILD THE .EXE
======================

1. Copy this whole "exe_project" folder to your Windows PC.

2. Into the lib/ folder, put your 3 real library files
   (replacing the placeholder txt file):
     - chart.umd.min.js
     - chartjs-plugin-zoom.min.js
     - papaparse.min.js
   (the same ones your index.html already <script src="lib/...">'s)

3. Make sure Python 3.9+ is installed on Windows
   (python.org installer, or "python" from the Microsoft Store).
   During install, check "Add python.exe to PATH".

4. Open Command Prompt in the exe_project folder and run:

       build.bat

   This installs pywebview, py7zr, pillow and pyinstaller, then builds the exe.
   First run can take a couple of minutes.

5. Your finished app is at:

       dist\AudioTestLogAnalyzer.exe

   Double-click it — it opens as a normal desktop window,
   no browser, no console window. You can copy that single
   .exe anywhere and it'll run standalone (index.html and the
   lib/ files are baked inside it).

NOTES
-----
- pywebview uses the WebView2 runtime on Windows, which comes
  preinstalled on Windows 10 (recent updates) and Windows 11.
  If the window opens blank on an older machine, install the
  "WebView2 Runtime" from Microsoft (free, small download).

- If you edit index.html later, just re-run build.bat to
  rebuild the exe.

- If PyInstaller/antivirus flags a false positive (common with
  onefile exes), you can drop --onefile from build.bat to get
  a dist\AudioTestLogAnalyzer\ folder instead of a single exe —
  it runs the same way, just isn't flagged as often.

- Fetch Logs: fetched .7z files are downloaded to a temporary file,
  only the images inside are extracted, and the .7z is deleted.
  Images are stored next to the .exe in:

       downloads\.extracted\<archive name>\

  Fetching the same serial number again does not re-download
  archives that were already extracted. The "Open folder" button in
  the Fetch dialog opens that folder.

- FTP_USER / FTP_PASS are set at the top of app.py.

- After building, test the .exe once with a real fetch: py7zr uses
  compiled helper libraries, and build.bat bundles them with
  --collect-all py7zr. If a fetch fails only in the .exe, check the
  error text shown in the Fetch dialog.
