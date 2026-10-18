"""Compare actual returned hardware/native buses; never select a silent fallback."""


def compare(hardware: list[dict], native: list[dict]) -> dict:
    if len(hardware) != len(native):
        return {
            "equal": False,
            "first_difference": {
                "field": "record_count",
                "hardware": len(hardware),
                "assembly": len(native),
            },
        }
    for index, (hw, asm) in enumerate(zip(hardware, native, strict=True)):
        for bus, (left, right) in enumerate(
            zip(hw["buses"], asm["buses"], strict=True)
        ):
            if left != right:
                return {
                    "equal": False,
                    "first_difference": {
                        "index": index,
                        "field": f"B{bus}",
                        "hardware": left,
                        "assembly": right,
                    },
                }
    return {"equal": True, "first_difference": None}
