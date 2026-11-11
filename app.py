from pathlib import Path
import math

import numpy as np
from astropy.io import fits
from astropy.table import Table
from flask import Flask, abort, jsonify, render_template
import gdown

app = Flask(__name__)
DATA_FILE = Path(__file__).parent / "data" / "CSC_AGN_prepared.fits"
DRIVE_FILE_ID = "1lszZgVoO0X01oQq7IXQItBTqXD6U8aE8"

# Boolean-like flag columns that can be overplotted in the viewer
FLAGS = ["IR_AGN_wedge", "IR_AGN_line", "Xray_AGN"]

# Extra columns shown in the info panel when a source is clicked.
# Add column names from your FITS table here, e.g. ["z", "log_Lx", "class"]
EXTRA_COLUMNS = []


# How each flag is labelled and coloured (keep in step with skyviewer.html)
FLAG_INFO = {
    "IR_AGN_wedge": ("IR AGN (Mateos+2012)", "#ff9f1c"),
    "IR_AGN_line": ("IR AGN (Assef+2013)", "#2ec4b6"),
    "Xray_AGN": ("X-ray AGN", "#ff4d6d"),
}

def ensure_data():
    """Download the FITS file from Google Drive if it isn't already on disk."""
    if not DATA_FILE.exists():
        DATA_FILE.parent.mkdir(exist_ok=True)
        print("Downloading data file from Google Drive (first run only)...")
        gdown.download(f"https://drive.google.com/uc?id={DRIVE_FILE_ID}", str(DATA_FILE), quiet=False)

ensure_data()
def clean_name(value):
    # FITS string columns often come back as bytes
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return str(value).strip()


def jsonable(value):
    """Convert numpy/FITS values into something JSON can carry."""
    if value is np.ma.masked or value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        f = float(value)
        return f if math.isfinite(f) else None
    return str(value).strip()


def to_bool(value):
    """Turn True/False, 1/0, 'T'/'F', 'yes'/'no' (or masked/NaN) into a Python bool."""
    if value is np.ma.masked or value is None:
        return False
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    if isinstance(value, str):
        return value.strip().lower() in {"true", "t", "1", "yes", "y"}
    try:
        f = float(value)
    except (TypeError, ValueError):
        return bool(value)
    return math.isfinite(f) and f != 0


def read_data():
    with fits.open(DATA_FILE) as hdul:
        table = Table(hdul[1].data)

    # case-insensitive lookup of the flag columns
    lookup = {c.lower(): c for c in table.colnames}
    flag_cols = {}
    for flag in FLAGS:
        col = lookup.get(flag.lower())
        if col is None:
            print(f"Warning: column '{flag}' not found in {DATA_FILE.name}; treating as False")
        flag_cols[flag] = col

    extra_cols = []
    for name in EXTRA_COLUMNS:
        col = lookup.get(name.lower())
        if col is None:
            print(f"Warning: extra column '{name}' not found in {DATA_FILE.name}")
        else:
            extra_cols.append((name, col))

    records = []
    for row in table:
        ra = float(row["ra"])
        dec = float(row["dec"])
        if not (math.isfinite(ra) and math.isfinite(dec)):
            continue  # skip rows without usable coordinates
        record = {
            "name": clean_name(row["name"]),
            "RA": ra,
            "DEC": dec,
        }
        for label, col in extra_cols:
            record[label] = jsonable(row[col])
        for flag, col in flag_cols.items():
            record[flag] = to_bool(row[col]) if col else False
        records.append(record)
    return records


# ---------- single-source pages ----------

_cache = {"mtime": None, "table": None, "index": None}


def get_table():
    """Read the FITS table once and reload it only if the file changes."""
    mtime = DATA_FILE.stat().st_mtime
    if _cache["mtime"] != mtime:
        with fits.open(DATA_FILE) as hdul:
            table = Table(hdul[1].data)
        index = {}
        for i, value in enumerate(table["name"]):
            index.setdefault(clean_name(value).lower(), i)
        _cache.update(mtime=mtime, table=table, index=index)
    return _cache["table"], _cache["index"]


def display_value(column, value):
    """Format a table cell as text for the detail page."""
    if value is np.ma.masked or value is None:
        return "\u2014"
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace").strip()
    if isinstance(value, (np.bool_, bool)):
        return "True" if value else "False"
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (np.floating, float)):
        f = float(value)
        if not math.isfinite(f):
            return "\u2014"
        if column.lower() in ("ra", "dec"):
            return f"{f:.6f}"
        return f"{f:.6g}"
    if hasattr(value, "tolist"):  # array-valued columns
        text = str(value.tolist())
        return text if len(text) < 200 else text[:197] + "..."
    return str(value).strip()


def sexagesimal(ra, dec):
    h = ra / 15
    hh, mm = int(h), int((h - int(h)) * 60)
    ss = ((h - hh) * 60 - mm) * 60
    sign = "-" if dec < 0 else "+"
    d = abs(dec)
    dd, dm = int(d), int((d - int(d)) * 60)
    ds = ((d - dd) * 60 - dm) * 60
    return f"{hh:02d}:{mm:02d}:{ss:05.2f}", f"{sign}{dd:02d}:{dm:02d}:{ds:04.1f}"


@app.route("/source/<path:name>")
def source(name):
    table, index = get_table()
    i = index.get(name.strip().lower())
    if i is None:
        abort(404)
    row = table[i]

    lookup = {c.lower(): c for c in table.colnames}
    ra, dec = float(row[lookup["ra"]]), float(row[lookup["dec"]])
    ra_hms, dec_dms = sexagesimal(ra, dec)

    flags = []
    for key, (label, color) in FLAG_INFO.items():
        col = lookup.get(key.lower())
        flags.append({"label": label, "color": color, "set": bool(col and to_bool(row[col]))})

    columns = [(c, display_value(c, row[c])) for c in table.colnames]
    return render_template(
        "source.html",
        name=clean_name(row[lookup["name"]]),
        ra=ra, dec=dec, ra_hms=ra_hms, dec_dms=dec_dms,
        flags=flags, columns=columns,
    )


@app.errorhandler(404)
def not_found(_):
    return render_template("notfound.html"), 404


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/skyviewer")
def skyviewer():
    return render_template("skyviewer.html")

@app.route("/about/credits")
def credits(): 
    return render_template("about/credits.html")
@app.route("/about/team")
def team(): 
    return render_template("about/our_team.html")
@app.route("/about/users")
def users(): 
    return render_template("about/our_users.html")
@app.route("/behind_the_scenes/analysis")
def analysis(): 
    return render_template("behind_the_scenes/analysis.html")
@app.route("/behind_the_scenes/processing")
def processing(): 
    return render_template("behind_the_scenes/processing.html")
@app.route("/data_access/download")
def download(): 
    return render_template("data_access/download.html")
@app.route("/data_access/organization")
def organization(): 
    return render_template("data_access/organization.html")
@app.route("/data_access/overview")
def overview(): 
    return render_template("data_access/overview.html")
@app.route('/contact')
def contact(): 
    return render_template('contact.html')


@app.route("/api/data")
def api_data():
    response = jsonify(read_data())
    response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    app.run(debug=True, port=5000)