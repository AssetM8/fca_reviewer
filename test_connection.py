from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.insert(0, ".")
from backend.commentary import _call_kimi

print("Sending test message to Kimi-K2.5...")
result = _call_kimi("Say hello in one sentence.")
print("Response:", result)