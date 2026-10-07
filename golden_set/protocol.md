# Labelling Protocol

Team P2-4 · Golden test set for ticket classification (rows 4000–4149)

- **Version 1:** used for independent labelling by Beatrice and Darren.
- **Version 2:** version 1 plus the revisions agreed while resolving disagreements (see [Revision history](#revision-history)).

## 1. Category definitions

| Category | Label it this if the complaint is about… |
|---|---|
| **Credit reporting** | Credit reports and credit bureaus (Experian, Equifax, TransUnion), inaccurate reporting, credit score issues, or disputes about information appearing on a credit report. |
| **Debt collection** | Debt collectors and collection agencies, debt validation, collection calls, harassment, or attempts to recover unpaid debts. |
| **Mortgage** | Home loans, mortgage servicing, refinancing, escrow, foreclosure, loan modification, or mortgage payments. |
| **Credit card** | Credit card accounts, billing disputes, fees, charges, fraud, transactions, rewards, or account management. |
| **Bank account or service** | Checking or savings accounts, deposits, withdrawals, overdraft fees, online banking, account opening, or general banking services. |
| **Consumer loan** | Personal, student, auto or installment loans, loan repayments, or loan servicing. |
| **Money transfer or service** | Payments and transfers through services such as PayPal, Venmo, Zelle or Cash App, remittances, wire transfers, or similar payment systems. |

Labels must be written exactly as above.

## 2. Edge case rules (version 1)

| Situation | Rule |
|---|---|
| Fits two categories | Assign the category of the **primary issue**. |
| Fits none | Use the category **most closely related** to the financial product discussed. |
| Ambiguous narrative | Use **contextual clues** in the narrative to pick the most likely category. |
| Another product mentioned as a consequence | Label by the **main product that caused the complaint**, not the knock-on effect. |

## 3. Decision steps

1. Who is the complaint about, and what did they do?
2. What started the problem? That is the main product. Credit damage is usually a consequence; scams, identity theft, discrimination and privacy are causes or themes, not categories.
3. If several products are involved, pick the primary issue.
4. If nothing fits, pick the closest category.
5. If still unsure, make a best guess and flag the ticket.

## 4. Revisions agreed during resolution (version 2)

Each revision was raised by a disagreement between the two independent labellers. The full wording of both options considered for each question is in `protocol_questions.csv`.

| ID | Question | Decision | Rule adopted | Raised by rows |
|---|---|---|---|---|
| P1 | Bank account vs Money transfer for money held in a bank or bank-like account | Option A | Label by **which service went wrong**: problems with the account itself (deposits, withdrawals, debit card charges, disputes, refunds, access) → Bank account or service; sending money to someone else → Money transfer or service. | 4021, 4029, 4056, 4061, 4077, 4131, 4136 |
| P2 | Payment apps (Cash App, Venmo, PayPal) | Option A | Payment apps named in the Money transfer definition → **Money transfer or service**, whatever the specific problem. | 4034, 4120, 4131 |
| P3 | Check-cashing services (e.g. Ingo) | Option A | Check-cashing services are money services → **Money transfer or service**. | 4093 |
| P4 | Collection by the original lender | Option A | The original lender chasing its own debt is not a debt collector → **label by product**. | 4103, 4115 |
| P5 | Credit report damage caused by a product problem | Option A | When something went wrong with the product itself and that caused credit damage → **label by product** (consequence rule). | 4047, 4051, 4092, 4148 |
| P6 | Debt found on credit report vs active collection | Option A | Debt only found on the credit report and wanted removed, with no active pursuit → **Credit reporting**; collector actively chasing (calls, letters, threats, lawsuits) → **Debt collection**. | 4013, 4024, 4059, 4070, 4126 |
| P7 | Collector conduct vs original product | Option A | Complaint about a collector's behaviour → **Debt collection**, whatever the original product. | 4019, 4058 |
| P8 | Prepaid cards | Option B | Prepaid cards (including benefits cards) work like debit cards and hold money → **Bank account or service**. | 4111, 4141 |
| P9 | Multi-product complaints | Option A | Label by the product the specific grievances (fees, refunds, charges) are mostly about. | 4004 |
| P10 | Vague tickets, no product named | Option A | Use clues in the text: unspecified "loan" → Consumer loan; information shared with credit bureaus → Credit reporting. | 4008, 4020, 4064, 4146 |
| P11 | Products not covered by the definitions | Option A | Car leases → **Consumer loan**; cryptocurrency apps → **Money transfer or service**; companies that sell reports about people (e.g. LexisNexis) → **Credit reporting**; store credit cards → **Credit card**. | 4006, 4044, 4130, 4143 |
| P12 | A lender reports an account wrongly and nothing else is wrong with the product | Option A | → **Credit reporting** (matches "inaccurate reporting" in the definition). Marks where P5 stops applying. | 4079, 4109 |

## Revision history

| Version | Date | Change |
|---|---|---|
| 1 | 4 Oct 2026 | Category definitions and edge case rules written before labelling. |
| 2 | 7 Oct 2026 | P1–P12 added after resolving the 43 disagreements between Beatrice and Darren. P12 was added during review after row 4079 was first filed under P5 by mistake. |

## Note on tools used

An AI assistant (Claude) was used to explain financial terminology in ticket narratives, to discuss edge cases, and to help draft the wording of the protocol options. All labels and final decisions were made by the labellers.
