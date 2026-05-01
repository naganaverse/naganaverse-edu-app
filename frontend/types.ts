// Authentication & User Types
export type UserRole = "super_admin" | "owner" | "teacher" | "student" | "parent";

export interface AuthUser {
  userId: string;
  orgId: string;
  name: string;
  role: UserRole;
  phone?: string;
  email?: string;
  telegramId?: number;
  token?: string;
}

// Organization Types
export type OrgStatus = "pending" | "approved" | "rejected" | "active" | "suspended";
export type PlanType = "starter" | "enterprise";

export interface Organization {
  id: string;
  orgId: string;
  orgName: string;
  ownerName: string;
  phone: string;
  city: string;
  referralCode: string;
  referredBy?: string;
  status: OrgStatus;
  planType: PlanType;
  createdAt: string;
}

// Student Types
export interface Student {
  studentId: string;
  orgId: string;
  name: string;
  class: string;
  rollNumber: number;
  subjects: string[];
  fatherName?: string;
  motherName?: string;
  parentPhone: string;
  telegramId?: number;
  agreedFee?: number;
  currentDue?: number;
}

// Teacher Types
export interface Teacher {
  teacherId: string;
  orgId: string;
  name: string;
  subjects: string[];
  assignedClasses: string[];
  phone: string;
  telegramId?: number;
}

// Attendance Types
export interface AttendanceSession {
  attendanceId: string;
  orgId: string;
  className: string;
  subjectName: string;
  date: string;
  presentCount: number;
  absentCount: number;
  teacherId: string;
}

export interface AttendanceDetail {
  attendanceDetailId: string;
  attendanceId: string;
  studentId: string;
  status: "present" | "absent";
}

export interface StudentAttendance {
  studentId: string;
  className: string;
  subjectName: string;
  percentage: number;
  status: "excellent" | "good" | "average" | "low"; // Based on percentage
  totalClasses: number;
  presentClasses: number;
}

// Fee Types
export type TransactionType = "PAYMENT" | "DUE_ADDED";

export interface FeeTransaction {
  transactionId: string;
  orgId: string;
  studentId: string;
  amount: number;
  transactionType: TransactionType;
  receiptFileId?: string;
  recordedBy: string;
  notes?: string;
  createdAt: string;
}

export interface StudentFeeStatus {
  studentId: string;
  studentName: string;
  className: string;
  agreedFee: number;
  currentDue: number;
  lastPaymentDate?: string;
  lastPaymentAmount?: number;
}

// Test Types
export interface Test {
  testId: string;
  orgId: string;
  className: string;
  subjectName: string;
  testName: string;
  testDate: string;
  totalMarks: number;
  createdBy: string;
  createdAt: string;
}

export interface TestQuestion {
  questionId: string;
  testId: string;
  questionText: string;
  marks: number;
  correctAnswer: "A" | "B" | "C" | "D";
  optionA: string;
  optionB: string;
  optionC: string;
  optionD: string;
}

export interface TestAttempt {
  attemptId: string;
  studentId: string;
  questionId: string;
  selectedAnswer: "A" | "B" | "C" | "D" | null;
  isCorrect: boolean;
  createdAt: string;
}

export interface TestResult {
  resultId: string;
  testId: string;
  studentId: string;
  totalMarks: number;
  obtainedMarks: number;
  percentage: number;
  createdAt: string;
}

export interface StudentTestResult extends TestResult {
  testName: string;
  className: string;
  subjectName: string;
  testDate: string;
}

// Resource Types
export type ResourceType = "notes" | "worksheet" | "pyq" | "other";

export interface Resource {
  resourceId: string;
  orgId: string;
  className: string;
  subjectName: string;
  resourceType: ResourceType;
  fileName: string;
  fileUrl: string;
  uploadedBy: string;
  uploadedAt: string;
}

// Announcement Types
export interface Announcement {
  announcementId: string;
  orgId: string;
  title: string;
  message: string;
  targetType: "all_students" | "class" | "all_teachers";
  targetClass?: string;
  createdBy: string;
  createdAt: string;
}

// Homework Types
export interface Homework {
  homeworkId: string;
  orgId: string;
  className: string;
  subjectName: string;
  description: string;
  dueDate: string;
  setBy: string;
  createdAt: string;
}

// Notification Types
export interface ParentNotification {
  notificationId: string;
  orgId: string;
  studentId: string;
  parentPhone: string;
  eventType: "absence_alert" | "test_result" | "attendance_report" | "announcement";
  message: string;
  sentAt: string;
  deliveryStatus: "pending" | "sent" | "failed";
}

// Subscription Types
export interface Subscription {
  subscriptionId: string;
  orgId: string;
  planType: PlanType;
  startDate: string;
  expiryDate: string;
  status: "active" | "expired" | "cancelled";
}

// Audit Log Types
export interface AuditLog {
  logId: string;
  orgId: string;
  userId: string;
  action: string;
  entityType: string;
  entityId: string;
  details?: Record<string, unknown>;
  createdAt: string;
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}
