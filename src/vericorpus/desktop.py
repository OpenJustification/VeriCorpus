# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import shutil
import sys
import tempfile
import threading
import time
import webbrowser

from . import __schema_version__, __version__
from .config import settings_for_profile
from .optional_adapters import availability
from .pipeline import prepare


def supported_profiles(bundle: str) -> list[str]:
    """Only expose modes compatible with a packaged bundle's Python dependencies."""
    return {"lite": ["lite"], "standard": ["lite", "standard"],
            "verified": ["lite", "standard", "verified"]}.get(bundle, ["lite"])


def _bundle_profile() -> str:
    if getattr(sys, "frozen", False):
        marker = Path(sys.executable).resolve().parent / "BUNDLE_PROFILE.json"
        try:
            name = json.loads(marker.read_text(encoding="utf-8")).get("bundle_profile", "lite")
            return name if name in {"lite", "standard", "verified"} else "lite"
        except (OSError, ValueError, TypeError):
            return "lite"
    # Developers can exercise each GUI mode when launched from Python source.
    return os.environ.get("VERICORPUS_BUNDLE_PROFILE", "verified").lower()


def _prepare_bundle_runtime() -> None:
    """Activate a redistributable, bundled Windows Tesseract when one is present."""
    if getattr(sys, "frozen", False) and sys.platform.startswith("win"):
        root = Path(sys.executable).resolve().parent
        tesseract_dir = root / "Tesseract-OCR"
        if (tesseract_dir / "tesseract.exe").is_file():
            os.environ["PATH"] = str(tesseract_dir) + os.pathsep + os.environ.get("PATH", "")
            # Tesseract looks for data files inside its adjacent tessdata directory.
            os.environ.setdefault("TESSDATA_PREFIX", str(tesseract_dir / "tessdata"))


def _bundle_info() -> dict:
    return {"version": __version__, "bundle_profile": _bundle_profile(),
            "supported_profiles": supported_profiles(_bundle_profile()), "engines": availability()}


def _default_home() -> Path:
    env = os.environ.get("VERICORPUS_HOME")
    if env:
        return Path(env).expanduser().resolve()
    # Packaged releases are deliberately portable: caches, models, and outputs
    # live beside the executable after the release archive is extracted.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "VeriCorpusData"
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "VeriCorpus"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "vericorpus"


def _configure_local_paths(home: Path) -> None:
    cache = home / "cache"
    mapping = {
        "VERICORPUS_HOME": home,
        "VERICORPUS_MODEL_HOME": home / "models",
        "PADDLE_PDX_CACHE_HOME": cache / "paddlex",
        "HF_HOME": cache / "huggingface",
        "TORCH_HOME": cache / "torch",
    }
    for key, value in mapping.items():
        value.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(value)


def _open_path(path: Path) -> None:
    path = path.resolve()
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        import subprocess
        subprocess.Popen(["open", str(path)])
        return
    import subprocess
    opener = shutil.which("xdg-open")
    if opener:
        subprocess.Popen([opener, str(path)])
    else:
        webbrowser.open(path.as_uri())


def _self_test() -> int:
    """Headless smoke test used by release CI and packaged binaries."""
    import fitz

    td = Path(tempfile.mkdtemp(prefix="vericorpus_selftest_"))
    try:
        pdf = td / "input.pdf"
        out = td / "output"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "VeriCorpus desktop self-test")
        page.insert_text((72, 100), "The concentration was 0.05 mg/mL.")
        page.insert_text((72, 128), "The samples were incubated for 30 min.")
        doc.save(pdf)
        doc.close()

        manifest = prepare(pdf, out, settings_for_profile("lite", offline=True))
        training = (out / "training.jsonl").read_text(encoding="utf-8")
        assert "0.05 mg/mL" in training
        assert "30 min" in training
        assert manifest.get("pages_total") == 1
        result = {
            "status": "PASS",
            "version": __version__,
            "schema": __schema_version__,
            "pages": manifest.get("pages_total"),
        }
        output = os.environ.get("VERICORPUS_SELFTEST_OUTPUT")
        if output:
            Path(output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        result = {"status": "FAIL", "error": repr(exc)}
        output = os.environ.get("VERICORPUS_SELFTEST_OUTPUT")
        if output:
            try:
                Path(output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            except Exception:
                pass
        print(json.dumps(result, sort_keys=True), file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(td, ignore_errors=True)


def _run_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as exc:
        print(f"Tk GUI is unavailable: {exc}", file=sys.stderr)
        return 2

    _prepare_bundle_runtime()
    home = _default_home()
    _configure_local_paths(home)
    outputs_home = home / "outputs"
    outputs_home.mkdir(parents=True, exist_ok=True)

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title(f"VeriCorpus {__version__}")
            self.geometry("900x700")
            self.minsize(760, 600)
            self.input_path = tk.StringVar()
            self.output_path = tk.StringVar(value=str(outputs_home))
            self.profile = tk.StringVar(value=_bundle_profile())
            self.allow_network = tk.BooleanVar(value=False)
            self.dpi = tk.IntVar(value=300)
            self.status_text = tk.StringVar(value="Ready")
            self.last_output: Path | None = None
            self.events: queue.Queue[tuple[str, object]] = queue.Queue()
            self._build()
            self.after(100, self._poll_events)

        def _build(self):
            style = ttk.Style(self)
            try:
                style.theme_use("vista" if sys.platform.startswith("win") else "clam")
            except Exception:
                pass

            outer = ttk.Frame(self, padding=18)
            outer.pack(fill="both", expand=True)

            title = ttk.Label(outer, text="VeriCorpus", font=("TkDefaultFont", 22, "bold"))
            title.pack(anchor="w")
            ttk.Label(
                outer,
                text="Local, evidence-first document preparation for auditable LLM training data",
            ).pack(anchor="w", pady=(0, 16))

            file_box = ttk.LabelFrame(outer, text="Input", padding=12)
            file_box.pack(fill="x", pady=(0, 12))
            row = ttk.Frame(file_box)
            row.pack(fill="x")
            ttk.Entry(row, textvariable=self.input_path).pack(side="left", fill="x", expand=True)
            ttk.Button(row, text="Choose PDF/EPUB", command=self._choose_pdf).pack(side="left", padx=(8, 0))
            ttk.Button(row, text="Choose folder", command=self._choose_folder).pack(side="left", padx=(8, 0))

            options = ttk.LabelFrame(outer, text="Processing profile", padding=12)
            options.pack(fill="x", pady=(0, 12))
            profiles = ttk.Frame(options)
            profiles.pack(fill="x")
            for name, desc in [
                ("lite", "Lite — native PDF + Document Structure Engine; fastest/offline"),
                ("standard", "Standard — autonomous layout routing + PaddleOCR-VL/Docling when available"),
                ("verified", "Verified — cross-family OCR/parser verification and abstention"),
            ]:
                enabled = name in supported_profiles(_bundle_profile())
                ttk.Radiobutton(profiles, text=desc, variable=self.profile, value=name,
                                state="normal" if enabled else "disabled").pack(anchor="w", pady=2)
            opts2 = ttk.Frame(options)
            opts2.pack(fill="x", pady=(10, 0))
            ttk.Checkbutton(
                opts2,
                text="Allow network for missing model assets (turn off after first download)",
                variable=self.allow_network,
            ).pack(side="left")
            ttk.Label(opts2, text="Render DPI:").pack(side="left", padx=(18, 4))
            ttk.Combobox(opts2, textvariable=self.dpi, width=6, state="readonly", values=(150, 200, 250, 300, 400, 500, 600)).pack(side="left")

            out_box = ttk.LabelFrame(outer, text="Output", padding=12)
            out_box.pack(fill="x", pady=(0, 12))
            outrow = ttk.Frame(out_box)
            outrow.pack(fill="x")
            ttk.Entry(outrow, textvariable=self.output_path).pack(side="left", fill="x", expand=True)
            ttk.Button(outrow, text="Choose output folder", command=self._choose_output).pack(side="left", padx=(8, 0))

            actions = ttk.Frame(outer)
            actions.pack(fill="x", pady=(0, 12))
            self.run_button = ttk.Button(actions, text="Prepare training data", command=self._start_run)
            self.run_button.pack(side="left")
            ttk.Button(actions, text="System status", command=self._show_status).pack(side="left", padx=(8, 0))
            ttk.Button(actions, text="Open last output", command=self._open_last_output).pack(side="left", padx=(8, 0))

            self.progress = ttk.Progressbar(outer, mode="indeterminate")
            self.progress.pack(fill="x", pady=(0, 8))
            ttk.Label(outer, textvariable=self.status_text).pack(anchor="w")

            log_box = ttk.LabelFrame(outer, text="Run log", padding=8)
            log_box.pack(fill="both", expand=True, pady=(8, 0))
            self.log = tk.Text(log_box, wrap="word", height=14, state="disabled")
            scroll = ttk.Scrollbar(log_box, command=self.log.yview)
            self.log.configure(yscrollcommand=scroll.set)
            self.log.pack(side="left", fill="both", expand=True)
            scroll.pack(side="right", fill="y")

            ttk.Label(
                outer,
                text=(
                    f"VeriCorpus {__version__} • schema {__schema_version__} • AGPL-3.0-or-later\n"
                    "No proprietary API is required. Unresolved content is rejected rather than guessed."
                ),
                justify="left",
            ).pack(anchor="w", pady=(10, 0))

        def _choose_pdf(self):
            from tkinter import filedialog
            value = filedialog.askopenfilename(title="Choose PDF", filetypes=[("Documents", "*.pdf *.epub"), ("PDF files", "*.pdf"), ("EPUB files", "*.epub")])
            if value:
                self.input_path.set(value)

        def _choose_folder(self):
            from tkinter import filedialog
            value = filedialog.askdirectory(title="Choose folder containing PDFs or EPUBs")
            if value:
                self.input_path.set(value)

        def _choose_output(self):
            from tkinter import filedialog
            value = filedialog.askdirectory(title="Choose output folder")
            if value:
                self.output_path.set(value)

        def _append_log(self, text: str):
            self.log.configure(state="normal")
            self.log.insert("end", text.rstrip() + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")

        def _show_status(self):
            from tkinter import messagebox
            status = availability()
            lines = [f"{k}: {'available' if v else 'not available'}" for k, v in sorted(status.items())]
            messagebox.showinfo("VeriCorpus system status", "\n".join(lines))

        def _open_last_output(self):
            from tkinter import messagebox
            if self.last_output and self.last_output.exists():
                try:
                    _open_path(self.last_output)
                except Exception as exc:
                    messagebox.showerror("Open output", str(exc))
            else:
                messagebox.showinfo("Open output", "No completed output is available yet.")

        def _start_run(self):
            from tkinter import messagebox
            raw = self.input_path.get().strip()
            if not raw:
                messagebox.showerror("Input required", "Choose a PDF/EPUB or a folder containing documents.")
                return
            inp = Path(raw)
            if not inp.exists():
                messagebox.showerror("Input not found", str(inp))
                return
            base = Path(self.output_path.get().strip() or outputs_home)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            run_name = inp.stem if inp.is_file() else inp.name or "corpus"
            out = base / f"{run_name}_{stamp}"

            settings = settings_for_profile(
                self.profile.get(),
                offline=not self.allow_network.get(),
                render_dpi=int(self.dpi.get()),
            )
            self.run_button.configure(state="disabled")
            self.progress.start(12)
            self.status_text.set("Processing…")
            self._append_log(f"Input: {inp}")
            self._append_log(f"Output: {out}")
            self._append_log(f"Profile: {settings.profile} | offline={settings.offline} | dpi={settings.render_dpi}")

            def worker():
                try:
                    manifest = prepare(inp, out, settings)
                except Exception as exc:
                    self.events.put(("error", (exc, out)))
                else:
                    self.events.put(("done", (manifest, out)))

            threading.Thread(target=worker, daemon=True).start()

        def _poll_events(self):
            try:
                while True:
                    kind, payload = self.events.get_nowait()
                    if kind == "done":
                        manifest, out = payload  # type: ignore[misc]
                        self.last_output = Path(out)
                        self.progress.stop()
                        self.run_button.configure(state="normal")
                        accepted = manifest.get("pages_accepted_after_dedupe", "?")
                        rejected = manifest.get("pages_rejected_or_reprocess", "?")
                        review = manifest.get("pages_partial_held_for_review", "?")
                        self.status_text.set(f"Completed — training {accepted}, review {review}, rejected {rejected}")
                        self._append_log(json.dumps(manifest, indent=2, sort_keys=True))
                        from tkinter import messagebox
                        if messagebox.askyesno("VeriCorpus complete", f"Processing completed.\n\nOutput:\n{out}\n\nOpen the output folder?"):
                            _open_path(Path(out))
                    elif kind == "error":
                        exc, out = payload  # type: ignore[misc]
                        self.progress.stop()
                        self.run_button.configure(state="normal")
                        self.status_text.set("Processing failed")
                        self._append_log(f"ERROR: {exc!r}")
                        from tkinter import messagebox
                        messagebox.showerror(
                            "VeriCorpus error",
                            f"Processing failed:\n\n{exc}\n\nFor Standard/Verified mode, ensure required local models are installed or enable network once for official model downloads.",
                        )
            except queue.Empty:
                pass
            self.after(100, self._poll_events)

    App().mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vericorpus-desktop")
    parser.add_argument("--self-test", action="store_true", help="run a headless packaged-binary smoke test")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument("--bundle-info", action="store_true", help="report installed engines and bundle profile")
    args = parser.parse_args(argv)
    _prepare_bundle_runtime()
    if args.bundle_info:
        data = json.dumps(_bundle_info(), indent=2, sort_keys=True) + "\n"
        output = os.environ.get("VERICORPUS_INFO_OUTPUT")
        if output:
            Path(output).write_text(data, encoding="utf-8")
        print(data)
        return 0
    if args.version:
        print(__version__)
        return 0
    if args.self_test:
        return _self_test()
    return _run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
