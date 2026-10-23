"""Pilote de l'imprimante thermique CSN-A2 (version TTL, papier 58 mm, 384 points par ligne).

L'imprimante n'a pas de contrôle de flux matériel : on estime le temps d'impression de chaque ligne et
on attend en conséquence, sinon sa mémoire tampon déborde et le ticket est illisible. Les temps sont
réglables dans la configuration (`dot_print_time_s`, `dot_feed_time_s`).

Jeu de caractères : CP437, la table par défaut de tous les firmwares. Elle contient les accents
minuscules du français et beaucoup de symboles mathématiques (½ ¼ ² ± ÷ ≤ ≥ √ ° π ∞). Les caractères
absents sont translittérés (À → A, œ → oe, × → x…).

Le module sépare :
- le modèle de ticket (`Ticket` et ses blocs), indépendant du matériel ;
- `render_commands()` qui le traduit en octets (fonction pure, testée) ;
- `render_preview()` qui en donne un aperçu texte (simulation, aperçu à l'écran) ;
- `CsnA2Printer` qui envoie les octets sur un transport série, avec temporisation.
"""

from __future__ import annotations

import logging
import textwrap
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Literal, Protocol, Union

import numpy as np

log = logging.getLogger(__name__)

# --- Constantes du protocole ---------------------------------------------------------------------

ESC, GS, DC2 = 0x1B, 0x1D, 0x12
DOTS_PER_LINE = 384
CHAR_HEIGHT_DOTS = 24
LINE_SPACING_DOTS = 6

# Bits du mode d'impression (ESC ! n)
MODE_INVERSE = 1 << 1
MODE_UPSIDE_DOWN = 1 << 2
MODE_BOLD = 1 << 3
MODE_DOUBLE_HEIGHT = 1 << 4
MODE_DOUBLE_WIDTH = 1 << 5

Size = Literal["S", "M", "L"]
Align = Literal["left", "center", "right"]

# Largeur en caractères selon la taille : police A 12×24 → 32 colonnes ; double largeur → 16.
COLUMNS = {"S": 32, "M": 32, "L": 16}
_SIZE_MODE = {"S": 0, "M": MODE_DOUBLE_HEIGHT, "L": MODE_DOUBLE_HEIGHT | MODE_DOUBLE_WIDTH}
_SIZE_HEIGHT = {"S": 1, "M": 2, "L": 2}
_ALIGN = {"left": 0, "center": 1, "right": 2}

# Caractères absents de CP437 → remplacement lisible
_TRANSLIT = str.maketrans({
    "À": "A", "Â": "A", "È": "E", "Ê": "E", "Ë": "E", "Î": "I", "Ï": "I", "Ô": "O", "Û": "U", "Ù": "U",
    "Ÿ": "Y", "ÿ": "y",
    "œ": "oe", "Œ": "OE", "æ": "ae",
    "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...",
    "€": "EUR", "×": "x", "−": "-", "≠": "=/=", "→": "->", "⇒": "=>", "≈": "~",
    " ": " ", " ": " ",
})


def encode_cp437(text: str) -> bytes:
    """Encode pour l'imprimante : translittération puis CP437, caractère inconnu → '?'."""
    return text.translate(_TRANSLIT).encode("cp437", errors="replace")


# --- Modèle de ticket ----------------------------------------------------------------------------

@dataclass
class Text:
    text: str
    size: Size = "S"
    bold: bool = False
    align: Align = "left"
    inverse: bool = False
    underline: bool = False


@dataclass
class Separator:
    char: str = "-"


@dataclass
class AnswerLines:
    """Zone de réponse manuscrite : lignes pointillées."""
    count: int = 3


@dataclass
class Feed:
    lines: int = 1


@dataclass
class Bitmap:
    """Image 1 bit (True = point noir), largeur ≤ 384. Sert aux figures, fractions, QR codes rendus en image."""
    pixels: np.ndarray
    align: Align = "center"


Block = Union[Text, Separator, AnswerLines, Feed, Bitmap]


@dataclass
class Ticket:
    blocks: list[Block] = field(default_factory=list)

    def add(self, *blocks: Block) -> "Ticket":
        self.blocks.extend(blocks)
        return self


def exercise_ticket(
    *,
    student: str,
    kiosk: str,
    title: str,
    instructions: str,
    questions: list[str],
    answer_lines: int = 3,
    footer: str = "Agrafe ce ticket dans ton cahier.",
    now: datetime | None = None,
) -> Ticket:
    """Ticket d'exercice standard (exercice imprimé, ticket de remédiation…)."""
    now = now or datetime.now()
    ticket = Ticket()
    ticket.add(
        Text("ARISTOTE", size="M", bold=True, align="center"),
        Text(f"{student} · {kiosk} · {now:%d/%m/%Y %H:%M}", align="center"),
        Separator("="),
        Text(title, bold=True),
        Text(instructions),
        Feed(),
    )
    for n, question in enumerate(questions, start=1):
        ticket.add(Text(f"{n}) {question}"), AnswerLines(answer_lines), Feed())
    ticket.add(Separator(), Text(footer, align="center"), Feed(3))
    return ticket


# --- Rendu -----------------------------------------------------------------------------------------

def wrap(text: str, size: Size) -> list[str]:
    width = COLUMNS[size]
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width=width, break_long_words=True) or [""])
    return lines


@dataclass
class Chunk:
    """Morceau de flux série + nombre de lignes de points qu'il fait avancer (pour la temporisation)."""
    data: bytes
    printed_dots: int = 0
    fed_dots: int = 0


def _mode_bytes(block: Text) -> bytes:
    mode = _SIZE_MODE[block.size]
    if block.bold:
        mode |= MODE_BOLD
    if block.inverse:
        mode |= MODE_INVERSE
    return bytes([
        ESC, ord("!"), mode,
        ESC, ord("a"), _ALIGN[block.align],
        ESC, ord("-"), 1 if block.underline else 0,
    ])


_RESET_STYLE = bytes([ESC, ord("!"), 0, ESC, ord("a"), 0, ESC, ord("-"), 0])


def _bitmap_chunks(bitmap: Bitmap) -> list[Chunk]:
    pixels = np.asarray(bitmap.pixels, dtype=bool)
    if pixels.ndim != 2:
        raise ValueError("le bitmap doit être une matrice 2D")
    height, width = pixels.shape
    if width > DOTS_PER_LINE:
        raise ValueError(f"bitmap trop large : {width} > {DOTS_PER_LINE} points")
    # Centrage/alignement par marge blanche à gauche, puis largeur arrondie à l'octet.
    left = {"left": 0, "center": (DOTS_PER_LINE - width) // 2, "right": DOTS_PER_LINE - width}[bitmap.align]
    total = left + width
    row_bytes = (total + 7) // 8
    canvas = np.zeros((height, row_bytes * 8), dtype=bool)
    canvas[:, left:left + width] = pixels
    packed = np.packbits(canvas, axis=1)  # bit de poids fort = point le plus à gauche
    chunks = []
    for start in range(0, height, 255):  # DC2 * r n : au plus 255 lignes par commande
        rows = packed[start:start + 255]
        header = bytes([DC2, ord("*"), rows.shape[0], row_bytes])
        chunks.append(Chunk(header + rows.tobytes(), printed_dots=rows.shape[0]))
    return chunks


def render_chunks(ticket: Ticket) -> list[Chunk]:
    chunks: list[Chunk] = []
    for block in ticket.blocks:
        if isinstance(block, Text):
            chunks.append(Chunk(_mode_bytes(block)))
            for line in wrap(block.text, block.size):
                dots = CHAR_HEIGHT_DOTS * _SIZE_HEIGHT[block.size]
                chunks.append(Chunk(encode_cp437(line) + b"\n", printed_dots=dots, fed_dots=LINE_SPACING_DOTS))
            chunks.append(Chunk(_RESET_STYLE))
        elif isinstance(block, Separator):
            line = (block.char * COLUMNS["S"])[: COLUMNS["S"]]
            chunks.append(Chunk(encode_cp437(line) + b"\n", printed_dots=CHAR_HEIGHT_DOTS, fed_dots=LINE_SPACING_DOTS))
        elif isinstance(block, AnswerLines):
            for _ in range(block.count):
                chunks.append(Chunk(b"\n", fed_dots=CHAR_HEIGHT_DOTS + LINE_SPACING_DOTS))
                chunks.append(Chunk(b". " * (COLUMNS["S"] // 2) + b"\n", printed_dots=CHAR_HEIGHT_DOTS,
                                    fed_dots=LINE_SPACING_DOTS))
        elif isinstance(block, Feed):
            if block.lines > 0:
                chunks.append(Chunk(bytes([ESC, ord("d"), min(block.lines, 255)]),
                                    fed_dots=block.lines * (CHAR_HEIGHT_DOTS + LINE_SPACING_DOTS)))
        elif isinstance(block, Bitmap):
            chunks.extend(_bitmap_chunks(block))
        else:  # pragma: no cover - garde-fou
            raise TypeError(f"bloc inconnu : {block!r}")
    return chunks


def render_commands(ticket: Ticket) -> bytes:
    return b"".join(chunk.data for chunk in render_chunks(ticket))


def render_preview(ticket: Ticket) -> str:
    """Aperçu texte approximatif du ticket (32 colonnes)."""
    out: list[str] = []
    width = COLUMNS["S"]
    for block in ticket.blocks:
        if isinstance(block, Text):
            for line in wrap(block.text, block.size):
                if block.size == "L":
                    line = " ".join(line)
                if block.align == "center":
                    line = line.center(width).rstrip()
                elif block.align == "right":
                    line = line.rjust(width)
                out.append(line.upper() if block.bold and block.size != "S" else line)
        elif isinstance(block, Separator):
            out.append((block.char * width)[:width])
        elif isinstance(block, AnswerLines):
            for _ in range(block.count):
                out.extend(["", ". " * (width // 2)])
        elif isinstance(block, Feed):
            out.extend([""] * block.lines)
        elif isinstance(block, Bitmap):
            h, w = np.asarray(block.pixels).shape
            out.append(f"[image {w}×{h}]".center(width).rstrip())
    return "\n".join(out) + "\n"


# --- Transport et pilote --------------------------------------------------------------------------

class Transport(Protocol):
    def write(self, data: bytes) -> None: ...
    def read(self, size: int) -> bytes: ...
    def close(self) -> None: ...


class SerialTransport:
    def __init__(self, port: str, baudrate: int, timeout: float = 0.5) -> None:
        import serial  # pyserial

        self._serial = serial.Serial(port, baudrate=baudrate, timeout=timeout, write_timeout=5)

    def write(self, data: bytes) -> None:
        self._serial.write(data)

    def read(self, size: int) -> bytes:
        return self._serial.read(size)

    def reset_input(self) -> None:
        self._serial.reset_input_buffer()

    def close(self) -> None:
        self._serial.close()


class MemoryTransport:
    """Transport en mémoire (tests, simulation)."""

    def __init__(self, reply: bytes = b"") -> None:
        self.buffer = bytearray()
        self._reply = reply

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    def read(self, size: int) -> bytes:
        reply, self._reply = self._reply[:size], self._reply[size:]
        return reply

    def close(self) -> None:
        pass


class CsnA2Printer:
    def __init__(
        self,
        transport: Transport,
        *,
        baudrate: int = 19200,
        heat_dots: int = 11,
        heat_time: int = 120,
        heat_interval: int = 40,
        density: int = 10,
        break_time: int = 2,
        dot_print_time_s: float = 0.0033,
        dot_feed_time_s: float = 0.0021,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._t = transport
        self._byte_time = 11 / baudrate  # 1 bit de départ + 8 bits + 2 bits d'arrêt, marge comprise
        self._dot_print = dot_print_time_s
        self._dot_feed = dot_feed_time_s
        self._sleep = sleep
        self._heat = (heat_dots, heat_time, heat_interval)
        self._density = (break_time << 5) | density
        self.initialize()

    def initialize(self) -> None:
        self._sleep(0.5)  # l'imprimante ignore les octets pendant ~0,5 s après la mise sous tension
        self._send(Chunk(bytes([ESC, ord("@")])))                               # réinitialisation
        self._send(Chunk(bytes([ESC, ord("7"), *self._heat])))                  # chauffe
        self._send(Chunk(bytes([DC2, ord("#"), self._density])))                # densité
        self._send(Chunk(bytes([ESC, ord("t"), 0])))                            # table CP437

    def _send(self, chunk: Chunk) -> None:
        self._t.write(chunk.data)
        delay = (len(chunk.data) * self._byte_time + chunk.printed_dots * self._dot_print
                 + chunk.fed_dots * self._dot_feed)
        self._sleep(delay)

    def print_ticket(self, ticket: Ticket) -> None:
        for chunk in render_chunks(ticket):
            self._send(chunk)

    def has_paper(self) -> bool | None:
        """Interroge le capteur de papier (nécessite le fil TX de l'imprimante). None si pas de réponse."""
        reset = getattr(self._t, "reset_input", None)
        if reset:
            reset()
        self._t.write(bytes([ESC, ord("v"), 0]))
        reply = self._t.read(1)
        if not reply:
            return None
        return not (reply[0] & 0b0000_0100)

    def sleep_mode(self, seconds: int = 1) -> None:
        """Met l'imprimante en veille (réduit la consommation au repos)."""
        self._send(Chunk(bytes([ESC, ord("8"), seconds & 0xFF, seconds >> 8])))

    def wake(self) -> None:
        self._send(Chunk(bytes([0xFF])))
        self._sleep(0.05)
        self._send(Chunk(bytes([ESC, ord("8"), 0, 0])))

    def close(self) -> None:
        self._t.close()


class PreviewPrinter:
    """Imprimante simulée : conserve les aperçus texte (et les octets) des tickets imprimés."""

    def __init__(self) -> None:
        self.printed: list[str] = []
        self.raw: list[bytes] = []

    def print_ticket(self, ticket: Ticket) -> None:
        preview = render_preview(ticket)
        self.printed.append(preview)
        self.raw.append(render_commands(ticket))
        log.info("ticket (imprimante simulée) :\n%s", preview)

    def has_paper(self) -> bool | None:
        return True

    def close(self) -> None:
        pass
