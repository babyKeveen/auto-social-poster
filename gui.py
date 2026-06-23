import json
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext

from PIL import Image, ImageTk
from dotenv import load_dotenv

from ai_utils import generate_alt_text
from social_utils import post_to_mastodon, post_to_instagram

PREVIEW_SIZE = (300, 300)
DEFAULT_IMAGE_DIR = os.path.expanduser(r"~\photoworkshop")
PREFS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prefs.json")


def load_prefs():
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_prefs(prefs):
    try:
        with open(PREFS_FILE, "w") as f:
            json.dump(prefs, f)
    except Exception:
        pass


class TextRedirector:
    def __init__(self, widget, root):
        self.widget = widget
        self.root = root

    def write(self, text):
        self.root.after(0, self._write, text)

    def _write(self, text):
        self.widget.insert("end", text)
        self.widget.see("end")

    def flush(self):
        pass


class App:
    def __init__(self, root):
        self.root = root
        self.prefs = load_prefs()
        root.title("Auto Social Poster")
        root.geometry("860x560")
        root.minsize(700, 450)
        self._preview_image = None

        # Top area: form (left) + image preview (right)
        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")

        form = ttk.Frame(top)
        form.grid(row=0, column=0, sticky="nw")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Image:").grid(row=0, column=0, sticky="w")
        self.image_var = tk.StringVar()
        self.image_var.trace_add("write", self._on_image_var_change)
        ttk.Entry(form, textvariable=self.image_var, width=38).grid(row=0, column=1, sticky="we", padx=5, pady=3)
        ttk.Button(form, text="Browse...", command=self.browse_image).grid(row=0, column=2)

        ttk.Label(form, text="Title / Caption:").grid(row=1, column=0, sticky="w")
        self.caption_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.caption_var, width=38).grid(row=1, column=1, columnspan=2, sticky="we", padx=5, pady=3)

        ttk.Label(form, text="AI Provider:").grid(row=2, column=0, sticky="w")
        self.provider_var = tk.StringVar(value="moondream")
        ttk.Combobox(
            form, textvariable=self.provider_var,
            values=["openai", "gemini", "moondream"], state="readonly", width=20
        ).grid(row=2, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(form, text="Post to:").grid(row=3, column=0, sticky="w")
        self.postto_var = tk.StringVar(value="none")
        ttk.Combobox(
            form, textvariable=self.postto_var,
            values=["none", "mastodon", "instagram", "all"], state="readonly", width=20
        ).grid(row=3, column=1, sticky="w", padx=5, pady=3)

        # Image preview pane
        preview_frame = ttk.LabelFrame(top, text="Preview", padding=5)
        preview_frame.grid(row=0, column=1, sticky="ne", padx=(20, 0))
        self.preview_label = ttk.Label(
            preview_frame, text="No image selected",
            width=30, anchor="center", justify="center"
        )
        self.preview_label.pack(expand=True)

        self.run_btn = ttk.Button(root, text="Generate Alt-Text & Post", command=self.run)
        self.run_btn.pack(pady=6)

        self.output = scrolledtext.ScrolledText(root, height=14, wrap="word")
        self.output.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _on_image_var_change(self, *_):
        if hasattr(self, "_preview_after"):
            self.root.after_cancel(self._preview_after)
        self._preview_after = self.root.after(200, lambda: self.update_preview(self.image_var.get().strip()))

    def update_preview(self, path):
        if not path or not os.path.exists(path):
            self.preview_label.config(image="", text="No image selected")
            self._preview_image = None
            return
        try:
            img = Image.open(path)
            img.thumbnail(PREVIEW_SIZE, Image.LANCZOS)
            self._preview_image = ImageTk.PhotoImage(img)
            self.preview_label.config(image=self._preview_image, text="")
        except Exception:
            self.preview_label.config(image="", text="Cannot preview image")
            self._preview_image = None

    def browse_image(self):
        last_dir = self.prefs.get("last_image_dir", DEFAULT_IMAGE_DIR)
        if not os.path.isdir(last_dir):
            last_dir = DEFAULT_IMAGE_DIR if os.path.isdir(DEFAULT_IMAGE_DIR) else None
        path = filedialog.askopenfilename(
            title="Select an image",
            initialdir=last_dir,
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.gif *.webp *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.prefs["last_image_dir"] = os.path.dirname(path)
            save_prefs(self.prefs)
            self.image_var.set(path)
            self.update_preview(path)

    def log(self, msg):
        self.root.after(0, self._log, msg)

    def _log(self, msg):
        self.output.insert("end", msg)
        self.output.see("end")

    def run(self):
        image = self.image_var.get().strip()
        caption = self.caption_var.get().strip()
        provider = self.provider_var.get()
        post_to = self.postto_var.get()

        if not image or not os.path.exists(image):
            self.log("Error: Please select a valid image file.\n")
            return
        if not caption:
            self.log("Error: Please enter a title/caption.\n")
            return

        self.run_btn.config(state="disabled")
        self.output.delete("1.0", "end")
        thread = threading.Thread(target=self.worker, args=(image, caption, provider, post_to), daemon=True)
        thread.start()

    def worker(self, image, caption, provider, post_to):
        old_stdout = sys.stdout
        sys.stdout = TextRedirector(self.output, self.root)
        try:
            print(f"Generating alt-text using {provider}...")
            alt_text = generate_alt_text(image, provider)
            print("\nGenerated Alt-Text:")
            print("-" * 40)
            print(alt_text)
            print("-" * 40)

            if post_to in ("mastodon", "all"):
                print("\nPosting to Mastodon...")
                post_to_mastodon(image, caption, alt_text)
            if post_to in ("instagram", "all"):
                print("\nPosting to Instagram...")
                post_to_instagram(image, caption, alt_text)

            if post_to == "none":
                print("\nDone (not posted).")
            else:
                print("\nDone.")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            sys.stdout = old_stdout
            self.root.after(0, lambda: self.run_btn.config(state="normal"))


def main():
    load_dotenv()
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
