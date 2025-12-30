import React from 'react';
import { Box, Typography } from '@mui/material';

const Footer: React.FC = () => {
    return (
        <Box sx={{
            mt: 'auto', // Push to bottom
            py: 2,
            px: 2,
            bgcolor: 'primary.main',
            color: 'white',
            textAlign: 'center',
        }}>
            <Typography variant="body2">
                © {new Date().getFullYear()} GenHR. All rights reserved.
            </Typography>
        </Box>
    );
};

export default Footer;
