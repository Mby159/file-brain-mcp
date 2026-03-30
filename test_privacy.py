from privacy_guard import PrivacyGuard

guard = PrivacyGuard()

print("=== Testing new patterns ===")
result = guard.detect(
    "银行卡6222021234567890123，JWT eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)
print("Bank card + JWT:", [r["info_type"] for r in result])

print("\n=== Testing Luhn validation ===")
cards = [
    ("Valid Visa", "4532015112830366"),
    ("Invalid", "1234567890123456"),
]
for name, card in cards:
    result = guard.detect(f"卡号: {card}")
    found = [r["info_type"] for r in result]
    print(f"{name}: {card[:6]}... -> {found}")

print("\n=== Testing redact-file ===")
print("Config example:")
print(guard.export_config_example())
