"""
Test extended detector patterns (v1.5.1)
"""
import sys
from pathlib import Path

engine_dir = Path(r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine")
sys.path.insert(0, str(engine_dir))

from security.detector import SensitiveDetector, SensitiveCategory

def test_pattern(name: str, text: str, expected_category: SensitiveCategory | None, should_detect: bool = True):
    detector = SensitiveDetector()
    result = detector.scan(text)
    
    if should_detect:
        if not result.is_sensitive:
            return False, f"Expected detection but got none"
        if expected_category and expected_category not in result.categories:
            return False, f"Expected category {expected_category}, got {result.categories}"
        return True, f"Detected: {result.items[0].pattern_name}"
    else:
        if result.is_sensitive:
            return False, f"Expected no detection but got {result.items}"
        return True, "No detection"

def main():
    with open(r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\detector_test_result.txt", "w", encoding="utf-8") as log:
        log.write("=" * 60 + "\n")
        log.write("Extended Detector Pattern Tests (v1.5.1)\n")
        log.write("=" * 60 + "\n\n")
        
        tests = [
            ("OpenAI API Key", "sk-abc123XYZ789abcABC456DEF789", SensitiveCategory.API_KEY),
            ("OpenAI Project Key", "sk-proj-abc123_def456_ghi789", SensitiveCategory.API_KEY),
            ("Anthropic API Key", "sk-ant-api03-abc123defghijklmnopqrstuvwxyz1234", SensitiveCategory.API_KEY),
            ("Generic API Key", "api_key: abcdefghijklmnop12345678", SensitiveCategory.API_KEY),
            ("AWS Access Key", "AKIAIOSFODNN7EXAMPLE", SensitiveCategory.AWS_KEY),
            ("AWS Secret Key", "aws_secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", SensitiveCategory.AWS_KEY),
            ("GitHub Token", "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", SensitiveCategory.GITHUB_TOKEN),
            ("Bearer Token", "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", SensitiveCategory.ACCESS_TOKEN),
            ("JWT Token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0v", SensitiveCategory.JWT_TOKEN),
            ("Password Assignment", "password: mySecret123", SensitiveCategory.PASSWORD),
            ("Chinese National ID", "11010119900307889X", SensitiveCategory.NATIONAL_ID),
            ("Chinese Phone", "13812345678", SensitiveCategory.PHONE_NUMBER),
            ("Bank Card", "6222021234567890123", SensitiveCategory.BANK_CARD),
            ("Credit Card Visa", "4111111111111111", SensitiveCategory.CREDIT_CARD),
            ("PEM Private Key", "-----BEGIN RSA PRIVATE KEY-----", SensitiveCategory.PRIVATE_KEY),
            ("MongoDB URL", "mongodb://user:pass@localhost:27017/db", SensitiveCategory.DATABASE_URL),
            ("Env Secret", "SECRET_API_KEY=abcdef123456789", SensitiveCategory.SECRET),
        ]
        
        passed = 0
        failed = 0
        
        for name, text, category in tests:
            ok, msg = test_pattern(name, text, category)
            status = "PASS" if ok else "FAIL"
            log.write(f"[{status}] {name}: {msg}\n")
            if ok:
                passed += 1
            else:
                failed += 1
        
        # Negative tests
        log.write("\n--- Negative Tests ---\n")
        negative_tests = [
            ("Normal Text", "This is just a normal sentence", None),
            ("Short Number", "12345", None),
        ]
        
        for name, text, category in negative_tests:
            ok, msg = test_pattern(name, text, category, should_detect=False)
            status = "PASS" if ok else "FAIL"
            log.write(f"[{status}] {name}: {msg}\n")
            if ok:
                passed += 1
            else:
                failed += 1
        
        log.write("\n" + "=" * 60 + "\n")
        log.write(f"Results: {passed} passed, {failed} failed\n")
        log.write("=" * 60 + "\n")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
