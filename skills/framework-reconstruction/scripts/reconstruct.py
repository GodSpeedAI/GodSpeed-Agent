def reconstruction_prompt(failed_doctrine: str) -> str:
    return f"Reconstruct this doctrine from settlement evidence, not preference: {failed_doctrine}"


__all__ = ["reconstruction_prompt"]

