"""Campaigns as mods: installed into your profile, or packaged one per campaign for the official mod site.

A campaign's mod holds its .aoe2campaign, its campaign screen (`<slug>_layout.json`, our own map and pins) and
its mission intros (`<slug>.json` and the slide images). The game reads campaign screens only from mods.

Publishing (ageofempires.com/mods, signed in, or the in-game mod manager): upload the zip, which holds the mod's
files at its root (info.json, thumbnail.jpg, modes/...), not a folder. Every published campaign is titled
"[RoR-RI] <campaign>" so they're easy to find together.
"""
from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from . import campaign_maps, intros, layout
from .convert import campaign_path

PREFIX = "[RoR-RI]"
AUTHOR = "aoe2-de-ror-reimagined"
THUMBNAIL = (1280, 720)                  # the campaign screen, 16:9
PAGE_IMAGE = (1920, 1080)                # the image for the mod page, beside the zip
BUILD = layout.ROOT / "out"


def mod_title(c: layout.CampaignInfo) -> str:
    return f"{PREFIX} {c.title}"


def _demojibake(text: str) -> str:
    """UTF-8 text that was read as Windows-1252 somewhere ("Republicâ€™s") back to what it says."""
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def campaign_description(c: layout.CampaignInfo) -> str:
    import yaml
    spec = yaml.safe_load((c.root / f"{c.slug}.yaml").read_text(encoding="utf-8")) or {}
    return _demojibake(str(spec.get("description") or "")).strip()


def description(c: layout.CampaignInfo) -> str:
    """The mod's description: the original campaign's own, as AoE DE shows it."""
    return campaign_description(c)


def campaign_files(c: layout.CampaignInfo, root: Path = layout.AOE2DE_ROR) -> tuple[Path, dict]:
    """The converted campaign and its screen and intro data, as committed in aoe2de_ror/."""
    from aoe2ed import screens as ed_screens
    camp = campaign_path(c, root)
    data = {suffix: ed_screens.read_json(p) for suffix in ("_layout.json", ".json")
            if (p := camp.with_name(f"{c.slug}{suffix}")).is_file()}
    if not camp.is_file():
        raise FileNotFoundError(f"{camp} doesn't exist: run `reimagined convert {c.slug}` first")
    return camp, data


def install(c: layout.CampaignInfo, campaign: Path, data: dict, mod: str, *, profile: Path | None = None,
            description_text: str = "", warn=print) -> dict:
    """Install one campaign with its screen and intros into the local mod `mod` (under `profile`'s mods/local)."""
    from aoe2ed import screens as ed_screens

    from .screens import slide_images
    widget_files = {}
    if intros.has_art():
        build = BUILD / "intros"
        for rel, img in slide_images(c, data[".json"]).items():
            dest = build / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            img.save(dest)
            widget_files[rel] = dest
    else:
        warn("  (no AoE DE art copied: intros install without images; run `reimagined setup`)")
    own = campaign_maps.load()
    map_files = []
    if c.slug in own and intros.has_art():
        map_files = campaign_maps.files(c, own[c.slug], BUILD / "maps" / c.slug)
    return ed_screens.install_campaign_mod(campaign, mod, layout=data.get("_layout.json"), intro=data.get(".json"),
                                           files=map_files, widget_files=widget_files, game="ror",
                                           description=description_text, author=AUTHOR, profile=profile)


def campaign_view(c: layout.CampaignInfo, lay: dict):
    """The campaign screen as the game draws it, without text: the book and map with each mission's pin, cropped to
    the 3840 x 2160 the screen shows. Pins come from our drawn files (out/maps/<slug>) or RoR's own."""
    from PIL import Image
    own = campaign_maps.load()
    bg = campaign_maps.render_background(c, own[c.slug]).convert("RGBA")
    files = {m["Material"]: BUILD / "maps" / c.slug / m["FileName"] for m in lay.get("UserMaterials", [])}
    ror = campaign_maps._ror_icon_files()
    for w in (x["Widget"] for x in lay["Widgets"]):
        if w["Type"] != "Button":
            continue
        vp = w["ViewPort"]
        material = w["StateMaterials"]["StateNormal"].get("Material")
        source = files.get(material) or ror.get(material)
        x, y = vp["xorigin"] + campaign_maps.BG_OFFSET_X, vp["yorigin"]
        if source and Path(source).is_file():
            pin = Image.open(source).convert("RGBA").resize((vp["width"], vp["height"]))
            bg.alpha_composite(pin, (x, y))
    left = campaign_maps.BG_OFFSET_X
    return bg.crop((left, 0, left + 3840, 2160)).convert("RGB")


def thumbnail(c: layout.CampaignInfo, dest: Path, lay: dict | None, size: tuple[int, int] = THUMBNAIL) -> Path | None:
    """The campaign view, with its pins when the layout is given, as a JPG; None without the campaign's map art."""
    own = campaign_maps.load()
    if c.slug not in own or not intros.has_art():
        return None
    if lay:
        img = campaign_view(c, lay)
    else:
        img = campaign_maps.render_background(c, own[c.slug]).convert("RGB")
    img.resize(size).save(dest, quality=90)
    return dest


def package(c: layout.CampaignInfo, out_dir: Path, warn=print) -> dict:
    """`out_dir/<title>/` (the mod, to drop into mods/local for a test) and `out_dir/<title>.zip` (to upload)."""
    title = mod_title(c)
    campaign, data = campaign_files(c)
    out_dir.mkdir(parents=True, exist_ok=True)
    folder = out_dir / title
    if folder.exists():
        shutil.rmtree(folder)
    with tempfile.TemporaryDirectory() as tmp:
        res = install(c, campaign, data, title, profile=Path(tmp), description_text=description(c), warn=warn)
        shutil.copytree(res["mod"], folder)
    lay = data.get("_layout.json")
    thumb = thumbnail(c, folder / "thumbnail.jpg", lay)
    image = thumbnail(c, out_dir / f"{title}.jpg", lay, PAGE_IMAGE)     # for the mod page form
    page = out_dir / f"{title}.txt"
    page.write_text(f"Title:\n{title}\n\nDescription:\n{description(c)}\n", encoding="utf-8")
    zip_path = out_dir / f"{title}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(folder).as_posix())            # the mod's files at the zip's root
    size = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
    return {"title": title, "folder": folder, "zip": zip_path, "thumbnail": thumb, "image": image, "page": page,
            "mb": round(size / 2**20, 1),
            "zip_mb": round(zip_path.stat().st_size / 2**20, 1)}
