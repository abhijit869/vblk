"""JARVIS Interactive Shell.

Provides an interactive command-line environment for direct communication
with the JARVIS OS Core.
"""

from __future__ import annotations

import cmd
import sys
from typing import Any

from jarvis_core.core import JarvisCore


class JarvisShell(cmd.Cmd):
    intro = "Welcome to JARVIS OS Shell. Type 'help' or '?' to list commands. Type 'exit' to quit.\n"
    prompt = "(jarvis) "

    def __init__(self, core: JarvisCore | None = None) -> None:
        super().__init__()
        self.core = core or JarvisCore()
        self.session_id: str | None = None

    def default(self, line: str) -> None:
        """Handle natural language requests."""
        if not line.strip():
            return

        print(f"JARVIS is thinking...")
        try:
            # We use the agent engine if we want multi-step, but for raw shell we just use handle_text
            # Wait, core.handle_text does the single/multi-tool execution.
            response = self.core.handle_text(line, self.session_id)
            self.session_id = response.get("session_id")
            
            print(f"\n{response.get('answer')}\n")
            
            if response.get("selected_tools"):
                tools = ", ".join(response["selected_tools"])
                print(f"[Tools used: {tools}]")
                
        except Exception as e:
            print(f"[Error: {e}]")

    def do_exit(self, arg: str) -> bool:
        """Exit the JARVIS Shell."""
        print("Goodbye.")
        return True

    def do_quit(self, arg: str) -> bool:
        """Exit the JARVIS Shell."""
        return True

    def do_status(self, arg: str) -> None:
        """Show the current OS monitoring status."""
        print("JARVIS Core is ONLINE.")
        print(f"Session ID: {self.session_id or 'None'}")


def main() -> None:
    try:
        JarvisShell().cmdloop()
    except KeyboardInterrupt:
        print("\nGoodbye.")
        sys.exit(0)

if __name__ == "__main__":
    main()
