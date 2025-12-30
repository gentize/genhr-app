const express = require('express');
const { v4: uuidv4 } = require('uuid');
const router = express.Router();

module.exports = ({ readDb, writeDb }) => {
    // GET all employees
    router.get('/', (req, res) => {
        const employees = readDb('employees.json');
        res.json(employees);
    });

    // POST a new employee
    router.post('/', (req, res) => {
        const employees = readDb('employees.json');
        const newEmployee = {
            id: uuidv4(),
            ...req.body,
            // Generate a unique avatar for the new employee
            avatarUrl: `https://robohash.org/${req.body.email}.png?size=200x200&set=set4`
        };
        employees.push(newEmployee);
        writeDb('employees.json', employees);
        res.status(201).json(newEmployee);
    });

    // PUT (update) an employee
    router.put('/:id', (req, res) => {
        let employees = readDb('employees.json');
        const employeeIndex = employees.findIndex(e => e.id === req.params.id);

        if (employeeIndex === -1) {
            return res.status(404).json({ message: 'Employee not found' });
        }

        // Preserve original avatar if email doesn't change
        const currentEmployee = employees[employeeIndex];
        const updatedAvatar = req.body.email === currentEmployee.email 
            ? currentEmployee.avatarUrl 
            : `https://robohash.org/${req.body.email}.png?size=200x200&set=set4`;

        const updatedEmployee = { 
            ...currentEmployee, 
            ...req.body, 
            avatarUrl: updatedAvatar 
        };
        employees[employeeIndex] = updatedEmployee;

        writeDb('employees.json', employees);
        res.json(updatedEmployee);
    });

    // DELETE an employee
    router.delete('/:id', (req, res) => {
        let employees = readDb('employees.json');
        const filteredEmployees = employees.filter(e => e.id !== req.params.id);

        if (employees.length === filteredEmployees.length) {
            return res.status(404).json({ message: 'Employee not found' });
        }

        writeDb('employees.json', filteredEmployees);
        res.status(204).send(); // No content
    });

    return router;
};
