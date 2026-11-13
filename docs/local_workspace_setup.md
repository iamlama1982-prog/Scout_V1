# Using the standalone Scout folder

This project was separated from the earlier Ops Sentinel workspace.

For a fresh checkout:

```powershell
git clone https://github.com/iamlama1982-prog/Scout.git
cd Scout
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Download `incidents.csv` from [SevAnalysis](https://sevanalysis.com/data/)
and either upload it in Scout's sidebar, or place it at
`data/raw/incident_taxonomy/snapshot_2026-10-23/incidents.csv`.

**Existing cases are stored locally** in `data/scout_cases.db`. If moving
from a different local Scout folder, stop Streamlit first and copy the database
into the matching location in the new folder. Make a separate backup first.
The entire `data/` directory apart from its README is excluded from Git.

If old cases do not appear, check that Streamlit was launched from the folder
containing the database. Never overwrite one existing database with another
without backing up both.
