import random
import hashlib
from django.core.cache import cache
from .tasks import send_otp_email_task

OTP_EXPIRE_SECONDS = 180

def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        ip = x_forwarded.split(',')[0]
        return ip
def check_ip_rate_limit(ip, num_limit):
    key = f"otp_ip:{ip}"
    block_key = f"otp_ip_block:{ip}"

    if cache.get(block_key):
        return False, "blocked"

    count = cache.get(key, 0)

    if count >= num_limit:
        cache.set(block_key, 1, timeout=300)
        return False, "blocked"

    cache.set(key, count + 1, timeout=60)
    return True, None

def generate_otp():
    return str(random.randint(100000, 999999))


def hash_otp(code: str):
    return hashlib.sha256(code.encode()).hexdigest()


def get_otp_key(email):
    return f"otp:{email}"

def create_and_send_otp(email):
    key = get_otp_key(email)
    key_limit = f"otp_limit:{email}"

    if cache.get(key_limit):
        return False

    raw_code = generate_otp()
    code_hash = hash_otp(raw_code)

    cache.set(key, code_hash, timeout=OTP_EXPIRE_SECONDS)

    # limit resend
    cache.set(key_limit, 1, timeout=60)

    send_otp_email_task.delay(email, raw_code)

    return True

def increase_attempt(email):
    key = f"otp_attempt:{email}"
    attempts = cache.get(key, 0)

    if attempts >= 5:
        return False

    cache.set(key, attempts + 1, timeout=180)
    return True
