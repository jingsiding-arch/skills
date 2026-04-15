---
name: rent-contract-review
description: Review residential lease and rental contracts from the tenant perspective, identify landlord-favorable clauses, legal and practical risks, missing protections, and negotiation points, then draft concise summaries and replacement clauses. Use when the user asks to 审查租房合同、看出租合同有没有坑、从租客视角找风险、提炼需要争取的权益、逐条批注租赁协议， or provides a housing lease as text, screenshots, .docx, or .pdf for review.
---

# Rent Contract Review

Review the contract as a tenant-protection pass. Prioritize deposit, rent payment, fees, repairs, handover, termination, landlord breach, entry rights, renewal, and proof of ownership or authorization.

## Workflow

1. Extract the contract text.
   - If the input is a `.docx`, use [$docx](/Users/homg/.codex/skills/docx/SKILL.md).
   - If the input is a `.pdf`, use [$pdf](/Users/homg/.codex/skills/pdf/SKILL.md).
   - If the input is screenshots or pasted text, read directly and reconstruct missing context conservatively.
   - If the user asks to 在文档中批注、加底色标记、输出修订版合同, preserve the original file, create a copy, and use [$docx](/Users/homg/.codex/skills/docx/SKILL.md) to add inline review notes or produce a tenant-friendly revised draft.
2. Classify the review.
   - Confirm city if available.
   - Treat the user as the tenant unless the user says otherwise.
   - Note whether the lease is a full-unit rental or shared rental if the contract reveals it.
3. Scan for high-risk clauses first.
   - Deposit forfeiture or vague deduction language.
   - One-sided early termination or immediate repossession clauses.
   - Weak or missing repair obligations.
   - Unclear fee allocation.
   - Missing handover checklist or inventory.
   - Lack of ownership, co-owner consent, or authorization proof.
   - Broad landlord access rights.
   - Missing protection for sale of the property, renewal, or refund timing.
4. Separate issues into three buckets.
   - Clearly unfavorable or risky.
   - Missing terms that should be added.
   - Acceptable but should be clarified with dates, amounts, timelines, or evidence.
5. Draft tenant-facing outputs in practical language.
   - Keep the first summary short.
   - Then provide formal replacement clauses if the user wants contract-ready text.

## Output format

Default to this structure unless the user asks for a different format:

### 1. 结论
Give a 3-8 bullet summary of the biggest risks.

### 2. 有问题的条款
For each issue, include:
- 原条款或其要点
- 风险点
- 对租客的影响
- 建议怎么改

### 3. 建议补充的权益
List missing protections the tenant should negotiate for.

### 4. 可直接替换的正式条款
Draft concise contract language when useful.

### 5. 签约前核对清单
List the documents, photos, meter readings, and signatures the tenant should collect before signing or moving in.

## Review heuristics

Apply these heuristics unless the contract already handles them clearly:

- Do not accept blank fields in identity, address, rent, deposit, term, payment cycle, or notice period.
- Treat “押金不退”, “租金不退”, “甲方概不负责”, or similar blanket clauses as high risk unless narrowly limited to actual proven loss.
- Treat “如有任何损坏” as overbroad if it does not exclude normal wear and tear.
- Require explicit repair responsibility, response timing, and a tenant self-help remedy if the landlord delays.
- Require refund timing for deposit after move-out and settlement.
- Require a handover annex covering furniture, appliances, defects, keys, access cards, and utility meter readings.
- Require clear allocation of water, electricity, gas, property management, internet, parking, and other recurring fees.
- Require lawful rental authority: ownership certificate, co-owner or spouse consent where applicable, or valid authorization if signed by an agent.
- Recommend tenant termination rights when there is title risk, safety risk, major interference with use, refusal to repair, or landlord early repossession.
- Recommend “买卖不破租赁”, priority renewal on equal terms, and advance notice before landlord entry except emergencies.

## Legal grounding

This skill is for practical contract review, not formal legal representation.

When citing current law or local rules, verify using official or primary sources. Prefer current PRC official sources and local government rules for the contract city. If the law or rule may vary by city or has changed, say so explicitly and avoid overclaiming.

## China residential lease checklist

When reviewing a PRC residential lease, read `/Users/homg/.codex/skills/rent-contract-review/references/china-housing-lease-checklist.md` and use it as the default audit checklist. Adapt for the city if local rules differ.

## Annotated document workflow

If the user wants edits on the document itself, use this order:
1. Extract and review the contract first.
2. Mark only the risky or incomplete clauses.
3. Preserve the original file and write to a new filename such as `*-批注版.docx` or `*-修订版.docx`.
4. Prefer concise inline notes, highlighted clauses, or clean replacement text over long commentary.
5. If producing a revised version, keep the original structure and only tighten risky clauses unless the user asks for a full rewrite.

## Clause library

When the user wants contract-ready language, read `/Users/homg/.codex/skills/rent-contract-review/references/clause-library.md` and adapt only the clauses needed for the contract at hand.

## Style

- Write in Chinese unless the user asks otherwise.
- Be direct, practical, and tenant-oriented.
- Prefer short bullets first, then formal clauses.
- Flag assumptions clearly.
- Do not say a clause is illegal unless you are confident and can support it.
