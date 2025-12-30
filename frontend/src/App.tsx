import React, { useState } from 'react';
import { Box, Container, Typography, Button } from '@mui/material';
import Header from './components/Header';
import Footer from './components/Footer';
import EmployeeList from './components/EmployeeList';
import EmployeeForm from './components/EmployeeForm';
import AttendancePanel from './components/AttendancePanel';
import DailyAttendanceLog from './components/DailyAttendanceLog';
import { Employee } from './types';

function App() {
    const [isFormOpen, setIsFormOpen] = useState(false);
    const [employeeToEdit, setEmployeeToEdit] = useState<Employee | null>(null);
    const [employeeListRefresh, setEmployeeListRefresh] = useState(false);
    const [attendanceLogRefresh, setAttendanceLogRefresh] = useState(false);

    const handleOpenForm = (employee: Employee | null = null) => {
        setEmployeeToEdit(employee);
        setIsFormOpen(true);
    };

    const handleCloseForm = () => {
        setIsFormOpen(false);
        setEmployeeToEdit(null);
    };

    const handleEmployeeSave = () => {
        handleCloseForm();
        setEmployeeListRefresh(!employeeListRefresh); // Trigger refresh for employee list
    };

    const handleAttendanceRecordUpdate = () => {
        setAttendanceLogRefresh(!attendanceLogRefresh); // Trigger refresh for attendance log
    };

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <Header />
            <Container maxWidth="lg" sx={{ my: 4, flexGrow: 1 }}>
                <Typography variant="h4" component="h1" gutterBottom align="center" sx={{ mb: 4 }}>
                    HR Employee & Attendance Management
                </Typography>

                {/* Attendance Panel */}
                <Box mb={4}>
                    <AttendancePanel onRecordUpdate={handleAttendanceRecordUpdate} />
                </Box>

                {/* Employee Management Section */}
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h5" component="h2">
                        Employee Directory
                    </Typography>
                    <Button variant="contained" color="primary" onClick={() => handleOpenForm()}>
                        Add New Employee
                    </Button>
                </Box>
                <EmployeeList onEdit={handleOpenForm} onRefresh={employeeListRefresh} />

                {/* Daily Attendance Log */}
                <DailyAttendanceLog refreshTrigger={attendanceLogRefresh} />

                <EmployeeForm
                    open={isFormOpen}
                    onClose={handleCloseForm}
                    onSave={handleEmployeeSave}
                    employeeToEdit={employeeToEdit}
                />
            </Container>
            <Footer />
        </Box>
    );
}

export default App;
