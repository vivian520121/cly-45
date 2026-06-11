"""彩色日志模块"""

import sys
from colorama import init, Fore, Style

init(autoreset=True)


class Logger:
    @staticmethod
    def info(msg: str) -> None:
        print(f"{Fore.CYAN}[INFO] {Style.RESET_ALL}{msg}")

    @staticmethod
    def success(msg: str) -> None:
        print(f"{Fore.GREEN}[SUCCESS] {Style.RESET_ALL}{msg}")

    @staticmethod
    def warning(msg: str) -> None:
        print(f"{Fore.YELLOW}[WARNING] {Style.RESET_ALL}{msg}")

    @staticmethod
    def error(msg: str) -> None:
        print(f"{Fore.RED}[ERROR] {Style.RESET_ALL}{msg}", file=sys.stderr)

    @staticmethod
    def dry_run(msg: str) -> None:
        print(f"{Fore.MAGENTA}[DRY-RUN] {Style.RESET_ALL}{msg}")

    @staticmethod
    def skip(msg: str) -> None:
        print(f"{Fore.LIGHTBLACK_EX}[SKIP] {Style.RESET_ALL}{msg}")


logger = Logger()
