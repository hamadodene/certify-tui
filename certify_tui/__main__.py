from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Input, Button, Static,
    Label, TabbedContent, TabPane, Select
)
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from pathlib import Path
import subprocess
import tempfile
import datetime
import os
import argparse

class CSRGenerator(Horizontal):
    sans_list = reactive([])
    config_preview = reactive("")

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Generate a CSR")
            yield Input(placeholder="Common Name (CN)", id="cn")
            yield Input(placeholder="Organization (O)", id="o")
            yield Input(placeholder="Organizational Unit (OU)", id="ou")
            yield Input(placeholder="Locality (L)", id="l")
            yield Input(placeholder="State (ST)", id="st")
            yield Input(placeholder="Country (C)", id="c")
            yield Input(placeholder="Add SAN (press Enter to add, type ! to remove last)", id="san-input")
            yield Static("SANs: []", id="sans-display")
            yield Input(placeholder="Password to protect key (optional)", id="pass-protect")
            yield Button("Generate CSR", id="generate")
            yield Static(id="output")

        with Vertical():
            yield Label("OpenSSL Configuration Preview")
            yield Static("", id="conf-preview")

    def on_mount(self) -> None:
        for field_id in ["cn", "o", "ou", "l", "st", "c"]:
            self.query_one(f"#{field_id}", Input).on_change = self.on_input_changed

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "san-input":
            value = event.value.strip()
            if value == "!" and self.sans_list:
                self.sans_list.pop()
            elif value:
                self.sans_list.append(value)
            event.input.value = ""
            self.update_displays()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.update_displays()

    def update_displays(self):
        self.query_one("#sans-display", Static).update(f"SANs: {self.sans_list}")
        self.query_one("#conf-preview", Static).update(self.build_config_preview())

    def build_config_preview(self):
        cn = self.query_one("#cn", Input).value.strip()
        o = self.query_one("#o", Input).value.strip()
        ou = self.query_one("#ou", Input).value.strip()
        l = self.query_one("#l", Input).value.strip()
        st = self.query_one("#st", Input).value.strip()
        c = self.query_one("#c", Input).value.strip()

        config = f"""[req]
default_bits = 4096
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[dn]
C={c}
ST={st}
L={l}
O={o}
OU={ou}
CN={cn}

[req_ext]
subjectAltName = @alt_names

[alt_names]
"""
        for i, san in enumerate(self.sans_list):
            config += f"DNS.{i+1} = {san.strip()}\n"
        return config

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "generate":
            self.generate_csr()

    def log(self, message: str, color: str = ""):
        output = self.query_one("#output", Static)
        output.update(f"[{color}]{message}[/]" if color else message)

    def generate_csr(self):
        cn = self.query_one("#cn", Input).value.strip()
        o = self.query_one("#o", Input).value.strip()
        ou = self.query_one("#ou", Input).value.strip()
        l = self.query_one("#l", Input).value.strip()
        st = self.query_one("#st", Input).value.strip()
        c = self.query_one("#c", Input).value.strip()
        password = self.query_one("#pass-protect", Input).value.strip()

        if not cn:
            self.log("CN is required.", "red")
            return

        year = datetime.datetime.now().year
        filename_base = cn.replace("*.", "wildcard.") + f"-{year}-{year+10}"
        key_file = f"{filename_base}.key.nopasswd"
        key_pass_file = f"{filename_base}.key"
        csr_file = f"{filename_base}.csr"

        config = self.build_config_preview()

        with tempfile.NamedTemporaryFile("w", delete=False) as conf:
            conf.write(config)
            conf_path = conf.name

        try:
            subprocess.run([
                "openssl", "req", "-new", "-sha256", "-nodes",
                "-out", csr_file,
                "-newkey", "rsa:4096",
                "-keyout", key_file,
                "-config", conf_path
            ], check=True)

            if password:
                subprocess.run([
                    "openssl", "rsa", "-des3",
                    "-in", key_file,
                    "-out", key_pass_file,
                    "-passout", f"pass:{password}"
                ], check=True)
                self.log(f"Protected key created: {key_pass_file}", "yellow")

            self.log(f"CSR and key generated: {csr_file}, {key_file}", "green")
        except subprocess.CalledProcessError as e:
            self.log(f"OpenSSL error: {e}", "red")
        finally:
            os.unlink(conf_path)

class CertificateConverter(Vertical):
    def compose(self) -> ComposeResult:
        yield Label("Certificate Format Conversion")
        yield Input(placeholder="Input file 1 (.cer, .pem, .p12, etc.)", id="input1")
        yield Input(placeholder="Input file 2 (.key or password-protected file if needed)", id="input2")
        yield Input(placeholder="Output file name (optional)", id="output")
        yield Input(placeholder="Password (optional)", id="password")
        yield Select(
            options=[
                ("CER + KEY → P12", "cer+key->p12"),
                ("P12 → CER + KEY", "p12->cer+key"),
                ("CER → PEM", "cer->pem"),
                ("P12 → PEM", "p12->pem"),
                ("PEM + KEY → P12", "pem+key->p12")
            ],
            prompt="Select conversion type",
            id="conversion",
            value="cer+key->p12"
        )
        yield Button("Convert", id="convert")
        yield Static(id="convert-output")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "convert":
            self.run_conversion()

    def run_conversion(self):
        inp1 = self.query_one("#input1", Input).value.strip()
        inp2 = self.query_one("#input2", Input).value.strip()
        out = self.query_one("#output", Input).value.strip()
        password = self.query_one("#password", Input).value.strip()
        select = self.query_one("#conversion", Select)
        conv = select.value if select.value else None

        log = self.query_one("#convert-output", Static)

        # Validation
        if not conv:
            log.update("[red]Please select a conversion type.[/red]")
            return

        conv = conv.strip().lower()

        if not inp1:
            log.update("[red]Input file 1 is required.[/red]")
            return
        if not Path(inp1).exists():
            log.update(f"[red]Input file 1 not found: {inp1}[/red]")
            return

        if conv in ["cer+key->p12", "pem+key->p12"]:
            if not inp2:
                log.update("[red]Input file 2 is required for this conversion.[/red]")
                return
            if not Path(inp2).exists():
                log.update(f"[red]Input file 2 not found: {inp2}[/red]")
                return

        try:
            if conv == "cer+key->p12":
                if not out:
                    out = Path(inp1).stem + ".p12"
                subprocess.run([
                    "openssl", "pkcs12", "-export",
                    "-in", inp1,
                    "-inkey", inp2,
                    "-out", out,
                    "-password", f"pass:{password}" if password else ""
                ], check=True)

            elif conv == "p12->cer+key":
                subprocess.run([
                    "openssl", "pkcs12", "-in", inp1,
                    "-clcerts", "-nokeys",
                    "-out", out or "output.cer",
                    "-password", f"pass:{password}" if password else ""
                ], check=True)
                subprocess.run([
                    "openssl", "pkcs12", "-in", inp1,
                    "-nocerts", "-nodes",
                    "-out", Path(out or "output.key").with_suffix(".key"),
                    "-password", f"pass:{password}" if password else ""
                ], check=True)

            elif conv == "cer->pem":
                subprocess.run([
                    "openssl", "x509", "-in", inp1,
                    "-out", out or "output.pem",
                    "-outform", "PEM"
                ], check=True)

            elif conv == "p12->pem":
                subprocess.run([
                    "openssl", "pkcs12", "-in", inp1,
                    "-out", out or "output.pem",
                    "-nodes",
                    "-password", f"pass:{password}" if password else ""
                ], check=True)

            elif conv == "pem+key->p12":
                subprocess.run([
                    "openssl", "pkcs12", "-export",
                    "-in", inp1,
                    "-inkey", inp2,
                    "-out", out or "output.p12",
                    "-password", f"pass:{password}" if password else ""
                ], check=True)

            else:
                log.update(f"Unknown conversion type: {conv}", style="red")
                return

            log.update(f"[green]Conversion successful! Output: {out}[/green]")

        except subprocess.CalledProcessError as e:
            log.update(f"[red]Conversion failed: {e}[/red]")

class CertifyTUI(App):
    CSS_PATH = None
    TITLE = "Certify TUI"
    SUB_TITLE = "Generate CSRs and manage certificates"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("tab", "focus_next", "Next Tab"),
        ("shift+tab", "focus_previous", "Prev Tab")
    ]

    def compose(self) -> ComposeResult:
        yield Header("[b]Certify TUI[/b] — TAB to switch tabs, Q to quit")
        with TabbedContent(initial="csr"):
            with TabPane("CSR", id="csr"):
                yield CSRGenerator()
            with TabPane("Conversions", id="conversions"):
                yield CertificateConverter()
        yield Footer()

def main():
    app = CertifyTUI()
    app.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Certify TUI - CSR & Certificate Conversion Tool")
    parser.add_argument(
        "--workdir", type=str, default=".",
        help="Directory where generated or converted files will be stored (default: current directory)"
    )
    args = parser.parse_args()

    # Set global output dir
    os.chdir(args.workdir)
    main()