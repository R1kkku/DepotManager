import asyncio
import hashlib
import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from .config import APP_DIR, KEYS_FILE

logger = logging.getLogger("DepotManager.Downloader")

class DownloadManager:
    """Manages downloading selected Steam depots using DepotDownloaderMod.exe."""
    def __init__(
        self,
        settings: dict,
        inventory: dict,
        current_temp_dir: Optional[Path],
        log_callback: Callable[[str], None]
    ) -> None:
        self.settings = settings
        self.inventory = inventory
        self.current_temp_dir = current_temp_dir
        self.log_callback = log_callback

    def _write_keys_file(self, keys_dict: Dict[str, str]) -> None:
        """Writes the decryption keys file for the downloader."""
        try:
            with open(KEYS_FILE, "w", encoding="utf-8") as f:
                for did, key in keys_dict.items():
                    f.write(f"{did};{key}\n")
            logger.debug("Keys file written: %d keys.", len(keys_dict))
        except OSError as exc:
            logger.error("Cannot write keys file: %s", exc)
            raise exc

    async def run_downloads(
        self,
        selected_ids: List[str],
        exe_path: Path,
        app_id: str,
        output_dir: Optional[Path] = None,
        validate_dir: Optional[Path] = None,
    ) -> None:
        """Orchestrates downloads of all selected depots with controlled concurrency.

        output_dir   : destination folder for downloads (-dir).
        validate_dir : when set, used as -dir with -validate so only missing/changed
                       files are fetched (skips files already present and correct).
        """
        # Pre-populate keys
        keys_to_write = {
            str(did): self.inventory[str(did)]["key"]
            for did in selected_ids
            if self.inventory.get(str(did)) and self.inventory[str(did)]["key"]
        }
        await asyncio.to_thread(self._write_keys_file, keys_to_write)

        max_concurrent = self.settings.get("max_concurrent_downloads", 1)
        sem = asyncio.Semaphore(max_concurrent)

        tasks = [
            asyncio.create_task(
                self._download_single(
                    did, exe_path, app_id, sem,
                    output_dir=output_dir,
                    validate_dir=validate_dir,
                )
            )
            for did in selected_ids
        ]

        try:
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                cancelled = any(isinstance(r, asyncio.CancelledError) for r in results)
                errors = [r for r in results if isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError)]

                if cancelled:
                    self.log_callback("--- 🛑 OPERATION CANCELLED BY USER ---")
                    raise asyncio.CancelledError()
                elif errors:
                    self.log_callback(f"--- ⚠️ COMPLETED WITH {len(errors)} ERRORS ---")
                    raise RuntimeError(f"{len(errors)} depots encountered errors during download.")
                else:
                    self.log_callback("--- ✅ ALL SELECTED DOWNLOADS COMPLETED ---")

            except asyncio.CancelledError:
                # Handle cancellation of the orchestrating task
                for t in tasks:
                    t.cancel()
                self.log_callback("--- 🛑 DOWNLOAD OPERATION CANCELLED ---")
                raise
        finally:
            keys_path = Path(KEYS_FILE)
            if keys_path.exists():
                try:
                    await asyncio.to_thread(keys_path.unlink)
                    logger.debug("Keys file removed immediately after download: %s", KEYS_FILE)
                except OSError as exc:
                    logger.warning("Cannot remove keys file %s immediately: %s", KEYS_FILE, exc)

    async def run_update_downloads(
        self,
        selected_ids: List[str],
        exe_path: Path,
        app_id: str,
        game_dir: Path,
        output_dir: Path,
        custom_filelists: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """
        Three-phase update flow:
          Phase 1 — Snapshot: hash every file in game_dir before downloading (skipped if custom file list is loaded).
          Phase 2 — Download: run DepotDownloaderMod with -dir game_dir -validate
                    (only changed chunks/files are fetched; files are updated in-place).
          Phase 3 — Diff & Copy: compare current game_dir against the snapshot, or use the SteamDB file list,
                    copy every file that changed or is new into output_dir.
        """
        steamdb_lists = custom_filelists if custom_filelists is not None else {}

        keys_to_write = {
            str(did): self.inventory[str(did)]["key"]
            for did in selected_ids
            if self.inventory.get(str(did)) and self.inventory[str(did)]["key"]
        }
        await asyncio.to_thread(self._write_keys_file, keys_to_write)

        temp_filelists = {}
        has_filelists = all(str(did) in steamdb_lists for did in selected_ids)

        snapshot = {}
        if not has_filelists:
            # ── Phase 1: snapshot ──────────────────────────────────────────────
            self.log_callback("[*] Phase 1/3 — Scanning game folder before download...")
            snapshot = await asyncio.to_thread(self._snapshot_dir, game_dir)
            self.log_callback(f"[+] Snapshot done: {len(snapshot)} files indexed.")
        else:
            self.log_callback("[*] SteamDB file lists found. Skipping directory snapshot!")
            for did in selected_ids:
                flist = steamdb_lists[str(did)]
                import tempfile
                temp_file = Path(tempfile.mktemp(prefix=f"filelist_{did}_", suffix=".txt", dir=str(APP_DIR)))
                with open(temp_file, "w", encoding="utf-8") as f:
                    for filename in flist:
                        f.write(f"{filename}\n")
                temp_filelists[str(did)] = temp_file
                self.log_callback(f"[+] Created file list for Depot {did} containing {len(flist)} files.")

        # ── Phase 2: download ──────────────────────────────────────────────
        self.log_callback("[*] Phase 2/3 — Downloading updates to game folder...")
        max_concurrent = self.settings.get("max_concurrent_downloads", 1)
        sem = asyncio.Semaphore(max_concurrent)

        tasks = []
        for did in selected_ids:
            flist_path = temp_filelists.get(str(did))
            tasks.append(
                asyncio.create_task(
                    self._download_single(
                        did, exe_path, app_id, sem,
                        output_dir=game_dir,
                        validate=True,
                        file_list_path=flist_path,
                    )
                )
            )

        try:
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                cancelled = any(isinstance(r, asyncio.CancelledError) for r in results)
                errors = [
                    r for r in results
                    if isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError)
                ]

                if cancelled:
                    self.log_callback("--- 🛑 UPDATE DOWNLOAD CANCELLED ---")
                    raise asyncio.CancelledError()
                elif errors:
                    self.log_callback(f"--- ⚠️ COMPLETED WITH {len(errors)} ERRORS ---")
                    raise RuntimeError(f"{len(errors)} depots encountered errors during download.")

                # ── Phase 3: diff & copy ───────────────────────────────────
                if has_filelists:
                    self.log_callback("[*] Phase 3/3 — Copying update files to output...")
                    copied = 0
                    missing = 0
                    for did in selected_ids:
                        flist = steamdb_lists[str(did)]
                        for relative_name in flist:
                            game_file = game_dir / relative_name
                            dest = output_dir / relative_name
                            if game_file.is_file():
                                try:
                                    dest.parent.mkdir(parents=True, exist_ok=True)
                                    shutil.copy2(str(game_file), str(dest))
                                    copied += 1
                                    logger.debug("Copied update file: %s", relative_name)
                                except OSError as exc:
                                    logger.warning("Cannot copy %s to output: %s", relative_name, exc)
                                    self.log_callback(f"    [❌] Failed: {relative_name} ({exc})")
                            else:
                                missing += 1
                                logger.warning("Expected update file not found: %s", relative_name)
                                self.log_callback(f"    [⚠️] Missing (not downloaded): {relative_name}")
                    self.log_callback(f"[+] Finished: Copied {copied} files to output directory.")
                else:
                    self.log_callback("[*] Phase 3/3 — Detecting changed files and copying to output...")
                    copied, unchanged = await asyncio.to_thread(
                        self._copy_changed_files, game_dir, snapshot, output_dir
                    )
                    self.log_callback(
                        f"[+] Changed/new files copied to output: {copied}  |  Unchanged skipped: {unchanged}"
                    )
                self.log_callback("--- ✅ UPDATE COMPLETE ---")

            except asyncio.CancelledError:
                for t in tasks:
                    t.cancel()
                self.log_callback("--- 🛑 UPDATE DOWNLOAD CANCELLED ---")
                raise
        finally:
            for flist_path in temp_filelists.values():
                if flist_path.exists():
                    try:
                        flist_path.unlink()
                        logger.debug("Deleted temporary file list: %s", flist_path)
                    except OSError as exc:
                        logger.warning("Cannot delete temporary file list %s: %s", flist_path, exc)

            keys_path = Path(KEYS_FILE)
            if keys_path.exists():
                try:
                    await asyncio.to_thread(keys_path.unlink)
                    logger.debug("Keys file removed after update download.")
                except OSError as exc:
                    logger.warning("Cannot remove keys file: %s", exc)

    def _snapshot_dir(self, directory: Path) -> Dict[Path, str]:
        """Hashes every file in directory. Logs a count every 500 files."""
        def md5(path: Path) -> str:
            h = hashlib.md5()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()

        snapshot: Dict[Path, str] = {}
        count = 0
        for file in sorted(directory.rglob("*")):
            if file.is_file():
                relative = file.relative_to(directory)
                try:
                    snapshot[relative] = md5(file)
                except OSError as exc:
                    logger.warning("Cannot hash %s for snapshot: %s", relative, exc)
                count += 1
                if count % 500 == 0:
                    self.log_callback(f"    ↳ Scanning... ({count:,} files indexed)")
        return snapshot

    def _copy_changed_files(
        self,
        game_dir: Path,
        snapshot: Dict[Path, str],
        output_dir: Path,
    ) -> Tuple[int, int]:
        """
        Walks game_dir, compares each file against the pre-download snapshot.
        Changed/new files are copied to output_dir.
        Emits per-file progress for copies and overall % at every 10% step.
        Returns (copied_count, unchanged_count).
        """
        def md5(path: Path) -> str:
            h = hashlib.md5()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()

        all_files = [f for f in game_dir.rglob("*") if f.is_file()]
        total = len(all_files)

        copied = 0
        unchanged = 0
        last_pct_step = -1

        for i, game_file in enumerate(all_files, 1):
            relative = game_file.relative_to(game_dir)
            old_hash = snapshot.get(relative)
            pct = int(i / total * 100) if total > 0 else 100
            pct_step = pct // 10

            is_changed = True
            if old_hash is not None:
                try:
                    if md5(game_file) == old_hash:
                        unchanged += 1
                        is_changed = False
                except OSError as exc:
                    logger.warning("Cannot hash %s for comparison: %s", relative, exc)

            if is_changed:
                dest = output_dir / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(str(game_file), str(dest))
                    logger.debug("Copied changed: %s", relative)
                    copied += 1
                    self.log_callback(f"    [{pct:3d}%] ✅ Copied: {relative}")
                except OSError as exc:
                    logger.warning("Cannot copy %s to output: %s", relative, exc)
                    self.log_callback(f"    [{pct:3d}%] ❌ Failed: {relative}  ({exc})")
            elif pct_step != last_pct_step:
                # Log overall progress at each 10% step for unchanged files
                self.log_callback(
                    f"    [{pct:3d}%] Comparing... ({i:,}/{total:,} files — {copied} changed so far)"
                )

            if pct_step != last_pct_step:
                last_pct_step = pct_step

        return copied, unchanged

    async def _download_single(
        self,
        did: str,
        exe_path: Path,
        app_id: str,
        sem: asyncio.Semaphore,
        output_dir: Optional[Path] = None,
        validate: bool = False,
        validate_dir: Optional[Path] = None,
        file_list_path: Optional[Path] = None,
    ) -> None:
        """Downloads a single depot using DepotDownloaderMod.exe in a subprocess.

        output_dir   : if provided, adds -dir so files go to that folder.
        validate_dir : when set, used as -dir instead (existing install) with -validate
                       so only missing/changed files are fetched.
        validate     : bare -validate flag (used by the update flow).
        """
        info = self.inventory.get(str(did))
        if not info or not info["manifest_file"]:
            logger.warning("Depot %s: no manifest file, skipping.", did)
            self.log_callback(f"⚠️ Depot {did}: Missing manifest file, skipping.")
            return

        manifest_src: Path = info["manifest_file"]

        if self.current_temp_dir is None:
            raise RuntimeError("No temporary directory is set.")

        if not manifest_src.is_absolute():
            manifest_src = self.current_temp_dir / manifest_src.name

        match = re.search(r"_(\d+)\.manifest$", manifest_src.name)
        if not match:
            logger.warning("Depot %s: unparsable manifest name (%s), skipping.", did, manifest_src.name)
            self.log_callback(f"⚠️ Depot {did}: Unparsable manifest name, skipping.")
            return

        manifest_id = match.group(1)
        local_manifest = APP_DIR / manifest_src.name

        # Copy manifest to local APP_DIR so DepotDownloaderMod can access it
        try:
            await asyncio.to_thread(shutil.copy, str(manifest_src), str(local_manifest))
        except OSError as exc:
            logger.error("Cannot copy manifest for depot %s: %s", did, exc)
            self.log_callback(f"❌ Error copying manifest Depot {did}: {exc}")
            return

        async with sem:
            # Determine effective download destination
            if validate_dir is not None:
                # Use existing install as -dir with -validate: only fetches missing/changed files
                effective_dir = validate_dir
                dest_label = f"{validate_dir.name} (validate — updates only)"
            else:
                effective_dir = output_dir
                dest_label = output_dir.name if output_dir else "default"

            self.log_callback(f"\n>>> Starting download Depot {did} → {dest_label}...")
            cmd = [
                str(exe_path),
                "-app", app_id,
                "-depot", str(did),
                "-manifest", manifest_id,
                "-manifestfile", local_manifest.name,
                "-depotkeys", KEYS_FILE,
                "-max-downloads", "16",
            ]
            if effective_dir is not None:
                cmd += ["-dir", str(effective_dir)]
            if file_list_path is not None:
                cmd += ["-filelist", str(file_list_path)]
            # Add -validate when validate_dir is set OR the plain validate flag is on
            if validate_dir is not None or validate:
                cmd += ["-validate"]
            logger.debug("Command: %s", " ".join(cmd))

            process: Optional[asyncio.subprocess.Process] = None
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(APP_DIR),
                )

                if process.stdout is None:
                    self.log_callback(f"❌ No output from process for Depot {did}")
                    logger.error("Depot %s: stdout not available.", did)
                    return

                while True:
                    line = await process.stdout.readline()
                    if not line:
                        break
                    self.log_callback(line.decode(errors="replace").strip())

                await process.wait()
                logger.info("Depot %s: process exited with code %s.", did, process.returncode)
                if process.returncode != 0:
                    raise RuntimeError(f"Process exited with non-zero code {process.returncode}")

            except asyncio.CancelledError:
                if process and process.returncode is None:
                    try:
                        process.terminate()
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        process.kill()
                        logger.warning("Depot %s: process forcefully killed.", did)
                self.log_callback(f"🛑 Stopped Depot {did}")
                logger.info("Depot %s cancelled by user.", did)
                raise

            except FileNotFoundError:
                logger.error("Executable not found: %s", exe_path)
                self.log_callback(f"❌ Executable not found: {exe_path}")
                raise
            except OSError as exc:
                logger.exception("OS error in subprocess for Depot %s.", did)
                self.log_callback(f"❌ OS error in subprocess Depot {did}: {exc}")
                raise
            except Exception as exc:
                logger.exception("Unexpected error in subprocess for Depot %s.", did)
                self.log_callback(f"❌ Unexpected error Depot {did}. See the log for details.")
                raise
            finally:
                if local_manifest.exists():
                    try:
                        local_manifest.unlink()
                        logger.debug("Local manifest removed: %s", local_manifest)
                    except OSError as exc:
                        logger.warning("Cannot remove local manifest %s: %s", local_manifest, exc)

    @staticmethod
    def _filter_unchanged_files(output_dir: Path, install_dir: Path) -> Tuple[int, int]:
        """
        Walks output_dir and removes files that are byte-for-byte identical to
        the corresponding file in install_dir (matched by relative path).

        Returns (kept_count, removed_count) where:
          - kept   = files that differ from the install (actual updates / new files)
          - removed = files that were identical (unchanged, safely deleted)
        """
        def md5(path: Path) -> str:
            h = hashlib.md5()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()

        kept = 0
        removed = 0

        for output_file in sorted(output_dir.rglob("*")):
            if not output_file.is_file():
                continue

            relative = output_file.relative_to(output_dir)
            install_file = install_dir / relative

            if install_file.is_file():
                # Fast size check first, then hash only if sizes match
                if output_file.stat().st_size == install_file.stat().st_size:
                    try:
                        if md5(output_file) == md5(install_file):
                            output_file.unlink()
                            logger.debug("Removed unchanged: %s", relative)
                            removed += 1
                            continue
                    except OSError as exc:
                        logger.warning("Cannot compare/remove %s: %s", relative, exc)

            kept += 1
            logger.debug("Kept (updated/new): %s", relative)

        # Remove any directories that became empty after filtering
        for dirpath in sorted(output_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if dirpath.is_dir():
                try:
                    dirpath.rmdir()  # no-op unless the directory is empty
                except OSError:
                    pass

        return kept, removed
