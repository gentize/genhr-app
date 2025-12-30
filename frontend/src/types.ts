// src/types.ts

export interface Employee {
    id: string;
    name: string;
    email: string;
    phone: string;
    jobTitle: string;
    avatarUrl: string;
}

export interface EmployeeCreate {
    name: string;
    email: string;
    phone: string;
    jobTitle: string;
}

export interface EmployeeUpdate {
    name?: string;
    email?: string;
    phone?: string;
    jobTitle?: string;
}

export type AttendanceStatus = 'Checked In' | 'Checked Out';

export interface AttendanceRecord {
    id: string;
    employeeId: string;
    status: AttendanceStatus;
    date: string; // YYYY-MM-DD
    timestamp: string; // ISO string
}

export interface AttendanceLogEntry {
    employeeId: string;
    employeeName: string;
    status: AttendanceStatus;
    timestamp: string;
}
