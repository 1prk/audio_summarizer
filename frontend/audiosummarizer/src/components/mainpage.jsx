import React, {useEffect, useState} from 'react';
import {TextField, Button, Container, Box, Typography, CircularProgress} from '@mui/material';

export default function MainPage() {
  const [inputValue, setInputValue] = useState('');
  const [taskId, setTaskId] = useState('');
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [taskStatus, setTaskStatus] = useState(null);

  const handleChange = (event) => {
    setInputValue(event.target.value);
  };

  const handleSend = () => {
    setLoading(true);
    setError(null);
    fetch(`http://localhost:5000/api/get_audio?url=${inputValue}`, {method: 'GET'})
        .then(response => {
          if (!response.ok) {
              throw Error(response.statusText);
          }
          return response.json();
        })
        .then(data => {
            setTaskId(data.task_id || 'no task id provided.');
            setTaskStatus("processing")
            setLoading(false)
        })
        .catch(err => {
            console.log(err)
            setLoading(false);
            setError(err.message);
        });
  };

useEffect(() => {
  if (taskId && taskStatus === 'processing') {
    // Polling starten
    const interval = setInterval(() => {
      fetch(`http://localhost:5000/api/result/${taskId}`, { method: 'GET' })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.statusText}`);
          }
          return response.json();
        })
        .then((data) => {
          setTaskStatus(data.status);

          if (data.status === 'done') {
            // Ergebnis verarbeiten und Polling stoppen
            setResult(JSON.stringify(data.result || 'No result found'));
            clearInterval(interval);
          } else if (data.status === 'failed') {
            // Fehlerstatus behandeln
            setError('Task failed on the server.');
            clearInterval(interval);
          }
        })
        .catch((err) => {
          setError(`Fetch error: ${err.message}`);
          clearInterval(interval); // Polling bei Fehler beenden
        });
    }, 2000); // Alle 2 Sekunden pollen

    // Cleanup-Funktion bei Component-Unmount
    return () => clearInterval(interval);
  }
}, [taskId, taskStatus]);

  return (
    <Container maxWidth="sm">
      <Box
        display="flex"
        alignItems="center"
        justifyContent="space-between"
        mt={4}
      >
        <TextField
          label="URL"
          variant="outlined"
          value={inputValue}
          onChange={handleChange}
          fullWidth
          sx={{ marginRight: 2 }}
        />
        <Button
          variant="contained"
          color="primary"
          onClick={handleSend}
          disabled={loading || !inputValue}
        >
          {loading ? <CircularProgress size={24} /> : 'Transcribe'}
        </Button>
      </Box>
      <Box mt={4}>
        {error && (
          <Typography color="error" variant="body1">
            Error: {error}
          </Typography>
        )}
        {taskId && (
          <Typography color="primary" variant="h6">
            Task ID: {taskId}
          </Typography>
        )}
        {result && (
          <Typography variant="h6" color="secondary">
            Result: {result}
          </Typography>
        )}
      </Box>
    </Container>
  );
}
