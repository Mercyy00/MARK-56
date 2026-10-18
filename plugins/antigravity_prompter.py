"""
plugins/antigravity_prompter.py — Antigravity Prompt Engineering & IDE Integration for JARVIS

Enables JARVIS to formulate master-level prompts for Google Antigravity agents,
incorporating slash commands (/goal, /plan, /boost, /grill-me), structured XML tags,
and technical constraints, and automatically deliver/paste them directly into
the active Antigravity IDE window or copy them to the clipboard.
"""

from pathlib import Path
from core import antigravity_engine

PLUGIN = {
    "name": "antigravity_prompter",
    "description": (
        "Formulate high-impact, prompt-engineered directives specifically for Google Antigravity "
        "agents and write or paste them directly into the active Antigravity IDE chat window. "
        "Leverages Antigravity slash commands (/goal, /plan, /boost, /grill-me, /learn) and saves "
        "prompt copies to Desktop/Antigravity_Prompts."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "user_goal": {
                "type": "STRING",
                "description": "The coding task, feature, bug fix, or refactoring objective to prompt Antigravity with."
            },
            "slash_command": {
                "type": "STRING",
                "description": "Optional Antigravity slash command: 'plan', 'goal', 'boost', 'grill-me', 'schedule', 'learn'."
            },
            "auto_deliver": {
                "type": "BOOLEAN",
                "description": "If true (default), focuses the Antigravity IDE window and pastes the prompt into the chat box."
            },
            "auto_submit": {
                "type": "BOOLEAN",
                "description": "If true, submits the prompt automatically by pressing Enter. Defaults to false for safe review."
            },
            "save_file": {
                "type": "BOOLEAN",
                "description": "If true (default), saves a copy of the prompt to Desktop/Antigravity_Prompts/."
            }
        },
        "required": ["user_goal"]
    }
}


def run(parameters: dict, player=None, session_memory=None) -> str:
    user_goal = parameters.get("user_goal", "")
    if not user_goal.strip():
        return "Sir, please specify the objective or task you want me to prompt Antigravity with."

    slash_cmd = parameters.get("slash_command")
    auto_deliver = parameters.get("auto_deliver", True)
    auto_submit = parameters.get("auto_submit", False)
    save_to_disk = parameters.get("save_file", True)

    try:
        # 1. Engineer prompt for Antigravity
        prompt_text = antigravity_engine.engineer_antigravity_prompt(user_goal, slash_command=slash_cmd)

        saved_path_str = ""
        # 2. Save prompt to file if requested
        if save_to_disk:
            saved_file = antigravity_engine.save_prompt(prompt_text, title=user_goal[:30])
            saved_path_str = f" Saved a copy to '{saved_file.name}'."

        # 3. Deliver to IDE or clipboard
        if auto_deliver:
            success, delivery_msg = antigravity_engine.paste_to_antigravity(prompt_text, auto_submit=auto_submit)
            res = f"Sir, I have engineered your Antigravity prompt. {delivery_msg}{saved_path_str}"
        else:
            if antigravity_engine._PYPERCLIP:
                antigravity_engine.pyperclip.copy(prompt_text)
            res = f"Sir, I have engineered your Antigravity prompt and copied it to your clipboard.{saved_path_str}"

        if player:
            try:
                player.write_log(f"JARVIS: {res}")
            except Exception:
                pass

        return res

    except Exception as e:
        err = f"Sir, Antigravity prompter failed: {e}"
        if player:
            try:
                player.write_log(f"JARVIS: {err}")
            except Exception:
                pass
        return err
