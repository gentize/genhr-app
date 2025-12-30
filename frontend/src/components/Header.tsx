import React, { useEffect, useState } from 'react';
import { AppBar, Toolbar, Typography, Box } from '@mui/material';
import { getAppLogo } from '../services/api';

const Header: React.FC = () => {
    const [logoSvg, setLogoSvg] = useState<string>('');

    useEffect(() => {
        const fetchLogo = async () => {
            try {
                const svg = await getAppLogo();
                setLogoSvg(svg);
            } catch (error) {
                console.error('Error fetching logo:', error);
            }
        };
        fetchLogo();
    }, []);

    return (
        <AppBar position="static">
            <Toolbar>
                <Box display="flex" alignItems="center" sx={{ flexGrow: 1 }}>
                    {logoSvg ? (
                        <Box
                            component="div"
                            dangerouslySetInnerHTML={{ __html: logoSvg }}
                            sx={{
                                display: 'flex',
                                alignItems: 'center',
                                '& svg': {
                                    height: 30, // Adjust height as needed
                                    marginRight: 1,
                                },
                            }}
                        />
                    ) : (
                        <Typography variant="h6" component="div" sx={{ marginRight: 1 }}>
                            GenHR
                        </Typography>
                    )}
                    <Typography variant="h6" component="div">
                        Employee Management
                    </Typography>
                </Box>
            </Toolbar>
        </AppBar>
    );
};

export default Header;
