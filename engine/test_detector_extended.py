"""
Test extended detector patterns (v1.5.1)
测试扩展后的敏感信息检测规则
"""
import sys
from pathlib import Path

# Get engine directory
engine_dir = Path(r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine")
sys.path.insert(0, str(engine_dir))

from security.detector import SensitiveDetector, SensitiveCategory

def test_pattern(name: str, text: str, expected_category: SensitiveCategory | None, should_detect: bool = True):
    """Test a single pattern."""
    detector = SensitiveDetector()
    result = detector.scan(text)
    
    if should_detect:
        if not result.is_sensitive:
            print(f"[FAIL] {name} - Expected detection but got none")
            return False
        if expected_category and expected_category not in result.categories:
            print(f"[FAIL] {name} - Expected category {expected_category}, got {result.categories}")
            return False
        print(f"[PASS] {name}")
        return True
    else:
        if result.is_sensitive:
            print(f"[FAIL] {name} - Expected no detection but got {result.items}")
            return False
        print(f"[PASS] {name}")
        return True

def main():
    print("=" * 60)
    print("Extended Detector Pattern Tests (v1.5.1)")
    print("=" * 60)
    
    tests = [
        # API Keys
        ("OpenAI API Key", "sk-abc123XYZ789abcABC456DEF789", SensitiveCategory.API_KEY),
        ("OpenAI Project Key", "sk-proj-abc123_def456_ghi789", SensitiveCategory.API_KEY),
        ("Anthropic API Key", "sk-ant-api03-abc123defghijklmnopqrstuvwxyz1234", SensitiveCategory.API_KEY),
        ("Generic API Key", "api_key: abcdefghijklmnop12345678", SensitiveCategory.API_KEY),
        
        # AWS
        ("AWS Access Key", "AKIAIOSFODNN7EXAMPLE", SensitiveCategory.AWS_KEY),
        ("AWS Secret Key", "aws_secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", SensitiveCategory.AWS_KEY),
        
        # GitHub
        ("GitHub Token", "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", SensitiveCategory.GITHUB_TOKEN),
        ("GitHub Classic Token", "ghp_1234567890abcdef1234567890abcdef12345678", SensitiveCategory.GITHUB_TOKEN),
        
        # Tokens
        ("Bearer Token", "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", SensitiveCategory.ACCESS_TOKEN),
        ("JWT Token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0v", SensitiveCategory.JWT_TOKEN),
        ("Basic Auth", "Basic dXNlcjpwYXNzd29yZA==", SensitiveCategory.ACCESS_TOKEN),
        
        # Passwords & Secrets
        ("Password Assignment", "password: mySecret123", SensitiveCategory.PASSWORD),
        ("Chinese Password", "密码：我的秘密", SensitiveCategory.PASSWORD),
        ("Secret Assignment", "secret: abcdef123456", SensitiveCategory.SECRET),
        
        # PII
        ("Chinese National ID", "11010119900307889X", SensitiveCategory.NATIONAL_ID),
        ("Chinese Phone", "13812345678", SensitiveCategory.PHONE_NUMBER),
        ("Bank Card", "6222021234567890123", SensitiveCategory.BANK_CARD),
        ("Credit Card Visa", "4111111111111111", SensitiveCategory.CREDIT_CARD),
        ("Credit Card Master", "5555555555554444", SensitiveCategory.CREDIT_CARD),
        
        # Private Keys
        ("PEM Private Key", "-----BEGIN RSA PRIVATE KEY-----", SensitiveCategory.PRIVATE_KEY),
        ("OpenSSH Key", "-----BEGIN OPENSSH PRIVATE KEY-----", SensitiveCategory.PRIVATE_KEY),
        
        # Database URLs
        ("MongoDB URL", "mongodb://user:pass@localhost:27017/db", SensitiveCategory.DATABASE_URL),
        ("PostgreSQL URL", "postgresql://user:pass@localhost:5432/db", SensitiveCategory.DATABASE_URL),
        
        # Environment Variables
        ("Env Secret", "SECRET_API_KEY=abcdef123456789", SensitiveCategory.SECRET),
        ("Env Token", "export TOKEN_VALUE=xyz123abc", SensitiveCategory.SECRET),
    ]
    
    passed = 0
    failed = 0
    
    for name, text, category in tests:
        if test_pattern(name, text, category):
            passed += 1
        else:
            failed += 1
    
    # Negative tests
    print("\n--- Negative Tests ---")
    negative_tests = [
        ("Normal Text", "This is just a normal sentence about cats and dogs", None),
        ("Short Number", "12345", None),
        ("Public URL", "https://example.com", None),
    ]
    
    for name, text, category in negative_tests:
        if test_pattern(name, text, category, should_detect=False):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
