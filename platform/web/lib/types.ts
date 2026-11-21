export type Role = "student" | "teacher" | "admin" | "network";

export type RubricCriterion = { id: string; label: string; descriptors?: Record<string, string> };
export type RubricSnapshot = {
  version: number; competency_id: string; competency: string; focus: string;
  criteria: RubricCriterion[]; scale: { min: number; max: number; meaning: string }; notice: string;
};
export type ItemCompetency = { id: string; name: string; rubric: RubricSnapshot };
export type OpenItem = { id: string; stem: string; stimulus: Stimulus | null; competencies?: ItemCompetency[] };
export type OpenAssignmentDraft = { item_id: string; title: string; instructions?: string; course_id?: string; due_at?: string; competency_id?: string };
export type OpenAssignment = {
  id: string; item_id: string; title: string; instructions: string; due_at: string | null;
  created_at: string; submission_id?: string | null; status?: "pendiente" | "corregida" | null;
  score?: number | null; feedback?: string | null; rubric?: Record<string, number> | null;
  competency_id?: string | null; rubric_snapshot?: RubricSnapshot | null; item?: OpenItem | null;
  submissions?: number; pending?: number; expired?: boolean;
};
export type OpenSubmission = {
  id: string; student_label: string; student_name?: string; response: string; status: "pendiente" | "corregida";
  score: number | null; feedback: string | null; rubric: Record<string, number> | null;
  competency_id?: string | null; rubric_snapshot?: RubricSnapshot | null; submitted_at: string;
};

export type TableStimulus = { type: "table"; header: string[]; rows: string[][] };
export type ChartStimulus = { type: "bar_chart" | "line_chart"; title: string; x_label: string; y_label: string; categories: string[]; values: number[] };
export type RectStimulus = { type: "rect"; width: number; height: number; unit: string };
export type Stimulus = TableStimulus | ChartStimulus | RectStimulus;

export type PublicItem = {
  id: string;
  stem: string;
  kind: "choice" | "numeric" | "expression" | "open";
  stimulus: Stimulus | null;
  options: { id: string; text: string }[];
};

export type SessionState = {
  done: boolean; answered: number; total: number; mode?: string; items: PublicItem[];
  correct?: boolean; duplicate?: boolean; explanation?: string[];
};
export type StartOut = SessionState & { session_id: string };

export type LadderStep = { level: number; descriptor: string };

export type Mistake = { stem: string; answer: string; steps: string[] };

export type Report = {
  kind?: "mst" | "dirigida" | "piloto";
  skill?: string; skill_name?: string; correct?: number; mistakes?: Mistake[];
  theta: number;
  se: number;
  level: number;
  descriptor: string;
  at_or_above_baseline: boolean;
  answered: number;
  error_tags: Record<string, number>;
  ladder: LadderStep[];
  preliminary: boolean;
  note: string;
};

export type Cohort = { levels: Record<string, number>; n: number; baseline_level: number; ladder: LadderStep[] };

export type ReviewTemplate = {
  id: string; title: string; level: number; axis: string; process: string;
  n_items: number; n_approved: number; status: "pendiente" | "aprobada" | "rechazada";
  approvals: number; rejections: number; required: number; reviewed_by_me: boolean;
};
export type ReviewList = { templates: ReviewTemplate[]; required_approvals: number };
export type ReviewItemData = {
  id: string; stem: string; kind: PublicItem["kind"]; stimulus: Stimulus | null; correct: string | number;
  answer_text: string | null; target_level: number; license: string; explanation?: string[];
  options: { id: string; text: string; tag: string | null }[];
};
export type ReviewSample = { template: string; title: string; checklist: string[]; items: ReviewItemData[] };

export type SkillMastery = { skill: string; name: string; p_known: number | null; n: number };
export type Recommendation = { skill: string; name: string; reason: "nuevo" | "para reforzar" | "repaso" };
export type Progress = {
  sessions: { id: string; mode: string; level: number | null; finished_at: string | null }[];
  mastery: SkillMastery[]; recommended: Recommendation[]; responses: number;
};
export type Course = { course_id: string; course_label: string | null; sessions: number };
export type ClassSkill = { skill: string; name: string; mean_p: number; students: number };
export type FamilyStat = {
  template: string; n: number; p: number | null; discrimination: number | null; mean_time_s: number | null;
  top_errors: Record<string, number>; flags: string[];
};
export type Consent = { attested: boolean; at: string | null; by: string | null; required: boolean };

export type ObsMeta = {
  domains: Record<string, string>; cycles: number[]; entities: { entity: string; group: string }[];
  reference: string; points_per_year: number; notes: string[]; has_se?: boolean; has_gaps?: boolean;
};
export type TrendStats = {
  first_cycle: number; first: number; last_cycle: number; last: number; total_change: number; slope_per_year: number;
  short_change: number; short_from: number; n_cycles: number; gaps: [number, number][];
};
export type Change = { from: number; to: number; diff: number; se: number; z: number; significant: boolean };
export type ObsSeries = {
  entity: string; group: string; points: [number, number][]; se?: [number, number | null][]; changes?: Change[]; trend: TrendStats | null;
};
export type GapRow = { cycle: number; dimension: string; group: string; value: number; se: number | null; n: number | null; quality: string };
export type Provenance = { source: string; url: string; quality: string };
export type ObsSeriesOut = { domain: string; series: ObsSeries[]; region_average: [number, number][]; provenance: Provenance[] };
export type CompareRow = { entity: string; group: string; mean: number; quality: string; gap_vs_oecd: number | null; years_vs_oecd: number | null };
export type Focus = {
  entity: string;
  domains: Record<string, TrendStats & { gap_vs_oecd: number | null; years_vs_oecd: number | null }>;
  below_level2: { cycle: number; value: number; quality: string }[];
};
export type Period = { period: string; n: number | null; suppressed: boolean; mean_level: number | null; share_baseline: number | null; se: number | null };
export type NetRow = { school: string; n: number; mean_level: number; share_baseline: number };
export type NetworkSummary = {
  network_id: string; min_cell: number; schools: NetRow[]; others: NetRow | null; total: Omit<NetRow, "school"> | null;
  baseline_level: number; note: string; pending_invitations: number; pending_tenants: string[];
};
