import hmac
import hashlib

def verify_webapp_data(init_data: str, bot_token: str) -> bool:
    try:
        from urllib.parse import parse_qs
        parsed = parse_qs(init_data)
        
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            return False
        
        data_pairs = []
        for key_value in init_data.split("&"):
            key = key_value.split("=", 1)[0]
            if key != "hash":
                data_pairs.append(key_value)
        data_pairs.sort()
        data_check_string = "\n".join(data_pairs)
        
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return hmac.compare_digest(computed_hash, received_hash)
    except Exception as e:
        return False

def test_hmac():
    bot_token = "1234567890:FAKE_TOKEN_FOR_TESTING"
    data = "auth_date=1620000000&query_id=AA&user=%7B%22id%22%3A123%7D"
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    
    # Sort keys properly for test valid_hash generation
    pairs = data.split("&")
    pairs.sort()
    test_data_check_string = "\n".join(pairs)
    
    valid_hash = hmac.new(secret_key, test_data_check_string.encode(), hashlib.sha256).hexdigest()
    
    init_data_valid = f"{data}&hash={valid_hash}"
    init_data_invalid = f"{data}&hash=fakehash"
    init_data_no_hash = data
    
    res1 = verify_webapp_data(init_data_valid, bot_token)
    res2 = verify_webapp_data(init_data_invalid, bot_token)
    res3 = verify_webapp_data(init_data_no_hash, bot_token)
    
    print(f"Valid hash: {res1}")
    print(f"Invalid hash: {res2}")
    print(f"No hash: {res3}")

if __name__ == "__main__":
    test_hmac()
