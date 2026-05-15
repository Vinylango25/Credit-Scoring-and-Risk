import React from "react";
import { Paper, Typography, Box } from "@mui/material";

const BAND_COLORS = {
  green: "#2e7d32",
  red: "#c62828",
  blue: "#1565c0",
  orange: "#e65100",
  purple: "#6a1b9a",
  teal: "#00695c",
};

export default function KPICard({ title, value, subtitle, color = "blue", icon }) {
  return (
    <Paper
      elevation={2}
      sx={{
        p: 2.5,
        borderLeft: `5px solid ${BAND_COLORS[color] || color}`,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <Box display="flex" justifyContent="space-between" alignItems="flex-start">
        <Typography variant="body2" color="text.secondary" fontWeight={600} textTransform="uppercase" fontSize={11}>
          {title}
        </Typography>
        {icon && <Box sx={{ color: BAND_COLORS[color] || color, opacity: 0.7 }}>{icon}</Box>}
      </Box>
      <Typography variant="h4" fontWeight={700} sx={{ color: BAND_COLORS[color] || color, my: 1 }}>
        {value}
      </Typography>
      {subtitle && (
        <Typography variant="caption" color="text.secondary">
          {subtitle}
        </Typography>
      )}
    </Paper>
  );
}
