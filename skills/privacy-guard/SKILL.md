---
name: privacy-guard
description: 检测、脱敏、恢复敏感信息。支持批量处理，Luhn校验，多种敏感类型
---
## 工具

### detect / batch_detect / redact / batch_redact / redact_file
检测和脱敏工具

### add_rule / list_rules / restore
自定义规则管理

## 支持的敏感类型
phone, email, id_card_cn, bank_card (Luhn), ssn, ipv4, url, china_passport, china_credit_code, jwt_token

## 实现
D:/github/privacy-guard/privacy_guard.py