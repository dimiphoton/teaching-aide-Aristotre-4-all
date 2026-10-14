import numpy as np
import pytest

from aristote.hardware.printer_csn_a2 import (
    DC2,
    ESC,
    AnswerLines,
    Bitmap,
    CsnA2Printer,
    MemoryTransport,
    PreviewPrinter,
    Text,
    Ticket,
    encode_cp437,
    exercise_ticket,
    render_chunks,
    render_commands,
    wrap,
)


def test_french_accents_and_math_symbols_use_cp437():
    assert encode_cp437("é è à ç ù ô") == bytes([0x82, 0x20, 0x8A, 0x20, 0x85, 0x20, 0x87, 0x20, 0x97, 0x20, 0x93])
    assert encode_cp437("½ ² ≤ √ π °") == bytes([0xAB, 0x20, 0xFD, 0x20, 0xF3, 0x20, 0xFB, 0x20, 0xE3, 0x20, 0xF8])


def test_missing_characters_are_transliterated_not_dropped():
    assert encode_cp437("À l’école, œuvre — 3×4 €") == b"A l'\x82cole, oeuvre - 3x4 EUR"
    assert encode_cp437("日") == b"?"


def test_wrap_respects_columns_per_size():
    text = "mot " * 20
    assert all(len(line) <= 32 for line in wrap(text, "S"))
    assert all(len(line) <= 16 for line in wrap(text, "L"))
    assert wrap("a\n\nb", "S") == ["a", "", "b"]


def test_text_block_sets_and_resets_style():
    data = render_commands(Ticket().add(Text("Titre", size="L", bold=True, align="center")))
    assert data.startswith(bytes([ESC, ord("!"), 0x38, ESC, ord("a"), 1, ESC, ord("-"), 0]))
    assert b"Titre\n" in data
    assert data.endswith(bytes([ESC, ord("!"), 0, ESC, ord("a"), 0, ESC, ord("-"), 0]))


def test_bitmap_is_packed_msb_first_and_centered():
    pixels = np.zeros((2, 16), dtype=bool)
    pixels[0, 0] = True       # premier point de la 1re ligne
    pixels[1, 15] = True      # dernier point de la 2e ligne
    data = render_commands(Ticket().add(Bitmap(pixels, align="left")))
    assert data[:4] == bytes([DC2, ord("*"), 2, 2])
    assert data[4:] == bytes([0b1000_0000, 0, 0, 0b0000_0001])

    centered = render_commands(Ticket().add(Bitmap(pixels, align="center")))
    row_bytes = centered[3]
    assert row_bytes == (184 + 16 + 7) // 8  # marge (384-16)/2 = 184 points


def test_tall_bitmap_is_split_in_255_row_commands():
    chunks = render_chunks(Ticket().add(Bitmap(np.ones((300, 8), dtype=bool), align="left")))
    assert [c.data[2] for c in chunks] == [255, 45]


def test_bitmap_wider_than_paper_is_rejected():
    with pytest.raises(ValueError):
        render_commands(Ticket().add(Bitmap(np.ones((1, 400), dtype=bool))))


def test_printer_initialisation_and_throttling():
    delays = []
    transport = MemoryTransport()
    printer = CsnA2Printer(transport, heat_dots=7, heat_time=80, heat_interval=2, density=15, break_time=1,
                           sleep=delays.append)
    assert bytes(transport.buffer) == bytes([
        ESC, ord("@"),
        ESC, ord("7"), 7, 80, 2,
        DC2, ord("#"), (1 << 5) | 15,
        ESC, ord("t"), 0,
    ])
    delays.clear()
    printer.print_ticket(Ticket().add(Text("bonjour"), AnswerLines(1)))
    assert all(d >= 0 for d in delays)
    assert sum(delays) > 0.05  # le temps d'impression des lignes est bien attendu


@pytest.mark.parametrize("status, expected", [(b"\x00", True), (b"\x04", False), (b"", None)])
def test_paper_sensor(status, expected):
    printer = CsnA2Printer(MemoryTransport(reply=status), sleep=lambda s: None)
    assert printer.has_paper() is expected


def test_exercise_ticket_preview():
    printer = PreviewPrinter()
    printer.print_ticket(exercise_ticket(student="E07", kiosk="K03", title="Fractions",
                                         instructions="Réponds sur les pointillés.",
                                         questions=["1/3 + 1/4 = ?"], answer_lines=2))
    preview = printer.printed[0]
    assert "E07" in preview and "1) 1/3 + 1/4 = ?" in preview
    assert sum(line.startswith(". . .") for line in preview.splitlines()) == 2
    assert all(len(line) <= 32 for line in preview.splitlines())
