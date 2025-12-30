const express = require('express');
const { v4: uuidv4 } = require('uuid');
const router = express.Router();

module.exports = ({ readDb, writeDb }) => {
    // GET today's attendance
    router.get('/today', (req, res) => {
        const attendance = readDb('attendance.json');
        const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
        const todaysAttendance = attendance.filter(a => a.date === today);
        res.json(todaysAttendance);
    });

    // GET latest attendance status for a specific employee
    router.get('/status/:employeeId', (req, res) => {
        const attendance = readDb('attendance.json');
        const employeeId = req.params.employeeId;
        const employeeRecords = attendance
            .filter(a => a.employeeId === employeeId)
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)); // Sort by most recent first

        if (employeeRecords.length > 0) {
            res.json(employeeRecords[0]); // Return the latest record
        } else {
            res.json({ employeeId, status: 'Checked Out' }); // Default status if no records exist
        }
    });

    // POST a new attendance event (check-in/check-out)
    router.post('/', (req, res) => {
        const attendance = readDb('attendance.json');
        const { employeeId, status } = req.body; // status should be 'Checked In' or 'Checked Out'

        if (!employeeId || !status) {
            return res.status(400).json({ message: 'employeeId and status are required' });
        }

        const newRecord = {
            id: uuidv4(),
            employeeId,
            status,
            date: new Date().toISOString().split('T')[0], // YYYY-MM-DD
            timestamp: new Date().toISOString(),
        };

        attendance.push(newRecord);
        writeDb('attendance.json', attendance);
        res.status(201).json(newRecord);
    });

    return router;
};
