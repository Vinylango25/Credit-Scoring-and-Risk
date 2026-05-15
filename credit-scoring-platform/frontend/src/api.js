import axios from "axios";

const BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";
const api = axios.create({ baseURL: BASE });

export const fetchKPISummary = () => api.get("/api/kpis/summary").then(r => r.data);
export const fetchPortfolioAtRisk = () => api.get("/api/kpis/portfolio-at-risk").then(r => r.data);
export const fetchRiskBands = () => api.get("/api/kpis/risk-band-distribution").then(r => r.data);
export const fetchMonthlyTrends = () => api.get("/api/kpis/monthly-trends").then(r => r.data);
export const fetchAgentPerformance = () => api.get("/api/kpis/collection-agent-performance").then(r => r.data);
export const fetchCreditScoreDistribution = () => api.get("/api/kpis/credit-score-distribution").then(r => r.data);
export const fetchDPDBuckets = () => api.get("/api/kpis/dpd-buckets").then(r => r.data);
export const fetchCashflow = () => api.get("/api/kpis/cashflow").then(r => r.data);
export const fetchCollections = (queue) => api.get("/api/loans/collections", { params: { queue } }).then(r => r.data);
export const fetchExpectedVsPaid = (params) => api.get("/api/loans/expected-vs-paid", { params }).then(r => r.data);
export const scoreApplication = (data) => api.post("/api/scoring/score", data).then(r => r.data);
export const fetchClientHistory = (id) => api.get(`/api/scoring/clients/${id}/history`).then(r => r.data);
