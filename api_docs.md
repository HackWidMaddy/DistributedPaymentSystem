# PhonePay API Documentation

## Base URL
`http://localhost:5000` (API Gateway)

## Authentication
All endpoints (except Auth and Admin) require a JWT token in the `Authorization` header.
`Authorization: Bearer <token>`

## Auth Endpoints

### Login
**POST** `/auth/login`
```json
{
  "email": "user@example.com"
}
```
**Response:**
```json
{
  "token": "jwt_token_here",
  "user": { "user_id": "USR123", "name": "User Name" }
}
```

### Register
**POST** `/auth/register`
```json
{
  "name": "User Name",
  "email": "user@example.com",
  "user_id": "USR123"
}
```

## Payment Endpoints

### Initiate Payment
**POST** `/api/payment/initiate`
```json
{
  "sender_id": "USR123",
  "receiver_id": "USR456",
  "amount": 100.0
}
```
**Response:**
```json
{
  "status": "SUCCESS",
  "transaction_id": "TXN789"
}
```

### Check Status
**GET** `/api/payment/status/<transaction_id>`

### Wallet Balance
**GET** `/api/wallet/balance?user_id=<user_id>`

### Transaction History
**GET** `/api/transactions/history?user_id=<user_id>`

## Admin Endpoints

### Load Balancer Stats
**GET** `/admin/lb-stats`

### System Status
**GET** `/admin/system-status`
