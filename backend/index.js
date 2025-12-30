const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3001; // Using a different port than the default React port

app.use(cors());
app.use(bodyParser.json());

// --- Helper Functions to read/write from JSON DB ---
const dbPath = (fileName) => path.join(__dirname, 'db', fileName);

const readDb = (fileName) => {
    try {
        const data = fs.readFileSync(dbPath(fileName), 'utf8');
        return JSON.parse(data);
    } catch (error) {
        console.error(`Error reading from ${fileName}:`, error);
        return [];
    }
};

const writeDb = (fileName, data) => {
    try {
        fs.writeFileSync(dbPath(fileName), JSON.stringify(data, null, 2));
    } catch (error) {
        console.error(`Error writing to ${fileName}:`, error);
    }
};

// --- API Routes ---
const employeeRoutes = require('./routes/employees');
const attendanceRoutes = require('./routes/attendance');

app.use('/api/employees', employeeRoutes({ readDb, writeDb }));
app.use('/api/attendance', attendanceRoutes({ readDb, writeDb }));


// --- Simple Logo SVG Route ---
app.get('/api/logo', (req, res) => {
    const logoSvg = `
        <svg width="100" height="40" viewBox="0 0 100 40" xmlns="http://www.w3.org/2000/svg">
            <rect width="100" height="40" rx="5" ry="5" fill="#6D28D9" />
            <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="white">
                GenHR
            </text>
        </svg>
    `;
    res.setHeader('Content-Type', 'image/svg+xml');
    res.send(logoSvg);
});


app.listen(PORT, () => {
    console.log(`Backend server is running on http://localhost:${PORT}`);
});
