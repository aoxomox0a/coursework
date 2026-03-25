import { useState, useEffect } from 'react';
import axios from 'axios';
import styles from '../styles/IndexingPanel.module.css';

export default function IndexingPanel() {
  const [endpoint, setEndpoint] = useState('http://dbpedia.org/sparql');
  const [isIndexing, setIsIndexing] = useState(false);
  const [resumeFromCheckpoint, setResumeFromCheckpoint] = useState(false);
  const [totalEntities, setTotalEntities] = useState(0);
  const [indexedEntities, setIndexedEntities] = useState(0);
  const [loadingProgress, setLoadingProgress] = useState(false);
  const [currentProcess, setCurrentProcess] = useState(''); // 'fetching', 'indexing', 'saving'
  const [processProgress, setProcessProgress] = useState(0);
  const [processTotal, setProcessTotal] = useState(0);

  const predefinedEndpoints = [
    { label: 'DBpedia', value: 'http://dbpedia.org/sparql' },
    { label: 'Wikidata', value: 'https://query.wikidata.org/sparql' },
  ];

  const fetchProgress = async (endpointUrl) => {
    setLoadingProgress(true);
    try {
      const response = await axios.post('/api/progress', {
        endpoint: endpointUrl
      });

      if (response.data.status === 'success') {
        setTotalEntities(response.data.total || 0);
        setIndexedEntities(response.data.indexed || 0);
      }
    } catch (error) {
      console.error('Error fetching progress:', error);
    } finally {
      setLoadingProgress(false);
    }
  };

  // Fetch progress on component mount
  useEffect(() => {
    fetchProgress('http://dbpedia.org/sparql');
  }, []);

  const handleEndpointChange = (value) => {
    setEndpoint(value);
    if (value.trim()) {
      fetchProgress(value);
    }
  };

  const renderProgressBar = (current, total, width = 30) => {
    if (total === 0) return '0%|' + '░'.repeat(width) + '| 0/0';
    
    const percentage = Math.round((current / total) * 100);
    const filledChars = Math.round((current / total) * width);
    const emptyChars = width - filledChars;
    
    const filled = '█'.repeat(Math.max(0, filledChars - 1));
    const partial = filledChars > 0 ? '▍' : '';
    const empty = '░'.repeat(Math.max(0, emptyChars));
    
    return `${percentage}%|${filled}${partial}${empty}| ${current}/${total}`;
  };

  const handleIndex = async () => {
    if (!endpoint.trim()) {
      alert('Please enter a SPARQL endpoint URL');
      return;
    }

    setIsIndexing(true);
    setCurrentProcess('fetching');
    setProcessProgress(0);
    setProcessTotal(totalEntities);

    try {
      // Simulate fetching with progress
      for (let i = 0; i <= totalEntities; i += Math.ceil(totalEntities / 10)) {
        setProcessProgress(Math.min(i, totalEntities));
        await new Promise(r => setTimeout(r, 100));
      }
      setProcessProgress(totalEntities);

      // Switch to indexing
      setCurrentProcess('indexing');
      setProcessProgress(0);
      setProcessTotal(totalEntities);

      // Simulate indexing with progress
      for (let i = 0; i <= totalEntities; i += Math.ceil(totalEntities / 10)) {
        setProcessProgress(Math.min(i, totalEntities));
        await new Promise(r => setTimeout(r, 100));
      }
      setProcessProgress(totalEntities);

      // Fetch with custom endpoint
      const response = await axios.post('/api/index', {
        endpoint: endpoint,
        resume: resumeFromCheckpoint
      });

      // Switch to saving
      setCurrentProcess('saving');
      setProcessProgress(0);
      setProcessTotal(totalEntities);

      // Simulate saving with progress
      for (let i = 0; i <= totalEntities; i += Math.ceil(totalEntities / 10)) {
        setProcessProgress(Math.min(i, totalEntities));
        await new Promise(r => setTimeout(r, 100));
      }
      setProcessProgress(totalEntities);

      if (response.data.status === 'success') {
        setCurrentProcess('');
        setTimeout(() => {
          alert('✓ Indexing completed successfully!');
        }, 500);
      } else {
        setCurrentProcess('');
        alert('✗ Indexing failed: ' + (response.data.message || 'Unknown error'));
      }
    } catch (error) {
      setCurrentProcess('');
      alert('✗ Indexing failed: ' + (error.message || 'Failed to connect to the backend API'));
      console.error('Indexing error:', error);
    } finally {
      setIsIndexing(false);
      setProcessProgress(0);
      setProcessTotal(0);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>Natural Language ⇌ SPARQL</h1>

        <div className={styles.section}>
          <label className={styles.label}>SPARQL Endpoint URL</label>

          {/* Quick select buttons */}
          <div className={styles.quickSelect}>
            {predefinedEndpoints.map((ep) => (
              <button
                key={ep.value}
                className={`${styles.quickBtn} ${endpoint === ep.value ? styles.active : ''}`}
                onClick={() => handleEndpointChange(ep.value)}
              >
                {ep.label}
              </button>
            ))}
          </div>

          {/* URL input */}
          <input
            type="text"
            value={endpoint}
            onChange={(e) => handleEndpointChange(e.target.value)}
            placeholder="Enter SPARQL endpoint URL"
            className={styles.input}
            disabled={isIndexing}
          />
        </div>

        {/* Action buttons */}
        <div className={styles.buttonGroup}>
          <button
            onClick={handleIndex}
            disabled={isIndexing}
            className={`${styles.button} ${styles.primary}`}
          >
            {isIndexing ? 'Loading and indexing...' : '▶ Load and index'}
          </button>

          {indexedEntities > 0 && (
            <div className={styles.uploadedInfo}>
              Uploaded: {indexedEntities} / {totalEntities}
            </div>
          )}
        </div>

        {/* Resume checkbox - only visible if entities exist */}
        {indexedEntities > 0 && (
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={resumeFromCheckpoint}
              onChange={(e) => setResumeFromCheckpoint(e.target.checked)}
              disabled={isIndexing}
              className={styles.checkbox}
            />
            Resume loading
          </label>
        )}

        {/* Progress bar before indexing starts */}
        {totalEntities > 0 && !currentProcess && (
          <div className={styles.progressSection}>
            <div className={styles.progressStats}>
              <span>{indexedEntities} / {totalEntities} entities indexed</span>
              <span className={styles.progressPercent}>
                {totalEntities > 0 ? Math.round((indexedEntities / totalEntities) * 100) : 0}%
              </span>
            </div>
            <div className={styles.progressBar}>
              <div
                className={styles.progressFill}
                style={{ width: totalEntities > 0 ? ((indexedEntities / totalEntities) * 100) : 0 + '%' }}
              />
            </div>
          </div>
        )}

        {loadingProgress && (
          <div className={styles.loadingMessage}>
            Loading entity count...
          </div>
        )}

        {/* Fancy progress bar during processing */}
        {currentProcess && (
          <div className={styles.fancyProgressSection}>
            <div className={styles.processLabel}>
              {currentProcess.charAt(0).toUpperCase() + currentProcess.slice(1)}...
            </div>
            <div className={styles.fancyProgressBar}>
              <code>{renderProgressBar(processProgress, processTotal)}</code>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
