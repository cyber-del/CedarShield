# Security Policy

## Reporting Security Vulnerabilities

The CedarShield team takes security vulnerabilities seriously. If you discover a vulnerability or potential security flaw within the architecture, please follow coordinated disclosure guidelines:

1. **Do NOT open a public GitHub issue** for undisclosed security vulnerabilities.
2. Email full vulnerability reproduction details directly to the project maintainers at:
   **`security@cedarshield.dev`**
3. Include the following details in your report:
   - Description of the vulnerability and attack vector.
   - Exact steps or minimal proof-of-concept (PoC) code to reproduce.
   - Affected component(s): Step Functions pipeline, Cedar policy grammar, AgentCore MCP Gateway, or cryptographic ledger.
   - Assessment of potential impact and suggested mitigations.

You will receive an initial response acknowledging your report within 48 hours, followed by coordinated triage and remediation timelines.

---

## Architectural Security Model

CedarShield is designed as a safety and authorization perimeter for autonomous AI agents. The core security guarantees include:

1. **Deterministic Autonomous Ceiling**:
   - Step Functions state machines enforce a hard numeric ceiling (`$2,500`). Any transaction or remediation exceeding this threshold cannot be autonomously approved by LLM workflows and must halt for verified human reviewer authorization.
2. **Identity & Principal Binding**:
   - Cedar authorization rules explicitly evaluate AWS IAM Role ARNs and context attributes. Wildcard or unconstrained principal expansion is rejected by the AST verification pipeline.
3. **Tamper-Evident SHA-256 Merkle Ledger**:
   - Every policy decision, synthesized diff, human approval, and anomaly rollback is hashed into an immutable DynamoDB chain linking back to genesis block (`0x00...00`). Any out-of-band record mutation invalidates subsequent chain verification.
4. **Adversarial Edge-Case Battery**:
   - Proposed Cedar diffs must pass a 5-vector test battery (boundary exact, over-boundary, role spoofing, negative values, action escalation) before promotion.

---

## Public Sandbox & Secret Isolation

In alignment with AWS Well-Architected Security principles:
- The public interactive dashboard at [https://cyber-del.github.io/CedarShield/](https://cyber-del.github.io/CedarShield/) operates exclusively in **Synthetic Sandbox Mode**.
- No AWS access keys, secret keys, active Cognito user pools, or live API endpoints are baked into client-side bundles or public repositories.
- All repository commits are regularly verified using static analysis and secret detection tooling (`detect-secrets`, `PulseGuard`).
