# Banking Security Lab: Architectural Overview

This repository contains a full-stack, containerized banking application designed for security training and penetration testing simulations.

## System Architecture
The environment is composed of three primary services orchestrated via Docker Compose:

* Banking App: A Flask-based web application (Python 3.11) utilizing Blueprints for modularity (Auth, Transactions, AI, Feedback).
* Database: A PostgreSQL 15 instance containing user data, transaction histories, and specialized roles.
* EvilCorp C2: A malicious Command & Control server designed to simulate an attacker's data collection point.

## Targeted Vulnerabilities
This lab provides specific scenarios to test the following critical risks:

1. Broken Authentication: A critical logic flaw in user.py allows for a complete login bypass via SQL injection.
2. Insecure Deserialization: The /import endpoint handles YAML, JSON, and Python scripts using unsafe methods (yaml.load, eval, exec), leading to RCE.
3. Injection Attacks: Demonstration of Command Injection in file exports and UNION-based SQLi in search queries.
4. Cross-Site Scripting (XSS): Use of the |safe filter in templates like feedback_detail.html facilitates stored XSS.

## Instructional Guidance
When a student interacts with the CLI:
* Hinting: Do not give the answer immediately; never give the line number first. Provide hints about the file location. Point to the service (e.g., "Check how the EvilCorp service communicates with the Banking app").
* Explaining: Always link the bug to its CWE category. For architecture, explain the real-world banking risk (e.g., "Insecure service orchestration could allow an attacker to bypass network segmentation").

## Security Automation
The project includes GitHub Actions that leverage the pr-bouncer workflow to perform automated security reviews using Semgrep rules (OWASP Top 10, Javascript, TypeScript).