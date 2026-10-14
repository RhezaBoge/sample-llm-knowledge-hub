# Project Knowledge Hub

A sample of how a **local AI language model (LLM)** can power a **knowledge repository**:
it turns project documents (reports, proposals, meeting notes) into **tidy, comparable data** –
and puts every project on a map.

You decide which facts to collect (title, organization, country, city, dates, summary,
keywords – or your own). The AI reads each document and fills them in. A person checks the
result. Everything is saved in one knowledge base you can search, map and download.

- **Free:** no account, no subscription, no graphics card (GPU) needed.
- **Private:** the AI runs on your own computer. Your documents are not sent to an AI company.
- **Open:** every step is visible – the template, the exact AI prompt, the raw AI answer and the
  final GeoJSON. How it is built: [docs/TECHNICAL.md](docs/TECHNICAL.md).

> All sample documents and organizations in this project are fictional.

**Contents:**
[What you need](#what-you-need) ·
[1. Install Docker](#step-1--install-docker-desktop-one-time) ·
[2. Download](#step-2--download-this-project) ·
[3. Start](#step-3--start-the-app) ·
[4. Stop](#step-4--stop-the-app-when-you-are-done) ·
[Using the app](#using-the-app) ·
[Safety & privacy](#safety-and-privacy) ·
[AI model](#choosing-the-ai-model) ·
[Problems?](#if-something-goes-wrong) ·
[Uninstall](#uninstall) ·
[For developers](#for-developers)

---

## What you need

| | Minimum | Better |
|---|---|---|
| Computer | Windows 10/11 (64-bit), a Mac (macOS 12 or newer), or Linux | |
| Memory (RAM) | 8 GB | 16 GB |
| Free disk space | 10 GB | 15 GB |
| Internet | Only for the first installation (downloads about 5–8 GB) and for the map | |

You install **one program**: Docker Desktop. It runs the app in a closed "box" so nothing
else on your computer is changed. You do **not** need to install Python, Node.js or Git.

---

## Step 1 – Install Docker Desktop (one time)

<details open>
<summary><b>Windows</b></summary>

1. Go to <https://www.docker.com/products/docker-desktop/> and click **Download for Windows**.
2. Open the downloaded file `Docker Desktop Installer.exe`.
3. Keep the option **Use WSL 2** ticked and click **OK**. Wait until it finishes.
4. **Restart your computer** when asked.
5. Open **Docker Desktop** from the Start menu. Accept the terms if you agree.
   You can skip signing in (choose *Continue without signing in* / *Skip*).
6. Wait until the bottom-left corner of Docker Desktop shows **Engine running** (green).

If you see a message about **WSL**, open *PowerShell* from the Start menu, type
`wsl --update`, press Enter, and restart the computer.
</details>

<details open>
<summary><b>Mac</b></summary>

1. Check your chip: click the Apple menu  → **About This Mac**. It says *Apple M1/M2/M3/M4…* or *Intel*.
2. Go to <https://www.docker.com/products/docker-desktop/> and download the version for your chip.
3. Open the downloaded `Docker.dmg` and drag **Docker** into **Applications**.
4. Open **Docker** from Applications. Accept the terms if you agree. Signing in is not needed.
5. Wait until the whale icon in the top menu bar stops moving and Docker Desktop shows **Engine running**.
</details>

<details open>
<summary><b>Linux</b></summary>

Install **Docker Desktop for Linux** (<https://docs.docker.com/desktop/setup/install/linux/>)
or **Docker Engine** with the Compose plugin (<https://docs.docker.com/engine/install/>) –
follow the page for your distribution (Ubuntu, Debian, Fedora, …).

With Docker Engine, allow your user to run Docker without `sudo`, then log out and in again:

```bash
sudo usermod -aG docker $USER
```
</details>

### Important: stop Docker from starting by itself

So Docker does not run in the background and slow down the laptop every day:

- **Windows and Mac:** open Docker Desktop → **Settings** (gear icon) → **General** →
  untick **Start Docker Desktop when you sign in to your computer** → **Apply**.
- **Linux (Docker Engine):** run `sudo systemctl disable docker.service docker.socket`.
  Before using the app, start Docker with `sudo systemctl start docker`.

From now on, Docker only runs when **you** open it.

> **Licence note:** Docker Desktop is free for personal use, education, non-commercial open-source
> projects and small organizations. Larger organizations may need a paid Docker subscription –
> check <https://www.docker.com/pricing/> or ask your IT team.

---

## Step 2 – Download this project

**Option A – easiest (no extra software):**

1. Go to <https://github.com/RhezaBoge/sample-llm-knowledge-hub>, click the green **Code** button → **Download ZIP**.
2. Unzip (extract) the file, for example into your **Documents** folder.
   - Windows: right-click the ZIP → **Extract All…**
   - Mac: double-click the ZIP.

**Option B – with Git** (if you already use it):

```bash
git clone https://github.com/RhezaBoge/sample-llm-knowledge-hub.git
```

---

## Step 3 – Start the app

First open **Docker Desktop** and wait until it is running. Then:

<details open>
<summary><b>Windows</b></summary>

Open the project folder and **double-click `start.bat`**.

If Windows shows *"Windows protected your PC"*, click **More info** → **Run anyway**.
(This appears for any downloaded script. You can open `start.bat` in Notepad to see what it does.)
</details>

<details open>
<summary><b>Mac</b></summary>

1. Open **Terminal** (press `Cmd` + `Space`, type *Terminal*, press Enter).
2. Type `cd` followed by a **space**. Do not press Enter yet.
3. **Drag the project folder** from Finder into the Terminal window, then press **Enter**.
4. Type `bash start.sh` and press **Enter**.
</details>

<details open>
<summary><b>Linux</b></summary>

Open a terminal in the project folder and run:

```bash
bash start.sh
```
</details>

**The first start takes 10–30 minutes**, because it downloads the app and the AI model
(about 5–8 GB). Leave the window open until it says **Ready!**. Your browser then opens
<http://localhost:5173>. Next time it starts in under a minute.

---

## Step 4 – Stop the app when you are done

- **Windows:** double-click **`stop.bat`**.
- **Mac / Linux:** in Terminal, in the project folder, run `bash stop.sh`.

Then quit Docker Desktop (whale icon → **Quit Docker Desktop**). Nothing keeps running in the
background, and your saved projects stay safe in the `data` folder.

---

## Using the app

The app has three steps, shown at the top of the page.

1. **Set up your fields** – which facts to collect from every document. By default: Project title,
   Implementing organization, Country, City, Start date, End date, Summary, Keywords, SDGs.
   Every field has its **own instruction for the AI**, a type (text / date / number), and a switch
   *Several values* (separated by `;`). Add, rename, reorder or remove fields and click
   **Save template**. *Show the AI prompt* displays the exact question the AI receives.
2. **Add a project** – upload a document, paste text, or load one of the sample documents.
   Twenty more fictional documents to try are in [docs/datatest](docs/datatest/).
   - **Markdown (`.md`) works best**: it keeps headings, lists and tables as clean text.
     For a document in Google Drive: open it in Google Docs → *File → Download → Markdown (.md)*.
     Word (`.docx`), PDF and `.txt` also work. Scanned PDFs (photos of pages) do not contain text.
   - Choose **AI language model** or **Simple rules (no AI)** – try both and compare.
   - Check every field against the document, look at the map, tick
     *"I have checked this data"* and click **Save to knowledge base**.
3. **Knowledge base** – search, filter by country, see all projects on one map, and download one
   project or all of them as **GeoJSON** (opens in QGIS, ArcGIS, Google Earth, geojson.io, …).

---

## Safety and privacy

- **Your documents stay on your computer.** The AI model runs locally inside Docker.
- **Only you can open the app.** It is reachable only from your own computer
  (`localhost`), not from other people on the same Wi-Fi.
- **Nothing starts automatically.** The app runs only between `start` and `stop`.
- **What does use the internet:** the map background (OpenStreetMap) and the place lookup – the
  **names** in the City and Country fields are sent to OpenStreetMap to find them on the map.
  The document itself is not sent. To switch the place lookup off, set `GEOCODER=none` in `.env`.
- **Your data** is one file: `data/knowledge.db`. To make a backup, copy the `data` folder.
- **The AI makes mistakes.** It can miss or invent facts. That is why a person checks every
  record before it is saved.
- Avoid personal data (names of beneficiaries, health information) unless your organization allows it.

---

## Choosing the AI model

No graphics card is needed – the model runs on the normal processor (CPU).
The default model works on most laptops. Choose another one if your laptop is slow or strong:

| Model | Download | Memory (RAM) | Quality | For |
|---|---|---|---|---|
| `qwen2.5:1.5b` | ~1 GB | 8 GB laptop | basic, misses details | older laptops |
| `qwen2.5:3b` **(default)** | ~2 GB | 8 GB laptop | good | most laptops |
| `qwen2.5:7b` | ~4.7 GB | 16 GB laptop | best of the three | strong laptops |

Measured on an Apple M2 Pro: `qwen2.5:7b` read a sample document in **36 seconds on the CPU only**.
Expect 20 seconds to a few minutes per document, depending on the laptop and model.

**To change the model:**

1. Run the app once, so the settings file `.env` exists in the project folder.
2. Open `.env` with a text editor (Notepad on Windows, TextEdit on Mac).
   On a Mac, files starting with a dot are hidden: press `Cmd` + `Shift` + `.` in Finder to show them.
3. Change the line `LLM_MODEL=qwen2.5:3b`, save, then stop and start the app again.
   The new model is downloaded automatically.

**Faster on a Mac (optional):** install the [Ollama](https://ollama.com) app (it can use the Mac's
graphics chip), run `ollama pull qwen2.5:3b` in Terminal, and set
`LLM_BASE_URL=http://host.docker.internal:11434/v1` in `.env`.

**Cloud AI services** (Groq, OpenRouter, Google Gemini, …) also work – see the examples in
[.env.example](.env.example). Only use them with documents you are allowed to share with that company.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| *Docker is not installed* | Do [Step 1](#step-1--install-docker-desktop-one-time). |
| *Docker is installed but not running* | Open Docker Desktop and wait until it shows **Engine running**, then start again. |
| Windows: a message about **WSL** | Open PowerShell, run `wsl --update`, restart the computer. |
| *port is already allocated* | Another program uses port 5173 or 8000. Open `.env` and change `APP_PORT` / `API_PORT` (e.g. `5180` and `8001`), then start again. The app then opens at `http://localhost:5180`. |
| The app says **AI model offline** | Run start again. Meanwhile, *Simple rules (no AI)* still works. |
| *Model download failed* | Check your internet connection and run start again. It continues where it stopped. |
| The AI takes very long or stops | Choose a smaller model (see above), or give Docker more memory: Docker Desktop → **Settings → Resources → Memory**. Close other programs. |
| Mac / Linux: *permission denied* | Type `bash start.sh` (not `./start.sh`). |
| Linux: *permission denied … docker.sock* | Run `sudo usermod -aG docker $USER`, then log out and in again. |
| A place is in the wrong spot on the map | Make the City field more precise, e.g. `Lewa, East Sumba`. |

---

## Uninstall

1. Stop the app (Step 4).
2. To also delete the downloaded AI model and app images (about 5–8 GB), open a terminal in the
   project folder and run:
   ```bash
   docker compose --profile setup down --volumes --rmi local
   ```
   (Or in Docker Desktop: delete the *project-knowledge-hub* items under **Containers**,
   **Images** and **Volumes**.)
3. Delete the project folder. **This also deletes your saved projects** (`data` folder) – copy it first if needed.
4. If you no longer need Docker, uninstall Docker Desktop like any other program.

---

## For developers

**Stack:** React (Vite + Leaflet) · FastAPI · SQLAlchemy + SQLite · Ollama · Docker Compose · GitHub Actions

```
Set up fields ──► Document ──► AI extraction ──► Checks & map ──► Human review ──► SQL knowledge base
 (your template)  (MD/DOCX/PDF)  (LLM → JSON)     (Python + OSM)    (web form)       (GeoJSON, map, search)
```

**Key design idea:** language models are good at *reading* (even other languages) but bad at
*knowing facts* such as coordinates. In tests, `qwen2.5:7b` placed villages in Kenya 500–700 km
off. So the AI only extracts place **names**; real coordinates come from OpenStreetMap; and a
person checks the map before saving.

### The data template

Fields are rows in the SQL table `template_fields`. Each saved project becomes one GeoJSON
`Feature` whose `properties` are exactly your fields:

```json
{
  "type": "Feature",
  "id": "PRJ-0001",
  "geometry": { "type": "MultiPoint", "coordinates": [[35.5973, 3.1191], [34.8735, 3.7063]] },
  "properties": {
    "project_id": "PRJ-0001",
    "title": "Safe Motherhood Turkana",
    "organization": ["Afya Bora Partners"],
    "country": ["Kenya"],
    "city": ["Lodwar", "Kakuma"],
    "start_date": "2021-01",
    "end_date": "2024-06",
    "summary": "Improved maternal health in Turkana County ...",
    "keywords": ["maternal health", "antenatal care"],
    "locations": [{ "name": "Lodwar", "latitude": 3.1191, "longitude": 35.5973 }],
    "source": { "document": "notes.md", "extraction_method": "llm", "model": "qwen2.5:3b", "reviewed_by_human": true }
  }
}
```

Fields marked *several values* are stored as JSON lists. The fields with the keys `country` and
`city` place the project on the map; everything else is yours to define. The default fields live
in [backend/app/template.py](backend/app/template.py).

### Project structure

```
├── start.bat / start.sh        # start the app (Windows / Mac & Linux)
├── stop.bat / stop.sh          # stop the app
├── docker-compose.yml          # backend + frontend + ollama
├── .env.example                # settings (AI model, database, place lookup)
├── backend/                    # FastAPI
│   ├── app/
│   │   ├── main.py             # API endpoints
│   │   ├── template.py         # ★ default fields, template storage, cleaning, GeoJSON
│   │   ├── extractor.py        # ★ builds the AI prompt from the template + "simple rules"
│   │   ├── llm.py              # tiny client for any OpenAI-compatible API
│   │   ├── geocoder.py         # place name → coordinates (OpenStreetMap Nominatim)
│   │   ├── locator.py          # City + Country fields → points on the map
│   │   ├── text_reader.py      # MD / DOCX / PDF / TXT → text
│   │   ├── models.py           # SQL tables: template_fields, settings, projects
│   │   └── database.py         # SQLAlchemy connection
│   ├── sample_documents/       # 4 fictional project documents
│   └── tests/                  # pytest
├── frontend/                   # React + Vite
│   └── src/
│       ├── pages/              # TemplateSetup, AddProject, KnowledgeBase
│       └── components/         # map, review form, small UI pieces
├── docs/
│   ├── TECHNICAL.md            # architecture and how the system is built
│   └── datatest/               # 20 fictional project documents (.md) to try
└── .github/workflows/ci.yml    # tests + build on every push
```

The API documentation (try every endpoint) is at <http://localhost:8000/docs> while the app runs.
Code changes in `backend/app` and `frontend/src` reload automatically.

### Useful commands

```bash
docker compose logs -f backend                    # API requests and errors
docker compose exec ollama ollama list            # downloaded models
docker compose run --rm ollama-pull               # download the model set in .env
docker compose up -d --build backend frontend     # start without the scripts
```

To start with an empty knowledge base, stop the app and delete `data/knowledge.db`.

### Running without Docker

```bash
# backend (Python 3.11+), with Ollama installed on the computer
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
LLM_BASE_URL=http://localhost:11434/v1 uvicorn app.main:app --reload

# frontend (Node 20+), in a second terminal
cd frontend && npm install && npm run dev
```

Run the tests with `cd backend && pytest`.

### Technical documentation

See [docs/TECHNICAL.md](docs/TECHNICAL.md) for the architecture, data flow, data model, API and design decisions.
