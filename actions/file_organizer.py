"""
Safe local file organizer helpers for common Windows folders.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


HOME = Path.home()
ALLOWED_ROOTS = {
    "downloads": HOME / "Downloads",
    "desktop": HOME / "Desktop",
    "documents": HOME / "Documents",
    "pictures": HOME / "Pictures",
    "videos": HOME / "Videos",
    "music": HOME / "Music",
}

TYPE_FOLDERS = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".heic"},
    "Videos": {".mp4", ".mov", ".mkv", ".avi", ".webm", ".wmv"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Installers": {".exe", ".msi", ".dmg", ".pkg"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yml", ".yaml"},
}


def _safe_root(folder: str) -> Path:
    key = (folder or "downloads").strip().lower()
    root = ALLOWED_ROOTS.get(key)
    if not root:
        allowed = ", ".join(sorted(ALLOWED_ROOTS))
        raise ValueError(f"Desteklenen klasorler: {allowed}")
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _category_for(path: Path) -> str:
    suffix = path.suffix.lower()
    for name, extensions in TYPE_FOLDERS.items():
        if suffix in extensions:
            return name
    return "Other"


def _unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for index in range(2, 1000):
        candidate = parent / f"{stem} ({index}){suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Benzersiz dosya adi bulunamadi: {path.name}")


def organize_files(folder: str = "downloads", mode: str = "by_type", dry_run: bool = True, limit: int = 80) -> str:
    root = _safe_root(folder)
    normalized_mode = (mode or "by_type").strip().lower()
    if normalized_mode not in {"by_type", "by_extension"}:
        return "Desteklenen duzenleme modlari: by_type, by_extension"

    files = [p for p in root.iterdir() if p.is_file() and not p.name.startswith(".")]
    if not files:
        return f"{root} icinde tasinacak dosya yok."

    planned: list[tuple[Path, Path]] = []
    for path in files[: max(1, int(limit or 80))]:
        if normalized_mode == "by_extension":
            folder_name = path.suffix.lower().lstrip(".") or "no-extension"
            folder_name = folder_name.upper()
        else:
            folder_name = _category_for(path)
        target_dir = root / folder_name
        target = _unique_destination(target_dir / path.name)
        planned.append((path, target))

    if dry_run:
        preview = [f"{src.name} -> {dst.parent.name}/" for src, dst in planned[:12]]
        extra = "" if len(planned) <= 12 else f"\n... ve {len(planned) - 12} dosya daha"
        return "Tasima onizlemesi:\n" + "\n".join(preview) + extra

    moved = 0
    for src, dst in planned:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved += 1
    return f"{root.name} icinde {moved} dosya duzenlendi."


def list_large_files(folder: str = "downloads", min_mb: float = 100, limit: int = 10) -> str:
    root = _safe_root(folder)
    threshold = max(0, float(min_mb or 0)) * 1024 * 1024
    found = []
    for path in root.rglob("*"):
        if path.is_file():
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size >= threshold:
                found.append((size, path))
    found.sort(reverse=True)
    if not found:
        return f"{root.name} icinde {min_mb:g} MB ustu dosya bulunamadi."
    lines = []
    for size, path in found[: max(1, int(limit or 10))]:
        rel = path.relative_to(root)
        lines.append(f"{size / (1024**2):.1f} MB - {rel}")
    return "\n".join(lines)


def find_files(folder: str = "downloads", query: str = "", limit: int = 20) -> str:
    root = _safe_root(folder)
    needle = (query or "").strip().lower()
    if not needle:
        return "Aranacak dosya adi belirtilmedi."
    matches = []
    for path in root.rglob("*"):
        if path.is_file() and needle in path.name.lower():
            matches.append(path)
            if len(matches) >= max(1, int(limit or 20)):
                break
    if not matches:
        return f"{root.name} icinde '{query}' bulunamadi."
    return "\n".join(str(path.relative_to(root)) for path in matches)


def clean_empty_folders(folder: str = "downloads", dry_run: bool = True) -> str:
    root = _safe_root(folder)
    empty_dirs = []
    for current, dirs, files in os.walk(root, topdown=False):
        path = Path(current)
        if path == root:
            continue
        if not dirs and not files:
            empty_dirs.append(path)
    if not empty_dirs:
        return f"{root.name} icinde bos klasor yok."
    if dry_run:
        return "Bos klasor onizlemesi:\n" + "\n".join(str(p.relative_to(root)) for p in empty_dirs[:20])
    for path in empty_dirs:
        try:
            path.rmdir()
        except OSError:
            pass
    return f"{len(empty_dirs)} bos klasor temizlendi."


def file_organizer(action: str, folder: str = "downloads", query: str = "", dry_run: bool = True, limit: int = 20, min_mb: float = 100) -> str:
    normalized = (action or "").strip().lower()
    if normalized in {"organize", "duzenle", "organize_files"}:
        return organize_files(folder=folder, dry_run=dry_run, limit=limit)
    if normalized in {"large", "large_files", "buyuk", "buyuk_dosyalar"}:
        return list_large_files(folder=folder, min_mb=min_mb, limit=limit)
    if normalized in {"find", "search", "ara"}:
        return find_files(folder=folder, query=query, limit=limit)
    if normalized in {"clean_empty", "empty_dirs", "bos_klasor"}:
        return clean_empty_folders(folder=folder, dry_run=dry_run)
    return "Dosya islemi icin action: organize | large_files | find | clean_empty"
