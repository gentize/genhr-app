import React, { useState, useEffect } from 'react';
import {
    Button, Box, Typography, Select, MenuItem, FormControl, InputLabel, Card, CardContent
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import { getEmployees, getEmployeeAttendanceStatus, recordAttendance } from '../services/api';
import { Employee, AttendanceRecord, AttendanceStatus } from '../types';

interface AttendancePanelProps {
    onRecordUpdate: () => void;
}

const AttendancePanel: React.FC<AttendancePanelProps> = ({ onRecordUpdate }) => {
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('');
    const [status, setStatus] = useState<AttendanceStatus | null>(null);
    const [lastRecord, setLastRecord] = useState<AttendanceRecord | null>(null);

    useEffect(() => {
        const fetchEmployees = async () => {
            try {
                const data = await getEmployees();
                setEmployees(data);
            } catch (error) {
                console.error('Error fetching employees:', error);
            }
        };
        fetchEmployees();
    }, []);

    useEffect(() => {
        const fetchStatus = async () => {
            if (selectedEmployeeId) {
                try {
                    const record = await getEmployeeAttendanceStatus(selectedEmployeeId);
                    // The backend returns the last record, or a default 'Checked Out' if none exists.
                    setStatus(record.status);
                    setLastRecord(record);
                } catch (error) {
                    console.error('Error fetching employee status:', error);
                    setStatus('Checked Out'); // Default to checked out on error
                    setLastRecord(null);
                }
            } else {
                setStatus(null);
                setLastRecord(null);
            }
        };
        fetchStatus();
    }, [selectedEmployeeId]);

    const handleRecordAttendance = async () => {
        if (selectedEmployeeId && status !== null) {
            const newStatus: AttendanceStatus = status === 'Checked In' ? 'Checked Out' : 'Checked In';
            try {
                await recordAttendance(selectedEmployeeId, newStatus);
                setStatus(newStatus); // Update local status immediately
                onRecordUpdate(); // Notify parent to refresh log
                // Re-fetch the last record to update timestamp
                const record = await getEmployeeAttendanceStatus(selectedEmployeeId);
                setLastRecord(record);
            } catch (error) {
                console.error('Error recording attendance:', error);
            }
        }
    };

    const displayEmployee = employees.find(emp => emp.id === selectedEmployeeId);

    return (
        <Card>
            <CardContent>
                <Typography variant="h6" gutterBottom>Attendance Panel</Typography>
                <FormControl fullWidth margin="normal">
                    <InputLabel id="employee-select-label">Select Employee</InputLabel>
                    <Select
                        labelId="employee-select-label"
                        value={selectedEmployeeId}
                        label="Select Employee"
                        onChange={(e) => setSelectedEmployeeId(e.target.value as string)}
                    >
                        {employees.map((employee) => (
                            <MenuItem key={employee.id} value={employee.id}>
                                {employee.name}
                            </MenuItem>
                        ))}
                    </Select>
                </FormControl>

                {selectedEmployeeId && (
                    <Box mt={2}>
                        <Typography variant="subtitle1">
                            {displayEmployee ? `Current Status for ${displayEmployee.name}:` : 'Current Status:'}
                        </Typography>
                        <Box display="flex" alignItems="center" mt={1}>
                            {status === 'Checked In' ? (
                                <CheckCircleIcon color="success" sx={{ mr: 1 }} />
                            ) : (
                                <CancelIcon color="error" sx={{ mr: 1 }} />
                            )}
                            <Typography variant="h5" color={status === 'Checked In' ? 'success.main' : 'error.main'}>
                                {status || 'N/A'}
                            </Typography>
                        </Box>
                        {lastRecord && lastRecord.timestamp && (
                            <Typography variant="caption" color="textSecondary">
                                Last action at: {new Date(lastRecord.timestamp).toLocaleTimeString()}
                            </Typography>
                        )}
                        <Button
                            variant="contained"
                            color={status === 'Checked In' ? 'error' : 'success'}
                            onClick={handleRecordAttendance}
                            sx={{ mt: 2 }}
                            fullWidth
                            disabled={status === null}
                        >
                            {status === 'Checked In' ? 'Check Out' : 'Check In'}
                        </Button>
                    </Box>
                )}
            </CardContent>
        </Card>
    );
};

export default AttendancePanel;
