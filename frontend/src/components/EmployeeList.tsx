import React, { useEffect, useState } from 'react';
import {
    Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
    IconButton, Avatar, Typography, Box
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { getEmployees, deleteEmployee } from '../services/api';
import { Employee } from '../types';

interface EmployeeListProps {
    onEdit: (employee: Employee) => void;
    onRefresh: () => void;
}

const EmployeeList: React.FC<EmployeeListProps> = ({ onEdit, onRefresh }) => {
    const [employees, setEmployees] = useState<Employee[]>([]);

    useEffect(() => {
        fetchEmployees();
    }, [onRefresh]); // Re-fetch when onRefresh prop changes (triggered by App.tsx)

    const fetchEmployees = async () => {
        try {
            const data = await getEmployees();
            setEmployees(data);
        } catch (error) {
            console.error('Error fetching employees:', error);
        }
    };

    const handleDelete = async (id: string) => {
        if (window.confirm('Are you sure you want to delete this employee?')) {
            try {
                await deleteEmployee(id);
                fetchEmployees(); // Refresh the list
            } catch (error) {
                console.error('Error deleting employee:', error);
            }
        }
    };

    return (
        <TableContainer component={Paper}>
            <Table>
                <TableHead>
                    <TableRow>
                        <TableCell>Avatar</TableCell>
                        <TableCell>Name</TableCell>
                        <TableCell>Email</TableCell>
                        <TableCell>Job Title</TableCell>
                        <TableCell>Actions</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {employees.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={5} align="center">
                                <Typography variant="subtitle1">No employees found. Add some!</Typography>
                            </TableCell>
                        </TableRow>
                    ) : (
                        employees.map((employee) => (
                            <TableRow key={employee.id}>
                                <TableCell>
                                    <Avatar src={employee.avatarUrl} alt={employee.name} />
                                </TableCell>
                                <TableCell>{employee.name}</TableCell>
                                <TableCell>{employee.email}</TableCell>
                                <TableCell>{employee.jobTitle}</TableCell>
                                <TableCell>
                                    <IconButton onClick={() => onEdit(employee)} color="primary">
                                        <EditIcon />
                                    </IconButton>
                                    <IconButton onClick={() => handleDelete(employee.id)} color="secondary">
                                        <DeleteIcon />
                                    </IconButton>
                                </TableCell>
                            </TableRow>
                        ))
                    )}
                </TableBody>
            </Table>
        </TableContainer>
    );
};

export default EmployeeList;
