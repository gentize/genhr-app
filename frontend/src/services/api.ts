// src/services/api.ts
import axios from 'axios';
import { Employee, EmployeeCreate, EmployeeUpdate, AttendanceRecord } from '../types';

const API_BASE_URL = 'http://localhost:3001/api';

// --- Employee Endpoints ---
export const getEmployees = async (): Promise<Employee[]> => {
    const response = await axios.get(`${API_BASE_URL}/employees`);
    return response.data;
};

export const createEmployee = async (employeeData: EmployeeCreate): Promise<Employee> => {
    const response = await axios.post(`${API_BASE_URL}/employees`, employeeData);
    return response.data;
};

export const updateEmployee = async (id: string, employeeData: EmployeeUpdate): Promise<Employee> => {
    const response = await axios.put(`${API_BASE_URL}/employees/${id}`, employeeData);
    return response.data;
};

export const deleteEmployee = async (id: string): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/employees/${id}`);
};

// --- Attendance Endpoints ---
export const getAttendanceToday = async (): Promise<AttendanceRecord[]> => {
    const response = await axios.get(`${API_BASE_URL}/attendance/today`);
    return response.data;
};

export const getEmployeeAttendanceStatus = async (employeeId: string): Promise<AttendanceRecord> => {
    const response = await axios.get(`${API_BASE_URL}/attendance/status/${employeeId}`);
    return response.data;
};

export const recordAttendance = async (employeeId: string, status: 'Checked In' | 'Checked Out'): Promise<AttendanceRecord> => {
    const response = await axios.post(`${API_BASE_URL}/attendance`, { employeeId, status });
    return response.data;
};

export const getAppLogo = async (): Promise<string> => {
    const response = await axios.get(`${API_BASE_URL}/logo`, { responseType: 'text' });
    return response.data;
};
