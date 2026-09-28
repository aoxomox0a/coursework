### 📝 Engineering Log: Concurrency Optimization & Backend Scaling

**1. The Baseline & Discovery**
* **Action:** Conducted initial load testing on the `/api/answer` SPARQL generation endpoint to simulate concurrent API traffic. 
* **Methodology:** Used ApacheBench to send a mock JSON question (`{"question": "Who directed the movie Inception released in 2010?"}`). The test was configured for 100 total requests with a concurrency level of 5:
  ```bash
  ab -n 100 -c 5 -p post_data.json -T 'application/json' http://localhost:8000/api/answer
  ```
* **Symptom:** The system struggled under the concurrent load. Wait times spiked to ~13 seconds per request, and system RAM ballooned to an unsustainable 19GB.
* **Diagnosis:** Identified the architecture was suffering from "Model Loading Multiplication." Because FastAPI handles requests concurrently in background threads, synchronous pipeline steps were creating massive duplication.

**2. Intervention 1: Global Model Caching (The RAM Fix)**
* **The Problem:** The pipeline was loading the `en_core_web_sm` spaCy model and the `SentenceTransformer` embedding model from scratch on every single request. 5 concurrent requests meant 5 separate copies of heavyweight neural networks loaded into memory simultaneously.
* **The Fix:** Implemented the **Singleton Pattern** in `spacy_setup.py` and `embedding.py`. Models are now instantiated exactly once into a global variable at server startup, and shared across all incoming requests.
* **Result:** The 19GB RAM spike vanished entirely, memory consumption flatlined, and Requests Per Second (RPS) increased by nearly 70%.

**3. Intervention 2: Database Connection Sharing (The CPU/Locking Fix)**
* **The Problem:** The entity linking pipeline was instantiating a brand new ChromaDB `PersistentClient` for every query. This forced multiple threads to fight over SQLite file locks, creating a severe bottleneck.
* **The Fix:** Refactored the `/link` pipeline to utilize a single, shared database client scoped to the application.
* **Result:** Eliminated thread-locking contention, allowing the vector similarity search to execute truly in parallel.

**4. Intervention 3: HTTP Connection Pooling (The Network Fix)**
* **The Problem:** The server was performing full TCP and TLS/SSL handshakes with the external LLM provider (Hactar) for every generated SPARQL query, adding network latency and risking port exhaustion.
* **The Fix:** Created a globally shared `httpx.AsyncClient` with custom concurrency limits (`max_connections=100`, `max_keepalive_connections=20`) to enable HTTP Keep-Alive. 
* **The Cleanup:** Integrated a FastAPI `lifespan` context manager into `api/main.py` to ensure these persistent network tunnels are gracefully closed when the server shuts down, preventing OS-level socket warnings.

**5. The Final Outcome**
* The architecture successfully shifted from a fragile, hardware-bound script into a highly concurrent, asynchronous web server.
* **Final Metrics:** 98% of requests now complete in under 4.5 seconds (the absolute floor of the external LLM's generation speed). The application is stable and ready for production traffic.
