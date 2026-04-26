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

// Multiple ambient music URLs (free ambient/elevator music)
const AMBIENT_MUSIC_URLS = [
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3',
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3',
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3',
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3',
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-6.mp3',
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-7.mp3',
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3',
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3',
  'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3',
];

const getRandomMusicUrl = () => {
  return AMBIENT_MUSIC_URLS[Math.floor(Math.random() * AMBIENT_MUSIC_URLS.length)];
};

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
  
  const [isPlayingMusic, setIsPlayingMusic] = useState(false);
  
  const dropdownRef = useRef(null);
  const audioRef = useRef(null);

  // Initialize audio element
  useEffect(() => {
    if (!audioRef.current) {
      const audio = new Audio(getRandomMusicUrl());
      audio.loop = true;
      audio.volume = 0.3; // Set volume to 30%
      audioRef.current = audio;
    }
  }, []);

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

  // Handle music toggle
  const handleMusicToggle = async () => {
    if (!audioRef.current) return;

    try {
      if (isPlayingMusic) {
        audioRef.current.pause();
        setIsPlayingMusic(false);
        console.log('🔊 Music paused');
      } else {
        // Load a random track before playing
        audioRef.current.src = getRandomMusicUrl();
        audioRef.current.currentTime = 0;
        await audioRef.current.play();
        setIsPlayingMusic(true);
        console.log('🔊 Music playing (random track selected)');
      }
    } catch (error) {
      console.error('🔊 Error toggling music:', error);
      // Silently fail - may be due to browser autoplay policies
    }
  };

  // Cleanup: stop music when component unmounts
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);


  // Check if endpoint is indexed
  const checkIndexStatus = async (url) => {
    try {
      const response = await axios.post('http://localhost:8000/api/check', {
        endpoint: url
      });
      if (response.data.is_indexed) {
        setIndexStatus('indexed');
        setIndexMessage('✓ Indexed');
        console.log(`✅ Endpoint ${url} is indexed`);
      } else {
        setIndexStatus('not-indexed');
        setIndexMessage('Not indexed');
        console.log(`⚠️  Endpoint ${url} is not indexed`);
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

  // Index & Link button - now with SSE streaming
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

      // Stream status updates via SSE
      const eventSource = new EventSource(`http://localhost:8000/api/status/stream?endpoint=${encodeURIComponent(endpoint)}`);
      let sseTimeout;
      
      console.log(`🔌 [SSE] Connected to stream for ${endpoint}`);
      
      // Fallback: If SSE takes too long (10 minutes), assume complete
      sseTimeout = setTimeout(() => {
        console.warn(`⏱️ [SSE] Timeout after 10 minutes, assuming indexing complete`);
        setIndexStatus('indexed');
        setIndexMessage('✓ Indexing completed (timeout)');
        setIsIndexing(false);
        eventSource.close();
      }, 10 * 60 * 1000);
      
      eventSource.onmessage = (event) => {
        try {
          const status = JSON.parse(event.data);
          console.log(`📡 [SSE] Received status:`, status);
          setIndexMessage(status.current_step || 'Indexing...');
          
          if (!status.is_indexing) {
            console.log(`✅ [SSE] Indexing complete! Setting status to 'indexed'`);
            clearTimeout(sseTimeout);
            setIndexStatus('indexed');
            setIndexMessage('✓ Indexing completed successfully!');
            setIsIndexing(false);
            eventSource.close();
            console.log(`🔌 [SSE] Stream closed by client`);
          }
        } catch (error) {
          console.error('❌ Error parsing SSE message:', error);
        }
      };
      
      eventSource.onerror = (error) => {
        console.error('❌ [SSE] Stream error:', error);
        console.log(`📊 Current state - isIndexing: ${isIndexing}, indexStatus: ${indexStatus}`);
        clearTimeout(sseTimeout);
        setIndexStatus('error');
        setIndexMessage('Status stream error');
        setIsIndexing(false);
        eventSource.close();
      };
    } catch (error) {
      setIndexStatus('error');
      setIndexMessage('Indexing failed');
      console.error('Indexing error:', error);
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
        setNlExplanation(response.data.question || '');
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
      {/* Music Player Button */}
      <button
        onClick={handleMusicToggle}
        className={`${styles.musicButton} ${isPlayingMusic ? styles.playing : ''}`}
        title={isPlayingMusic ? 'Stop music' : 'Play ambient music'}
        aria-label="Toggle ambient music"
      >
        {isPlayingMusic ? '🎵' : '🎵'}
      </button>

      <h1 className={styles.title}>Natural Language ⇌ SPARQL</h1>
      
      <div className={styles.mainWrapper}>
        {/* ===== CARD 1: SELECT ENDPOINT & INDEX ===== */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div className={styles.cardStep}>1</div>
            <h2 className={styles.cardTitle}>Select Endpoint & Index</h2>
          </div>

          <div className={styles.section}>
            {/* Endpoint Input Row */}
            <div style={{ marginBottom: '16px' }}>
              <label className={styles.label}>SPARQL Endpoint URL</label>
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
            </div>

            {/* Index & Entities Row */}
            <div className={styles.indexLineContainer}>
              {/* Index Button with Tooltip */}
              <button
                onClick={handleIndexLink}
                disabled={isIndexing || indexStatus === 'indexed'}
                className={`${styles.button} ${styles.indexBtn}`}
                data-status={indexMessage}
                title={indexMessage}
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

              {/* Entities Limit Input */}
              <div className={styles.entityLimitContainer}>
                <label className={styles.label}>Entities Limit</label>
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
        </div>

        {/* ===== CARD 2: NL TO SPARQL ===== */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div className={styles.cardStep}>2</div>
            <h2 className={styles.cardTitle}>Natural Language to SPARQL</h2>
          </div>

          <div className={styles.section}>
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
                  {isTranslating ? (
                    <>
                      <span className={styles.skeleton}>⏳</span>
                      <br />
                      Translate
                    </>
                  ) : (
                    <>
                      📖
                      <br />
                      Translate
                    </>
                  )}
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
        </div>

        {/* ===== CARD 3: SPARQL TO NL ===== */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div className={styles.cardStep}>3</div>
            <h2 className={styles.cardTitle}>SPARQL to Natural Language</h2>
          </div>

          <div className={styles.section}>
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
                  {isExplaining ? (
                    <>
                      <span className={styles.skeleton}>⏳</span>
                      <br />
                      Translate
                    </>
                  ) : (
                    <>
                      📖
                      <br />
                      Translate
                    </>
                  )}
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
    </div>
  );
}
