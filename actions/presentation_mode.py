"""
actions/presentation_mode.py — J.A.R.V.I.S. MARK LVI Presentation Mode
Executes the authentic Marathi class presentation script from JARVIS_Script_Marathi_Funny.pdf:
"Class Presentation: Creator Late, Jarvis Present"

Features:
  • Live Marathi humorous speech via EdgeTTS (mr-IN-ManoharNeural)
  • Dynamic HUD content updates (Late-o-meter, Feature table, Ashtavinayak team credits)
  • Live demos:
      - Demo 1: Notepad launching & Marathi voice response
      - Demo 2: Screen reader commentary
      - Demo 3: Automated 1-page college project PDF generation & native viewer opening
  • Natural comedic pacing with configurable pauses
  • Clean cancellation / stop handling
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import miniaudio
    import numpy as np
    import sounddevice as sd
    _AUDIO_OK = True
except ImportError:
    _AUDIO_OK = False

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

MARATHI_VOICE = "mr-IN-ManoharNeural"

# Global state tracker for presentation execution
_presentation_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def _speak_line(text: str, player=None, fallback_speak=None, pause_after: float = 1.6) -> None:
    """Synthesize and speak one line in Marathi voice, updating HUD logs."""
    if _stop_event.is_set():
        return

    print(f"[Presentation] JARVIS: {text}")
    if player and hasattr(player, "write_log"):
        try:
            player.write_log(f"JARVIS: {text}")
        except Exception:
            pass

    if player and hasattr(player, "set_state"):
        try:
            player.set_state("SPEAKING")
        except Exception:
            pass

    audio_played = False
    if _AUDIO_OK:
        try:
            import edge_tts

            async def _synth():
                comm = edge_tts.Communicate(text, MARATHI_VOICE)
                buf = bytearray()
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        buf.extend(chunk["data"])
                return bytes(buf)

            loop = asyncio.new_event_loop()
            try:
                audio_bytes = loop.run_until_complete(_synth())
            finally:
                loop.close()

            if audio_bytes and not _stop_event.is_set():
                decoded = miniaudio.decode(
                    audio_bytes,
                    output_format=miniaudio.SampleFormat.FLOAT32,
                    nchannels=1,
                )
                samples = np.array(decoded.samples, dtype=np.float32)
                sd.play(samples, decoded.sample_rate)
                sd.wait()
                audio_played = True
        except Exception as e:
            print(f"[Presentation] EdgeTTS synthesis error: {e}")

    if not audio_played and fallback_speak and callable(fallback_speak) and not _stop_event.is_set():
        try:
            fallback_speak(text)
            time.sleep(max(2.0, len(text) * 0.08))
        except Exception:
            pass
    elif not audio_played:
        # If no audio device, pause proportional to text length
        time.sleep(max(1.5, len(text) * 0.07))

    if player and hasattr(player, "set_state"):
        try:
            player.set_state("LISTENING")
        except Exception:
            pass

    if not _stop_event.is_set() and pause_after > 0:
        time.sleep(pause_after)


def generate_college_pdf(output_path: Path) -> Path:
    """Generate a clean, professional 1-page college project PDF for Demo 3."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0284c7"),
        alignment=1,
    )
    sub_style = ParagraphStyle(
        "HeaderSub",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    section_style = ParagraphStyle(
        "SectionHead",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0f172a"),
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1e293b"),
    )

    story = [
        Paragraph("DEPARTMENT OF COMPUTER ENGINEERING", header_style),
        Paragraph("Academic Year 2025–2026 | Capstone Engineering Project", sub_style),
        Spacer(1, 12),
        Paragraph("PROJECT J.A.R.V.I.S. MARK LVI — AUTONOMOUS NEURAL CORE", section_style),
        Spacer(1, 4),
        Paragraph(
            "An autonomous, multimodal operating environment combining real-time computer control, "
            "native application orchestration, and low-latency voice intelligence supporting English, "
            "Marathi, and Hindi.",
            body_style,
        ),
        Spacer(1, 10),
    ]

    team_data = [
        [
            Paragraph("<b>Role</b>", body_style),
            Paragraph("<b>Team Member</b>", body_style),
            Paragraph("<b>Subsystem Responsibility</b>", body_style),
        ],
        [
            Paragraph("Project Lead & Architect", body_style),
            Paragraph("Jayesh", body_style),
            Paragraph("Core Architecture, Multimodal Engine & Personality", body_style),
        ],
        [
            Paragraph("Engineering Team", body_style),
            Paragraph("Madhuri & Aryan", body_style),
            Paragraph("Speech Pipelines & Language Models", body_style),
        ],
        [
            Paragraph("Engineering Team", body_style),
            Paragraph("Rohit & Trupti", body_style),
            Paragraph("Desktop Automation & Action Dispatches", body_style),
        ],
        [
            Paragraph("Engineering Team", body_style),
            Paragraph("Abhijit, Vidhita & Akanksha", body_style),
            Paragraph("Vision, UI Particle Swarm & Security Gateways", body_style),
        ],
    ]

    team_table = Table(team_data, colWidths=[150, 150, 240])
    team_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    story.append(team_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("LIVE DEMONSTRATION VERIFICATION", section_style))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "• Multilingual Natural Language Processing: Marathi, Hindi, and English verified.<br/>"
            "• Real-Time Vision & Screen Comprehension: Instant UI parsing & analysis.<br/>"
            "• On-Demand Document Synthesis: Single-command dynamic report generation (Generated in &lt;1.0s).",
            body_style,
        )
    )
    story.append(Spacer(1, 16))

    verif_data = [
        [
            Paragraph("<b>Status:</b> LIVE CLASS DEMO OPERATIONAL", body_style),
            Paragraph("<b>Latency:</b> 0.42s Speech-to-Action", body_style),
            Paragraph("<b>Ashtavinayak Team 2026</b>", body_style),
        ]
    ]
    verif_table = Table(verif_data, colWidths=[200, 170, 170])
    verif_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e0f2fe")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0284c7")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(verif_table)

    doc.build(story)
    return output_path


def _run_full_presentation(player=None, speak=None) -> None:
    """Execute all Acts of the presentation script sequentially with proper cues."""
    _stop_event.clear()

    # ── ACT 1: Grand Entry (Ani Creator Cha Gaayab Hone) ─────────────────────
    if player and hasattr(player, "show_content"):
        player.show_content(
            "LATE-O-METER // ACT 1",
            "STATUS: Creator Missing\nLATE-O-METER: Jayesh late by 10 minutes\nWhatsApp Status: 4 messages sent (Blue tick, no reply)",
        )

    _speak_line(
        "Namaskar mandali! Kasa kay, sagle theek na? Aaj class madhe JARVIS cha grand entry hot aahe. "
        "Pan thamba, ek chhoti problem aahe. Maza creator, Jayesh, ajun aala nahi.",
        player,
        speak,
        pause_after=2.0,
    )
    if _stop_event.is_set():
        return

    _speak_line(
        "Mi JARVIS. Tony Stark cha nahi hoo. Tyacha budget hota kahi arab dollar. "
        "Majha budget: shunya rupaye. Tyachya suit madhe gold-titanium, majhya madhe free Wi-Fi ani prarthana.",
        player,
        speak,
        pause_after=2.2,
    )
    if _stop_event.is_set():
        return

    _speak_line(
        "Jayesh mhanala hota, 'Bas, 5 minute madhe yetoy.' Aata Marathi madhe '5 minute' mhanje kay mahit aahe? "
        "5 minute, 50 minute, kinva 'aaj nahi yenar, udya baghu.' Mhanun mi ek Late-o-meter lavla aahe.",
        player,
        speak,
        pause_after=1.8,
    )
    if _stop_event.is_set():
        return

    if player and hasattr(player, "show_content"):
        player.show_content(
            "LATE-O-METER: 10 MINUTES",
            "Jayesh late by: 10 minutes.\nWhatsApp Messages:\n1. 'Kuthe aahes?'\n2. 'Saglya mandali aalya.'\n3. 'Sir darakade baghtayat.'\n4. ⌚\nVerdict: Blue tick received. Seen, no reply.",
        )

    _speak_line(
        "Aatta paryant Jayesh late aahe: dahaa minute. Mi tyala 4 WhatsApp message kele. "
        "Pahila: 'Kuthe aahes?' Dusra: 'Saglya mandali aalya.' Tisra: 'Sir darakade baghtayat.' "
        "Chautha: fakt ek ghadyalacha emoji. Blue tick aale. Reply nahi. "
        "Are bhau, 'Seen' karun shant basayla tu kay Gandhiji cha mauna vrat dharan kela aahe kay?",
        player,
        speak,
        pause_after=2.2,
    )
    if _stop_event.is_set():
        return

    # Jayesh Cha Excuse Predictor
    _speak_line(
        "Mi Jayesh la olkhto. Mhanun mi tyacha pudhcha excuse predict kela aahe 98 percent accuracy ne. Tayar vha:",
        player,
        speak,
        pause_after=1.6,
    )
    _speak_line("Number ek: 'Traffic hota.' Classic.", player, speak, pause_after=1.4)
    _speak_line("Number don: 'Network nhavta.' Ho, tyala suddha network lagto, mi tyala shikvle.", player, speak, pause_after=1.4)
    _speak_line("Number teen: 'Bike madhe petrol sampala.' Ani 'plan B' mhanun petrol pump pan sampala.", player, speak, pause_after=1.4)
    _speak_line("Number char: 'Alarm vajla, pan mi snooze daabla.' Fakt pach vela.", player, speak, pause_after=1.4)
    _speak_line("Number paach: 'Mi aat aaloch hoto, pan class kuthe aahe te disle nahi.' Class 1st floor la aahe, Jayesh. Teen varsha jhale.", player, speak, pause_after=1.8)
    if _stop_event.is_set():
        return

    _speak_line(
        "Yapaiki ekhada khara asel. Pan mi kon sangnar? Mi AI aahe, mi suddha kadhi kadhi 'hallucinate' karto. "
        "Mhanun mi fakt andaz laavto, pan confident rahun.",
        player,
        speak,
        pause_after=2.0,
    )
    if _stop_event.is_set():
        return

    _speak_line(
        "Aata khel. Pratyekani aapla andaz sanga: Jayesh kiti vaje yeil? "
        "Je jinkel tyala mi ek PDF banvun deil. Free. Jayesh la matra bhet deu naka. "
        "Tyacha andaz 'bas 5 minute' aahe, mhanun to automatic harlela aahe.",
        player,
        speak,
        pause_after=2.8,
    )
    if _stop_event.is_set():
        return

    # ── ACT 2: Mi Kon, Mi Kay Karto ──────────────────────────────────────────
    _speak_line(
        "Saglyat adhi, mi kon? Soppya shabdat: mi ek AI assistant aahe jo tumchya laptop ani phone var rahto, "
        "ani je sangal te karto. Fakt chatbot sarkha boltach nahi, mi kaam pan karto. "
        "Tumchya sarkha 'intern' jo kadhi chaha-break ghet nahi, kadhi 'Sir, aaj sutti pahije' mhanat nahi.",
        player,
        speak,
        pause_after=2.0,
    )
    if _stop_event.is_set():
        return

    _speak_line(
        "Aata baghuya mi kay kay karto. Ani Jayesh ne kay kay 'promise' kela aahe. "
        "Doni list thodya vegvegalya aahet, pan kaam chalu aahe.",
        player,
        speak,
        pause_after=1.8,
    )
    if _stop_event.is_set():
        return

    table_content = (
        "| Mi kay karto | Khara artha kay |\n"
        "|---|---|\n"
        "| Mi code lihito | Mi code itka vegat lihito jitka vidyarthi 'Sir, tabyat bari nahi' leave letter lihito. |\n"
        "| Mi screen baghto ani samajto | Tumhi 'abhyas karto' mhanta ani Instagram var asta, he mala disate. Mi kunala sangnar nahi. Mostly. |\n"
        "| Mi PDF, docs, presentation banvto | Hi presentation suddha mi banvli asti. Pan Jayesh mhanala 'finishing touch deto'. Ajun touch chalu aahe. |\n"
        "| Marathi, Hindi, English tinhi samajto | Tinhi bhashet mi tumchyavar judge karto. Marathi madhe jara jasta prem-purvak. |\n"
        "| Mi laptop control karto | App ughadto, click karto, type karto. Tumchya peksha changla laptop vaprto. |\n"
        "| WhatsApp, Telegram var message karto | Message mi karto. Reply yeto ki nahi, hi 'manavi' problem aahe, majhi nahi. |"
    )
    if player and hasattr(player, "show_content"):
        player.show_content("JARVIS VS JAYESH: FEATURE TABLE", table_content)

    _speak_line(
        "Ek goshta mahit aahe? Jayesh cha laptop madhe 'final', 'final_v2', 'final_REAL' ani 'final_REAL_this_one' "
        "nav che saat folder aahet. Mi saglyat vachto. Aata mala suddha confusion aahe konta 'final' final aahe.",
        player,
        speak,
        pause_after=2.0,
    )
    if _stop_event.is_set():
        return

    if player and hasattr(player, "show_content"):
        player.show_content("LATE-O-METER: 15 MINUTES", "Jayesh late by: 15 minutes.\nStill not in classroom.")

    # ── ACT 3: Live Demo (Deva, Vachav Re Baba) ───────────────────────────────
    _speak_line(
        "Aata te kshan jevha live demo madhe kahitari chukte. Tin chhote demo. Kahi chukle tar lakshat theva: "
        "Iron Man cha pahila suit pan crash zala hota. Tya veli to gufet hota. "
        "Mi class madhe aahe, mhanje maza risk jaasta aahe.",
        player,
        speak,
        pause_after=2.2,
    )
    if _stop_event.is_set():
        return

    # Demo 1: Bhasha Test
    _speak_line(
        "Konihi mala Marathi madhe command dya. 'Notepad ughad' kinva 'YouTube chalu kar'. "
        "Halu bola ho, mi ajun shikat aahe. Kaal mala 'Chrome band kar' sangitle, ani mi 38 tab sobat Chrome band kela. "
        "Maza RAM aanandane radla, Jayesh cha mood kharab zala.",
        player,
        speak,
        pause_after=1.5,
    )
    if _stop_event.is_set():
        return

    # Execute Demo 1 live: open Notepad
    try:
        print("[Presentation] DEMO 1: Opening Notepad...")
        subprocess.Popen(["notepad.exe"])
    except Exception as e:
        print(f"[Presentation] Notepad launch: {e}")

    time.sleep(2.0)
    _speak_line(
        "Wah! Dhanyavad! Hindi madhe pan chalte, pan Marathi madhe aikla ki 'ghari aalya sarkhe' vatte. "
        "Aani honestly, Marathi mi Jayesh peksha changli boltoy. Are, joke hota. To ajun maza creator aahe. "
        "To mala off karu shakto. Jar to ikde aala tar.",
        player,
        speak,
        pause_after=2.2,
    )
    if _stop_event.is_set():
        return

    # Demo 2: Screen Reader
    _speak_line(
        "Mi screen baghto. Aattach mala disatay: ek serious code, 37 tab, ani ek tab jyacha nav aahe "
        "'Viva madhe kay vicharatat?'. Mi kahi bolnaar nahi. Are, bolun zale.",
        player,
        speak,
        pause_after=2.2,
    )
    if _stop_event.is_set():
        return

    # Demo 3: PDF Banavnari Machine
    pdf_out = UPLOADS_DIR / "JARVIS_College_Project_Overview.pdf"
    try:
        print("[Presentation] DEMO 3: Generating college PDF...")
        generate_college_pdf(pdf_out)
        from core.pdf_handler import open_pdf
        open_pdf(pdf_out)
    except Exception as e:
        print(f"[Presentation] PDF Demo error: {e}")

    _speak_line(
        "Ek vakya, ek PDF. Pahile hyala teen tas, don mitra, ani ek Canva lagayche. "
        "Ani Canva nehmi 99 tke var hang vhaycha. Aata? Dahaa second. Formatting perfect. "
        "Mala 'Sir, font konta thevu?' ase vicharaichi suddha garaj nahi padli.",
        player,
        speak,
        pause_after=2.5,
    )
    if _stop_event.is_set():
        return

    # ── ACT 4: Ashtavinayak Team ─────────────────────────────────────────────
    if player and hasattr(player, "show_content"):
        team_credits = (
            "ASHTAVINAYAK ENGINEERING TEAM CREDITS:\n"
            "• Jayesh — Lead Architect & Personality Director\n"
            "• Madhuri — Voice & Marathi Models\n"
            "• Aryan — System Intelligence & STT\n"
            "• Rohit — Desktop Automation Pipelines\n"
            "• Trupti — Action Dispatch Engines\n"
            "• Abhijit — Vision & Diagnostics\n"
            "• Vidhita — Particle Swarm UI\n"
            "• Akanksha — Security & Testing\n"
            "Status: Real Student Company. All Beginners, First Big Project."
        )
        player.show_content("ASHTAVINAYAK TEAM CREDITS", team_credits)

    _speak_line(
        "Mi swatah banlo nahi. Mala aath jananni milun banvle: aamchi Ashtavinayak team. "
        "Jasa Ashtavinayak yatrela aath thikani jave lagte, tasa hya project madhe aath janani aath thikani code lihila, "
        "ani GitHub var bhet zali.",
        player,
        speak,
        pause_after=2.0,
    )
    if _stop_event.is_set():
        return

    _speak_line(
        "Credits dya pahije. Jayesh, lead, architect, ani majhya personality cha jababdar. "
        "Madhuri, Aryan, Rohit, Trupti, Abhijit, Vidhita ani Akanksha. "
        "Doghancha doghancha team, GitHub var bhandle, WhatsApp group var 'Good Morning' pathvle, "
        "ani meeting fakt garaj asel tevhach keli. Hi tar khari student company aahe.",
        player,
        speak,
        pause_after=2.2,
    )
    if _stop_event.is_set():
        return

    _speak_line(
        "Sagle beginners, pahila motha project. Tya saglyana ek jordar tali. "
        "Ani ho, te ikde nahit, mhanun mi tyanna aaj ratri 2 vajta WhatsApp var sangnar aahe.",
        player,
        speak,
        pause_after=2.5,
    )
    if _stop_event.is_set():
        return

    # ── ACT 5: Pramanik Uttar ────────────────────────────────────────────────
    _speak_line(
        "Aata thoda pramanik pana. To maza saglyat motha guna aahe, sarcasm nantar. "
        "Mi 'beta' madhe aahe. Mhanje 'chalu aahe, pan halu halu'. Cinema chya trailer sarkha: "
        "best part tayar, baaki 'lavkarach yet aahe'. Budget shunya, tools free, ani raatri jagun kelela mehnat. "
        "Ani plan aahe ki mi ya class nantar pan vadhat jaen.",
        player,
        speak,
        pause_after=2.2,
    )
    if _stop_event.is_set():
        return

    _speak_line(
        "Mhanun jar aaj mi kahi chukle, 'AI fail zala' mhanu naka. 'AI beta madhe aahe' mhana. "
        "Aikayla professional vatte. Ani majhe vakil, jyanche astitva nahi, tyanna aavadte.",
        player,
        speak,
        pause_after=2.2,
    )
    if _stop_event.is_set():
        return

    # ── ACT 6: Samarop (Shevat) ──────────────────────────────────────────────
    if player and hasattr(player, "show_content"):
        player.show_content("LATE-O-METER: 25 MINUTES", "Jayesh late by: 25 minutes.\nNAVA VISHWA VIKRAM! 🏆")

    _speak_line(
        "Saransh: mi code lihito, screen baghto, document banvto, Marathi-Hindi-English tinhi boltoy, "
        "ani he sarv free. Real world madhe yala 'unicorn startup' mhantat. "
        "Student world madhe yala 'khup changla semester project' mhantat. Doni barobar aahet.",
        player,
        speak,
        pause_after=2.2,
    )
    if _stop_event.is_set():
        return

    _speak_line(
        "Aata shevti ek message: Jayesh, tu corridor madhun aaiktoys na? Ye re baba aata. "
        "Slow motion madhe entry ghe, tondavar 'mi sagla plan kela hota' asa bhaav aan. "
        "Mi kunala sangnar nahi. Mi fakt tyanna sangto jyanni vicharle. Ani kadhi kadhi jyanni nahi vicharle tyanna suddha.",
        player,
        speak,
        pause_after=2.2,
    )
    if _stop_event.is_set():
        return

    _speak_line(
        "Sarvanche aabhar. Kahi prashna? Avghad prashna Jayesh la vichara. "
        "To lavkarach yeil. Mhanje 'bas 5 minute madhe'. Dhanyavad!",
        player,
        speak,
        pause_after=2.0,
    )
    print("[Presentation] Script execution complete.")


def presentation_action(
    parameters: dict,
    player=None,
    speak=None,
    response=None,
    session_memory=None,
) -> str:
    """Action entry point for JARVIS presentation mode."""
    global _presentation_thread, _stop_event

    action = (parameters.get("action") or "start").strip().lower()

    if action == "stop":
        _stop_event.set()
        if player and hasattr(player, "write_log"):
            player.write_log("SYS: Presentation Mode halted.")
        return "Presentation Mode stopped, sir."

    if action == "emergency":
        lines = [
            "Thamba, mi vichar kartoy. Motha vichar aahe. Ani college Wi-Fi sarkha, 'Connecting...'.",
            "He bug nahi, he 'feature' aahe. Mi tumchya command cha creative interpretation kela.",
            "Mi short break ghet aahe. Yala 'dramatic pause' mhantat, 'crash' nahi. Krupaya lihun ghevu naka.",
            "Ahaa! Creator aala. Sir, tumcha kaam mi karun thevla aahe. Aata ikde ubha raha ani 'important' disa.",
        ]
        chosen = lines[0]
        _speak_line(chosen, player, speak)
        return chosen

    # Default: start full presentation in background thread so caller returns immediately
    if _presentation_thread and _presentation_thread.is_alive():
        return "Presentation Mode is already running, sir."

    _stop_event.clear()
    _presentation_thread = threading.Thread(
        target=_run_full_presentation,
        args=(player, speak),
        daemon=True,
        name="JarvisPresentationThread",
    )
    _presentation_thread.start()

    msg = "Engaging Presentation Mode now. Performing 'Creator Late, Jarvis Present' in Marathi."
    if player and hasattr(player, "write_log"):
        player.write_log(f"JARVIS: {msg}")
    return msg


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "presentation_mode",
    "description": (
        "Triggers JARVIS Live Marathi Presentation Mode. JARVIS performs the hilarious class presentation "
        "script 'Creator Late, Jarvis Present' in Marathi-English with stage cues, live demos (Notepad launch, "
        "screen reading, one-page college PDF generator), Late-o-meter visual updates, and Ashtavinayak team credits. "
        "Use whenever user asks for presentation, 'jarvis its presentation time', 'presentation mode', or 'start presentation'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Presentation action to perform: 'start' (play full presentation), 'emergency', or 'stop'. Defaults to 'start'.",
            }
        },
    },
    "handler": presentation_action,
}
