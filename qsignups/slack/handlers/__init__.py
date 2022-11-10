from dataclasses import dataclass

@dataclass
class UpdateResponse:
  success: bool
  message: str = ""