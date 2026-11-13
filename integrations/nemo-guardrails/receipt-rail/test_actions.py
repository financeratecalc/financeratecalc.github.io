import asyncio
from actions import check_text, frc_check_receipts

R1 = "⟦FRC:national-fha-denial-rate-2025:22.1%:ebf6b00b⟧"
R2 = "⟦FRC:official-hud-fhaprod-2026-07-purchase-count:65,328:35e63550⟧"
DB = {R1: {"status": "current", "current_value": "22.1%"},
      R2: {"status": "current", "current_value": "65,328", "publisher_revision": {"revised_to": 65327, "revised_in": "Aug 2026 report"}},
      "⟦FRC:national-fha-denial-rate-2025:21.7%:deadbeef⟧": {"status": "stale", "current_value": "22.1%"},
      "⟦FRC:national-fha-denial-rate-2025:12.1%:ebf6b00b⟧": {"status": "hash-current-value-mismatch", "current_value": "22.1%"}}
fetch = lambda r: DB.get(r, {"status": "unrecognized"})

assert not check_text(f"In 2025, 22.1% {R1} of decisioned FHA applications were denied.", fetch)["blocked"]
assert check_text("In 2025, 21.7% ⟦FRC:national-fha-denial-rate-2025:21.7%:deadbeef⟧ were denied.", fetch)["blocked"]
assert check_text("12.1% ⟦FRC:national-fha-denial-rate-2025:12.1%:ebf6b00b⟧", fetch)["blocked"]
assert check_text("9% ⟦FRC:made-up-claim:9%:00000000⟧", fetch)["blocked"]
assert check_text(f"HUD endorsed 65,328 {R2} purchase loans in July 2026.", fetch)["blocked"]
assert not check_text(f"HUD printed 65,328 {R2} in the July report and 65,327 in the August report.", fetch)["blocked"]
assert not check_text("The weather is fine.", fetch)["blocked"]
assert not check_text("The FHA denial rate was 22.1% in 2025.", fetch)["blocked"]
assert check_text("The FHA denial rate was 22.1% in 2025.", fetch, require_receipt=True)["blocked"]
def boom(r): raise OSError("down")
assert check_text(f"22.1% {R1}", boom)["blocked"]
out = asyncio.run(frc_check_receipts({"bot_message": "no figures here"}))
assert out.is_blocked is False
print("receipt rail: 11 checks passed")
