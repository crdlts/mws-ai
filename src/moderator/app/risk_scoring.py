def calculate_risk(secret: str, path: str, llm_verdict: str, llm_conf: float):
    risk = 0.0
    reasons = []

    if llm_verdict == "TP":
        risk += llm_conf
        reasons.append("llm_thinks_real_secret")

    if any(x in path.lower() for x in ["auth", "token", "secrets"]):
        risk += 0.3
        reasons.append("sensitive_path")

    if secret.startswith("AKIA") or len(secret) > 30:
        risk += 0.3
        reasons.append("format_looks_sensitive")

    return min(risk, 1.0), reasons
