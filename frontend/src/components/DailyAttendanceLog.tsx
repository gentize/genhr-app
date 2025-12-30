import React, { useEffect, useState } from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
    Typography, Box
} from '@mui/material';
import { getAttendanceToday, getEmployees } from '../services/api';
import { AttendanceRecord, Employee } from '../types';

interface DailyAttendanceLogProps {
    refreshTrigger: boolean;
}

const DailyAttendanceLog: React.FC<DailyAttendanceLogProps> = ({ refreshTrigger }) => {
    const [attendanceRecords, setAttendanceRecords] = useState<AttendanceRecord[]>([]);
    const [employees, setEmployees] = useState<Employee[]>([]); // To map employee IDs to names

    useEffect(() => {
        const fetchData = async () => {
            try {
                const employeesData = await getEmployees();
                setEmployees(employeesData);

                const recordsData = await getAttendanceToday();
                // Sort records by timestamp, newest first
                recordsData.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
                setAttendanceRecords(recordsData);
            } catch (error) {
                console.error('Error fetching daily attendance:', error);
            }
        };
        fetchData();
    }, [refreshTrigger]); // Re-fetch when refreshTrigger changes

    const getEmployeeName = (employeeId: string) => {
        const employee = employees.find(emp => emp.id === employeeId);
        return employee ? employee.name : 'Unknown Employee';
    };

    return (
        <Paper sx={{ p: 2, mt: 3 }}>
            <Typography variant="h6" gutterBottom>Today's Attendance Log</Typography>
            <TableContainer>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Time</TableCell>
                            <TableCell>Employee</TableCell>
                            <TableCell>Status</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {attendanceRecords.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={3} align="center">
                                    <Typography variant="body2">No attendance records for today.</Typography>
                                </TableCell>
                            </TableRow>
                        ) : (
                            attendanceRecords.map((record) => (
                                <TableRow key={record.id}>
                                    <TableCell>{new Date(record.timestamp).toLocaleTimeString()}</TableCell>
                                    <TableCell>{getEmployeeName(record.employeeId)}</TableCell>
                                    <TableCell>
                                        <Box component="span" sx={{
                                            color: record.status === 'Checked In' ? 'success.main' : 'error.main',
                                            fontWeight: 'bold'
                                        }}>
                                            {record.status}
                                        </Box>
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
        </Paper>
    );
};

export default DailyAttendanceLog;
