from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Input, Button, Static,
    Label, TabbedContent, TabPane, Tabs
)
from textual.containers import Vertical, Horizontal, Container
from textual.reactive import reactive
from pathlib import Path
import subprocess
import tempfile
import datetime
import os

class CSRGenerator(Static):
    sans_list = reactive([])
    config_preview = reactive("")

    def compose(self) -> ComposeResult:
        yield Label("Generate a CSR")
        yield Input(placeholder="Common Name (CN)", id="cn")
        yield Input(placeholder="Organization (O)", id="o")
        yield Input(placeholder="Organizational Unit (OU)", id="ou")
        yield Input(placeholder="Locality (L)", id="l")
        yield Input(placeholder="State (ST)", id="st")
        yield Input(placeholder="Country (C)", id="c")
        yield Input(placeholder="Add SAN (press Enter to add, type ! to remove last)", id="san-input")
        yield Static("SANs: []", id="sans-display")
        yield Static("", id="conf-preview")
        yield Input(placeholder="Password to protect key (optional)", id="pass-protect")
        yield Button("Generate CSR", id="generate")
        yield Static(id="output")

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


class ConversionPanel(Static):
    def compose(self) -> ComposeResult:
        yield Label("Certificate Conversion")
        yield Input(placeholder="Input certificate file (e.g. cert.cer)", id="cert")
        yield Input(placeholder="Private key file (optional)", id="key")
        yield Input(placeholder="Output file name (e.g. bundle.p12)", id="output")
        yield Input(placeholder="Password (for P12, optional)", id="password")
        yield Button("Convert to P12", id="to_p12")
        yield Button("Extract from P12", id="from_p12")
        yield Static(id="conv-output")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        cert = self.query_one("#cert", Input).value.strip()
        key = self.query_one("#key", Input).value.strip()
        out = self.query_one("#output", Input).value.strip()
        password = self.query_one("#password", Input).value.strip()
        log = self.query_one("#conv-output", Static)

        try:
            if event.button.id == "to_p12":
                if not (cert and key and out):
                    log.update("[red]Certificate, key, and output name are required.")
                    return
                cmd = [
                    "openssl", "pkcs12", "-export",
                    "-in", cert,
                    "-inkey", key,
                    "-out", out
                ]
                if password:
                    cmd.extend(["-passout", f"pass:{password}"])
                subprocess.run(cmd, check=True)
                log.update(f"[green]Created P12: {out}")

            elif event.button.id == "from_p12":
                if not (cert and out):
                    log.update("[red]P12 input file and output base name are required.")
                    return
                subprocess.run([
                    "openssl", "pkcs12", "-in", cert, "-out", out + ".crt",
                    "-clcerts", "-nokeys",
                    *(["-passin", f"pass:{password}"] if password else [])
                ], check=True)
                subprocess.run([
                    "openssl", "pkcs12", "-in", cert, "-out", out + ".key",
                    "-nocerts", "-nodes",
                    *(["-passin", f"pass:{password}"] if password else [])
                ], check=True)
                log.update(f"[green]Extracted CRT and KEY to {out}.crt and {out}.key")
        except subprocess.CalledProcessError as e:
            log.update(f"[red]Conversion failed: {e}")


class CertifyTUI(App):
    CSS_PATH = None
    TITLE = "Certify TUI"
    SUB_TITLE = "Generate CSRs and manage certificates"

    BINDINGS = [
        ("ctrl+c", "copy", "Copy"),
        ("ctrl+v", "paste", "Paste"),
        ("q", "quit", "Quit")
    ]

    def compose(self) -> ComposeResult:
        yield Header("[b]Certify TUI[/b] — CTRL+C to copy, CTRL+V to paste, Q to quit")
        yield TabbedContent(
            Tabs("CSR Generator", "Conversions"),
            TabPane(CSRGenerator(id="csr-gen"), id="CSR Generator"),
            TabPane(ConversionPanel(id="convert"), id="Conversions")
        )
        yield Footer()


if __name__ == "__main__":
    app = CertifyTUI()
    app.run()
