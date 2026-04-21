import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import styles from '../styles/QueryTranslator.module.css';

const PREDEFINED_QUERIES = [
  {
    label: 'DBpedia',
    value: 'http://dbpedia.org/sparql'
  },
  {
    label: 'Wikidata',
    value: 'https://query.wikidata.org/sparql'
  }
];

export default function QueryTranslator() {
  const [endpoint, setEndpoint] = useState('http://dbpedia.org/sparql');
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexStatus, setIndexStatus] = useState('unknown');
  const [indexMessage, setIndexMessage] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [entityLimit, setEntityLimit] = useState('10000');
  
  const [nlQuery, setNlQuery] = useState('');
  const [sparqlQuery, setSparqlQuery] = useState('');
  const [isTranslating, setIsTranslating] = useState(false);
  const [translationError, setTranslationError] = useState('');
  
  const [sparqlInput, setSparqlInput] = useState('');
  const [nlExplanation, setNlExplanation] = useState('');
  const [isExplaining, setIsExplaining] = useState(false);
  const [explanationError, setExplanationError] = useState('');
  
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Check if endpoint is indexed
  const checkIndexStatus = async (url) => {
    try {
      const response = await axios.post('http://localhost:8000/api/counts', {
        endpoint: url
      });
      if (response.data.status === 'success' && response.data.counts.entities > 0) {
        setIndexStatus('indexed');
        setIndexMessage(`✓ Indexed (${response.data.counts.entities} entities)`);
      } else {
        setIndexStatus('not-indexed');
        setIndexMessage('Not indexed');
      }
    } catch (error) {
      setIndexStatus('error');
      setIndexMessage('Status check failed');
      console.error('Error checking index status:', error);
    }
  };

  // Handle endpoint selection from dropdown
  const handleEndpointSelect = (value) => {
    setEndpoint(value);
    checkIndexStatus(value);
  };

  // Handle manual endpoint input
  const handleEndpointChange = (e) => {
    const value = e.target.value;
    setEndpoint(value);
    if (value.trim()) {
      checkIndexStatus(value);
    }
  };

  // Index & Link button
  const handleIndexLink = async () => {
    if (!endpoint.trim()) {
      alert('Please enter a SPARQL endpoint URL');
      return;
    }

    setIsIndexing(true);
    setIndexMessage('Indexing in progress...');
    setIndexStatus('indexing');

    try {
      const indexPayload = { endpoint: endpoint };
      if (entityLimit) {
        indexPayload.max_entities = parseInt(entityLimit);
      }
      
      await axios.post('http://localhost:8000/api/index', indexPayload);

      // Keep isIndexing true and poll /counts until confirmed indexed
      let isConfirmed = false;
      let attempts = 0;
      const maxAttempts = 120; // 2 minutes with 1-second intervals

      while (!isConfirmed && attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
        
        try {
          const response = await axios.post('http://localhost:8000/api/counts', {
            endpoint: endpoint
          });
          
          if (response.data.status === 'success' && response.data.counts.entities > 0) {
            isConfirmed = true;
            setIndexStatus('indexed');
            setIndexMessage(`✓ Indexed (${response.data.counts.entities} entities)`);
          }
        } catch (error) {
          console.log('Checking index status...', attempts);
        }
        
        attempts++;
      }

      if (!isConfirmed) {
        setIndexStatus('error');
        setIndexMessage('Indexing timeout - please try again');
      }
    } catch (error) {
      setIndexStatus('error');
      setIndexMessage('Indexing failed');
      console.error('Indexing error:', error);
    } finally {
      setIsIndexing(false);
    }
  };

  // Translate NL to SPARQL
  const handleTranslate = async () => {
    if (!nlQuery.trim()) {
      alert('Please enter a natural language question');
      return;
    }

    if (indexStatus !== 'indexed') {
      alert('Please index the endpoint first');
      return;
    }

    setIsTranslating(true);
    setTranslationError('');
    setSparqlQuery('');

    try {
      const response = await axios.post('http://localhost:8000/api/generate-sparql', {
        question: nlQuery
      });

      if (response.data.status === 'success') {
        setSparqlQuery(response.data.sparql_query || '');
        setTranslationError('');
      } else {
        setTranslationError(response.data.error || 'Translation failed');
        setSparqlQuery('');
      }
    } catch (error) {
      setTranslationError(error.response?.data?.message || error.message || 'Translation error');
      setSparqlQuery('');
      console.error('Translation error:', error);
    } finally {
      setIsTranslating(false);
    }
  };

  // Explain SPARQL to Natural Language
  const handleExplain = async () => {
    if (!sparqlInput.trim()) {
      alert('Please enter a SPARQL query');
      return;
    }

    setIsExplaining(true);
    setExplanationError('');
    setNlExplanation('');

    try {
      const response = await axios.post('http://localhost:8000/api/explain', {
        sparql_query: sparqlInput
      });

      if (response.data.status === 'success') {
        setNlExplanation(response.data.explanation || '');
        setExplanationError('');
      } else {
        setExplanationError(response.data.error || 'Explanation failed');
        setNlExplanation('');
      }
    } catch (error) {
      setExplanationError(error.response?.data?.message || error.message || 'Explanation error');
      setNlExplanation('');
      console.error('Explanation error:', error);
    } finally {
      setIsExplaining(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>Natural Language ⇌ SPARQL</h1>

        {/* ENDPOINT SECTION */}
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>1. Select Endpoint</h2>
          
          <div className={styles.labelsRow}>
            <label className={styles.label}>SPARQL Endpoint URL</label>
            <label className={styles.label}>Entities Amount</label>
          </div>
          
          <div className={styles.endpointLineContainer}>
            <div className={styles.comboboxContainer} ref={dropdownRef}>
              <input
                type="text"
                value={endpoint}
                onChange={(e) => {
                  setEndpoint(e.target.value);
                  checkIndexStatus(e.target.value);
                }}
                onFocus={() => setShowDropdown(true)}
                placeholder="http://your-sparql-endpoint/sparql"
                className={styles.comboboxInput}
                disabled={isIndexing}
              />
              <button
                onClick={() => setShowDropdown(!showDropdown)}
                className={styles.dropdownToggle}
                disabled={isIndexing}
              >
                ▼
              </button>
              
              {showDropdown && (
                <div className={styles.dropdownList}>
                  {PREDEFINED_QUERIES.map((query) => (
                    <div
                      key={query.value}
                      className={`${styles.dropdownItem} ${endpoint === query.value ? styles.active : ''}`}
                      onClick={() => {
                        setEndpoint(query.value);
                        checkIndexStatus(query.value);
                        setShowDropdown(false);
                      }}
                    >
                      {query.label}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button
              onClick={handleIndexLink}
              disabled={isIndexing || indexStatus === 'indexed'}
              className={`${styles.button} ${styles.indexBtn}`}
            >
              {isIndexing ? (
                <>
                  <span className={styles.skeleton}>⏳</span> Indexing...
                </>
              ) : indexStatus === 'indexed' ? (
                '✓ Indexed'
              ) : (
                '📊 Index & Link'
              )}
            </button>

            <div className={styles.entityLimitContainer}>
              <input
                type="number"
                value={entityLimit}
                onChange={(e) => setEntityLimit(e.target.value)}
                placeholder="10000"
                className={styles.entityLimitInput}
                disabled={isIndexing || indexStatus === 'indexed'}
                min="1"
              />
            </div>
          </div>
        </div>

        {/* TRANSLATION SECTION */}
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>2. Natural Language to SPARQL</h2>

          <div className={styles.translationContainer}>
            {/* LEFT: Natural Language Input */}
            <div className={styles.inputColumn}>
              <label className={styles.label}>Natural Language Question</label>
              <textarea
                value={nlQuery}
                onChange={(e) => setNlQuery(e.target.value)}
                placeholder="e.g., Who directed Inception?"
                className={styles.textarea}
                disabled={isTranslating || indexStatus !== 'indexed'}
              />
            </div>

            {/* MIDDLE: Translate Button */}
            <div className={styles.buttonColumn}>
              <button
                onClick={handleTranslate}
                disabled={isTranslating || indexStatus !== 'indexed'}
                className={`${styles.button} ${styles.translateBtn}`}
              >
                {isTranslating ? '⏳' : '📖'}
                <br />
                Translate
              </button>
            </div>

            {/* RIGHT: SPARQL Output */}
            <div className={styles.outputColumn}>
              <label className={styles.label}>SPARQL Query Output</label>
              <textarea
                value={sparqlQuery}
                readOnly
                placeholder="SPARQL query will appear here..."
                className={`${styles.textarea} ${styles.outputTextarea}`}
              />
            </div>
          </div>

          {translationError && (
            <div className={styles.error}>
              ✗ {translationError}
            </div>
          )}
        </div>

        {/* EXPLANATION SECTION */}
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>3. SPARQL to Natural Language</h2>

          <div className={styles.translationContainer}>
            {/* LEFT: SPARQL Input */}
            <div className={styles.inputColumn}>
              <label className={styles.label}>SPARQL Query Input</label>
              <textarea
                value={sparqlInput}
                onChange={(e) => setSparqlInput(e.target.value)}
                placeholder="e.g., SELECT ?name WHERE { ?x rdf:type Person; foaf:name ?name }"
                className={styles.textarea}
                disabled={isExplaining}
              />
            </div>

            {/* MIDDLE: Explain Button */}
            <div className={styles.buttonColumn}>
              <button
                onClick={handleExplain}
                disabled={isExplaining}
                className={`${styles.button} ${styles.explainBtn}`}
              >
                {isExplaining ? '⏳' : '📖'}
                <br />
                Translate
              </button>
            </div>

            {/* RIGHT: Natural Language Output */}
            <div className={styles.outputColumn}>
              <label className={styles.label}>Natural Language Explanation</label>
              <textarea
                value={nlExplanation}
                readOnly
                placeholder="Explanation will appear here..."
                className={`${styles.textarea} ${styles.outputTextarea}`}
              />
            </div>
          </div>

          {explanationError && (
            <div className={styles.error}>
              ✗ {explanationError}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
