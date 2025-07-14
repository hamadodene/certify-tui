from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Input, Button, Static,
    Label
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

    def compose(self) -> ComposeResult:
        yield Label("Generate a CSR")
        yield Input(placeholder="Common Name (CN)", id="cn")
        yield Input(placeholder="Organization (O)", id="o")
        yield Input(placeholder="Organizational Unit (OU)", id="ou")
        yield Input(placeholder="Locality (L)", id="l")
        yield Input(placeholder="State (ST)", id="st")
        yield Input(placeholder="Country (C)", id="c")
        yield Input(placeholder="Add SAN (press Enter to add)", id="san-input")
        yield Static("SANs: []", id="sans-display")
        yield Button("Generate CSR", id="generate")
        yield Static(id="output")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "san-input":
            value = event.value.strip()
            if value:
                self.sans_list.append(value)
                event.input.value = ""
                sans_display = self.query_one("#sans-display", Static)
                sans_display.update(f"SANs: {self.sans_list}")

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

        if not cn:
            self.log("CN is required.", "red")
            return

        year = datetime.datetime.now().year
        filename_base = cn.replace("*.", "wildcard.") + f"-{year}-{year+10}"
        key_file = f"{filename_base}.key.nopasswd"
        csr_file = f"{filename_base}.csr"

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
            self.log(f"CSR and key generated: {csr_file}, {key_file}", "green")
        except subprocess.CalledProcessError as e:
            self.log(f"OpenSSL error: {e}", "red")
        finally:
            os.unlink(conf_path)


class CertifyTUI(App):
    CSS_PATH = None
    TITLE = "Certify TUI"
    SUB_TITLE = "Generate CSRs and manage certificates"

    def compose(self) -> ComposeResult:
        yield Header()
        yield CSRGenerator(id="csr-gen")
        yield Footer()


if __name__ == "__main__":
    app = CertifyTUI()
    app.run()
