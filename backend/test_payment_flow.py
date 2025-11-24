import requests
import time
import uuid

GATEWAY_URL = "http://localhost:5000"

def test_payment_flow():
    print("--- Starting End-to-End Payment Test ---")
    
    # 1. Register Users
    sender_id = f"USR_{uuid.uuid4().hex[:6]}"
    receiver_id = f"USR_{uuid.uuid4().hex[:6]}"
    
    print(f"Registering Sender: {sender_id}")
    requests.post(f"{GATEWAY_URL}/auth/register", json={
        "name": "Sender", "email": f"{sender_id}@test.com", "user_id": sender_id
    })
    
    print(f"Registering Receiver: {receiver_id}")
    requests.post(f"{GATEWAY_URL}/auth/register", json={
        "name": "Receiver", "email": f"{receiver_id}@test.com", "user_id": receiver_id
    })
    
    # 2. Login (Get Token)
    print("Logging in Sender...")
    login_res = requests.post(f"{GATEWAY_URL}/auth/login", json={"email": f"{sender_id}@test.com"})
    token = login_res.json()['token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Check Initial Balance
    print("Checking Initial Balance...")
    bal_res = requests.get(f"{GATEWAY_URL}/api/wallet/balance?user_id={sender_id}", headers=headers)
    print(f"Sender Balance: {bal_res.json()['balance']}")
    
    # 4. Initiate Payment
    amount = 100.0
    print(f"Initiating Payment of {amount}...")
    pay_res = requests.post(f"{GATEWAY_URL}/api/payment/initiate", json={
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "amount": amount
    }, headers=headers)
    
    print(f"Payment Response: {pay_res.json()}")
    transaction_id = pay_res.json().get('transaction_id')
    
    if not transaction_id:
        print("FAILED: No transaction ID returned")
        return

    # 5. Wait for Async Processing
    print("Waiting for async processing...")
    time.sleep(2)
    
    # 6. Check Final Status
    print("Checking Final Status...")
    status_res = requests.get(f"{GATEWAY_URL}/api/payment/status/{transaction_id}", headers=headers)
    print(f"Transaction Status: {status_res.json()}")
    
    # 7. Check Receiver Balance
    print("Checking Receiver Balance...")
    # Login as receiver to check balance (or just use sender token if admin/open)
    # For simplicity, using same token as our mock gateway allows it or we just check via wallet service directly if we could
    # But let's stick to gateway
    rec_bal_res = requests.get(f"{GATEWAY_URL}/api/wallet/balance?user_id={receiver_id}", headers=headers)
    print(f"Receiver Balance: {rec_bal_res.json()['balance']}")
    
    if rec_bal_res.json()['balance'] == 100.0: # 0 + 100
        print("✅ TEST PASSED: Receiver got the money")
    else:
        print("❌ TEST FAILED: Receiver balance incorrect")

if __name__ == "__main__":
    try:
        test_payment_flow()
    except Exception as e:
        print(f"❌ TEST FAILED with Exception: {e}")
