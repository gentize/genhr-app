import React, { useState, useEffect } from 'react';
import {
    TextField, Button, Dialog, DialogActions, DialogContent, DialogTitle
} from '@mui/material';
import { Employee, EmployeeCreate, EmployeeUpdate } from '../types';
import { createEmployee, updateEmployee } from '../services/api';

interface EmployeeFormProps {
    open: boolean;
    onClose: () => void;
    onSave: () => void;
    employeeToEdit: Employee | null;
}

const EmployeeForm: React.FC<EmployeeFormProps> = ({ open, onClose, onSave, employeeToEdit }) => {
    const [formData, setFormData] = useState<EmployeeCreate | EmployeeUpdate>({
        name: '',
        email: '',
        phone: '',
        jobTitle: ''
    });

    useEffect(() => {
        if (employeeToEdit) {
            setFormData({
                name: employeeToEdit.name,
                email: employeeToEdit.email,
                phone: employeeToEdit.phone,
                jobTitle: employeeToEdit.jobTitle,
            });
        } else {
            setFormData({ // Reset for new employee
                name: '',
                email: '',
                phone: '',
                jobTitle: ''
            });
        }
    }, [employeeToEdit, open]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async () => {
        try {
            if (employeeToEdit) {
                await updateEmployee(employeeToEdit.id, formData);
            } else {
                await createEmployee(formData as EmployeeCreate);
            }
            onSave();
        } catch (error) {
            console.error('Error saving employee:', error);
        }
    };

    return (
        <Dialog open={open} onClose={onClose}>
            <DialogTitle>{employeeToEdit ? 'Edit Employee' : 'Add New Employee'}</DialogTitle>
            <DialogContent>
                <TextField
                    autoFocus
                    margin="dense"
                    name="name"
                    label="Full Name"
                    type="text"
                    fullWidth
                    variant="standard"
                    value={formData.name}
                    onChange={handleChange}
                />
                <TextField
                    margin="dense"
                    name="email"
                    label="Email Address"
                    type="email"
                    fullWidth
                    variant="standard"
                    value={formData.email}
                    onChange={handleChange}
                />
                <TextField
                    margin="dense"
                    name="phone"
                    label="Phone Number"
                    type="text"
                    fullWidth
                    variant="standard"
                    value={formData.phone}
                    onChange={handleChange}
                />
                <TextField
                    margin="dense"
                    name="jobTitle"
                    label="Job Title"
                    type="text"
                    fullWidth
                    variant="standard"
                    value={formData.jobTitle}
                    onChange={handleChange}
                />
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button onClick={handleSubmit}>Save</Button>
            </DialogActions>
        </Dialog>
    );
};

export default EmployeeForm;
