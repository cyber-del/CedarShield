// CedarShield API & Cognito Integration Service
export const API_BASE_URL = "/api";

export const COGNITO_CONFIG = {
  region: "ap-southeast-2",
  userPoolId: "ap-southeast-2_QGbPPwecZ",
  clientId: "5v5di986mlbftuo81vvspu1qcd",
};

// ----------------------------------------------------------------------------
// 1. Amazon Cognito Authentication
// ----------------------------------------------------------------------------
export async function authenticateCognitoUser(username, password) {
  const cognitoEndpoint = `https://cognito-idp.${COGNITO_CONFIG.region}.amazonaws.com/`;
  
  const payload = {
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: COGNITO_CONFIG.clientId,
    AuthParameters: {
      USERNAME: username,
      PASSWORD: password,
    },
  };

  const response = await fetch(cognitoEndpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.message || data.__type || "Cognito authentication failed");
  }

  const authResult = data.AuthenticationResult;
  if (!authResult) {
    throw new Error("No AuthenticationResult in Cognito response");
  }

  // Parse ID Token claims
  const idToken = authResult.IdToken;
  const payloadBase64 = idToken.split(".")[1];
  const normalizedBase64 = payloadBase64.replace(/-/g, "+").replace(/_/g, "/");
  const claims = JSON.parse(atob(normalizedBase64));

  const session = {
    idToken: authResult.IdToken,
    accessToken: authResult.AccessToken,
    refreshToken: authResult.RefreshToken,
    tokenType: authResult.TokenType,
    expiresIn: authResult.ExpiresIn,
    email: claims.email || username,
    sub: claims.sub,
    claims,
    authenticatedAt: new Date().toISOString(),
  };

  localStorage.setItem("cedarshield_cognito_session", JSON.stringify(session));
  return session;
}

export function getStoredSession() {
  try {
    const raw = localStorage.getItem("cedarshield_cognito_session");
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearStoredSession() {
  localStorage.removeItem("cedarshield_cognito_session");
}

// ----------------------------------------------------------------------------
// 2. Real Backend API Calls (via Local Proxy to AWS Live Services)
// ----------------------------------------------------------------------------
export async function triggerDenial(payload) {
  const response = await fetch(`${API_BASE_URL}/trigger-denial`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || data.error || `Failed with HTTP ${response.status}`);
  }
  return data;
}

export async function fetchAuditLog() {
  const response = await fetch(`${API_BASE_URL}/audit-log`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || data.error || `Failed with HTTP ${response.status}`);
  }
  return data.runs || data.items || [];
}

export async function approvePatch(runId, idToken) {
  const headers = {
    "Content-Type": "application/json",
  };
  if (idToken) {
    headers["Authorization"] = `Bearer ${idToken}`;
  }

  const response = await fetch(`${API_BASE_URL}/approve`, {
    method: "POST",
    headers,
    body: JSON.stringify({ run_id: runId }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || data.error || `Approval rejected with HTTP ${response.status}`);
  }
  return data;
}

export async function rejectPatch(runId, reason, idToken) {
  const headers = {
    "Content-Type": "application/json",
  };
  if (idToken) {
    headers["Authorization"] = `Bearer ${idToken}`;
  }

  const response = await fetch(`${API_BASE_URL}/reject`, {
    method: "POST",
    headers,
    body: JSON.stringify({ run_id: runId, reason }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || data.error || `Rejection rejected with HTTP ${response.status}`);
  }
  return data;
}

// ----------------------------------------------------------------------------
// 3. Cryptographic Hash Chain Verifier
// ----------------------------------------------------------------------------
export async function verifyAuditChainServer() {
  const response = await fetch(`${API_BASE_URL}/verify-audit-chain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || data.error || `Verification failed with HTTP ${response.status}`);
  }
  return data;
}

export async function simulateAbuseAndRollback(amounts = [2450, 2480, 2490]) {
  const response = await fetch(`${API_BASE_URL}/simulate-abuse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ amounts }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || data.error || `Anomaly simulation failed with HTTP ${response.status}`);
  }
  return data;
}

export async function fetchKpis() {
  const response = await fetch(`${API_BASE_URL}/kpis`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `KPI fetch failed with HTTP ${response.status}`);
  }
  return data.kpis || {
    active_agents: 2,
    policy_violations: 3,
    auto_remediable: 2,
    pending_approval: 1,
  };
}
