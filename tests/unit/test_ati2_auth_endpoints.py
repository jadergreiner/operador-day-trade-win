"""
Testes para OAuth/JWT Endpoints
Validação de 5 Acceptance Criteria (AC-5.1 até AC-5.5)
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from src.application.auth_endpoints_ati2 import router
from src.application.token_manager_ati2 import TokenManager

# Criar aplicação de teste
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestAuthEndpoints:
    """Testes para endpoints de autenticação OAuth/JWT"""
    
    def test_login_success(self):
        """AC-5.1: Login com credenciais válidas retorna access + refresh tokens"""
        response = client.post("/auth/login", json={
            "username": "trader01",
            "password": "SecurePass123!"
        })
        
        assert response.status_code == 200, f"Status inválido: {response.status_code}"
        data = response.json()
        
        assert "access_token" in data, "access_token ausente"
        assert "refresh_token" in data, "refresh_token ausente"
        assert data["token_type"] == "bearer", f"token_type inválido: {data.get('token_type')}"
        assert data["expires_in"] > 0, f"expires_in inválido: {data.get('expires_in')}"
        
        print(f"✅ AC-5.1 PASSED: Login com tokens válidos")
    
    def test_login_invalid_username(self):
        """AC-5.1: Login com username inválido retorna 401"""
        response = client.post("/auth/login", json={
            "username": "usuario_inexistente",
            "password": "SecurePass123!"
        })
        
        assert response.status_code == 401, f"Status deveria ser 401, got {response.status_code}"
        assert "Credenciais inválidas" in response.text
        
        print(f"✅ AC-5.1 PASSED: Login com username inválido rejeitado")
    
    def test_login_invalid_password(self):
        """AC-5.1: Login com password inválida retorna 401"""
        response = client.post("/auth/login", json={
            "username": "trader01",
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == 401, f"Status deveria ser 401, got {response.status_code}"
        assert "Credenciais inválidas" in response.text
        
        print(f"✅ AC-5.1 PASSED: Login com password inválida rejeitado")
    
    def test_refresh_token_success(self):
        """AC-5.2: Refresh token com token válido retorna novo access token"""
        # 1. Fazer login
        login_response = client.post("/auth/login", json={
            "username": "trader01",
            "password": "SecurePass123!"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # 2. Usar refresh token
        response = client.post("/auth/refresh-token", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200, f"Status: {response.status_code}"
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        print(f"✅ AC-5.2 PASSED: Refresh token sucesso")
    
    def test_refresh_token_invalid(self):
        """AC-5.2: Refresh token com token inválido retorna 401"""
        response = client.post("/auth/refresh-token", json={
            "refresh_token": "invalid_token_xyz"
        })
        
        assert response.status_code == 401, f"Status: {response.status_code}"
        
        print(f"✅ AC-5.2 PASSED: Refresh token inválido rejeitado")
    
    def test_protected_endpoint_with_valid_token(self):
        """AC-5.4 + AC-5.5: Endpoint protegido com token válido retorna user info"""
        # 1. Fazer login
        login_response = client.post("/auth/login", json={
            "username": "trader01",
            "password": "SecurePass123!"
        })
        access_token = login_response.json()["access_token"]
        
        # 2. Acessar endpoint protegido
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 200, f"Status: {response.status_code}"
        data = response.json()
        
        assert data["username"] == "trader01", f"username: {data.get('username')}"
        assert data["user_id"] == "user_001", f"user_id: {data.get('user_id')}"
        assert data["role"] == "trader", f"role: {data.get('role')}"
        assert "issued_at" in data, "issued_at ausente"
        assert "expires_at" in data, "expires_at ausente"
        
        print(f"✅ AC-5.4 PASSED: JWT com claims corretos (sub, user_id, role, iat, exp)")
    
    def test_protected_endpoint_without_token(self):
        """AC-5.5: Endpoint protegido sem token retorna 401"""
        response = client.get("/auth/me")
        
        assert response.status_code == 401, f"Status deveria ser 401, got {response.status_code}"
        assert "Token ausente" in response.text or "ausente" in response.text.lower()
        
        print(f"✅ AC-5.5 PASSED: Requisição sem token → 401 Unauthorized")
    
    def test_protected_endpoint_invalid_token(self):
        """AC-5.5: Endpoint protegido com token inválido retorna 401"""
        headers = {"Authorization": "Bearer invalid_token_xyz123"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401, f"Status: {response.status_code}"
        
        print(f"✅ AC-5.5 PASSED: Token inválido → 401 Unauthorized")
    
    def test_protected_endpoint_malformed_authorization(self):
        """AC-5.5: Authorization header malformed retorna 401"""
        headers = {"Authorization": "InvalidFormat token"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == 401, f"Status: {response.status_code}"
        
        print(f"✅ AC-5.5 PASSED: Authorization malformed → 401")
    
    def test_logout_endpoint(self):
        """AC-5.3: Logout invalida token na blacklist"""
        # 1. Fazer login
        login_response = client.post("/auth/login", json={
            "username": "trader01",
            "password": "SecurePass123!"
        })
        access_token = login_response.json()["access_token"]
        
        # 2. Fazer logout
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.post("/auth/logout", headers=headers)
        
        assert response.status_code == 200, f"Status: {response.status_code}"
        data = response.json()
        assert "Logout realizado com sucesso" in data["message"]
        assert "timestamp" in data
        
        print(f"✅ AC-5.3 PASSED: Logout endpoint funcional")
    
    def test_admin_user_login(self):
        """Teste com usuário admin"""
        response = client.post("/auth/login", json={
            "username": "admin01",
            "password": "AdminPass123!"
        })
        
        assert response.status_code == 200, f"Status: {response.status_code}"
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        
        # Usar token para acessar /me
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        me_response = client.get("/auth/me", headers=headers)
        
        assert me_response.status_code == 200
        assert me_response.json()["role"] == "admin"
        
        print(f"✅ Admin user login: PASSED")
    
    def test_health_check(self):
        """Teste endpoint health check"""
        response = client.get("/auth/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "auth"
        
        print(f"✅ Health check: PASSED")


if __name__ == "__main__":
    # Rodar testes
    pytest.main([__file__, "-v", "-s"])
