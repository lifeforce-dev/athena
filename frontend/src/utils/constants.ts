/**
 * Income events exceeding this dollar amount are treated as paycheck boundaries
 * for pay-period grouping in charts and expense analysis.
 *
 * The backend has a proper is_paycheck flag on commitments, but the projection
 * ledger does not expose it per-entry. This heuristic bridges the gap until
 * the ledger schema includes paycheck markers.
 */
export const PAYCHECK_INCOME_THRESHOLD = 500
