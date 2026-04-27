export type ApplicationStatus =
  | "draft"
  | "applied"
  | "interview"
  | "offer"
  | "rejected";

export type Profile = {
  id: string;
  fullName: string;
  email: string;
  headline?: string;
  baseResumeId?: string;
  createdAt: string;
};

export type Resume = {
  id: string;
  title: string;
  /** If this resume was tailored to an application, link back. */
  applicationId?: string;
  isBase?: boolean;
  content: string;
  createdAt: string;
};

export type GapItem = {
  skill: string;
  severity: "low" | "medium" | "high";
  note?: string;
};

export type Application = {
  id: string;
  company: string;
  position: string;
  jobUrl?: string;
  jobDescription: string;
  matchScore: number;
  status: ApplicationStatus;
  resumeId?: string;
  coverLetter?: string;
  gaps?: GapItem[];
  createdAt: string;
};

export type DashboardStats = {
  applications: number;
  interviews: number;
  averageMatchScore: number;
  resumesGenerated: number;
};

export type TailorRequest = {
  jobUrl?: string;
  jobDescription?: string;
  baseResumeId: string;
};

export type MatchAnalysis = {
  originalScore: number;
  tailoredScore: number;
  improvement: number;
  /** Bullet points describing what was changed/improved */
  whatWeImproved: string[];
  strengths: string[];
  remainingDeficits: string[];
  matchedKeywords: string[];
  missingKeywords: string[];
  suggestions: string[];
};

export type DraftEmail = {
  subject: string;
  body: string;
};

export type TailorResponse = {
  applicationId: string;
  matchScore: number;
  resume: Resume;
  coverLetter: string;
  draftEmail: DraftEmail;
  gaps: GapItem[];
  analysis: MatchAnalysis;
};

export type EntitlementLimits = {
  monthlyLlmTokenBudget: number;
  monthlyApplicationLimit: number;
  monthlyBaseResumeLimit: number;
};

export type EntitlementUsage = {
  llmPromptTokens: number;
  llmCompletionTokens: number;
  totalLlmTokens: number;
  applicationsCreated: number;
  baseResumeUploads: number;
};

export type Entitlements = {
  plan: string;
  period: string;
  limits: EntitlementLimits;
  usage: EntitlementUsage;
};
