# -*- coding: utf-8 -*-
"""
Wagara Recommender (Streamlit single-file)
- English UI
- External JSON (data/patterns_en.json)
- Simple Add: image -> pattern (+optional tags), auto color palette
- Cards prioritize IMAGES (up to 3)
- Color chips toggle (default: OFF)
- Strong Gallery: forcibly discovers & displays images
- Pattern Manager + bulk import, image link manager
- Reset tools & delete-all
- Hero background prefers assets/backgrounds/hero_placeholder.png (MIME fixed)
- Debug panel

Run:  streamlit run streamlit_app.py
"""
from __future__ import annotations
import base64, json, os, glob
from dataclasses import dataclass
from typing import Any, Dict, List

import streamlit as st
from PIL import Image

# ==============================================
# PAGE CONFIG
# ==============================================
st.set_page_config(
    page_title="Wagara Recommender",
    page_icon="🎴",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_BG = os.path.join(APP_DIR, "assets", "backgrounds")
ASSETS_PATTERNS = os.path.join(APP_DIR, "assets", "patterns")
DATA_DIR = os.path.join(APP_DIR, "data")
IMAGE_INDEX_JSON = os.path.join(DATA_DIR, "images.json")
PATTERN_JSON_PATH = os.path.join(DATA_DIR, "patterns_en.json")

os.makedirs(ASSETS_BG, exist_ok=True)
os.makedirs(ASSETS_PATTERNS, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Ensure files exist
if not os.path.exists(PATTERN_JSON_PATH):
    with open(PATTERN_JSON_PATH, "w", encoding="utf-8") as f:
        f.write("[]")
if not os.path.exists(IMAGE_INDEX_JSON):
    with open(IMAGE_INDEX_JSON, "w", encoding="utf-8") as f:
        f.write("{}")

# ==============================================
# CSS / STYLE
# ==============================================
def _encode_image_b64(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None

FONTS_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;600;700&family=Zen+Maru+Gothic:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{--card-radius:1.25rem;}
html, body, [class^="css"]{font-family:"Zen Maru Gothic", "Noto Serif JP", system-ui, -apple-system, Segoe UI, Roboto, sans-serif;}
section.main > div {padding-top:0 !important}
/* hero */
.hero{position:relative; width:100%; min-height:46vh; display:flex; align-items:center; justify-content:center; overflow:hidden;}
.hero::before{content:""; position:absolute; inset:0; background:var(--hero-bg, linear-gradient(120deg,#0f172a 0%,#111827 100%)); background-size:cover; background-position:center; filter:contrast(0.95) saturate(0.9);}
.hero::after{content:""; position:absolute; inset:0; background:radial-gradient(ellipse at 20% 10%, rgba(255,255,255,.12), transparent 40%), radial-gradient(ellipse at 80% 90%, rgba(255,255,255,.08), transparent 40%);}
.hero-inner{position:relative; padding:2rem 2.4rem; text-align:center; backdrop-filter: blur(6px); background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,.18); border-radius:1.5rem;}
.hero-title{font-size:clamp(2rem,4vw,3.2rem); font-weight:800; color:#fff; letter-spacing:0.04em;}
.hero-sub{margin-top:.5rem; color:#e5e7eb; font-size:clamp(.95rem,1.6vw,1.1rem)}
/* cards */
.rec-card{background:#fff; border-radius:var(--card-radius); padding:1rem 1.1rem; box-shadow:0 10px 24px rgba(0,0,0,.06); border:1px solid #eef2f7}
.rec-title{font-size:1.25rem; font-weight:800; margin-bottom:.35rem}
.rec-badge{display:inline-block; border:1px solid #e5e7eb; padding:.15rem .5rem; border-radius:999px; margin-right:.3rem; font-size:.8rem; color:#334155; background:#f8fafc}
.colors{display:flex; gap:.5rem; flex-wrap:wrap;}
.color-chip{display:flex; align-items:center; gap:.5rem; border-radius:.75rem; border:1px solid #e5e7eb; padding:.5rem .7rem;}
.color-swatch{width:20px; height:20px; border-radius:6px; border:1px solid rgba(0,0,0,.1)}
.small-muted{color:#64748b; font-size:.85rem}
/* sidebar */
[data-testid="stSidebar"] {border-right:1px solid #e5e7eb}
</style>
"""

# Hero background (prefer hero_placeholder.png) — MIME fixed
hero_img_b64 = None
hero_mime = None
for cand in ("hero_placeholder.png", "hero.jpg", "hero.png", "hero.jpeg"):
    p = os.path.join(ASSETS_BG, cand)
    if os.path.exists(p):
        hero_img_b64 = _encode_image_b64(p)
        ext = os.path.splitext(cand)[1].lower()
        hero_mime = "image/png" if ext == ".png" else "image/jpeg"
        break
hero_style = f"<style>.hero{{--hero-bg:url('data:{hero_mime};base64,{hero_img_b64}')}}</style>" if hero_img_b64 else ""
st.markdown(FONTS_CSS + hero_style, unsafe_allow_html=True)

# ==============================================
# DATA MODEL
# ==============================================
@dataclass
class Pattern:
    name: str
    motifs: List[str]
    seasons: List[str]
    formality: List[str]
    mood: List[str]
    genders: List[str]
    contrast_pref: List[str]
    color_palettes: List[List[str]]
    notes: str = ""

@st.cache_data(show_spinner=False)
def load_patterns_from_json(path: str) -> List[Pattern]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        patterns: List[Pattern] = []
        for i, obj in enumerate(data):
            try:
                patterns.append(Pattern(
                    name=obj["name"],
                    motifs=list(obj.get("motifs", [])),
                    seasons=list(obj.get("seasons", [])),
                    formality=list(obj.get("formality", [])),
                    mood=list(obj.get("mood", [])),
                    genders=list(obj.get("genders", [])),
                    contrast_pref=list(obj.get("contrast_pref", [])),
                    color_palettes=[list(p) for p in obj.get("color_palettes", [])],
                    notes=obj.get("notes", ""),
                ))
            except Exception as e:
                st.error(f"Invalid pattern at index {i}: {e}")
        return patterns
    except FileNotFoundError:
        st.warning(f"Pattern JSON not found: {path}. Using empty list.")
        return []
    except Exception as e:
        st.error(f"Failed to load patterns: {e}")
        return []

def save_patterns_to_json(path: str, patterns: List[Pattern]) -> bool:
    try:
        payload = []
        for p in patterns:
            payload.append({
                "name": p.name,
                "motifs": list(p.motifs),
                "seasons": list(p.seasons),
                "formality": list(p.formality),
                "mood": list(p.mood),
                "genders": list(p.genders),
                "contrast_pref": list(p.contrast_pref),
                "color_palettes": [list(c) for c in p.color_palettes],
                "notes": p.notes,
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        load_patterns_from_json.clear()
        return True
    except Exception as e:
        st.error(f"Failed to save patterns: {e}")
        return False

PATTERNS: List[Pattern] = load_patterns_from_json(PATTERN_JSON_PATH)

# ==============================================
# COLOR UTILS
# ==============================================
def hex_to_rgb(h: str):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0,2,4))

def rel_luminance(rgb):
    def f(c): c = c/255.0; return c/12.92 if c <= 0.04045*255 else ((c+0.055)/1.055)**2.4
    r,g,b = rgb; r,g,b = f(r), f(g), f(b); return 0.2126*r + 0.7152*g + 0.0722*b

def contrast(a_hex, b_hex):
    L1 = rel_luminance(hex_to_rgb(a_hex)); L2 = rel_luminance(hex_to_rgb(b_hex))
    hi, lo = (max(L1, L2), min(L1, L2)); return (hi + 0.05) / (lo + 0.05)

def pick_contrasting_color(base: str, palette: List[str], desired: str):
    target = {"Low":(1.1,1.8), "Medium":(1.8,3.5), "High":(3.5,21.0)}.get(desired, (1.8,3.5))
    cand = []
    for c in palette:
        if c == base: continue
        cr = contrast(base, c)
        if target[0] <= cr <= target[1]: cand.append((cr, c))
    if not cand:
        mid = sum(target)/2
        return min(palette, key=lambda c: abs(contrast(base, c) - mid))
    return sorted(cand, key=lambda x: abs(x[0] - sum(target)/2))[0][1]

# ==============================================
# SCORING & RECOMMENDATION
# ==============================================
WEIGHTS = {"gender":1.0,"mood":1.1,"season":0.9,"formality":1.0,"motif":0.8,"contrast":0.6}

def score_pattern(p: Pattern, prefs: Dict[str, Any]) -> float:
    s = 0.0
    if (g := prefs.get("gender")) and (g in p.genders or "Unisex" in p.genders): s += WEIGHTS["gender"]
    if (m := prefs.get("mood")) and (m in p.mood): s += WEIGHTS["mood"]
    if (ss := prefs.get("season")) and (ss in p.seasons or "All year" in p.seasons): s += WEIGHTS["season"]
    if (t := prefs.get("tpo")) and (t in p.formality): s += WEIGHTS["formality"]
    if (mo := prefs.get("motif")) and (mo in p.motifs): s += WEIGHTS["motif"]
    if (c := prefs.get("contrast")) and (c in p.contrast_pref): s += WEIGHTS["contrast"]
    return s

def build_reasons(p: Pattern, prefs: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    if prefs.get("mood") in p.mood: reasons.append(f"Matches mood '{prefs['mood']}'")
    s = prefs.get("season")
    if s and (s in p.seasons or "All year" in p.seasons): reasons.append(f"Works for '{s}'")
    t = prefs.get("tpo")
    if t in p.formality: reasons.append(f"Appropriate for '{t}'")
    m = prefs.get("motif")
    if m in p.motifs: reasons.append(f"Motif '{m}' included")
    if prefs.get("contrast") in p.contrast_pref: reasons.append(f"Good for contrast '{prefs['contrast']}'")
    if not reasons: reasons.append("Versatile and easy to coordinate")
    return reasons

def pick_combo(p: Pattern, prefs: Dict[str, Any]) -> Dict[str, Any]:
    palette = p.color_palettes[0] if p.color_palettes else ["#222222","#dddddd","#aaaaaa"]
    if len(p.color_palettes) > 1:
        idx = (hash(p.name + str(prefs)) % len(p.color_palettes))
        palette = p.color_palettes[idx]
    base_kimono = palette[0]
    sub1 = palette[1] if len(palette) > 1 else palette[0]
    sub2 = palette[2] if len(palette) > 2 else palette[0]
    desired_contrast = prefs.get("contrast", "Medium")
    obi = pick_contrasting_color(base_kimono, palette + ["#FFFFFF", "#000000"], desired_contrast)
    obijime = pick_contrasting_color(obi, palette, "Medium")
    obiage = sub2
    return {"kimono_base": base_kimono,"kimono_accent1": sub1,"kimono_accent2": sub2,"obi": obi,"obijime": obijime,"obiage": obiage}

def recommend(prefs: Dict[str, Any], k: int = 3):
    if not PATTERNS: return []
    scored = sorted(((score_pattern(p, prefs), p) for p in PATTERNS), key=lambda x: x[0], reverse=True)
    top = [p for _, p in scored[:k]]
    results = []
    for p in top:
        combo = pick_combo(p, prefs); reasons = build_reasons(p, prefs)
        results.append({"pattern": p.name,"motifs": p.motifs,"notes": p.notes,"reasons": reasons,"colors": combo})
    return results

# ==============================================
# IMAGE INDEX
# ==============================================
@st.cache_data(show_spinner=False)
def load_image_index() -> Dict[str, List[str]]:
    try:
        with open(IMAGE_INDEX_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        fixed = {}
        for k, v in data.items():
            fixed[k] = [p if os.path.isabs(p) else os.path.join(ASSETS_PATTERNS, os.path.basename(p)) for p in v]
        return fixed
    except Exception:
        return {}

def save_image_index(index: Dict[str, List[str]]):
    try:
        with open(IMAGE_INDEX_JSON, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        st.toast("Saved image index.", icon="✅")
        load_image_index.clear()
    except Exception as e:
        st.error(f"Failed to save: {e}")

@st.cache_data(show_spinner=False)
def list_all_pattern_images() -> List[str]:
    files = []
    if os.path.exists(ASSETS_PATTERNS):
        for fn in sorted(os.listdir(ASSETS_PATTERNS)):
            if fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                files.append(os.path.join(ASSETS_PATTERNS, fn))
    return files

# ==============================================
# UI HEADER
# ==============================================
st.markdown(
    '<div class="hero"><div class="hero-inner">'
    '<div class="hero-title">🎴 Wagara Recommender</div>'
    '<div class="hero-sub">Find kimono patterns and color palettes that match your mood, season, and style.</div>'
    '</div></div>', unsafe_allow_html=True
)
st.markdown("\n")

# ==============================================
# SIDEBAR
# ==============================================
with st.sidebar:
    st.header("Select your preferences")
    gender = st.radio("Gender (for style reference only)", ["Male","Female","Unisex"], index=2)
    mood = st.selectbox("Mood", ["Bright","Calm","Elegant","Sharp","Playful","Serene"], index=1)
    season = st.selectbox("Season", ["Spring","Summer","Autumn","Winter","All year"], index=4)
    tpo = st.selectbox("Formality", ["Casual","Semi-formal","Formal"], index=1)
    motif = st.selectbox("Motif type", ["Geometric","Nature","Classic","Modern","Lucky symbol"], index=0)
    contrast_level = st.radio("Contrast level", ["Low","Medium","High"], index=1, horizontal=True)
    show_colors = st.toggle("Show color palette", value=False)  # default OFF
    st.divider()
    edit_mode = st.toggle("Edit mode (upload/link images, manage patterns)", value=False)

# ==============================================
# RECOMMEND SECTION
# ==============================================
prefs = {"gender":gender, "mood":mood, "season":season, "tpo":tpo, "motif":motif, "contrast":contrast_level}
recs = recommend(prefs, k=3)

st.subheader("Top 3 matches")
img_index = load_image_index()
cols = st.columns(3 if recs else 1)

if recs:
    for i, (col, r) in enumerate(zip(cols, recs), start=1):
        with col:
            st.markdown('<div class="rec-card">', unsafe_allow_html=True)
            st.markdown(f"<div class='rec-title'>[{i}] {r['pattern']}</div>", unsafe_allow_html=True)
            st.markdown(" ".join([f"<span class='rec-badge'>{b}</span>" for b in r["motifs"]]), unsafe_allow_html=True)
            if r["notes"]:
                st.markdown("<div class='small-muted' style='margin-top:.35rem'>" + r["notes"] + "</div>", unsafe_allow_html=True)

            st.markdown("**Why it fits**")
            for reason in r["reasons"]:
                st.write("• ", reason)

            if show_colors:
                st.markdown("**Suggested colors**")
                c = r["colors"]
                items = [("Kimono base", c["kimono_base"]),("Accent 1", c["kimono_accent1"]),
                         ("Accent 2", c["kimono_accent2"]),("Obi", c["obi"]),
                         ("Obijime", c["obijime"]),("Obiage", c["obiage"])]
                chips_html = "<div class='colors'>" + "".join(
                    [f"<div class='color-chip'><span class='color-swatch' style='background:{hx}'></span><span>{label}</span><code style='margin-left:.25rem'>{hx}</code></div>"
                     for label, hx in items]) + "</div>"
                st.markdown(chips_html, unsafe_allow_html=True)

            # Preview images (max 3 side-by-side)
            if r["pattern"] in img_index and img_index[r["pattern"]]:
                st.markdown("**Preview**")
                imgs = img_index[r["pattern"]][:3]
                cols_img = st.columns(len(imgs))
                for j, pth in enumerate(imgs):
                    with cols_img[j]:
                        try:
                            with open(pth, "rb") as fh:
                                data = fh.read()
                            st.image(data, use_column_width=True, output_format="auto")
                        except Exception:
                            st.info("Failed to load image.")
            else:
                st.caption("No linked images. Add some in Edit mode.")
            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("No patterns yet. Go to Edit mode to create patterns, then link images.")

st.divider()

# ==============================================
# GALLERY (強制表示版)
# ==============================================
st.subheader("Image Gallery")

def _all_images_in_folder(folder: str) -> List[str]:
    if not os.path.isdir(folder):
        return []
    exts = ["png","jpg","jpeg","webp","PNG","JPG","JPEG","WEBP"]
    files: List[str] = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(folder, f"*.{ext}")))
    # Also include linked images if they exist
    try:
        idx = load_image_index()
        for paths in idx.values():
            for p in paths:
                if os.path.exists(p) and p not in files:
                    files.append(p)
    except Exception:
        pass
    files.sort(key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0)
    return files

gallery_files = _all_images_in_folder(ASSETS_PATTERNS)
if not gallery_files:
    st.warning(f"No images found in: {ASSETS_PATTERNS}")
    st.caption("Put images in assets/patterns or add via Edit mode → ✚ Simple Add.")
else:
    ncols = 4
    cols_g = [st.columns(ncols) for _ in range((len(gallery_files)+ncols-1)//ncols)]
    idx = 0
    for row in cols_g:
        for col in row:
            if idx >= len(gallery_files):
                break
            path = gallery_files[idx]; idx += 1
            with col:
                try:
                    with open(path, "rb") as fh:
                        data = fh.read()
                    st.image(data, use_column_width=True, caption=os.path.basename(path))
                except Exception as e:
                    st.error(f"Failed to display {os.path.basename(path)}: {e}")

st.divider()

# ==============================================
# EDIT MODE
# ==============================================
if edit_mode:
    st.divider()
    st.subheader("Initialize / Clean up")
    with st.expander("Reset tools (remove samples & start fresh)", expanded=False):
        st.caption("Caution: irreversible operations.")
        c1, c2 = st.columns(2)
        with c1:
            reset_index = st.button("Clear images.json (unlink all)", use_container_width=True)
        with c2:
            wipe_all = st.button("Delete all images in assets/patterns", use_container_width=True)
        confirm = st.checkbox("I understand. Go ahead.")
        if confirm and reset_index:
            try:
                with open(IMAGE_INDEX_JSON, "w", encoding="utf-8") as f: f.write("{}")
                load_image_index.clear(); st.success("Cleared images.json. Reloading…"); st.rerun()
            except Exception as e: st.error(f"Failed: {e}")
        if confirm and wipe_all:
            try:
                removed = 0
                if os.path.isdir(ASSETS_PATTERNS):
                    for fn in os.listdir(ASSETS_PATTERNS):
                        if fn.lower().endswith((".png",".jpg",".jpeg",".webp")):
                            try: os.remove(os.path.join(ASSETS_PATTERNS, fn)); removed += 1
                            except Exception: pass
                with open(IMAGE_INDEX_JSON, "w", encoding="utf-8") as f: f.write("{}")
                load_image_index.clear(); st.success(f"Removed {removed} files and cleared links. Reloading…"); st.rerun()
            except Exception as e: st.error(f"Failed: {e}")

    st.divider()
    st.subheader("Upload images / Link images to patterns")
    img_index = load_image_index()

    # ---------- Simple Add (image → pattern) ----------
    st.markdown("### ✚ Simple Add (image → pattern)")
    st.caption("Upload a wagara image, name the pattern, and (optionally) tick only attributes you want. Palette is auto-extracted.")

    def extract_palette_from_image(file_path: str, n: int = 3) -> List[str]:
        try:
            img = Image.open(file_path).convert("RGB"); img.thumbnail((150, 150))
            colors = img.getcolors(maxcolors=150*150)
            if not colors: return ["#333333", "#DDDDDD", "#999999"]
            colors.sort(reverse=True, key=lambda x: x[0])
            hexes = []
            for _, rgb in colors[: n * 4]:
                hx = '#%02X%02X%02X' % rgb
                if hx not in hexes: hexes.append(hx)
                if len(hexes) >= n: break
            while len(hexes) < n: hexes.append("#CCCCCC")
            return hexes
        except Exception:
            return ["#333333", "#DDDDDD", "#999999"]

    MOTIF_CHOICES = ["Geometric","Nature","Classic","Modern","Lucky symbol","Dynamic","Seasonal"]
    SEASON_CHOICES = ["Spring","Summer","Autumn","Winter","All year"]
    FORMALITY_CHOICES = ["Casual","Semi-formal","Formal"]
    MOOD_CHOICES = ["Bright","Calm","Elegant","Sharp","Playful","Serene","Graceful","Soft","Dynamic","Refined","Bold","Refreshing","Feminine"]
    GENDER_CHOICES = ["Male","Female","Unisex"]
    CONTRAST_CHOICES = ["Low","Medium","High"]

    colS1, colS2 = st.columns([2,1])
    with colS1:
        simple_image = st.file_uploader("Wagara image (single)", type=["png","jpg","jpeg","webp"], accept_multiple_files=False)
        simple_name = st.text_input("Pattern name", placeholder="e.g. Seigaiha (Blue Ocean Waves)")
        simple_motifs = st.multiselect("Motifs (optional)", options=MOTIF_CHOICES)
        simple_seasons = st.multiselect("Seasons (optional)", options=SEASON_CHOICES, default=["All year"])
        simple_formality = st.multiselect("Formality (optional)", options=FORMALITY_CHOICES)
        simple_mood = st.multiselect("Mood (optional)", options=MOOD_CHOICES)
        simple_genders = st.multiselect("Genders (optional)", options=GENDER_CHOICES, default=["Unisex"])
        simple_contrast = st.multiselect("Contrast preference (optional)", options=CONTRAST_CHOICES)
    with colS2:
        st.write(""); st.write("")
        go_simple = st.button("➕ Add this pattern from image", use_container_width=True)
        wipe_patterns = st.button("🗑️ Delete ALL existing patterns", use_container_width=True)

    if wipe_patterns:
        try:
            with open(PATTERN_JSON_PATH, "w", encoding="utf-8") as f: f.write("[]")
            load_patterns_from_json.clear(); st.success("All patterns removed. Reloading…"); st.rerun()
        except Exception as e: st.error(f"Failed: {e}")

    if go_simple:
        if not simple_image or not simple_name.strip():
            st.error("Need both an image and a pattern name.")
        else:
            dest = os.path.join(ASSETS_PATTERNS, simple_image.name)
            with open(dest, "wb") as f: f.write(simple_image.getbuffer())
            palette = extract_palette_from_image(dest, n=3)
            _patterns = list(PATTERNS)
            new_obj = Pattern(
                name=simple_name.strip(),
                motifs=list(simple_motifs), seasons=list(simple_seasons),
                formality=list(simple_formality), mood=list(simple_mood),
                genders=list(simple_genders) if simple_genders else ["Unisex"],
                contrast_pref=list(simple_contrast) if simple_contrast else ["Medium"],
                color_palettes=[palette], notes="",
            )
            updated = False
            for i, p in enumerate(_patterns):
                if p.name == new_obj.name:
                    _patterns[i] = new_obj; updated = True; break
            if not updated: _patterns.append(new_obj)
            ok = save_patterns_to_json(PATTERN_JSON_PATH, _patterns)
            # link image
            idx = dict(load_image_index()); idx.setdefault(new_obj.name, [])
            if dest not in idx[new_obj.name]: idx[new_obj.name].append(dest); save_image_index(idx)
            if ok: st.success("Added/updated pattern and linked the image. Reloading…"); st.rerun()

    # ---------- Advanced (optional) ----------
    st.markdown("### Advanced: Upload images / Link images to patterns (manual)")
    up_files = st.file_uploader("Add images (multiple allowed)", type=["png","jpg","jpeg","webp"], accept_multiple_files=True)
    if up_files:
        for uf in up_files:
            dest = os.path.join(ASSETS_PATTERNS, uf.name)
            with open(dest, "wb") as f: f.write(uf.getbuffer())
        st.success(f"Saved {len(up_files)} file(s). Click 'Rescan folder' if not visible.")
    if st.button("Rescan folder"):
        list_all_pattern_images.clear(); load_image_index.clear(); st.rerun()

    with st.form("link_form"):
        st.write("Link image(s) to a pattern")
        files = list_all_pattern_images()
        target_files = st.multiselect("Image files (multiple allowed)", files)
        pattern_names = [p.name for p in PATTERNS]
        target_pattern = st.selectbox("Pattern name", pattern_names)
        add_btn = st.form_submit_button("Add link(s)")
    if add_btn and target_files and target_pattern:
        index = dict(load_image_index()); index.setdefault(target_pattern, [])
        added = 0
        for tf in target_files:
            if tf not in index[target_pattern]: index[target_pattern].append(tf); added += 1
        if added: save_image_index(index); st.success(f"Linked {added} image(s) to '{target_pattern}'. Reloading…"); st.rerun()
        else: st.info("All selected images were already linked.")

    index = dict(load_image_index())
    if index:
        st.write("Existing links")
        for pname, paths in index.items():
            st.markdown(f"**{pname}**")
            for pth in list(paths):
                cols2 = st.columns([6,1])
                with cols2[0]: st.caption(os.path.basename(pth))
                with cols2[1]:
                    if st.button("Unlink", key=f"rm-{pname}-{pth}"):
                        paths.remove(pth); save_image_index(index); st.rerun()
    else:
        st.caption("No links yet.")

    # ---------- Pattern Manager ----------
    st.divider(); st.subheader("Pattern Manager (add/edit/delete & bulk import)")
    _patterns = list(PATTERNS)
    MOTIF_CHOICES = ["Geometric","Nature","Classic","Modern","Lucky symbol","Dynamic","Seasonal"]
    SEASON_CHOICES = ["Spring","Summer","Autumn","Winter","All year"]
    FORMALITY_CHOICES = ["Casual","Semi-formal","Formal"]
    MOOD_CHOICES = ["Bright","Calm","Elegant","Sharp","Playful","Serene","Graceful","Soft","Dynamic","Refined","Bold","Refreshing","Feminine"]
    GENDER_CHOICES = ["Male","Female","Unisex"]
    CONTRAST_CHOICES = ["Low","Medium","High"]

    names = [p.name for p in _patterns]
    selected = st.selectbox("Select a pattern to edit or create new", ["<New pattern>"] + names)
    cur = next((p for p in _patterns if p.name == selected), None) if selected != "<New pattern>" else None

    col1, col2 = st.columns([2,1])
    with col1:
        name = st.text_input("Name", value=(cur.name if cur else ""), placeholder="e.g. Seigaiha (Blue Ocean Waves)")
        motifs = st.multiselect("Motifs", options=MOTIF_CHOICES, default=(cur.motifs if cur else []))
        seasons = st.multiselect("Seasons", options=SEASON_CHOICES, default=(cur.seasons if cur else []))
        formality = st.multiselect("Formality", options=FORMALITY_CHOICES, default=(cur.formality if cur else []))
        mood = st.multiselect("Mood", options=MOOD_CHOICES, default=(cur.mood if cur else []))
        genders = st.multiselect("Genders", options=GENDER_CHOICES, default=(cur.genders if cur else []))
        contrast_pref = st.multiselect("Contrast preference", options=CONTRAST_CHOICES, default=(cur.contrast_pref if cur else []))
    with col2:
        st.caption("Color palettes (1 line = 1 palette, comma-separated hex)")
        def palettes_to_text(p): return "\n".join([", ".join(row) for row in p.color_palettes]) if p else "#0F4C81, #E6EDF7, #F2C75C"
        palettes_text = st.text_area("Palettes", value=palettes_to_text(cur), height=180)
        notes = st.text_area("Notes", value=(cur.notes if cur else ""), height=100)

    def parse_palettes(text: str):
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line: continue
            items = [x.strip() for x in line.split(',') if x.strip()]
            valid = []
            for it in items:
                if it.startswith('#') and len(it) in (4,7): valid.append(it.upper())
                elif len(it) in (3,6): valid.append('#' + it.upper())
            if valid: rows.append(valid)
        return rows

    colA, colB, colC = st.columns([1,1,1])
    with colA: save_btn = st.button("Save (Create/Update)", use_container_width=True)
    with colB: delete_btn = st.button("Delete", use_container_width=True, disabled=(cur is None))
    with colC:
        export_btn = st.download_button(
            "Export all patterns (JSON)",
            data=json.dumps([{
                "name": p.name, "motifs": p.motifs, "seasons": p.seasons, "formality": p.formality,
                "mood": p.mood, "genders": p.genders, "contrast_pref": p.contrast_pref,
                "color_palettes": p.color_palettes, "notes": p.notes,
            } for p in _patterns], ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="patterns_export.json", mime="application/json", use_container_width=True
        )

    if save_btn:
        if not name: st.error("Name is required.")
        else:
            new_palettes = parse_palettes(palettes_text)
            if not new_palettes: st.error("At least one valid color palette is required. Example: #0F4C81, #E6EDF7, #F2C75C")
            else:
                new_obj = Pattern(name=name, motifs=motifs, seasons=seasons, formality=formality,
                                  mood=mood, genders=genders, contrast_pref=contrast_pref,
                                  color_palettes=new_palettes, notes=notes)
                updated = False
                for i, p in enumerate(_patterns):
                    if p.name == name: _patterns[i] = new_obj; updated = True; break
                if not updated: _patterns.append(new_obj)
                if save_patterns_to_json(PATTERN_JSON_PATH, _patterns): st.success("Patterns saved. Reloading…"); st.rerun()

    if delete_btn and cur is not None:
        _patterns = [p for p in _patterns if p.name != cur.name]
        if save_patterns_to_json(PATTERN_JSON_PATH, _patterns): st.success("Deleted. Reloading…"); st.rerun()

    st.markdown("---"); st.markdown("### Bulk add/update (multiple at once)")
    st.caption("Paste an array of patterns in JSON, or upload a JSON file. Existing names will be updated; new ones will be created.")
    up_json = st.file_uploader("Upload JSON file (array of pattern objects)", type=["json"])
    pasted = st.text_area(
        "Or paste JSON here (array of pattern objects)",
        placeholder='[ { "name": "...", "motifs": ["Geometric"], "seasons": ["All year"], "formality": ["Casual"], "mood": ["Calm"], "genders": ["Unisex"], "contrast_pref": ["Medium"], "color_palettes": [["#0F4C81","#E6EDF7","#F2C75C"]], "notes": "..." } ]',
        height=200
    )
    colU1, colU2 = st.columns([1,1])
    with colU1: import_btn = st.button("Import / Merge JSON", use_container_width=True)
    with colU2: seed_btn = st.button("Seed sample 10 patterns", use_container_width=True)

    def merge_patterns(base: List[Pattern], incoming: List[Dict[str, Any]]) -> List[Pattern]:
        base_map = {p.name: p for p in base}
        for obj in incoming:
            try:
                name = obj["name"]
                newp = Pattern(
                    name=name, motifs=list(obj.get("motifs", [])), seasons=list(obj.get("seasons", [])),
                    formality=list(obj.get("formality", [])), mood=list(obj.get("mood", [])),
                    genders=list(obj.get("genders", [])), contrast_pref=list(obj.get("contrast_pref", [])),
                    color_palettes=[list(p) for p in obj.get("color_palettes", [])], notes=obj.get("notes", ""),
                )
                base_map[name] = newp
            except Exception as e:
                st.error(f"Skipped invalid entry: {e}")
        return list(base_map.values())

    if import_btn:
        incoming = None
        try:
            if up_json is not None: incoming = json.load(up_json)
            elif pasted.strip(): incoming = json.loads(pasted)
            else: st.warning("Provide either a JSON file or pasted JSON.")
            if isinstance(incoming, list):
                new_list = merge_patterns(_patterns, incoming)
                if save_patterns_to_json(PATTERN_JSON_PATH, new_list): st.success(f"Imported {len(incoming)} entries. Reloading…"); st.rerun()
            else: st.error("JSON must be an array of pattern objects.")
        except Exception as e:
            st.error(f"Failed to import: {e}")

    if seed_btn:
        samples = [
            {"name":"Seigaiha (Blue Ocean Waves)","motifs":["Geometric","Classic","Nature"],"seasons":["Spring","Summer","Autumn","All year"],"formality":["Casual","Semi-formal"],"mood":["Calm","Elegant","Refreshing"],"genders":["Male","Female","Unisex"],"contrast_pref":["Low","Medium"],"color_palettes":[["#0F4C81","#E6EDF7","#F2C75C"],["#2C3E50","#BDC3C7","#F39C12"]],"notes":"Waves symbolizing peace and everlasting happiness."},
            {"name":"Asanoha (Hemp Leaf)","motifs":["Geometric","Classic"],"seasons":["Spring","Summer","All year"],"formality":["Casual","Semi-formal"],"mood":["Bright","Sharp","Refreshing"],"genders":["Male","Female","Unisex"],"contrast_pref":["Medium","High"],"color_palettes":[["#EF476F","#FFD166","#06D6A0"],["#264653","#2A9D8F","#E9C46A"]],"notes":"Dynamic hemp leaf pattern symbolizing growth and protection."},
            {"name":"Shippō (Seven Treasures)","motifs":["Geometric","Classic","Lucky symbol"],"seasons":["All year"],"formality":["Semi-formal","Formal"],"mood":["Elegant","Graceful","Soft"],"genders":["Female","Unisex"],"contrast_pref":["Low","Medium"],"color_palettes":[["#8E7CC3","#F6F2FF","#D4AF37"],["#984447","#F5E6CA","#3A6EA5"]],"notes":"Circular motif symbolizing harmony and good fortune."},
            {"name":"Yagasuri (Arrow Feathers)","motifs":["Geometric","Classic"],"seasons":["All year"],"formality":["Casual","Semi-formal"],"mood":["Sharp","Strong","Calm"],"genders":["Female","Unisex"],"contrast_pref":["Medium","High"],"color_palettes":[["#800020","#FFF1E6","#1B1B1B"],["#0D3B66","#FAF0CA","#F95738"]],"notes":"Arrow feather pattern representing determination and direction."},
            {"name":"Ichimatsu (Checkerboard)","motifs":["Geometric","Modern","Classic"],"seasons":["All year"],"formality":["Casual","Semi-formal"],"mood":["Playful","Bold","Bright"],"genders":["Male","Female","Unisex"],"contrast_pref":["Medium","High"],"color_palettes":[["#2D3142","#BFC0C0","#EF8354"],["#1B998B","#EDEBED","#E71D36"]],"notes":"Checker pattern representing balance, prosperity, and modern style."},
            {"name":"Kikkō (Tortoise Shell)","motifs":["Geometric","Classic","Lucky symbol"],"seasons":["All year"],"formality":["Semi-formal","Formal"],"mood":["Elegant","Calm"],"genders":["Male","Female","Unisex"],"contrast_pref":["Low","Medium"],"color_palettes":[["#1C2331","#D1D8E0","#C0A062"],["#4C5B5C","#EAEAEA","#8AA29E"]],"notes":"Hexagonal tortoise shell pattern symbolizing longevity and stability."},
            {"name":"Karakusa (Arabesque Vines)","motifs":["Nature","Classic"],"seasons":["All year"],"formality":["Casual","Semi-formal"],"mood":["Graceful","Soft","Elegant"],"genders":["Female","Unisex"],"contrast_pref":["Low","Medium"],"color_palettes":[["#356859","#F1FAEE","#B56576"],["#355070","#E56B6F","#E0FBFC"]],"notes":"Curving vine motif symbolizing vitality and continuity."},
            {"name":"Tsurukame (Crane & Tortoise)","motifs":["Nature","Lucky symbol","Classic"],"seasons":["All year"],"formality":["Formal"],"mood":["Elegant","Traditional","Refined"],"genders":["Unisex"],"contrast_pref":["Low","Medium"],"color_palettes":[["#C0A062","#F5F3E7","#6C757D"],["#D4AF37","#E9E9E9","#5D5D5D"]],"notes":"Crane and tortoise — symbols of longevity and celebration."},
            {"name":"Sakura (Cherry Blossoms)","motifs":["Nature","Seasonal"],"seasons":["Spring"],"formality":["Casual","Semi-formal"],"mood":["Bright","Feminine","Soft"],"genders":["Female"],"contrast_pref":["Low","Medium"],"color_palettes":[["#FFC1CC","#F9E2E7","#B56576"],["#FFD7E0","#FFFFFF","#A45D7E"]],"notes":"Cherry blossoms representing beauty, transience, and renewal."},
            {"name":"Namichidori (Plovers over Waves)","motifs":["Nature","Dynamic"],"seasons":["All year"],"formality":["Casual","Semi-formal"],"mood":["Playful","Dynamic","Resilient"],"genders":["Unisex"],"contrast_pref":["Medium","High"],"color_palettes":[["#0077B6","#CAF0F8","#FFD166"],["#023E8A","#ADE8F4","#FF9F1C"]],"notes":"Waves and plovers — overcoming hardships together with vitality."}
        ]
        merged = merge_patterns(_patterns, samples)
        if save_patterns_to_json(PATTERN_JSON_PATH, merged): st.success("Seeded 10 patterns. Reloading…"); st.rerun()

# ==============================================
# DEBUG PANEL
# ==============================================
with st.sidebar:
    st.divider()
    with st.expander("Debug panel", expanded=False):
        st.write("**App dir**:", os.path.abspath(APP_DIR))
        st.write("**Running file**:", os.path.abspath(__file__))
        st.write("**patterns_en.json**:", os.path.abspath(PATTERN_JSON_PATH))
        st.write("**images.json**:", os.path.abspath(IMAGE_INDEX_JSON))
        hero_candidates = []
        for cand in ("hero_placeholder.png", "hero.jpg", "hero.png"):
            p = os.path.join(ASSETS_BG, cand)
            hero_candidates.append((cand, os.path.exists(p), p))
        st.write("**Hero candidates**:")
        for name, exists, full in hero_candidates:
            st.write(f"- {name}: {'FOUND ✅' if exists else 'not found'}  ({full})")
        try: st.write("**#Patterns loaded**:", len(PATTERNS))
        except Exception: st.write("**#Patterns loaded**: error")
        try:
            _idx = load_image_index()
            st.write("**#Linked patterns (with imgs)**:", len([k for k,v in _idx.items() if v]))
        except Exception: st.write("**#Linked patterns (with imgs)**: error")
        if st.button("Force clear cache & rerun"):
            st.cache_data.clear(); st.rerun()

# ==============================================
# FOOTER
# ==============================================
st.markdown("""
<div style='text-align:center; color:#64748b; margin:3rem 0 1rem;'>
  <small>© Wagara Recommender</small>
</div>
""", unsafe_allow_html=True)
