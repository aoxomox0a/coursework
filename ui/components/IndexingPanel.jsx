import { useState, useEffect } from 'react';
import axios from 'axios';
import styles from '../styles/IndexingPanel.module.css';

export default function IndexingPanel() {
  const [endpoint, setEndpoint] = useState('http://dbpedia.org/sparql');
  const [isIndexing, setIsIndexing] = useState(false);
  const [loadingCounts, setLoadingCounts] = useState(false);
  const [indexedCounts, setIndexedCounts] = useState({ 
    entities: 0, 
    properties: 0, 
    classes: 0,
    sample_triples: 0,
    class_entity_mappings: 0
  });

  const predefinedEndpoints = [
    { label: 'DBpedia', value: 'http://dbpedia.org/sparql' },
    { label: 'Wikidata', value: 'https://query.wikidata.org/sparql' },
  ];

  const fetchCollectionCounts = async (endpointUrl) => {
    setLoadingCounts(true);
    try {
      const response = await axios.post('/api/counts', {
        endpoint: endpointUrl
      });
      if (response.data.status === 'success') {
        const counts = response.data.counts || {};
        setIndexedCounts({
          entities: counts.entities || 0,
          properties: counts.properties || 0,
          classes: counts.classes || 0,
          sample_triples: counts.sample_triples || 0,
          class_entity_mappings: counts.class_entity_mappings || 0
        });
      }
    } catch (error) {
      console.error('Error fetching collection counts:', error);
    } finally {
      setLoadingCounts(false);
    }
  };

  // Fetch counts on component mount
  useEffect(() => {
    const defaultEndpoint = 'http://dbpedia.org/sparql';
    fetchCollectionCounts(defaultEndpoint);
  }, []);

  const handleEndpointChange = (value) => {
    setEndpoint(value);
    if (value.trim()) {
      // Fetch counts for the new endpoint
      fetchCollectionCounts(value);
    }
  };

  const handleIndex = async () => {
    if (!endpoint.trim()) {
      alert('Please enter a SPARQL endpoint URL');
      return;
    }

    setIsIndexing(true);

    try {
      // Start the indexing process in background
      await axios.post('/api/index', {
        endpoint: endpoint
      });

      // Wait a moment and then show completion
      setTimeout(() => {
        alert('✓ Indexing started in background and will complete shortly');
      }, 500);

      // Fetch final counts once after a delay
      await new Promise(resolve => setTimeout(resolve, 3000));
      try {
        const countsResponse = await axios.post('/api/counts', {
          endpoint: endpoint
        });
        if (countsResponse.data.status === 'success') {
          setIndexedCounts({
            entities: countsResponse.data.counts.entities || 0,
            properties: countsResponse.data.counts.properties || 0,
            classes: countsResponse.data.counts.classes || 0,
            sample_triples: countsResponse.data.counts.sample_triples || 0,
            class_entity_mappings: countsResponse.data.counts.class_entity_mappings || 0
          });
        }
      } catch (error) {
        console.error('Error fetching final counts:', error);
      }
    } catch (error) {
      alert('✗ Failed to start indexing: ' + (error.message || 'Unknown error'));
      console.error('Indexing error:', error);
    } finally {
      setIsIndexing(false);
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
        </div>

        {/* Indexed counts display */}
        <div className={styles.countsDisplay}>
          {loadingCounts ? (
            <div className={styles.loadingCounts}>Loading counts...</div>
          ) : (
            <>
              <div className={styles.countItem}>
                <span className={styles.countLabel}>Properties:</span>
                <span className={styles.countValue}>{indexedCounts.properties} indexed</span>
              </div>
              <div className={styles.countItem}>
                <span className={styles.countLabel}>Classes:</span>
                <span className={styles.countValue}>{indexedCounts.classes} indexed</span>
              </div>
              <div className={styles.countItem}>
                <span className={styles.countLabel}>Entities:</span>
                <span className={styles.countValue}>{indexedCounts.entities} indexed</span>
              </div>
              <div className={styles.countItem}>
                <span className={styles.countLabel}>Sample Triples:</span>
                <span className={styles.countValue}>{indexedCounts.sample_triples} indexed</span>
              </div>
              <div className={styles.countItem}>
                <span className={styles.countLabel}>Class-Entity Mappings:</span>
                <span className={styles.countValue}>{indexedCounts.class_entity_mappings} indexed</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
