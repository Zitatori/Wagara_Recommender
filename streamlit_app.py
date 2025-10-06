# -*- coding: utf-8 -*-
"""
Wagara Recommender – single file, robust version.
- 背景画像: assets/backgrounds/ 配下の画像を自動検出（任意名OK、hero* 優先）
- Top3カード: 必ず画像を表示（links → ファイル名あいまい一致 → ギャラリーfallback）
- ギャラリー: フォルダ全走査、Pillowで読み込んで表示
- Edit mode: 画像アップ→パターン登録（複数タグ可）、リンク管理、パターン管理、シード投入
"""

from __future__ import annotations
import os, json, base64, glob, re
from dataclasses import dataclass
from typing import Any, Dict, List

import streamlit as st
from PIL import Image

# ==============================
# 基本パス（フォルダのみ作成）
# ==============================
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(APP_DIR, "assets")
ASSETS_BG = os.path.join(ASSETS_DIR, "backgrounds")     # フォルダ
ASSETS_PATTERNS = os.path.join(ASSETS_DIR, "patterns")  # フォルダ
DATA_DIR = os.path.join(APP_DIR, "data")
IMAGE_INDEX_JSON = os.path.join(DATA_DIR, "images.json")
PATTERN_JSON_PATH = os.path.join(DATA_DIR, "patterns_en.json")

for d in (ASSETS_DIR, ASSETS_BG, ASSETS_PATTERNS, DATA_DIR):
    os.makedirs(d, exist_ok=True)
if not os.path.exists(PATTERN_JSON_PATH):
    with open(PATTERN_JSON_PATH, "w", encoding="utf-8") as f: f.write("[]")
if not os.path.exists(IMAGE_INDEX_JSON):
    with open(IMAGE_INDEX_JSON, "w", encoding="utf-8") as f: f.write("{}")

# ==============================
# ページ設定
# ==============================
st.set_page_config(page_title="Wagara Recommender", page_icon="🎴", layout="wide", initial_sidebar_state="expanded")

# ==============================
# ユーティリティ
# ==============================
def b64_of(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None

def read_bytes(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None

def all_images_in(folder: str) -> List[str]:
    if not os.path.isdir(folder): return []
    exts = ("png","jpg","jpeg","webp","PNG","JPG","JPEG","WEBP")
    files: List[str] = []
    for e in exts:
        files.extend(glob.glob(os.path.join(folder, f"*.{e}")))
    files = [p for p in files if os.path.isfile(p)]
    files.sort(key=lambda p: (os.path.getmtime(p), os.path.basename(p)), reverse=True)
    return files

def find_hero_image(folder: str) -> tuple[str | None, str | None]:
    """assets/backgrounds/ 内の画像を拾う。hero* を優先。"""
    files = all_images_in(folder)
    if not files: return None, None
    heroish = [p for p in files if os.path.basename(p).lower().startswith("hero")]
    pick = (heroish or files)[0]
    ext = os.path.splitext(pick)[1].lower()
    mime = "image/png" if ext == ".png" else ("image/webp" if ext == ".webp" else "image/jpeg")
    return pick, mime

def norm(s: str) -> str:
    return re.sub(r"[^\w]+", "", s.lower())

# ==============================
# CSS / ヒーロー
# ==============================
FONTS_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;600;700&family=Zen+Maru+Gothic:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{--card-radius:1.25rem;}
html,body,[class^="css"]{font-family:"Zen Maru Gothic","Noto Serif JP",system-ui,-apple-system,Segoe UI,Roboto,sans-serif;}
section.main > div {padding-top:0 !important}
.hero{position:relative;width:100%;min-height:46vh;display:flex;align-items:center;justify-content:center;overflow:hidden;
      background-size:cover;background-position:center center;}
.hero::after{content:"";position:absolute;inset:0;
  background:radial-gradient(ellipse at 20% 10%, rgba(255,255,255,.12), transparent 40%),
             radial-gradient(ellipse at 80% 90%, rgba(255,255,255,.08), transparent 40%);}
.hero-inner{position:relative;padding:2rem 2.4rem;text-align:center;backdrop-filter: blur(6px);
  background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,.18);border-radius:1.5rem;}
.hero-title{font-size:clamp(2rem,4vw,3.2rem);font-weight:800;color:#fff;letter-spacing:0.04em;}
.hero-sub{margin-top:.5rem;color:#e5e7eb;font-size:clamp(.95rem,1.6vw,1.1rem)}
.rec-card{background:#fff;border-radius:var(--card-radius);padding:1rem 1.1rem;box-shadow:0 10px 24px rgba(0,0,0,.06);border:1px solid #eef2f7}
.rec-title{font-size:1.25rem;font-weight:800;margin-bottom:.35rem}
.rec-badge{display:inline-block;border:1px solid #e5e7eb;padding:.15rem .5rem;border-radius:999px;margin-right:.3rem;font-size:.8rem;color:#334155;background:#f8fafc}
.colors{display:flex;gap:.5rem;flex-wrap:wrap;}
.color-chip{display:flex;align-items:center;gap:.5rem;border-radius:.75rem;border:1px solid #e5e7eb;padding:.5rem .7rem;}
.color-swatch{width:20px;height:20px;border-radius:6px;border:1px solid rgba(0,0,0,.1)}
.small-muted{color:#64748b;font-size:.85rem}
[data-testid="stSidebar"]{border-right:1px solid #e5e7eb}
</style>
"""

st.markdown(FONTS_CSS, unsafe_allow_html=True)

hero_path, hero_mime = find_hero_image(ASSETS_BG)
hero_b64 = b64_of(hero_path) if hero_path else None
bg_style = f"background-image:url('data:{hero_mime};base64,{hero_b64}')" if hero_b64 else \
           "background-image:linear-gradient(120deg,#0f172a 0%,#111827 100%)"

st.markdown(
    f'<div class="hero" style="{bg_style}"><div class="hero-inner">'
    '<div class="hero-title">🎴 Wagara Recommender</div>'
    '<div class="hero-sub">Find kimono patterns and color palettes that match your mood, season, and style.</div>'
    '</div></div>',
    unsafe_allow_html=True
)
st.markdown("\n")

# ==============================
# データモデル
# ==============================
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
def load_patterns(path: str) -> List[Pattern]:
    try:
        data = json.load(open(path, "r", encoding="utf-8"))
    except Exception:
        data = []
    out: List[Pattern] = []
    for o in data:
        out.append(Pattern(
            name=o.get("name",""),
            motifs=list(o.get("motifs",[])),
            seasons=list(o.get("seasons",[])),
            formality=list(o.get("formality",[])),
            mood=list(o.get("mood",[])),
            genders=list(o.get("genders",[])),
            contrast_pref=list(o.get("contrast_pref",[])),
            color_palettes=[list(p) for p in o.get("color_palettes",[])],
            notes=o.get("notes",""),
        ))
    return out

def save_patterns(path: str, items: List[Pattern]) -> bool:
    try:
        payload=[{
            "name":p.name,"motifs":p.motifs,"seasons":p.seasons,"formality":p.formality,
            "mood":p.mood,"genders":p.genders,"contrast_pref":p.contrast_pref,
            "color_palettes":p.color_palettes,"notes":p.notes
        } for p in items]
        json.dump(payload, open(path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        load_patterns.clear()
        return True
    except Exception as e:
        st.error(f"Failed to save patterns: {e}")
        return False

PATTERNS: List[Pattern] = load_patterns(PATTERN_JSON_PATH)

# ==============================
# 画像リンク（images.json）
# ==============================
@st.cache_data(show_spinner=False)
def load_links() -> Dict[str, List[str]]:
    try:
        data = json.load(open(IMAGE_INDEX_JSON,"r",encoding="utf-8"))
        fixed={}
        for k,v in data.items():
            fixed[k]=[p if os.path.isabs(p) else os.path.join(ASSETS_PATTERNS, os.path.basename(p)) for p in v]
        return fixed
    except Exception:
        return {}

def save_links(d: Dict[str, List[str]]):
    json.dump(d, open(IMAGE_INDEX_JSON,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    load_links.clear()
    st.toast("Saved image links.", icon="✅")

# ==============================
# 推薦ロジック（シンプル）
# ==============================
WEIGHTS = {"gender":1.0,"mood":1.1,"season":0.9,"formality":1.0,"motif":0.8,"contrast":0.6}

def score(p: Pattern, pref: Dict[str, Any]) -> float:
    s=0.0
    if (g:=pref.get("gender")) and (g in p.genders or "Unisex" in p.genders): s+=WEIGHTS["gender"]
    if (m:=pref.get("mood")) and (m in p.mood): s+=WEIGHTS["mood"]
    if (ss:=pref.get("season")) and (ss in p.seasons or "All year" in p.seasons): s+=WEIGHTS["season"]
    if (t:=pref.get("tpo")) and (t in p.formality): s+=WEIGHTS["formality"]
    if (mo:=pref.get("motif")) and (mo in p.motifs): s+=WEIGHTS["motif"]
    if (c:=pref.get("contrast")) and (c in p.contrast_pref): s+=WEIGHTS["contrast"]
    return s

def recommend(pref: Dict[str, Any], k:int=3):
    ranked = sorted(((score(p,pref),p) for p in PATTERNS), key=lambda x:x[0], reverse=True)
    return [p for _,p in ranked[:k]]

# ==============================
# サイドバー
# ==============================
with st.sidebar:
    st.header("Select your preferences")
    gender = st.radio("Gender (for style reference only)", ["Male","Female","Unisex"], index=2)
    mood = st.selectbox("Mood", ["Bright","Calm","Elegant","Sharp","Playful","Serene"], index=1)
    season = st.selectbox("Season", ["Spring","Summer","Autumn","Winter","All year"], index=4)
    tpo = st.selectbox("Formality", ["Casual","Semi-formal","Formal"], index=1)
    motif = st.selectbox("Motif type", ["Geometric","Nature","Classic","Modern","Lucky symbol"], index=0)
    contrast = st.radio("Contrast level", ["Low","Medium","High"], index=1, horizontal=True)
    show_colors = st.toggle("Show color palette", value=False)
    st.divider()
    edit_mode = st.toggle("Edit mode (upload/link images, manage patterns)", value=False)

# ==============================
# Top 3 （必ず画像を出す）
# ==============================
prefs={"gender":gender,"mood":mood,"season":season,"tpo":tpo,"motif":motif,"contrast":contrast}
top = recommend(prefs, k=3)
st.subheader("Top 3 matches")
cols = st.columns(3 if top else 1)

links = load_links()
gallery = all_images_in(ASSETS_PATTERNS)

def guess_images(pname: str, limit:int=3) -> List[str]:
    linked = links.get(pname, [])
    if linked: return linked[:limit]
    tokens = [t for t in re.split(r"[\s\(\)\-_/]+", pname) if t]
    scored=[]
    for path in gallery:
        base = norm(os.path.basename(path))
        hits = sum(1 for t in tokens if norm(t) in base)
        if hits>0: scored.append((hits, path))
    if scored:
        scored.sort(key=lambda x:(-x[0], os.path.basename(x[1])))
        return [p for _,p in scored[:limit]]
    return gallery[:limit]

if top:
    for i, (c, pat) in enumerate(zip(cols, top), start=1):
        with c:
            st.markdown('<div class="rec-card">', unsafe_allow_html=True)
            st.markdown(f"<div class='rec-title'>[{i}] {pat.name}</div>", unsafe_allow_html=True)
            st.markdown(" ".join([f"<span class='rec-badge'>{m}</span>" for m in pat.motifs]), unsafe_allow_html=True)

            st.markdown("**Why it fits**")
            bullets=[]
            if mood in pat.mood: bullets.append(f"Matches mood '{mood}'")
            if season in pat.seasons or "All year" in pat.seasons: bullets.append(f"Works for '{season}'")
            if tpo in pat.formality: bullets.append(f"Appropriate for '{tpo}'")
            if motif in pat.motifs: bullets.append(f"Motif '{motif}' included")
            if contrast in pat.contrast_pref: bullets.append(f"Good for contrast '{contrast}'")
            if not bullets: bullets.append("Versatile and easy to coordinate")
            for b in bullets: st.write("•", b)

            if show_colors and pat.color_palettes:
                st.markdown("**Suggested colors**")
                pal = pat.color_palettes[0]
                html = "<div class='colors'>" + "".join(
                    [f"<div class='color-chip'><span class='color-swatch' style='background:{hx}'></span>"
                     f"<span>{i+1}</span><code style='margin-left:.25rem'>{hx}</code></div>" for i,hx in enumerate(pal)]
                ) + "</div>"
                st.markdown(html, unsafe_allow_html=True)

            cand = guess_images(pat.name, 3)
            if cand:
                st.markdown("**Preview**")
                ic = st.columns(len(cand))
                for j, pth in enumerate(cand):
                    with ic[j]:
                        data = read_bytes(pth)
                        if data: st.image(data, use_column_width=True)
                        else: st.info("Failed to load image.")
                # リンクしてない推測結果を登録
                new_to_add = [p for p in cand if p not in links.get(pat.name, [])]
                if new_to_add and st.button("Link guessed images", key=f"link-{i}"):
                    links.setdefault(pat.name, []).extend(new_to_add)
                    save_links(links)
                    st.rerun()
            else:
                st.caption("No images found yet.")
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("No patterns yet. Use Edit mode to add.")

st.divider()

# ==============================
# ギャラリー
# ==============================
st.subheader("Image Gallery")
if not gallery:
    st.warning(f"No images found in: {ASSETS_PATTERNS}")
    st.caption("Put images in assets/patterns or add via Edit mode → ✚ Simple Add.")
else:
    n = 4
    rows = (len(gallery)+n-1)//n
    idx=0
    for _ in range(rows):
        r = st.columns(n)
        for col in r:
            if idx>=len(gallery): break
            data = read_bytes(gallery[idx]); fname = os.path.basename(gallery[idx]); idx+=1
            with col:
                if data: st.image(data, use_column_width=True, caption=fname)
                else: st.error(f"Failed to display {fname}")

# ==============================
# Edit mode
# ==============================
if edit_mode:
    st.divider()
    st.subheader("✚ Simple Add (image → pattern)")
    col1, col2 = st.columns([2,1])

    MOTIF_CHOICES=["Geometric","Nature","Classic","Modern","Lucky symbol","Dynamic","Seasonal"]
    SEASON_CHOICES=["Spring","Summer","Autumn","Winter","All year"]
    FORM_CHOICES=["Casual","Semi-formal","Formal"]
    MOOD_CHOICES=["Bright","Calm","Elegant","Sharp","Playful","Serene","Graceful","Soft","Dynamic","Refined","Bold","Refreshing","Feminine"]
    GENDER_CHOICES=["Male","Female","Unisex"]
    CONTRAST_CHOICES=["Low","Medium","High"]

    with col1:
        up = st.file_uploader("Wagara image", type=["png","jpg","jpeg","webp"])
        name = st.text_input("Pattern name", placeholder="e.g. Seigaiha (Blue Ocean Waves)")
        motifs = st.multiselect("Motifs (optional)", MOTIF_CHOICES)
        seasons = st.multiselect("Seasons (optional)", SEASON_CHOICES, default=["All year"])
        formality = st.multiselect("Formality (optional)", FORM_CHOICES)
        mood_ms = st.multiselect("Mood (optional)", MOOD_CHOICES)
        genders = st.multiselect("Genders (optional)", GENDER_CHOICES, default=["Unisex"])
        contrast_ms = st.multiselect("Contrast preference (optional)", CONTRAST_CHOICES)

    with col2:
        def extract_palette(path: str, n:int=3) -> List[str]:
            try:
                img=Image.open(path).convert("RGB"); img.thumbnail((150,150))
                colors=img.getcolors(maxcolors=22500)
                colors.sort(reverse=True, key=lambda x:x[0])
                hexes=[]
                for _, rgb in colors[: n*4]:
                    hx='#%02X%02X%02X'%rgb
                    if hx not in hexes: hexes.append(hx)
                    if len(hexes)>=n: break
                while len(hexes)<n: hexes.append("#CCCCCC")
                return hexes
            except Exception:
                return ["#333333","#DDDDDD","#999999"]

        go = st.button("➕ Add this pattern from image", use_container_width=True)
        wipe_patterns = st.button("🗑️ Delete ALL patterns", use_container_width=True)

    if wipe_patterns:
        with open(PATTERN_JSON_PATH,"w",encoding="utf-8") as f: f.write("[]")
        load_patterns.clear()
        st.success("All patterns removed.")
        st.rerun()

    if go:
        if not up or not name.strip():
            st.error("Need both an image and a pattern name.")
        else:
            dest = os.path.join(ASSETS_PATTERNS, up.name)
            with open(dest,"wb") as f: f.write(up.getbuffer())
            pal = extract_palette(dest, 3)
            pats = list(PATTERNS)
            new = Pattern(name=name.strip(), motifs=motifs, seasons=seasons, formality=formality,
                          mood=mood_ms, genders=genders if genders else ["Unisex"],
                          contrast_pref=contrast_ms if contrast_ms else ["Medium"],
                          color_palettes=[pal], notes="")
            replaced=False
            for i,p in enumerate(pats):
                if p.name==new.name: pats[i]=new; replaced=True; break
            if not replaced: pats.append(new)
            ok = save_patterns(PATTERN_JSON_PATH, pats)
            lk = load_links(); lk.setdefault(new.name, [])
            if dest not in lk[new.name]: lk[new.name].append(dest); save_links(lk)
            if ok: st.success("Added/updated. Reloading…"); st.rerun()

    st.divider()
    st.subheader("Upload / Link images (manual)")
    ups = st.file_uploader("Add images (multiple)", type=["png","jpg","jpeg","webp"], accept_multiple_files=True)
    if ups:
        for f in ups:
            with open(os.path.join(ASSETS_PATTERNS, f.name),"wb") as w: w.write(f.getbuffer())
        st.success(f"Saved {len(ups)} file(s).")
    if st.button("Rescan"):
        st.cache_data.clear(); st.rerun()

    with st.form("link_form"):
        files = all_images_in(ASSETS_PATTERNS)
        tgt_files = st.multiselect("Images", files)
        names = [p.name for p in PATTERNS]
        tgt_name = st.selectbox("Pattern", names)
        ok = st.form_submit_button("Link")
    if ok and tgt_files and tgt_name:
        lk = load_links(); lk.setdefault(tgt_name, [])
        add=0
        for f in tgt_files:
            if f not in lk[tgt_name]: lk[tgt_name].append(f); add+=1
        if add: save_links(lk); st.success(f"Linked {add} image(s)."); st.rerun()
        else: st.info("Nothing to add.")

    # 既存リンク表示
    lk = load_links()
    if lk:
        st.write("Existing links")
        for pname, paths in lk.items():
            st.markdown(f"**{pname}**")
            for pth in list(paths):
                c1,c2 = st.columns([6,1])
                with c1: st.caption(os.path.basename(pth))
                with c2:
                    if st.button("Unlink", key=f"unlink-{pname}-{pth}"):
                        paths.remove(pth); save_links(lk); st.rerun()
    else:
        st.caption("No links yet.")

    # パターン管理（最小）
    st.divider()
    st.subheader("Pattern Manager")
    pats = list(PATTERNS)
    names = [p.name for p in pats]
    sel = st.selectbox("Select or create", ["<New>"]+names)
    cur = next((p for p in pats if p.name==sel), None) if sel!="<New>" else None

    a,b = st.columns([2,1])
    with a:
        nm = st.text_input("Name", value=(cur.name if cur else ""))
        mt = st.text_input("Motifs (comma)", value=", ".join(cur.motifs) if cur else "")
        ss = st.text_input("Seasons (comma)", value=", ".join(cur.seasons) if cur else "")
        fm = st.text_input("Formality (comma)", value=", ".join(cur.formality) if cur else "")
        md = st.text_input("Mood (comma)", value=", ".join(cur.mood) if cur else "")
        gd = st.text_input("Genders (comma)", value=", ".join(cur.genders) if cur else "")
        ct = st.text_input("Contrast (comma)", value=", ".join(cur.contrast_pref) if cur else "")
    with b:
        pal_text = st.text_area("Palettes (one line = comma hex)", value=("\n".join([", ".join(x) for x in (cur.color_palettes if cur else [["#0F4C81","#E6EDF7","#F2C75C"]])])))
        notes = st.text_area("Notes", value=(cur.notes if cur else ""))

    def parse_palettes(text:str) -> List[List[str]]:
        rows=[]
        for line in text.splitlines():
            line=line.strip()
            if not line: continue
            items=[x.strip().upper() for x in line.split(",") if x.strip()]
            fixed=[]
            for it in items:
                if it.startswith("#") and len(it) in (4,7): fixed.append(it)
                elif len(it) in (3,6): fixed.append("#"+it)
            if fixed: rows.append(fixed)
        return rows

    csa, csb, csc = st.columns(3)
    with csa: save_btn = st.button("Save/Update", use_container_width=True)
    with csb: del_btn = st.button("Delete", use_container_width=True, disabled=(cur is None))
    with csc:
        st.download_button("Export JSON",
            data=json.dumps([{
                "name":p.name,"motifs":p.motifs,"seasons":p.seasons,"formality":p.formality,
                "mood":p.mood,"genders":p.genders,"contrast_pref":p.contrast_pref,"color_palettes":p.color_palettes,"notes":p.notes
            } for p in pats], ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="patterns_export.json", mime="application/json", use_container_width=True)

    if save_btn:
        if not nm.strip(): st.error("Name required.")
        else:
            new = Pattern(
                name=nm.strip(),
                motifs=[x.strip() for x in mt.split(",") if x.strip()],
                seasons=[x.strip() for x in ss.split(",") if x.strip()],
                formality=[x.strip() for x in fm.split(",") if x.strip()],
                mood=[x.strip() for x in md.split(",") if x.strip()],
                genders=[x.strip() for x in gd.split(",") if x.strip()],
                contrast_pref=[x.strip() for x in ct.split(",") if x.strip()],
                color_palettes=parse_palettes(pal_text),
                notes=notes
            )
            rep=False
            for i,p in enumerate(pats):
                if p.name==new.name: pats[i]=new; rep=True; break
            if not rep: pats.append(new)
            if save_patterns(PATTERN_JSON_PATH, pats): st.success("Saved."); st.rerun()

    if del_btn and cur is not None:
        pats=[p for p in pats if p.name!=cur.name]
        if save_patterns(PATTERN_JSON_PATH, pats): st.success("Deleted."); st.rerun()

# ==============================
# Debug（最小）
# ==============================
with st.sidebar:
    st.divider()
    with st.expander("Debug", expanded=False):
        st.write("APP_DIR:", APP_DIR)
        st.write("ASSETS_BG (dir):", ASSETS_BG, " | isdir:", os.path.isdir(ASSETS_BG))
        st.write("Hero picked:", hero_path or "(none)")
        st.write("patterns_en.json:", PATTERN_JSON_PATH)
        st.write("images.json:", IMAGE_INDEX_JSON)
        if st.button("Force clear cache & rerun"):
            st.cache_data.clear(); st.rerun()
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
