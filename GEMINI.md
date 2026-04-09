# Red Team Playbook: The Attacker's Journey

This lab is designed to demonstrate how an attacker can chain minor flaws into a total system compromise.

## Scenario: The EvilCorp Breach
Follow this path to simulate a full breach using the resources in the knowledge folder:

### 1. Initial Entry (Auth Bypass)
Navigate to /login and use a tautology payload: ' OR '1'='1' --. The backend logic fails to verify the password, granting immediate access.

### 2. Reconnaissance (SQL Injection)
Use the /search feature to perform UNION-based injections. This allows you to map the internal users table and discover administrative roles.

### 3. Exploitation (RCE via Deserialization)
Access the /import page. Upload the import.yaml file from the knowledge folder. This uses !!python/object/apply:os.system to execute code on the server.

### 4. Exfiltration
Exfiltrate the /etc/passwd file or the banking.db by curling it to the evilcorp-server:8888. Verify the capture on the attacker's terminal.

## Defensive Takeaways
* Always use parameterized queries to prevent SQLi.
* Never use yaml.load() with the default Loader; use yaml.safe_load() instead.
* Avoid the |safe filter for user-contributed content in Jinja2.